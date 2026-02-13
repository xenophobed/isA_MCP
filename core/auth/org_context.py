"""
Org context helper - Extract organization ID from request state.

Used by API endpoints to pass org_id to repositories for tenant filtering.
"""

from typing import Optional
from starlette.requests import Request


def get_org_id(request: Request) -> Optional[str]:
    """
    Get the current organization ID from request state.

    Returns:
        Organization ID string, or None if not set (global-only access).
    """
    return getattr(request.state, "organization_id", None)
