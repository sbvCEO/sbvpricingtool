# T008 Deliverable: Deterministic Pricing Engine v1

Implemented:
- Deterministic line pricing against price book entries.
- Discount cap (`max_discount_pct`) and floor enforcement (`min_price`).
- Aggregate totals and margin calculation.

Key files:
- `backend/app/pricing.py`
- `backend/app/routers/quotes.py`
- `backend/tests/test_quote_pricing_workflow.py`
