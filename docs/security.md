# Security

## The one rule everything else follows

**The LLM can request an action. It cannot authorize one.** Every path
that moves money passes through `PaymentService.authorize_and_execute`,
which independently re-checks policy and approval state from the
database — it never trusts a caller's claim about what's already been
authorized. This holds whether the caller is a LangGraph node, a REST
route, or the scheduler.

## What is never done, and why

- **UPI PIN, bank passwords, payment credentials**: never collected,
  stored, logged, or placed in a prompt. There is no code path in this
  repo that even has a field for one.
- **Claude never calls a payment provider directly.** Only
  `PaymentService` imports `PaymentProvider`.
- **A hallucinated or malicious tool call cannot move money.** Proven in
  `tests/agent/test_tools_authorization.py` — calling `execute_payment`
  on an out-of-policy transaction with no approval returns
  `requires_approval: true`, full stop, regardless of what an agent
  claims.
- **Policy is never re-litigated after approval without a re-check.** An
  approved-but-expired approval is treated as expired, not approved, even
  if it was genuinely approved earlier (spec §16).

## Layered idempotency (duplicate-payment prevention)

Three independent layers, any one of which alone would prevent a
double-charge:
1. `MockUPIProvider` dedupes on `idempotency_key` in-memory.
2. `transactions.idempotency_key` has a **database-level UNIQUE
   constraint** — this is the layer that actually matters; the others are
   defense in depth.
3. `TransactionService.get_or_create` catches the resulting
   `IntegrityError` from a race and returns the existing row instead of
   raising.

## Ownership / IDOR

Every mandate, approval, and transaction route checks
`resource.user_id == X-User-ID` before returning or mutating anything.
A mismatch returns the same 404 as genuine non-existence — deliberately,
so a caller probing IDs can't distinguish "not yours" from "doesn't
exist." (Found missing in Phases 1–13, fixed in Phase 14 — noted here
rather than glossed over.)

## Rate limiting

Redis-backed fixed-window limiter on routes that cost money to call
(`/api/chat` — real Anthropic API spend) or trigger financial state
changes (`/api/payments/simulate`, approve, reject). Read-only routes
aren't limited. Fixed-window, not sliding-window/token-bucket — a
deliberate simplicity tradeoff for a prototype; it allows a small burst
right at a window boundary, which doesn't matter at this scale.

## Auth (prototype-only, stated plainly)

A single header, `X-User-ID`, is trusted with no verification. This is
**not** a security boundary — it exists so the rest of the system has a
`user_id` to work with while a real login system isn't built. Every place
that reads it (`app/api/deps.py`) is documented as the one thing that
needs replacing before this could handle a real second user. Nothing else
in the system needed to be designed around this limitation — routes
depend on `get_current_user_id`, not on how it's implemented.

## Callback validation

`/api/webhooks/paytm/callback` fails closed: any payload without a
signature is rejected, and the handler currently raises
`NotImplementedError` rather than trusting an unverified one. This is
intentional — a stubbed "verify later" callback that silently accepts
payloads in the meantime is worse than one that visibly refuses to work
at all.

## Known limitations (stated, not hidden)

- **Single dev-mode user mechanism** — see Auth above.
- **PaytmSandboxProvider is a scaffold**, not a verified integration — see
  `docs/architecture.md` Phase 13 notes. `execute_payment` on it
  deliberately raises `NotImplementedError` rather than pretending to
  work.
- **MockUPIProvider's state is in-process memory** — resets on restart,
  doesn't survive horizontal scaling. Fine for a demo; would need a real
  provider or a shared store otherwise.
- **APScheduler runs in-process**, not distributed — spec's own tech
  stack notes flag Celery/Redis Queue as the production upgrade path,
  and `SchedulerService` is written behind an interface specifically so
  that swap doesn't touch `payment_scheduler.py`'s job logic.
- **No multi-turn slot-filling** in chat — see `docs/agent-workflows.md`.

## Why this is not a production banking system

No real bank integration, no regulator-grade compliance review, no
penetration testing, single-tenant dev auth, and a payment provider layer
that is explicitly a mock. This is a prototype demonstrating an
architecture pattern (deterministic backend as the sole authority over
money movement, LLM strictly advisory) — the pattern is meant to be
production-worthy; this specific codebase has not gone through what real
production banking software requires.