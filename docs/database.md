# Database Schema

PostgreSQL 16. All tables use UUID primary keys (`gen_random_uuid()` via
Python's `uuid.uuid4()` at the application layer, not a DB default — this
keeps ID generation testable without hitting the database).

## Tables

### users
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(255) | NOT NULL |
| email | VARCHAR(255) | NOT NULL, UNIQUE, indexed |
| phone | VARCHAR(20) | nullable |
| created_at | TIMESTAMPTZ | server default now() |
| updated_at | TIMESTAMPTZ | server default now(), on update now() |

### mandates
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, ON DELETE CASCADE, indexed |
| merchant_id | VARCHAR(255) | NOT NULL |
| merchant_name | VARCHAR(255) | NOT NULL |
| category | VARCHAR(100) | NOT NULL |
| amount_limit | NUMERIC(10,2) | NOT NULL |
| frequency | VARCHAR(20) | NOT NULL — DAILY / WEEKLY / MONTHLY / YEARLY |
| next_payment_date | DATE | NOT NULL, indexed |
| status | VARCHAR(20) | NOT NULL, indexed — ACTIVE / PAUSED / CANCELLED / EXPIRED |
| pause_reason | VARCHAR(255) | nullable — the USP |
| paused_until | DATE | nullable — NULL while paused means indefinite |
| provider_mandate_id | VARCHAR(255) | nullable, UNIQUE — never touched while paused |
| created_at / updated_at | TIMESTAMPTZ | as above |

Composite index: `(status, next_payment_date)` — this is the scheduler's
primary query path (`WHERE status IN (ACTIVE, PAUSED) AND next_payment_date <= today`).

### payment_rules
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, CASCADE, indexed |
| category | VARCHAR(100) | NOT NULL |
| max_amount | NUMERIC(10,2) | NOT NULL |
| auto_approve | BOOLEAN | NOT NULL, default TRUE |
| created_at / updated_at | TIMESTAMPTZ | |

Unique constraint: `(user_id, category)` — one rule per category per user.

### transactions
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, CASCADE, indexed |
| mandate_id | UUID | FK → mandates.id, SET NULL, indexed, nullable |
| merchant_id / merchant_name / category | VARCHAR | NOT NULL |
| amount | NUMERIC(10,2) | NOT NULL |
| currency | VARCHAR(3) | default 'INR' |
| payment_type | VARCHAR(20) | RECURRING / NEW |
| status | VARCHAR(20) | indexed — PENDING / PROCESSING / SUCCESS / FAILED / CANCELLED |
| provider_transaction_id | VARCHAR(255) | nullable |
| idempotency_key | VARCHAR(255) | **NOT NULL, UNIQUE, indexed** — the duplicate-payment guarantee |
| failure_reason | VARCHAR(500) | nullable |
| created_at / updated_at | TIMESTAMPTZ | |

Composite index: `(user_id, status)`.

### approval_requests
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, CASCADE, indexed |
| transaction_id | UUID | FK → transactions.id, CASCADE, **UNIQUE** (0-or-1 approval per transaction) |
| reason | VARCHAR(500) | NOT NULL |
| status | VARCHAR(20) | indexed — PENDING / APPROVED / REJECTED / EXPIRED |
| expires_at | TIMESTAMPTZ | NOT NULL, indexed |
| approved_at / rejected_at | TIMESTAMPTZ | nullable |
| created_at | TIMESTAMPTZ | |

### audit_logs
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, SET NULL, nullable, indexed |
| event_type | VARCHAR(100) | NOT NULL |
| entity_type | VARCHAR(50) | NOT NULL |
| entity_id | UUID | NOT NULL |
| decision | VARCHAR(50) | nullable |
| reason | VARCHAR(500) | nullable |
| log_metadata | JSONB | nullable — never contains secrets or a UPI PIN |
| created_at | TIMESTAMPTZ | indexed |

Composite index: `(entity_type, entity_id)`.

**Column named `log_metadata`, not `metadata`:** SQLAlchemy's Declarative
base reserves the attribute name `metadata` on every model class — using
it would shadow `Base.metadata`. This is a naming workaround, not a schema
decision with meaning.

### notifications
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, CASCADE, indexed |
| title | VARCHAR(255) | NOT NULL |
| body | VARCHAR(1000) | NOT NULL |
| channel | VARCHAR(20) | default 'console' |
| read | BOOLEAN | default FALSE |
| created_at | TIMESTAMPTZ | |

### LangGraph checkpoint tables (Phase 9, auto-created by `PostgresSaver.setup()`)
`checkpoints`, `checkpoint_writes`, `checkpoint_blobs` — managed entirely
by the `langgraph-checkpoint-postgres` library, not by our Alembic
migrations. Don't hand-edit these.

## Relationships