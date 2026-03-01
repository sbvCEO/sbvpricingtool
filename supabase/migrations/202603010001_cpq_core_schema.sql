-- 0001_cpq_core_schema.sql
-- CPQ core schema modeled by commercial behavior.
-- PostgreSQL 15+

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

-- =========================================================
-- Shared helpers
-- =========================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================================================
-- Tenant + Identity
-- =========================================================

CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  plan_tier TEXT NOT NULL DEFAULT 'STANDARD',
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  default_currency CHAR(3) NOT NULL,
  timezone TEXT NOT NULL DEFAULT 'UTC',
  settings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  region TEXT,
  tax_profile_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, name)
);

CREATE INDEX idx_organizations_tenant ON organizations (tenant_id);

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  email CITEXT NOT NULL,
  full_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  auth_provider_sub TEXT,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, email)
);

CREATE INDEX idx_users_tenant_status ON users (tenant_id, status);

CREATE TABLE roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, name)
);

CREATE TABLE permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL UNIQUE,
  resource TEXT NOT NULL,
  action TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_roles (
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (tenant_id, user_id, role_id)
);

CREATE TABLE role_permissions (
  role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
  granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (role_id, permission_id)
);

-- =========================================================
-- Flexible code sets (avoid hard DB enums)
-- =========================================================

CREATE TABLE ref_item_types (
  code TEXT PRIMARY KEY,
  description TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO ref_item_types (code, description) VALUES
  ('LICENSED_SOFTWARE', 'Licensed software/product modules'),
  ('SUBSCRIPTION', 'Recurring term-based commercial item'),
  ('SUPPORT_PACKAGE', 'Support hours package'),
  ('SERVICE', 'Professional or managed service'),
  ('HARDWARE', 'Physical item'),
  ('DATA_PRODUCT', 'Report or data product'),
  ('TOKEN', 'Usage/consumption token'),
  ('BUNDLE', 'Composite container item'),
  ('POC', 'Proof-of-concept deal item');

CREATE TABLE ref_pricing_models (
  code TEXT PRIMARY KEY,
  description TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO ref_pricing_models (code, description) VALUES
  ('FIXED_PRICE', 'Flat value'),
  ('PER_USER', 'Per user pricing'),
  ('PER_UNIT', 'Per unit/item pricing'),
  ('TIERED', 'Tier-based pricing'),
  ('USAGE_BASED', 'Consumption pricing'),
  ('RATE_CARD', 'Role/delivery based rates'),
  ('CUSTOM', 'Manually negotiated non-standard model');

CREATE TABLE ref_component_types (
  code TEXT PRIMARY KEY,
  description TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO ref_component_types (code, description) VALUES
  ('BASE_PRICE', 'Primary base price component'),
  ('DISCOUNT', 'Negative adjustment'),
  ('SURCHARGE', 'Positive adjustment'),
  ('REGIONAL_ADJUSTMENT', 'Geo/currency adjustment'),
  ('MARGIN_ADJUSTMENT', 'Margin guardrail adjustment'),
  ('TOKEN_MULTIPLIER', 'Usage multiplier component');

CREATE TABLE ref_value_types (
  code TEXT PRIMARY KEY,
  description TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO ref_value_types (code, description) VALUES
  ('PERCENT', 'Percentage value'),
  ('ABSOLUTE', 'Absolute currency/quantity value'),
  ('FORMULA', 'Formula expression evaluation');

CREATE TABLE ref_inclusion_types (
  code TEXT PRIMARY KEY,
  description TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO ref_inclusion_types (code, description) VALUES
  ('REQUIRED', 'Must be included in bundle'),
  ('OPTIONAL', 'Can be included if selected');

-- Tenant-specific extension values for future custom coding.
CREATE TABLE tenant_reference_values (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  reference_set TEXT NOT NULL,
  code TEXT NOT NULL,
  description TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, reference_set, code)
);

CREATE INDEX idx_tenant_reference_values_tenant_set
  ON tenant_reference_values (tenant_id, reference_set, is_active);

-- =========================================================
-- Commercial Catalog (canonical)
-- =========================================================

CREATE TABLE commercial_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  item_code TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  item_type TEXT NOT NULL REFERENCES ref_item_types(code),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  versionable BOOLEAN NOT NULL DEFAULT FALSE,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, item_code)
);

CREATE INDEX idx_commercial_items_tenant_type_active
  ON commercial_items (tenant_id, item_type, is_active);

CREATE INDEX idx_commercial_items_metadata_gin
  ON commercial_items USING GIN (metadata_json);

CREATE TABLE bundle_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  bundle_item_id UUID NOT NULL REFERENCES commercial_items(id) ON DELETE CASCADE,
  child_item_id UUID NOT NULL REFERENCES commercial_items(id) ON DELETE RESTRICT,
  inclusion_type TEXT NOT NULL REFERENCES ref_inclusion_types(code),
  qty_rule_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  override_price_allowed BOOLEAN NOT NULL DEFAULT FALSE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (bundle_item_id <> child_item_id),
  UNIQUE (tenant_id, bundle_item_id, child_item_id)
);

CREATE INDEX idx_bundle_items_tenant_bundle
  ON bundle_items (tenant_id, bundle_item_id);

-- =========================================================
-- Pricing structures
-- =========================================================

CREATE TABLE price_books (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  currency CHAR(3) NOT NULL,
  valid_from DATE,
  valid_to DATE,
  status TEXT NOT NULL DEFAULT 'DRAFT',
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_from <= valid_to),
  UNIQUE (tenant_id, name, currency)
);

CREATE INDEX idx_price_books_tenant_status_dates
  ON price_books (tenant_id, status, valid_from, valid_to);

CREATE TABLE price_book_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  price_book_id UUID NOT NULL REFERENCES price_books(id) ON DELETE CASCADE,
  commercial_item_id UUID NOT NULL REFERENCES commercial_items(id) ON DELETE RESTRICT,
  pricing_model TEXT NOT NULL REFERENCES ref_pricing_models(code),
  base_price NUMERIC(18,6),
  min_qty NUMERIC(18,6),
  max_qty NUMERIC(18,6),
  min_price NUMERIC(18,6),
  max_discount_pct NUMERIC(7,4),
  ratecard_id UUID,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (base_price IS NULL OR base_price >= 0),
  CHECK (min_qty IS NULL OR min_qty >= 0),
  CHECK (max_qty IS NULL OR max_qty >= 0),
  CHECK (max_qty IS NULL OR min_qty IS NULL OR max_qty >= min_qty),
  CHECK (min_price IS NULL OR min_price >= 0),
  CHECK (max_discount_pct IS NULL OR (max_discount_pct >= 0 AND max_discount_pct <= 100))
);

CREATE INDEX idx_price_book_entries_tenant_book_item
  ON price_book_entries (tenant_id, price_book_id, commercial_item_id);

CREATE INDEX idx_price_book_entries_tenant_model
  ON price_book_entries (tenant_id, pricing_model);

CREATE INDEX idx_price_book_entries_metadata_gin
  ON price_book_entries USING GIN (metadata_json);

CREATE TABLE pricing_components (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  price_book_entry_id UUID NOT NULL REFERENCES price_book_entries(id) ON DELETE CASCADE,
  component_type TEXT NOT NULL REFERENCES ref_component_types(code),
  value_type TEXT NOT NULL REFERENCES ref_value_types(code),
  value NUMERIC(18,6),
  formula_expression TEXT,
  sequence_no INTEGER NOT NULL DEFAULT 100,
  scope_filter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (
    (value_type = 'FORMULA' AND formula_expression IS NOT NULL)
    OR
    (value_type IN ('PERCENT', 'ABSOLUTE') AND value IS NOT NULL)
  )
);

CREATE INDEX idx_pricing_components_tenant_entry
  ON pricing_components (tenant_id, price_book_entry_id, sequence_no, is_active);

CREATE INDEX idx_pricing_components_scope_gin
  ON pricing_components USING GIN (scope_filter_json);

CREATE INDEX idx_pricing_components_metadata_gin
  ON pricing_components USING GIN (metadata_json);

-- Tiering model for TIERED pricing.
CREATE TABLE pricing_tiers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  price_book_entry_id UUID NOT NULL REFERENCES price_book_entries(id) ON DELETE CASCADE,
  tier_no INTEGER NOT NULL,
  lower_bound NUMERIC(18,6) NOT NULL,
  upper_bound NUMERIC(18,6),
  tier_price NUMERIC(18,6),
  tier_discount_pct NUMERIC(7,4),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (lower_bound >= 0),
  CHECK (upper_bound IS NULL OR upper_bound > lower_bound),
  CHECK (tier_price IS NULL OR tier_price >= 0),
  CHECK (tier_discount_pct IS NULL OR (tier_discount_pct >= 0 AND tier_discount_pct <= 100)),
  CHECK ((tier_price IS NOT NULL) OR (tier_discount_pct IS NOT NULL)),
  UNIQUE (tenant_id, price_book_entry_id, tier_no)
);

CREATE INDEX idx_pricing_tiers_tenant_entry_bounds
  ON pricing_tiers (tenant_id, price_book_entry_id, lower_bound, upper_bound);

-- =========================================================
-- Rate card for service/rate-based offerings
-- =========================================================

CREATE TABLE rate_cards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  currency CHAR(3) NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, name, currency)
);

CREATE TABLE rate_card_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  rate_card_id UUID NOT NULL REFERENCES rate_cards(id) ON DELETE CASCADE,
  role_name TEXT NOT NULL,
  delivery_type TEXT NOT NULL,
  unit TEXT NOT NULL DEFAULT 'HOUR',
  rate_per_unit NUMERIC(18,6) NOT NULL,
  effective_from DATE,
  effective_to DATE,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (rate_per_unit >= 0),
  CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_from <= effective_to),
  UNIQUE (tenant_id, rate_card_id, role_name, delivery_type, unit, effective_from)
);

CREATE INDEX idx_rate_card_entries_tenant_card
  ON rate_card_entries (tenant_id, rate_card_id, role_name, delivery_type);

ALTER TABLE price_book_entries
  ADD CONSTRAINT fk_price_book_entries_ratecard
  FOREIGN KEY (ratecard_id) REFERENCES rate_cards(id) ON DELETE SET NULL;

-- =========================================================
-- Rules model (storage, execution by app engine)
-- =========================================================

CREATE TABLE rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  rule_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'DRAFT',
  priority INTEGER NOT NULL DEFAULT 100,
  effective_from TIMESTAMPTZ,
  effective_to TIMESTAMPTZ,
  dsl_json JSONB NOT NULL,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_from <= effective_to)
);

CREATE INDEX idx_rules_tenant_type_status_priority
  ON rules (tenant_id, rule_type, status, priority);

CREATE INDEX idx_rules_dsl_gin ON rules USING GIN (dsl_json);

CREATE TABLE rule_bindings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  rule_id UUID NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
  scope_type TEXT NOT NULL,
  selector_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, rule_id, scope_type)
);

CREATE INDEX idx_rule_bindings_tenant_rule ON rule_bindings (tenant_id, rule_id);
CREATE INDEX idx_rule_bindings_selector_gin ON rule_bindings USING GIN (selector_json);

-- =========================================================
-- Quote + lifecycle + pricing trace
-- =========================================================

CREATE TABLE quotes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  quote_no TEXT NOT NULL,
  organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
  customer_external_id TEXT,
  status TEXT NOT NULL DEFAULT 'DRAFT',
  currency CHAR(3) NOT NULL,
  region TEXT,
  price_book_id UUID REFERENCES price_books(id) ON DELETE RESTRICT,
  subtotal NUMERIC(18,6) NOT NULL DEFAULT 0,
  discount_total NUMERIC(18,6) NOT NULL DEFAULT 0,
  surcharge_total NUMERIC(18,6) NOT NULL DEFAULT 0,
  tax_total NUMERIC(18,6) NOT NULL DEFAULT 0,
  grand_total NUMERIC(18,6) NOT NULL DEFAULT 0,
  margin_pct NUMERIC(7,4),
  revision_no INTEGER NOT NULL DEFAULT 1,
  valid_until DATE,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, quote_no)
);

CREATE INDEX idx_quotes_tenant_status_created
  ON quotes (tenant_id, status, created_at DESC);

CREATE TABLE quote_line_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  quote_id UUID NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
  line_no INTEGER NOT NULL,
  commercial_item_id UUID NOT NULL REFERENCES commercial_items(id) ON DELETE RESTRICT,
  price_book_entry_id UUID REFERENCES price_book_entries(id) ON DELETE SET NULL,
  quantity NUMERIC(18,6) NOT NULL DEFAULT 1,
  term_months INTEGER,
  list_price NUMERIC(18,6),
  unit_price NUMERIC(18,6),
  net_price NUMERIC(18,6),
  discount_pct NUMERIC(7,4),
  cost_amount NUMERIC(18,6),
  margin_pct NUMERIC(7,4),
  config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  pricing_snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (quantity > 0),
  CHECK (discount_pct IS NULL OR (discount_pct >= 0 AND discount_pct <= 100)),
  UNIQUE (tenant_id, quote_id, line_no)
);

CREATE INDEX idx_quote_lines_tenant_quote
  ON quote_line_items (tenant_id, quote_id, line_no);

CREATE INDEX idx_quote_lines_config_gin
  ON quote_line_items USING GIN (config_json);

CREATE TABLE quote_revisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  quote_id UUID NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
  revision_no INTEGER NOT NULL,
  change_reason TEXT,
  snapshot_json JSONB NOT NULL,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, quote_id, revision_no)
);

CREATE INDEX idx_quote_revisions_tenant_quote
  ON quote_revisions (tenant_id, quote_id, revision_no DESC);

CREATE TABLE pricing_calculation_traces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  quote_id UUID REFERENCES quotes(id) ON DELETE CASCADE,
  quote_line_item_id UUID REFERENCES quote_line_items(id) ON DELETE CASCADE,
  execution_mode TEXT NOT NULL DEFAULT 'PREVIEW',
  engine_version TEXT NOT NULL,
  rule_set_version TEXT,
  trace_json JSONB NOT NULL,
  input_hash TEXT NOT NULL,
  output_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pricing_traces_tenant_quote
  ON pricing_calculation_traces (tenant_id, quote_id, created_at DESC);

CREATE INDEX idx_pricing_traces_input_hash
  ON pricing_calculation_traces (tenant_id, input_hash);

-- =========================================================
-- Approval workflow
-- =========================================================

CREATE TABLE approval_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  conditions_json JSONB NOT NULL,
  route_template_json JSONB NOT NULL,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, name)
);

CREATE TABLE approval_instances (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  quote_id UUID NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
  approval_policy_id UUID REFERENCES approval_policies(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'PENDING',
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  sla_due_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approval_instances_tenant_quote_status
  ON approval_instances (tenant_id, quote_id, status);

CREATE TABLE approval_steps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  approval_instance_id UUID NOT NULL REFERENCES approval_instances(id) ON DELETE CASCADE,
  seq_no INTEGER NOT NULL,
  approver_type TEXT NOT NULL,
  approver_ref TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'PENDING',
  acted_by UUID REFERENCES users(id),
  acted_at TIMESTAMPTZ,
  comments TEXT,
  sla_due_at TIMESTAMPTZ,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, approval_instance_id, seq_no)
);

CREATE INDEX idx_approval_steps_tenant_instance_status
  ON approval_steps (tenant_id, approval_instance_id, status);

-- =========================================================
-- Audit + async outbox
-- =========================================================

CREATE TABLE audit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  entity_type TEXT NOT NULL,
  entity_id UUID,
  action TEXT NOT NULL,
  actor_user_id UUID REFERENCES users(id),
  request_id TEXT,
  source_ip INET,
  before_json JSONB,
  after_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_events_tenant_entity_time
  ON audit_events (tenant_id, entity_type, entity_id, created_at DESC);

CREATE TABLE outbox_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  aggregate_type TEXT NOT NULL,
  aggregate_id UUID,
  event_type TEXT NOT NULL,
  payload_json JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'PENDING',
  available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  retry_count INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  published_at TIMESTAMPTZ
);

CREATE INDEX idx_outbox_status_available
  ON outbox_events (status, available_at, created_at);

CREATE INDEX idx_outbox_tenant_event
  ON outbox_events (tenant_id, event_type, created_at DESC);

-- =========================================================
-- Trigger setup
-- =========================================================

CREATE TRIGGER trg_tenants_updated_at BEFORE UPDATE ON tenants FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_roles_updated_at BEFORE UPDATE ON roles FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_commercial_items_updated_at BEFORE UPDATE ON commercial_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_price_books_updated_at BEFORE UPDATE ON price_books FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_price_book_entries_updated_at BEFORE UPDATE ON price_book_entries FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_pricing_components_updated_at BEFORE UPDATE ON pricing_components FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_rate_cards_updated_at BEFORE UPDATE ON rate_cards FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_rules_updated_at BEFORE UPDATE ON rules FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_quotes_updated_at BEFORE UPDATE ON quotes FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_quote_line_items_updated_at BEFORE UPDATE ON quote_line_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_approval_policies_updated_at BEFORE UPDATE ON approval_policies FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================================================
-- Notes for T003 (RLS) - implemented in next migration.
-- 1) Enable RLS on all tenant tables.
-- 2) Use current_setting('app.current_tenant', true) for tenant scope.
-- =========================================================
