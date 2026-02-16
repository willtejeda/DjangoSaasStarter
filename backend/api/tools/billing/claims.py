from __future__ import annotations

from typing import Any

from django.conf import settings

DEFAULT_BILLING_CLAIM = "entitlements"


def _normalize_feature(value: Any) -> str:
    return str(value or "").strip().lower()


def extract_billing_features(
    claims: dict[str, Any],
    claim_name: str | None = None,
) -> list[str]:
    selected_claim = claim_name or getattr(
        settings,
        "CLERK_BILLING_CLAIM",
        DEFAULT_BILLING_CLAIM,
    )
    value = claims.get(selected_claim)
    if value is None and selected_claim != DEFAULT_BILLING_CLAIM:
        value = claims.get(DEFAULT_BILLING_CLAIM)

    raw_features: list[str] = []
    if isinstance(value, list):
        raw_features = [_normalize_feature(item) for item in value]
    elif isinstance(value, dict):
        raw_features = [
            _normalize_feature(feature) for feature, enabled in value.items() if enabled
        ]
    elif isinstance(value, str):
        raw_features = [_normalize_feature(segment) for segment in value.split(",")]

    deduped: list[str] = []
    seen: set[str] = set()
    for feature in raw_features:
        if not feature or feature in seen:
            continue
        seen.add(feature)
        deduped.append(feature)
    return deduped


def infer_plan_tier(features: list[str]) -> str:
    normalized = {feature.lower() for feature in features}
    if "enterprise" in normalized:
        return "enterprise"
    if {"pro", "premium", "growth"} & normalized:
        return "pro"
    return "free"
