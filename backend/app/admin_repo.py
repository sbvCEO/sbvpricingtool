import json
from typing import Any
from uuid import UUID

from app.config import settings


class AdminRepository:
    def __init__(self) -> None:
        self.backend = settings.admin_store_backend
        self.database_url = settings.database_url
        self._memory: dict[UUID, dict[str, Any]] = {}

    def _has_postgres(self) -> bool:
        return self.backend == "postgres" and bool(self.database_url)

    def _ensure_table(self) -> None:
        if not self._has_postgres():
            return
        import psycopg

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS admin_state (
                      tenant_id UUID PRIMARY KEY,
                      state JSONB NOT NULL,
                      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            conn.commit()

    def get_state(self, tenant_id: UUID) -> dict[str, Any] | None:
        if self._has_postgres():
            self._ensure_table()
            import psycopg

            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT state FROM admin_state WHERE tenant_id = %s", (str(tenant_id),))
                    row = cur.fetchone()
                    if row:
                        return row[0] if isinstance(row[0], dict) else json.loads(row[0])
                    return None

        return self._memory.get(tenant_id)

    def save_state(self, tenant_id: UUID, state: dict[str, Any]) -> dict[str, Any]:
        if self._has_postgres():
            self._ensure_table()
            import psycopg

            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO admin_state (tenant_id, state, updated_at)
                        VALUES (%s, %s::jsonb, NOW())
                        ON CONFLICT (tenant_id)
                        DO UPDATE SET state = EXCLUDED.state, updated_at = NOW()
                        """,
                        (str(tenant_id), json.dumps(state)),
                    )
                conn.commit()
            return state

        self._memory[tenant_id] = state
        return state

    def clear(self) -> None:
        if self._has_postgres():
            self._ensure_table()
            import psycopg

            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM admin_state")
                conn.commit()
        self._memory.clear()


admin_repo = AdminRepository()
