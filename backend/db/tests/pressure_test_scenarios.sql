-- pressure_test_scenarios.sql
-- Run after 0001_cpq_core_schema.sql.
-- This script validates that the schema can represent requested commercial patterns.

BEGIN;

-- -------------------------------------------------------------------
-- Shared setup
-- -------------------------------------------------------------------

WITH t AS (
  INSERT INTO tenants (name, default_currency, timezone)
  VALUES ('ACME Cyber', 'USD', 'America/New_York')
  RETURNING id
), u AS (
  INSERT INTO users (tenant_id, email, full_name)
  SELECT id, 'admin@acme.test', 'ACME Admin' FROM t
  RETURNING id, tenant_id
)
SELECT 1;

-- -------------------------------------------------------------------
-- Company 1: Cybersecurity portfolio
-- -------------------------------------------------------------------

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Cyber'
), pb AS (
  INSERT INTO price_books (tenant_id, name, currency, status, valid_from)
  SELECT tenant_id, 'FY26 Standard', 'USD', 'ACTIVE', DATE '2026-01-01' FROM tenant
  RETURNING id, tenant_id
), rc AS (
  INSERT INTO rate_cards (tenant_id, name, currency)
  SELECT tenant_id, 'Services Rate Card 2026', 'USD' FROM tenant
  RETURNING id, tenant_id
)
INSERT INTO rate_card_entries (tenant_id, rate_card_id, role_name, delivery_type, unit, rate_per_unit)
SELECT tenant_id, id, 'Architect', 'ONSITE', 'HOUR', 250 FROM rc
UNION ALL
SELECT tenant_id, id, 'Analyst', 'OFFSHORE', 'HOUR', 90 FROM rc;

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Cyber'
)
INSERT INTO commercial_items (tenant_id, item_code, name, item_type, versionable, metadata_json)
SELECT tenant_id, 'PLATFORM_CORE', 'Platform Core', 'LICENSED_SOFTWARE', TRUE, '{"license_metric":"PER_USER"}'::jsonb FROM tenant
UNION ALL
SELECT tenant_id, 'MOD_THREAT', 'Threat Detection Module', 'LICENSED_SOFTWARE', TRUE, '{}'::jsonb FROM tenant
UNION ALL
SELECT tenant_id, 'MOD_COMPLIANCE', 'Compliance Module', 'LICENSED_SOFTWARE', TRUE, '{}'::jsonb FROM tenant
UNION ALL
SELECT tenant_id, 'BUNDLE_ENTERPRISE', 'Enterprise Security Suite', 'BUNDLE', FALSE, '{}'::jsonb FROM tenant
UNION ALL
SELECT tenant_id, 'SUPPORT_200H', 'Enterprise Support 200H', 'SUPPORT_PACKAGE', FALSE,
       '{"included_hours":200,"overage_rate":"RATE_CARD_LINK","term":"ANNUAL"}'::jsonb FROM tenant
UNION ALL
SELECT tenant_id, 'REPORT_X', 'Threat Landscape Report', 'DATA_PRODUCT', FALSE, '{}'::jsonb FROM tenant
UNION ALL
SELECT tenant_id, 'SERVICES_PS', 'Professional Services', 'SERVICE', FALSE, '{}'::jsonb FROM tenant
UNION ALL
SELECT tenant_id, 'HW_SENSOR', 'Edge Security Sensor', 'HARDWARE', FALSE, '{}'::jsonb FROM tenant
UNION ALL
SELECT tenant_id, 'TOKEN_POOL', 'Detection Tokens', 'TOKEN', FALSE,
       '{"unit":"token","expiry_policy":"12_MONTHS","min_commitment":1000}'::jsonb FROM tenant;

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Cyber'
), ids AS (
  SELECT
    MAX(CASE WHEN item_code='BUNDLE_ENTERPRISE' THEN id END) AS bundle_id,
    MAX(CASE WHEN item_code='PLATFORM_CORE' THEN id END) AS core_id,
    MAX(CASE WHEN item_code='MOD_THREAT' THEN id END) AS threat_id,
    MAX(CASE WHEN item_code='MOD_COMPLIANCE' THEN id END) AS compliance_id,
    tenant_id
  FROM commercial_items
  WHERE tenant_id = (SELECT tenant_id FROM tenant)
)
INSERT INTO bundle_items (tenant_id, bundle_item_id, child_item_id, inclusion_type, qty_rule_json, override_price_allowed, sort_order)
SELECT tenant_id, bundle_id, core_id, 'REQUIRED', '{"fixed_qty":1}'::jsonb, FALSE, 10 FROM ids
UNION ALL
SELECT tenant_id, bundle_id, threat_id, 'OPTIONAL', '{"min_qty":0,"max_qty":1}'::jsonb, TRUE, 20 FROM ids
UNION ALL
SELECT tenant_id, bundle_id, compliance_id, 'OPTIONAL', '{"min_qty":0,"max_qty":1}'::jsonb, TRUE, 30 FROM ids;

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Cyber'
), pb AS (
  SELECT id AS price_book_id, tenant_id
  FROM price_books
  WHERE tenant_id = (SELECT tenant_id FROM tenant)
    AND name = 'FY26 Standard'
), rc AS (
  SELECT id AS rate_card_id, tenant_id
  FROM rate_cards
  WHERE tenant_id = (SELECT tenant_id FROM tenant)
    AND name = 'Services Rate Card 2026'
)
INSERT INTO price_book_entries (
  tenant_id, price_book_id, commercial_item_id, pricing_model, base_price, min_qty, max_qty, metadata_json, ratecard_id
)
SELECT pb.tenant_id, pb.price_book_id, ci.id,
       CASE ci.item_code
         WHEN 'PLATFORM_CORE' THEN 'PER_USER'
         WHEN 'MOD_THREAT' THEN 'PER_USER'
         WHEN 'MOD_COMPLIANCE' THEN 'PER_USER'
         WHEN 'SUPPORT_200H' THEN 'FIXED_PRICE'
         WHEN 'REPORT_X' THEN 'FIXED_PRICE'
         WHEN 'SERVICES_PS' THEN 'RATE_CARD'
         WHEN 'HW_SENSOR' THEN 'PER_UNIT'
         WHEN 'TOKEN_POOL' THEN 'USAGE_BASED'
         ELSE 'CUSTOM'
       END,
       CASE ci.item_code
         WHEN 'PLATFORM_CORE' THEN 99
         WHEN 'MOD_THREAT' THEN 30
         WHEN 'MOD_COMPLIANCE' THEN 25
         WHEN 'SUPPORT_200H' THEN 50000
         WHEN 'REPORT_X' THEN 5000
         WHEN 'HW_SENSOR' THEN 1200
         ELSE NULL
       END,
       CASE WHEN ci.item_code='TOKEN_POOL' THEN 1000 ELSE NULL END,
       NULL,
       CASE WHEN ci.item_code='TOKEN_POOL'
            THEN '{"unit":"token","consumption_rules":"event_driven"}'::jsonb
            ELSE '{}'::jsonb
       END,
       CASE WHEN ci.item_code='SERVICES_PS' THEN rc.rate_card_id ELSE NULL END
FROM commercial_items ci
JOIN pb ON pb.tenant_id = ci.tenant_id
LEFT JOIN rc ON rc.tenant_id = ci.tenant_id
WHERE ci.tenant_id = (SELECT tenant_id FROM tenant)
  AND ci.item_code <> 'BUNDLE_ENTERPRISE';

WITH pbe AS (
  SELECT pbe.id, pbe.tenant_id
  FROM price_book_entries pbe
  JOIN commercial_items ci ON ci.id = pbe.commercial_item_id
  WHERE ci.item_code = 'PLATFORM_CORE'
)
INSERT INTO pricing_components (tenant_id, price_book_entry_id, component_type, value_type, value, sequence_no)
SELECT tenant_id, id, 'BASE_PRICE', 'ABSOLUTE', 99, 10 FROM pbe
UNION ALL
SELECT tenant_id, id, 'DISCOUNT', 'PERCENT', 10, 20 FROM pbe
UNION ALL
SELECT tenant_id, id, 'MARGIN_ADJUSTMENT', 'FORMULA', NULL, 30 FROM pbe;

UPDATE pricing_components
SET formula_expression = 'max(unit_price, cost * 1.15)'
WHERE value_type = 'FORMULA';

-- -------------------------------------------------------------------
-- Company 2: Service company with POC
-- -------------------------------------------------------------------

WITH t AS (
  INSERT INTO tenants (name, default_currency, timezone)
  VALUES ('BrightOps Services', 'USD', 'America/Chicago')
  RETURNING id
), pb AS (
  INSERT INTO price_books (tenant_id, name, currency, status, valid_from)
  SELECT id, 'FY26 Services', 'USD', 'ACTIVE', DATE '2026-01-01' FROM t
  RETURNING id, tenant_id
), ci AS (
  INSERT INTO commercial_items (tenant_id, item_code, name, item_type, metadata_json)
  SELECT tenant_id, 'POC_CLOUD_SEC', 'Cloud Security POC', 'POC',
         '{"scope_constraints":"2 workloads","conversion_credit_policy":"50%","time_bound":true}'::jsonb
  FROM pb
  RETURNING id, tenant_id
)
INSERT INTO price_book_entries (tenant_id, price_book_id, commercial_item_id, pricing_model, base_price)
SELECT pb.tenant_id, pb.id, ci.id, 'CUSTOM', 15000
FROM pb
JOIN ci ON ci.tenant_id = pb.tenant_id;

-- -------------------------------------------------------------------
-- Company 3: Product company simple mapping
-- -------------------------------------------------------------------

WITH t AS (
  INSERT INTO tenants (name, default_currency, timezone)
  VALUES ('ProdTech Systems', 'USD', 'America/Los_Angeles')
  RETURNING id
), pb AS (
  INSERT INTO price_books (tenant_id, name, currency, status)
  SELECT id, 'Standard', 'USD', 'ACTIVE' FROM t
  RETURNING id, tenant_id
), ci AS (
  INSERT INTO commercial_items (tenant_id, item_code, name, item_type)
  SELECT tenant_id, 'SW_STD', 'Software Standard', 'LICENSED_SOFTWARE' FROM pb
  UNION ALL
  SELECT tenant_id, 'HW_STD', 'Device Standard', 'HARDWARE' FROM pb
  RETURNING id, tenant_id, item_code
)
INSERT INTO price_book_entries (tenant_id, price_book_id, commercial_item_id, pricing_model, base_price)
SELECT ci.tenant_id, pb.id, ci.id,
       CASE WHEN ci.item_code = 'SW_STD' THEN 'FIXED_PRICE' ELSE 'PER_UNIT' END,
       CASE WHEN ci.item_code = 'SW_STD' THEN 3000 ELSE 800 END
FROM ci JOIN pb ON pb.tenant_id = ci.tenant_id;

-- -------------------------------------------------------------------
-- Assertions
-- -------------------------------------------------------------------

-- A1: every tenant can represent all expected commercial item patterns.
SELECT tenant_id, COUNT(DISTINCT item_type) AS item_type_count
FROM commercial_items
GROUP BY tenant_id
ORDER BY item_type_count DESC;

-- A2: bundle contains both required and optional child logic.
SELECT ci.item_code AS bundle_code, bi.inclusion_type, COUNT(*)
FROM bundle_items bi
JOIN commercial_items ci ON ci.id = bi.bundle_item_id
GROUP BY ci.item_code, bi.inclusion_type;

-- A3: service rate-card linkage works.
SELECT pbe.id, pbe.pricing_model, pbe.ratecard_id
FROM price_book_entries pbe
JOIN commercial_items ci ON ci.id = pbe.commercial_item_id
WHERE ci.item_code = 'SERVICES_PS';

-- A4: token usage metadata retained.
SELECT item_code, metadata_json
FROM commercial_items
WHERE item_type = 'TOKEN';

-- A5: no schema fork was required to represent POC.
SELECT item_code, item_type
FROM commercial_items
WHERE item_type = 'POC';

ROLLBACK;
