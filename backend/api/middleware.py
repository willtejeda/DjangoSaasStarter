"""Optional middleware that enriches requests with Clerk user data.

When enabled, authenticated requests will have ``request.clerk_user``
populated with the full user object from Clerk's Backend API.  This
saves individual views from needing to make their own Clerk API calls.

To enable, add to ``MIDDLEWARE`` in settings.py::

    MIDDLEWARE = [
        ...
        "api.middleware.ClerkUserMiddleware",
    ]

.. note::
    This middleware makes an API call to Clerk on every authenticated
    request.  For high-traffic endpoints, consider caching the user data
    or using JWT claims directly instead.
"""

from __future__ import annotations

import logging

from django.http import HttpRequest

logger = logging.getLogger(__name__)


class ClerkUserMiddleware:
    """Attach ``request.clerk_user`` after Clerk JWT authentication."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        response = self.get_response(request)
        return response

    def process_view(self, request: HttpRequest, view_func, view_args, view_kwargs):
        """Populate ``request.clerk_user`` if a Clerk token was verified."""
        claims = getattr(request, "clerk_claims", None)
        if claims is None:
            return None

        clerk_user_id = claims.get("sub")
        if not clerk_user_id:
            return None

        try:
            from .clerk_client import get_clerk_user

            request.clerk_user = get_clerk_user(clerk_user_id)
        except Exception:
            logger.debug(
                "Could not fetch Clerk user %s via Backend SDK", clerk_user_id, exc_info=True
            )
            request.clerk_user = None

        return None
