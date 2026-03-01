# T001 Deliverable: Domain Model & Bounded Contexts

Task ID: T001  
Status: DONE  
Date: 2026-02-25

## Objective
Define the CPQ domain model and bounded contexts to establish clear ownership, data boundaries, and integration contracts before schema implementation (T002).

## Domain Scope
In-scope domains:
- Tenant & Identity
- Product Catalog
- Price Book
- Pricing Engine
- Rules Engine
- Quote Management
- Approval Workflow
- Audit & Compliance
- Analytics
- AI Assist
- Integration

Out of scope for T001:
- Physical deployment topology details
- Concrete SQL migrations
- UI implementation specifics

## Bounded Contexts

### 1) Tenant & Identity Context
Responsibilities:
- Tenant/org setup
- User lifecycle
- Roles/permissions mapping
- Auth claims normalization

Owns aggregates:
- Tenant
- Organization
- User
- Role
- Permission

Publishes events:
- `tenant.created`
- `user.invited`
- `role.updated`

Consumes events:
- none (source-of-truth context)

### 2) Catalog Context
Responsibilities:
- Product/service/labor/bundle definition
- Product attributes and constraints
- Bundle composition

Owns aggregates:
- Product
- ProductComponent
- Bundle
- BundleItem

Publishes events:
- `product.created`
- `product.updated`
- `bundle.updated`

Consumes events:
- `tenant.created`

### 3) Price Book Context
Responsibilities:
- Price book lifecycle
- Versioning and effective date windows
- Region/currency scoped price entries
- Tier model definitions

Owns aggregates:
- PriceBook
- PriceBookVersion
- PriceEntry
- TierModel
- Tier

Publishes events:
- `pricebook.version.published`
- `priceentry.changed`

Consumes events:
- `product.updated`

### 4) Rules Context
Responsibilities:
- Rule definitions (pricing/validation/approval triggers)
- Rule versioning and lifecycle
- Rule binding to scopes
- Rule validation and simulation metadata

Owns aggregates:
- Rule
- RuleBinding
- RuleVersion

Publishes events:
- `rule.published`
- `rule.deactivated`

Consumes events:
- `pricebook.version.published`

### 5) Pricing Context
Responsibilities:
- Deterministic quote pricing calculations
- Rule application ordering
- Calculation trace generation
- Guardrail enforcement

Owns aggregates:
- PricingSession (ephemeral)
- CalculationTrace

Publishes events:
- `quote.priced`
- `quote.pricing.failed`

Consumes events:
- `rule.published`
- `pricebook.version.published`
- `quote.line.changed`

### 6) Quote Context
Responsibilities:
- Quote lifecycle state transitions
- Line item modeling
- Revision history and quote snapshots
- Submission flow trigger

Owns aggregates:
- Quote
- QuoteLineItem
- QuoteRevision

Publishes events:
- `quote.created`
- `quote.line.changed`
- `quote.submitted`
- `quote.finalized`

Consumes events:
- `quote.priced`
- `approval.completed`

### 7) Approval Context
Responsibilities:
- Approval policy definition
- Runtime approval routing and step execution
- SLA timers/escalations

Owns aggregates:
- ApprovalPolicy
- ApprovalInstance
- ApprovalStep

Publishes events:
- `approval.started`
- `approval.step.completed`
- `approval.completed`
- `approval.rejected`

Consumes events:
- `quote.submitted`

### 8) Audit & Compliance Context
Responsibilities:
- Immutable business and security audit logs
- Change history capture
- Compliance evidence retrieval

Owns aggregates:
- AuditEvent
- ComplianceEvidenceRecord

Publishes events:
- `audit.recorded`

Consumes events:
- all domain events (selectively persisted)

### 9) Analytics Context
Responsibilities:
- KPI materialization
- Operational and revenue metrics
- Anomaly and trend views

Owns aggregates:
- MetricSnapshot
- AggregateFact tables (read-side)

Publishes events:
- `analytics.snapshot.ready`

Consumes events:
- `quote.finalized`
- `approval.completed`
- `quote.priced`

### 10) AI Assist Context
Responsibilities:
- Suggestion generation (discount/pricing)
- Risk scoring
- Explainable recommendation output

Owns aggregates:
- AISuggestion
- RiskScore
- ModelInferenceLog

Publishes events:
- `ai.suggestion.generated`
- `ai.risk.scored`

Consumes events:
- `quote.priced`
- `quote.submitted`

### 11) Integration Context
Responsibilities:
- External CRM/ERP/Billing synchronization
- Outbound webhook dispatch
- Retry + idempotency

Owns aggregates:
- IntegrationEndpoint
- IntegrationJob
- ExternalSyncMap

Publishes events:
- `integration.sync.completed`
- `integration.sync.failed`

Consumes events:
- `quote.finalized`
- `pricebook.version.published`

## Aggregate Boundaries and Invariants
- Quote aggregate invariant: totals and status transition validity are enforced within Quote context.
- PriceBookVersion invariant: no overlapping effective window per scope (tenant, pricebook, currency, region).
- Rule invariant: published versions are immutable.
- Approval invariant: step state transitions must be monotonic and audit-logged.
- Tenant invariant: all tenant-owned entities must include tenant_id and pass tenant authorization checks.

## Canonical Ubiquitous Language
- Quote Draft: mutable quote before submission.
- Pricing Preview: non-final calculation execution used during configuration.
- Finalized Quote: approved and locked commercial artifact.
- Guardrail: hard constraint (min margin/max discount) that cannot be bypassed without explicit approval rule path.
- Effective Window: active validity range for price book/rule version.

## Context Interaction Pattern
- Synchronous interaction:
  - Quote -> Pricing (live preview)
  - Quote -> Approval (submit)
- Asynchronous interaction:
  - Outbox event publication from transactional contexts
  - Audit, Analytics, AI, Integration subscribe via async consumers

## Anti-Corruption Layer Requirements
- Integration context must shield core domains from external CRM/ERP model drift.
- AI suggestions must pass deterministic pricing validation before being applied.
- Rule DSL compiler isolates business expression from execution internals.

## Risks Identified at T001
1. Overlap between Rules and Pricing contexts can cause ownership ambiguity.
Mitigation: Rules owns definitions; Pricing owns execution.

2. Approval triggers can be split between Rules and Approval contexts.
Mitigation: Rules emits trigger decision; Approval owns process state and routing.

3. Multi-tenant leakage risk across analytics and async consumers.
Mitigation: mandatory tenant envelope in every event payload + consumer guard checks.

## Exit Criteria for T001
- Context boundaries defined and accepted.
- Aggregate ownership clear with invariants documented.
- Event contracts identified at context level.
- Known risks and mitigations recorded.
