-- 0004_tenant_rls_extensions.sql
-- RLS enablement for extension tables introduced in 0003.
-- Apply after 0002_tenant_rls.sql and 0003_cpq_crm_ai_extensions.sql.

ALTER TABLE admin_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE internal_teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE internal_team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_recipients ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_template_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_template_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_document_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_delegations ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_action_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_sla_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_locks ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_assistant_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_guardrail_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_query_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_query_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY p_admin_state_isolation ON admin_state
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_customer_accounts_isolation ON customer_accounts
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_customer_contacts_isolation ON customer_contacts
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_opportunities_isolation ON opportunities
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_internal_teams_isolation ON internal_teams
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_internal_team_members_isolation ON internal_team_members
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_quote_recipients_isolation ON quote_recipients
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_quote_templates_isolation ON quote_templates
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_quote_template_versions_isolation ON quote_template_versions
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_quote_template_bindings_isolation ON quote_template_bindings
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_quote_documents_isolation ON quote_documents
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_quote_document_events_isolation ON quote_document_events
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_approval_delegations_isolation ON approval_delegations
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_approval_action_log_isolation ON approval_action_log
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_approval_sla_events_isolation ON approval_sla_events
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_quote_locks_isolation ON quote_locks
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_ai_assistant_sessions_isolation ON ai_assistant_sessions
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_ai_messages_isolation ON ai_messages
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_ai_recommendations_isolation ON ai_recommendations
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_ai_guardrail_policies_isolation ON ai_guardrail_policies
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_ai_feedback_isolation ON ai_feedback
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_customer_query_threads_isolation ON customer_query_threads
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

CREATE POLICY p_customer_query_messages_isolation ON customer_query_messages
  USING (tenant_id = app_current_tenant())
  WITH CHECK (tenant_id = app_current_tenant());

