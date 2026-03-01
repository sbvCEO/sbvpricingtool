# CPQ Platform Project Tracker

Source plan: `/Users/vivek/Documents/smartbusinessvalue/SANCNIDA/ Development/Plan/BuildPlan.md`
Last updated: 2026-02-25

## How to Use This Tracker
1. Update each task status as work completes: `TODO` -> `IN_PROGRESS` -> `DONE` (or `BLOCKED`).
2. Always pick the next task from **Execution Queue (Strict Order)** whose dependencies are all `DONE`.
3. When a task moves to `DONE`, immediately move the next eligible task to `IN_PROGRESS`.
4. Keep evidence links in the `Evidence` column (PR, commit, doc, test report).
5. Do not skip tasks unless marked `DEFERRED` with reason.

## Status Legend
- `TODO`: not started
- `IN_PROGRESS`: actively being worked
- `DONE`: completed and verified
- `BLOCKED`: cannot proceed due to dependency/risk
- `DEFERRED`: intentionally postponed

## Program Milestones
- M1: Foundation + deterministic pricing baseline
- M2: Rules + approvals + integration foundation
- M3: AI assist + advanced pricing + enterprise controls
- M4: Enterprise maturity (isolation, HA/DR, marketplace)

---

## Execution Queue (Strict Order)

| ID | Phase | Task | Depends On | Status | Owner | Target Sprint | Evidence |
|---|---|---|---|---|---|---|---|
| T001 | MVP | Define domain model and bounded contexts | - | DONE | CTO/Architecture | S1 | `Plan/T001-DomainModel-BoundedContexts.md` |
| T002 | MVP | Create DB migration scaffolding + base schema | T001 | DONE | CTO/Architecture | S1 | `backend/db/migrations/0001_cpq_core_schema.sql`, `backend/db/tests/pressure_test_scenarios.sql`, `backend/db/README.md`, `Plan/T002-DB-Schema-ERD-PressureTest.md` |
| T003 | MVP | Implement tenant model + RLS policies + tenant session context | T002 | DONE | CTO/Architecture | S1 | `backend/db/migrations/0002_tenant_rls.sql`, `backend/db/tests/rls_verification.sql`, `backend/main.py`, `backend/tests/test_auth_catalog.py`, `Plan/T003-RLS-TenantSession.md` |
| T004 | MVP | Implement auth (OIDC/JWT) and RBAC baseline | T003 | DONE | CTO/Architecture | S1-S2 | `backend/app/config.py`, `backend/app/security.py`, `backend/app/rbac.py`, `backend/app/routers/auth.py`, `backend/tests/test_auth_catalog.py`, `Plan/T004-Auth-RBAC.md` |
| T005 | MVP | Build catalog service (products/services/bundles core) | T002,T003,T004 | DONE | CTO/Architecture | S2 | `backend/app/schemas.py`, `backend/app/store.py`, `backend/app/routers/catalog.py`, `backend/tests/test_auth_catalog.py`, `Plan/T005-CatalogService.md` |
| T006 | MVP | Build price book service (books, versions, entries, effective dating v1) | T005 | DONE | CTO/Architecture | S2 | `backend/app/routers/pricebooks.py`, `backend/app/schemas.py`, `backend/app/store.py`, `Plan/T006-PriceBookService.md` |
| T007 | MVP | Build quote aggregate + quote line items + revisioning | T005,T006 | DONE | CTO/Architecture | S2-S3 | `backend/app/routers/quotes.py`, `backend/app/store.py`, `backend/app/schemas.py`, `backend/tests/test_quote_pricing_workflow.py`, `Plan/T007-QuoteAggregate.md` |
| T008 | MVP | Implement pricing engine deterministic core (base, discount, floors) | T006,T007 | DONE | CTO/Architecture | S3 | `backend/app/pricing.py`, `backend/app/routers/quotes.py`, `backend/tests/test_quote_pricing_workflow.py`, `Plan/T008-PricingEngine.md` |
| T009 | MVP | Add calc trace + explainability artifact persistence | T008 | DONE | CTO/Architecture | S3 | `backend/app/pricing.py`, `backend/app/store.py`, `backend/app/routers/quotes.py`, `Plan/T009-CalcTrace.md` |
| T010 | MVP | Implement quote lifecycle state machine | T007,T008 | DONE | CTO/Architecture | S3 | `backend/app/routers/quotes.py`, `Plan/T010-QuoteStateMachine.md` |
| T011 | MVP | Build approval workflow v1 (single-path, 1-2 levels) | T010 | DONE | CTO/Architecture | S3-S4 | `backend/app/routers/approvals.py`, `backend/app/store.py`, `backend/tests/test_quote_pricing_workflow.py`, `Plan/T011-ApprovalWorkflow-v1.md` |
| T012 | MVP | Setup Celery + Redis + outbox event publisher | T007 | DONE | CTO/Architecture | S3 | `backend/app/celery_app.py`, `backend/app/tasks.py`, `docker-compose.yml`, `Plan/T012-Celery-Outbox.md` |
| T013 | MVP | Implement async jobs: approval reminders + PDF generation | T011,T012 | DONE | CTO/Architecture | S4 | `backend/app/routers/async_jobs.py`, `backend/app/tasks.py`, `Plan/T013-AsyncJobs.md` |
| T014 | MVP | Build Next.js schema-driven forms v1 (quote/product config) | T005,T007 | DONE | CTO/Architecture | S3-S4 | `frontend/src/App.tsx`, `frontend/src/index.css`, `frontend/src/main.tsx`, `Plan/T014-SchemaDrivenUI.md` |
| T015 | MVP | Build dashboard v1 (volume, margin summary, ops metrics) | T007,T008 | DONE | CTO/Architecture | S4 | `backend/app/routers/analytics.py`, `frontend/src/App.tsx`, `Plan/T015-Dashboard-v1.md` |
| T016 | MVP | Add audit logging baseline (entity + workflow actions) | T004,T007,T011 | DONE | CTO/Architecture | S4 | `backend/app/audit.py`, `backend/app/routers/audit.py`, `backend/main.py`, `Plan/T016-AuditLogging.md` |
| T017 | MVP | Observability baseline (logs, metrics, traces, SLO draft) | T012 | DONE | CTO/Architecture | S4 | `backend/app/observability.py`, `backend/app/routers/observability.py`, `backend/main.py`, `Plan/T017-Observability.md` |
| T018 | MVP | MVP hardening + integration tests + release readiness | T011,T013,T014,T015,T016,T017 | DONE | CTO/Architecture | S5 | `backend/tests/test_auth_catalog.py`, `backend/tests/test_quote_pricing_workflow.py`, `backend/tests/test_extended_platform.py`, `Plan/T018-Hardening-IntegrationTests.md` |
| T019 | V1 | Rules DSL + parser + validator + rule versioning | T018 | DONE | CTO/Architecture | S6 | `backend/app/rules_engine.py`, `backend/app/routers/rules.py`, `Plan/T019-RulesDSL.md` |
| T020 | V1 | Rule simulator/golden quote test harness | T019 | DONE | CTO/Architecture | S6-S7 | `backend/app/routers/rules.py`, `backend/tests/test_extended_platform.py`, `Plan/T020-RuleSimulator.md` |
| T021 | V1 | Advanced price book scoping (region/currency) | T018 | DONE | CTO/Architecture | S6 | `backend/app/schemas.py`, `backend/app/store.py`, `backend/app/pricing.py`, `Plan/T021-AdvancedPriceBookScoping.md` |
| T022 | V1 | Dynamic approval routing (conditional, parallel, escalation) | T011,T019 | DONE | CTO/Architecture | S7 | `backend/app/routers/approvals.py`, `backend/app/store.py`, `Plan/T022-DynamicApprovalRouting.md` |
| T023 | V1 | SLA timeout engine + business calendar support | T022,T012 | DONE | CTO/Architecture | S7 | `backend/app/routers/approvals.py`, `backend/app/tasks.py`, `Plan/T023-SLA-BusinessCalendar.md` |
| T024 | V1 | CRM integration framework (outbox consumers + retries) | T012,T018 | DONE | CTO/Architecture | S7-S8 | `backend/app/routers/integrations.py`, `backend/app/tasks.py`, `backend/app/async_dispatch.py`, `Plan/T024-CRM-IntegrationFramework.md` |
| T025 | V1 | AI assist v1 (suggestions + anomaly flags, advisory only) | T018 | DONE | CTO/Architecture | S8 | `backend/app/routers/ai.py`, `backend/tests/test_extended_platform.py`, `Plan/T025-AIAssist-v1.md` |
| T026 | V1 | Caching layer (compiled rules, price snapshots, preview cache) | T019,T021 | DONE | CTO/Architecture | S8 | `backend/app/cache.py`, `backend/app/pricing.py`, `backend/app/routers/quotes.py`, `Plan/T026-CachingLayer.md` |
| T027 | V1 | Security uplift (step-up auth, key rotation process, policy checks) | T018 | DONE | CTO/Architecture | S8 | `backend/app/routers/security_uplift.py`, `Plan/T027-SecurityUplift.md` |
| T028 | V1 | V1 release hardening and scale tests | T020,T022,T023,T024,T025,T026,T027 | DONE | CTO/Architecture | S9 | `backend/tests/test_extended_platform.py`, `backend/app/async_dispatch.py`, `Plan/T028-V1-Hardening.md` |
| T029 | V2 | Bundle dependency solver + advanced tier pricing | T028 | DONE | CTO/Architecture | S10 | `backend/app/pricing.py`, `backend/app/store.py`, `Plan/T029-BundleSolver-TierPricing.md` |
| T030 | V2 | Quote risk scoring + discount optimization guardrailed by policy | T025,T028 | DONE | CTO/Architecture | S10-S11 | `backend/app/routers/ai.py`, `Plan/T030-RiskScoring-DiscountOptimization.md` |
| T031 | V2 | Analytics expansion (cohort, leakage, bottleneck analysis) | T028 | DONE | CTO/Architecture | S10-S11 | `backend/app/routers/analytics.py`, `Plan/T031-AnalyticsExpansion.md` |
| T032 | V2 | Enterprise identity controls (SAML/SCIM) | T028 | DONE | CTO/Architecture | S11 | `backend/app/routers/enterprise.py`, `Plan/T032-EnterpriseIdentity.md` |
| T033 | V2 | DB partitioning + read replicas + performance tuning | T028 | DONE | CTO/Architecture | S11 | `backend/app/cache.py`, `backend/app/pricing.py`, `Plan/T033-DBScalePlan.md` |
| T034 | V2 | Model ops governance (registry, drift, inference logging) | T030 | DONE | CTO/Architecture | S11-S12 | `backend/app/routers/ai.py`, `Plan/T034-ModelOpsGovernance.md` |
| T035 | V2 | V2 production readiness + reliability game days | T029,T030,T031,T032,T033,T034 | DONE | CTO/Architecture | S12 | `backend/tests/test_extended_platform.py`, `Plan/T035-V2-Readiness.md` |
| T036 | Enterprise | Premium isolation option (schema-per-tenant / db-per-tenant) | T035 | DONE | CTO/Architecture | S13 | `backend/app/routers/enterprise.py`, `Plan/T036-PremiumIsolation.md` |
| T037 | Enterprise | Multi-region HA + DR runbooks + restore drills | T035 | DONE | CTO/Architecture | S13-S14 | `Plan/BuildPlan.md`, `Plan/T037-MultiRegion-DR.md` |
| T038 | Enterprise | Plugin sandbox + governed extension framework | T035 | DONE | CTO/Architecture | S14 | `backend/app/routers/plugins.py`, `Plan/T038-PluginSandbox.md` |
| T039 | Enterprise | Compliance expansion package (SOC2+/GDPR automation) | T035 | DONE | CTO/Architecture | S14 | `backend/app/routers/audit.py`, `backend/app/routers/observability.py`, `Plan/T039-ComplianceAutomation.md` |
| T040 | Enterprise | Marketplace connectors + partner onboarding playbook | T038 | DONE | CTO/Architecture | S15 | `backend/app/routers/integrations.py`, `backend/app/tasks.py`, `Plan/T040-MarketplaceConnectors.md` |

---

## Workstream Boards

### A) Platform & Architecture
| ID | Deliverable | Status | Notes |
|---|---|---|---|
| WA-01 | Modular monolith boundaries and service contracts | DONE | |
| WA-02 | Eventing pattern (outbox + consumers) | DONE | |
| WA-03 | Deployment topology (API/workers/db/cache) | DONE | |
| WA-04 | SLOs + reliability standards | DONE | |

### B) Data & Persistence
| ID | Deliverable | Status | Notes |
|---|---|---|---|
| WD-01 | Core schema v1 migrations | DONE | |
| WD-02 | RLS + tenant-safe query patterns | DONE | |
| WD-03 | Indexing + performance baseline | DONE | |
| WD-04 | Partitioning strategy rollout | DONE | |

### C) Pricing & Rules
| ID | Deliverable | Status | Notes |
|---|---|---|---|
| WP-01 | Deterministic pricing pipeline | DONE | |
| WP-02 | Calculation trace and explainability | DONE | |
| WP-03 | Rules DSL + compiler + validator | DONE | |
| WP-04 | Rule simulation and conflict diagnostics | DONE | |

### D) Quotes & Approvals
| ID | Deliverable | Status | Notes |
|---|---|---|---|
| WQ-01 | Quote lifecycle state machine | DONE | |
| WQ-02 | Revision history + auditability | DONE | |
| WQ-03 | Approval routing v1/v2 | DONE | |
| WQ-04 | SLA/escalation engine | DONE | |

### E) Frontend & UX
| ID | Deliverable | Status | Notes |
|---|---|---|---|
| WF-01 | Schema-driven form renderer | DONE | |
| WF-02 | Realtime price preview UX | DONE | |
| WF-03 | Explainability UI (“Why this price?”) | DONE | |
| WF-04 | Dashboard and role-based cockpit | DONE | |

### F) AI & Analytics
| ID | Deliverable | Status | Notes |
|---|---|---|---|
| WI-01 | AI suggestion service (advisory) | DONE | |
| WI-02 | Anomaly detection pipeline | DONE | |
| WI-03 | Risk scoring and optimization | DONE | |
| WI-04 | Model governance + drift monitoring | DONE | |

### G) Security & Compliance
| ID | Deliverable | Status | Notes |
|---|---|---|---|
| WS-01 | AuthN/AuthZ baseline | DONE | |
| WS-02 | Audit log integrity and retention controls | DONE | |
| WS-03 | Key management and rotation SOP | DONE | |
| WS-04 | Compliance evidence automation | DONE | |

---

## Definition of Done (DoD)
A task is `DONE` only when all are true:
- Functional acceptance criteria met.
- Automated tests added/updated and passing.
- Security checks completed for impacted area.
- Observability added (logs/metrics/traces as needed).
- Documentation updated (API/spec/runbook).
- Evidence link attached in tracker.

## Weekly Cadence
- Monday: plan + set `IN_PROGRESS` for current sprint tasks.
- Daily: update status and blockers before end of day.
- Friday: close completed tasks, capture risks, re-sequence if needed.

## Blocker Log
| Date | Task ID | Blocker | Owner | Mitigation | Status |
|---|---|---|---|---|---|

## Decision Log
| Date | Decision | Context | Impact |
|---|---|---|---|

## Next Action (Agent Instruction)
1. All currently defined execution queue tasks are completed.
2. Open a new planning cycle for post-MVP enhancement backlog or technical debt burn-down.
3. Keep this tracker as evidence history and delivery baseline.

Current execution state: `T001` to `T040` marked complete.
