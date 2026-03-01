# SANCNIDA: Smart AI-Native Cloud-Native Intelligent Deal Application
**Project Goal:** Build a multi-tenant Deal Desk for mid-market margin protection in 90 days.
**Stack:** React + FastAPI + Supabase + Railway + Antigravity IDE.

## 3-Month Roadmap

### Month 1: Infrastructure & Core CRUD (The Container)
* **Focus:** Multi-tenancy, Auth, and Deal Schema.
* **End Goal:** Reps can log in, create a deal, and save it to a tenant-isolated database.

### Month 2: The Intelligence Layer (The Brain)
* **Focus:** Pricing Engines, Smart Guardrails, and AI Analysis.
* **End Goal:** The system auto-flags low-margin deals and provides "AI Health Scores" using Gemini 3/Claude 4.5.

### Month 3: Governance & Integration (The Closer)
* **Focus:** Approval Workflows, CRM Webhooks, and PDF Export.
* **End Goal:** Managers can approve deals via dashboard/mobile; deals sync automatically with HubSpot/Salesforce.

## Success Metrics for MVP
1. Zero data leakage between tenants (verified by RLS).
2. Deal creation to "Smart Feedback" in < 10 seconds.
3. 1-click HubSpot integration capability.