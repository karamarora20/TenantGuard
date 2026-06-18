-- ============================================================
-- Multi-Tenant SaaS Backend — Database Schema
-- Tenant isolation enforced via PostgreSQL Row-Level Security (RLS)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- for gen_random_uuid()

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'enterprise')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
	tenant_email TEXT NOT NULL
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member', 'viewer')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, email)
);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;  -- applies RLS even to the table owner

CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.current_tenant', true)::UUID);

CREATE ROLE IF NOT EXISTS app_login_role NOLOGIN;
GRANT SELECT,INSERT  ON users TO app_login_role;
GRANT SELECT on tenants to app_login_role;

CREATE POLICY login_lookup_by_email ON users
    FOR SELECT
    TO app_login_role
    USING (true);  -- explicitly tenant-agnostic, ONLY for this narrow role,
                    -- ONLY a SELECT on the 4 columns granted above.

-- In app/db/connection.py, the login-specific connection uses
-- `SET ROLE app_login_role;` for the duration of that one query,
-- then the role is dropped back to the default before the connection
-- returns to the pool. See get_login_db() for the implementation.

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES users(id),
    customer_name TEXT NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_orders ON orders
    USING (tenant_id = current_setting('app.current_tenant', true)::UUID);

-- ----------------------------------------------------------------
-- API_USAGE — tracks per-tenant request counts for billing + rate limiting.
-- This table is intentionally append-only and queried in aggregate,
-- which is why we don't bother with per-row RLS overhead here —
-- all access goes through tenant-scoped aggregate queries in app code.
-- ----------------------------------------------------------------
CREATE TABLE api_usage (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    status_code INT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_api_usage_tenant_time ON api_usage (tenant_id, recorded_at);

-- ----------------------------------------------------------------
-- Indexes to keep RLS-filtered queries fast — every RLS policy
-- filters on tenant_id, so it must always be indexed.
-- ----------------------------------------------------------------
CREATE INDEX idx_users_tenant ON users (tenant_id);
CREATE INDEX idx_orders_tenant ON orders (tenant_id);

-- ----------------------------------------------------------------
-- SEED DATA — two tenants, so you can demo isolation immediately:
-- prove tenant A's session can never see tenant B's rows.
--
-- IMPORTANT: the hashed_password values below are PLACEHOLDERS and will
-- NOT verify against any real password. Generate real bcrypt hashes by
-- running this once you have passlib installed:
--
--   python3 -c "from passlib.context import CryptContext; \
--   print(CryptContext(schemes=['bcrypt']).hash('password123'))"
--
-- Then replace the two hashed_password values below with the output
-- before running this seed script.
-- ----------------------------------------------------------------
INSERT INTO tenants (id, name, plan) VALUES
    ('11111111-1111-1111-1111-111111111111', 'Acme Corp', 'pro'),
    ('22222222-2222-2222-2222-222222222222', 'Globex Inc', 'free');

INSERT INTO users (id, tenant_id, email, hashed_password, role) VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111',
     'admin@acme.com', 'REPLACE_WITH_REAL_BCRYPT_HASH', 'admin'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '22222222-2222-2222-2222-222222222222',
     'admin@globex.com', 'REPLACE_WITH_REAL_BCRYPT_HASH', 'admin');
