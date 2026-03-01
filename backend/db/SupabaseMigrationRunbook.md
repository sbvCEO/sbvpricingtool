# Supabase Migration Runbook (CPQ Platform)

This runbook applies the database schema safely to a Supabase project and verifies tenant isolation + CPQ/CRM/AI extension readiness.

## Scope

Migrations covered:
1. `backend/db/migrations/0001_cpq_core_schema.sql`
2. `backend/db/migrations/0002_tenant_rls.sql`
3. `backend/db/migrations/0003_cpq_crm_ai_extensions.sql`
4. `backend/db/migrations/0004_tenant_rls_extensions.sql`
5. `backend/db/migrations/0005_supabase_rls_tenant_claims.sql`

## Prerequisites

1. Supabase CLI installed.
2. You have:
   - Project ref
   - DB password
   - Access token (if using `supabase link`)
3. You are in repo root:
   - `/Users/vivek/Documents/smartbusinessvalue/SANCNIDA/ Development`
4. Local backup target directory exists:
   - `backend/db/backups`

## Safety Rules (Do First)

1. Never run directly on production first.
2. Run first on a staging Supabase project cloned from prod.
3. Take a backup before applying migrations.
4. Apply migrations in strict order.
5. Run verification SQL before opening API traffic.

## Step 1: Link Supabase Project

```bash
cd "/Users/vivek/Documents/smartbusinessvalue/SANCNIDA/ Development"
supabase login
supabase link --project-ref <your-project-ref>
```

## Step 2: Create Pre-Migration Backup

Option A: Use Supabase dashboard backup/snapshot.

Option B: Use `pg_dump` (recommended for explicit rollback point):

```bash
mkdir -p backend/db/backups
pg_dump \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file="backend/db/backups/pre_migration_$(date +%Y%m%d_%H%M%S).dump" \
  "postgresql://postgres:<DB_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require"
```

## Step 3: Register Migrations in Supabase Migration Folder

Supabase expects migrations under `supabase/migrations`. Copy existing SQL files with sortable timestamps:

```bash
mkdir -p supabase/migrations
cp backend/db/migrations/0001_cpq_core_schema.sql supabase/migrations/202603010001_cpq_core_schema.sql
cp backend/db/migrations/0002_tenant_rls.sql supabase/migrations/202603010002_tenant_rls.sql
cp backend/db/migrations/0003_cpq_crm_ai_extensions.sql supabase/migrations/202603010003_cpq_crm_ai_extensions.sql
cp backend/db/migrations/0004_tenant_rls_extensions.sql supabase/migrations/202603010004_tenant_rls_extensions.sql
cp backend/db/migrations/0005_supabase_rls_tenant_claims.sql supabase/migrations/202603010005_supabase_rls_tenant_claims.sql
```

## Step 4: Dry Run Locally (Strongly Recommended)

```bash
supabase start
supabase db reset
```

Expected result: all migrations apply cleanly.

## Step 5: Push to Staging First

```bash
supabase db push
```

If successful, repeat backup + push for production.

## Step 6: Post-Migration Verification

Open SQL editor in Supabase and run checks below.

### 6.1 Table Presence Check

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'tenants','users','roles','permissions',
    'commercial_items','price_books','price_book_entries',
    'quotes','quote_line_items','approval_instances','approval_steps',
    'admin_state','customer_accounts','customer_contacts','opportunities',
    'quote_templates','quote_template_versions','quote_documents',
    'ai_assistant_sessions','ai_messages','ai_recommendations'
  )
order by table_name;
```

### 6.2 RLS Enabled Check

```sql
select schemaname, tablename, rowsecurity
from pg_tables
where schemaname = 'public'
  and tablename in (
    'quotes','quote_line_items','approval_instances',
    'customer_accounts','customer_contacts',
    'quote_templates','quote_documents',
    'ai_assistant_sessions','ai_messages'
  )
order by tablename;
```

Expected: `rowsecurity = true`.

### 6.3 Policy Presence Check

```sql
select tablename, policyname
from pg_policies
where schemaname = 'public'
  and tablename in (
    'quotes','quote_line_items','approval_instances',
    'customer_accounts','customer_contacts',
    'quote_templates','quote_documents',
    'ai_assistant_sessions','ai_messages'
  )
order by tablename, policyname;
```

### 6.4 Tenant Resolver Check

```sql
select app_current_tenant();
```

Expected:
- Returns tenant UUID when request has tenant claim or `app.current_tenant` is set.
- Returns `null` without tenant context.

### 6.5 RLS Isolation Script

Run:
- `backend/db/tests/rls_verification.sql`

## Step 7: Seed Minimal Reference Data

`0001` already seeds reference code sets (`ref_item_types`, `ref_pricing_models`, etc.).  
After migration, seed one tenant + admin user + base role mappings via your app bootstrap or SQL seed script.

## Step 8: App Configuration for Supabase

Backend env:

```bash
APP_CPQ_STORE_BACKEND=postgres
APP_ADMIN_STORE_BACKEND=postgres
APP_DATABASE_URL=postgresql://postgres:<DB_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require
```

Ensure API tokens/JWT include `tenant_id` claim for RLS paths.

## Step 9: Smoke Tests (API Level)

1. Create tenant-scoped user.
2. Create commercial item + price book + price book entry.
3. Create quote + line item + price preview.
4. Submit approval + action.
5. Create customer account/contact + bind quote recipient.
6. Create quote template + version + document record.
7. Insert AI recommendation row and fetch by tenant.

## Rollback Plan

1. Stop API writes.
2. Restore from `pg_dump` backup:

```bash
pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  --dbname="postgresql://postgres:<DB_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require" \
  backend/db/backups/<backup-file>.dump
```

3. Re-run verification queries.
4. Resume traffic.

## Common Failure Modes

1. `policy violation` on insert/select:
   - Tenant context not set in JWT claim or session.
2. `relation already exists`:
   - Migration files applied manually before `supabase db push`; reconcile migration history.
3. `function app_current_tenant already exists with incompatible signature`:
   - Ensure `0002` then `0005` order.
4. Cross-environment drift:
   - Run `supabase db diff` and commit generated drift migrations.
