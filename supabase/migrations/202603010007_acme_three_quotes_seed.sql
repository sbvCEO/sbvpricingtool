-- ACME additional scenario quotes seed (3 quotes)
BEGIN;

-- Accounts + contacts for 3 clients
WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), clients AS (
  SELECT * FROM (
    VALUES
      ('CLIENT-B', 'Client B Manufacturing Inc', 'Client B', 'Manufacturing', 'Mid-Market', 'nina.patel@clientb.example.com', 'Nina', 'Patel', 'VP Digital Transformation'),
      ('CLIENT-C', 'Client C Retail Group', 'Client C', 'Retail', 'Enterprise', 'omar.diaz@clientc.example.com', 'Omar', 'Diaz', 'Head of Security Operations'),
      ('CLIENT-D', 'Client D Financial Services', 'Client D', 'Financial Services', 'Enterprise', 'elena.rossi@clientd.example.com', 'Elena', 'Rossi', 'CISO')
  ) AS x(account_code, legal_name, display_name, industry, segment, email, first_name, last_name, title)
)
INSERT INTO customer_accounts (
  tenant_id, account_code, legal_name, display_name, status, account_type, industry, segment, website, metadata_json
)
SELECT
  t.tenant_id,
  c.account_code,
  c.legal_name,
  c.display_name,
  'ACTIVE',
  'CUSTOMER',
  c.industry,
  c.segment,
  lower(replace(c.display_name, ' ', '')) || '.example.com',
  '{"seed":"acme-three-quotes"}'::jsonb
FROM tenant t
JOIN clients c ON TRUE
ON CONFLICT (tenant_id, account_code) DO UPDATE
SET legal_name = EXCLUDED.legal_name,
    display_name = EXCLUDED.display_name,
    industry = EXCLUDED.industry,
    segment = EXCLUDED.segment,
    status = 'ACTIVE';

WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), clients AS (
  SELECT * FROM (
    VALUES
      ('CLIENT-B', 'nina.patel@clientb.example.com', 'Nina', 'Patel', 'VP Digital Transformation'),
      ('CLIENT-C', 'omar.diaz@clientc.example.com', 'Omar', 'Diaz', 'Head of Security Operations'),
      ('CLIENT-D', 'elena.rossi@clientd.example.com', 'Elena', 'Rossi', 'CISO')
  ) AS x(account_code, email, first_name, last_name, title)
), acct AS (
  SELECT ca.id AS account_id, ca.tenant_id, ca.account_code
  FROM customer_accounts ca
  JOIN tenant t ON t.tenant_id = ca.tenant_id
)
INSERT INTO customer_contacts (
  tenant_id, account_id, first_name, last_name, email, title, buying_role,
  is_primary, is_billing_contact, status
)
SELECT
  a.tenant_id,
  a.account_id,
  c.first_name,
  c.last_name,
  c.email,
  c.title,
  'Economic Buyer',
  TRUE,
  TRUE,
  'ACTIVE'
FROM acct a
JOIN clients c ON c.account_code = a.account_code
ON CONFLICT (tenant_id, account_id, email) DO UPDATE
SET first_name = EXCLUDED.first_name,
    last_name = EXCLUDED.last_name,
    title = EXCLUDED.title,
    status = 'ACTIVE';

-- Opportunities
WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), acct AS (
  SELECT ca.id AS account_id, ca.tenant_id, ca.account_code
  FROM customer_accounts ca
  JOIN tenant t ON t.tenant_id = ca.tenant_id
  WHERE ca.account_code IN ('CLIENT-B','CLIENT-C','CLIENT-D')
), opps AS (
  SELECT * FROM (
    VALUES
      ('CLIENT-B', 'OPP-CLIENTB-2026-001', 'Client B SMB Starter Expansion', 68500::numeric, DATE '2026-05-20'),
      ('CLIENT-C', 'OPP-CLIENTC-2026-001', 'Client C Mid-Market Security Modernization', 182000::numeric, DATE '2026-06-18'),
      ('CLIENT-D', 'OPP-CLIENTD-2026-001', 'Client D Enterprise Command Rollout', 244000::numeric, DATE '2026-07-15')
  ) AS x(account_code, opportunity_no, name, amount, close_date)
)
INSERT INTO opportunities (
  tenant_id, account_id, opportunity_no, name, stage, status, amount, currency, close_date, metadata_json
)
SELECT
  a.tenant_id,
  a.account_id,
  o.opportunity_no,
  o.name,
  'PROPOSAL',
  'OPEN',
  o.amount,
  'USD',
  o.close_date,
  '{"seed":"acme-three-quotes"}'::jsonb
FROM acct a
JOIN opps o ON o.account_code = a.account_code
ON CONFLICT (tenant_id, opportunity_no) DO UPDATE
SET name = EXCLUDED.name,
    amount = EXCLUDED.amount,
    close_date = EXCLUDED.close_date,
    status = 'OPEN';

-- Quotes (3 scenarios)
WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), pb AS (
  SELECT p.id AS price_book_id, p.tenant_id
  FROM price_books p
  JOIN tenant t ON t.tenant_id = p.tenant_id
  WHERE p.name = 'ACME FY2026 Master' AND p.currency = 'USD'
), acct AS (
  SELECT ca.id AS customer_account_id, ca.tenant_id, ca.account_code
  FROM customer_accounts ca
  JOIN tenant t ON t.tenant_id = ca.tenant_id
), opp AS (
  SELECT o.id AS opportunity_id, o.tenant_id, o.opportunity_no
  FROM opportunities o
  JOIN tenant t ON t.tenant_id = o.tenant_id
)
INSERT INTO quotes (
  tenant_id, quote_no, customer_external_id, customer_account_id, opportunity_id,
  status, currency, region, price_book_id, valid_until,
  subtotal, discount_total, surcharge_total, tax_total, grand_total, margin_pct, revision_no
)
SELECT
  pb.tenant_id,
  q.quote_no,
  q.account_code,
  a.customer_account_id,
  o.opportunity_id,
  q.status,
  'USD',
  'US',
  pb.price_book_id,
  q.valid_until,
  0,0,0,0,0,0,1
FROM pb
JOIN (
  VALUES
    ('Q-ACME-CLIENTB-0001','CLIENT-B','OPP-CLIENTB-2026-001','DRAFT', DATE '2026-06-10'),
    ('Q-ACME-CLIENTC-0001','CLIENT-C','OPP-CLIENTC-2026-001','REVIEW', DATE '2026-06-30'),
    ('Q-ACME-CLIENTD-0001','CLIENT-D','OPP-CLIENTD-2026-001','APPROVAL_PENDING', DATE '2026-07-31')
) AS q(quote_no, account_code, opportunity_no, status, valid_until) ON TRUE
JOIN acct a ON a.tenant_id = pb.tenant_id AND a.account_code = q.account_code
JOIN opp o ON o.tenant_id = pb.tenant_id AND o.opportunity_no = q.opportunity_no
ON CONFLICT (tenant_id, quote_no) DO UPDATE
SET customer_external_id = EXCLUDED.customer_external_id,
    customer_account_id = EXCLUDED.customer_account_id,
    opportunity_id = EXCLUDED.opportunity_id,
    status = EXCLUDED.status,
    valid_until = EXCLUDED.valid_until,
    price_book_id = EXCLUDED.price_book_id;

-- Remove existing lines for these 3 quotes
WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), q AS (
  SELECT id AS quote_id, tenant_id
  FROM quotes
  WHERE tenant_id = (SELECT tenant_id FROM tenant)
    AND quote_no IN ('Q-ACME-CLIENTB-0001','Q-ACME-CLIENTC-0001','Q-ACME-CLIENTD-0001')
)
DELETE FROM quote_line_items qli
USING q
WHERE qli.tenant_id = q.tenant_id
  AND qli.quote_id = q.quote_id;

-- Insert scenario lines
WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), pb AS (
  SELECT p.id AS price_book_id, p.tenant_id
  FROM price_books p
  JOIN tenant t ON t.tenant_id = p.tenant_id
  WHERE p.name = 'ACME FY2026 Master' AND p.currency = 'USD'
), quote_ref AS (
  SELECT q.id AS quote_id, q.tenant_id, q.quote_no
  FROM quotes q
  JOIN tenant t ON t.tenant_id = q.tenant_id
  WHERE q.quote_no IN ('Q-ACME-CLIENTB-0001','Q-ACME-CLIENTC-0001','Q-ACME-CLIENTD-0001')
), line_data AS (
  SELECT * FROM (
    VALUES
      ('Q-ACME-CLIENTB-0001', 1, 'ACME-PLT-CORE', 1::numeric, 12::numeric),
      ('Q-ACME-CLIENTB-0001', 2, 'ACME-MOD-AUTO', 60::numeric, 10::numeric),
      ('Q-ACME-CLIENTB-0001', 3, 'ACME-DATA-10', 100::numeric, 0::numeric),
      ('Q-ACME-CLIENTB-0001', 4, 'ACME-SUP-SMALL', 1::numeric, 0::numeric),
      ('Q-ACME-CLIENTB-0001', 5, 'ACME-SVC-PRO', 40::numeric, 0::numeric),

      ('Q-ACME-CLIENTC-0001', 1, 'ACME-BND-SECURE', 1::numeric, 9::numeric),
      ('Q-ACME-CLIENTC-0001', 2, 'ACME-DATA-03', 10::numeric, 5::numeric),
      ('Q-ACME-CLIENTC-0001', 3, 'ACME-DATA-07', 50::numeric, 6::numeric),
      ('Q-ACME-CLIENTC-0001', 4, 'ACME-SUP-MEDIUM', 1::numeric, 2::numeric),
      ('Q-ACME-CLIENTC-0001', 5, 'ACME-MAINT-ANNUAL', 1::numeric, 0::numeric),
      ('Q-ACME-CLIENTC-0001', 6, 'ACME-SVC-PRO', 120::numeric, 0::numeric),

      ('Q-ACME-CLIENTD-0001', 1, 'ACME-BND-ENTERPRISE', 1::numeric, 10::numeric),
      ('Q-ACME-CLIENTD-0001', 2, 'ACME-DATA-09', 50::numeric, 7::numeric),
      ('Q-ACME-CLIENTD-0001', 3, 'ACME-SUP-LARGE', 1::numeric, 4::numeric),
      ('Q-ACME-CLIENTD-0001', 4, 'ACME-MAINT-ANNUAL', 1::numeric, 3::numeric),
      ('Q-ACME-CLIENTD-0001', 5, 'ACME-SVC-PRO', 350::numeric, 0::numeric)
  ) AS x(quote_no, line_no, item_code, quantity, discount_pct)
), chosen_entry AS (
  SELECT
    pb.price_book_id,
    ci.id AS commercial_item_id,
    ci.item_code,
    pbe.id AS price_book_entry_id,
    pbe.base_price,
    pbe.min_price
  FROM pb
  JOIN commercial_items ci ON ci.tenant_id = pb.tenant_id
  JOIN LATERAL (
    SELECT pbe.*
    FROM price_book_entries pbe
    WHERE pbe.tenant_id = pb.tenant_id
      AND pbe.price_book_id = pb.price_book_id
      AND pbe.commercial_item_id = ci.id
    ORDER BY pbe.created_at DESC
    LIMIT 1
  ) pbe ON TRUE
)
INSERT INTO quote_line_items (
  tenant_id, quote_id, line_no, commercial_item_id, price_book_entry_id,
  quantity, discount_pct, list_price, unit_price, net_price, config_json, pricing_snapshot_json
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
  jsonb_build_object('seed', true, 'scenario', ld.quote_no)
FROM quote_ref qr
JOIN line_data ld ON ld.quote_no = qr.quote_no
JOIN chosen_entry ce ON ce.item_code = ld.item_code;

-- Recompute totals
WITH tenant AS (
  SELECT id AS tenant_id FROM tenants WHERE name = 'ACME Inc'
), q AS (
  SELECT id AS quote_id, tenant_id
  FROM quotes
  WHERE tenant_id = (SELECT tenant_id FROM tenant)
    AND quote_no IN ('Q-ACME-CLIENTB-0001','Q-ACME-CLIENTC-0001','Q-ACME-CLIENTD-0001')
), totals AS (
  SELECT
    qli.tenant_id,
    qli.quote_id,
    COALESCE(SUM(qli.list_price * qli.quantity), 0)::numeric(18,6) AS subtotal,
    COALESCE(SUM((qli.list_price * qli.quantity) - qli.net_price), 0)::numeric(18,6) AS discount_total,
    COALESCE(SUM(qli.net_price), 0)::numeric(18,6) AS grand_total
  FROM quote_line_items qli
  JOIN q ON q.quote_id = qli.quote_id AND q.tenant_id = qli.tenant_id
  GROUP BY qli.tenant_id, qli.quote_id
)
UPDATE quotes qq
SET subtotal = t.subtotal,
    discount_total = t.discount_total,
    surcharge_total = 0,
    tax_total = 0,
    grand_total = t.grand_total,
    margin_pct = CASE WHEN t.grand_total > 0 THEN 28 ELSE 0 END,
    updated_at = NOW()
FROM totals t
WHERE qq.tenant_id = t.tenant_id
  AND qq.id = t.quote_id;

COMMIT;

SELECT q.quote_no, q.status, q.grand_total, q.margin_pct
FROM quotes q
JOIN tenants t ON t.id = q.tenant_id
WHERE t.name = 'ACME Inc'
  AND q.quote_no IN ('Q-ACME-CLIENTB-0001','Q-ACME-CLIENTC-0001','Q-ACME-CLIENTD-0001')
ORDER BY q.quote_no;
