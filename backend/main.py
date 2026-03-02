from time import perf_counter
from uuid import uuid4
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.audit import record_audit_event
from app.config import settings
from app.observability import record_request, start_timer
from app.routers.analytics import router as analytics_router
from app.routers.approvals import router as approvals_router
from app.routers.audit import router as audit_router
from app.routers.async_jobs import router as async_jobs_router
from app.routers.ai import router as ai_router
from app.routers.admin_console import router as admin_console_router
from app.routers.auth import router as auth_router
from app.routers.catalog import router as catalog_router
from app.routers.enterprise import router as enterprise_router
from app.routers.guided_quotes import router as guided_quotes_router
from app.routers.integrations import router as integrations_router
from app.routers.observability import router as observability_router
from app.routers.plugins import router as plugins_router
from app.routers.pricebooks import router as price_books_router
from app.routers.quotes import router as quotes_router
from app.routers.rules import router as rules_router
from app.routers.security_uplift import router as security_router

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PUBLIC_PATHS = {"/", "/api/health", "/api/auth/dev-token"}


@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id", str(uuid4()))
    request.state.request_id = request_id
    start = start_timer()

    # Let CORS preflight requests pass without tenant/auth context checks.
    if request.method == "OPTIONS":
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        record_request(request.url.path, response.status_code, perf_counter() - start)
        return response

    if request.url.path in PUBLIC_PATHS:
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        record_request(request.url.path, response.status_code, perf_counter() - start)
        return response

    tenant_header = request.headers.get("X-Tenant-Id")
    if not tenant_header:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Missing tenant context. Provide X-Tenant-Id header."
            },
        )

    try:
        tenant_id = UUID(tenant_header)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid X-Tenant-Id. Must be a UUID."},
        )

    request.state.tenant_id = str(tenant_id)
    response = await call_next(request)
    response.headers["X-Tenant-Id"] = str(tenant_id)
    response.headers["X-Request-Id"] = request_id
    elapsed = perf_counter() - start
    record_request(request.url.path, response.status_code, elapsed)

    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        record_audit_event(
            tenant_id=tenant_id,
            entity_type="http_request",
            action=f"{request.method} {request.url.path}",
            actor_sub=request.headers.get("X-User-Sub"),
            path=request.url.path,
            method=request.method,
            status_code=response.status_code,
            metadata={"request_id": request_id, "latency_ms": round(elapsed * 1000, 3)},
        )
    return response


@app.get("/")
async def root():
    return {"message": "Welcome to SANCNIDA API", "status": "running"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/tenant-context")
async def tenant_context(request: Request):
    return {
        "tenant_id": getattr(request.state, "tenant_id", None),
        "message": "Tenant context resolved for request",
    }


app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(price_books_router)
app.include_router(quotes_router)
app.include_router(approvals_router)
app.include_router(guided_quotes_router)
app.include_router(analytics_router)
app.include_router(async_jobs_router)
app.include_router(admin_console_router)
app.include_router(audit_router)
app.include_router(observability_router)
app.include_router(rules_router)
app.include_router(ai_router)
app.include_router(integrations_router)
app.include_router(security_router)
app.include_router(enterprise_router)
app.include_router(plugins_router)
