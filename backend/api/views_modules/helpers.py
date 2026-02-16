from __future__ import annotations

from typing import Any

from django.conf import settings
from rest_framework.exceptions import ValidationError

from ..tools.billing import (
    extract_billing_features as extract_billing_features_from_claims,
    infer_plan_tier as infer_plan_tier_from_features,
)
from ..models import CustomerAccount, Profile


def extract_billing_features(claims: dict[str, Any]) -> list[str]:
    """Backward-compatible local wrapper used by existing tests."""
    return extract_billing_features_from_claims(claims)


def infer_plan_tier(features: list[str]) -> str:
    """Backward-compatible local wrapper used by existing code paths."""
    return infer_plan_tier_from_features(features)


def _safe_str(value: Any) -> str:
    return str(value).strip() if value else ""


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _resolve_plan_tier(profile: Profile, claims: dict[str, Any]) -> str:
    tier = str(getattr(profile, "plan_tier", "") or "").strip().lower()
    if tier in {"free", "pro", "enterprise"}:
        return tier
    return infer_plan_tier(extract_billing_features(claims))


def _build_ai_provider_payload() -> list[dict[str, Any]]:
    openrouter_base = _safe_str(getattr(settings, "OPENROUTER_BASE_URL", "")) or "https://openrouter.ai/api/v1"
    openrouter_key = _safe_str(getattr(settings, "OPENROUTER_API_KEY", ""))
    openrouter_model = _safe_str(getattr(settings, "OPENROUTER_DEFAULT_MODEL", ""))

    ollama_base = _safe_str(getattr(settings, "OLLAMA_BASE_URL", "")) or "http://127.0.0.1:11434"
    ollama_model = _safe_str(getattr(settings, "OLLAMA_MODEL", ""))

    return [
        {
            "key": "openrouter",
            "label": "OpenRouter",
            "kind": "remote",
            "enabled": bool(openrouter_key),
            "base_url": openrouter_base,
            "model_hint": openrouter_model,
            "docs_url": "https://openrouter.ai/docs/quickstart",
            "env_vars": ["OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "OPENROUTER_DEFAULT_MODEL"],
        },
        {
            "key": "ollama",
            "label": "Ollama",
            "kind": "self_hosted",
            "enabled": bool(ollama_model),
            "base_url": ollama_base,
            "model_hint": ollama_model,
            "docs_url": "https://github.com/ollama/ollama/blob/main/docs/api.md",
            "env_vars": ["OLLAMA_BASE_URL", "OLLAMA_MODEL"],
        },
    ]


def _build_usage_bucket(
    *,
    key: str,
    label: str,
    used: int,
    limit: int | None,
    unit: str,
    reset_window: str,
) -> dict[str, Any]:
    if limit is None or limit <= 0:
        percent_used = None
    else:
        percent_used = round((used / limit) * 100, 2)
    near_limit = bool(percent_used is not None and percent_used >= 80)
    return {
        "key": key,
        "label": label,
        "used": max(used, 0),
        "limit": limit if limit and limit > 0 else None,
        "unit": unit,
        "reset_window": reset_window,
        "percent_used": percent_used,
        "near_limit": near_limit,
    }


def sync_profile_from_claims(claims: dict[str, Any]) -> Profile | None:
    clerk_user_id = _safe_str(claims.get("sub"))
    if not clerk_user_id:
        return None

    billing_features = extract_billing_features(claims)
    metadata = claims.get("metadata") if isinstance(claims.get("metadata"), dict) else {}
    defaults = {
        "email": _safe_str(claims.get("email")),
        "first_name": _safe_str(claims.get("given_name") or claims.get("first_name")),
        "last_name": _safe_str(claims.get("family_name") or claims.get("last_name")),
        "image_url": _safe_str(claims.get("picture") or claims.get("image_url")),
        "plan_tier": infer_plan_tier(billing_features),
        "billing_features": billing_features,
        "is_active": True,
        "metadata": metadata,
    }
    profile, created = Profile.objects.get_or_create(
        clerk_user_id=clerk_user_id,
        defaults=defaults,
    )

    if not created:
        changed_fields: list[str] = []
        for field_name, field_value in defaults.items():
            if getattr(profile, field_name) != field_value:
                setattr(profile, field_name, field_value)
                changed_fields.append(field_name)
        if changed_fields:
            profile.save(update_fields=[*changed_fields, "updated_at"])

    return profile


def get_request_claims(request) -> dict[str, Any]:
    claims = getattr(request, "clerk_claims", request.auth or {})
    return claims if isinstance(claims, dict) else {}


def get_request_profile(request) -> Profile:
    cached_profile = getattr(request, "_cached_profile", None)
    if cached_profile is not None:
        return cached_profile

    profile = sync_profile_from_claims(get_request_claims(request))
    if profile is None:
        raise ValidationError("Missing Clerk identity in token claims.")

    request._cached_profile = profile
    return profile


def get_request_customer_account(request) -> CustomerAccount:
    cached_account = getattr(request, "_cached_customer_account", None)
    if cached_account is not None:
        return cached_account

    profile = get_request_profile(request)
    defaults = {
        "external_customer_id": profile.clerk_user_id,
        "billing_email": profile.email,
        "full_name": profile.display_name,
    }
    account, created = CustomerAccount.objects.get_or_create(profile=profile, defaults=defaults)

    if not created:
        changed_fields: list[str] = []
        if not account.billing_email and profile.email:
            account.billing_email = profile.email
            changed_fields.append("billing_email")
        if not account.full_name and profile.display_name:
            account.full_name = profile.display_name
            changed_fields.append("full_name")
        if not account.external_customer_id and profile.clerk_user_id:
            account.external_customer_id = profile.clerk_user_id
            changed_fields.append("external_customer_id")
        if changed_fields:
            account.save(update_fields=[*changed_fields, "updated_at"])

    request._cached_customer_account = account
    return account
