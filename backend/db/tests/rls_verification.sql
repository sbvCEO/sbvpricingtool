-- rls_verification.sql
-- Validate tenant isolation behavior after running 0001 + 0002 migrations.

BEGIN;

-- Seed two tenants and tenant-scoped rows.
WITH t1 AS (
  INSERT INTO tenants (name, default_currency, timezone)
  VALUES ('RLS Tenant A', 'USD', 'UTC')
  RETURNING id
), t2 AS (
  INSERT INTO tenants (name, default_currency, timezone)
  VALUES ('RLS Tenant B', 'USD', 'UTC')
  RETURNING id
)
INSERT INTO commercial_items (tenant_id, item_code, name, item_type)
SELECT id, 'A-ITEM-1', 'Tenant A Item', 'SERVICE' FROM t1
UNION ALL
SELECT id, 'B-ITEM-1', 'Tenant B Item', 'SERVICE' FROM t2;

-- As tenant A, only A rows should be visible.
SELECT app_set_tenant((SELECT id FROM tenants WHERE name='RLS Tenant A'));
SELECT COUNT(*) AS tenant_a_visible_items FROM commercial_items;

-- As tenant B, only B rows should be visible.
SELECT app_set_tenant((SELECT id FROM tenants WHERE name='RLS Tenant B'));
SELECT COUNT(*) AS tenant_b_visible_items FROM commercial_items;

-- As tenant A, insert row with tenant A should succeed.
SELECT app_set_tenant((SELECT id FROM tenants WHERE name='RLS Tenant A'));
INSERT INTO commercial_items (tenant_id, item_code, name, item_type)
SELECT id, 'A-ITEM-2', 'Tenant A Item 2', 'SERVICE'
FROM tenants WHERE name='RLS Tenant A';

-- As tenant A, insert row for tenant B should fail under WITH CHECK policy.
-- Uncomment to validate enforcement behavior:
-- INSERT INTO commercial_items (tenant_id, item_code, name, item_type)
-- SELECT id, 'B-ITEM-BAD', 'Should Fail', 'SERVICE'
-- FROM tenants WHERE name='RLS Tenant B';

ROLLBACK;
