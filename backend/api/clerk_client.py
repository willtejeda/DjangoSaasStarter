"""Compatibility shim for Clerk backend SDK helpers.

Canonical location: api.tools.auth.clerk
"""

from .tools.auth.clerk import ClerkClientError, get_clerk_client, get_clerk_user

__all__ = ["ClerkClientError", "get_clerk_client", "get_clerk_user"]
