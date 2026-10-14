# EDITH — Development Phases
## Complete Phase Breakdown: From Foundation to Deployment

**Document Version:** 1.0.0
**Status:** Approved Planning Baseline
**Last Updated:** October 2026
**Companion Documents:** PRD.md · SYSTEM_ARCHITECTURE.md · IMPLEMENTATION.md

---

> **IMPORTANT:** Each phase must be **approved before implementation begins**. Each phase produces **testable, runnable deliverables** — no phase ends with code that cannot be verified.

---

## Phase Dependency Graph

```
Phase 0 (Design) — COMPLETE
    |
    v
Phase 1 (Foundation: Docker + FastAPI + DB + Health)
    |
    v
Phase 2 (Auth + Facilities + Users + RBAC)
    |
    v
Phase 3 (Emergency Requests — Core Workflow)
    |
    v
Phase 4 (Volunteer Offers + Assignment Approval)
    |
    v
Phase 5 (Logistics + Verified Delivery + Disputes)
    |
    v
Phase 6 (Dashboard APIs + Audit History)
    |
    v
Phase 7 (Offline PWA + Service Worker + Sync Engine)
    |
    v
Phase 8 (Testing + Deployment + Demo)
```

---

## Phase 0 — Requirements & Design COMPLETE

**Objective:** Establish the authoritative design baseline before any code is written.

### Deliverables Produced
- [x] PRD.md — Full product requirements, user roles, lifecycle rules, business invariants
- [x] SYSTEM_ARCHITECTURE.md — 3-tier architecture, ERD, API catalogue, security, offline sync, ADRs
- [x] DEVELOPMENT_PHASES.md — This document
- [x] IMPLEMENTATION.md — Task-level implementation guide

### Design Decisions Locked
- [x] PostgreSQL 16 via Docker from Day 1
- [x] Dual-token JWT strategy (1hr access + 24hr refresh) for offline resilience
- [x] Option A partial allocation — coordinators approve partial quantities from an offer
- [x] Modular monolith (no microservices)
- [x] Vanilla JS + CSS + HTML PWA (no frontend framework)
- [x] client_id UUID idempotency on all mutable entities
- [x] SELECT FOR UPDATE concurrency control for allocation transactions
- [x] Append-only audit_events in same DB transaction

### Acceptance Criteria
- [x] All state machines documented with role transition matrices
- [x] ERD with correct 1:N cardinalities
- [x] Full API catalogue with standard error envelope
- [x] Offline sync protocol with conflict resolution matrix
- [x] Architecture comparison with ChatGPT baseline — gaps identified

---

## Phase 1 — Foundation

**Objective:** Build the structural backbone. Server runs, connects to PostgreSQL, passes health check.

### 1.1 — Docker & PostgreSQL Environment

| Task | Description | Acceptance |
|------|-------------|------------|
| docker-compose.yml | postgres:16-alpine, named volume, healthcheck | docker compose up -d -> container healthy |
| .env.example | DATABASE_URL, SECRET_KEY, ENVIRONMENT, LOG_LEVEL | All keys present with examples |
| .env (local) | Actual secrets (gitignored) | postgres accessible on localhost:5432 |
| Volume persistence | Named Docker volume postgres_data | Data survives docker compose down + up |

### 1.2 — Backend Project Skeleton

| Task | Description | Acceptance |
|------|-------------|------------|
| requirements.txt | FastAPI, Uvicorn, SQLAlchemy 2.0, Psycopg3, Alembic, Pydantic, Pydantic-Settings, Pytest, HTTPX, python-jose, passlib | pip install succeeds |
| backend/Dockerfile | Python 3.12-slim, copy + install, expose 8000 | Container builds and runs |
| backend/app/main.py | FastAPI app factory, register routers, CORS middleware | App imports without error |
| backend/app/core/config.py | Settings class via Pydantic-Settings from .env | Settings() loads all values |

### 1.3 — Database Session & Base Model

| Task | Description | Acceptance |
|------|-------------|------------|
| backend/app/db/session.py | SQLAlchemy async engine, AsyncSessionLocal, get_db() | Session connects to PostgreSQL |
| backend/app/db/base.py | Base + TimestampMixin (created_at, updated_at) + UUIDPKMixin | Mixin applies to all future models |

### 1.4 — Alembic Migration Setup

| Task | Description | Acceptance |
|------|-------------|------------|
| alembic init | Initialize inside backend/ | alembic/ directory created |
| alembic/env.py | Connect to DATABASE_URL, import Base.metadata | alembic current works |
| Initial migration | alembic revision --autogenerate -m "initial_empty" | Migration file generated |
| Apply migration | alembic upgrade head | No errors; alembic_version table in DB |

### 1.5 — Health Check Endpoint

| Task | Description | Acceptance |
|------|-------------|------------|
| GET /api/v1/health | Query SELECT 1; return status + database + version | 200 when DB healthy; 503 when unreachable |

### 1.6 — Test Infrastructure

| Task | Description | Acceptance |
|------|-------------|------------|
| tests/conftest.py | Test DB setup, override get_db, HTTPX AsyncClient fixture | pytest discovers tests |
| tests/test_health.py | Health with DB up; health with DB broken | Both pass |

### Phase 1 Done Criteria
- [ ] docker compose up -d -> PostgreSQL healthy
- [ ] alembic upgrade head -> succeeds
- [ ] uvicorn app.main:app --reload -> server starts
- [ ] GET /api/v1/health -> {"status":"ok","database":"connected"}
- [ ] pytest tests/ -> 100% pass

### Known Risks
- Psycopg3 async driver requires psycopg[async] — verify driver string in DATABASE_URL
- Alembic env.py must use async engine adapter for SQLAlchemy 2.0

---

## Phase 2 — Authentication & Facility Management

**Objective:** Users log in, receive JWT tokens, refresh when expired. Backend enforces RBAC on every endpoint.

### 2.1 — Database Models

| Task | Description | Acceptance |
|------|-------------|------------|
| Facility model | id, name, facility_type CHECK, lat, lon, address, contact, is_active, timestamps | Migration creates correct constraints |
| User model | id, facility_id FK, username UNIQUE, hashed_password, role CHECK, is_active, timestamps | User requires valid facility_id |
| Alembic migration | add_facilities_users | Tables created with all constraints |

### 2.2 — Pydantic Schemas

| Schema | Fields | Purpose |
|--------|--------|---------|
| FacilityCreate | name, facility_type, address, contact_phone, lat, lon | Admin creates facility |
| FacilityOut | All fields except sensitive | API response |
| UserCreate | username, password, full_name, phone, role, facility_id | Admin creates user |
| UserOut | All fields except hashed_password | API response |
| LoginRequest | username, password | Login body |
| TokenResponse | access_token, refresh_token, token_type, user_profile | Login response |
| RefreshRequest | refresh_token | Refresh body |

### 2.3 — Security Utilities

| Task | Description | Acceptance |
|------|-------------|------------|
| security.py | hash_password(), verify_password() using Bcrypt | Password never stored plain |
| create_access_token() | JWT with sub, role, facility_id, exp (1hr) | Verifiable via decode_token() |
| create_refresh_token() | JWT with sub, type:refresh, exp (24hr) | Distinguishable from access |
| decode_token() | Verify signature, check expiry | Expired raises 401 |

### 2.4 — FastAPI Dependencies

| Task | Description | Acceptance |
|------|-------------|------------|
| get_current_user() | Extract Bearer token, decode, load user | Returns User or raises 401 |
| require_role(*roles) | Dependency factory: checks user.role in allowed_roles | Returns user or raises 403 |
| get_current_facility() | Returns facility of current user | Used for ownership checks |

### 2.5 — Auth Endpoints

| Endpoint | Logic | Acceptance |
|----------|-------|------------|
| POST /api/v1/auth/login | Verify credentials; issue tokens | Valid -> 200 + tokens; wrong -> 401 |
| POST /api/v1/auth/refresh | Verify refresh token; issue new access | Valid -> 200 + access; expired -> 401 |

### 2.6 — Facility & User Endpoints

| Endpoint | Logic | Acceptance |
|----------|-------|------------|
| GET /api/v1/facilities | List all active facilities | Paginated list |
| POST /api/v1/facilities | Admin-only: create facility | 409 if name conflict |
| POST /api/v1/users | Admin-only: create user | Password hashed before store |
| GET /api/v1/users/me | Return current user profile | User + facility details |

### 2.7 — Seed Data Script

| Task | Description |
|------|-------------|
| scripts/seed.py | 1 Command Centre + 1 ICC Coordinator; 2 Hospitals + 2 Hospital Users; 1 Logistics Operator |

### Phase 2 Done Criteria
- [ ] POST /auth/login returns access + refresh tokens
- [ ] POST /auth/refresh issues new access token
- [ ] GET /users/me returns correct user + facility
- [ ] Role-protected endpoint rejects wrong role with 403
- [ ] Seed script creates all test users
- [ ] All auth tests pass

---

## Phase 3 — Emergency Request Management

**Objective:** Hospitals create emergency requests. ICC acknowledges and manages state. Full idempotency enforced.

### 3.1 — Database Model

| Field | Type | Constraint |
|-------|------|------------|
| id | UUID PK | Auto |
| client_id | UUID | UNIQUE — idempotency key |
| requesting_facility_id | UUID FK | References facilities |
| resource_name | VARCHAR(100) | NOT NULL |
| unit | VARCHAR(30) | NOT NULL |
| quantity_required | INT | CHECK > 0 |
| urgency | VARCHAR(20) | CHECK IN (LOW, MEDIUM, HIGH, CRITICAL) |
| status | VARCHAR(30) | CHECK IN lifecycle states; DEFAULT SUBMITTED |
| operational_notes | TEXT | Nullable |
| created_by_id | UUID FK | References users |
| timestamps | TIMESTAMPTZ | Auto |

### 3.2 — Pydantic Schemas

| Schema | Key Fields |
|--------|------------|
| RequestCreate | client_id (required), resource_name, unit, quantity_required, urgency, operational_notes |
| RequestOut | All fields + requesting_facility details nested |
| RequestListOut | Paginated list + total_count |
| AcknowledgeOut | id, status, acknowledged_at, acknowledged_by |

### 3.3 — Service Layer

| Function | Logic | Invariant |
|----------|-------|-----------|
| create_request() | Check client_id uniqueness -> if exists return existing; else INSERT SUBMITTED | Duplicate retry returns same record |
| acknowledge_request() | Verify status==SUBMITTED; UPDATE ACKNOWLEDGED; audit log | ICC Coordinator only |
| cancel_request() | Verify no active assignments; UPDATE CANCELLED; audit | Blocked if active assignments exist |
| get_requests() | Filter by status, urgency, facility_id; paginate | Role-scoped results |
| get_request_detail() | Join with offers, assignments, deliveries | Full operational picture |

### 3.4 — API Endpoints

| Endpoint | Authorized Role | Key Behavior |
|----------|-----------------|--------------|
| POST /api/v1/requests | HOSPITAL_USER | Idempotent via client_id |
| GET /api/v1/requests | ALL | Paginated; filter by status, urgency |
| GET /api/v1/requests/{id} | ALL | Full detail with nested relationships |
| POST /api/v1/requests/{id}/acknowledge | ICC_COORDINATOR | SUBMITTED -> ACKNOWLEDGED |
| POST /api/v1/requests/{id}/cancel | HOSPITAL_USER (own), ICC | No active assignments guard |
| POST /api/v1/requests/{id}/resolve | ICC_COORDINATOR | Validates confirmed qty >= required |

### 3.5 — Tests

| Test Scenario | Expected Outcome |
|---------------|------------------|
| Create request online | 201 created, status=SUBMITTED |
| Create same request (same client_id) | 200 with existing record, no duplicate |
| ICC acknowledges | status -> ACKNOWLEDGED |
| Hospital user tries to acknowledge | 403 Forbidden |
| Cancel with no assignments | Succeeds |
| Resolve with insufficient delivery | 409 — insufficient confirmed delivery |
| Quantity <= 0 | 422 Unprocessable |

### Phase 3 Done Criteria
- [ ] Hospital creates request with client_id
- [ ] Duplicate client_id returns existing (not error, not duplicate)
- [ ] ICC acknowledges; hospital cannot
- [ ] Cancel blocked when active assignments exist
- [ ] Resolve blocked when confirmed delivery < required
- [ ] Audit event written for every state transition
- [ ] All tests pass

---

## Phase 4 — Volunteer Offers & Assignment Approval

**Objective:** Facilities volunteer quantities. ICC approves (partial or full) atomically creating assignments. Row-level locking prevents over-allocation race conditions.

### 4.1 — Database Models

| Model | Critical Fields | Critical Constraints |
|-------|----------------|---------------------|
| VolunteerOffer | client_id UNIQUE, offering_facility_id FK, target_request_id FK nullable, quantity_offered >0, quantity_allocated >=0, status ENUM | quantity_allocated <= quantity_offered (CHECK) |
| Assignment | request_id FK, offer_id FK, assigned_quantity >0, status ENUM, approved_by_id FK | No direct client creation |

### 4.2 — Atomic Approval Transaction (Critical)

```
approve_offer() transaction:
  BEGIN TX
    1. SELECT emergency_requests WHERE id=req_id FOR UPDATE   (row lock)
    2. SELECT volunteer_offers WHERE id=offer_id FOR UPDATE   (row lock)
    3. confirmed_delivered = SUM(deliveries.quantity_received WHERE CONFIRMED)
    4. active_committed = SUM(assignments.assigned_quantity WHERE NOT CANCELLED/EXCEPTION)
    5. remaining = quantity_required - confirmed_delivered - active_committed
    6. ASSERT qty_to_assign <= remaining          -> 409 OVER_ALLOCATION_PROHIBITED
    7. ASSERT qty_to_assign <= (quantity_offered - quantity_allocated) -> 409 OFFER_CAPACITY_EXCEEDED
    8. INSERT assignments (status=APPROVED)
    9. UPDATE volunteer_offers.quantity_allocated += qty_to_assign
   10. UPDATE volunteer_offers.status -> PARTIALLY_APPROVED / FULLY_APPROVED
   11. UPDATE emergency_requests.status -> IN_PROGRESS (if ACKNOWLEDGED)
   12. INSERT audit_events x3
  COMMIT
```

### 4.3 — API Endpoints

| Endpoint | Authorized Role | Key Behavior |
|----------|-----------------|--------------|
| POST /api/v1/offers | HOSPITAL_USER | Idempotent; validates facility ownership |
| GET /api/v1/offers | ALL | Paginated; filter by status, request |
| GET /api/v1/offers/{id} | ALL | Full detail with assignments |
| POST /api/v1/offers/{id}/approve | ICC_COORDINATOR | Atomic transaction with row locks |
| POST /api/v1/offers/{id}/reject | ICC_COORDINATOR | PENDING -> REJECTED |
| POST /api/v1/offers/{id}/withdraw | HOSPITAL_USER | Validates unallocated balance |
| GET /api/v1/assignments | ALL | Paginated assignment list |
| GET /api/v1/assignments/{id} | ALL | Detail with delivery history |
| POST /api/v1/assignments/{id}/prepare | LOGISTICS, HOSPITAL_USER | APPROVED -> PREPARING |
| POST /api/v1/assignments/{id}/cancel | ICC_COORDINATOR | CANCELLED; release offer quantity |

### 4.4 — Concurrency Tests (Critical)

| Test Scenario | Expected Outcome |
|---------------|------------------|
| Single offer approval within quota | 201 Assignment; offer FULLY_APPROVED |
| Partial offer approval | Offer PARTIALLY_APPROVED; quantity_allocated updated |
| Over-allocation (sequential) | 409 OVER_ALLOCATION_PROHIBITED |
| Concurrent over-allocation (two simultaneous) | Exactly one succeeds; second gets 409 |
| Withdraw with zero allocated | Offer WITHDRAWN |
| Hospital tries to approve offer | 403 Forbidden |
| Same offer twice (client_id) | Idempotent |

### Phase 4 Done Criteria
- [ ] Offer creation idempotent via client_id
- [ ] Approve offer creates assignment atomically
- [ ] quantity_allocated correctly updated on partial approval
- [ ] Over-allocation impossible (sequential AND concurrent)
- [ ] PARTIALLY_APPROVED state correctly set
- [ ] Assignment cancellation releases offer allocated quantity
- [ ] Concurrency test passes
- [ ] All tests pass

---

## Phase 5 — Logistics & Verified Delivery

**Objective:** Logistics records dispatch and delivery. Recipients confirm or dispute. ICC resolves disputes. Driver "delivered" does NOT equal request fulfilled.

### 5.1 — Database Model

| Field | Type | Rule |
|-------|------|------|
| id | UUID PK | Auto |
| client_id | UUID UNIQUE | Idempotency |
| assignment_id | UUID FK | Required |
| quantity_dispatched | INT | > 0 |
| quantity_received | INT nullable | >= 0; null until confirmed |
| status | VARCHAR ENUM | DISPATCHED, DELIVERED_RECORDED, RECEIPT_CONFIRMED, RECEIPT_DISPUTED, DISPUTE_RESOLVED |
| transporter_info | TEXT | Required |
| discrepancy_reason | VARCHAR ENUM | NONE, DAMAGED_CARGO, SHORT_SHIPMENT, WRONG_SPECIFICATION, CONTAMINATED, LOST_IN_TRANSIT |
| dispatched_at | TIMESTAMPTZ | Auto |
| confirmed_by_id | UUID FK | Set on confirmation |

### 5.2 — Fulfillment Calculation Logic

```
After any delivery confirmation:
  total_confirmed = SUM(quantity_received)
    FROM deliveries
    WHERE assignment links to request
    AND status IN (RECEIPT_CONFIRMED, DISPUTE_RESOLVED)

  If total_confirmed >= assigned_quantity:
    UPDATE assignment SET status = FULFILLED
  Else:
    UPDATE assignment SET status = PARTIALLY_FULFILLED

  Request stays IN_PROGRESS until ICC manually confirms resolution.
  AUTO-CLOSURE OF REQUEST IS PROHIBITED.
```

### 5.3 — API Endpoints

| Endpoint | Authorized Role | Key Behavior |
|----------|-----------------|--------------|
| POST /api/v1/deliveries | LOGISTICS_OPERATOR | Create for dispatched assignment |
| GET /api/v1/deliveries/{id} | ALL | Full delivery detail |
| POST /api/v1/deliveries/{id}/record | LOGISTICS_OPERATOR | Driver logs drop-off |
| POST /api/v1/deliveries/{id}/confirm | HOSPITAL_USER (recipient) | Confirm qty received |
| POST /api/v1/deliveries/{id}/dispute | HOSPITAL_USER (recipient) | Log discrepancy |
| POST /api/v1/deliveries/{id}/resolve-dispute | ICC_COORDINATOR | Set authoritative qty |
| POST /api/v1/assignments/{id}/dispatch | LOGISTICS_OPERATOR | PREPARING -> DISPATCHED |
| POST /api/v1/assignments/{id}/exception | LOGISTICS, ICC | -> EXCEPTION |

### 5.4 — Tests

| Test Scenario | Expected Outcome |
|---------------|------------------|
| Create delivery for dispatched assignment | 201 DISPATCHED |
| Driver records delivery | DELIVERED_RECORDED; NOT fulfilled |
| Recipient confirms full quantity | RECEIPT_CONFIRMED; FULFILLED |
| Recipient confirms partial (10 of 12) | PARTIALLY_FULFILLED |
| Recipient disputes delivery | RECEIPT_DISPUTED; qty NOT counted |
| ICC resolves dispute with qty=10 | DISPUTE_RESOLVED; qty counted |
| Auto-resolve request after partial | 409 — cannot resolve |
| Non-recipient confirms | 403 Forbidden |
| Duplicate delivery (client_id) | Idempotent |

### Phase 5 Done Criteria
- [ ] Delivery lifecycle enforced correctly
- [ ] Driver delivered != request fulfilled
- [ ] Disputed deliveries do NOT count toward fulfillment
- [ ] Partial delivery keeps request IN_PROGRESS
- [ ] Request auto-resolution blocked
- [ ] Dispute resolution updates quantity correctly
- [ ] All audit events written
- [ ] All tests pass

---

## Phase 6 — ICC Dashboard APIs & Audit History

**Objective:** ICC sees real-time operational picture: unacknowledged requests, overdue items, pending offers, disputed deliveries, partial fulfillments.

### 6.1 — Dashboard Summary Endpoint

```
GET /api/v1/dashboard/summary

Response:
{
  "unacknowledged_requests": 4,
  "in_progress_requests": 11,
  "critical_requests": 3,
  "pending_offers": 6,
  "partially_fulfilled_assignments": 2,
  "disputed_deliveries": 1,
  "resolved_today": 5,
  "requests_by_urgency": { "CRITICAL": 3, "HIGH": 5, "MEDIUM": 8, "LOW": 2 },
  "overdue_requests": [...]
}
```

### 6.2 — Dashboard List Endpoints

| Endpoint | Returns | Filter Options |
|----------|---------|----------------|
| GET /api/v1/dashboard/requests | Paginated requests with counts | status, urgency, facility, created_after |
| GET /api/v1/dashboard/pending-offers | Offers awaiting ICC review | facility, resource_name |
| GET /api/v1/dashboard/disputed-deliveries | RECEIPT_DISPUTED deliveries | assignment_id, facility |
| GET /api/v1/dashboard/assignments | Active assignments by status | status, request_id |

### 6.3 — Audit History Endpoints

| Endpoint | Returns | Filter Options |
|----------|---------|----------------|
| GET /api/v1/audit | Paginated audit_events | entity_type, entity_id, actor_user_id, timestamps |
| GET /api/v1/audit/request/{id} | Full trail for request + children | N/A |

### Phase 6 Done Criteria
- [ ] Dashboard summary returns correct operational counts
- [ ] Overdue requests correctly identified
- [ ] Audit trail covers all lifecycle events
- [ ] Role restriction on ICC-only endpoints
- [ ] Pagination works correctly
- [ ] All tests pass

---

## Phase 7 — Offline PWA & Synchronization Engine

**Objective:** Full Progressive Web App with Service Worker and IndexedDB sync engine. EDITH works without internet.

### 7.1 — PWA Shell

| Task | Acceptance |
|------|------------|
| index.html (app shell) | Loads instantly from SW cache |
| offline.html (fallback) | Shown when SW cannot serve |
| manifest.json | PWA installable on mobile |
| css/style.css | Design system: Google Fonts Inter, tokens, layout |
| css/components.css | Cards, badges, buttons, status indicators, banners |

### 7.2 — Core JavaScript Modules

| File | Key Functions |
|------|--------------|
| app.js | boot(), navigate() — entry point |
| router.js | Hash-based SPA routing (#/requests, #/dashboard) |
| auth.js | login(), refreshToken(), logout(), getHeaders() |
| api-client.js | fetch wrapper: get(), post() with retry + error parsing |
| sync-engine.js | enqueue(), processOutbox(), markConflict() |
| connectivity.js | isOnline(), onReconnect(callback) — heartbeat ping |
| db.js | IndexedDB wrapper: put(), get(), getAll(), delete() |

### 7.3 — Page Modules

| Page | Key Features | Roles |
|------|-------------|-------|
| login.js | Login form, token storage, role-based redirect | Public |
| dashboard.js | Summary cards, overdue list, pending offers | ICC |
| requests.js | List + sync badges, create form (offline), detail | All |
| offers.js | Offer list, submit (offline), approve/reject | All (role-filtered) |
| assignments.js | Assignment list, prepare/dispatch controls | All |
| logistics.js | Dispatch form, delivery recording, receipt/dispute | Logistics + Hospital |
| audit.js | Timeline view per request | ICC + restricted |

### 7.4 — Service Worker Caching Strategy

| Resource | Strategy |
|----------|----------|
| HTML, CSS, JS, fonts, icons | Cache-First; update in background |
| GET /api/v1/requests, /facilities | Network-First -> IndexedDB fallback |
| POST / PUT mutations | Network-Only -> outbox on NetworkError |
| /api/v1/health | Network-Only (no cache) |
| Unmatched routes | Serve offline.html |

### 7.5 — Sync Engine FIFO Protocol

| Step | Detail |
|------|--------|
| Connectivity detection | navigator.onLine + 30s heartbeat ping |
| Token validation before sync | Check expiry; call /auth/refresh if needed |
| Outbox processing | Sort by created_at ASC; FIFO, not parallel |
| Idempotent submission | POST /api/v1/sync/batch |
| Success | Remove from outbox; update cache; UI badge 🟢 |
| Conflict | Mark FAILED_CONFLICT; display 🔴 + server reason |
| Dependency ordering | Offer not sent until parent request has server ID |

### 7.6 — Phase 7 Additions (from Architecture Comparison)

| Addition | Implementation |
|----------|---------------|
| GET /api/v1/sync/pull?after={timestamp} | Return records updated after cursor for user scope |
| sync_log table | Server-side log of sync operation outcomes |
| Cache clearing on logout | auth.js logout() clears auth_vault + prompts for cached_entities |

### 7.7 — UI Connectivity Contract

| State | Banner | Color | Entity Badge |
|-------|--------|-------|-------------|
| Online + Synced | Central Synchronized | Green | 🟢 Server Confirmed |
| Offline | Offline — Changes Saved Locally | Amber | 🟡 Queued Locally |
| Syncing | Sending X operations... | Blue | 🔄 Syncing Now |
| Conflict | 1 item needs attention | Red | 🔴 Sync Rejected |

### Phase 7 Done Criteria
- [ ] PWA installable on mobile (manifest + SW)
- [ ] Static shell loads < 1.5s without network
- [ ] All forms functional offline
- [ ] Outbox processes FIFO on reconnect
- [ ] Connectivity banner accurately reflects state
- [ ] Per-entity sync badges work correctly
- [ ] ICC actions locked on un-synced entities
- [ ] Token refresh transparent during sync
- [ ] Sync conflicts shown with server explanation
- [ ] GET /sync/pull returns incremental delta
- [ ] Logout clears auth vault
- [ ] All tests pass

---

## Phase 8 — Testing, Deployment & Demo

**Objective:** Validate complete end-to-end system. Produce deployable artifacts. Prepare demonstration.

### 8.1 — Integration Test Suite

| Suite | Scenarios |
|-------|-----------|
| test_full_workflow.py | Hospital A requests 20 O2 -> B offers 12 -> C offers 8 -> ICC approves -> dispatch -> partial 10 -> dispute -> resolve -> second 10 -> ICC confirms resolution |
| test_concurrency.py | Two coordinators race to over-allocate; exactly one succeeds |
| test_offline_sync.py | Offline create -> sync -> server record; sync conflict scenario |
| test_permissions.py | Every role on every endpoint it should NOT access |
| test_idempotency.py | All mutable endpoints with same client_id twice; no duplicates |
| test_partial_fulfillment.py | Partial delivery does not close request |
| test_audit_trail.py | Complete lifecycle in audit_events |

### 8.2 — Demo Data Script

| Script | Creates |
|--------|---------|
| scripts/demo_seed.py | 1 Command Centre + 3 hospitals + 2 logistics operators; 5 requests at various stages; 3 offers; 2 deliveries (one disputed) |

### 8.3 — Deployment Artifacts

| Artifact | Description |
|----------|-------------|
| docker-compose.prod.yml | Production Compose: no DB port exposure, resource limits |
| backend/Dockerfile | Production-optimized: no dev dependencies |
| frontend/ | Static files ready for CDN (GitHub Pages / Netlify) |
| scripts/backup.sh | pg_dump daily snapshot script |
| README.md | Setup, migration, seed, run, test guide |
| .env.example | Complete environment template |

### 8.4 — Demo Sequence

| Demo Step | Validates |
|-----------|-----------|
| Hospital A creates request offline | Offline-first + queue badge |
| Reconnect -> request SUBMITTED on server | Sync engine + idempotency |
| ICC acknowledges | State machine |
| Hospital B offers 12, C offers 8 | Offer creation |
| ICC approves both | Partial allocation + Option A |
| Logistics dispatches, delivers 10 | Partial delivery |
| Dashboard: 10 fulfilled, 10 outstanding | Partial fulfillment display |
| Second delivery: 10 confirmed | Fulfillment completion |
| ICC confirms resolution | Resolution rule |
| Audit trail shows all actors + timestamps | Accountability |

### Phase 8 Done Criteria
- [ ] All integration tests pass (0 failures)
- [ ] Concurrency test passes 10/10 runs
- [ ] Demo script runs end-to-end without errors
- [ ] docker compose up starts cleanly
- [ ] GET /health returns 200 in production config
- [ ] PWA installs on Android Chrome
- [ ] README complete and accurate

---

## Summary Timeline & Effort Matrix

| Phase | Key Output | Estimated Effort | Dependency |
|-------|------------|-----------------|------------|
| Phase 0 | PRD, Architecture, Docs | COMPLETE | None |
| Phase 1 | Docker, DB, FastAPI, Health | 1 session | Phase 0 |
| Phase 2 | JWT, RBAC, Seed data | 1-2 sessions | Phase 1 |
| Phase 3 | Request lifecycle | 1-2 sessions | Phase 2 |
| Phase 4 | Offers, Assignments, Row locks | 2 sessions | Phase 3 |
| Phase 5 | Delivery lifecycle, Disputes | 1-2 sessions | Phase 4 |
| Phase 6 | Dashboard APIs, Audit | 1 session | Phase 5 |
| Phase 7 | Full PWA + Sync Engine | 2-3 sessions | Phase 6 |
| Phase 8 | Integration tests, Deploy, Demo | 1-2 sessions | Phase 7 |

---

## Approval Gates

- [ ] Phase 1 approved — begin Foundation
- [ ] Phase 2 approved — begin Auth
- [ ] Phase 3 approved — begin Requests
- [ ] Phase 4 approved — begin Offers
- [ ] Phase 5 approved — begin Logistics
- [ ] Phase 6 approved — begin Dashboard
- [ ] Phase 7 approved — begin PWA
- [ ] Phase 8 approved — begin Testing & Deployment
