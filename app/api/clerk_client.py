"""Clerk Backend SDK client for server-side user management.

Usage::

    from api.clerk_client import get_clerk_client

    client = get_clerk_client()
    user = client.users.get(user_id="user_2abc...")
"""

from __future__ import annotations

import threading
from typing import Any

from django.conf import settings


class ClerkClientError(RuntimeError):
    pass


_lock = threading.Lock()
_client: Any = None


def get_clerk_client() -> Any:
    """Return a lazily-initialized Clerk Backend SDK client.

    The client is created once and reused across requests.  It uses
    ``settings.CLERK_SECRET_KEY`` which must be set in your ``.env``.

    Raises:
        ClerkClientError: If the secret key is missing or the SDK cannot be imported.
    """
    global _client
    if _client is not None:
        return _client

    with _lock:
        if _client is not None:
            return _client

        secret_key = getattr(settings, "CLERK_SECRET_KEY", "")
        if not secret_key:
            raise ClerkClientError(
                "CLERK_SECRET_KEY is not configured. "
                "Get it from https://dashboard.clerk.com → API Keys."
            )

        try:
            from clerk_backend_api import Clerk
        except ImportError as exc:
            raise ClerkClientError(
                "clerk-backend-api package is required. "
                "Run: pip install clerk-backend-api"
            ) from exc

        _client = Clerk(bearer_auth=secret_key)
        return _client


def get_clerk_user(clerk_user_id: str) -> Any:
    """Look up a single user by their Clerk user ID.

    Returns the full user object from Clerk's API, including metadata,
    email addresses, and profile information.
    """
    client = get_clerk_client()
    return client.users.get(user_id=clerk_user_id)
