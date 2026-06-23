# Multi-Tenant SaaS Backend

A FastAPI-based SaaS backend demonstrating tenant isolation, JWT auth,
role-based access control, Redis-backed per-tenant rate limits, and
real-time usage-based billing.

## Core project pillars

- Tenant isolation + auth
- Rate limiting by tenant and pricing tier
- Usage-based billing with monthly limits and overage tracking

## Tenant isolation strategy

This project uses **PostgreSQL Row-Level Security (RLS)** rather than
application-side `WHERE tenant_id = ...` filtering.

### Why RLS?

- RLS enforces tenant boundaries inside PostgreSQL itself.
- A forgotten filter in application code cannot expose another tenant's data.
- The database enforces the security guarantee consistently for all
  queries in a session.

### Implementation details

- `src.db.connection.get_tenant_db` sets the Postgres session config
  variable `app.current_tenant` for each request.
- Authenticated routes use `auth_middleware` to verify JWTs and populate
  `request.state.tenant_id`, `user_id`, and `user_role`.
- Login uses a dedicated low-privilege login role (`app_login_role`) so
  tenant-agnostic authentication can occur without weakening RLS policies.

## Authentication and RBAC

- JWTs include `tenant_id`, `sub` (user_id), and `role`.
- `auth_middleware` validates tokens and stores tenant context in request state.
- `require_role([...])` is used for business authorization, e.g. only
  `admin` users may delete orders or view billing summary.
- Supported roles: `admin`, `member`, `viewer`.

## Rate limiting

This backend enforces **per-tenant** rate limiting using Redis and a
sliding-window pattern.

### How rate limiting works

- Each tenant has a Redis sorted set keyed by `ratelimit:{tenant_id}`.
- The middleware removes all timestamps older than the 60-second window,
  counts the remaining requests, then records the current request.
- If the current count exceeds the plan-specific limit, the request is
  rejected with `429 Too Many Requests`.

### Pricing tier limits

Configured in `src.config.settings`:

- `free`: 60 requests / 60 seconds
- `pro`: 600 requests / 60 seconds
- `enterprise`: 6000 requests / 60 seconds

The middleware also caches tenant plan data in Redis for 5 minutes to
avoid repeated database lookups on every request.

## Usage-based billing

This project tracks API usage in real time and computes billing summary
for the current billing period.

### What is tracked

- Each request is logged in the `api_usage` table with `tenant_id`,
  `endpoint`, `status_code`, and timestamp.
- Usage is recorded asynchronously so request latency remains low.
- Both successful and rejected requests are logged, which is important
  for accurate usage and overage accounting.

### Billing model

- Monthly plan limits are separate from per-minute rate limits.
- Plan tiers in `src.config.settings`:
  - `free`: 10,000 requests/month, no overage allowed
  - `pro`: 500,000 requests/month, $0.50 per 1000 overage requests
  - `enterprise`: 10,000,000 requests/month, $0.20 per 1000 overage requests
- The usage summary endpoint reports current period totals, remaining
  quota, overage usage, overage charge estimate, and endpoint breakdown.

## Key routes

- `POST /auth/login` — authenticate and receive a JWT.
- `GET /orders` — list tenant-scoped orders.
- `POST /orders` — create a new order for the current tenant.
- `DELETE /orders/{order_id}` — admin-only order deletion.
- `GET /usage` — current tenant usage summary.
- `GET /usage/summary` — admin-only billing summary with plan comparison.
- `GET /health` — health check.

## Database model highlights

- `tenants` store tenant identity and plan (`free`, `pro`, `enterprise`).
- `users` are tied to a tenant and have a role.
- `orders` are tenant-scoped and linked to a user.
- `api_usage` stores request-level usage events for billing and metrics.

## Setup

1. Create the Postgres database:

```bash
createdb saas_db
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:

```bash
set DATABASE_URL=postgresql+asyncpg://app_user:password123@localhost:5432/saas_db
set JWT_SECRET=<your-own-random-secret>
```

4. Load the database schema:

```bash
psql saas_db < db/schema.sql
```

5. Run the app:

```bash
uvicorn main:app --reload
```

## Notes

- The README assumes PostgreSQL is configured with the required RLS
  policies and `app_login_role` as defined in `db/schema.sql`.
- The login route is intentionally separated from tenant-scoped DB access
  to preserve the security model.
- Rate limiting and billing are intentionally distinct concerns: rate
  limiting controls burst traffic, billing tracks monthly consumption.
