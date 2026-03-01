-- ACME Inc CPQ simulation seed
-- Creates a complete tenant simulation with catalog, bundles, pricebook, rate card,
-- approval policy, CRM account/contact, and a draft quote for Client A.

BEGIN;

-- 1) Tenant + core users
INSERT INTO tenants (name, default_currency, timezone, plan_tier, status, settings_json)
VALUES (
  'ACME Inc',
  'USD',
  'America/New_York',
  'ENTERPRISE',
  'ACTIVE',
  '{"industry":"SaaS","seed":"acme-simulation"}'::jsonb
)
ON CONFLICT (name) DO UPDATE
SET default_currency = EXCLUDED.default_currency,
    timezone = EXCLUDED.timezone,
    plan_tier = EXCLUDED.plan_tier,
    status = EXCLUDED.status,
    settings_json = tenants.settings_json || EXCLUDED.settings_json;

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
)
INSERT INTO users (tenant_id, email, full_name, status)
SELECT tenant.tenant_id, v.email, v.full_name, 'ACTIVE'
FROM tenant
CROSS JOIN (
  VALUES
    ('admin@acmeinc.com', 'Alex Morgan'),
    ('pricing.ops@acmeinc.com', 'Priya Mehta'),
    ('sales.lead@acmeinc.com', 'Jordan Lee'),
    ('finance.approver@acmeinc.com', 'Maya Brooks'),
    ('cto.office@acmeinc.com', 'Ravi Nair')
) AS v(email, full_name)
ON CONFLICT (tenant_id, email) DO UPDATE
SET full_name = EXCLUDED.full_name,
    status = 'ACTIVE';

-- 2) Catalog: platform, modules, data products, bundles, support, maintenance, services
WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
)
INSERT INTO commercial_items (
  tenant_id, item_code, name, description, item_type, is_active, versionable, metadata_json
)
SELECT
  tenant.tenant_id,
  v.item_code,
  v.name,
  v.description,
  v.item_type,
  TRUE,
  TRUE,
  v.metadata_json
FROM tenant
CROSS JOIN (
  VALUES
    ('ACME-PLT-CORE', 'NimbusOne SaaS Platform', 'Core multi-tenant SaaS control plane.', 'LICENSED_SOFTWARE', '{"edition":"Enterprise"}'::jsonb),

    ('ACME-MOD-THREAT', 'Sentinel Threat Monitor', 'Real-time threat telemetry module.', 'LICENSED_SOFTWARE', '{"family":"module"}'::jsonb),
    ('ACME-MOD-GRC', 'Prism GRC Studio', 'Compliance and governance workflows.', 'LICENSED_SOFTWARE', '{"family":"module"}'::jsonb),
    ('ACME-MOD-IDENT', 'Identity Shield', 'Identity posture and access analytics.', 'LICENSED_SOFTWARE', '{"family":"module"}'::jsonb),
    ('ACME-MOD-AUTO', 'FlowPilot Automation', 'No-code policy automation module.', 'LICENSED_SOFTWARE', '{"family":"module"}'::jsonb),
    ('ACME-MOD-OBS', 'Pulse Observability', 'Ops visibility and SLA insights.', 'LICENSED_SOFTWARE', '{"family":"module"}'::jsonb),

    ('ACME-DATA-01', 'Threat Intel Snapshot', 'Single intelligence report package.', 'DATA_PRODUCT', '{"unit":"report"}'::jsonb),
    ('ACME-DATA-02', 'Industry Benchmark Grid', 'Market benchmark insight package.', 'DATA_PRODUCT', '{"unit":"report"}'::jsonb),
    ('ACME-DATA-03', 'Vulnerability Heatmap Feed', 'Risk heatmap export feed.', 'DATA_PRODUCT', '{"unit":"feed"}'::jsonb),
    ('ACME-DATA-04', 'Executive Risk Brief', 'Board-ready quarterly risk brief.', 'DATA_PRODUCT', '{"unit":"brief"}'::jsonb),
    ('ACME-DATA-05', 'Compliance Delta Digest', 'Regulation change digest.', 'DATA_PRODUCT', '{"unit":"digest"}'::jsonb),
    ('ACME-DATA-06', 'Regional Threat Pulse', 'Regional threat movement summary.', 'DATA_PRODUCT', '{"unit":"report"}'::jsonb),
    ('ACME-DATA-07', 'Cloud Exposure Scan', 'Exposure map of cloud assets.', 'DATA_PRODUCT', '{"unit":"scan"}'::jsonb),
    ('ACME-DATA-08', 'Breach Narrative Pack', 'Incident and breach narrative package.', 'DATA_PRODUCT', '{"unit":"pack"}'::jsonb),
    ('ACME-DATA-09', 'SOC KPI Stream', 'SOC KPI time-series stream.', 'DATA_PRODUCT', '{"unit":"stream"}'::jsonb),
    ('ACME-DATA-10', 'SMB Starter Intelligence', 'Starter intelligence unit.', 'DATA_PRODUCT', '{"unit":"unit"}'::jsonb),

    ('ACME-BND-SECURE', 'SecureOps Bundle', 'Platform + Threat + GRC + Observability.', 'BUNDLE', '{"bundle_tier":"secure"}'::jsonb),
    ('ACME-BND-IDENT', 'IdentityOps Bundle', 'Platform + Identity + Automation.', 'BUNDLE', '{"bundle_tier":"identity"}'::jsonb),
    ('ACME-BND-ENTERPRISE', 'Enterprise Command Bundle', 'Platform + all core modules.', 'BUNDLE', '{"bundle_tier":"enterprise"}'::jsonb),

    ('ACME-SUP-SMALL', 'Enterprise Support Small', '8x5 support with 200 annual hours.', 'SUPPORT_PACKAGE', '{"included_hours":200,"term":"ANNUAL"}'::jsonb),
    ('ACME-SUP-MEDIUM', 'Enterprise Support Medium', '24x5 support with 500 annual hours.', 'SUPPORT_PACKAGE', '{"included_hours":500,"term":"ANNUAL"}'::jsonb),
    ('ACME-SUP-LARGE', 'Enterprise Support Large', '24x7 support with 2000 annual hours.', 'SUPPORT_PACKAGE', '{"included_hours":2000,"term":"ANNUAL"}'::jsonb),

    ('ACME-MAINT-ANNUAL', 'Platform Maintenance Annual', 'Platform maintenance and updates per year.', 'SUBSCRIPTION', '{"billing_cycle":"ANNUAL"}'::jsonb),
    ('ACME-SVC-PRO', 'Professional Services Delivery', 'Delivery services billed on labor rate card.', 'SERVICE', '{"billing_basis":"RATE_CARD"}'::jsonb)
) AS v(item_code, name, description, item_type, metadata_json)
ON CONFLICT (tenant_id, item_code) DO UPDATE
SET name = EXCLUDED.name,
    description = EXCLUDED.description,
    item_type = EXCLUDED.item_type,
    is_active = TRUE,
    versionable = TRUE,
    metadata_json = EXCLUDED.metadata_json;

-- 3) Bundles composition
WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), links AS (
  SELECT * FROM (
    VALUES
      ('ACME-BND-SECURE', 'ACME-PLT-CORE', 'REQUIRED', 1),
      ('ACME-BND-SECURE', 'ACME-MOD-THREAT', 'REQUIRED', 2),
      ('ACME-BND-SECURE', 'ACME-MOD-GRC', 'REQUIRED', 3),
      ('ACME-BND-SECURE', 'ACME-MOD-OBS', 'OPTIONAL', 4),

      ('ACME-BND-IDENT', 'ACME-PLT-CORE', 'REQUIRED', 1),
      ('ACME-BND-IDENT', 'ACME-MOD-IDENT', 'REQUIRED', 2),
      ('ACME-BND-IDENT', 'ACME-MOD-AUTO', 'OPTIONAL', 3),

      ('ACME-BND-ENTERPRISE', 'ACME-PLT-CORE', 'REQUIRED', 1),
      ('ACME-BND-ENTERPRISE', 'ACME-MOD-THREAT', 'REQUIRED', 2),
      ('ACME-BND-ENTERPRISE', 'ACME-MOD-GRC', 'REQUIRED', 3),
      ('ACME-BND-ENTERPRISE', 'ACME-MOD-IDENT', 'REQUIRED', 4),
      ('ACME-BND-ENTERPRISE', 'ACME-MOD-AUTO', 'REQUIRED', 5),
      ('ACME-BND-ENTERPRISE', 'ACME-MOD-OBS', 'REQUIRED', 6)
  ) AS x(bundle_code, child_code, inclusion_type, sort_order)
)
INSERT INTO bundle_items (
  tenant_id, bundle_item_id, child_item_id, inclusion_type, qty_rule_json, override_price_allowed, sort_order
)
SELECT
  t.tenant_id,
  b.id,
  c.id,
  l.inclusion_type,
  '{}'::jsonb,
  TRUE,
  l.sort_order
FROM tenant t
JOIN links l ON TRUE
JOIN commercial_items b ON b.tenant_id = t.tenant_id AND b.item_code = l.bundle_code
JOIN commercial_items c ON c.tenant_id = t.tenant_id AND c.item_code = l.child_code
ON CONFLICT (tenant_id, bundle_item_id, child_item_id) DO UPDATE
SET inclusion_type = EXCLUDED.inclusion_type,
    sort_order = EXCLUDED.sort_order,
    override_price_allowed = EXCLUDED.override_price_allowed;

-- 4) Rate card + 75 role rows (25 each for Functional, Business, Technical)
WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
)
INSERT INTO rate_cards (tenant_id, name, currency, status, metadata_json)
SELECT tenant.tenant_id, 'ACME Professional Services 2026', 'USD', 'ACTIVE', '{"model":"hourly"}'::jsonb
FROM tenant
ON CONFLICT (tenant_id, name, currency) DO UPDATE
SET status = 'ACTIVE',
    metadata_json = EXCLUDED.metadata_json;

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), rate_card AS (
  SELECT rc.id AS rate_card_id, rc.tenant_id
  FROM rate_cards rc
  JOIN tenant t ON t.tenant_id = rc.tenant_id
  WHERE rc.name = 'ACME Professional Services 2026' AND rc.currency = 'USD'
), generated AS (
  SELECT
    tenant_id,
    rate_card_id,
    format('Functional Role %s', lpad(gs::text, 2, '0')) AS role_name,
    CASE WHEN gs % 3 = 0 THEN 'ONSITE' WHEN gs % 3 = 1 THEN 'REMOTE' ELSE 'OFFSHORE' END AS delivery_type,
    'HOUR'::text AS unit,
    (95 + gs * 4)::numeric(18,6) AS rate_per_unit,
    DATE '2026-01-01' AS effective_from
  FROM rate_card, generate_series(1,25) gs

  UNION ALL

  SELECT
    tenant_id,
    rate_card_id,
    format('Business Role %s', lpad(gs::text, 2, '0')),
    CASE WHEN gs % 3 = 0 THEN 'ONSITE' WHEN gs % 3 = 1 THEN 'REMOTE' ELSE 'OFFSHORE' END,
    'HOUR',
    (110 + gs * 5)::numeric(18,6),
    DATE '2026-01-01'
  FROM rate_card, generate_series(1,25) gs

  UNION ALL

  SELECT
    tenant_id,
    rate_card_id,
    format('Technical Role %s', lpad(gs::text, 2, '0')),
    CASE WHEN gs % 3 = 0 THEN 'ONSITE' WHEN gs % 3 = 1 THEN 'REMOTE' ELSE 'OFFSHORE' END,
    'HOUR',
    (125 + gs * 6)::numeric(18,6),
    DATE '2026-01-01'
  FROM rate_card, generate_series(1,25) gs
)
INSERT INTO rate_card_entries (
  tenant_id, rate_card_id, role_name, delivery_type, unit, rate_per_unit, effective_from, metadata_json
)
SELECT
  g.tenant_id,
  g.rate_card_id,
  g.role_name,
  g.delivery_type,
  g.unit,
  g.rate_per_unit,
  g.effective_from,
  '{}'::jsonb
FROM generated g
ON CONFLICT (tenant_id, rate_card_id, role_name, delivery_type, unit, effective_from) DO UPDATE
SET rate_per_unit = EXCLUDED.rate_per_unit;

-- 5) Master price book and entries
WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
)
INSERT INTO price_books (
  tenant_id, name, currency, valid_from, valid_to, status, metadata_json
)
SELECT
  tenant.tenant_id,
  'ACME FY2026 Master',
  'USD',
  DATE '2026-01-01',
  DATE '2026-12-31',
  'ACTIVE',
  '{"market":"GLOBAL","seed":"acme-simulation"}'::jsonb
FROM tenant
ON CONFLICT (tenant_id, name, currency) DO UPDATE
SET valid_from = EXCLUDED.valid_from,
    valid_to = EXCLUDED.valid_to,
    status = 'ACTIVE',
    metadata_json = EXCLUDED.metadata_json;

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), pb AS (
  SELECT p.id AS price_book_id, p.tenant_id
  FROM price_books p
  JOIN tenant t ON t.tenant_id = p.tenant_id
  WHERE p.name = 'ACME FY2026 Master' AND p.currency = 'USD'
), item_codes AS (
  SELECT * FROM (
    VALUES
      ('ACME-PLT-CORE'),
      ('ACME-MOD-THREAT'),('ACME-MOD-GRC'),('ACME-MOD-IDENT'),('ACME-MOD-AUTO'),('ACME-MOD-OBS'),
      ('ACME-DATA-01'),('ACME-DATA-02'),('ACME-DATA-03'),('ACME-DATA-04'),('ACME-DATA-05'),
      ('ACME-DATA-06'),('ACME-DATA-07'),('ACME-DATA-08'),('ACME-DATA-09'),('ACME-DATA-10'),
      ('ACME-BND-SECURE'),('ACME-BND-IDENT'),('ACME-BND-ENTERPRISE'),
      ('ACME-SUP-SMALL'),('ACME-SUP-MEDIUM'),('ACME-SUP-LARGE'),
      ('ACME-MAINT-ANNUAL'),('ACME-SVC-PRO')
  ) AS x(item_code)
)
DELETE FROM price_book_entries pbe
USING pb, commercial_items ci, item_codes ic
WHERE pbe.tenant_id = pb.tenant_id
  AND pbe.price_book_id = pb.price_book_id
  AND ci.id = pbe.commercial_item_id
  AND ci.tenant_id = pb.tenant_id
  AND ci.item_code = ic.item_code;

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), pb AS (
  SELECT p.id AS price_book_id, p.tenant_id
  FROM price_books p
  JOIN tenant t ON t.tenant_id = p.tenant_id
  WHERE p.name = 'ACME FY2026 Master' AND p.currency = 'USD'
), rc AS (
  SELECT r.id AS rate_card_id, r.tenant_id
  FROM rate_cards r
  JOIN tenant t ON t.tenant_id = r.tenant_id
  WHERE r.name = 'ACME Professional Services 2026' AND r.currency = 'USD'
), pricing AS (
  SELECT * FROM (
    VALUES
      ('ACME-PLT-CORE', 'FIXED_PRICE', 120000::numeric, 100000::numeric, 18::numeric),
      ('ACME-MOD-THREAT', 'PER_USER', 480::numeric, 350::numeric, 22::numeric),
      ('ACME-MOD-GRC', 'PER_USER', 390::numeric, 295::numeric, 20::numeric),
      ('ACME-MOD-IDENT', 'PER_USER', 340::numeric, 250::numeric, 20::numeric),
      ('ACME-MOD-AUTO', 'PER_USER', 310::numeric, 225::numeric, 25::numeric),
      ('ACME-MOD-OBS', 'PER_USER', 270::numeric, 190::numeric, 25::numeric),

      ('ACME-DATA-01', 'TIERED', 1250::numeric, 900::numeric, 10::numeric),
      ('ACME-DATA-02', 'TIERED', 1800::numeric, 1300::numeric, 12::numeric),
      ('ACME-DATA-03', 'TIERED', 2200::numeric, 1650::numeric, 10::numeric),
      ('ACME-DATA-04', 'TIERED', 750::numeric, 520::numeric, 10::numeric),
      ('ACME-DATA-05', 'TIERED', 620::numeric, 450::numeric, 10::numeric),
      ('ACME-DATA-06', 'TIERED', 1400::numeric, 980::numeric, 11::numeric),
      ('ACME-DATA-07', 'TIERED', 1650::numeric, 1200::numeric, 12::numeric),
      ('ACME-DATA-08', 'TIERED', 980::numeric, 700::numeric, 10::numeric),
      ('ACME-DATA-09', 'TIERED', 4500::numeric, 3000::numeric, 8::numeric),
      ('ACME-DATA-10', 'TIERED', 50::numeric, 50::numeric, 0::numeric),

      ('ACME-BND-SECURE', 'FIXED_PRICE', 165000::numeric, 140000::numeric, 15::numeric),
      ('ACME-BND-IDENT', 'FIXED_PRICE', 148000::numeric, 126000::numeric, 15::numeric),
      ('ACME-BND-ENTERPRISE', 'FIXED_PRICE', 250000::numeric, 220000::numeric, 12::numeric),

      ('ACME-SUP-SMALL', 'FIXED_PRICE', 15000::numeric, 12000::numeric, 10::numeric),
      ('ACME-SUP-MEDIUM', 'FIXED_PRICE', 45000::numeric, 38000::numeric, 10::numeric),
      ('ACME-SUP-LARGE', 'FIXED_PRICE', 120000::numeric, 98000::numeric, 10::numeric),

      ('ACME-MAINT-ANNUAL', 'FIXED_PRICE', 30000::numeric, 25000::numeric, 15::numeric),
      ('ACME-SVC-PRO', 'RATE_CARD', 250::numeric, 180::numeric, 20::numeric)
  ) AS x(item_code, pricing_model, base_price, min_price, max_discount_pct)
)
INSERT INTO price_book_entries (
  tenant_id,
  price_book_id,
  commercial_item_id,
  pricing_model,
  base_price,
  min_price,
  max_discount_pct,
  ratecard_id,
  metadata_json
)
SELECT
  pb.tenant_id,
  pb.price_book_id,
  ci.id,
  pricing.pricing_model,
  pricing.base_price,
  pricing.min_price,
  pricing.max_discount_pct,
  CASE WHEN pricing.item_code = 'ACME-SVC-PRO' THEN rc.rate_card_id ELSE NULL END,
  CASE
    WHEN ci.item_code LIKE 'ACME-DATA-%' THEN
      jsonb_build_object(
        'unit', 'unit',
        'tiers', jsonb_build_array(
          jsonb_build_object('min', 1, 'max', 9, 'price', pricing.base_price),
          jsonb_build_object('min', 10, 'max', 49, 'price', round(pricing.base_price * 0.9, 2)),
          jsonb_build_object('min', 50, 'max', 99, 'price', round(pricing.base_price * 0.82, 2)),
          jsonb_build_object('min', 100, 'price', round(pricing.base_price * 0.75, 2))
        )
      )
    WHEN ci.item_code = 'ACME-SVC-PRO' THEN
      jsonb_build_object('billing_basis', 'HOUR', 'default_role', 'Technical Role 10')
    ELSE '{}'::jsonb
  END
FROM pricing
JOIN pb ON TRUE
JOIN commercial_items ci ON ci.tenant_id = pb.tenant_id AND ci.item_code = pricing.item_code
LEFT JOIN rc ON rc.tenant_id = pb.tenant_id;

-- 6) Approval policy
WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
)
INSERT INTO approval_policies (
  tenant_id, name, status, conditions_json, route_template_json
)
SELECT
  tenant.tenant_id,
  'ACME Deal Guardrail Policy',
  'ACTIVE',
  '{"min_grand_total":100000,"max_margin_pct":30,"max_discount_pct":22}'::jsonb,
  '{"levels":2,"route":["FINANCE_MANAGER","EXECUTIVE"]}'::jsonb
FROM tenant
ON CONFLICT (tenant_id, name) DO UPDATE
SET status = 'ACTIVE',
    conditions_json = EXCLUDED.conditions_json,
    route_template_json = EXCLUDED.route_template_json;

-- 7) CRM: Client A account/contact + opportunity
WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
)
INSERT INTO customer_accounts (
  tenant_id, account_code, legal_name, display_name, status, account_type, industry, segment, website, metadata_json
)
SELECT
  tenant.tenant_id,
  'CLIENT-A',
  'Client A Holdings LLC',
  'Client A',
  'ACTIVE',
  'CUSTOMER',
  'Financial Services',
  'Enterprise',
  'https://clienta.example.com',
  '{"priority":"strategic"}'::jsonb
FROM tenant
ON CONFLICT (tenant_id, account_code) DO UPDATE
SET legal_name = EXCLUDED.legal_name,
    display_name = EXCLUDED.display_name,
    status = EXCLUDED.status,
    industry = EXCLUDED.industry,
    segment = EXCLUDED.segment,
    website = EXCLUDED.website,
    metadata_json = EXCLUDED.metadata_json;

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), account AS (
  SELECT ca.id AS account_id, ca.tenant_id
  FROM customer_accounts ca
  JOIN tenant t ON t.tenant_id = ca.tenant_id
  WHERE ca.account_code = 'CLIENT-A'
)
INSERT INTO customer_contacts (
  tenant_id, account_id, first_name, last_name, email, phone, title, buying_role, is_primary, is_billing_contact, status
)
SELECT
  account.tenant_id,
  account.account_id,
  'Anita',
  'Khan',
  'anita.khan@clienta.example.com',
  '+1-212-555-0148',
  'Director of Security Programs',
  'Economic Buyer',
  TRUE,
  TRUE,
  'ACTIVE'
FROM account
ON CONFLICT (tenant_id, account_id, email) DO UPDATE
SET first_name = EXCLUDED.first_name,
    last_name = EXCLUDED.last_name,
    phone = EXCLUDED.phone,
    title = EXCLUDED.title,
    buying_role = EXCLUDED.buying_role,
    is_primary = EXCLUDED.is_primary,
    is_billing_contact = EXCLUDED.is_billing_contact,
    status = EXCLUDED.status;

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), account AS (
  SELECT ca.id AS account_id, ca.tenant_id
  FROM customer_accounts ca
  JOIN tenant t ON t.tenant_id = ca.tenant_id
  WHERE ca.account_code = 'CLIENT-A'
)
INSERT INTO opportunities (
  tenant_id, account_id, opportunity_no, name, stage, status, amount, currency, close_date, metadata_json
)
SELECT
  account.tenant_id,
  account.account_id,
  'OPP-CLIENTA-2026-001',
  'Client A Enterprise Platform Expansion',
  'PROPOSAL',
  'OPEN',
  466500,
  'USD',
  DATE '2026-06-30',
  '{"source":"seed-script"}'::jsonb
FROM account
ON CONFLICT (tenant_id, opportunity_no) DO UPDATE
SET name = EXCLUDED.name,
    stage = EXCLUDED.stage,
    status = EXCLUDED.status,
    amount = EXCLUDED.amount,
    currency = EXCLUDED.currency,
    close_date = EXCLUDED.close_date,
    metadata_json = EXCLUDED.metadata_json;

-- 8) Draft quote for Client A
WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), pb AS (
  SELECT p.id AS price_book_id, p.tenant_id
  FROM price_books p
  JOIN tenant t ON t.tenant_id = p.tenant_id
  WHERE p.name = 'ACME FY2026 Master' AND p.currency = 'USD'
), account AS (
  SELECT ca.id AS customer_account_id, ca.tenant_id
  FROM customer_accounts ca
  JOIN tenant t ON t.tenant_id = ca.tenant_id
  WHERE ca.account_code = 'CLIENT-A'
), opp AS (
  SELECT o.id AS opportunity_id, o.tenant_id
  FROM opportunities o
  JOIN tenant t ON t.tenant_id = o.tenant_id
  WHERE o.opportunity_no = 'OPP-CLIENTA-2026-001'
)
INSERT INTO quotes (
  tenant_id, quote_no, customer_external_id, customer_account_id, opportunity_id,
  status, currency, region, price_book_id, valid_until,
  subtotal, discount_total, surcharge_total, tax_total, grand_total, margin_pct, revision_no
)
SELECT
  pb.tenant_id,
  'Q-ACME-CLIENTA-0001',
  'CLIENT-A',
  account.customer_account_id,
  opp.opportunity_id,
  'DRAFT',
  'USD',
  'US',
  pb.price_book_id,
  DATE '2026-07-31',
  0, 0, 0, 0, 0, 0, 1
FROM pb
JOIN account ON account.tenant_id = pb.tenant_id
JOIN opp ON opp.tenant_id = pb.tenant_id
ON CONFLICT (tenant_id, quote_no) DO UPDATE
SET customer_external_id = EXCLUDED.customer_external_id,
    customer_account_id = EXCLUDED.customer_account_id,
    opportunity_id = EXCLUDED.opportunity_id,
    status = 'DRAFT',
    currency = EXCLUDED.currency,
    region = EXCLUDED.region,
    price_book_id = EXCLUDED.price_book_id,
    valid_until = EXCLUDED.valid_until;

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), quote_ref AS (
  SELECT q.id AS quote_id, q.tenant_id
  FROM quotes q
  JOIN tenant t ON t.tenant_id = q.tenant_id
  WHERE q.quote_no = 'Q-ACME-CLIENTA-0001'
)
DELETE FROM quote_line_items qli
USING quote_ref qr
WHERE qli.tenant_id = qr.tenant_id
  AND qli.quote_id = qr.quote_id;

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), quote_ref AS (
  SELECT q.id AS quote_id, q.tenant_id
  FROM quotes q
  JOIN tenant t ON t.tenant_id = q.tenant_id
  WHERE q.quote_no = 'Q-ACME-CLIENTA-0001'
), line_data AS (
  SELECT * FROM (
    VALUES
      (1, 'ACME-PLT-CORE', 1::numeric, 5::numeric),
      (2, 'ACME-MOD-THREAT', 250::numeric, 8::numeric),
      (3, 'ACME-MOD-GRC', 250::numeric, 8::numeric),
      (4, 'ACME-DATA-03', 50::numeric, 5::numeric),
      (5, 'ACME-SUP-MEDIUM', 1::numeric, 0::numeric),
      (6, 'ACME-MAINT-ANNUAL', 1::numeric, 0::numeric),
      (7, 'ACME-SVC-PRO', 200::numeric, 0::numeric)
  ) AS x(line_no, item_code, quantity, discount_pct)
), chosen_entry AS (
  SELECT
    pb.id AS price_book_id,
    ci.id AS commercial_item_id,
    ci.item_code,
    pbe.id AS price_book_entry_id,
    pbe.base_price,
    pbe.min_price
  FROM tenant t
  JOIN price_books pb ON pb.tenant_id = t.tenant_id AND pb.name = 'ACME FY2026 Master' AND pb.currency = 'USD'
  JOIN commercial_items ci ON ci.tenant_id = t.tenant_id
  JOIN LATERAL (
    SELECT pbe.*
    FROM price_book_entries pbe
    WHERE pbe.tenant_id = t.tenant_id
      AND pbe.price_book_id = pb.id
      AND pbe.commercial_item_id = ci.id
    ORDER BY pbe.created_at DESC
    LIMIT 1
  ) pbe ON TRUE
)
INSERT INTO quote_line_items (
  tenant_id, quote_id, line_no, commercial_item_id, price_book_entry_id,
  quantity, discount_pct, list_price, unit_price, net_price,
  config_json, pricing_snapshot_json
)
SELECT
  qr.tenant_id,
  qr.quote_id,
  ld.line_no,
  ce.commercial_item_id,
  ce.price_book_entry_id,
  ld.quantity,
  ld.discount_pct,
  ce.base_price,
  GREATEST(ce.base_price * (1 - (ld.discount_pct / 100.0)), COALESCE(ce.min_price, 0)),
  GREATEST(ce.base_price * (1 - (ld.discount_pct / 100.0)), COALESCE(ce.min_price, 0)) * ld.quantity,
  '{}'::jsonb,
  jsonb_build_object(
    'seed', true,
    'base_price', ce.base_price,
    'discount_pct', ld.discount_pct,
    'line_source', 'acme-simulation'
  )
FROM quote_ref qr
JOIN line_data ld ON TRUE
JOIN chosen_entry ce ON ce.item_code = ld.item_code;

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), quote_ref AS (
  SELECT q.id AS quote_id, q.tenant_id
  FROM quotes q
  JOIN tenant t ON t.tenant_id = q.tenant_id
  WHERE q.quote_no = 'Q-ACME-CLIENTA-0001'
), totals AS (
  SELECT
    qli.tenant_id,
    qli.quote_id,
    COALESCE(SUM(qli.list_price * qli.quantity), 0)::numeric(18,6) AS subtotal,
    COALESCE(SUM((qli.list_price * qli.quantity) - qli.net_price), 0)::numeric(18,6) AS discount_total,
    COALESCE(SUM(qli.net_price), 0)::numeric(18,6) AS grand_total
  FROM quote_line_items qli
  JOIN quote_ref qr ON qr.tenant_id = qli.tenant_id AND qr.quote_id = qli.quote_id
  GROUP BY qli.tenant_id, qli.quote_id
)
UPDATE quotes q
SET subtotal = t.subtotal,
    discount_total = t.discount_total,
    surcharge_total = 0,
    tax_total = 0,
    grand_total = t.grand_total,
    margin_pct = CASE WHEN t.grand_total > 0 THEN 28 ELSE 0 END,
    updated_at = NOW()
FROM totals t
WHERE q.tenant_id = t.tenant_id
  AND q.id = t.quote_id;

-- 9) Quote recipients (customer + ACME internal sales/leadership)
WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), quote_ref AS (
  SELECT q.id AS quote_id, q.tenant_id
  FROM quotes q
  JOIN tenant t ON t.tenant_id = q.tenant_id
  WHERE q.quote_no = 'Q-ACME-CLIENTA-0001'
)
DELETE FROM quote_recipients qr
USING quote_ref q
WHERE qr.tenant_id = q.tenant_id
  AND qr.quote_id = q.quote_id;

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), quote_ref AS (
  SELECT q.id AS quote_id, q.tenant_id
  FROM quotes q
  JOIN tenant t ON t.tenant_id = q.tenant_id
  WHERE q.quote_no = 'Q-ACME-CLIENTA-0001'
), contact_ref AS (
  SELECT cc.id AS contact_id, cc.tenant_id
  FROM customer_contacts cc
  JOIN customer_accounts ca ON ca.id = cc.account_id AND ca.tenant_id = cc.tenant_id
  JOIN tenant t ON t.tenant_id = cc.tenant_id
  WHERE ca.account_code = 'CLIENT-A'
    AND cc.email = 'anita.khan@clienta.example.com'
)
INSERT INTO quote_recipients (
  tenant_id, quote_id, contact_id, recipient_type, recipient_role,
  email_override, name_override, sequence_no, is_active, metadata_json
)
SELECT q.tenant_id, q.quote_id, c.contact_id, 'TO', 'CUSTOMER', NULL, NULL, 1, TRUE, '{}'::jsonb
FROM quote_ref q
JOIN contact_ref c ON c.tenant_id = q.tenant_id
UNION ALL
SELECT q.tenant_id, q.quote_id, NULL, 'CC', 'SALES', 'sales.lead@acmeinc.com', 'Jordan Lee', 2, TRUE, '{}'::jsonb
FROM quote_ref q
UNION ALL
SELECT q.tenant_id, q.quote_id, NULL, 'CC', 'LEADERSHIP', 'cto.office@acmeinc.com', 'Ravi Nair', 3, TRUE, '{}'::jsonb
FROM quote_ref q;

COMMIT;

-- Post-seed visibility
SELECT 'TENANT' AS section, t.id::text AS id, t.name AS label, t.default_currency AS detail
FROM tenants t
WHERE t.name = 'ACME Inc';

SELECT 'CATALOG_ITEMS' AS section, COUNT(*)::text AS id, 'commercial_items' AS label, 'rows' AS detail
FROM commercial_items ci
JOIN tenants t ON t.id = ci.tenant_id
WHERE t.name = 'ACME Inc';

SELECT 'RATE_CARD_ENTRIES' AS section, COUNT(*)::text AS id, 'rate_card_entries' AS label, 'rows' AS detail
FROM rate_card_entries rce
JOIN tenants t ON t.id = rce.tenant_id
WHERE t.name = 'ACME Inc';

SELECT 'PRICEBOOK_ENTRIES' AS section, COUNT(*)::text AS id, 'price_book_entries' AS label, 'rows' AS detail
FROM price_book_entries pbe
JOIN tenants t ON t.id = pbe.tenant_id
JOIN price_books pb ON pb.id = pbe.price_book_id
WHERE t.name = 'ACME Inc'
  AND pb.name = 'ACME FY2026 Master';

SELECT 'QUOTE' AS section, q.id::text AS id, q.quote_no AS label,
       ('$' || TO_CHAR(q.grand_total, 'FM999,999,999,990.00')) AS detail
FROM quotes q
JOIN tenants t ON t.id = q.tenant_id
WHERE t.name = 'ACME Inc'
  AND q.quote_no = 'Q-ACME-CLIENTA-0001';
