from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from app.cache import get_cache, set_cache
from app.store import catalog_store
from app.store import price_book_store, quote_store


def price_quote(tenant_id: UUID, quote_id: UUID) -> dict:
    quote = quote_store.get_quote(tenant_id, quote_id)
    if not quote:
        raise KeyError("Quote not found")

    lines = quote_store.list_lines(tenant_id, quote_id)
    cache_key = f"price-preview:{tenant_id}:{quote_id}:{quote.get('revision_no', 1)}:{len(lines)}"
    cached = get_cache(cache_key)
    if cached:
        return cached
    subtotal = 0.0
    discount_total = 0.0
    grand_total = 0.0
    list_total = 0.0
    line_breakdown: list[dict] = []
    pricing_explanations: list[dict] = []
    rule_impact: dict[str, float] = {
        "Volume Pricing": 0.0,
        "Discount Policy": 0.0,
        "Price Floor": 0.0,
        "Bundle Dependency": 0.0,
        "Regional Modifier": 0.0,
    }

    price_book = price_book_store.get_book(tenant_id, quote["price_book_id"])
    price_book_name = price_book.get("name") if price_book else str(quote["price_book_id"])

    for line in lines:
        previous_unit_price = float(line.get("unit_price") or 0.0)
        previous_net_price = float(line.get("net_price") or 0.0)
        item = catalog_store.get_item(tenant_id, line["commercial_item_id"])
        if not item:
            raise ValueError(f"Commercial item missing for line {line['line_no']}")

        bundle_dependency_impact = 0.0
        if item["item_type"] == "BUNDLE":
            required_links = [
                link
                for link in catalog_store.list_bundle_links_for_bundle(tenant_id, item["id"])
                if link["bundle_item_id"] == item["id"] and link["inclusion_type"] == "REQUIRED"
            ]
            quoted_item_ids = {ln["commercial_item_id"] for ln in lines}
            for link in required_links:
                if link["child_item_id"] not in quoted_item_ids:
                    raise ValueError(f"Bundle dependency missing on line {line['line_no']}")
            bundle_dependency_impact = 0.0

        entry = price_book_store.find_entry_by_item(
            tenant_id,
            quote["price_book_id"],
            line["commercial_item_id"],
            region=quote.get("region"),
            currency=quote.get("currency"),
        )
        if not entry:
            raise ValueError(f"Missing price book entry for line {line['line_no']}")

        base_unit = float(entry.get("base_price") or 0.0)
        original_base_unit = base_unit
        quantity = float(line.get("quantity") or 1)
        tier_adjustment = 0.0

        if entry.get("pricing_model") == "TIERED":
            tiers = (entry.get("metadata_json") or {}).get("tiers", [])
            tier_base = base_unit
            for tier in tiers:
                lower = float(tier.get("min", 0))
                upper = tier.get("max")
                upper_ok = upper is None or quantity <= float(upper)
                if quantity >= lower and upper_ok:
                    base_unit = float(tier.get("price", base_unit))
                    break
            tier_adjustment = (base_unit - tier_base) * quantity

        requested_discount = float(line.get("discount_pct") or 0.0)
        requested_discount_before_cap = requested_discount
        max_discount = entry.get("max_discount_pct")
        if max_discount is not None:
            requested_discount = min(requested_discount, float(max_discount))

        min_price = entry.get("min_price")
        discounted_unit = base_unit * (1 - (requested_discount / 100.0))
        price_floor_impact = 0.0
        if min_price is not None:
            pre_floor = discounted_unit
            discounted_unit = max(discounted_unit, float(min_price))
            price_floor_impact = (discounted_unit - pre_floor) * quantity

        line_list_total = base_unit * quantity
        line_net_total = discounted_unit * quantity
        discount_amount = max(line_list_total - line_net_total, 0.0)
        discount_policy_impact = -discount_amount

        subtotal += line_list_total
        grand_total += line_net_total
        discount_total += discount_amount
        list_total += line_list_total

        line["list_price"] = round(base_unit, 6)
        line["unit_price"] = round(discounted_unit, 6)
        line["net_price"] = round(line_net_total, 6)
        line["pricing_snapshot_json"] = {
            "base_unit": base_unit,
            "applied_discount_pct": requested_discount,
            "min_price": min_price,
            "pricing_model": entry["pricing_model"],
        }

        line_breakdown.append(
            {
                "line_id": str(line["id"]),
                "line_no": line["line_no"],
                "commercial_item_id": str(line["commercial_item_id"]),
                "quantity": quantity,
                "base_unit": round(base_unit, 6),
                "applied_discount_pct": round(requested_discount, 6),
                "net_total": round(line_net_total, 6),
            }
        )

        warnings: list[dict] = []
        if max_discount is not None and requested_discount_before_cap > float(max_discount):
            warnings.append(
                {
                    "code": "DISCOUNT_CAPPED",
                    "message": f"Requested discount {requested_discount_before_cap:.2f}% capped at {float(max_discount):.2f}%.",
                    "severity": "WARNING",
                }
            )
        if min_price is not None and price_floor_impact > 0:
            warnings.append(
                {
                    "code": "MIN_PRICE_FLOOR",
                    "message": f"Minimum unit price floor {float(min_price):.2f} applied.",
                    "severity": "WARNING",
                }
            )

        calculation_breakdown = [
            {"label": "Base Price", "operator": "=", "amount": round(original_base_unit * quantity, 6)},
            {"label": "Volume Adjustment", "operator": "+" if tier_adjustment >= 0 else "-", "amount": round(abs(tier_adjustment), 6)},
            {"label": "Bundle Dependency Impact", "operator": "+" if bundle_dependency_impact >= 0 else "-", "amount": round(abs(bundle_dependency_impact), 6)},
            {"label": "Subtotal", "operator": "=", "amount": round((original_base_unit * quantity) + tier_adjustment + bundle_dependency_impact, 6)},
            {"label": "Discount Applied", "operator": "-", "amount": round(discount_amount, 6)},
            {"label": "Price Floor Impact", "operator": "+" if price_floor_impact >= 0 else "-", "amount": round(abs(price_floor_impact), 6)},
            {"label": "Final Net Price", "operator": "=", "amount": round(line_net_total, 6)},
        ]

        rules_applied = [
            {
                "name": "Volume Tier Pricing Applied",
                "trigger_condition": f"pricing_model={entry.get('pricing_model')}, quantity={quantity}",
                "impact_amount": round(tier_adjustment, 6),
                "source": "System",
                "statement": "Quantity matched active tier threshold.",
            },
            {
                "name": "Discount Policy Applied",
                "trigger_condition": f"requested_discount={requested_discount_before_cap}",
                "impact_amount": round(discount_policy_impact, 6),
                "source": "System",
                "statement": "Discount constrained by policy and price floor.",
            },
            {
                "name": "Bundle Dependency Adjustment",
                "trigger_condition": f"item_type={item['item_type']}",
                "impact_amount": round(bundle_dependency_impact, 6),
                "source": "System",
                "statement": "Bundle composition validated before pricing.",
            },
        ]

        discounts = [
            {
                "type": "System Discount",
                "percent": round(requested_discount, 6),
                "amount": round(discount_amount, 6),
                "applied_by": "Pricing Engine",
                "justification": "Price book and policy-driven discount.",
                "approval_impact": "May trigger approval depending on margin and threshold.",
            },
            {
                "type": "Manual Discount",
                "percent": round(requested_discount_before_cap, 6),
                "amount": round((base_unit * quantity) * (requested_discount_before_cap / 100.0), 6),
                "applied_by": "Quote User",
                "justification": "User-entered discount request.",
                "approval_impact": "Higher manual discount increases approval likelihood.",
            },
        ]

        pricing_explanations.append(
            {
                "line_id": str(line["id"]),
                "line_no": line["line_no"],
                "item_summary": {
                    "item_name": item["name"],
                    "item_type": item["item_type"],
                    "pricing_model": entry.get("pricing_model"),
                    "price_book_source": price_book_name,
                    "currency": quote.get("currency"),
                    "quantity": quantity,
                    "quantity_impact_notice": "Tier thresholds may change with quantity changes."
                    if entry.get("pricing_model") == "TIERED"
                    else "Quantity scales line total linearly.",
                },
                "calculation_breakdown": calculation_breakdown,
                "rules_applied": rules_applied,
                "discounts_overrides": discounts,
                "warnings": warnings,
                "delta": {
                    "previous_unit_price": round(previous_unit_price, 6),
                    "current_unit_price": round(discounted_unit, 6),
                    "previous_net_price": round(previous_net_price, 6),
                    "current_net_price": round(line_net_total, 6),
                    "reason": "Quantity/discount or rule impact changed computed totals.",
                },
                "simulation_seed": {
                    "base_unit": round(base_unit, 6),
                    "max_discount_pct": max_discount,
                    "min_price": min_price,
                    "tiers": (entry.get("metadata_json") or {}).get("tiers", []),
                },
                "audit_metadata": {
                    "price_book_version": price_book_name,
                    "calculation_timestamp": datetime.now(UTC).isoformat(),
                    "pricing_engine_version": "v1-deterministic",
                    "last_modified_by": "pricing-engine",
                    "recalculation_triggers": ["LINE_CHANGE", "PRICE_PREVIEW"],
                },
            }
        )

        rule_impact["Volume Pricing"] += abs(tier_adjustment)
        rule_impact["Discount Policy"] += abs(discount_policy_impact)
        rule_impact["Price Floor"] += abs(price_floor_impact)
        rule_impact["Bundle Dependency"] += abs(bundle_dependency_impact)

    quote["subtotal"] = round(subtotal, 6)
    quote["discount_total"] = round(discount_total, 6)
    quote["grand_total"] = round(grand_total, 6)
    quote["surcharge_total"] = 0.0
    quote["tax_total"] = 0.0
    quote["margin_pct"] = round(((grand_total * 0.28) / grand_total) * 100.0, 4) if grand_total > 0 else 0.0

    trace_payload = {
        "engine_version": "v1-deterministic",
        "rule_set_version": "baseline",
        "execution_mode": "PREVIEW",
        "line_breakdown": line_breakdown,
        "pricing_explanations": pricing_explanations,
        "totals": {
            "subtotal": quote["subtotal"],
            "discount_total": quote["discount_total"],
            "grand_total": quote["grand_total"],
        },
        "input_hash": sha256(f"{tenant_id}:{quote_id}:{len(lines)}".encode("utf-8")).hexdigest(),
    }
    trace_payload["output_hash"] = sha256(str(trace_payload["totals"]).encode("utf-8")).hexdigest()
    trace = quote_store.save_trace(tenant_id, quote_id, trace_payload)

    approval_signals: list[dict] = []
    if quote["margin_pct"] < 35:
        approval_signals.append(
            {
                "code": "MARGIN_BELOW_THRESHOLD",
                "severity": "WARNING",
                "message": f"Margin below threshold (Target: 35%, Current: {quote['margin_pct']:.2f}%).",
            }
        )
    if quote["grand_total"] >= 100000:
        approval_signals.append(
            {
                "code": "FINANCE_APPROVAL_REQUIRED",
                "severity": "INFO",
                "message": "Finance Approval Required.",
            }
        )

    heatmap = [
        {"driver": key, "impact": round(value, 6)}
        for key, value in rule_impact.items()
    ]

    result = {
        "quote_id": quote_id,
        "subtotal": quote["subtotal"],
        "discount_total": quote["discount_total"],
        "grand_total": quote["grand_total"],
        "margin_pct": quote["margin_pct"],
        "line_breakdown": line_breakdown,
        "pricing_explanations": pricing_explanations,
        "approval_signals": approval_signals,
        "rule_impact_heatmap": heatmap,
        "engine_metadata": {
            "price_book_version": price_book_name,
            "calculation_timestamp": datetime.now(UTC).isoformat(),
            "pricing_engine_version": "v1-deterministic",
            "rule_set_version": "baseline",
        },
        "trace_id": trace["id"],
    }
    set_cache(cache_key, result, ttl_seconds=45)
    return result
