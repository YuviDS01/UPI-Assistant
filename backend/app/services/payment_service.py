"""
PaymentService is the ONLY code in this app allowed to call into a
PaymentProvider.

authorize_and_execute() is the function agent tools call. It deliberately
takes NO authorization_source argument from its caller — it re-derives
authorization from DB state every time (policy engine result, or an
existing APPROVED-and-not-expired approval row). This is what makes it
safe to let an LLM call this: a hallucinated or malicious call can't move
money, because the function doesn't trust anything the caller claims.

execute_payment_authorized() is the lower-level primitive used internally
once authorization is already established — it's also used directly by
the scheduler (Phase 10), which derives its own authorization the same way.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import PolicyViolationError
from app.models import Mandate, Transaction
from app.models.enums import ApprovalStatus, TransactionStatus
from app.payment_providers.base import PaymentProvider
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService

VALID_AUTHORIZATION_SOURCES = {"policy_auto_approved", "human_approved"}


class PaymentService:
    @staticmethod
    def execute_payment_authorized(
        db: Session,
        transaction: Transaction,
        provider: PaymentProvider,
        authorization_source: str,
        mandate: Mandate | None = None,
    ) -> Transaction:
        """
        The single execution path. authorization_source must be one of
        VALID_AUTHORIZATION_SOURCES — this exists so that "why was this
        payment allowed to run" is always an explicit, auditable string,
        never implicit in the fact that the function was merely called.
        """
        if authorization_source not in VALID_AUTHORIZATION_SOURCES:
            raise PolicyViolationError(
                "execute_payment_authorized called without a valid authorization_source.",
                detail={"received": authorization_source, "valid": list(VALID_AUTHORIZATION_SOURCES)},
            )

        if transaction.status in (
            TransactionStatus.SUCCESS,
            TransactionStatus.FAILED,
            TransactionStatus.CANCELLED,
        ):
            return transaction

        transaction.status = TransactionStatus.PROCESSING
        db.flush()

        provider_mandate_id = mandate.provider_mandate_id if mandate else None

        try:
            result = provider.execute_payment(
                idempotency_key=transaction.idempotency_key,
                amount=float(transaction.amount),
                merchant_id=transaction.merchant_id,
                mandate_provider_id=provider_mandate_id,
            )
        except Exception as exc:
            transaction.status = TransactionStatus.FAILED
            transaction.failure_reason = f"Provider error: {exc}"
            AuditService.log_event(
                db,
                "PAYMENT_FAILED",
                "transaction",
                transaction.id,
                user_id=transaction.user_id,
                decision=authorization_source,
                reason=transaction.failure_reason,
            )
            db.commit()
            raise

        transaction.provider_transaction_id = result.provider_transaction_id
        transaction.status = TransactionStatus(result.status)
        transaction.failure_reason = result.failure_reason

        AuditService.log_event(
            db,
            "PAYMENT_EXECUTED",
            "transaction",
            transaction.id,
            user_id=transaction.user_id,
            decision=authorization_source,
            metadata={"amount": float(transaction.amount), "provider_status": result.status},
        )

        if transaction.status == TransactionStatus.SUCCESS:
            AuditService.log_event(
                db, "PAYMENT_SUCCEEDED", "transaction", transaction.id, user_id=transaction.user_id
            )
            NotificationService.notify(
                db,
                transaction.user_id,
                title="Payment successful",
                body=(
                    f"₹{transaction.amount} paid to {transaction.merchant_name}. "
                    f"Transaction ID: {transaction.provider_transaction_id}"
                ),
            )
        elif transaction.status == TransactionStatus.FAILED:
            AuditService.log_event(
                db,
                "PAYMENT_FAILED",
                "transaction",
                transaction.id,
                user_id=transaction.user_id,
                reason=transaction.failure_reason,
            )
            NotificationService.notify(
                db,
                transaction.user_id,
                title="Payment failed",
                body=f"₹{transaction.amount} to {transaction.merchant_name} failed: {transaction.failure_reason}",
            )
        # PENDING/PROCESSING: no terminal notification yet — status polling
        # (get_payment_status) resolves it later, never a blind retry.

        db.commit()
        db.refresh(transaction)
        return transaction

    @staticmethod
    def authorize_and_execute(
        db: Session,
        transaction: Transaction,
        provider: PaymentProvider,
        mandate: Mandate | None = None,
    ) -> dict:
        """
        THE function agent tools call. Never accepts a caller-supplied
        authorization_source — derives it itself from DB state:

          1. Terminal transaction -> no-op, report current state.
          2. Has a mandate -> check_can_execute (ACTIVE/PAUSED/CANCELLED),
             then check_mandate_execution (amount vs mandate limit).
          3. No mandate -> check_category_policy (amount vs payment_rules).
          4. If policy says allowed -> execute with "policy_auto_approved".
          5. If not allowed -> look for an APPROVED, not-expired
             ApprovalRequest tied to this exact transaction -> execute with
             "human_approved". Otherwise, refuse and report requires_approval.

        This function is intentionally the ONLY thing standing between "an
        agent tool call" and "money actually moves" — read it slowly.
        """
        # Local imports to avoid a services <-> policy/mandate import cycle
        from app.policy.engine import PolicyEngine
        from app.services.mandate_service import MandateService

        if transaction.status in (
            TransactionStatus.SUCCESS,
            TransactionStatus.FAILED,
            TransactionStatus.CANCELLED,
        ):
            return {
                "executed": transaction.status == TransactionStatus.SUCCESS,
                "status": transaction.status,
                "reason": "Transaction already in a terminal state.",
                "transaction_id": str(transaction.id),
            }

        engine = PolicyEngine()

        if mandate is not None:
            decision = MandateService.check_can_execute(mandate)
            if not decision.should_execute:
                return {
                    "executed": False,
                    "status": "SKIPPED",
                    "reason": decision.skip_reason,
                    "transaction_id": str(transaction.id),
                }
            policy_result = engine.check_mandate_execution(mandate, float(transaction.amount))
        else:
            policy_result = engine.check_category_policy(
                db, transaction.user_id, transaction.category, float(transaction.amount)
            )

        auth_source: str | None = None

        if policy_result.allowed:
            auth_source = "policy_auto_approved"
        else:
            approval = transaction.approval_request
            if approval is not None and approval.status == ApprovalStatus.APPROVED:
                if approval.expires_at < datetime.now(timezone.utc):
                    return {
                        "executed": False,
                        "requires_approval": True,
                        "reason": "Approval was granted but has since expired — request a new approval.",
                        "transaction_id": str(transaction.id),
                    }
                auth_source = "human_approved"

        if auth_source is None:
            return {
                "executed": False,
                "requires_approval": True,
                "reason": policy_result.reason,
                "policy_result": policy_result.model_dump(),
                "transaction_id": str(transaction.id),
            }

        txn = PaymentService.execute_payment_authorized(db, transaction, provider, auth_source, mandate=mandate)
        return {
            "executed": txn.status == TransactionStatus.SUCCESS,
            "status": txn.status,
            "reason": policy_result.reason,
            "authorization_source": auth_source,
            "transaction_id": str(txn.id),
            "provider_transaction_id": txn.provider_transaction_id,
            "failure_reason": txn.failure_reason,
        }