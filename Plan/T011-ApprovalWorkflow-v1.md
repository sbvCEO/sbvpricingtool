# T011 Deliverable: Approval Workflow v1

Implemented:
- Quote submission endpoint with auto-routing of 1-2 levels.
- Approval action endpoint (`APPROVE` / `REJECT`).
- SLA timestamp per step.
- Quote state updates based on approval result.

Key files:
- `backend/app/routers/approvals.py`
- `backend/app/store.py`
- `backend/tests/test_quote_pricing_workflow.py`
