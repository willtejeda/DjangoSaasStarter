from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone as django_timezone

from ..models import CustomerAccount, Entitlement, Order, PaymentTransaction, Profile, Subscription
from .helpers import (
    _extract_checkout_id,
    _extract_clerk_user_id_from_subscription_payload,
    _extract_payment_external_id,
    _extract_payment_status,
    _find_price_from_clerk_ids,
    _is_success_status,
    _map_payment_transaction_status,
    _map_subscription_status,
    _normalize_text,
    _profile_defaults_from_clerk_user,
    _resolve_customer_account_from_clerk_user_id,
    _resolve_order_from_payment_payload,
    _safe_datetime,
)

logger = logging.getLogger(__name__)


def _sync_plan_entitlements(
    account: CustomerAccount,
    feature_keys: list[str],
    source_reference: str,
    active: bool,
):
    normalized_features = {
        str(feature or "").strip().lower().replace(" ", "_")
        for feature in feature_keys
        if str(feature or "").strip()
    }

    now = django_timezone.now()
    existing = list(
        Entitlement.objects.filter(
            customer_account=account,
            source_type=Entitlement.SourceType.PLAN,
            source_reference=source_reference,
        )
    )

    existing_map = {row.feature_key: row for row in existing}

    for feature in normalized_features:
        row = existing_map.get(feature)
        if row is None:
            Entitlement.objects.create(
                customer_account=account,
                feature_key=feature,
                source_type=Entitlement.SourceType.PLAN,
                source_reference=source_reference,
                starts_at=now,
                ends_at=None if active else now,
                is_active=active,
            )
            continue

        updates: list[str] = []
        if row.is_active != active:
            row.is_active = active
            updates.append("is_active")
        if active and row.ends_at is not None:
            row.ends_at = None
            updates.append("ends_at")
        if not active and row.ends_at is None:
            row.ends_at = now
            updates.append("ends_at")
        if updates:
            row.save(update_fields=[*updates, "updated_at"])

    for feature, row in existing_map.items():
        if feature in normalized_features:
            continue
        updates: list[str] = []
        if row.is_active:
            row.is_active = False
            updates.append("is_active")
        if row.ends_at is None:
            row.ends_at = now
            updates.append("ends_at")
        if updates:
            row.save(update_fields=[*updates, "updated_at"])


def handle_user_created(data: dict[str, Any]) -> None:
    clerk_user_id = str(data.get("id") or "").strip()
    if not clerk_user_id:
        logger.warning("Cannot create profile from webhook without Clerk user id.")
        return

    profile, _ = Profile.objects.update_or_create(
        clerk_user_id=clerk_user_id,
        defaults=_profile_defaults_from_clerk_user(data),
    )

    CustomerAccount.objects.update_or_create(
        profile=profile,
        defaults={
            "external_customer_id": profile.clerk_user_id,
            "billing_email": profile.email,
            "full_name": profile.display_name,
        },
    )
    logger.info("Clerk user created: %s", clerk_user_id)


def handle_user_updated(data: dict[str, Any]) -> None:
    clerk_user_id = str(data.get("id") or "").strip()
    if not clerk_user_id:
        logger.warning("Cannot update profile from webhook without Clerk user id.")
        return

    profile, _ = Profile.objects.update_or_create(
        clerk_user_id=clerk_user_id,
        defaults=_profile_defaults_from_clerk_user(data),
    )

    CustomerAccount.objects.update_or_create(
        profile=profile,
        defaults={
            "external_customer_id": profile.clerk_user_id,
            "billing_email": profile.email,
            "full_name": profile.display_name,
        },
    )
    logger.info("Clerk user updated: %s", clerk_user_id)


def handle_user_deleted(data: dict[str, Any]) -> None:
    clerk_user_id = str(data.get("id") or "").strip()
    if not clerk_user_id:
        logger.warning("Cannot deactivate profile from webhook without Clerk user id.")
        return

    Profile.objects.filter(clerk_user_id=clerk_user_id).update(
        is_active=False,
        email="",
        first_name="",
        last_name="",
        image_url="",
        plan_tier=Profile.PlanTier.FREE,
        billing_features=[],
        metadata={},
    )
    logger.info("Clerk user deleted: %s", clerk_user_id)


def handle_session_created(data: dict[str, Any]) -> None:
    user_id = data.get("user_id", "")
    logger.info("Clerk session created for user: %s", user_id)


def handle_billing_subscription_upsert(data: dict[str, Any]) -> None:
    clerk_subscription_id = str(data.get("id") or data.get("subscription_id") or "").strip() or None
    clerk_user_id = _extract_clerk_user_id_from_subscription_payload(data)
    account = _resolve_customer_account_from_clerk_user_id(clerk_user_id)

    if account is None:
        logger.warning("Skipping billing subscription sync: unknown Clerk user '%s'.", clerk_user_id)
        return

    price = _find_price_from_clerk_ids(data)
    status = _map_subscription_status(str(data.get("status") or ""))
    period_start = _safe_datetime(
        data.get("current_period_start")
        or data.get("period_start")
        or data.get("starts_at")
    )
    period_end = _safe_datetime(
        data.get("current_period_end")
        or data.get("period_end")
        or data.get("ends_at")
    )

    defaults = {
        "customer_account": account,
        "product": price.product if price else None,
        "price": price,
        "status": status,
        "current_period_start": period_start,
        "current_period_end": period_end,
        "cancel_at_period_end": bool(data.get("cancel_at_period_end", False)),
        "canceled_at": _safe_datetime(data.get("canceled_at") or data.get("cancelled_at")),
        "metadata": data if isinstance(data, dict) else {},
    }

    if clerk_subscription_id:
        subscription, _ = Subscription.objects.update_or_create(
            clerk_subscription_id=clerk_subscription_id,
            defaults=defaults,
        )
    else:
        subscription = Subscription.objects.create(**defaults)

    feature_keys: list[str] = []
    if subscription.product and isinstance(subscription.product.feature_keys, list):
        feature_keys = subscription.product.feature_keys

    source_reference = subscription.clerk_subscription_id or f"local-sub-{subscription.pk}"
    is_active = subscription.status in {Subscription.Status.ACTIVE, Subscription.Status.TRIALING}
    _sync_plan_entitlements(account, feature_keys, source_reference=source_reference, active=is_active)

    logger.info(
        "Synced billing subscription %s for account %s with status %s",
        source_reference,
        account.id,
        subscription.status,
    )


def handle_billing_subscription_canceled(data: dict[str, Any]) -> None:
    clerk_subscription_id = str(data.get("id") or data.get("subscription_id") or "").strip()
    if clerk_subscription_id:
        Subscription.objects.filter(clerk_subscription_id=clerk_subscription_id).update(
            status=Subscription.Status.CANCELED,
            canceled_at=_safe_datetime(data.get("canceled_at") or data.get("cancelled_at"))
            or django_timezone.now(),
            cancel_at_period_end=True,
            metadata=data if isinstance(data, dict) else {},
        )

    clerk_user_id = _extract_clerk_user_id_from_subscription_payload(data)
    account = _resolve_customer_account_from_clerk_user_id(clerk_user_id)
    if account is None:
        return

    source_reference = clerk_subscription_id or ""
    if source_reference:
        _sync_plan_entitlements(account, [], source_reference=source_reference, active=False)


def _upsert_payment_transaction_for_payload(
    *,
    order: Order,
    provider: str,
    external_id: str,
    raw_status: str,
    payload: dict[str, Any],
) -> None:
    transaction_status = _map_payment_transaction_status(raw_status)
    defaults = {
        "subscription": None,
        "status": transaction_status,
        "amount_cents": order.total_cents,
        "currency": order.currency,
        "raw_payload": payload if isinstance(payload, dict) else {},
    }

    if external_id:
        PaymentTransaction.objects.update_or_create(
            provider=provider,
            external_id=external_id,
            order=order,
            defaults=defaults,
        )
        return

    PaymentTransaction.objects.create(
        order=order,
        provider=provider,
        external_id="",
        **defaults,
    )


def _confirm_order_from_payment_payload(
    data: dict[str, Any],
    *,
    fallback_checkout_id: str = "",
) -> None:
    if not isinstance(data, dict):
        return

    raw_status = _extract_payment_status(data)
    checkout_id = _extract_checkout_id(data) or _normalize_text(fallback_checkout_id)
    external_id = _extract_payment_external_id(data) or checkout_id

    with transaction.atomic():
        order = _resolve_order_from_payment_payload(data)
        if order is None:
            logger.warning(
                "Skipping payment webhook sync: could not resolve order for payment payload id=%s checkout=%s",
                external_id,
                checkout_id,
            )
            return

        _upsert_payment_transaction_for_payload(
            order=order,
            provider=PaymentTransaction.Provider.CLERK,
            external_id=external_id,
            raw_status=raw_status,
            payload=data,
        )

        if not _is_success_status(raw_status):
            return

        try:
            from ..views import confirm_order_payment

            confirm_order_payment(
                order,
                provider=PaymentTransaction.Provider.CLERK,
                external_id=external_id,
                clerk_checkout_id=checkout_id,
                raw_payload=data,
            )
        except Exception:
            logger.exception("Failed to confirm order from payment webhook payload.")
            raise


def handle_billing_payment_attempt_upsert(data: dict[str, Any]) -> None:
    _confirm_order_from_payment_payload(data)


def handle_billing_checkout_upsert(data: dict[str, Any]) -> None:
    _confirm_order_from_payment_payload(data, fallback_checkout_id=_normalize_text(data.get("id")))


EVENT_HANDLERS: dict[str, Any] = {
    "user.created": handle_user_created,
    "user.updated": handle_user_updated,
    "user.deleted": handle_user_deleted,
    "session.created": handle_session_created,
    # Clerk Billing subscription event names.
    "subscription.created": handle_billing_subscription_upsert,
    "subscription.updated": handle_billing_subscription_upsert,
    "subscription.active": handle_billing_subscription_upsert,
    "subscription.pastDue": handle_billing_subscription_upsert,
    "subscription.paused": handle_billing_subscription_upsert,
    "subscription.canceled": handle_billing_subscription_canceled,
    "subscription.cancelled": handle_billing_subscription_canceled,
    # Compatibility aliases for prefixed billing subscription names.
    "billing.subscription.created": handle_billing_subscription_upsert,
    "billing.subscription.updated": handle_billing_subscription_upsert,
    "billing.subscription.active": handle_billing_subscription_upsert,
    "billing.subscription.pastDue": handle_billing_subscription_upsert,
    "billing.subscription.paused": handle_billing_subscription_upsert,
    "billing.subscription.canceled": handle_billing_subscription_canceled,
    "billing.subscription.cancelled": handle_billing_subscription_canceled,
    # New Clerk Billing event names.
    "paymentAttempt.created": handle_billing_payment_attempt_upsert,
    "paymentAttempt.updated": handle_billing_payment_attempt_upsert,
    "checkout.created": handle_billing_checkout_upsert,
    "checkout.updated": handle_billing_checkout_upsert,
    # Compatibility aliases for snake_case or prefixed providers.
    "payment_attempt.created": handle_billing_payment_attempt_upsert,
    "payment_attempt.updated": handle_billing_payment_attempt_upsert,
    "billing.payment_attempt.created": handle_billing_payment_attempt_upsert,
    "billing.payment_attempt.updated": handle_billing_payment_attempt_upsert,
    "billing.checkout.created": handle_billing_checkout_upsert,
    "billing.checkout.updated": handle_billing_checkout_upsert,
}
