"""Compatibility shim for DRF authentication.

Canonical location: api.tools.auth.authentication
"""

from .tools.auth.authentication import ClerkJWTAuthentication, ClerkPrincipal
from .tools.auth.clerk import ClerkConfigurationError, decode_clerk_token

__all__ = [
    "ClerkJWTAuthentication",
    "ClerkPrincipal",
    "ClerkConfigurationError",
    "decode_clerk_token",
]
