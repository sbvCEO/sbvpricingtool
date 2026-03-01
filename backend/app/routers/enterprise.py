from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.rbac import require_permission
from app.schemas import AuthContext

router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])


class SSOConfigRequest(BaseModel):
    idp_type: str
    metadata_url: str
    enforce_sso: bool = True


@router.post("/sso/config")
def configure_sso(
    payload: SSOConfigRequest,
    _: Annotated[AuthContext, Depends(require_permission("async:run"))],
):
    return {
        "status": "CONFIGURED",
        **payload.model_dump(),
    }


@router.post("/scim/provisioning")
def configure_scim(
    _: Annotated[AuthContext, Depends(require_permission("async:run"))],
):
    return {
        "status": "ENABLED",
        "base_path": "/api/enterprise/scim/v2",
        "supported_resources": ["Users", "Groups"],
    }


@router.get("/tenant-isolation-options")
def tenant_isolation_options(
    _: Annotated[AuthContext, Depends(require_permission("async:run"))],
):
    return {
        "modes": ["SHARED_SCHEMA", "SCHEMA_PER_TENANT", "DATABASE_PER_TENANT"],
        "default": "SHARED_SCHEMA",
    }
