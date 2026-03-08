from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.config import settings


def utcnow() -> datetime:
    return datetime.now(UTC)


def _to_float_if_decimal(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, dict):
            normalized[key] = _normalize_row(value)
        elif isinstance(value, list):
            normalized[key] = [
                _normalize_row(item) if isinstance(item, dict) else _to_float_if_decimal(item)
                for item in value
            ]
        else:
            normalized[key] = _to_float_if_decimal(value)
    return normalized


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    return value


class _PostgresSupport:
    @property
    def _use_postgres(self) -> bool:
        return settings.cpq_store_backend.lower() == "postgres" and bool(settings.database_url)

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(settings.database_url, row_factory=dict_row)

    def _ensure_tenant(self, tenant_id: UUID) -> None:
        if not self._use_postgres:
            return
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tenants (id, name, default_currency, timezone)
                    VALUES (%s, %s, 'USD', 'UTC')
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (tenant_id, f"Tenant-{tenant_id}"),
                )


@dataclass
class CatalogStore(_PostgresSupport):
    items: dict[UUID, dict[UUID, dict[str, Any]]]
    bundle_links: dict[UUID, dict[UUID, dict[str, Any]]]

    def __init__(self) -> None:
        self.items = {}
        self.bundle_links = {}

    def create_item(self, tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        if self._use_postgres:
            self._ensure_tenant(tenant_id)
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO commercial_items (
                          tenant_id, item_code, name, description, item_type, is_active, versionable, metadata_json
                        )
                        VALUES (%(tenant_id)s, %(item_code)s, %(name)s, %(description)s, %(item_type)s, %(is_active)s, %(versionable)s, %(metadata_json)s)
                        RETURNING *
                        """,
                        {
                            "tenant_id": tenant_id,
                            "item_code": payload["item_code"],
                            "name": payload["name"],
                            "description": payload.get("description"),
                            "item_type": payload["item_type"],
                            "is_active": payload.get("is_active", True),
                            "versionable": payload.get("versionable", False),
                            "metadata_json": payload.get("metadata_json") or {},
                        },
                    )
                    return _normalize_row(cur.fetchone())

        tenant_items = self.items.setdefault(tenant_id, {})
        if any(item["item_code"] == payload["item_code"] for item in tenant_items.values()):
            raise ValueError("item_code already exists for tenant")

        item_id = uuid4()
        item = {
            "id": item_id,
            "tenant_id": tenant_id,
            **payload,
        }
        tenant_items[item_id] = item
        return item

    def list_items(self, tenant_id: UUID) -> list[dict[str, Any]]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM commercial_items WHERE tenant_id = %s ORDER BY created_at DESC",
                        (tenant_id,),
                    )
                    return [_normalize_row(row) for row in cur.fetchall()]
        return list(self.items.get(tenant_id, {}).values())

    def get_item(self, tenant_id: UUID, item_id: UUID) -> dict[str, Any] | None:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM commercial_items WHERE tenant_id = %s AND id = %s",
                        (tenant_id, item_id),
                    )
                    row = cur.fetchone()
                    return _normalize_row(row) if row else None
        return self.items.get(tenant_id, {}).get(item_id)

    def link_bundle_item(self, tenant_id: UUID, bundle_item_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        if self._use_postgres:
            bundle = self.get_item(tenant_id, bundle_item_id)
            if not bundle:
                raise KeyError("Bundle item not found")
            if bundle["item_type"] != "BUNDLE":
                raise ValueError("Target item is not a BUNDLE")

            child = self.get_item(tenant_id, payload["child_item_id"])
            if not child:
                raise KeyError("Child item not found")
            if child["id"] == bundle_item_id:
                raise ValueError("Bundle cannot include itself")

            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO bundle_items (
                          tenant_id, bundle_item_id, child_item_id, inclusion_type, qty_rule_json,
                          override_price_allowed, sort_order
                        )
                        VALUES (%(tenant_id)s, %(bundle_item_id)s, %(child_item_id)s, %(inclusion_type)s,
                                %(qty_rule_json)s, %(override_price_allowed)s, %(sort_order)s)
                        RETURNING *
                        """,
                        {
                            "tenant_id": tenant_id,
                            "bundle_item_id": bundle_item_id,
                            "child_item_id": payload["child_item_id"],
                            "inclusion_type": payload.get("inclusion_type", "OPTIONAL"),
                            "qty_rule_json": payload.get("qty_rule_json") or {},
                            "override_price_allowed": payload.get("override_price_allowed", False),
                            "sort_order": payload.get("sort_order", 0),
                        },
                    )
                    return _normalize_row(cur.fetchone())

        bundle = self.get_item(tenant_id, bundle_item_id)
        if not bundle:
            raise KeyError("Bundle item not found")
        if bundle["item_type"] != "BUNDLE":
            raise ValueError("Target item is not a BUNDLE")

        child = self.get_item(tenant_id, payload["child_item_id"])
        if not child:
            raise KeyError("Child item not found")
        if child["id"] == bundle_item_id:
            raise ValueError("Bundle cannot include itself")

        tenant_links = self.bundle_links.setdefault(tenant_id, {})
        link_id = uuid4()
        link = {
            "id": link_id,
            "tenant_id": tenant_id,
            "bundle_item_id": bundle_item_id,
            **payload,
        }
        tenant_links[link_id] = link
        return link

    def list_bundle_links_for_bundle(self, tenant_id: UUID, bundle_item_id: UUID) -> list[dict[str, Any]]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT * FROM bundle_items
                        WHERE tenant_id = %s AND bundle_item_id = %s
                        ORDER BY sort_order, created_at
                        """,
                        (tenant_id, bundle_item_id),
                    )
                    return [_normalize_row(row) for row in cur.fetchall()]

        return [
            link
            for link in self.bundle_links.get(tenant_id, {}).values()
            if link["bundle_item_id"] == bundle_item_id
        ]

    def clear(self) -> None:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM bundle_items")
                    cur.execute("DELETE FROM commercial_items")
                conn.commit()
            return
        self.items.clear()
        self.bundle_links.clear()


@dataclass
class PriceBookStore(_PostgresSupport):
    books: dict[UUID, dict[UUID, dict[str, Any]]]
    entries: dict[UUID, dict[UUID, dict[str, Any]]]

    def __init__(self) -> None:
        self.books = {}
        self.entries = {}

    def _hydrate_entry(self, row: dict[str, Any]) -> dict[str, Any]:
        entry = _normalize_row(row)
        metadata = entry.get("metadata_json") or {}
        entry["region"] = metadata.get("region")
        entry["currency"] = metadata.get("currency")
        return entry

    def create_book(self, tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        if self._use_postgres:
            self._ensure_tenant(tenant_id)
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO price_books (tenant_id, name, currency, valid_from, valid_to, status, metadata_json)
                        VALUES (%(tenant_id)s, %(name)s, %(currency)s, %(valid_from)s, %(valid_to)s, 'DRAFT', %(metadata_json)s)
                        RETURNING *
                        """,
                        {
                            "tenant_id": tenant_id,
                            "name": payload["name"],
                            "currency": payload["currency"],
                            "valid_from": payload.get("valid_from"),
                            "valid_to": payload.get("valid_to"),
                            "metadata_json": payload.get("metadata_json") or {},
                        },
                    )
                    return _normalize_row(cur.fetchone())

        tenant_books = self.books.setdefault(tenant_id, {})
        book_id = uuid4()
        book = {
            "id": book_id,
            "tenant_id": tenant_id,
            "status": "DRAFT",
            **payload,
        }
        tenant_books[book_id] = book
        return book

    def list_books(self, tenant_id: UUID) -> list[dict[str, Any]]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM price_books WHERE tenant_id = %s ORDER BY created_at DESC",
                        (tenant_id,),
                    )
                    return [_normalize_row(row) for row in cur.fetchall()]
        return list(self.books.get(tenant_id, {}).values())

    def get_book(self, tenant_id: UUID, price_book_id: UUID) -> dict[str, Any] | None:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM price_books WHERE tenant_id = %s AND id = %s",
                        (tenant_id, price_book_id),
                    )
                    row = cur.fetchone()
                    return _normalize_row(row) if row else None
        return self.books.get(tenant_id, {}).get(price_book_id)

    def publish_book(self, tenant_id: UUID, price_book_id: UUID) -> dict[str, Any]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE price_books
                        SET status = 'ACTIVE', updated_at = NOW()
                        WHERE tenant_id = %s AND id = %s
                        RETURNING *
                        """,
                        (tenant_id, price_book_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise KeyError("Price book not found")
                    return _normalize_row(row)

        book = self.get_book(tenant_id, price_book_id)
        if not book:
            raise KeyError("Price book not found")
        book["status"] = "ACTIVE"
        return book

    def update_book(self, tenant_id: UUID, price_book_id: UUID, patch: dict[str, Any]) -> dict[str, Any]:
        allowed = {"name", "currency", "valid_from", "valid_to", "metadata_json", "status"}
        values = {k: v for k, v in patch.items() if k in allowed and v is not None}
        if not values:
            book = self.get_book(tenant_id, price_book_id)
            if not book:
                raise KeyError("Price book not found")
            return book

        if self._use_postgres:
            assignments = []
            params: list[Any] = []
            for key, value in values.items():
                assignments.append(f"{key} = %s")
                params.append(value)
            assignments.append("updated_at = NOW()")
            params.extend([tenant_id, price_book_id])
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        UPDATE price_books
                        SET {", ".join(assignments)}
                        WHERE tenant_id = %s AND id = %s
                        RETURNING *
                        """,
                        params,
                    )
                    row = cur.fetchone()
                    if not row:
                        raise KeyError("Price book not found")
                    return _normalize_row(row)

        book = self.get_book(tenant_id, price_book_id)
        if not book:
            raise KeyError("Price book not found")
        book.update(values)
        return book

    def delete_book(self, tenant_id: UUID, price_book_id: UUID) -> None:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM price_books WHERE tenant_id = %s AND id = %s",
                        (tenant_id, price_book_id),
                    )
                    if cur.rowcount == 0:
                        raise KeyError("Price book not found")
            return

        tenant_books = self.books.get(tenant_id, {})
        if price_book_id not in tenant_books:
            raise KeyError("Price book not found")
        del tenant_books[price_book_id]
        if tenant_id in self.entries:
            self.entries[tenant_id] = {
                entry_id: entry
                for entry_id, entry in self.entries[tenant_id].items()
                if entry["price_book_id"] != price_book_id
            }

    def create_entry(self, tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        if self._use_postgres:
            metadata = dict(payload.get("metadata_json") or {})
            if payload.get("region"):
                metadata["region"] = payload["region"]
            if payload.get("currency"):
                metadata["currency"] = payload["currency"]

            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO price_book_entries (
                          tenant_id, price_book_id, commercial_item_id, pricing_model,
                          base_price, min_qty, max_qty, min_price, max_discount_pct,
                          metadata_json
                        )
                        VALUES (
                          %(tenant_id)s, %(price_book_id)s, %(commercial_item_id)s, %(pricing_model)s,
                          %(base_price)s, %(min_qty)s, %(max_qty)s, %(min_price)s, %(max_discount_pct)s,
                          %(metadata_json)s
                        )
                        RETURNING *
                        """,
                        {
                            "tenant_id": tenant_id,
                            "price_book_id": payload["price_book_id"],
                            "commercial_item_id": payload["commercial_item_id"],
                            "pricing_model": payload["pricing_model"],
                            "base_price": payload.get("base_price"),
                            "min_qty": payload.get("min_qty"),
                            "max_qty": payload.get("max_qty"),
                            "min_price": payload.get("min_price"),
                            "max_discount_pct": payload.get("max_discount_pct"),
                            "metadata_json": metadata,
                        },
                    )
                    return self._hydrate_entry(cur.fetchone())

        tenant_entries = self.entries.setdefault(tenant_id, {})
        entry_id = uuid4()
        entry = {
            "id": entry_id,
            "tenant_id": tenant_id,
            "region": payload.get("region"),
            "currency": payload.get("currency"),
            **payload,
        }
        tenant_entries[entry_id] = entry
        return entry

    def list_entries(self, tenant_id: UUID, price_book_id: UUID) -> list[dict[str, Any]]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT * FROM price_book_entries
                        WHERE tenant_id = %s AND price_book_id = %s
                        ORDER BY created_at DESC
                        """,
                        (tenant_id, price_book_id),
                    )
                    return [self._hydrate_entry(row) for row in cur.fetchall()]

        return [
            entry
            for entry in self.entries.get(tenant_id, {}).values()
            if entry["price_book_id"] == price_book_id
        ]

    def find_entry_by_item(
        self,
        tenant_id: UUID,
        price_book_id: UUID,
        commercial_item_id: UUID,
        region: str | None = None,
        currency: str | None = None,
    ) -> dict[str, Any] | None:
        candidates = [
            entry
            for entry in self.list_entries(tenant_id, price_book_id)
            if entry["commercial_item_id"] == commercial_item_id
        ]
        for entry in candidates:
            region_ok = entry.get("region") in (None, "", region)
            currency_ok = entry.get("currency") in (None, "", currency)
            if region_ok and currency_ok:
                return entry
        return candidates[0] if candidates else None

    def clear(self) -> None:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM pricing_components")
                    cur.execute("DELETE FROM pricing_tiers")
                    cur.execute("DELETE FROM price_book_entries")
                    cur.execute("DELETE FROM price_books")
                conn.commit()
            return
        self.books.clear()
        self.entries.clear()


@dataclass
class QuoteStore(_PostgresSupport):
    quotes: dict[UUID, dict[UUID, dict[str, Any]]]
    lines: dict[UUID, dict[UUID, dict[str, dict[UUID, dict[str, Any]]]]]
    revisions: dict[UUID, dict[UUID, list[dict[str, Any]]]]
    traces: dict[UUID, list[dict[str, Any]]]
    approvals: dict[UUID, dict[UUID, dict[str, Any]]]
    outbox: dict[UUID, list[dict[str, Any]]]
    approval_policies: dict[UUID, list[dict[str, Any]]]

    def __init__(self) -> None:
        self.quotes = {}
        self.lines = {}
        self.revisions = {}
        self.traces = {}
        self.approvals = {}
        self.outbox = {}
        self.approval_policies = {}

    def _build_quote_no(self) -> str:
        return f"Q-{uuid4().hex[:8].upper()}"

    def _hydrate_approval(self, approval_row: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
        approval = _normalize_row(approval_row)
        approval["steps"] = [
            {
                "id": step["id"],
                "seq_no": step["seq_no"],
                "status": step["status"],
                "approver_role": step.get("approver_ref"),
                "approver_type": step.get("approver_type"),
                "approver_ref": step.get("approver_ref"),
                "sla_due_at": step.get("sla_due_at"),
                "acted_at": step.get("acted_at"),
                "comments": step.get("comments"),
            }
            for step in [_normalize_row(s) for s in steps]
        ]
        return approval

    def create_quote(self, tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        if self._use_postgres:
            self._ensure_tenant(tenant_id)
            with self._connect() as conn:
                with conn.cursor() as cur:
                    quote_no = self._build_quote_no()
                    cur.execute(
                        """
                        INSERT INTO quotes (
                          tenant_id, quote_no, customer_external_id, customer_account_id, opportunity_id,
                          status, currency, region, price_book_id, subtotal, discount_total, surcharge_total,
                          tax_total, grand_total, margin_pct, revision_no, valid_until
                        )
                        VALUES (
                          %(tenant_id)s, %(quote_no)s, %(customer_external_id)s, %(customer_account_id)s, %(opportunity_id)s,
                          'DRAFT', %(currency)s, %(region)s, %(price_book_id)s, 0, 0, 0, 0, 0, 0, 1, %(valid_until)s
                        )
                        RETURNING *
                        """,
                        {
                            "tenant_id": tenant_id,
                            "quote_no": quote_no,
                            "customer_external_id": payload.get("customer_external_id"),
                            "customer_account_id": payload.get("customer_account_id"),
                            "opportunity_id": payload.get("opportunity_id"),
                            "currency": payload["currency"],
                            "region": payload.get("region"),
                            "price_book_id": payload["price_book_id"],
                            "valid_until": payload.get("valid_until"),
                        },
                    )
                    quote = _normalize_row(cur.fetchone())
            self.emit_event(tenant_id, "quote.created", quote["id"], {"quote_no": quote["quote_no"]})
            return quote

        tenant_quotes = self.quotes.setdefault(tenant_id, {})
        quote_id = uuid4()
        next_num = len(tenant_quotes) + 1
        quote = {
            "id": quote_id,
            "tenant_id": tenant_id,
            "quote_no": f"Q-{next_num:05d}",
            "status": "DRAFT",
            "subtotal": 0.0,
            "discount_total": 0.0,
            "surcharge_total": 0.0,
            "tax_total": 0.0,
            "grand_total": 0.0,
            "margin_pct": 0.0,
            "revision_no": 1,
            "created_at": utcnow(),
            "updated_at": utcnow(),
            **payload,
        }
        tenant_quotes[quote_id] = quote
        self.lines.setdefault(tenant_id, {})[quote_id] = {}
        self.revisions.setdefault(tenant_id, {})[quote_id] = []
        self.approvals.setdefault(tenant_id, {})
        self.outbox.setdefault(tenant_id, [])
        self.emit_event(tenant_id, "quote.created", quote_id, {"quote_no": quote["quote_no"]})
        return quote

    def list_quotes(self, tenant_id: UUID) -> list[dict[str, Any]]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM quotes WHERE tenant_id = %s ORDER BY created_at DESC", (tenant_id,))
                    return [_normalize_row(row) for row in cur.fetchall()]
        return list(self.quotes.get(tenant_id, {}).values())

    def get_quote(self, tenant_id: UUID, quote_id: UUID) -> dict[str, Any] | None:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM quotes WHERE tenant_id = %s AND id = %s", (tenant_id, quote_id))
                    row = cur.fetchone()
                    return _normalize_row(row) if row else None
        return self.quotes.get(tenant_id, {}).get(quote_id)

    def add_line(self, tenant_id: UUID, quote_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        if self._use_postgres:
            if not self.get_quote(tenant_id, quote_id):
                raise KeyError("Quote not found")
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COALESCE(MAX(line_no), 0) + 1 AS next_line_no FROM quote_line_items WHERE tenant_id = %s AND quote_id = %s",
                        (tenant_id, quote_id),
                    )
                    next_line_no = int(cur.fetchone()["next_line_no"])
                    cur.execute(
                        """
                        INSERT INTO quote_line_items (
                          tenant_id, quote_id, line_no, commercial_item_id, quantity,
                          discount_pct, term_months, config_json, pricing_snapshot_json
                        )
                        VALUES (
                          %(tenant_id)s, %(quote_id)s, %(line_no)s, %(commercial_item_id)s, %(quantity)s,
                          %(discount_pct)s, %(term_months)s, %(config_json)s, %(pricing_snapshot_json)s
                        )
                        RETURNING *
                        """,
                        {
                            "tenant_id": tenant_id,
                            "quote_id": quote_id,
                            "line_no": next_line_no,
                            "commercial_item_id": payload["commercial_item_id"],
                            "quantity": payload.get("quantity", 1),
                            "discount_pct": payload.get("discount_pct", 0),
                            "term_months": payload.get("term_months"),
                            "config_json": payload.get("config_json") or {},
                            "pricing_snapshot_json": payload.get("pricing_snapshot_json") or {},
                        },
                    )
                    line = _normalize_row(cur.fetchone())
            self.emit_event(tenant_id, "quote.line.changed", quote_id, {"line_id": str(line["id"])})
            return line

        quote = self.get_quote(tenant_id, quote_id)
        if not quote:
            raise KeyError("Quote not found")

        quote_lines = self.lines.setdefault(tenant_id, {}).setdefault(quote_id, {})
        line_id = uuid4()
        line_no = len(quote_lines) + 1
        line = {
            "id": line_id,
            "tenant_id": tenant_id,
            "quote_id": quote_id,
            "line_no": line_no,
            "discount_pct": 0.0,
            "term_months": None,
            "config_json": {},
            "pricing_snapshot_json": {},
            **payload,
        }
        quote_lines[line_id] = line
        self.emit_event(tenant_id, "quote.line.changed", quote_id, {"line_id": str(line_id)})
        return line

    def list_lines(self, tenant_id: UUID, quote_id: UUID) -> list[dict[str, Any]]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT * FROM quote_line_items
                        WHERE tenant_id = %s AND quote_id = %s
                        ORDER BY line_no
                        """,
                        (tenant_id, quote_id),
                    )
                    return [_normalize_row(row) for row in cur.fetchall()]
        return list(self.lines.get(tenant_id, {}).get(quote_id, {}).values())

    def update_line(self, tenant_id: UUID, quote_id: UUID, line_id: UUID, patch: dict[str, Any]) -> dict[str, Any]:
        if self._use_postgres:
            if not patch:
                existing = next((line for line in self.list_lines(tenant_id, quote_id) if line["id"] == line_id), None)
                if not existing:
                    raise KeyError("Line item not found")
                return existing

            allowed_fields = {"quantity", "discount_pct", "term_months", "config_json"}
            values = {k: v for k, v in patch.items() if k in allowed_fields and v is not None}
            if not values:
                existing = next((line for line in self.list_lines(tenant_id, quote_id) if line["id"] == line_id), None)
                if not existing:
                    raise KeyError("Line item not found")
                return existing

            assignments = []
            params: list[Any] = []
            for key, value in values.items():
                assignments.append(f"{key} = %s")
                params.append(value)
            assignments.append("updated_at = NOW()")
            params.extend([tenant_id, quote_id, line_id])

            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        UPDATE quote_line_items
                        SET {', '.join(assignments)}
                        WHERE tenant_id = %s AND quote_id = %s AND id = %s
                        RETURNING *
                        """,
                        params,
                    )
                    row = cur.fetchone()
                    if not row:
                        raise KeyError("Line item not found")
                    line = _normalize_row(row)
            self.emit_event(tenant_id, "quote.line.changed", quote_id, {"line_id": str(line_id), "action": "updated"})
            return line

        quote_lines = self.lines.get(tenant_id, {}).get(quote_id, {})
        line = quote_lines.get(line_id)
        if not line:
            raise KeyError("Line item not found")
        for key, value in patch.items():
            if value is not None:
                line[key] = value
        self.emit_event(tenant_id, "quote.line.changed", quote_id, {"line_id": str(line_id), "action": "updated"})
        return line

    def delete_line(self, tenant_id: UUID, quote_id: UUID, line_id: UUID) -> None:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM quote_line_items WHERE tenant_id = %s AND quote_id = %s AND id = %s RETURNING line_no",
                        (tenant_id, quote_id, line_id),
                    )
                    deleted = cur.fetchone()
                    if not deleted:
                        raise KeyError("Line item not found")

                    cur.execute(
                        """
                        WITH ordered AS (
                          SELECT id, ROW_NUMBER() OVER (ORDER BY line_no) AS new_line_no
                          FROM quote_line_items
                          WHERE tenant_id = %s AND quote_id = %s
                        )
                        UPDATE quote_line_items q
                        SET line_no = ordered.new_line_no
                        FROM ordered
                        WHERE q.id = ordered.id
                        """,
                        (tenant_id, quote_id),
                    )
            self.emit_event(tenant_id, "quote.line.changed", quote_id, {"line_id": str(line_id), "action": "deleted"})
            return

        quote_lines = self.lines.get(tenant_id, {}).get(quote_id, {})
        if line_id not in quote_lines:
            raise KeyError("Line item not found")
        del quote_lines[line_id]
        for idx, line in enumerate(quote_lines.values(), start=1):
            line["line_no"] = idx
        self.emit_event(tenant_id, "quote.line.changed", quote_id, {"line_id": str(line_id), "action": "deleted"})

    def create_revision(self, tenant_id: UUID, quote_id: UUID, reason: str) -> dict[str, Any]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE quotes
                        SET revision_no = revision_no + 1, updated_at = NOW()
                        WHERE tenant_id = %s AND id = %s
                        RETURNING *
                        """,
                        (tenant_id, quote_id),
                    )
                    quote = cur.fetchone()
                    if not quote:
                        raise KeyError("Quote not found")

                    quote_data = _normalize_row(quote)
                    lines = self.list_lines(tenant_id, quote_id)
                    snapshot = {
                        "quote": _to_jsonable(quote_data),
                        "lines": _to_jsonable(lines),
                    }

                    cur.execute(
                        """
                        INSERT INTO quote_revisions (tenant_id, quote_id, revision_no, change_reason, snapshot_json)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING *
                        """,
                        (
                            tenant_id,
                            quote_id,
                            quote_data["revision_no"],
                            reason,
                            snapshot,
                        ),
                    )
                    return _normalize_row(cur.fetchone())

        quote = self.get_quote(tenant_id, quote_id)
        if not quote:
            raise KeyError("Quote not found")
        quote["revision_no"] += 1
        quote["updated_at"] = utcnow()

        snapshot = {
            "quote": quote.copy(),
            "lines": [line.copy() for line in self.list_lines(tenant_id, quote_id)],
        }
        rev = {
            "id": uuid4(),
            "tenant_id": tenant_id,
            "quote_id": quote_id,
            "revision_no": quote["revision_no"],
            "change_reason": reason,
            "snapshot_json": snapshot,
            "created_at": utcnow(),
        }
        self.revisions[tenant_id][quote_id].append(rev)
        return rev

    def list_revisions(self, tenant_id: UUID, quote_id: UUID) -> list[dict[str, Any]]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT * FROM quote_revisions
                        WHERE tenant_id = %s AND quote_id = %s
                        ORDER BY revision_no DESC
                        """,
                        (tenant_id, quote_id),
                    )
                    return [_normalize_row(row) for row in cur.fetchall()]
        return list(self.revisions.get(tenant_id, {}).get(quote_id, []))

    def set_status(self, tenant_id: UUID, quote_id: UUID, status: str) -> dict[str, Any]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE quotes
                        SET status = %s, updated_at = NOW()
                        WHERE tenant_id = %s AND id = %s
                        RETURNING *
                        """,
                        (status, tenant_id, quote_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise KeyError("Quote not found")
                    return _normalize_row(row)

        quote = self.get_quote(tenant_id, quote_id)
        if not quote:
            raise KeyError("Quote not found")
        quote["status"] = status
        quote["updated_at"] = utcnow()
        return quote

    def save_trace(self, tenant_id: UUID, quote_id: UUID, trace: dict[str, Any]) -> dict[str, Any]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO pricing_calculation_traces (
                          tenant_id, quote_id, execution_mode, engine_version,
                          rule_set_version, trace_json, input_hash, output_hash
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *
                        """,
                        (
                            tenant_id,
                            quote_id,
                            trace.get("execution_mode", "PREVIEW"),
                            trace.get("engine_version", "unknown"),
                            trace.get("rule_set_version"),
                            _to_jsonable(trace),
                            trace.get("input_hash", ""),
                            trace.get("output_hash", ""),
                        ),
                    )
                    row = _normalize_row(cur.fetchone())
            trace_record = {
                "id": row["id"],
                "tenant_id": tenant_id,
                "quote_id": quote_id,
                "created_at": row["created_at"],
                **trace,
            }
            return trace_record

        trace_record = {
            "id": uuid4(),
            "tenant_id": tenant_id,
            "quote_id": quote_id,
            "created_at": utcnow(),
            **trace,
        }
        self.traces.setdefault(tenant_id, []).append(trace_record)
        return trace_record

    def list_traces(self, tenant_id: UUID, quote_id: UUID) -> list[dict[str, Any]]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT * FROM pricing_calculation_traces
                        WHERE tenant_id = %s AND quote_id = %s
                        ORDER BY created_at DESC
                        """,
                        (tenant_id, quote_id),
                    )
                    traces: list[dict[str, Any]] = []
                    for row in cur.fetchall():
                        record = _normalize_row(row)
                        trace_json = record.get("trace_json") or {}
                        traces.append(
                            {
                                "id": record["id"],
                                "tenant_id": record["tenant_id"],
                                "quote_id": record.get("quote_id"),
                                "created_at": record["created_at"],
                                **trace_json,
                            }
                        )
                    return traces
        return [trace for trace in self.traces.get(tenant_id, []) if trace["quote_id"] == quote_id]

    def create_approval_policy(self, tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        if self._use_postgres:
            self._ensure_tenant(tenant_id)
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO approval_policies (tenant_id, name, status, conditions_json, route_template_json)
                        VALUES (%s, %s, 'ACTIVE', %s, %s)
                        RETURNING *
                        """,
                        (
                            tenant_id,
                            payload["name"],
                            payload.get("conditions", {}),
                            payload.get("route", {"levels": 1}),
                        ),
                    )
                    row = _normalize_row(cur.fetchone())
                    return {
                        "id": str(row["id"]),
                        "tenant_id": str(row["tenant_id"]),
                        "name": row["name"],
                        "conditions": row.get("conditions_json") or {},
                        "route": row.get("route_template_json") or {"levels": 1},
                        "status": row["status"],
                    }

        policy = {
            "id": str(uuid4()),
            "tenant_id": str(tenant_id),
            "name": payload["name"],
            "conditions": payload.get("conditions", {}),
            "route": payload.get("route", {"levels": 1}),
            "status": "ACTIVE",
        }
        self.approval_policies.setdefault(tenant_id, []).append(policy)
        return policy

    def list_approval_policies(self, tenant_id: UUID) -> list[dict[str, Any]]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM approval_policies WHERE tenant_id = %s ORDER BY created_at DESC",
                        (tenant_id,),
                    )
                    rows = [_normalize_row(row) for row in cur.fetchall()]
                    return [
                        {
                            "id": str(row["id"]),
                            "tenant_id": str(row["tenant_id"]),
                            "name": row["name"],
                            "conditions": row.get("conditions_json") or {},
                            "route": row.get("route_template_json") or {"levels": 1},
                            "status": row["status"],
                        }
                        for row in rows
                    ]
        return list(self.approval_policies.get(tenant_id, []))

    def start_approval(self, tenant_id: UUID, quote_id: UUID, levels: int) -> dict[str, Any]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO approval_instances (tenant_id, quote_id, status, started_at)
                        VALUES (%s, %s, 'PENDING', NOW())
                        RETURNING *
                        """,
                        (tenant_id, quote_id),
                    )
                    approval = cur.fetchone()
                    instance_id = approval["id"]

                    for idx in range(levels):
                        approver_role = "FINANCE_MANAGER" if idx == 0 else "EXECUTIVE"
                        cur.execute(
                            """
                            INSERT INTO approval_steps (
                              tenant_id, approval_instance_id, seq_no, approver_type,
                              approver_ref, status, sla_due_at, comments
                            )
                            VALUES (%s, %s, %s, 'ROLE', %s, 'PENDING', %s, NULL)
                            """,
                            (
                                tenant_id,
                                instance_id,
                                idx + 1,
                                approver_role,
                                utcnow() + timedelta(hours=48),
                            ),
                        )

                conn.commit()
            result = self.get_approval(tenant_id, instance_id)
            if not result:
                raise KeyError("Approval not found")
            self.emit_event(tenant_id, "approval.started", quote_id, {"approval_id": str(instance_id)})
            return result

        instance_id = uuid4()
        steps: list[dict[str, Any]] = []
        for idx in range(levels):
            steps.append(
                {
                    "id": uuid4(),
                    "seq_no": idx + 1,
                    "status": "PENDING",
                    "approver_role": "FINANCE_MANAGER" if idx == 0 else "EXECUTIVE",
                    "sla_due_at": utcnow() + timedelta(hours=48),
                    "acted_at": None,
                    "comments": None,
                }
            )
        approval = {
            "id": instance_id,
            "tenant_id": tenant_id,
            "quote_id": quote_id,
            "status": "PENDING",
            "started_at": utcnow(),
            "completed_at": None,
            "steps": steps,
        }
        self.approvals.setdefault(tenant_id, {})[instance_id] = approval
        self.emit_event(tenant_id, "approval.started", quote_id, {"approval_id": str(instance_id)})
        return approval

    def get_approval(self, tenant_id: UUID, approval_id: UUID) -> dict[str, Any] | None:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM approval_instances WHERE tenant_id = %s AND id = %s",
                        (tenant_id, approval_id),
                    )
                    approval = cur.fetchone()
                    if not approval:
                        return None
                    cur.execute(
                        """
                        SELECT * FROM approval_steps
                        WHERE tenant_id = %s AND approval_instance_id = %s
                        ORDER BY seq_no
                        """,
                        (tenant_id, approval_id),
                    )
                    steps = cur.fetchall()
                    return self._hydrate_approval(approval, steps)

        return self.approvals.get(tenant_id, {}).get(approval_id)

    def get_approval_for_quote(self, tenant_id: UUID, quote_id: UUID) -> dict[str, Any] | None:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT * FROM approval_instances
                        WHERE tenant_id = %s AND quote_id = %s
                        ORDER BY started_at DESC
                        LIMIT 1
                        """,
                        (tenant_id, quote_id),
                    )
                    approval = cur.fetchone()
                    if not approval:
                        return None
                    return self.get_approval(tenant_id, approval["id"])

        for approval in self.approvals.get(tenant_id, {}).values():
            if approval["quote_id"] == quote_id:
                return approval
        return None

    def act_approval(self, tenant_id: UUID, approval_id: UUID, action: str, comments: str | None) -> dict[str, Any]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM approval_instances WHERE tenant_id = %s AND id = %s FOR UPDATE",
                        (tenant_id, approval_id),
                    )
                    approval = cur.fetchone()
                    if not approval:
                        raise KeyError("Approval not found")

                    cur.execute(
                        """
                        SELECT * FROM approval_steps
                        WHERE tenant_id = %s AND approval_instance_id = %s AND status = 'PENDING'
                        ORDER BY seq_no
                        LIMIT 1
                        FOR UPDATE
                        """,
                        (tenant_id, approval_id),
                    )
                    pending = cur.fetchone()
                    if not pending:
                        raise ValueError("No pending approval step")

                    if action == "APPROVE":
                        step_status = "APPROVED"
                    elif action == "REJECT":
                        step_status = "REJECTED"
                    elif action == "REQUEST_CHANGES":
                        step_status = "CHANGES_REQUESTED"
                    else:
                        raise ValueError("Unsupported action")

                    cur.execute(
                        """
                        UPDATE approval_steps
                        SET status = %s, acted_at = NOW(), comments = %s
                        WHERE tenant_id = %s AND id = %s
                        """,
                        (step_status, comments, tenant_id, pending["id"]),
                    )

                    if action == "APPROVE":
                        cur.execute(
                            """
                            SELECT COUNT(*) AS pending_count
                            FROM approval_steps
                            WHERE tenant_id = %s AND approval_instance_id = %s AND status = 'PENDING'
                            """,
                            (tenant_id, approval_id),
                        )
                        pending_count = int(cur.fetchone()["pending_count"])
                        if pending_count == 0:
                            cur.execute(
                                """
                                UPDATE approval_instances
                                SET status = 'APPROVED', completed_at = NOW()
                                WHERE tenant_id = %s AND id = %s
                                """,
                                (tenant_id, approval_id),
                            )
                    else:
                        instance_status = "REJECTED" if action == "REJECT" else "CHANGES_REQUESTED"
                        cur.execute(
                            """
                            UPDATE approval_instances
                            SET status = %s, completed_at = NOW()
                            WHERE tenant_id = %s AND id = %s
                            """,
                            (instance_status, tenant_id, approval_id),
                        )

                conn.commit()
            updated = self.get_approval(tenant_id, approval_id)
            if not updated:
                raise KeyError("Approval not found")
            return updated

        approval = self.approvals.get(tenant_id, {}).get(approval_id)
        if not approval:
            raise KeyError("Approval not found")
        pending = next((step for step in approval["steps"] if step["status"] == "PENDING"), None)
        if not pending:
            raise ValueError("No pending approval step")

        if action == "APPROVE":
            pending["status"] = "APPROVED"
            pending["acted_at"] = utcnow()
            pending["comments"] = comments
            if all(step["status"] == "APPROVED" for step in approval["steps"]):
                approval["status"] = "APPROVED"
                approval["completed_at"] = utcnow()
        elif action == "REJECT":
            pending["status"] = "REJECTED"
            pending["acted_at"] = utcnow()
            pending["comments"] = comments
            approval["status"] = "REJECTED"
            approval["completed_at"] = utcnow()
        elif action == "REQUEST_CHANGES":
            pending["status"] = "CHANGES_REQUESTED"
            pending["acted_at"] = utcnow()
            pending["comments"] = comments
            approval["status"] = "CHANGES_REQUESTED"
            approval["completed_at"] = utcnow()
        else:
            raise ValueError("Unsupported action")

        return approval

    def emit_event(self, tenant_id: UUID, event_type: str, aggregate_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        if self._use_postgres:
            self._ensure_tenant(tenant_id)
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO outbox_events (
                          tenant_id, aggregate_type, aggregate_id, event_type, payload_json, status, available_at
                        )
                        VALUES (%s, %s, %s, %s, %s, 'PENDING', NOW())
                        RETURNING *
                        """,
                        (tenant_id, "QUOTE", aggregate_id, event_type, _to_jsonable(payload)),
                    )
                    row = _normalize_row(cur.fetchone())
                    return {
                        "id": row["id"],
                        "tenant_id": row["tenant_id"],
                        "aggregate_id": row.get("aggregate_id"),
                        "event_type": row["event_type"],
                        "payload": row.get("payload_json") or {},
                        "status": row["status"],
                        "created_at": row["created_at"],
                    }

        event = {
            "id": uuid4(),
            "tenant_id": tenant_id,
            "aggregate_id": aggregate_id,
            "event_type": event_type,
            "payload": payload,
            "status": "PENDING",
            "created_at": utcnow(),
        }
        self.outbox.setdefault(tenant_id, []).append(event)
        return event

    def list_outbox(self, tenant_id: UUID) -> list[dict[str, Any]]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT * FROM outbox_events
                        WHERE tenant_id = %s
                        ORDER BY created_at DESC
                        """,
                        (tenant_id,),
                    )
                    events = []
                    for row in cur.fetchall():
                        event = _normalize_row(row)
                        events.append(
                            {
                                "id": event["id"],
                                "tenant_id": event["tenant_id"],
                                "aggregate_id": event.get("aggregate_id"),
                                "event_type": event["event_type"],
                                "payload": event.get("payload_json") or {},
                                "status": event["status"],
                                "created_at": event["created_at"],
                                "published_at": event.get("published_at"),
                            }
                        )
                    return events

        return list(self.outbox.get(tenant_id, []))

    def list_pending_outbox(self, tenant_id: UUID) -> list[dict[str, Any]]:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT * FROM outbox_events
                        WHERE tenant_id = %s AND status = 'PENDING' AND available_at <= NOW()
                        ORDER BY created_at ASC
                        """,
                        (tenant_id,),
                    )
                    events = []
                    for row in cur.fetchall():
                        event = _normalize_row(row)
                        events.append(
                            {
                                "id": event["id"],
                                "tenant_id": event["tenant_id"],
                                "aggregate_id": event.get("aggregate_id"),
                                "event_type": event["event_type"],
                                "payload": event.get("payload_json") or {},
                                "status": event["status"],
                            }
                        )
                    return events

        return [event for event in self.outbox.get(tenant_id, []) if event["status"] == "PENDING"]

    def mark_outbox_event_published(self, tenant_id: UUID, event_id: UUID) -> None:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE outbox_events
                        SET status = 'PUBLISHED', published_at = NOW(), retry_count = retry_count + 1
                        WHERE tenant_id = %s AND id = %s
                        """,
                        (tenant_id, event_id),
                    )
            return

        for event in self.outbox.get(tenant_id, []):
            if event["id"] == event_id:
                event["status"] = "PUBLISHED"
                event["published_at"] = utcnow()
                return

    def clear(self) -> None:
        if self._use_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM approval_steps")
                    cur.execute("DELETE FROM approval_instances")
                    cur.execute("DELETE FROM approval_policies")
                    cur.execute("DELETE FROM pricing_calculation_traces")
                    cur.execute("DELETE FROM quote_revisions")
                    cur.execute("DELETE FROM quote_line_items")
                    cur.execute("DELETE FROM outbox_events")
                    cur.execute("DELETE FROM quotes")
                conn.commit()
            return

        self.quotes.clear()
        self.lines.clear()
        self.revisions.clear()
        self.traces.clear()
        self.approvals.clear()
        self.outbox.clear()
        self.approval_policies.clear()


catalog_store = CatalogStore()
price_book_store = PriceBookStore()
quote_store = QuoteStore()
