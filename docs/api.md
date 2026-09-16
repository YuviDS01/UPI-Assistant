# API Reference

Base URL: `http://localhost:8000`. All routes except `/health` require an
`X-User-ID: <uuid>` header (prototype dev-mode auth — see `docs/security.md`).

Error responses are always shaped:
```json
{"error_code": "MANDATE_NOT_FOUND", "message": "...", "detail": {}}
```

## System

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness — process is up |
| GET | `/health/ready` | Readiness — Postgres + Redis actually reachable |

## Users

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/users/me` | Resolve X-User-ID header to a profile |

## Mandates

| Method | Path | Request body | Purpose |
|---|---|---|---|
| GET | `/api/mandates` | — | List caller's mandates |
| POST | `/api/mandates` | `{merchant_id, merchant_name, category, amount_limit, frequency, next_payment_date}` | Create a mandate |
| GET | `/api/mandates/{id}` | — | Fetch one (404 if not yours) |
| POST | `/api/mandates/{id}/cancel` | — | Terminal cancel |
| POST | `/api/mandates/{id}/pause` | `{until?: date, reason?: string}` | **Soft-pause (the USP)** — provider mandate untouched |
| POST | `/api/mandates/{id}/resume` | — | Reactivate, no re-authorization needed |

## Payments

| Method | Path | Request body | Purpose |
|---|---|---|---|
| GET | `/api/payments?limit=20` | — | Payment history |
| GET | `/api/payments/upcoming` | — | Active mandates due soon |
| GET | `/api/payments/{id}` | — | Fetch one transaction |
| POST | `/api/payments/simulate` | `{merchant_id, merchant_name, category, amount}` | Prototype stand-in for a detected payment feed. **Rate-limited: 20/min.** |

## Approvals

| Method | Path | Request body | Purpose |
|---|---|---|---|
| GET | `/api/approvals` | — | List caller's approval requests |
| GET | `/api/approvals/{id}` | — | Fetch one (404 if not yours) |
| POST | `/api/approvals/{id}/approve` | — | Approve → policy re-validated → executed if still valid. **Rate-limited: 30/min.** |
| POST | `/api/approvals/{id}/reject` | — | Reject, terminal for that transaction. **Rate-limited: 30/min.** |

## Chat

| Method | Path | Request body | Response | Purpose |
|---|---|---|---|---|
| POST | `/api/chat` | `{message: string, thread_id?: string}` | `{thread_id, intent, response, requires_approval, tool_result}` | Conversational entry point. Omit `thread_id` on first message; reuse the returned one for follow-ups so LangGraph checkpointing keeps context. **Rate-limited: 20/min** (it calls the Anthropic API). |

## Webhooks

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/webhooks/paytm/callback` | Stub — fails closed until Phase 13's checksum verification is wired in. Never trusts an unverified payload. |

## Common error codes

| error_code | HTTP status | Meaning |
|---|---|---|
| VALIDATION_ERROR | 422 | Bad/missing input (including the X-User-ID header itself) |
| USER_NOT_FOUND / MANDATE_NOT_FOUND / TRANSACTION_NOT_FOUND / APPROVAL_NOT_FOUND | 404 | Doesn't exist, **or exists but isn't yours** (deliberately indistinguishable) |
| MANDATE_STATE_ERROR | 409 | e.g. trying to pause an already-cancelled mandate |
| APPROVAL_EXPIRED | 409 | Approval window passed — must request a new one |
| POLICY_VIOLATION | 403 | Internal guard tripped (e.g. a tool called with no valid authorization source) |
| RATE_LIMITED | 429 | Too many requests to a metered route — `detail.retry_after_seconds` given |
| INTERNAL_ERROR | 500 | Unexpected — logged server-side with full traceback, never leaked to the client |