from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.schemas import AuthContext
from app.security import get_current_auth_context

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "ADMIN": {
        "admin:manage",
        "admin:org:read",
        "admin:org:write",
        "admin:user:read",
        "admin:user:write",
        "admin:rbac:read",
        "admin:rbac:write",
        "admin:governance:read",
        "admin:governance:write",
        "catalog:read",
        "catalog:write",
        "pricebook:read",
        "pricebook:write",
        "quote:read",
        "quote:write",
        "approval:act",
        "dashboard:read",
        "async:run",
    },
    "SALES": {
        "catalog:read",
        "pricebook:read",
        "quote:read",
        "quote:write",
        "approval:act",
        "dashboard:read",
    },
    "OPERATIONS": {
        "catalog:read",
        "pricebook:read",
        "pricebook:write",
        "quote:read",
        "quote:write",
        "dashboard:read",
    },
    "FINANCE": {
        "catalog:read",
        "pricebook:read",
        "quote:read",
        "approval:act",
        "dashboard:read",
    },
    "DELIVERY": {
        "catalog:read",
        "pricebook:read",
        "quote:read",
        "quote:write",
        "dashboard:read",
    },
    "LEADERSHIP": {
        "catalog:read",
        "pricebook:read",
        "quote:read",
        "approval:act",
        "dashboard:read",
    },
    # Backward compatibility for legacy roles during migration.
    "FUNCTION_ADMIN": {
        "catalog:read",
        "catalog:write",
        "pricebook:read",
        "pricebook:write",
        "quote:read",
        "quote:write",
        "dashboard:read",
        "async:run",
    },
    "END_USER": {
        "catalog:read",
        "pricebook:read",
        "quote:read",
        "quote:write",
        "approval:act",
        "dashboard:read",
    },
    "NORMAL_USER": {
        "catalog:read",
        "pricebook:read",
        "quote:read",
        "quote:write",
        "approval:act",
        "dashboard:read",
    },
}


def resolved_permissions(ctx: AuthContext) -> set[str]:
    role_permissions: set[str] = set()
    for role in ctx.roles:
        role_permissions |= ROLE_PERMISSIONS.get(role.upper(), set())
    return role_permissions | set(ctx.scopes)


def require_permission(permission: str) -> Callable[[AuthContext], AuthContext]:
    def dependency(
        ctx: Annotated[AuthContext, Depends(get_current_auth_context)],
    ) -> AuthContext:
        permissions = resolved_permissions(ctx)
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return ctx

    return dependency


def require_role(role: str) -> Callable[[AuthContext], AuthContext]:
    def dependency(
        ctx: Annotated[AuthContext, Depends(get_current_auth_context)],
    ) -> AuthContext:
        if role not in ctx.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role: {role}",
            )
        return ctx

    return dependency


def require_any_role(*roles: str) -> Callable[[AuthContext], AuthContext]:
    allowed = set(roles)

    def dependency(
        ctx: Annotated[AuthContext, Depends(get_current_auth_context)],
    ) -> AuthContext:
        if not any(role in ctx.roles for role in allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role. Need one of: {', '.join(sorted(allowed))}",
            )
        return ctx

    return dependency
