from datetime import UTC, datetime, timedelta
from typing import Any

cache_store: dict[str, tuple[datetime, Any]] = {}


def get_cache(key: str) -> Any | None:
    item = cache_store.get(key)
    if not item:
        return None
    expires_at, value = item
    if datetime.now(UTC) > expires_at:
        cache_store.pop(key, None)
        return None
    return value


def set_cache(key: str, value: Any, ttl_seconds: int = 60) -> None:
    cache_store[key] = (datetime.now(UTC) + timedelta(seconds=ttl_seconds), value)


def clear_cache(prefix: str | None = None) -> None:
    if prefix is None:
        cache_store.clear()
        return
    for key in list(cache_store.keys()):
        if key.startswith(prefix):
            cache_store.pop(key, None)
