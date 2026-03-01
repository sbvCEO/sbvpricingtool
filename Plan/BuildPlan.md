## 0) Design Principles & Assumptions
1. **Tenant-safe by default**: every write/read path is tenant-scoped and authorization-enforced server-side.
2. **Deterministic core, AI assistive edge**: quote totals are always produced by deterministic rules; AI proposes, never silently overrides.
3. **Metadata-driven UX + engine**: product config, forms, rules, workflows, and validation are schema-driven to reduce code forks.
4. **Evented architecture with transactional boundaries**: synchronous APIs for user-critical paths; asynchronous pipelines for heavy/long-running work.
5. **Auditability everywhere**: immutable event/audit trails for pricing, approvals, and policy decisions.

---

## 1) System Architecture (Logical, Text Diagram)

**Client Layer**
- Next.js app (SSR + SPA islands), role-aware UI.
- Schema-driven form renderer for product/quote configuration.
- Realtime quote recalculation via WebSocket/SSE status updates.

**API & Orchestration Layer**
- FastAPI Gateway/BFF:
  - AuthN/AuthZ, tenant context resolution.
  - Request validation, idempotency, rate limiting.
  - Aggregation endpoints for UI workflows.
- Domain services (modular monolith first, microservices-ready boundaries):
  - Catalog Service
  - Price Book Service
  - Pricing Engine Service
  - Rules Service
  - Quote Service
  - Approval Workflow Service
  - Analytics Query Service
  - Audit & Compliance Service
  - AI Assist Service

**Data & Async Layer**
- PostgreSQL (Supabase): OLTP source of truth.
- Redis: cache, distributed locks, Celery broker (or RabbitMQ if strict delivery control preferred).
- Celery workers:
  - `calc` queue: heavy recalculations/simulations
  - `workflow` queue: SLA timers/escalations
  - `integration` queue: CRM/ERP sync
  - `ai` queue: inference/batch scoring
  - `analytics` queue: materialization jobs
- Event bus (Postgres outbox -> worker consumers; optional Kafka later at scale).

**Observability & Ops**
- OpenTelemetry traces + metrics + structured logs.
- SLOs, alerting, dead letter queue monitoring, task lag dashboards.

**Request-response vs event flows**
- **Sync**: create quote, add line item, preview pricing, submit approval.
- **Async events**: `quote.submitted`, `approval.timeout`, `pricebook.published`, `quote.finalized`, `risk.scored`.

---

## 2) Multi-Tenant Strategy

## Isolation model
1. **Primary model (recommended)**: shared DB, shared schema, strict tenant_id on all tenant-owned tables + PostgreSQL RLS.
2. **Premium isolation option**: dedicated schema or DB per tenant tier for regulated/large customers.
3. **Encryption strategy**: per-tenant key envelope for sensitive fields (KMS-managed DEKs).

## Data partitioning
- Every tenant table includes `tenant_id UUID NOT NULL`.
- Large/high-churn tables partitioned by `tenant_id hash` and/or time (quotes, audit_events).
- Analytics tables denormalized per tenant slice.

## Tenant-aware query design
- Session context variable `app.current_tenant`.
- RLS policy: `tenant_id = current_setting('app.current_tenant')::uuid`.
- Repository layer forbids non-tenant-filtered reads.
- Cross-tenant admin endpoints isolated to platform-admin service only.

## Performance considerations
- Composite indexes start with `tenant_id`.
- Prevent “noisy neighbor” via per-tenant quotas, connection pooling controls, and queue fair scheduling.
- Optional workload classes: SMB/shared vs enterprise/dedicated worker pools.

---

## 3) Data Model (Core Entities, Fields, Relationships, Indexing)

## Core entities (normalized OLTP)
| Entity | Key Fields | Relationships | Indexing |
|---|---|---|---|
| `tenants` | `id`, `name`, `plan_tier`, `status`, `default_currency`, `timezone`, `settings_json`, `created_at` | 1:M to users, catalogs, quotes | unique(`name`), idx(`status`) |
| `organizations` | `id`, `tenant_id`, `name`, `region`, `tax_profile` | optional sub-entity for multi-org tenant | idx(`tenant_id`) |
| `users` | `id`, `tenant_id`, `email`, `name`, `status`, `auth_provider_sub`, `last_login_at` | M:N roles, approvals | unique(`tenant_id`,`email`) |
| `roles` | `id`, `tenant_id`, `name`, `scope` | M:N permissions, users | unique(`tenant_id`,`name`) |
| `permissions` | `id`, `code`, `resource`, `action` | global lookup | unique(`code`) |
| `user_roles` | `user_id`, `role_id`, `tenant_id` | bridge | unique(`tenant_id`,`user_id`,`role_id`) |
| `role_permissions` | `role_id`, `permission_id` | bridge | unique(`role_id`,`permission_id`) |
| `products` | `id`, `tenant_id`, `sku`, `name`, `type`(good/service/labor/bundle), `uom`, `active` | 1:M components, bundle items | unique(`tenant_id`,`sku`) |
| `product_components` | `id`, `tenant_id`, `product_id`, `component_type`, `default_value`, `constraints_json` | part of pricing model | idx(`tenant_id`,`product_id`) |
| `bundles` | `id`, `tenant_id`, `product_id` | bundle header (product.type=bundle) | unique(`tenant_id`,`product_id`) |
| `bundle_items` | `id`, `tenant_id`, `bundle_id`, `child_product_id`, `qty_rule`, `required` | bundle composition | idx(`tenant_id`,`bundle_id`) |
| `price_books` | `id`, `tenant_id`, `name`, `currency_scope`, `region_scope`, `status` | 1:M versions | unique(`tenant_id`,`name`) |
| `price_book_versions` | `id`, `tenant_id`, `price_book_id`, `version_no`, `effective_from`, `effective_to`, `status`, `published_by` | 1:M entries | unique(`tenant_id`,`price_book_id`,`version_no`), idx effective window |
| `price_entries` | `id`, `tenant_id`, `pb_version_id`, `product_id`, `region`, `currency`, `list_price`, `cost`, `min_price`, `max_discount_pct`, `tier_model_id` | used by pricing engine | idx(`tenant_id`,`pb_version_id`,`product_id`,`region`,`currency`) |
| `tier_models` | `id`, `tenant_id`, `name`, `metric`(qty/revenue/term), `rounding_rule` | 1:M tiers | idx(`tenant_id`) |
| `tiers` | `id`, `tenant_id`, `tier_model_id`, `min_val`, `max_val`, `price_or_discount` | tier lookup | idx(`tenant_id`,`tier_model_id`,`min_val`) |
| `rules` | `id`, `tenant_id`, `name`, `rule_type`, `priority`, `status`, `dsl_json`, `effective_from`, `effective_to`, `owner` | linked to contexts | idx(`tenant_id`,`rule_type`,`status`,`priority`) |
| `rule_bindings` | `id`, `tenant_id`, `rule_id`, `scope`(quote/line/product/customer/region), `selector_json` | targeting | idx(`tenant_id`,`rule_id`) |
| `quotes` | `id`, `tenant_id`, `quote_no`, `customer_id`, `status`, `currency`, `region`, `price_book_version_id`, `subtotal`, `discount_total`, `tax_total`, `grand_total`, `margin_pct`, `revision_no`, `valid_until`, `created_by` | 1:M lines, approvals, revisions | unique(`tenant_id`,`quote_no`), idx(`tenant_id`,`status`,`created_at`) |
| `quote_line_items` | `id`, `tenant_id`, `quote_id`, `line_no`, `product_id`, `qty`, `term`, `list_price`, `net_price`, `discount_pct`, `cost`, `margin_pct`, `config_json`, `calc_trace_id` | quote composition | unique(`tenant_id`,`quote_id`,`line_no`) |
| `quote_revisions` | `id`, `tenant_id`, `quote_id`, `revision_no`, `snapshot_json`, `change_reason`, `created_by` | immutable history | unique(`tenant_id`,`quote_id`,`revision_no`) |
| `approval_policies` | `id`, `tenant_id`, `name`, `conditions_json`, `active` | route generation | idx(`tenant_id`,`active`) |
| `approval_instances` | `id`, `tenant_id`, `quote_id`, `policy_id`, `status`, `started_at`, `completed_at`, `sla_due_at` | 1:M steps | idx(`tenant_id`,`quote_id`,`status`) |
| `approval_steps` | `id`, `tenant_id`, `approval_instance_id`, `seq`, `approver_type`, `approver_ref`, `status`, `acted_at`, `comments`, `sla_due_at` | workflow detail | idx(`tenant_id`,`approval_instance_id`,`seq`) |
| `audit_events` | `id`, `tenant_id`, `entity_type`, `entity_id`, `action`, `actor_id`, `timestamp`, `before_json`, `after_json`, `request_id`, `ip` | immutable | idx(`tenant_id`,`entity_type`,`entity_id`,`timestamp`) |
| `outbox_events` | `id`, `tenant_id`, `event_type`, `payload_json`, `status`, `created_at`, `published_at` | async dispatch | idx(`status`,`created_at`) |

## Normalization strategy
- 3NF for transactional correctness.
- JSONB only for extensible metadata (`config_json`, `dsl_json`, selectors, snapshots).
- Derived totals persisted in quotes/lines for reporting speed; recalculable from traces.

---

## 4) Pricing Engine Design

## Calculation pipeline
1. Resolve context: tenant, customer segment, region, currency, contract terms.
2. Select active price book version by effective date and scope.
3. Expand bundles/dependencies.
4. Base price resolution (list/cost/min constraints).
5. Apply deterministic rules by ordered phases:
   - Eligibility/validation
   - Surcharges/adjustments
   - Discounts/promotions
   - Floor/ceiling guards
   - Margin guardrails
6. Tax/shipping/fees plug-ins.
7. Final rounding/precision policy.
8. Produce calculation trace (explainability artifact) and hash for idempotency.

## Rule order & determinism
- Strict phase ordering + priority numeric + stable tie-breaker (`rule_id`).
- Pure function semantics for core calculations.
- Deterministic seed when stochastic AI suggestions are used for recommendation mode.

## Extensibility
- Rule DSL with typed operators.
- Registered function library (`if`, `in_segment`, `tier_price`, `fx_rate`, `margin`).
- Controlled custom functions via tenant plug-in sandbox (WASM or vetted Python callable registry).

## Performance
- Precompiled rule plans cached by `(tenant, rule_set_version)`.
- Hot path memoization for repeated line contexts.
- Vectorized evaluation for large quotes.
- Async precompute for commonly used bundles and tier tables.

---

## 5) Rules Engine Design

## Rule types
1. Pricing adjustment rules.
2. Product compatibility/dependency rules.
3. Validation/blocking rules.
4. Approval trigger rules.
5. Alerting/anomaly threshold rules.

## Execution model
- Rules compiled from DSL JSON to AST to executable plan.
- Stateless evaluator for quote context + line context.
- Partial evaluation supported for “preview” during form edits.

## Storage representation
- `dsl_json` schema example: `when`, `then`, `priority`, `phase`, `effective_window`, `version`, `test_cases`.
- Versioned rules; publish creates immutable version snapshot.

## Conflict resolution
- Strategy per rule type:
  - additive (sum),
  - winner-takes-highest-priority,
  - restrictive override (safety floors/ceilings always last).
- Conflict logs attached to calc trace for admin debugging.

## Safety & validation
- Static linting before publish: type checks, circular dependency detection, unreachable clauses.
- Rule simulation suite against golden quotes.
- Canary activation by tenant subset or user group.

---

## 6) Approval Workflow Engine

## State machine
- `NOT_REQUIRED -> PENDING -> IN_REVIEW -> APPROVED | REJECTED | EXPIRED | CANCELLED`.
- Quote state transitions gated by approval state.

## Dynamic routing
- Policy evaluation on submission builds step graph:
  - sequential steps,
  - parallel branches,
  - conditional escalations.
- Approver resolution by role, manager chain, or named users.

## SLA logic
- Per-step `sla_due_at`.
- Celery scheduled tasks for reminders/escalation/auto-expire.
- Business calendar support (skip weekends/holidays).

## Failure handling
- Idempotent step actions with action tokens.
- Retry transient notification failures.
- DLQ for repeated task failures; operator replay tooling.

## Auditability
- Every action writes immutable `approval_events`.
- Full trail: who, when, before/after status, comment, reason code.

---

## 7) API Design (FastAPI)

## Resource principles
- RESTful resources with explicit workflow endpoints for commands.
- Tenant derived from token + enforced server-side.
- JSON:API-like pagination/filter/sort conventions.

## Key endpoints
1. `POST /v1/quotes` create draft.
2. `POST /v1/quotes/{id}/line-items` add/update lines.
3. `POST /v1/quotes/{id}/price-preview` deterministic calculation preview.
4. `POST /v1/quotes/{id}/submit` trigger approvals.
5. `POST /v1/approvals/{id}/actions` approve/reject/delegate.
6. `GET /v1/price-books`, `POST /v1/price-books`, `POST /v1/price-books/{id}/publish`.
7. `GET /v1/rules`, `POST /v1/rules`, `POST /v1/rules/{id}/validate`, `POST /v1/rules/{id}/publish`.
8. `GET /v1/analytics/*` curated dashboards.
9. `POST /v1/ai/pricing-suggestions`, `POST /v1/ai/quote-risk`.
10. `GET /v1/audit-events`.

## AuthN/AuthZ
- OIDC/SAML SSO + JWT access tokens.
- Claims: `sub`, `tenant_id`, `roles`, `scopes`.
- ABAC overlay for record-level permissions (region, business unit).

## Idempotency & validation
- `Idempotency-Key` required on create/submit endpoints.
- Pydantic schema validation + domain validation + rule validation.
- Optimistic concurrency with `version`/`etag`.

## Versioning
- URI major version (`/v1`), backward-compatible additive changes.
- Deprecation headers and migration window policy.

---

## 8) Async & Task Architecture (Celery)

## What runs async
- Approval reminders/escalations.
- Quote document/PDF generation.
- CRM/ERP sync.
- AI scoring/suggestions.
- Analytics aggregates/materialized views refresh.
- Bulk imports (catalog, price books).

## Queue structure
- Dedicated queues: `critical`, `workflow`, `integration`, `ai`, `analytics`.
- Priority lanes inside queue where broker supports it.
- Worker autoscaling by queue lag and p95 runtime.

## Retry strategy
- Exponential backoff + jitter.
- Retry only transient classes; poison messages to DLQ.
- Idempotent task handlers using task keys + state table.

## Race condition avoidance
- Quote-level distributed lock during finalize/submit.
- DB row locking (`SELECT FOR UPDATE`) on mutable quote/approval rows.
- Outbox pattern ensures event emission after commit.

---

## 9) AI-Native Capabilities

## Feature set
1. Smart price recommendation (target win-rate vs margin objective).
2. Discount optimization with policy constraints.
3. Quote risk scoring (approval delay risk, margin leakage, churn risk).
4. Anomaly detection (outlier discount, unusual bundle pattern).
5. NL quote assistant (convert natural language to draft quote config).
6. Explainable pricing narrative (human-readable calc rationale).

## Architecture placement
- AI Assist Service consumes feature views from OLTP + analytics store.
- Inference async by default; sync for low-latency assist endpoints with fallback.
- Model registry, feature store, and inference logging for drift monitoring.

## Governance
- AI output tagged as `suggestion`.
- Mandatory deterministic validation before accept.
- Human-in-the-loop acceptance recorded in audit.

---

## 10) Security & Enterprise Concerns

1. RLS + tenant-scoped service claims.
2. RBAC + optional ABAC constraints.
3. Strong secret management (KMS/Vault), key rotation.
4. Encryption in transit (TLS 1.2+) and at rest.
5. Immutable audit logs with tamper-evident hashing chain.
6. Data retention + legal hold policies.
7. Compliance path: SOC 2 Type II baseline, GDPR controls, optional HIPAA/ISO extensions.
8. Security testing: SAST, DAST, dependency scanning, penetration tests.
9. Admin actions require step-up auth + dual control for critical config publish.

---

## 11) Scalability & Reliability

1. Stateless API pods behind load balancer, horizontal autoscaling.
2. Read replicas for analytics-heavy read paths.
3. Redis caching:
   - reference data (catalog/pricebook snapshots),
   - compiled rules,
   - quote preview cache (short TTL).
4. Database tuning:
   - partition large tables,
   - autovacuum tuning,
   - prepared statements,
   - connection pooling (PgBouncer).
5. Reliability patterns:
   - circuit breakers for downstream integrations,
   - timeout budgets,
   - graceful degradation (AI unavailable does not block quoting).
6. DR strategy:
   - PITR backups,
   - multi-AZ primary,
   - tested restore runbooks.
7. Observability:
   - trace each quote calc and approval path,
   - SLIs: quote calc latency, submit success, approval cycle time, task lag.

---

## 12) UX / Frontend Considerations

1. Schema-driven renderer for product config forms and rule-managed conditional fields.
2. Progressive disclosure for complex pricing (basic view vs advanced finance view).
3. Real-time pricing panel with line-by-line explainability and rule impact badges.
4. “Why this price?” side drawer from calc trace.
5. Approval cockpit with SLA timers, blockers, and escalation actions.
6. Enterprise needs:
   - keyboard-heavy workflows,
   - bulk edit/import,
   - accessibility (WCAG 2.1 AA),
   - localization and multi-currency formatting.

---

## 13) Extensibility & Customization

1. Plug-in points:
   - pricing adjustment function hooks,
   - external approval participant resolvers,
   - document template generators.
2. Tenant-specific logic via metadata + DSL first; code plug-ins only for edge cases.
3. Integration framework:
   - outbound events/webhooks,
   - inbound APIs for CRM/ERP sync,
   - mapping layer with retryable sync jobs.
4. Marketplace-ready connectors (Salesforce, HubSpot, SAP, NetSuite, Stripe/Billing).

---

## 14) Execution Roadmap (Implementation-Ready)

## Phase 1: MVP (12-16 weeks)
1. Multi-tenant auth/RBAC foundation, core catalog, price books, quote CRUD.
2. Deterministic pricing engine v1 (base + discounts + guardrails).
3. Single-path approval workflow with 1-2 levels.
4. Basic dashboards (quote volume, win-rate proxy, margin summary).
5. Audit log baseline and observability setup.
6. Risks: under-modeled rules complexity, performance regressions on large quotes.

## Phase 2: V1 (next 12-16 weeks)
1. Advanced rules DSL + rule tester/simulator.
2. Versioned price books with effective dating and regional/currency support.
3. Full approval routing (conditional, SLA, escalation).
4. Integration outbox + CRM sync.
5. AI assist v1: suggestion + anomaly flags (advisory only).
6. Technical priorities: calc trace explainability, caching, queue isolation.

## Phase 3: V2 (next 16-20 weeks)
1. Bundle configurator, dependency solver, advanced tier pricing.
2. AI risk scoring + discount optimization with policy constraints.
3. Analytics expansion: cohort, approval bottlenecks, leakage detection.
4. Enterprise controls: SSO/SAML, SCIM, stronger compliance tooling.
5. Technical priorities: partitioning, read replicas, model ops governance.

## Phase 4: Enterprise Maturity
1. Premium isolation options (schema/db per tenant).
2. High-availability multi-region, DR drills, strict SLO governance.
3. Plug-in marketplace and governed custom function sandbox.
4. Advanced compliance packages and tenant-managed keys.
5. Technical priorities: platform hardening, cost controls, internal developer platform.

---

## Recommended Build Sequence (Engineering)
1. Domain model + migration scaffolding.
2. Pricing engine deterministic core + trace model.
3. Quote lifecycle + approval state machine.
4. Rule DSL + validation/simulation.
5. Async pipelines + outbox + observability.
6. AI assist services on top of stable deterministic core.

### Optional Next Artifacts
1. Concrete PostgreSQL DDL starter schema.
2. FastAPI OpenAPI contract draft.
3. First 10 epics with acceptance criteria and team topology.
