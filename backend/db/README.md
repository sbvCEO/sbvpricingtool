# Database Artifacts

## Migrations
1. `migrations/0001_cpq_core_schema.sql` - Core behavior-driven CPQ schema.
2. `migrations/0002_tenant_rls.sql` - Tenant session context helpers and row-level security policies.
3. `migrations/0003_cpq_crm_ai_extensions.sql` - CRM baseline, quote templates/documents, approval governance extensions, and AI-native tables.
4. `migrations/0004_tenant_rls_extensions.sql` - RLS policies for extension tables added in 0003.
5. `migrations/0005_supabase_rls_tenant_claims.sql` - Supabase-oriented tenant claim fallback for `app_current_tenant()`.

## Pressure Tests
- `tests/pressure_test_scenarios.sql` - Scenario coverage script for multi-company commercial patterns.
- `tests/rls_verification.sql` - Tenant-isolation RLS verification checks.

## Run Order
1. Execute migration SQL in order.
2. Execute pressure test script (uses transaction rollback; does not persist fixtures).

## Notes
- `tenant_id` is present on all tenant-owned tables.
- RLS is enforced via `app_current_tenant()` + `app_set_tenant(uuid)` policies on tenant-owned tables.
