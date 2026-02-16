"""Compatibility shim for Supabase client helpers.

Canonical location: api.tools.database.supabase
"""

from .tools.database.supabase import (  # noqa: F401
    SupabaseConfigurationError,
    _ensure_https,
    get_supabase_client,
)

__all__ = ["SupabaseConfigurationError", "_ensure_https", "get_supabase_client"]
