"""
Importing every model here is not decorative -- Alembic's autogenerate walks
Base.metadata, which only knows about a model class once it's been imported
somewhere. Forgetting a model here means Alembic silently won't create its
table. If you add a new model file, add its import here too.
"""

from app.models.approval_request import ApprovalRequest
from app.models.audit_log import AuditLog
from app.models.mandate import Mandate
from app.models.notification import Notification
from app.models.payment_rule import PaymentRule
from app.models.transaction import Transaction
from app.models.user import User

__all__ = [
    "User",
    "Mandate",
    "PaymentRule",
    "Transaction",
    "ApprovalRequest",
    "AuditLog",
    "Notification",
]
