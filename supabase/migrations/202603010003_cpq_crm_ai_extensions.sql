-- 0003_cpq_crm_ai_extensions.sql
-- Extends core CPQ schema with CRM baseline, quote templates/documents,
-- richer approval governance, and AI-native operational tables.
-- Apply after 0001_cpq_core_schema.sql and before 0004_tenant_rls_extensions.sql.

-- =========================================================
-- Operational admin persistence
-- =========================================================

CREATE TABLE IF NOT EXISTS admin_state (
  tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
  state JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================================
-- Basic CRM baseline
-- =========================================================

CREATE TABLE customer_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  account_code TEXT NOT NULL,
  legal_name TEXT NOT NULL,
  display_name TEXT,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  account_type TEXT NOT NULL DEFAULT 'CUSTOMER',
  industry TEXT,
  segment TEXT,
  website TEXT,
  billing_address_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  shipping_address_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  tax_profile_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  owner_user_id UUID REFERENCES users(id),
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, account_code)
);

CREATE INDEX idx_customer_accounts_tenant_status
  ON customer_accounts (tenant_id, status, account_type);

CREATE INDEX idx_customer_accounts_metadata_gin
  ON customer_accounts USING GIN (metadata_json);

CREATE TABLE customer_contacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  account_id UUID NOT NULL REFERENCES customer_accounts(id) ON DELETE CASCADE,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  email CITEXT NOT NULL,
  phone TEXT,
  title TEXT,
  buying_role TEXT,
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  is_billing_contact BOOLEAN NOT NULL DEFAULT FALSE,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, account_id, email)
);

CREATE INDEX idx_customer_contacts_tenant_account
  ON customer_contacts (tenant_id, account_id, status);

CREATE TABLE opportunities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  account_id UUID NOT NULL REFERENCES customer_accounts(id) ON DELETE RESTRICT,
  opportunity_no TEXT NOT NULL,
  name TEXT NOT NULL,
  stage TEXT NOT NULL DEFAULT 'QUALIFICATION',
  status TEXT NOT NULL DEFAULT 'OPEN',
  amount NUMERIC(18,6),
  currency CHAR(3),
  close_date DATE,
  owner_user_id UUID REFERENCES users(id),
  source_system TEXT,
  source_external_id TEXT,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, opportunity_no),
  UNIQUE (tenant_id, source_system, source_external_id)
);

CREATE INDEX idx_opportunities_tenant_stage
  ON opportunities (tenant_id, status, stage, close_date);

CREATE TABLE internal_teams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  team_type TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, team_type, name)
);

CREATE TABLE internal_team_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  team_id UUID NOT NULL REFERENCES internal_teams(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_in_team TEXT,
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, team_id, user_id)
);

-- =========================================================
-- Quote linkage and recipients
-- =========================================================

ALTER TABLE quotes
  ADD COLUMN IF NOT EXISTS customer_account_id UUID REFERENCES customer_accounts(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS opportunity_id UUID REFERENCES opportunities(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_quotes_tenant_customer_account
  ON quotes (tenant_id, customer_account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_quotes_tenant_opportunity
  ON quotes (tenant_id, opportunity_id);

CREATE TABLE quote_recipients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  quote_id UUID NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
  contact_id UUID REFERENCES customer_contacts(id) ON DELETE SET NULL,
  recipient_type TEXT NOT NULL DEFAULT 'TO',
  recipient_role TEXT NOT NULL DEFAULT 'CUSTOMER',
  email_override CITEXT,
  name_override TEXT,
  sequence_no INTEGER NOT NULL DEFAULT 1,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (recipient_type IN ('TO', 'CC', 'BCC')),
  CHECK (recipient_role IN ('CUSTOMER', 'SALES', 'LEADERSHIP', 'FINANCE', 'LEGAL'))
);

CREATE INDEX idx_quote_recipients_tenant_quote
  ON quote_recipients (tenant_id, quote_id, recipient_type, sequence_no);

-- =========================================================
-- Quote/proposal templates and generated documents
-- =========================================================

CREATE TABLE quote_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  template_code TEXT NOT NULL,
  name TEXT NOT NULL,
  doc_type TEXT NOT NULL DEFAULT 'QUOTE',
  channel TEXT NOT NULL DEFAULT 'PDF',
  locale TEXT NOT NULL DEFAULT 'en-US',
  status TEXT NOT NULL DEFAULT 'DRAFT',
  branding_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  content_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, template_code)
);

CREATE INDEX idx_quote_templates_tenant_status
  ON quote_templates (tenant_id, status, doc_type, channel);

CREATE TABLE quote_template_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  template_id UUID NOT NULL REFERENCES quote_templates(id) ON DELETE CASCADE,
  version_no INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'DRAFT',
  render_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  compiled_artifact_url TEXT,
  effective_from TIMESTAMPTZ,
  effective_to TIMESTAMPTZ,
  published_by UUID REFERENCES users(id),
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_from <= effective_to),
  UNIQUE (tenant_id, template_id, version_no)
);

CREATE INDEX idx_quote_template_versions_tenant_template
  ON quote_template_versions (tenant_id, template_id, status, version_no DESC);

CREATE TABLE quote_template_bindings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  template_id UUID NOT NULL REFERENCES quote_templates(id) ON DELETE CASCADE,
  scope_type TEXT NOT NULL,
  selector_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  priority INTEGER NOT NULL DEFAULT 100,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_quote_template_bindings_tenant_scope
  ON quote_template_bindings (tenant_id, scope_type, is_active, priority);

CREATE INDEX idx_quote_template_bindings_selector_gin
  ON quote_template_bindings USING GIN (selector_json);

CREATE TABLE quote_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  quote_id UUID NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
  template_version_id UUID REFERENCES quote_template_versions(id) ON DELETE SET NULL,
  document_type TEXT NOT NULL DEFAULT 'PROPOSAL',
  status TEXT NOT NULL DEFAULT 'GENERATED',
  file_url TEXT,
  file_storage_key TEXT,
  file_hash TEXT,
  generated_by UUID REFERENCES users(id),
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sent_at TIMESTAMPTZ,
  accepted_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_quote_documents_tenant_quote
  ON quote_documents (tenant_id, quote_id, status, generated_at DESC);

CREATE TABLE quote_document_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  quote_document_id UUID NOT NULL REFERENCES quote_documents(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  actor_user_id UUID REFERENCES users(id),
  actor_contact_id UUID REFERENCES customer_contacts(id),
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_quote_document_events_tenant_doc
  ON quote_document_events (tenant_id, quote_document_id, event_at DESC);

-- =========================================================
-- Approval governance extensions
-- =========================================================

CREATE TABLE approval_delegations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  approver_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  delegate_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ NOT NULL,
  reason TEXT,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (approver_user_id <> delegate_user_id),
  CHECK (ends_at > starts_at)
);

CREATE INDEX idx_approval_delegations_tenant_users
  ON approval_delegations (tenant_id, approver_user_id, delegate_user_id, status, starts_at, ends_at);

CREATE TABLE approval_action_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  approval_instance_id UUID NOT NULL REFERENCES approval_instances(id) ON DELETE CASCADE,
  approval_step_id UUID REFERENCES approval_steps(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  actor_user_id UUID REFERENCES users(id),
  comments TEXT,
  decision_context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approval_action_log_tenant_instance
  ON approval_action_log (tenant_id, approval_instance_id, created_at DESC);

CREATE TABLE approval_sla_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  approval_instance_id UUID NOT NULL REFERENCES approval_instances(id) ON DELETE CASCADE,
  approval_step_id UUID REFERENCES approval_steps(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approval_sla_events_tenant_instance
  ON approval_sla_events (tenant_id, approval_instance_id, event_at DESC);

CREATE TABLE quote_locks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  quote_id UUID NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
  lock_type TEXT NOT NULL DEFAULT 'APPROVAL_REVIEW',
  locked_by UUID REFERENCES users(id),
  locked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  reason TEXT,
  UNIQUE (tenant_id, quote_id, lock_type, is_active)
);

CREATE INDEX idx_quote_locks_tenant_quote
  ON quote_locks (tenant_id, quote_id, is_active, lock_type);

-- =========================================================
-- AI-native control plane tables
-- =========================================================

CREATE TABLE ai_assistant_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  context_type TEXT NOT NULL,
  context_id UUID,
  title TEXT,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_sessions_tenant_context
  ON ai_assistant_sessions (tenant_id, context_type, context_id, status);

CREATE TABLE ai_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  session_id UUID NOT NULL REFERENCES ai_assistant_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  content_json JSONB NOT NULL,
  model_name TEXT,
  prompt_version TEXT,
  input_tokens INTEGER,
  output_tokens INTEGER,
  latency_ms INTEGER,
  safety_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (role IN ('SYSTEM', 'USER', 'ASSISTANT', 'TOOL'))
);

CREATE INDEX idx_ai_messages_tenant_session
  ON ai_messages (tenant_id, session_id, created_at);

CREATE INDEX idx_ai_messages_content_gin
  ON ai_messages USING GIN (content_json);

CREATE TABLE ai_recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  recommendation_type TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id UUID,
  source_model TEXT,
  inputs_hash TEXT,
  recommendation_json JSONB NOT NULL,
  explanation_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  confidence NUMERIC(5,4),
  status TEXT NOT NULL DEFAULT 'PROPOSED',
  applied_by UUID REFERENCES users(id),
  applied_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
);

CREATE INDEX idx_ai_recommendations_tenant_target
  ON ai_recommendations (tenant_id, target_type, target_id, recommendation_type, status);

CREATE INDEX idx_ai_recommendations_json_gin
  ON ai_recommendations USING GIN (recommendation_json);

CREATE TABLE ai_guardrail_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  policy_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  config_json JSONB NOT NULL,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, name, policy_type)
);

CREATE INDEX idx_ai_guardrails_tenant_type_status
  ON ai_guardrail_policies (tenant_id, policy_type, status);

CREATE TABLE ai_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  recommendation_id UUID REFERENCES ai_recommendations(id) ON DELETE SET NULL,
  session_id UUID REFERENCES ai_assistant_sessions(id) ON DELETE SET NULL,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  feedback_value SMALLINT NOT NULL,
  comment TEXT,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (feedback_value IN (-1, 0, 1))
);

CREATE INDEX idx_ai_feedback_tenant_created
  ON ai_feedback (tenant_id, created_at DESC);

CREATE TABLE customer_query_threads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  account_id UUID REFERENCES customer_accounts(id) ON DELETE SET NULL,
  contact_id UUID REFERENCES customer_contacts(id) ON DELETE SET NULL,
  quote_id UUID REFERENCES quotes(id) ON DELETE SET NULL,
  channel TEXT NOT NULL DEFAULT 'PORTAL',
  status TEXT NOT NULL DEFAULT 'OPEN',
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_customer_query_threads_tenant_status
  ON customer_query_threads (tenant_id, status, created_at DESC);

CREATE TABLE customer_query_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  thread_id UUID NOT NULL REFERENCES customer_query_threads(id) ON DELETE CASCADE,
  sender_type TEXT NOT NULL,
  sender_ref TEXT,
  message_text TEXT NOT NULL,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (sender_type IN ('CUSTOMER', 'INTERNAL_USER', 'AI_ASSISTANT', 'SYSTEM'))
);

CREATE INDEX idx_customer_query_messages_tenant_thread
  ON customer_query_messages (tenant_id, thread_id, created_at);

-- =========================================================
-- Updated-at trigger bindings for new mutable tables
-- =========================================================

CREATE TRIGGER trg_customer_accounts_updated_at BEFORE UPDATE ON customer_accounts FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_customer_contacts_updated_at BEFORE UPDATE ON customer_contacts FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_opportunities_updated_at BEFORE UPDATE ON opportunities FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_internal_teams_updated_at BEFORE UPDATE ON internal_teams FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_quote_templates_updated_at BEFORE UPDATE ON quote_templates FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_ai_sessions_updated_at BEFORE UPDATE ON ai_assistant_sessions FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_ai_guardrail_policies_updated_at BEFORE UPDATE ON ai_guardrail_policies FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_customer_query_threads_updated_at BEFORE UPDATE ON customer_query_threads FOR EACH ROW EXECUTE FUNCTION set_updated_at();

