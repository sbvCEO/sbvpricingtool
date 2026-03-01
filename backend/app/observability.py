from collections import defaultdict
from time import perf_counter
from typing import Any

metrics_store: dict[str, Any] = {
    "request_count": 0,
    "status_codes": defaultdict(int),
    "route_latency_ms": defaultdict(list),
}


def start_timer() -> float:
    return perf_counter()


def record_request(path: str, status_code: int, elapsed_seconds: float) -> None:
    metrics_store["request_count"] += 1
    metrics_store["status_codes"][status_code] += 1
    metrics_store["route_latency_ms"][path].append(round(elapsed_seconds * 1000, 3))


def snapshot_metrics() -> dict[str, Any]:
    routes = {}
    for path, values in metrics_store["route_latency_ms"].items():
        if not values:
            continue
        routes[path] = {
            "count": len(values),
            "avg_ms": round(sum(values) / len(values), 3),
            "p95_ms": sorted(values)[max(0, int(len(values) * 0.95) - 1)],
        }

    return {
        "request_count": metrics_store["request_count"],
        "status_codes": dict(metrics_store["status_codes"]),
        "routes": routes,
        "slo_targets": {
            "api_p95_ms": 250,
            "error_rate_pct": 1.0,
        },
    }
