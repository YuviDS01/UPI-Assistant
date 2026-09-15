# AI Agentic UPI Payment Assistant (Prototype)

A conversational AI assistant that manages recurring UPI payments (mandates),
detects new payments, checks them against a deterministic policy engine, and
routes anything outside policy to a human approval step — while a
non-custodial `MockUPIProvider` stands in for real money movement.

**Not a production banking system.** See `docs/security.md` for the full list
of guardrails (the LLM never authorizes money movement; the backend does).

**USP:** mandates can be **paused** (e.g. "pause my Netflix payment for 2
months") without cancelling the underlying UPI AutoPay authorization — so
resuming later needs no re-authorization. See `docs/architecture.md` §0.

Full architecture, ER diagram, and workflow diagrams: `docs/architecture.md`.

---

## Progress so far

- **Phase 1:** Docker Compose stack (Postgres, Redis, FastAPI), `/health`
- **Phase 2:** SQLAlchemy models, Alembic migrations, seed data, `/health/ready`
- **Phase 3:** proper routing structure, centralized error handling, structured logging, first pytest suite
- **Phase 4 (this update):** deterministic Policy Engine + its test suite

The agent and the frontend are **not** built yet — those come in Phases 7–11.

---

## Prerequisites

- Docker Desktop (running)
- Git
- (Python 3.11+ and Node LTS are needed for later phases when you run tests
  or the frontend outside Docker — not required for this phase)

---

## Setup (Windows PowerShell)

1. Open PowerShell and go into the project folder:
   ```powershell
   cd C:\path\to\upi-payment-assistant
   ```

2. Create your local `.env` from the template:
   ```powershell
   Copy-Item .env.example .env
   ```
   You don't need to fill in `ANTHROPIC_API_KEY` or the Paytm fields yet —
   they aren't used until Phase 7 and Phase 13.

3. Build and start the stack:
   ```powershell
   docker compose up --build
   ```
   First run will take a minute or two (pulling Postgres/Redis images,
   installing Python deps). Leave this terminal running — it streams logs.

4. In a **second** PowerShell window, verify the backend is alive:
   ```powershell
   curl.exe http://localhost:8000/health
   ```
   Expected output:
   ```json
   {"status":"ok","app_env":"development"}
   ```

5. Verify Postgres is accepting connections:
   ```powershell
   docker compose exec db pg_isready -U upi_user -d upi_assistant
   ```
   Expected output:
   ```
   /var/run/postgresql:5432 - accepting connections
   ```

6. Verify Redis is accepting connections:
   ```powershell
   docker compose exec redis redis-cli ping
   ```
   Expected output:
   ```
   PONG
   ```

If all three checks pass, Phase 1 is done.

---

## Setup (Phase 2 — Windows PowerShell)

Run this **after** Phase 1's three checks all pass.

1. Rebuild the backend image (requirements.txt changed — SQLAlchemy/Alembic/psycopg/redis were added):
   ```powershell
   docker compose up --build -d
   ```
   `-d` runs it in the background so you get your terminal back.

2. Generate the initial migration from the models (Alembic compares
   `Base.metadata` against the live — currently empty — database and writes
   the `CREATE TABLE` statements for you):
   ```powershell
   docker compose exec backend alembic revision --autogenerate -m "initial schema"
   ```
   Expected output ends with something like:
   ```
   Generating /app/migrations/versions/xxxxxxxxxxxx_initial_schema.py ...  done
   ```
   Open that generated file in `backend/migrations/versions/` and skim it —
   you should see `create_table` calls for `users`, `mandates`,
   `payment_rules`, `transactions`, `approval_requests`, `audit_logs`,
   `notifications`. If any table is missing, tell me before you continue —
   don't apply a migration you haven't looked at.

3. Apply the migration:
   ```powershell
   docker compose exec backend alembic upgrade head
   ```
   Expected output ends with:
   ```
   Running upgrade  -> xxxxxxxxxxxx, initial schema
   ```

4. Verify the tables exist:
   ```powershell
   docker compose exec db psql -U upi_user -d upi_assistant -c "\dt"
   ```
   Expected: a list of 7 tables (`users`, `mandates`, `payment_rules`,
   `transactions`, `approval_requests`, `audit_logs`, `notifications`,
   plus Alembic's own `alembic_version`).

5. Load the deterministic demo data:
   ```powershell
   docker compose exec backend python -m app.core.seed
   ```
   Expected output:
   ```
   Seeded demo user <uuid> with 2 rules, 1 mandate, 3 transactions.
   ```

6. Confirm readiness end-to-end:
   ```powershell
   curl.exe http://localhost:8000/health/ready
   ```
   Expected:
   ```json
   {"status":"ok","checks":{"database":"ok","redis":"ok"}}
   ```

7. (Optional sanity check) look at the seeded mandate directly:
   ```powershell
   docker compose exec db psql -U upi_user -d upi_assistant -c "SELECT merchant_name, status, next_payment_date FROM mandates;"
   ```
   Expected: one row — `State Electricity Board | ACTIVE | <a date 30 days out>`.

If step 6 returns `"status":"ok"` for both checks, Phase 2 is done.

### Re-running from scratch
If you ever want to wipe the database and start clean:
```powershell
docker compose down -v
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.core.seed
```

### Stopping the stack
```powershell
docker compose down
```
(Add `-v` only if you want to wipe the Postgres data volume — you won't need
that until we're resetting demo data on purpose.)

---

## Setup (Phase 3 — Windows PowerShell)

Run this **after** Phase 2's steps all pass.

1. Rebuild the backend image (requirements.txt changed — httpx/pytest added):
   ```powershell
   docker compose up --build -d
   ```

2. Run the test suite (it runs against your real Postgres/Redis from
   docker-compose — there's no separate test database in this prototype):
   ```powershell
   docker compose exec backend pytest -v
   ```
   Expected: all tests pass, something like:
   ```
   tests/integration/test_health.py::test_health_returns_ok PASSED
   tests/integration/test_health.py::test_health_ready_reports_db_and_redis PASSED
   tests/integration/test_users.py::test_me_without_header_returns_422_validation_error PASSED
   tests/integration/test_users.py::test_me_with_malformed_uuid_returns_422 PASSED
   tests/integration/test_users.py::test_me_with_unknown_uuid_returns_404_user_not_found PASSED
   tests/integration/test_users.py::test_me_with_seeded_demo_user_returns_profile PASSED
   tests/unit/test_logging.py::test_response_includes_request_id_header PASSED
   ======================== 7 passed in X.XXs ========================
   ```
   If `test_me_with_seeded_demo_user_returns_profile` fails with "Demo user
   not found", run `docker compose exec backend python -m app.core.seed`
   first (Phase 2 step 5), then re-run the tests.

3. Manually exercise the new `/api/users/me` route. First get the demo
   user's real ID:
   ```powershell
   docker compose exec db psql -U upi_user -d upi_assistant -t -c "SELECT id FROM users WHERE email='demo.user@example.com';"
   ```
   Copy the UUID it prints, then:
   ```powershell
   curl.exe -H "X-User-ID: PASTE_UUID_HERE" http://localhost:8000/api/users/me
   ```
   Expected: a JSON object with `"name":"Demo User"`.

4. Confirm error handling is consistent — call the same route with a
   garbage header:
   ```powershell
   curl.exe -H "X-User-ID: not-a-real-id" http://localhost:8000/api/users/me
   ```
   Expected:
   ```json
   {"error_code":"VALIDATION_ERROR","message":"X-User-ID header is not a valid UUID.","detail":{"received":"not-a-real-id"}}
   ```

5. Check the backend logs are structured JSON now:
   ```powershell
   docker compose logs backend --tail 20
   ```
   Expected: each request line is a single JSON object with `method`,
   `path`, `status_code`, `duration_ms`, and `request_id` fields.

If steps 2–5 all match, Phase 3 is done.

---

## Setup (Phase 4 — Windows PowerShell)

No new dependencies this phase — the Policy Engine is pure Python + the DB
models you already have.

1. Rebuild (picks up the new files):
   ```powershell
   docker compose up --build -d
   ```

2. Run just the policy engine tests:
   ```powershell
   docker compose exec backend pytest tests/unit/test_policy_engine.py -v
   ```
   Expected: 8 tests, all passing:
   ```
   test_groceries_within_limit_is_allowed PASSED
   test_groceries_over_limit_requires_approval PASSED
   test_subscription_at_exact_boundary_is_allowed PASSED
   test_subscription_just_over_boundary_requires_approval PASSED
   test_category_with_no_rule_requires_approval PASSED
   test_rule_with_auto_approve_false_always_requires_approval PASSED
   test_mandate_amount_within_limit_is_allowed PASSED
   test_mandate_amount_over_limit_requires_approval PASSED
   ======================== 8 passed in X.XXs ========================
   ```

3. Run the full suite to confirm nothing from Phase 3 broke:
   ```powershell
   docker compose exec backend pytest -v
   ```
   Expected: 15 passed (7 from before + 8 new).

If both pass, Phase 4 is done — and it's worth noticing *why* it was this
short: the policy engine has zero dependency on FastAPI, the DB session
lifecycle beyond a plain query, or anything agent-related. That's
deliberate — it's the one piece of this whole system that must be boring,
predictable, and testable in complete isolation.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `docker compose` not recognized | Docker Desktop not on PATH / not running | Open Docker Desktop, wait for it to say "running", retry |
| Port `8000`/`5432`/`6379` already in use | Something else on your machine is using it | Stop that process, or change the left-hand port number in `docker-compose.yml` |
| `curl.exe` gives "connection refused" | Backend still starting, or build failed | Check the first terminal's logs for a Python traceback |
| Backend container keeps restarting | Syntax error in `app/main.py` or bad `.env` | Read the traceback in `docker compose logs backend` — paste it back to me |

---

## Project layout

See `docs/architecture.md` §6 for the full annotated directory tree.
