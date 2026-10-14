# System Architecture Document
# EDITH: Disaster-Response Healthcare Coordination Platform

**Document Version:** 1.0.0  
**Status:** Approved — Architecture Baseline  
**Last Updated:** October 2026  
**Author Role:** Senior Software Architect & System Designer  
**Companion Document:** [`PRD.md`](./PRD.md)

---

## Table of Contents

1. [Architectural Philosophy & Guiding Principles](#1-architectural-philosophy--guiding-principles)
2. [System Context Diagram (30,000-Foot View)](#2-system-context-diagram-30000-foot-view)
3. [Tier Architecture Overview](#3-tier-architecture-overview)
4. [Client Tier — Progressive Web App (PWA)](#4-client-tier--progressive-web-app-pwa)
5. [API Tier — FastAPI Modular Monolith](#5-api-tier--fastapi-modular-monolith)
6. [Data Tier — PostgreSQL 16 (Dockerized)](#6-data-tier--postgresql-16-dockerized)
7. [Offline Synchronization Architecture](#7-offline-synchronization-architecture)
8. [Security Architecture](#8-security-architecture)
9. [Internal Module Decomposition](#9-internal-module-decomposition)
10. [Directory & Project Structure](#10-directory--project-structure)
11. [Request Lifecycle — Full Data Flow](#11-request-lifecycle--full-data-flow)
12. [Concurrency & Data Integrity Architecture](#12-concurrency--data-integrity-architecture)
13. [Deployment Architecture](#13-deployment-architecture)
14. [Technology Stack Rationale](#14-technology-stack-rationale)
15. [Architecture Decision Records (ADRs)](#15-architecture-decision-records-adrs)
16. [Known Limitations & Future Evolution Paths](#16-known-limitations--future-evolution-paths)

---

## 1. Architectural Philosophy & Guiding Principles

EDITH is deployed in some of the most hostile computing environments that exist: active disaster zones. The architecture must not merely function in normal conditions — it must degrade gracefully, maintain data integrity without network access, and give coordinators a true picture of ground reality even when that reality is incomplete.

Every architectural decision in this document is grounded in five non-negotiable principles:

| Principle | Architectural Expression |
| :--- | :--- |
| **Offline-First Resilience** | Client must be fully functional for read/write operations without any server connection |
| **Truth Integrity** | Locally-queued operations are never presented as server-confirmed facts |
| **Human Authority** | No automated transitions cross business-critical thresholds; humans approve, reject, and confirm |
| **Non-Repudiation** | Every state change is attributed to a specific actor, with immutable records |
| **Deliberate Simplicity** | No infrastructure complexity without a demonstrated operational need |

---

## 2. System Context Diagram (30,000-Foot View)

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                         EDITH SYSTEM CONTEXT                                   ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                 ║
║   ┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐   ║
║   │   HOSPITAL /     │       │   INCIDENT CMD   │       │    LOGISTICS     │   ║
║   │   RELIEF CAMP    │       │   CENTRE (ICC)   │       │    OPERATOR      │   ║
║   │  Field Personnel │       │  Coordinators    │       │  Drivers / Fleet │   ║
║   └────────┬─────────┘       └────────┬─────────┘       └────────┬─────────┘   ║
║            │                          │                           │             ║
║    HTTPS / Offline Cache     HTTPS (reliable)           HTTPS / Offline Cache  ║
║            │                          │                           │             ║
║   ╔════════▼══════════════════════════▼═══════════════════════════▼══════════╗  ║
║   ║                    EDITH PWA (Browser — All Devices)                    ║  ║
║   ║        Vanilla HTML5 + CSS + JS  |  Service Worker  |  IndexedDB        ║  ║
║   ╚═══════════════════════════════════════════════════════════════════════════╝  ║
║                                       │                                         ║
║                               HTTPS REST API                                    ║
║                          /api/v1/  (Versioned)                                  ║
║                                       │                                         ║
║   ╔═══════════════════════════════════▼═══════════════════════════════════════╗  ║
║   ║                  EDITH Backend (FastAPI — Modular Monolith)              ║  ║
║   ║   Auth │ Facilities │ Requests │ Offers │ Assignments │ Logistics │ Sync ║  ║
║   ╚═══════════════════════════════════╦═══════════════════════════════════════╝  ║
║                                       ║ SQLAlchemy 2.0 (Psycopg3)               ║
║   ╔═══════════════════════════════════▼═══════════════════════════════════════╗  ║
║   ║          PostgreSQL 16 (Docker)  — Authoritative Truth Store            ║  ║
║   ║   Transactional | Row Locks | Constraints | Append-Only Audit Log       ║  ║
║   ╚═══════════════════════════════════════════════════════════════════════════╝  ║
║                                                                                 ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

### External Actors & Their Interaction Mode

| Actor | Primary Interface | Offline Capability | Trust Level |
| :--- | :--- | :--- | :--- |
| Hospital / Camp User | PWA (mobile, tablet, laptop) | Full offline drafting + read cache | Facility-scoped |
| ICC Coordinator | PWA (desktop preferred) | Partial (read cache, limited write) | Zone-wide authority |
| Logistics Operator | PWA (mobile) | Full offline delivery recording | Assignment-scoped |
| System Administrator | Direct DB / API (not PWA) | None (admin always online) | Platform-level |

---

## 3. Tier Architecture Overview

EDITH operates as a **three-tier architecture** across a clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TIER 1 — CLIENT (Presentation)                       │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                  PWA Shell (HTML5 + CSS + JS)                        │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │  │
│  │  │  Page Renderer   │  │  API Client     │  │  Sync Engine (JS)   │  │  │
│  │  │  (DOM Updates)   │  │  (fetch + retry)│  │  (Outbox Manager)   │  │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │   Service Worker                │  IndexedDB                         │  │
│  │   · Static asset caching        │  · outbox          (mutations)     │  │
│  │   · Offline fallback routing    │  · cached_entities (read cache)    │  │
│  │   · Background sync trigger     │  · auth_vault      (session)       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                              │  HTTPS  │
                              │ /api/v1 │
┌─────────────────────────────────────────────────────────────────────────────┐
│                       TIER 2 — APPLICATION (Logic)                          │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                 FastAPI Application (Uvicorn)                        │  │
│  │                                                                      │  │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐           │  │
│  │  │  auth/    │ │facilities/│ │ requests/ │ │  offers/  │           │  │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘           │  │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐           │  │
│  │  │assignments│ │ logistics/│ │   sync/   │ │  audit/   │           │  │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘           │  │
│  │                                                                      │  │
│  │  ┌──────────────────────┐  ┌──────────────────────┐                │  │
│  │  │  RBAC Middleware     │  │  Idempotency Guard   │                │  │
│  │  │  (Dependency Inject) │  │  (client_id dedup)   │                │  │
│  │  └──────────────────────┘  └──────────────────────┘                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                         │  SQLAlchemy 2.0 + Psycopg3  │
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TIER 3 — DATA (Persistence)                        │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     PostgreSQL 16 (Docker)                          │  │
│  │                                                                      │  │
│  │   Tables: facilities, users, emergency_requests, volunteer_offers   │  │
│  │           assignments, deliveries, audit_events                     │  │
│  │                                                                      │  │
│  │   Mechanisms: CHECK Constraints, FK Constraints, UQ on client_id   │  │
│  │               SELECT ... FOR UPDATE (row locks), Indexes            │  │
│  │               Append-Only audit_events (no UPDATE/DELETE)           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     Alembic (Schema Migrations)                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Client Tier — Progressive Web App (PWA)

### 4.1 PWA Architecture Internals

```
Browser Tab (EDITH PWA)
│
├── index.html ── App Shell (static)
│   ├── <link> → style.css (cached by SW)
│   └── <script> → app.js (entry point)
│       ├── router.js          → hash-based SPA routing
│       ├── auth.js            → JWT lifecycle, token refresh
│       ├── api-client.js      → fetch wrapper (retry, timeout, error norm.)
│       ├── sync-engine.js     → IndexedDB outbox queue management
│       ├── connectivity.js    → navigator.onLine + heartbeat ping
│       └── pages/
│           ├── login.js
│           ├── dashboard.js   → ICC Command Center View
│           ├── requests.js    → Request list, creation, detail
│           ├── offers.js      → Offer submission, review, withdrawal
│           ├── assignments.js → Assignment tracking
│           ├── logistics.js   → Dispatch, delivery recording
│           └── audit.js       → Audit event history
│
└── service-worker.js (registered on install)
    ├── Cache Strategy: Cache-First for static assets (HTML, CSS, JS)
    ├── Cache Strategy: Network-First with IndexedDB fallback for API reads
    ├── Background Sync: Triggers outbox flush on connectivity restore
    └── Offline Fallback: Serves offline.html when all strategies fail
```

### 4.2 IndexedDB Object Store Schema

```
Database: edith_local  (version 1)
│
├── Store: outbox
│   ├── keyPath: client_id (UUIDv4)
│   ├── index: sync_status (for filtering QUEUED items)
│   └── Record Shape:
│       {
│         client_id:   "550e8400-e29b-41d4-a716-446655440000",
│         endpoint:    "/api/v1/requests",
│         method:      "POST",
│         payload:     { resource_name: "Oxygen", quantity_required: 20, ... },
│         created_at:  "2026-10-12T13:20:00Z",
│         retry_count: 0,
│         sync_status: "QUEUED" | "SYNCING" | "FAILED_CONFLICT"
│       }
│
├── Store: cached_entities
│   ├── keyPath: id (server UUID)
│   ├── index: entity_type (for filtering by REQUEST / OFFER etc)
│   └── Record Shape:
│       {
│         id:           "server-uuid",
│         entity_type:  "REQUEST",
│         data:         { ... full server entity object ... },
│         cached_at:    "2026-10-12T14:00:00Z"
│       }
│
└── Store: auth_vault
    ├── keyPath: key (singleton "session")
    └── Record Shape:
        {
          key:           "session",
          user_id:       "user-uuid",
          username:      "dr.ravi",
          full_name:     "Dr. Ravi Kumar",
          role:          "HOSPITAL_USER",
          facility_id:   "facility-uuid",
          access_token:  "eyJhbGci...",
          refresh_token: "eyJhbGci...",
          access_expires_at:  "2026-10-12T15:00:00Z",
          refresh_expires_at: "2026-10-13T13:00:00Z"
        }
```

### 4.3 Offline Visual Contract (UI States)

The UI must unambiguously communicate the synchronization status of every entity shown to the user:

```
┌────────────────────────────────────────────────────────────────────┐
│ CONNECTIVITY BANNER (Global — top of every page)                  │
├────────────────────────────────────────────────────────────────────┤
│  🟢  Online  |  Synchronized with Central Server                  │
│  🟡  Offline |  Changes Saved Locally — Will Sync on Reconnect    │
│  🔄  Syncing |  Sending 3 queued operations to server...          │
└────────────────────────────────────────────────────────────────────┘

Per-Entity Tags on Cards / List Items:
┌────────────────────────────────────────────────────────────────────┐
│ 🟡 [QUEUED LOCALLY]    Not yet on server. Server actions disabled. │
│ 🟢 [SERVER CONFIRMED]  Synchronized and visible to all users.      │
│ 🔴 [SYNC REJECTED]     Server rejected. Review required.           │
│ 🔄 [SYNCING NOW]       Upload in progress.                         │
└────────────────────────────────────────────────────────────────────┘

Locked Actions Rule:
· Any action that depends on another entity's server state (e.g.,
  Coordinator approving an offer against a request) is DISABLED
  if the parent entity is in QUEUED LOCALLY state.
```

### 4.4 Service Worker Caching Strategy

| Resource Category | Caching Strategy | Rationale |
| :--- | :--- | :--- |
| HTML, CSS, JS, Fonts, Icons | Cache-First (Cache Storage) | Static shell must load instantly offline |
| `GET /api/v1/requests` | Network-First → IndexedDB fallback | Fresh data preferred; stale when offline |
| `GET /api/v1/facilities` | Cache-First with background refresh | Rarely changes; need offline access |
| `POST / PUT mutations` | Network-only → IndexedDB outbox on failure | Never serve stale mutation responses |
| `/api/v1/health` | Network-only (no cache) | Liveness check must reflect real server status |

---

## 5. API Tier — FastAPI Modular Monolith

### 5.1 Application Layering (Clean Architecture)

Each domain module follows a consistent three-layer internal structure:

```
backend/app/
│
├── main.py                     ← FastAPI app factory, router inclusion
├── core/
│   ├── config.py               ← Pydantic Settings (env-driven config)
│   ├── security.py             ← JWT creation, verification, hashing
│   └── dependencies.py         ← get_current_user(), require_role() deps
│
├── db/
│   ├── session.py              ← Engine, SessionLocal, get_db() dep
│   ├── base.py                 ← Declarative Base + UUID/timestamp mixin
│   └── migrations/             ← Alembic migration scripts
│
└── modules/                    ← Business Domain Modules
    ├── auth/
    │   ├── router.py           ← POST /auth/login, POST /auth/refresh
    │   ├── service.py          ← authenticate_user(), create_tokens()
    │   └── schemas.py          ← LoginRequest, TokenResponse
    │
    ├── facilities/
    │   ├── router.py           ← GET /facilities
    │   ├── models.py           ← Facility SQLAlchemy model
    │   ├── service.py          ← Facility CRUD operations
    │   └── schemas.py          ← FacilityOut, FacilityCreate
    │
    ├── requests/
    │   ├── router.py           ← GET/POST /requests, state transition endpoints
    │   ├── models.py           ← EmergencyRequest SQLAlchemy model
    │   ├── service.py          ← Business logic, state machine enforcement
    │   └── schemas.py          ← RequestCreate, RequestOut, AcknowledgeOut
    │
    ├── offers/
    │   ├── router.py
    │   ├── models.py
    │   ├── service.py          ← offer approval with allocation transaction
    │   └── schemas.py
    │
    ├── assignments/
    │   ├── router.py
    │   ├── models.py
    │   ├── service.py          ← quantity invariant enforcement
    │   └── schemas.py
    │
    ├── logistics/
    │   ├── router.py
    │   ├── models.py           ← Delivery SQLAlchemy model
    │   ├── service.py          ← dispatch / receipt / dispute logic
    │   └── schemas.py
    │
    ├── sync/
    │   ├── router.py           ← POST /sync/batch
    │   └── service.py          ← FIFO idempotent batch processor
    │
    └── audit/
        ├── router.py           ← GET /audit
        ├── models.py           ← AuditEvent SQLAlchemy model (append-only)
        └── service.py          ← log_event() helper (called by all services)
```

### 5.2 Request Processing Pipeline

Every incoming API request traverses this pipeline:

```
Incoming HTTP Request
        │
        ▼
┌───────────────────────┐
│ 1. Uvicorn ASGI Layer │  TCP socket handling, HTTP parsing
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ 2. FastAPI Middleware  │  CORS headers, request ID injection,
│    Stack              │  HTTPS enforcement, logging
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ 3. JWT Authentication │  Dependency: get_current_user()
│    Dependency         │  Validates Bearer token, loads user + facility
└───────────┬───────────┘
            │
            ├─── Token invalid / expired → 401 Unauthorized
            │
            ▼
┌───────────────────────┐
│ 4. RBAC Authorization │  Dependency: require_role([...roles])
│    Dependency         │  Validates user.role against endpoint requirements
└───────────┬───────────┘
            │
            ├─── Insufficient role → 403 Forbidden
            │
            ▼
┌───────────────────────┐
│ 5. Pydantic Request   │  Schema validation, type coercion,
│    Schema Validation  │  field constraint checking
└───────────┬───────────┘
            │
            ├─── Validation failure → 422 Unprocessable Entity
            │
            ▼
┌───────────────────────┐
│ 6. Idempotency Guard  │  For POST mutations: check client_id uniqueness
│    (client_id check)  │  If already processed → return existing record
└───────────┬───────────┘
            │
            ├─── Duplicate detected → 200 OK (existing record, no new write)
            │
            ▼
┌───────────────────────┐
│ 7. Domain Service     │  Business logic, state machine transitions,
│    (Module Service)   │  quantity invariant enforcement
└───────────┬───────────┘
            │
            ├─── Business rule violation → 409 Conflict + error code
            │
            ▼
┌───────────────────────┐
│ 8. SQLAlchemy ORM +   │  Database transaction (BEGIN/COMMIT/ROLLBACK)
│    PostgreSQL         │  Row-level locks for critical operations
└───────────┬───────────┘
            │
            ├─── DB error → 500 Internal Server Error
            │
            ▼
┌───────────────────────┐
│ 9. Audit Event Logger │  Append-only audit record written within
│    (within same txn)  │  same transaction for atomicity
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ 10. Pydantic Response │  Serialize ORM object → JSON response schema
│     Schema Serialize  │
└───────────┬───────────┘
            ▼
      HTTP Response (200 / 201 / 4xx / 5xx)
```

### 5.3 Standardized API Response Envelopes

**Success Response**
```json
{
  "success": true,
  "data": { "id": "...", "status": "ACKNOWLEDGED" },
  "message": "Request acknowledged successfully."
}
```

**Error Response**
```json
{
  "success": false,
  "error": {
    "code": "OVER_ALLOCATION_PROHIBITED",
    "message": "Approved quantity (10) exceeds remaining required quantity (6).",
    "details": {
      "quantity_required": 20,
      "already_committed": 14,
      "requested_allocation": 10
    }
  }
}
```

### 5.4 Complete API Endpoint Catalogue

```
/api/v1/
│
├── GET   /health
│
├── POST  /auth/login
├── POST  /auth/refresh
│
├── GET   /facilities
├── POST  /facilities                       [ADMIN]
│
├── GET   /requests
├── POST  /requests                         [HOSPITAL_USER]
├── GET   /requests/{id}
├── POST  /requests/{id}/acknowledge        [ICC_COORDINATOR]
├── POST  /requests/{id}/cancel             [HOSPITAL_USER, ICC_COORDINATOR]
├── POST  /requests/{id}/resolve            [ICC_COORDINATOR]
│
├── GET   /offers
├── POST  /offers                           [HOSPITAL_USER]
├── GET   /offers/{id}
├── POST  /offers/{id}/approve              [ICC_COORDINATOR]
├── POST  /offers/{id}/reject               [ICC_COORDINATOR]
├── POST  /offers/{id}/withdraw             [HOSPITAL_USER]
│
├── GET   /assignments
├── GET   /assignments/{id}
├── POST  /assignments/{id}/prepare         [LOGISTICS_OPERATOR, HOSPITAL_USER]
├── POST  /assignments/{id}/dispatch        [LOGISTICS_OPERATOR, ICC_COORDINATOR]
├── POST  /assignments/{id}/exception       [LOGISTICS_OPERATOR, ICC_COORDINATOR]
├── POST  /assignments/{id}/cancel          [ICC_COORDINATOR]
│
├── GET   /deliveries
├── POST  /deliveries                       [LOGISTICS_OPERATOR]
├── GET   /deliveries/{id}
├── POST  /deliveries/{id}/record           [LOGISTICS_OPERATOR]
├── POST  /deliveries/{id}/confirm          [HOSPITAL_USER]
├── POST  /deliveries/{id}/dispute          [HOSPITAL_USER]
├── POST  /deliveries/{id}/resolve-dispute  [ICC_COORDINATOR]
│
├── POST  /sync/batch
│
└── GET   /audit
```

---

## 6. Data Tier — PostgreSQL 16 (Dockerized)

### 6.1 Entity Relationship Diagram (Full)

```mermaid
erDiagram
    FACILITIES {
        uuid id PK
        varchar name
        varchar facility_type
        numeric latitude
        numeric longitude
        text address
        varchar contact_phone
        boolean is_active
        timestamptz created_at
    }

    USERS {
        uuid id PK
        uuid facility_id FK
        varchar username
        varchar hashed_password
        varchar full_name
        varchar role
        boolean is_active
        timestamptz created_at
    }

    EMERGENCY_REQUESTS {
        uuid id PK
        uuid client_id UK
        uuid requesting_facility_id FK
        varchar resource_name
        varchar unit
        int quantity_required
        varchar urgency
        varchar status
        text operational_notes
        uuid created_by_id FK
        timestamptz created_at
    }

    VOLUNTEER_OFFERS {
        uuid id PK
        uuid client_id UK
        uuid offering_facility_id FK
        uuid target_request_id FK
        varchar resource_name
        int quantity_offered
        int quantity_allocated
        varchar status
        uuid created_by_id FK
        timestamptz created_at
    }

    ASSIGNMENTS {
        uuid id PK
        uuid request_id FK
        uuid offer_id FK
        int assigned_quantity
        varchar status
        uuid approved_by_id FK
        text notes
        timestamptz created_at
    }

    DELIVERIES {
        uuid id PK
        uuid client_id UK
        uuid assignment_id FK
        int quantity_dispatched
        int quantity_received
        varchar status
        text transporter_info
        varchar discrepancy_reason
        text discrepancy_notes
        timestamptz dispatched_at
        timestamptz delivered_at
        timestamptz confirmed_at
        uuid confirmed_by_id FK
    }

    AUDIT_EVENTS {
        uuid id PK
        varchar entity_type
        uuid entity_id
        uuid actor_user_id FK
        varchar action
        varchar previous_state
        varchar new_state
        jsonb payload_diff
        timestamptz created_at
    }

    FACILITIES ||--o{ USERS : "employs"
    FACILITIES ||--o{ EMERGENCY_REQUESTS : "requests (1:N)"
    FACILITIES ||--o{ VOLUNTEER_OFFERS : "offers (1:N)"
    USERS ||--o{ EMERGENCY_REQUESTS : "creates"
    USERS ||--o{ VOLUNTEER_OFFERS : "creates"
    USERS ||--o{ ASSIGNMENTS : "approves"
    USERS ||--o{ DELIVERIES : "confirms"
    USERS ||--o{ AUDIT_EVENTS : "triggers"
    EMERGENCY_REQUESTS ||--o{ ASSIGNMENTS : "fulfilled by (1:N)"
    VOLUNTEER_OFFERS ||--o{ ASSIGNMENTS : "funds (1:N)"
    ASSIGNMENTS ||--o{ DELIVERIES : "shipped via (1:N)"
```

### 6.2 Database Isolation & Locking Strategy

| Operation | Isolation Level | Lock Type |
| :--- | :--- | :--- |
| Offer Approval (critical path) | READ COMMITTED | `SELECT...FOR UPDATE` on `requests` + `offers` rows |
| Standard read queries | READ COMMITTED | None (MVCC snapshot) |
| Delivery confirmation | READ COMMITTED | `SELECT...FOR UPDATE` on `assignments` row |
| Batch sync processing | READ COMMITTED | Per-item row locks acquired in order |
| Audit event writes | Within parent transaction | Inherits parent lock scope |

### 6.3 PostgreSQL Indexes

```sql
CREATE INDEX idx_requests_status          ON emergency_requests(status);
CREATE INDEX idx_requests_urgency         ON emergency_requests(urgency);
CREATE INDEX idx_requests_facility        ON emergency_requests(requesting_facility_id);
CREATE INDEX idx_requests_status_urgency  ON emergency_requests(status, urgency);

CREATE INDEX idx_offers_status            ON volunteer_offers(status);
CREATE INDEX idx_offers_facility          ON volunteer_offers(offering_facility_id);
CREATE INDEX idx_offers_target_request    ON volunteer_offers(target_request_id);

CREATE INDEX idx_assignments_request      ON assignments(request_id);
CREATE INDEX idx_assignments_offer        ON assignments(offer_id);
CREATE INDEX idx_assignments_status       ON assignments(status);

CREATE INDEX idx_deliveries_assignment    ON deliveries(assignment_id);
CREATE INDEX idx_deliveries_status        ON deliveries(status);

CREATE INDEX idx_audit_entity             ON audit_events(entity_type, entity_id);
CREATE INDEX idx_audit_actor              ON audit_events(actor_user_id);
CREATE INDEX idx_audit_time               ON audit_events(created_at DESC);
```

### 6.4 Docker Compose Configuration (Conceptual)

```yaml
# docker-compose.yml (conceptual — implemented in Phase 1)
services:
  postgres:
    image: postgres:16-alpine
    container_name: edith_postgres
    environment:
      POSTGRES_DB:       edith_db
      POSTGRES_USER:     edith_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U edith_user -d edith_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    container_name: edith_backend
    environment:
      DATABASE_URL: postgresql+psycopg://edith_user:${POSTGRES_PASSWORD}@postgres:5432/edith_db
      SECRET_KEY:   ${SECRET_KEY}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

volumes:
  postgres_data:
```

---

## 7. Offline Synchronization Architecture

### 7.1 Full Sync Protocol

```
FIELD DEVICE (Offline)                         SERVER (Online)
│                                              │
│ [User creates Request while offline]         │
│   ├── Generate client_id = UUIDv4()         │
│   ├── Save to IndexedDB outbox               │
│   └── Show UI tag: 🟡 "Queued Locally"      │
│                                              │
│ ············ CONNECTIVITY RESTORED ···· │
│                                              │
│ [Step 1: Liveness Ping]                     │
│   GET /api/v1/health ───────────────────────►│
│   ◄──── 200 OK ────────────────────────────│
│                                              │
│ [Step 2: Token Validation]                  │
│   Check auth_vault.access_expires_at        │
│   ├── Token valid → proceed to Step 3       │
│   └── Token expired?                        │
│       ├── POST /auth/refresh ───────────────►│ Validate refresh token
│       │   ◄──── new access_token ──────────│ Issue new access token
│       └── Refresh also expired?            │
│           └── Prompt user re-login         │
│               (outbox preserved)           │
│                                              │
│ [Step 3: FIFO Outbox Batch Transmission]    │
│   Sort outbox by created_at ASC             │
│   For each item (sync_status = QUEUED):     │
│     Mark as SYNCING                         │
│     POST /api/v1/sync/batch ───────────────►│ Per-item client_id check
│                              ◄─────────────│ Idempotent: existing → return
│                                            │ New: validate + persist
│     On 200: clear outbox item, UI 🟢       │
│     On 409: mark FAILED_CONFLICT, UI 🔴    │
│                                              │
│ [Step 4: Cache Refresh]                     │
│   GET /requests, /assignments → update      │
│   cached_entities → re-render dashboard     │
```

### 7.2 Conflict Resolution Matrix

| Scenario | Resolution |
| :--- | :--- |
| Same `client_id` transmitted twice (network retry) | Server returns existing record; outbox item cleared; no duplicate |
| Offer submitted offline; parent request CANCELLED by ICC | Server returns 409; client marks 🔴 SYNC_REJECTED; user prompted |
| Delivery logged offline; assignment CANCELLED meanwhile | Server returns 409; user prompted to review and discard |
| Two coordinators approve concurrent offers exceeding remaining quota | `SELECT FOR UPDATE` serializes; second coordinator receives 409 |
| Access token expired during offline period | Refresh token used transparently before outbox transmission |

---

## 8. Security Architecture

### 8.1 Authentication Flow — Dual Token Strategy

```
Client                                    Server
  │                                          │
  │  POST /auth/login {username, password} ──►│
  │                                          ├── bcrypt.verify(password, hash)
  │                                          ├── Build access_token  (JWT, 1hr)
  │                                          ├── Build refresh_token (JWT, 24hr)
  │◄── {access_token, refresh_token, user} ──│
  │                                          │
  │  Store in IndexedDB auth_vault           │
  │                                          │
  │  [Token approaching expiry / offline]    │
  │  POST /auth/refresh {refresh_token} ─────►│
  │◄── {access_token (new)} ─────────────────│
  │                                          │
  │  All API calls:                          │
  │  Authorization: Bearer <access_token>    │
```

### 8.2 Backend RBAC Enforcement (FastAPI Dependency Injection)

```python
# Conceptual — implementation in Phase 2

def require_role(*allowed_roles: str):
    """
    FastAPI dependency injected on every protected endpoint.
    UI hiding is cosmetic only — this is the real access control.
    """
    async def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Insufficient role permissions"
            )
        return current_user
    return dependency

# Usage:
@router.post("/requests/{id}/acknowledge")
async def acknowledge_request(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ICC_COORDINATOR"))
):
    ...
```

### 8.3 Facility-Scoped Access Control

```
HOSPITAL_USER write operations — backend enforces ownership:
  ├── Creating a request:     requesting_facility_id == user.facility_id
  ├── Submitting an offer:    offering_facility_id   == user.facility_id
  ├── Confirming receipt:     receiving_facility_id  == user.facility_id
  └── Withdrawing an offer:   offering_facility_id   == user.facility_id

ICC_COORDINATOR: Zone-wide read and write access (no facility restriction)
LOGISTICS_OPERATOR: Scoped to assignments on active delivery routes
```

### 8.4 Security Non-Goals (Out of Scope for v1)

- Patient data encryption at rest (no PHI stored — by design)
- Multi-factor authentication
- End-to-end coordinator messaging encryption
- Device attestation / mobile MDM

---

## 9. Internal Module Decomposition

### 9.1 Module Dependency Graph

```
                   ┌──────────────────────────────────────┐
                   │              auth                    │  ← No internal deps
                   │  provides: get_current_user()        │
                   │           require_role()             │
                   └──────────────────┬───────────────────┘
                                      │
                   ┌──────────────────▼───────────────────┐
                   │            facilities                │  ← Depends: auth
                   │  provides: facility context          │
                   └──────────────────┬───────────────────┘
                                      │
                   ┌──────────────────▼───────────────────┐
                   │             requests                 │  ← Depends: auth, facilities
                   │  provides: request state context     │
                   └──────────────────┬───────────────────┘
                                      │
                   ┌──────────────────▼───────────────────┐
                   │              offers                  │  ← Depends: auth, requests
                   │  triggers: assignment creation       │
                   └──────────────────┬───────────────────┘
                                      │
                   ┌──────────────────▼───────────────────┐
                   │           assignments                │  ← Depends: auth, offers, requests
                   │  enables: delivery creation          │
                   └──────────────────┬───────────────────┘
                                      │
                   ┌──────────────────▼───────────────────┐
                   │             logistics                │  ← Depends: auth, assignments
                   │  (deliveries, receipt, disputes)     │
                   └─────────────┬────────────────────────┘
                                 │
                  ┌──────────────┴─────────────┐
                  │                            │
           ┌──────▼──────┐            ┌────────▼────────┐
           │    sync     │            │      audit      │
           │ (uses all   │            │ (called by ALL  │
           │  modules)   │            │  services via   │
           └─────────────┘            │  log_event())   │
                                      └─────────────────┘
```

### 9.2 Service Layer Responsibilities

| Module | Key Responsibilities | Critical Constraint |
| :--- | :--- | :--- |
| `auth` | Password hashing, JWT lifecycle, refresh rotation | JWTs are stateless; no server-side token DB |
| `facilities` | Facility CRUD, user management | Facilities pre-registered by admin; no self-registration |
| `requests` | State machine for Request lifecycle | All state transitions validated before any DB write |
| `offers` | Offer creation, partial/full approval with row locks | Allocation atomically enforced under `SELECT FOR UPDATE` |
| `assignments` | Created only by offer approval service | No direct client-side assignment creation endpoint |
| `logistics` | Delivery CRUD, receipt, dispute filing | Receipt confirmation triggers assignment fulfillment re-evaluation |
| `sync` | FIFO batch processor, idempotency, conflict reporting | Items processed in FIFO order; not all-or-nothing per item |
| `audit` | Append-only event log writer | Always called inside the parent service transaction |

---

## 10. Directory & Project Structure

```
EDITH/
│
├── PRD.md                              ← Product Requirements
├── SYSTEM_ARCHITECTURE.md             ← This document
├── docker-compose.yml                  ← Service orchestration
├── .env.example                        ← Environment variable template
│
├── backend/                            ← FastAPI Application
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── dependencies.py
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── base.py
│   │   └── modules/
│   │       ├── auth/
│   │       ├── facilities/
│   │       ├── requests/
│   │       ├── offers/
│   │       ├── assignments/
│   │       ├── logistics/
│   │       ├── sync/
│   │       └── audit/
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_health.py
│       ├── test_auth.py
│       ├── test_requests.py
│       ├── test_offers.py
│       ├── test_assignments.py
│       ├── test_logistics.py
│       └── test_sync.py
│
└── frontend/                           ← Vanilla PWA
    ├── index.html
    ├── offline.html
    ├── manifest.json
    ├── service-worker.js
    ├── css/
    │   ├── style.css
    │   └── components.css
    └── js/
        ├── app.js
        ├── router.js
        ├── auth.js
        ├── api-client.js
        ├── sync-engine.js
        ├── connectivity.js
        └── pages/
            ├── login.js
            ├── dashboard.js
            ├── requests.js
            ├── offers.js
            ├── assignments.js
            ├── logistics.js
            └── audit.js
```

---

## 11. Request Lifecycle — Full End-to-End Data Flow

A concrete trace of **20 Oxygen Cylinders** from creation to resolution:

```
[PHASE 1] Request Creation (Hospital User — Offline Device)
─────────────────────────────────────────────────────────────
 User fills form → client_id = "abc-123" generated
 IndexedDB outbox: {endpoint:"/requests", payload:{qty:20}, sync_status:"QUEUED"}
 UI shows: "20 O2 Cylinders — 🟡 Queued Locally"

[PHASE 2] Synchronization
─────────────────────────────────────────────────────────────
 Reconnect → POST /api/v1/requests {client_id:"abc-123", quantity_required:20}
 Server: client_id new → INSERT emergency_requests {status:'SUBMITTED'}
           INSERT audit_events {action:'REQUEST_CREATED'}
 Response: 201 {id:"srv-001", status:"SUBMITTED"}
 Client: outbox cleared → UI: "🟢 SUBMITTED"

[PHASE 3] ICC Acknowledgement
─────────────────────────────────────────────────────────────
 POST /api/v1/requests/srv-001/acknowledge
 Server: BEGIN TX
   SELECT * FROM emergency_requests WHERE id='srv-001' FOR UPDATE
   Validate status == 'SUBMITTED' ✓
   UPDATE status → 'ACKNOWLEDGED'
   INSERT audit_events {prev:'SUBMITTED', new:'ACKNOWLEDGED'}
 COMMIT
 Dashboard: "🟡 ACKNOWLEDGED"

[PHASE 4] Offer Submission (Hospital B)
─────────────────────────────────────────────────────────────
 POST /api/v1/offers {target_request_id:"srv-001", quantity_offered:12}
 Server: INSERT volunteer_offers {status:'PENDING_REVIEW'}
 ICC dashboard: new offer pending review

[PHASE 5] ICC Approval (Concurrency-Critical Section)
─────────────────────────────────────────────────────────────
 POST /api/v1/offers/{offer-id}/approve {quantity_to_assign:12}
 Server: BEGIN TX
   SELECT * FROM emergency_requests WHERE id='srv-001' FOR UPDATE  ← row lock
   SELECT * FROM volunteer_offers WHERE id='offer-id' FOR UPDATE   ← row lock
   remaining = 20 - 0(confirmed) - 0(committed) = 20
   Assert 12 <= 20 ✓ | Assert 12 <= 12(offered) ✓
   INSERT assignments {request_id, offer_id, assigned_quantity:12, status:'APPROVED'}
   UPDATE volunteer_offers SET quantity_allocated=12, status='FULLY_APPROVED'
   UPDATE requests SET status='IN_PROGRESS'
   INSERT audit_events x2
 COMMIT
 [Concurrent second approval of same request: blocked by row lock →
  on unblock: recalculates remaining = 20-12=8 → only 8 can be assigned]

[PHASE 6] Logistics
─────────────────────────────────────────────────────────────
 POST /assignments/{id}/dispatch {vehicle:"TN22-5671", driver:"Arjun K."}
 POST /deliveries {assignment_id, quantity_dispatched:12}
 Delivery status: DISPATCHED

[PHASE 7] Partial Delivery & Dispute
─────────────────────────────────────────────────────────────
 Driver delivers 10 (2 lost in flood)
 POST /deliveries/{id}/record
 POST /deliveries/{id}/dispute {quantity_received:10, reason:"DAMAGED_CARGO"}
 Delivery: RECEIPT_DISPUTED
 Request: remains IN_PROGRESS (10 of 20 confirmed, 10 outstanding)

[PHASE 8] Dispute Resolution + Second Assignment
─────────────────────────────────────────────────────────────
 ICC resolves: 10 confirmed
 Hospital C offers 10 → ICC approves → Logistics dispatches → 10 received
 POST /deliveries/{id2}/confirm {quantity_received:10}

[PHASE 9] Resolution Confirmation
─────────────────────────────────────────────────────────────
 POST /requests/srv-001/resolve
 Server: SUM(RECEIPT_CONFIRMED deliveries) = 10 + 10 = 20 >= 20 ✓
 UPDATE requests SET status='RESOLUTION_CONFIRMED'
 INSERT audit_events {action:'REQUEST_RESOLVED'}
 Dashboard: "20 O2 Cylinders — ✅ RESOLUTION CONFIRMED"
```

---

## 12. Concurrency & Data Integrity Architecture

### 12.1 Over-Allocation Prevention — Concurrent Coordinator Scenario

```
Coordinator A                               Coordinator B
     │                                           │
     │  POST /offers/offer-A/approve {qty:12}    │  POST /offers/offer-B/approve {qty:12}
     │                                           │  (request only needs 20 total)
     │                                           │
     ├─ BEGIN TX ───────────────────────────────┤─ BEGIN TX
     │                                           │
     ├─ SELECT * FROM requests                  │
     │  WHERE id=req FOR UPDATE ← acquires lock │
     │                                           │
     │  [Coordinator B blocks here]             ├─ SELECT * FROM requests
     │  ···waiting···                           │  WHERE id=req FOR UPDATE ← BLOCKED
     │                                           │  ···waiting for A's lock release···
     │  remaining = 20 - 0 = 20                 │
     ├─ INSERT assignment (qty=12) ✓             │
     ├─ COMMIT ────── releases lock ────────────┤─ UNBLOCKED
     │                                           │
     │                                           ├─ remaining = 20 - 12 = 8
     │                                           ├─ 12 > 8 → raises 409 CONFLICT
     │                                           ├─ ROLLBACK
     │                                           │
     │                                     Coordinator B sees:
     │                                     "Only 8 units remaining.
     │                                      Approve up to 8."
```

### 12.2 Quantity Invariant — Server-Side Enforcement Logic

```python
# Conceptual — implemented in Phase 4 offers/service.py

def validate_allocation(db, request_id, offer_id, qty_to_assign):
    """Must run inside BEGIN ... FOR UPDATE transaction."""

    request = db.execute(
        "SELECT quantity_required FROM emergency_requests "
        "WHERE id = :id FOR UPDATE", {"id": request_id}
    ).fetchone()

    confirmed_delivered = db.scalar(
        "SELECT COALESCE(SUM(d.quantity_received), 0) "
        "FROM deliveries d JOIN assignments a ON d.assignment_id = a.id "
        "WHERE a.request_id = :rid "
        "AND d.status IN ('RECEIPT_CONFIRMED', 'DISPUTE_RESOLVED')",
        {"rid": request_id}
    )

    active_committed = db.scalar(
        "SELECT COALESCE(SUM(assigned_quantity), 0) FROM assignments "
        "WHERE request_id = :rid "
        "AND status NOT IN ('CANCELLED', 'EXCEPTION')",
        {"rid": request_id}
    )

    remaining = request.quantity_required - confirmed_delivered - active_committed

    if qty_to_assign > remaining:
        raise BusinessRuleViolation(
            code="OVER_ALLOCATION_PROHIBITED",
            detail={
                "quantity_required":    request.quantity_required,
                "confirmed_delivered":  confirmed_delivered,
                "active_committed":     active_committed,
                "remaining_capacity":   remaining,
                "requested_allocation": qty_to_assign
            }
        )
```

---

## 13. Deployment Architecture

### 13.1 Target Deployment Topology

```
Internet / Disaster Zone Network
          │
          ▼
┌─────────────────────────┐
│  CDN / Static Host      │   GitHub Pages / Netlify / S3 + CloudFront
│  (Frontend PWA)         │   HTML, CSS, JS, SW, Manifest
│  HTTPS (TLS 1.3)        │   Service Worker caches all on first load
└──────────┬──────────────┘
           │ /api/* REST calls
           ▼
┌─────────────────────────┐
│  Reverse Proxy          │   Nginx / Caddy
│  TLS Termination        │   Routes /api/* → FastAPI container
│  Rate Limiting          │   CORS headers, security headers
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  FastAPI Container      │   Uvicorn (2-4 workers)
│  (Docker)               │   Reads config from env / secrets
│  Port 8000 (internal)   │
└──────────┬──────────────┘
           │ SQLAlchemy + Psycopg3
           ▼
┌─────────────────────────┐
│  PostgreSQL 16          │   Docker named volume (persistent)
│  Container              │   Port 5432 — NOT exposed to internet
│  (private network only) │   Daily snapshots via pg_dump
└─────────────────────────┘
```

### 13.2 Environment Configuration

| Variable | Description | Example |
| :--- | :--- | :--- |
| `DATABASE_URL` | Full PostgreSQL connection string | `postgresql+psycopg://edith_user:pass@postgres:5432/edith_db` |
| `SECRET_KEY` | JWT signing key (min 32 chars random) | `openssl rand -hex 32` |
| `ACCESS_TOKEN_TTL_MINUTES` | Access token lifespan | `60` |
| `REFRESH_TOKEN_TTL_HOURS` | Refresh token lifespan | `24` |
| `ALLOWED_ORIGINS` | CORS whitelist | `https://edith.yourdomain.com` |
| `ENVIRONMENT` | Runtime mode | `development` or `production` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

---

## 14. Technology Stack Rationale

| Component | Choice | Rationale |
| :--- | :--- | :--- |
| Frontend Language | Vanilla JS | Zero build toolchain; Service Worker requires native JS; disaster-resilient |
| Frontend Styling | Vanilla CSS | Full control, no version conflicts, loads from SW cache instantly |
| PWA / Offline | Service Worker + IndexedDB | W3C standard, works in all modern browsers without native app |
| Backend Language | Python 3.12 | Fast to develop, readable, strong async support, rich ecosystem |
| Web Framework | FastAPI | Automatic OpenAPI docs, Pydantic-native, async-first, minimal boilerplate |
| ORM | SQLAlchemy 2.0 | Type-safe modern style, `SELECT FOR UPDATE` support, Alembic integration |
| DB Driver | Psycopg3 | Native async support, PostgreSQL-native, faster than psycopg2 for async |
| Migrations | Alembic | Integrates natively with SQLAlchemy; handles production schema versioning |
| Database | PostgreSQL 16 | ACID transactions, row-level locking, JSONB, UUID support, battle-proven |
| Containerization | Docker Compose | Identical dev-to-production environment; single command startup |
| Testing | Pytest + HTTPX | Native async support, in-process test client, fast iteration |

---

## 15. Architecture Decision Records (ADRs)

### ADR-001: Modular Monolith over Microservices
**Decision:** Single FastAPI application with internally modular domain structure.  
**Rationale:** Microservices require service discovery, distributed transactions, and network-based inter-service calls — all of which dramatically increase the failure surface area in a disaster context. A modular monolith is deployed, debugged, and scaled as a single unit. For the expected concurrent user count of a disaster coordination zone, a single well-structured application is more reliable than a distributed one.  
**Future Path:** If EDITH scales to a national multi-zone platform, individual domain modules can be extracted with minimal refactoring due to clean boundary design.

### ADR-002: PostgreSQL Row-Level Locks over Application-Level Locks
**Decision:** `SELECT ... FOR UPDATE` within DB transactions for all allocation checks.  
**Rationale:** Application-level locks (in-memory mutexes) are invalidated when multiple Uvicorn workers run or multiple server instances are deployed. Database-level locks are the only safe serialization mechanism for distributed concurrent writes.  
**Tradeoff:** High-contention approval requests queue at the DB level. Acceptable for the expected coordinator count (2–10 concurrent operations).

### ADR-003: Client-Generated `client_id` for Idempotency
**Decision:** Clients generate UUIDv4 keys for every mutation before network transmission.  
**Rationale:** Network timeouts mean the client cannot know whether a server-side write occurred. A resubmitted `client_id` allows the server to detect and return the existing record without creating duplicates.  
**Constraint:** Requires a `UNIQUE` constraint on `client_id` for every mutable entity table.

### ADR-004: Custom IndexedDB Outbox over Background Sync API
**Decision:** Custom JavaScript outbox manager using IndexedDB rather than the W3C Background Sync API.  
**Rationale:** Background Sync API lacks full cross-browser support (notably Firefox) and provides limited control over ordering, conflict reporting, and visual status management. The custom IndexedDB queue delivers predictable FIFO ordering, granular status tracking, and user-facing conflict notifications across all target browsers.  
**Tradeoff:** More client-side JS code to maintain; offset by full behavioral control.

### ADR-005: Audit Log Inside Application DB in Same Transaction
**Decision:** `audit_events` table in PostgreSQL, written atomically within each service transaction.  
**Rationale:** An external audit store (log stream, separate service) would require two-phase commit or eventual consistency. Writing the audit event in the same DB transaction guarantees atomicity: either the business state change and its audit record both commit, or neither does.  
**Tradeoff:** Audit table grows continuously with business data. Archival or table partitioning can be introduced in a future phase.

---

## 16. Known Limitations & Future Evolution Paths

| Limitation | Current Design | Future Evolution |
| :--- | :--- | :--- |
| No real-time push notifications | Coordinators poll / manually refresh dashboard | Add WebSocket or Server-Sent Events layer for live updates |
| Single-zone deployment | One backend instance serves one disaster zone | Multi-tenancy with zone isolation or regional deployments |
| No optional AI assist | Pure human coordination throughout | Pluggable AI service to flag duplicate requests or summarize load |
| No SMS / extreme offline messaging | Requires internet for server sync | Integration with SMS gateway or LoRa mesh relay |
| Limited horizontal scalability | 2–4 Uvicorn workers | Gunicorn + horizontal scaling (JWT is already stateless) |
| No media attachments | Text operational notes only | Object storage (MinIO/S3) for damage photos, delivery receipts |
| No inventory pre-loading | Facilities volunteer only on demand | Optional voluntary inventory hints (opt-in, never mandatory) |

---

## Document Control

| Field | Value |
| :--- | :--- |
| **Document** | SYSTEM_ARCHITECTURE.md |
| **Companion Document** | PRD.md |
| **Current Phase** | Phase 0 — Complete |
| **Next Gate** | Phase 1 (Foundation) — Awaiting Approval |
| **Review Status** | Ready for team sign-off |
