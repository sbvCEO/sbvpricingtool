-- 0002_tenant_rls.sql
-- Tenant session context + row-level security policies.
-- Apply after 0001_cpq_core_schema.sql

-- ------------------------------------------------------------------
-- Session context helpers
-- ------------------------------------------------------------------

CREATE OR REPLACE FUNCTION app_current_tenant()
RETURNS UUID
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  v_tenant TEXT;
BEGIN
  v_tenant := current_setting('app.current_tenant', true);
  IF v_tenant IS NULL OR v_tenant = '' THEN
    RETURN NULL;
  END IF;
  RETURN v_tenant::uuid;
END;
$$;

CREATE OR REPLACE FUNCTION app_set_tenant(p_tenant UUID)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
  PERFORM set_config('app.current_tenant', p_tenant::text, true);
END;
$$;

COMMENT ON FUNCTION app_set_tenant(UUID)
IS 'Call at request/session start so RLS policies can scope tenant-owned rows.';

-- ------------------------------------------------------------------
-- RLS enablement
-- ------------------------------------------------------------------

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE commercial_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE bundle_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_books ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_book_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_components ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_tiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_card_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE rule_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_line_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_calculation_traces ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_reference_values ENABLE ROW LEVEL SECURITY;

-- Optional hardening (uncomment after admin workflow is finalized):
-- ALTER TABLE tenants FORCE ROW LEVEL SECURITY;
-- ... repeat for all tenant tables

-- ------------------------------------------------------------------
-- Policy template: tenant_id must match app.current_tenant
-- ------------------------------------------------------------------

CREATE POLICY p_tenants_isolation ON tenants
  USING (id = app_current_tenant())
  WITH CHECK (id = app_current_tenant());

CREATE POLICY p_organizations_isolation ON organizations
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_users_isolation ON users
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_roles_isolation ON roles
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_user_roles_isolation ON user_roles
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_commercial_items_isolation ON commercial_items
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_bundle_items_isolation ON bundle_items
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_price_books_isolation ON price_books
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_price_book_entries_isolation ON price_book_entries
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_pricing_components_isolation ON pricing_components
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_pricing_tiers_isolation ON pricing_tiers
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_rate_cards_isolation ON rate_cards
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_rate_card_entries_isolation ON rate_card_entries
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_rules_isolation ON rules
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_rule_bindings_isolation ON rule_bindings
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_quotes_isolation ON quotes
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_quote_line_items_isolation ON quote_line_items
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_quote_revisions_isolation ON quote_revisions
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_pricing_calculation_traces_isolation ON pricing_calculation_traces
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_approval_policies_isolation ON approval_policies
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_approval_instances_isolation ON approval_instances
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_approval_steps_isolation ON approval_steps
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_audit_events_isolation ON audit_events
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_outbox_events_isolation ON outbox_events
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_tenant_reference_values_isolation ON tenant_reference_values
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

-- ------------------------------------------------------------------
-- Validation examples
-- ------------------------------------------------------------------
-- SELECT app_set_tenant('00000000-0000-0000-0000-000000000000');
-- SELECT * FROM commercial_items; -- only tenant rows visible
