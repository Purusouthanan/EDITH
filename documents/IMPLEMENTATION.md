# EDITH — Implementation Guide
## Task-Level Developer Reference for All Phases

**Document Version:** 1.0.0
**Status:** Ready for Execution
**Last Updated:** October 2026
**Companion Documents:** PRD.md · SYSTEM_ARCHITECTURE.md · DEVELOPMENT_PHASES.md

---

## 1. Prerequisites and Environment Setup

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| Docker Desktop | Latest | PostgreSQL container + backend container |
| Python | 3.12+ | Backend runtime |
| pip | Latest | Python package manager |
| Git | Latest | Version control |
| VS Code or PyCharm | Latest | IDE |
| Chrome or Edge | Latest | PWA testing |
| curl or Postman | Any | API testing |

### One-Time Project Setup

```bash
git clone <repo-url>
cd EDITH
cp .env.example .env
# Edit .env with actual values

docker compose up -d

cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

alembic upgrade head
uvicorn app.main:app --reload --port 8000

curl http://localhost:8000/api/v1/health
# Expected: {"status":"ok","database":"connected","version":"1.0.0"}
```

---

## 2. Environment Variables Reference

```ini
DATABASE_URL=postgresql+psycopg://edith_user:your_password@localhost:5432/edith_db
SECRET_KEY=your-32-char-minimum-random-string-here
ACCESS_TOKEN_TTL_MINUTES=60
REFRESH_TOKEN_TTL_HOURS=24
ENVIRONMENT=development
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:5500
POSTGRES_DB=edith_db
POSTGRES_USER=edith_user
POSTGRES_PASSWORD=your_password
```

Generate a secure SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 3. Project File Structure

```
EDITH/
|-- PRD.md
|-- SYSTEM_ARCHITECTURE.md
|-- DEVELOPMENT_PHASES.md
|-- IMPLEMENTATION.md
|-- docker-compose.yml
|-- docker-compose.prod.yml
|-- .env.example
|-- .gitignore
|-- README.md
|
|-- backend/
|   |-- Dockerfile
|   |-- requirements.txt
|   |-- alembic.ini
|   |-- alembic/
|   |   |-- env.py
|   |   `-- versions/
|   |       |-- 001_initial_empty.py
|   |       |-- 002_add_facilities_users.py
|   |       |-- 003_add_emergency_requests.py
|   |       |-- 004_add_offers_assignments.py
|   |       |-- 005_add_deliveries.py
|   |       |-- 006_add_audit_events.py
|   |       `-- 007_add_sync_log.py
|   |
|   |-- app/
|   |   |-- main.py
|   |   |-- core/
|   |   |   |-- config.py
|   |   |   |-- security.py
|   |   |   `-- dependencies.py
|   |   |-- db/
|   |   |   |-- session.py
|   |   |   `-- base.py
|   |   `-- modules/
|   |       |-- auth/     (router.py, service.py, schemas.py)
|   |       |-- facilities/ (router.py, models.py, service.py, schemas.py)
|   |       |-- requests/   (router.py, models.py, service.py, schemas.py)
|   |       |-- offers/     (router.py, models.py, service.py, schemas.py)
|   |       |-- assignments/(router.py, models.py, service.py, schemas.py)
|   |       |-- logistics/  (router.py, models.py, service.py, schemas.py)
|   |       |-- sync/       (router.py, models.py, service.py)
|   |       |-- dashboard/  (router.py, service.py)
|   |       `-- audit/      (router.py, models.py, service.py)
|   |
|   |-- scripts/
|   |   |-- seed.py
|   |   |-- demo_seed.py
|   |   `-- backup.sh
|   |
|   `-- tests/
|       |-- conftest.py
|       |-- test_health.py
|       |-- test_auth.py
|       |-- test_requests.py
|       |-- test_offers.py
|       |-- test_assignments.py
|       |-- test_logistics.py
|       |-- test_dashboard.py
|       |-- test_sync.py
|       |-- test_full_workflow.py
|       |-- test_concurrency.py
|       `-- test_idempotency.py
|
`-- frontend/
    |-- index.html
    |-- offline.html
    |-- manifest.json
    |-- service-worker.js
    |-- css/
    |   |-- style.css
    |   `-- components.css
    `-- js/
        |-- app.js
        |-- router.js
        |-- auth.js
        |-- api-client.js
        |-- sync-engine.js
        |-- connectivity.js
        |-- db.js
        `-- pages/
            |-- login.js
            |-- dashboard.js
            |-- requests.js
            |-- offers.js
            |-- assignments.js
            |-- logistics.js
            `-- audit.js
```

---

## 4. Backend Implementation Patterns

### 4.1 Base Model Pattern

```python
# backend/app/db/base.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class UUIDPKMixin:
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

class TimestampMixin:
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
```

### 4.2 Database Session

```python
# backend/app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
```

### 4.3 RBAC Dependency Pattern

```python
# backend/app/core/dependencies.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_token

bearer = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db=Depends(get_db)
):
    payload = decode_token(credentials.credentials)  # Raises 401 if invalid
    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(401, "User inactive or not found")
    return user

def require_role(*allowed_roles: str):
    async def dep(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(403, {
                "code": "INSUFFICIENT_PERMISSIONS",
                "message": f"Role '{current_user.role}' not authorized."
            })
        return current_user
    return dep

def require_facility_ownership(user, facility_id: str):
    """Call inside service layer for write operations."""
    if str(user.facility_id) != str(facility_id):
        raise HTTPException(403, {
            "code": "FACILITY_ACCESS_DENIED",
            "message": "You can only act on your own facility's records."
        })
```

### 4.4 Idempotency Pattern (All Mutable Endpoints)

```python
# Pattern used in every create service function

async def create_request(db, data, current_user):
    # Check if already processed
    existing = (await db.execute(
        select(EmergencyRequest).where(EmergencyRequest.client_id == data.client_id)
    )).scalar_one_or_none()

    if existing:
        return existing  # Idempotent: return same record

    require_facility_ownership(current_user, data.requesting_facility_id)

    new_request = EmergencyRequest(
        client_id=data.client_id,
        requesting_facility_id=data.requesting_facility_id,
        resource_name=data.resource_name,
        unit=data.unit,
        quantity_required=data.quantity_required,
        urgency=data.urgency,
        operational_notes=data.operational_notes,
        created_by_id=current_user.id,
        status="SUBMITTED"
    )
    db.add(new_request)
    await db.flush()
    await log_event(db, "REQUEST", new_request.id, current_user.id, "REQUEST_CREATED", None, "SUBMITTED")
    await db.commit()
    await db.refresh(new_request)
    return new_request
```

### 4.5 Critical Atomic Allocation Transaction

```python
# backend/app/modules/offers/service.py

async def approve_offer(db, offer_id, request_id, qty, coordinator):
    async with db.begin():
        # Acquire row locks in consistent order
        request = (await db.execute(
            select(EmergencyRequest)
            .where(EmergencyRequest.id == request_id)
            .with_for_update()
        )).scalar_one()

        offer = (await db.execute(
            select(VolunteerOffer)
            .where(VolunteerOffer.id == offer_id)
            .with_for_update()
        )).scalar_one()

        # Calculate confirmed delivered
        confirmed = (await db.execute(
            select(func.coalesce(func.sum(Delivery.quantity_received), 0))
            .join(Assignment, Delivery.assignment_id == Assignment.id)
            .where(Assignment.request_id == request_id)
            .where(Delivery.status.in_(["RECEIPT_CONFIRMED", "DISPUTE_RESOLVED"]))
        )).scalar()

        # Calculate active committed
        committed = (await db.execute(
            select(func.coalesce(func.sum(Assignment.assigned_quantity), 0))
            .where(Assignment.request_id == request_id)
            .where(Assignment.status.notin_(["CANCELLED", "EXCEPTION"]))
        )).scalar()

        remaining = request.quantity_required - confirmed - committed
        if qty > remaining:
            raise HTTPException(409, {
                "code": "OVER_ALLOCATION_PROHIBITED",
                "message": f"Cannot assign {qty}. Only {remaining} remaining.",
                "details": {"remaining": remaining, "requested": qty}
            })

        available = offer.quantity_offered - offer.quantity_allocated
        if qty > available:
            raise HTTPException(409, {
                "code": "OFFER_CAPACITY_EXCEEDED",
                "message": f"Offer only has {available} unallocated units."
            })

        # Create assignment
        assignment = Assignment(
            request_id=request_id, offer_id=offer_id,
            assigned_quantity=qty, status="APPROVED",
            approved_by_id=coordinator.id
        )
        db.add(assignment)

        offer.quantity_allocated += qty
        offer.status = "FULLY_APPROVED" if offer.quantity_allocated == offer.quantity_offered else "PARTIALLY_APPROVED"

        if request.status == "ACKNOWLEDGED":
            request.status = "IN_PROGRESS"

        await db.flush()
        await log_event(db, "ASSIGNMENT", assignment.id, coordinator.id, "ASSIGNMENT_CREATED", None, "APPROVED")
        await log_event(db, "OFFER", offer_id, coordinator.id, "OFFER_APPROVED", "PENDING_REVIEW", offer.status)

    await db.refresh(assignment)
    return assignment
```

### 4.6 Audit Event Logger

```python
# backend/app/modules/audit/service.py
# Must ALWAYS be called inside an active transaction

async def log_event(db, entity_type, entity_id, actor_user_id, action,
                    previous_state, new_state, payload_diff=None):
    event = AuditEvent(
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        action=action,
        previous_state=previous_state,
        new_state=new_state,
        payload_diff=payload_diff
    )
    db.add(event)
    # No commit — inherits parent transaction
```

### 4.7 Standard Response Pattern

```python
def ok(data, message="Operation completed successfully.", status_code=200):
    return JSONResponse({"success": True, "data": data, "message": message}, status_code=status_code)

def created(data, message="Created successfully."):
    return ok(data, message, status_code=201)

def fail(code, message, details=None, status_code=400):
    raise HTTPException(
        status_code=status_code,
        detail={"success": False, "error": {"code": code, "message": message, "details": details}}
    )
```

---

## 5. Alembic Migration Workflow

```bash
# Create migration after model changes
alembic revision --autogenerate -m "add_deliveries_table"

# ALWAYS review generated file before applying
# Apply migration
alembic upgrade head

# Roll back last migration
alembic downgrade -1

# Check current version
alembic current

# View history
alembic history --verbose
```

---

## 6. Testing Guide

### 6.1 Test Configuration

```python
# backend/tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.db.session import get_db
from app.db.base import Base

TEST_DATABASE_URL = "postgresql+psycopg://edith_user:password@localhost:5432/edith_test"

@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

### 6.2 Running Tests

```bash
# All tests
pytest tests/ -v

# Single phase
pytest tests/test_requests.py -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Concurrency tests
pytest tests/test_concurrency.py -v --timeout=30

# Failed tests only
pytest tests/ --lf
```

### 6.3 Critical Concurrency Test

```python
# tests/test_concurrency.py
import asyncio
import pytest

@pytest.mark.asyncio
async def test_concurrent_over_allocation(client, icc_headers, seeded_data):
    """Two coordinators race to approve; exactly one succeeds."""
    results = []

    async def approve(offer_id):
        r = await client.post(
            f"/api/v1/offers/{offer_id}/approve",
            json={"quantity_to_assign": 8},
            headers=icc_headers
        )
        results.append(r.status_code)

    await asyncio.gather(
        approve(seeded_data["offer_1_id"]),
        approve(seeded_data["offer_2_id"]),
        return_exceptions=True
    )

    assert results.count(201) == 1, "Exactly one must succeed"
    assert results.count(409) == 1, "Exactly one must be rejected"
```

---

## 7. Frontend Implementation Patterns

### 7.1 API Client with Offline Support

```javascript
// frontend/js/api-client.js
const API_BASE = '/api/v1';

async function request(method, endpoint, body = null, retries = 2) {
    const { access_token } = await getSession();
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            ...(access_token ? {'Authorization': `Bearer ${access_token}`} : {})
        },
        ...(body ? {body: JSON.stringify(body)} : {})
    };

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        if (!response.ok) {
            const err = await response.json();
            throw {status: response.status, ...err};
        }
        return await response.json();
    } catch (error) {
        if (!navigator.onLine) throw {offline: true};
        if (error.status === 401 && retries > 0) {
            if (await refreshAccessToken()) return request(method, endpoint, body, retries - 1);
        }
        throw error;
    }
}

export const api = {
    get: (e) => request('GET', e),
    post: (e, b) => request('POST', e, b),
};
```

### 7.2 Offline Form Submission Pattern

```javascript
async function submitWithOfflineSupport(endpoint, payload) {
    const clientId = crypto.randomUUID();
    const body = {client_id: clientId, ...payload};

    if (navigator.onLine) {
        try {
            const result = await api.post(endpoint, body);
            return {synced: true, data: result.data};
        } catch (err) {
            if (err.offline) {
                return enqueue(clientId, endpoint, 'POST', body);
            }
            throw err;
        }
    }
    return enqueue(clientId, endpoint, 'POST', body);
}

async function enqueue(clientId, endpoint, method, payload) {
    await db.put('outbox', {
        client_id: clientId,
        endpoint: `/api/v1${endpoint}`,
        method,
        payload,
        created_at: new Date().toISOString(),
        retry_count: 0,
        sync_status: 'QUEUED'
    });
    return {synced: false, local: true, client_id: clientId};
}
```

### 7.3 Sync Engine

```javascript
// frontend/js/sync-engine.js
async function processOutbox() {
    if (!navigator.onLine) return;
    if (!await ensureValidToken()) return;

    const items = (await db.getAll('outbox'))
        .filter(i => i.sync_status === 'QUEUED')
        .sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

    if (!items.length) return;

    updateBanner('syncing', `Sending ${items.length} items...`);

    for (const item of items) {
        try {
            const result = await api.post('/sync/batch', [item]);
            const record = result.data[item.client_id];
            await db.delete('outbox', item.client_id);
            await db.put('cached_entities', {
                id: record.id, entity_type: getType(item.endpoint),
                data: record, cached_at: new Date().toISOString()
            });
            updateEntityBadge(item.client_id, 'confirmed');
        } catch (err) {
            if (err.status === 409 || err.status === 422) {
                await db.put('outbox', {...item, sync_status: 'FAILED_CONFLICT',
                    conflict_reason: err.error?.message});
                updateEntityBadge(item.client_id, 'conflict');
            } else {
                await db.put('outbox', {...item, sync_status: 'QUEUED',
                    retry_count: item.retry_count + 1});
            }
        }
    }
    updateBanner('online');
}
```

---

## 8. Deployment Guide

### 8.1 Development Startup

```bash
# Start database
docker compose up -d

# Activate virtualenv and start backend
cd backend
venv\Scripts\activate  # Windows
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Serve frontend (separate terminal)
cd frontend
python -m http.server 5500
# Visit http://127.0.0.1:5500
```

### 8.2 Production Deployment Checklist

```
Pre-deployment:
  [ ] All tests passing
  [ ] .env.production configured with real secrets
  [ ] SECRET_KEY is 32+ random chars
  [ ] ENVIRONMENT=production
  [ ] ALLOWED_ORIGINS set to production domain

Database:
  [ ] PostgreSQL 16 running
  [ ] alembic upgrade head run
  [ ] seed.py run for initial users

Backend:
  [ ] docker compose -f docker-compose.prod.yml up -d
  [ ] GET /api/v1/health returns 200
  [ ] Reverse proxy (Nginx/Caddy) configured with TLS

Frontend:
  [ ] Deployed to CDN/GitHub Pages/Netlify
  [ ] API_BASE points to production URL
  [ ] Service Worker registered
  [ ] PWA manifest valid

Post-deployment:
  [ ] Login works with seeded credentials
  [ ] Full workflow test passes
  [ ] Offline mode works on mobile
```

### 8.3 Backup Script

```bash
#!/bin/bash
# scripts/backup.sh
BACKUP_DIR="/backups/edith"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
pg_dump -U edith_user -d edith_db --format=custom --file="$BACKUP_DIR/edith_$TIMESTAMP.dump"
find "$BACKUP_DIR" -name "*.dump" -mtime +7 -delete
echo "Backup: $BACKUP_DIR/edith_$TIMESTAMP.dump"
```

---

## 9. API Quick Reference

```
AUTH:
  POST /api/v1/auth/login        { username, password }
  POST /api/v1/auth/refresh      { refresh_token }

REQUESTS:
  POST   /api/v1/requests                    [HOSPITAL_USER]
  GET    /api/v1/requests?status=&urgency=   [ALL]
  GET    /api/v1/requests/{id}               [ALL]
  POST   /api/v1/requests/{id}/acknowledge   [ICC]
  POST   /api/v1/requests/{id}/cancel        [HOSPITAL_USER, ICC]
  POST   /api/v1/requests/{id}/resolve       [ICC]

OFFERS:
  POST   /api/v1/offers                      [HOSPITAL_USER]
  GET    /api/v1/offers?status=&request_id=  [ALL]
  POST   /api/v1/offers/{id}/approve         [ICC]
  POST   /api/v1/offers/{id}/reject          [ICC]
  POST   /api/v1/offers/{id}/withdraw        [HOSPITAL_USER]

ASSIGNMENTS:
  GET    /api/v1/assignments?request_id=     [ALL]
  GET    /api/v1/assignments/{id}            [ALL]
  POST   /api/v1/assignments/{id}/prepare    [LOGISTICS, HOSPITAL_USER]
  POST   /api/v1/assignments/{id}/dispatch   [LOGISTICS, ICC]
  POST   /api/v1/assignments/{id}/cancel     [ICC]
  POST   /api/v1/assignments/{id}/exception  [LOGISTICS, ICC]

DELIVERIES:
  POST   /api/v1/deliveries                      [LOGISTICS]
  GET    /api/v1/deliveries/{id}                 [ALL]
  POST   /api/v1/deliveries/{id}/record          [LOGISTICS]
  POST   /api/v1/deliveries/{id}/confirm         [HOSPITAL_USER (recipient)]
  POST   /api/v1/deliveries/{id}/dispute         [HOSPITAL_USER (recipient)]
  POST   /api/v1/deliveries/{id}/resolve-dispute [ICC]

DASHBOARD (ICC only):
  GET    /api/v1/dashboard/summary
  GET    /api/v1/dashboard/requests
  GET    /api/v1/dashboard/pending-offers
  GET    /api/v1/dashboard/disputed-deliveries

AUDIT:
  GET    /api/v1/audit?entity_type=&entity_id=
  GET    /api/v1/audit/request/{id}

SYNC:
  POST   /api/v1/sync/batch
  GET    /api/v1/sync/pull?after={timestamp}

HEALTH:
  GET    /api/v1/health
```

---

## 10. Error Codes Reference

| Code | HTTP | Meaning |
|------|------|---------|
| OVER_ALLOCATION_PROHIBITED | 409 | Approved qty exceeds remaining required qty |
| OFFER_CAPACITY_EXCEEDED | 409 | Approved qty exceeds unallocated offer balance |
| INVALID_STATE_TRANSITION | 409 | Entity not in required state for this operation |
| FACILITY_ACCESS_DENIED | 403 | User cannot act on another facility entity |
| INSUFFICIENT_PERMISSIONS | 403 | Role not authorized for this endpoint |
| INSUFFICIENT_CONFIRMED_DELIVERY | 409 | Confirmed qty < required — cannot resolve |
| ACTIVE_ASSIGNMENTS_EXIST | 409 | Cannot cancel request with active assignments |
| RESOURCE_NOT_FOUND | 404 | Entity with given ID does not exist |
| DUPLICATE_CLIENT_ID | 200 | client_id already processed — returning existing |

---

## 11. State Machine Quick Reference

### Request
```
SUBMITTED -> ACKNOWLEDGED (ICC only)
SUBMITTED -> CANCELLED    (Requestor or ICC; no active assignments)
ACKNOWLEDGED -> IN_PROGRESS (auto on first offer approval)
ACKNOWLEDGED -> CANCELLED   (Requestor or ICC)
IN_PROGRESS -> RESOLUTION_CONFIRMED (ICC; confirmed qty >= required)
IN_PROGRESS -> CANCELLED             (ICC; exception)
```

### Offer
```
PENDING_REVIEW -> FULLY_APPROVED     (ICC; full qty allocated)
PENDING_REVIEW -> PARTIALLY_APPROVED (ICC; partial qty allocated)
PENDING_REVIEW -> REJECTED           (ICC)
PENDING_REVIEW -> WITHDRAWN          (Donor; zero allocated)
PARTIALLY_APPROVED -> FULLY_APPROVED (ICC; remaining allocated)
PARTIALLY_APPROVED -> WITHDRAWN      (Donor; withdraws unallocated)
```

### Assignment
```
APPROVED -> PREPARING             (Logistics or Donor)
APPROVED -> CANCELLED             (ICC)
PREPARING -> DISPATCHED           (Logistics)
PREPARING -> CANCELLED            (ICC)
DISPATCHED -> PARTIALLY_FULFILLED (partial receipt confirmed)
DISPATCHED -> FULFILLED           (full receipt confirmed)
DISPATCHED -> EXCEPTION           (transit failure)
PARTIALLY_FULFILLED -> FULFILLED  (remaining confirmed)
PARTIALLY_FULFILLED -> EXCEPTION  (remaining lost)
```

### Delivery
```
DISPATCHED -> DELIVERED_RECORDED  (Driver logs drop-off)
DELIVERED_RECORDED -> RECEIPT_CONFIRMED (Recipient verifies)
DELIVERED_RECORDED -> RECEIPT_DISPUTED  (Recipient reports discrepancy)
RECEIPT_DISPUTED -> DISPUTE_RESOLVED    (ICC sets authoritative qty)
```

---

## 12. Development Rules

1. Every service mutation must write an audit event in the same transaction
2. No service function commits without the audit log — they are atomic
3. client_id is always provided by the client — never generated on the server
4. Facility ownership verified in the service layer, not just the router
5. State transition validation lives in the service layer only
6. Terminal states (CANCELLED, RESOLUTION_CONFIRMED, FULFILLED) cannot be re-transitioned
7. Disputed or unconfirmed deliveries never count toward fulfillment
8. Auto-closure of requests is prohibited — ICC must confirm manually

### Git Branch Convention
```
main           <- production-ready only
develop        <- integration
phase/1-foundation
phase/2-auth
phase/3-requests
phase/4-offers
phase/5-logistics
phase/6-dashboard
phase/7-pwa
phase/8-testing
```