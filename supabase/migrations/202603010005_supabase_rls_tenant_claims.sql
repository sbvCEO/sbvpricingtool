-- 0005_supabase_rls_tenant_claims.sql
-- Supabase hardening: resolve tenant from request JWT claims when app.current_tenant is not set.
-- Apply after 0002_tenant_rls.sql.

CREATE OR REPLACE FUNCTION app_current_tenant()
RETURNS UUID
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  v_tenant TEXT;
BEGIN
  -- 1) Explicit app-set tenant context (server-side preferred path)
  v_tenant := current_setting('app.current_tenant', true);
  IF v_tenant IS NOT NULL AND v_tenant <> '' THEN
    RETURN v_tenant::uuid;
  END IF;

  -- 2) Supabase/PostgREST request claim style
  v_tenant := current_setting('request.jwt.claim.tenant_id', true);
  IF v_tenant IS NOT NULL AND v_tenant <> '' THEN
    RETURN v_tenant::uuid;
  END IF;

  -- 3) Supabase auth.jwt() helper when available
  BEGIN
    SELECT COALESCE(
      auth.jwt()->>'tenant_id',
      auth.jwt()->'app_metadata'->>'tenant_id'
    ) INTO v_tenant;
  EXCEPTION
    WHEN undefined_function OR invalid_schema_name THEN
      v_tenant := NULL;
  END;

  IF v_tenant IS NOT NULL AND v_tenant <> '' THEN
    RETURN v_tenant::uuid;
  END IF;

  RETURN NULL;
EXCEPTION
  WHEN invalid_text_representation THEN
    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION app_current_tenant()
IS 'Tenant resolver for RLS: app.current_tenant -> request.jwt.claim.tenant_id -> auth.jwt().tenant_id.';

