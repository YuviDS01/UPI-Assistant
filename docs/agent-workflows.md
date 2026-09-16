# Agent Workflows

## Design principle

Claude is used for exactly two things: **classifying intent + extracting
entities** (`classify_intent` node), and nothing else touches the LLM.
Every workflow node after that is plain deterministic Python calling
Phase 6 services through Phase 7 tools. This is a stricter design than a
general ReAct tool-calling loop — Claude never chooses which tool to call
next; the classified intent fixes which fixed sequence of nodes runs.
That's what makes "the LLM is not a security boundary" (spec §23) true by
construction rather than by discipline.

## State

`PaymentState` (TypedDict, `app/agent/state.py`) carries: `user_id`,
`message`, `intent`, extracted entities (`merchant_name`, `category`,
`amount`, `frequency`, `next_payment_date`, `pause_until`, `reason`),
resolved `mandate_id`, `transaction_id`, `approval_id`, loaded `context`
(the user's mandates, for entity resolution), `tool_result`, and the final
`response` string. Nothing sensitive — no PIN, no credentials — is ever
stored here.

## Graph shape
classify_intent → load_context → [routed by intent] → END


`load_context` resolves a fuzzy mandate reference ("my netflix payment")
to a real `mandate_id` by matching merchant name/category against the
user's existing mandates — plain DB lookup, no LLM call.

## Routes

| Intent | Node | What it does |
|---|---|---|
| CREATE_MANDATE | `create_mandate_node` | Validates required fields present, calls `create_mandate` tool |
| CANCEL_MANDATE | `cancel_mandate_node` | Terminal cancel via tool |
| **PAUSE_MANDATE** | `pause_mandate_node` | **The USP.** Calls `pause_mandate` tool — provider mandate untouched |
| **RESUME_MANDATE** | `resume_mandate_node` | Reactivates, no re-authorization |
| NEW_PAYMENT | `new_payment_node` | Records the payment, checks policy, executes if allowed, else creates an approval request and stops |
| RECURRING_PAYMENT | `recurring_payment_node` | User-initiated trigger of a mandate via chat (distinct from the scheduler's own automatic path, Phase 10) |
| VIEW_MANDATES / VIEW_UPCOMING / VIEW_HISTORY | `query_node` | Read-only, formats already-fetched data — never fabricates a row |
| UNKNOWN | `unknown_node` | Asks the user to rephrase |

## Checkpointing

Postgres-backed (`langgraph-checkpoint-postgres`, Phase 9) — an
approval-pending conversation survives a server restart, per spec §16.
Thread continuity is keyed by `thread_id`, which the frontend persists in
`localStorage` and sends back on every `/api/chat` call.

## Prototype simplification, stated plainly

There is no multi-turn slot-filling loop. If `CREATE_MANDATE` is missing a
required field, the node asks for it in one message and the conversation
ends there — the user's next message starts a fresh graph run rather than
resuming a paused "waiting for more info" state. A production version
would use LangGraph's interrupt mechanism to actually pause mid-workflow
for missing information, the same way approvals pause mid-workflow for a
human decision. This wasn't built because the added complexity didn't
change any safety property — it only affects conversational polish.

## Why the agent can't cheat

`execute_payment` (the tool) takes only a `transaction_id`. It does not
accept, and has never accepted, any argument resembling "this is
authorized" — `PaymentService.authorize_and_execute` re-derives
authorization from database state (policy engine result, or an existing
APPROVED-and-unexpired approval row) on every single call, regardless of
what any node believes happened earlier in the conversation. See
`tests/agent/test_tools_authorization.py` for this proven directly.