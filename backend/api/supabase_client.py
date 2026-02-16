from __future__ import annotations

from functools import lru_cache
from typing import Any

from django.conf import settings


class SupabaseConfigurationError(RuntimeError):
    pass


def _require_setting(name: str) -> str:
    value = getattr(settings, name, "")
    if not value:
        raise SupabaseConfigurationError(f"{name} is not configured.")
    return value


def _ensure_https(url: str) -> str:
    """Prefix the URL with ``https://`` if no scheme is present."""
    if url and not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


@lru_cache(maxsize=2)
def _cached_client(url: str, key: str) -> Any:
    """Create and cache a Supabase client for the given URL and key."""
    from supabase import create_client

    return create_client(url, key)


def get_supabase_client(
    access_token: str | None = None,
    use_service_role: bool = False,
) -> Any:
    """Return a configured Supabase client.

    Args:
        access_token: Optional Clerk JWT to forward to Supabase PostgREST
            so that Row Level Security policies can identify the user.
        use_service_role: If ``True``, use the service-role key which
            bypasses RLS.  Use this only for trusted server-side jobs.

    Returns:
        A ``supabase.Client`` instance.

    Raises:
        SupabaseConfigurationError: If required settings are missing or
            the ``supabase`` package is not installed.
    """
    try:
        from supabase import create_client
    except ImportError as exc:
        raise SupabaseConfigurationError(
            "Supabase client dependencies are missing or incompatible."
        ) from exc

    url = _ensure_https(_require_setting("SUPABASE_URL"))
    key_setting = "SUPABASE_SERVICE_ROLE_KEY" if use_service_role else "SUPABASE_ANON_KEY"
    key = _require_setting(key_setting)

    if access_token:
        # When forwarding a user token we need a fresh client so the
        # auth header is specific to this request.
        client = create_client(url, key)
        postgrest_client = getattr(client, "postgrest", None)
        if postgrest_client and hasattr(postgrest_client, "auth"):
            postgrest_client.auth(access_token)
        return client

    # For anonymous / service-role calls, reuse a cached client.
    return _cached_client(url, key)
