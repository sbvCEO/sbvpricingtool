from typing import Annotated, Any
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException

from app.rbac import require_permission
from app.rules_engine import create_rule, list_rules, publish_rule, simulate_rule, validate_rule
from app.schemas import AuthContext

router = APIRouter(prefix="/api/rules", tags=["rules"])


class RuleCreateRequest(BaseModel):
    name: str
    rule_type: str
    priority: int = 100
    dsl_json: dict[str, Any]


class RuleSimulationRequest(BaseModel):
    rule: RuleCreateRequest
    context: dict[str, Any]


@router.post("")
def create_rule_endpoint(
    payload: RuleCreateRequest,
    ctx: Annotated[AuthContext, Depends(require_permission("pricebook:write"))],
):
    return create_rule(ctx.tenant_id, payload.model_dump())


@router.get("")
def list_rules_endpoint(
    ctx: Annotated[AuthContext, Depends(require_permission("pricebook:read"))],
):
    return list_rules(ctx.tenant_id)


@router.post("/validate")
def validate_rule_endpoint(
    payload: RuleCreateRequest,
    _: Annotated[AuthContext, Depends(require_permission("pricebook:write"))],
):
    return validate_rule(payload.model_dump())


@router.post("/{rule_id}/publish")
def publish_rule_endpoint(
    rule_id: str,
    ctx: Annotated[AuthContext, Depends(require_permission("pricebook:write"))],
):
    try:
        return publish_rule(ctx.tenant_id, rule_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/simulate")
def simulate_rule_endpoint(
    payload: RuleSimulationRequest,
    _: Annotated[AuthContext, Depends(require_permission("pricebook:read"))],
):
    return simulate_rule(payload.rule.model_dump(), payload.context)
