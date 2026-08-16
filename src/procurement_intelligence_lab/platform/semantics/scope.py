"""Explicit request authorization and state-projection scopes."""

from dataclasses import dataclass
from enum import StrEnum


class Permission(StrEnum):
    READ_EVIDENCE = "read_evidence"
    READ_STATE = "read_state"
    SEARCH = "search"
    REVIEW = "review"
    ACT = "act"


class ScopeAuthorizationError(PermissionError):
    """Raised when a request lacks an explicit authorized scope."""


@dataclass(frozen=True)
class RequestContext:
    """Caller and resource boundary for application queries and actions."""

    principal_id: str
    tenant_id: str
    project_id: str
    site_id: str
    permissions: frozenset[Permission]
    trace_id: str

    def __post_init__(self) -> None:
        if not all(
            (self.principal_id, self.tenant_id, self.project_id, self.site_id, self.trace_id)
        ):
            raise ValueError("principal, tenant, project, site, and trace IDs are required")

    def require(self, permission: Permission) -> None:
        if permission not in self.permissions:
            raise ScopeAuthorizationError(
                f"principal {self.principal_id!r} lacks {permission.value!r} permission"
            )

    def matches(self, other: "RequestContext") -> bool:
        return (self.tenant_id, self.project_id, self.site_id) == (
            other.tenant_id,
            other.project_id,
            other.site_id,
        )


@dataclass(frozen=True)
class StateScope:
    """Tenant/project/site plus a domain-owned state version."""

    tenant_id: str
    project_id: str
    site_id: str
    version: str

    def __post_init__(self) -> None:
        if not all((self.tenant_id, self.project_id, self.site_id, self.version)):
            raise ValueError("state scope identifiers and version are required")
