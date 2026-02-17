from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db.models import Q

from ..models import CustomerAccount, Order, PaymentTransaction, Price, Profile, Subscription
from ..tools.billing import extract_billing_features, infer_plan_tier

logger = logging.getLogger(__name__)
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)


def _extract_primary_email(data: dict[str, Any]) -> str:
    primary_email_id = data.get("primary_email_address_id")
    email_addresses = data.get("email_addresses", [])
    if not isinstance(email_addresses, list):
        return ""

    for email_obj in email_addresses:
        if (
            isinstance(email_obj, dict)
            and email_obj.get("id") == primary_email_id
            and email_obj.get("email_address")
        ):
            return str(email_obj["email_address"]).strip()

    first_email = email_addresses[0] if email_addresses else None
    if isinstance(first_email, dict) and first_email.get("email_address"):
        return str(first_email["email_address"]).strip()

    return ""


def _extract_billing_features(data: dict[str, Any]) -> list[str]:
    public_metadata = data.get("public_metadata", {})
    if not isinstance(public_metadata, dict):
        return []
    claim_name = getattr(settings, "CLERK_BILLING_CLAIM", "entitlements")
    return extract_billing_features(public_metadata, claim_name=claim_name)


def _infer_plan_tier(features: list[str]) -> str:
    return infer_plan_tier(features)


def _profile_defaults_from_clerk_user(data: dict[str, Any]) -> dict[str, Any]:
    billing_features = _extract_billing_features(data)
    public_metadata = data.get("public_metadata", {})
    metadata = public_metadata if isinstance(public_metadata, dict) else {}

    return {
        "email": _extract_primary_email(data),
        "first_name": str(data.get("first_name") or "").strip(),
        "last_name": str(data.get("last_name") or "").strip(),
        "image_url": str(data.get("image_url") or "").strip(),
        "billing_features": billing_features,
        "plan_tier": _infer_plan_tier(billing_features),
        "metadata": metadata,
        "is_active": True,
    }


def _safe_datetime(value: Any):
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 1_000_000_000_000:
            timestamp = timestamp / 1000.0
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    raw = str(value).strip()
    if not raw:
        return None

    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _extract_clerk_user_id_from_subscription_payload(data: dict[str, Any]) -> str:
    candidates = [
        data.get("user_id"),
        data.get("subscriber_id"),
        data.get("customer_id"),
        data.get("payer_id"),
        data.get("clerk_user_id"),
    ]

    subscriber = data.get("subscriber")
    if isinstance(subscriber, dict):
        candidates.extend(
            [
                subscriber.get("id"),
                subscriber.get("user_id"),
                subscriber.get("clerk_user_id"),
            ]
        )

    user = data.get("user")
    if isinstance(user, dict):
        candidates.extend([user.get("id"), user.get("user_id")])

    payer = data.get("payer")
    if isinstance(payer, dict):
        candidates.extend(
            [
                payer.get("user_id"),
                payer.get("clerk_user_id"),
                payer.get("subscriber_id"),
                payer.get("customer_id"),
                payer.get("id"),
            ]
        )
        payer_user = payer.get("user")
        if isinstance(payer_user, dict):
            candidates.extend(
                [
                    payer_user.get("id"),
                    payer_user.get("user_id"),
                ]
            )

    nested_id = _extract_first_value(
        data,
        [
            "clerk_user_id",
            "clerkUserId",
            "user_id",
            "userId",
            "subscriber_id",
            "subscriberId",
            "customer_id",
            "customerId",
        ],
    )
    if nested_id:
        candidates.append(nested_id)

    # Guard against non-user payer identifiers. Clerk user ids use the user_ prefix.
    for value in candidates:
        normalized = str(value or "").strip()
        if normalized.startswith("user_"):
            return normalized

    for value in candidates:
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    return ""


def _resolve_customer_account_from_clerk_user_id(clerk_user_id: str) -> CustomerAccount | None:
    normalized = str(clerk_user_id or "").strip()
    if not normalized:
        return None

    account = (
        CustomerAccount.objects.select_related("profile")
        .filter(Q(profile__clerk_user_id=normalized) | Q(external_customer_id=normalized))
        .first()
    )
    if account is not None:
        return account

    if not normalized.startswith("user_"):
        return None

    profile, _ = Profile.objects.get_or_create(
        clerk_user_id=normalized,
        defaults={"is_active": True},
    )

    account, _ = CustomerAccount.objects.get_or_create(
        profile=profile,
        defaults={
            "external_customer_id": profile.clerk_user_id,
            "billing_email": profile.email,
            "full_name": profile.display_name,
        },
    )
    return account


def _map_subscription_status(raw_status: str) -> str:
    normalized = str(raw_status or "").strip().lower().replace("-", "_")
    mapping = {
        "active": Subscription.Status.ACTIVE,
        "trialing": Subscription.Status.TRIALING,
        "past_due": Subscription.Status.PAST_DUE,
        "pastdue": Subscription.Status.PAST_DUE,
        "canceled": Subscription.Status.CANCELED,
        "cancelled": Subscription.Status.CANCELED,
        "incomplete": Subscription.Status.INCOMPLETE,
        "paused": Subscription.Status.PAUSED,
    }
    return mapping.get(normalized, Subscription.Status.INCOMPLETE)


def _find_price_from_clerk_ids(data: dict[str, Any]) -> Price | None:
    plan = data.get("plan")
    plan_id = ""
    price_id = ""

    if isinstance(plan, dict):
        plan_id = str(plan.get("id") or plan.get("plan_id") or "").strip()
        price_id = str(plan.get("price_id") or "").strip()

    if not plan_id:
        plan_id = str(data.get("plan_id") or data.get("price_plan_id") or "").strip()
    if not price_id:
        price_id = str(data.get("price_id") or "").strip()

    queryset = Price.objects.select_related("product")
    if price_id and plan_id:
        price = queryset.filter(Q(clerk_price_id=price_id) | Q(clerk_plan_id=plan_id)).first()
        if price:
            return price

    if price_id:
        price = queryset.filter(clerk_price_id=price_id).first()
        if price:
            return price

    if plan_id:
        return queryset.filter(clerk_plan_id=plan_id).first()

    return None


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_uuid(value: Any) -> str:
    raw = _normalize_text(value)
    if not raw:
        return ""
    try:
        return str(UUID(raw))
    except ValueError:
        match = UUID_PATTERN.search(raw)
        if not match:
            return ""
        try:
            return str(UUID(match.group(0)))
        except ValueError:
            return ""


def _iter_nested_dicts(data: dict[str, Any]):
    if not isinstance(data, dict):
        return

    queue: list[dict[str, Any]] = [data]
    seen_ids: set[int] = set()
    while queue:
        current = queue.pop(0)
        marker = id(current)
        if marker in seen_ids:
            continue
        seen_ids.add(marker)
        yield current

        for value in current.values():
            if isinstance(value, dict):
                queue.append(value)


def _extract_first_value(data: dict[str, Any], candidate_keys: list[str]) -> str:
    normalized_keys = {key.lower() for key in candidate_keys}
    for row in _iter_nested_dicts(data):
        for key, value in row.items():
            if str(key).strip().lower() not in normalized_keys:
                continue
            normalized = _normalize_text(value)
            if normalized:
                return normalized
    return ""


def _extract_order_public_id(data: dict[str, Any]) -> str:
    raw = _extract_first_value(
        data,
        [
            "order_public_id",
            "orderPublicId",
            "order_id",
            "orderId",
            "order_reference",
            "orderReference",
            "order",
        ],
    )
    return _normalize_uuid(raw)


def _extract_checkout_id(data: dict[str, Any]) -> str:
    return _extract_first_value(
        data,
        [
            "checkout_id",
            "checkoutId",
            "clerk_checkout_id",
            "checkout_session_id",
            "checkoutSessionId",
            "session_id",
            "sessionId",
        ],
    )


def _extract_payment_external_id(data: dict[str, Any]) -> str:
    return _extract_first_value(
        data,
        [
            "payment_attempt_id",
            "paymentAttemptId",
            "payment_id",
            "paymentId",
            "external_id",
            "externalId",
            "id",
        ],
    )


def _extract_payment_status(data: dict[str, Any]) -> str:
    return _extract_first_value(
        data,
        [
            "status",
            "payment_status",
            "paymentStatus",
            "checkout_status",
            "checkoutStatus",
            "state",
        ],
    ).lower()


def _is_success_status(raw_status: str) -> bool:
    return raw_status in {"succeeded", "success", "paid", "complete", "completed", "captured", "settled"}


def _is_failed_status(raw_status: str) -> bool:
    return raw_status in {"failed", "failure", "canceled", "cancelled", "voided", "refunded", "expired"}


def _map_payment_transaction_status(raw_status: str) -> str:
    if _is_success_status(raw_status):
        return PaymentTransaction.Status.SUCCEEDED
    if _is_failed_status(raw_status):
        return PaymentTransaction.Status.FAILED
    return PaymentTransaction.Status.PENDING


def _resolve_order_from_payment_payload(data: dict[str, Any]) -> Order | None:
    order_public_id = _extract_order_public_id(data)
    if order_public_id:
        return (
            Order.objects.select_for_update()
            .select_related("customer_account")
            .prefetch_related("items__product", "items__price")
            .filter(public_id=order_public_id)
            .first()
        )

    checkout_id = _extract_checkout_id(data)
    if checkout_id:
        return (
            Order.objects.select_for_update()
            .select_related("customer_account")
            .prefetch_related("items__product", "items__price")
            .filter(clerk_checkout_id=checkout_id)
            .first()
        )

    external_id = _extract_payment_external_id(data)
    if external_id:
        return (
            Order.objects.select_for_update()
            .select_related("customer_account")
            .prefetch_related("items__product", "items__price")
            .filter(external_reference=external_id)
            .first()
        )
    return None
