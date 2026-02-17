from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone as django_timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..tools.storage.block_storage import (
    BlockStorageConfigurationError,
    BlockStorageError,
    build_digital_asset_download_url,
)
from ..tools.email.resend import (
    resend_is_configured,
    send_fulfillment_order_requested_email,
    send_order_fulfilled_email,
    send_preflight_test_email,
)
from ..models import (
    DigitalAsset,
    DownloadGrant,
    Entitlement,
    FulfillmentOrder,
    Order,
    OrderItem,
    PaymentTransaction,
    Price,
    Product,
    Subscription,
    WebhookEvent,
)
from ..serializers import (
    CustomerAccountSerializer,
    DownloadGrantSerializer,
    EntitlementSerializer,
    FulfillmentOrderSerializer,
    OrderConfirmSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    SubscriptionSerializer,
)
from ..tools.auth.clerk import ClerkClientError, get_clerk_client
from ..webhooks.handlers import handle_billing_subscription_canceled, handle_billing_subscription_upsert
from ..webhooks.helpers import _extract_clerk_user_id_from_subscription_payload
from .helpers import _safe_dict, _safe_str, get_request_customer_account

logger = logging.getLogger(__name__)
SUBSCRIPTION_UPSERT_EVENT_TYPES = {
    "subscription.created",
    "subscription.updated",
    "subscription.active",
    "subscription.pastDue",
    "subscription.paused",
    "billing.subscription.created",
    "billing.subscription.updated",
    "billing.subscription.active",
    "billing.subscription.pastDue",
    "billing.subscription.paused",
}
SUBSCRIPTION_CANCELED_EVENT_TYPES = {
    "subscription.canceled",
    "subscription.cancelled",
    "billing.subscription.canceled",
    "billing.subscription.cancelled",
}
SUBSCRIPTION_BACKFILL_EVENT_LIMIT = 200
BILLING_SYNC_METADATA_KEY = "billing_sync"
BILLING_SYNC_STATE_FRESH = "fresh"
BILLING_SYNC_STATE_SOFT_STALE = "soft_stale"
BILLING_SYNC_STATE_HARD_STALE = "hard_stale"
BILLING_SYNC_REASON_FRESH = "fresh"
BILLING_SYNC_REASON_SOFT_STALE = "soft_stale"
BILLING_SYNC_REASON_HARD_STALE = "hard_stale"
BILLING_SYNC_REASON_NEVER_SYNCED = "never_synced"
BILLING_SYNC_REASON_FRESH_WITH_SYNC_ERROR = "fresh_with_sync_error"
BILLING_SYNC_REASON_SOFT_STALE_WITH_SYNC_ERROR = "soft_stale_with_sync_error"
BILLING_SYNC_REASON_HARD_STALE_WITH_SYNC_ERROR = "hard_stale_with_sync_error"


def _coerce_non_negative_int(raw_value: Any, default: int) -> int:
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return int(default)
    return max(parsed, 0)


def _is_truthy_query_flag(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _billing_sync_windows() -> tuple[int, int]:
    soft_window_seconds = _coerce_non_negative_int(
        getattr(settings, "BILLING_SYNC_SOFT_STALE_SECONDS", 900),
        900,
    )
    hard_ttl_seconds = _coerce_non_negative_int(
        getattr(settings, "BILLING_SYNC_HARD_TTL_SECONDS", 10800),
        10800,
    )
    if hard_ttl_seconds <= soft_window_seconds:
        hard_ttl_seconds = soft_window_seconds + 1
    return soft_window_seconds, hard_ttl_seconds


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
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
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _load_billing_sync_metadata(account) -> dict[str, Any]:
    metadata = account.metadata if isinstance(account.metadata, dict) else {}
    sync_metadata = metadata.get(BILLING_SYNC_METADATA_KEY)
    if isinstance(sync_metadata, dict):
        return dict(sync_metadata)
    return {}


def _save_billing_sync_metadata(account, sync_metadata: dict[str, Any]) -> None:
    metadata = account.metadata if isinstance(account.metadata, dict) else {}
    next_metadata = dict(metadata)
    next_metadata[BILLING_SYNC_METADATA_KEY] = sync_metadata
    if next_metadata == metadata:
        return
    account.metadata = next_metadata
    account.save(update_fields=["metadata", "updated_at"])


def _record_billing_sync_attempt(
    account,
    *,
    attempted_at: datetime,
    success: bool,
    reason_code: str,
    error_code: str = "",
    detail: str = "",
) -> None:
    sync_metadata = _load_billing_sync_metadata(account)
    sync_metadata["last_attempt_at"] = attempted_at.isoformat()
    sync_metadata["last_attempt_succeeded"] = bool(success)
    sync_metadata["last_reason_code"] = str(reason_code or "").strip()
    sync_metadata["last_error_code"] = str(error_code or "").strip()

    sanitized_detail = str(detail or "").strip()
    if sanitized_detail:
        sync_metadata["last_error_detail"] = sanitized_detail[:240]
    else:
        sync_metadata.pop("last_error_detail", None)

    if success:
        sync_metadata["last_success_at"] = attempted_at.isoformat()
        sync_metadata["last_error_code"] = ""
        sync_metadata.pop("last_error_detail", None)

    _save_billing_sync_metadata(account, sync_metadata)


def get_billing_sync_status(account, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or django_timezone.now()
    soft_window_seconds, hard_ttl_seconds = _billing_sync_windows()
    sync_metadata = _load_billing_sync_metadata(account)

    last_attempt_at_raw = sync_metadata.get("last_attempt_at")
    last_success_at_raw = sync_metadata.get("last_success_at")
    last_attempt_at = _parse_iso_datetime(last_attempt_at_raw)
    last_success_at = _parse_iso_datetime(last_success_at_raw)

    last_attempt_succeeded_raw = sync_metadata.get("last_attempt_succeeded")
    last_attempt_succeeded = (
        bool(last_attempt_succeeded_raw)
        if isinstance(last_attempt_succeeded_raw, bool)
        else None
    )
    last_error_code = str(sync_metadata.get("last_error_code") or "").strip()
    last_reason_code = str(sync_metadata.get("last_reason_code") or "").strip()
    age_seconds = None

    if last_success_at is None:
        state = BILLING_SYNC_STATE_HARD_STALE
        reason_code = BILLING_SYNC_REASON_NEVER_SYNCED
        blocking = True
    else:
        age_seconds = max(int((now - last_success_at).total_seconds()), 0)
        if age_seconds <= soft_window_seconds:
            state = BILLING_SYNC_STATE_FRESH
            reason_code = BILLING_SYNC_REASON_FRESH
            blocking = False
        elif age_seconds <= hard_ttl_seconds:
            state = BILLING_SYNC_STATE_SOFT_STALE
            reason_code = BILLING_SYNC_REASON_SOFT_STALE
            blocking = False
        else:
            state = BILLING_SYNC_STATE_HARD_STALE
            reason_code = BILLING_SYNC_REASON_HARD_STALE
            blocking = True

    if (
        state == BILLING_SYNC_STATE_FRESH
        and last_success_at is not None
        and last_attempt_at is not None
        and last_attempt_at > last_success_at
        and last_attempt_succeeded is False
        and last_error_code
    ):
        reason_code = BILLING_SYNC_REASON_FRESH_WITH_SYNC_ERROR
    elif state == BILLING_SYNC_STATE_SOFT_STALE and last_error_code:
        reason_code = BILLING_SYNC_REASON_SOFT_STALE_WITH_SYNC_ERROR
    elif state == BILLING_SYNC_STATE_HARD_STALE and last_error_code:
        reason_code = BILLING_SYNC_REASON_HARD_STALE_WITH_SYNC_ERROR

    if blocking:
        detail = str(
            getattr(
                settings,
                "BILLING_SYNC_HARD_BLOCK_MESSAGE",
                "Billing verification is stale. Retry in a moment.",
            )
            or "Billing verification is stale. Retry in a moment."
        ).strip()
    elif state == BILLING_SYNC_STATE_SOFT_STALE:
        detail = str(
            getattr(
                settings,
                "BILLING_SYNC_SOFT_WARNING_MESSAGE",
                "Billing sync is delayed. Usage enforcement still applies.",
            )
            or "Billing sync is delayed. Usage enforcement still applies."
        ).strip()
    elif reason_code == BILLING_SYNC_REASON_FRESH_WITH_SYNC_ERROR:
        detail = "Recent billing sync attempt failed, but last successful sync is still within the freshness window."
    else:
        detail = "Billing sync is healthy."

    if last_reason_code and reason_code == BILLING_SYNC_REASON_FRESH:
        reason_code = last_reason_code

    return {
        "state": state,
        "blocking": bool(blocking),
        "reason_code": reason_code,
        "error_code": last_error_code or None,
        "detail": detail,
        "last_attempt_at": str(last_attempt_at_raw or "") or None,
        "last_success_at": str(last_success_at_raw or "") or None,
        "age_seconds": age_seconds,
        "soft_window_seconds": soft_window_seconds,
        "hard_ttl_seconds": hard_ttl_seconds,
    }


def _billing_period_end(start_at, billing_period: str):
    if billing_period == Price.BillingPeriod.MONTHLY:
        return start_at + timedelta(days=30)
    if billing_period == Price.BillingPeriod.YEARLY:
        return start_at + timedelta(days=365)
    return None


def _resolve_service_delivery_mode(item: OrderItem) -> str:
    service_offer = getattr(item.product, "service_offer", None)
    metadata = service_offer.metadata if service_offer and isinstance(service_offer.metadata, dict) else {}
    raw_value = str(
        metadata.get("delivery_mode")
        or metadata.get("fulfillment_delivery_mode")
        or ""
    ).strip().lower()
    if raw_value in {"physical", "shipped", FulfillmentOrder.DeliveryMode.PHYSICAL_SHIPPED}:
        return FulfillmentOrder.DeliveryMode.PHYSICAL_SHIPPED
    return FulfillmentOrder.DeliveryMode.DOWNLOADABLE


def _create_pending_download_grant(
    order: Order,
    item: OrderItem,
    sequence: int,
    *,
    reason: str = "pending_fulfillment",
) -> DownloadGrant:
    safe_order_id = str(order.public_id)
    safe_product_name = (item.product_name_snapshot or item.product.name or "Custom deliverable").strip()
    asset = DigitalAsset.objects.create(
        product=item.product,
        title=f"{safe_product_name} deliverable #{sequence}",
        file_path=f"pending/fulfillment/{safe_order_id}/{item.id}-{sequence}.pending",
        version_label="pending",
        is_active=False,
        metadata={
            "pending_fulfillment": True,
            "pending_reason": reason,
            "order_public_id": safe_order_id,
            "order_item_id": item.id,
            "sequence": sequence,
        },
    )
    return DownloadGrant.objects.create(
        customer_account=order.customer_account,
        order_item=item,
        asset=asset,
        max_downloads=5,
        is_active=False,
    )


def _fulfill_order(order: Order) -> Order:
    if order.status == Order.Status.FULFILLED:
        return order

    now = django_timezone.now()
    items = list(
        order.items.select_related("product", "price")
        .prefetch_related("product__assets")
        .order_by("id")
    )

    for item in items:
        product = item.product
        feature_keys = product.feature_keys if isinstance(product.feature_keys, list) else []

        for feature_key in feature_keys:
            Entitlement.objects.get_or_create(
                customer_account=order.customer_account,
                feature_key=str(feature_key).strip().lower(),
                source_type=Entitlement.SourceType.PURCHASE,
                source_reference=str(order.public_id),
                defaults={
                    "starts_at": now,
                    "is_active": True,
                    "metadata": {"order_item_id": item.id},
                },
            )

        if product.product_type == Product.ProductType.DIGITAL:
            active_assets = list(product.assets.filter(is_active=True))
            for asset in active_assets:
                DownloadGrant.objects.get_or_create(
                    customer_account=order.customer_account,
                    order_item=item,
                    asset=asset,
                    defaults={"max_downloads": 5, "is_active": True},
                )
            if not active_assets:
                existing_pending = DownloadGrant.objects.filter(
                    customer_account=order.customer_account,
                    order_item=item,
                    asset__metadata__pending_fulfillment=True,
                ).count()
                needed = max((item.quantity or 1) - existing_pending, 0)
                for offset in range(needed):
                    sequence = existing_pending + offset + 1
                    _create_pending_download_grant(
                        order,
                        item,
                        sequence,
                        reason="missing_digital_asset",
                    )

        if product.product_type == Product.ProductType.SERVICE:
            existing_count = FulfillmentOrder.objects.filter(order_item=item).count()
            needed = max((item.quantity or 1) - existing_count, 0)
            delivery_mode = _resolve_service_delivery_mode(item)
            service_offer = getattr(product, "service_offer", None)
            delivery_days = int(getattr(service_offer, "delivery_days", 0) or 0)
            due_at = now + timedelta(days=delivery_days) if delivery_days > 0 else None
            for offset in range(needed):
                sequence = existing_count + offset + 1
                download_grant = None
                if delivery_mode == FulfillmentOrder.DeliveryMode.DOWNLOADABLE:
                    download_grant = _create_pending_download_grant(
                        order,
                        item,
                        sequence,
                        reason="service_fulfillment",
                    )

                fulfillment_order = FulfillmentOrder.objects.create(
                    customer_account=order.customer_account,
                    order_item=item,
                    product=product,
                    status=FulfillmentOrder.Status.REQUESTED,
                    delivery_mode=delivery_mode,
                    customer_request=order.notes,
                    due_at=due_at,
                    download_grant=download_grant,
                    metadata={
                        "order_public_id": str(order.public_id),
                        "order_item_id": item.id,
                        "sequence": sequence,
                    },
                )
                send_fulfillment_order_requested_email(fulfillment_order)

    order.status = Order.Status.FULFILLED
    order.fulfilled_at = order.fulfilled_at or now
    order.paid_at = order.paid_at or now
    order.save(update_fields=["status", "fulfilled_at", "paid_at", "updated_at"])

    # Best-effort transactional email. Purchase flow should not fail if email delivery fails.
    send_order_fulfilled_email(order)
    return order


def _order_confirm_secret_valid(request) -> bool:
    expected_secret = str(getattr(settings, "ORDER_CONFIRM_SHARED_SECRET", "") or "").strip()
    if not expected_secret:
        return True

    provided_secret = str(request.headers.get("X-Order-Confirm-Secret", "") or "").strip()
    return bool(provided_secret) and secrets.compare_digest(provided_secret, expected_secret)


def confirm_order_payment(
    order: Order,
    *,
    provider: str,
    external_id: str = "",
    clerk_checkout_id: str = "",
    raw_payload: dict[str, Any] | None = None,
) -> tuple[Order, bool]:
    if order.status in {Order.Status.CANCELED, Order.Status.REFUNDED}:
        raise ValidationError("Cannot confirm a canceled or refunded order.")

    if order.status in {Order.Status.PAID, Order.Status.FULFILLED}:
        if order.status == Order.Status.PAID:
            order = _fulfill_order(order)
        return order, True

    raw_payload = raw_payload if isinstance(raw_payload, dict) else {}
    external_id = _safe_str(external_id)
    clerk_checkout_id = _safe_str(clerk_checkout_id)

    now = django_timezone.now()
    order.status = Order.Status.PAID
    order.paid_at = order.paid_at or now
    if clerk_checkout_id and not order.clerk_checkout_id:
        order.clerk_checkout_id = clerk_checkout_id
    if external_id and not order.external_reference:
        order.external_reference = external_id
    order.save(
        update_fields=[
            "status",
            "paid_at",
            "clerk_checkout_id",
            "external_reference",
            "updated_at",
        ]
    )

    if external_id:
        PaymentTransaction.objects.update_or_create(
            provider=provider,
            external_id=external_id,
            order=order,
            defaults={
                "subscription": None,
                "status": PaymentTransaction.Status.SUCCEEDED,
                "amount_cents": order.total_cents,
                "currency": order.currency,
                "raw_payload": raw_payload,
            },
        )
    else:
        PaymentTransaction.objects.create(
            order=order,
            provider=provider,
            status=PaymentTransaction.Status.SUCCEEDED,
            amount_cents=order.total_cents,
            currency=order.currency,
            raw_payload=raw_payload,
        )

    recurring_items = [
        item
        for item in order.items.select_related("product", "price")
        if item.price and item.price.billing_period in {Price.BillingPeriod.MONTHLY, Price.BillingPeriod.YEARLY}
    ]

    for index, item in enumerate(recurring_items):
        existing_subscription = Subscription.objects.filter(
            customer_account=order.customer_account,
            price=item.price,
            metadata__order_public_id=str(order.public_id),
            metadata__order_item_id=item.id,
        ).exists()
        if existing_subscription:
            continue

        period_start = now
        period_end = _billing_period_end(period_start, item.price.billing_period)

        subscription_id = None
        if provider == PaymentTransaction.Provider.CLERK and external_id and index == 0:
            if not Subscription.objects.filter(clerk_subscription_id=external_id).exists():
                subscription_id = external_id

        Subscription.objects.create(
            customer_account=order.customer_account,
            product=item.product,
            price=item.price,
            status=Subscription.Status.ACTIVE,
            clerk_subscription_id=subscription_id,
            current_period_start=period_start,
            current_period_end=period_end,
            metadata={
                "order_public_id": str(order.public_id),
                "order_item_id": item.id,
                "quantity": item.quantity,
            },
        )

    order = _fulfill_order(order)
    return order, False


def _backfill_subscriptions_from_webhook_history(account) -> None:
    event_types = [*SUBSCRIPTION_UPSERT_EVENT_TYPES, *SUBSCRIPTION_CANCELED_EVENT_TYPES]
    recent_events = list(
        WebhookEvent.objects.filter(
            provider=WebhookEvent.Provider.CLERK,
            event_type__in=event_types,
        )
        .order_by("-received_at")[:SUBSCRIPTION_BACKFILL_EVENT_LIMIT]
    )
    if not recent_events:
        return

    allowed_customer_ids = {
        str(account.profile.clerk_user_id or "").strip(),
        str(account.external_customer_id or "").strip(),
    }
    allowed_customer_emails = {
        str(account.billing_email or "").strip().lower(),
        str(account.profile.email or "").strip().lower(),
    }

    def _add_value(values: set[str], raw: object, *, lower: bool = False) -> None:
        normalized = str(raw or "").strip()
        if lower:
            normalized = normalized.lower()
        if normalized:
            values.add(normalized)

    def _payload_matches_account(data: dict[str, Any]) -> bool:
        candidate_ids: set[str] = set()
        candidate_emails: set[str] = set()

        def collect(payload_part: dict[str, Any]) -> None:
            for field in ("id", "user_id", "clerk_user_id", "customer_id", "subscriber_id", "payer_id"):
                _add_value(candidate_ids, payload_part.get(field))
            for field in ("email", "email_address", "billing_email"):
                _add_value(candidate_emails, payload_part.get(field), lower=True)

            nested_user = payload_part.get("user")
            if isinstance(nested_user, dict):
                collect(nested_user)

        collect(data)

        for nested_field in ("payer", "subscriber", "customer"):
            nested = data.get(nested_field)
            if isinstance(nested, dict):
                collect(nested)

        _add_value(candidate_ids, _extract_clerk_user_id_from_subscription_payload(data))

        return bool(
            (candidate_ids & allowed_customer_ids)
            or (candidate_emails & allowed_customer_emails)
        )

    for event in reversed(recent_events):
        payload = event.payload if isinstance(event.payload, dict) else {}
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        if not isinstance(data, dict):
            continue

        if not _payload_matches_account(data):
            continue

        if event.event_type in SUBSCRIPTION_CANCELED_EVENT_TYPES:
            handle_billing_subscription_canceled(data)
        else:
            handle_billing_subscription_upsert(data)


def _to_plain_data(value: Any, *, _depth: int = 0) -> Any:
    if _depth > 8:
        return value

    if isinstance(value, dict):
        return {str(key): _to_plain_data(raw, _depth=_depth + 1) for key, raw in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_to_plain_data(item, _depth=_depth + 1) for item in value]

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _to_plain_data(model_dump(), _depth=_depth + 1)
        except Exception:
            logger.debug("Failed model_dump() when normalizing Clerk payload object: %s", type(value).__name__)

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return _to_plain_data(to_dict(), _depth=_depth + 1)
        except Exception:
            logger.debug("Failed to_dict() when normalizing Clerk payload object: %s", type(value).__name__)

    values = getattr(value, "__dict__", None)
    if isinstance(values, dict):
        return {
            str(key): _to_plain_data(raw, _depth=_depth + 1)
            for key, raw in values.items()
            if not str(key).startswith("_")
        }

    return value


def _looks_like_subscription_payload(payload: dict[str, Any]) -> bool:
    subscription_id = str(payload.get("id") or payload.get("subscription_id") or "").strip()
    if subscription_id.startswith("sub_"):
        return True

    status = str(payload.get("status") or "").strip()
    if not status:
        return False

    subscription_keys = (
        "current_period_start",
        "current_period_end",
        "period_start",
        "period_end",
        "starts_at",
        "ends_at",
        "cancel_at_period_end",
        "canceled_at",
        "cancelled_at",
        "plan",
        "plan_id",
        "price_id",
        "items",
        "subscription_items",
    )
    return any(key in payload for key in subscription_keys)


def _append_subscription_payload_if_dict(payloads: list[dict[str, Any]], candidate: Any) -> None:
    if isinstance(candidate, dict) and _looks_like_subscription_payload(candidate):
        payloads.append(candidate)


def _extract_subscription_payloads_from_clerk_response(raw_response: Any) -> list[dict[str, Any]]:
    normalized = _to_plain_data(raw_response)
    roots: list[dict[str, Any]] = []
    if isinstance(normalized, dict):
        roots.append(normalized)
        data = normalized.get("data")
        if isinstance(data, dict):
            roots.append(data)
        elif isinstance(data, list):
            roots.extend(item for item in data if isinstance(item, dict))
    elif isinstance(normalized, list):
        roots.extend(item for item in normalized if isinstance(item, dict))
    else:
        return []

    payloads: list[dict[str, Any]] = []
    for root in roots:
        _append_subscription_payload_if_dict(payloads, root)

        direct_subscription = root.get("subscription")
        _append_subscription_payload_if_dict(payloads, direct_subscription)

        billing = root.get("billing")
        if isinstance(billing, dict):
            nested_subscription = billing.get("subscription")
            _append_subscription_payload_if_dict(payloads, nested_subscription)

            nested_billing_subscriptions = billing.get("subscriptions")
            if isinstance(nested_billing_subscriptions, list):
                for payload in nested_billing_subscriptions:
                    _append_subscription_payload_if_dict(payloads, payload)

        nested_subscriptions = root.get("subscriptions")
        if isinstance(nested_subscriptions, list):
            for payload in nested_subscriptions:
                _append_subscription_payload_if_dict(payloads, payload)

    deduped_payloads: list[dict[str, Any]] = []
    seen: set[str] = set()
    for payload in payloads:
        key = str(payload.get("id") or payload.get("subscription_id") or payload)
        if key in seen:
            continue
        seen.add(key)
        deduped_payloads.append(payload)

    return deduped_payloads


def _clerk_response_explicitly_has_no_subscription(raw_response: Any) -> bool:
    normalized = _to_plain_data(raw_response)
    roots: list[dict[str, Any]] = []
    if isinstance(normalized, dict):
        roots.append(normalized)
        data = normalized.get("data")
        if isinstance(data, dict):
            roots.append(data)
        elif isinstance(data, list):
            roots.extend(item for item in data if isinstance(item, dict))
    elif isinstance(normalized, list):
        roots.extend(item for item in normalized if isinstance(item, dict))
    else:
        return False

    for root in roots:
        if _looks_like_subscription_payload(root):
            continue

        if "subscription" in root and root.get("subscription") is None:
            return True

        billing = root.get("billing")
        if isinstance(billing, dict):
            if "subscription" in billing and billing.get("subscription") is None:
                return True

            billing_subscriptions = billing.get("subscriptions")
            if isinstance(billing_subscriptions, list):
                has_subscription_payload = any(
                    isinstance(payload, dict) and _looks_like_subscription_payload(payload)
                    for payload in billing_subscriptions
                )
                if not has_subscription_payload:
                    return True

        if "subscriptions" in root and isinstance(root.get("subscriptions"), list):
            root_subscriptions = root.get("subscriptions") or []
            has_subscription_payload = any(
                isinstance(payload, dict) and _looks_like_subscription_payload(payload)
                for payload in root_subscriptions
            )
            if not has_subscription_payload:
                return True

    return False


def _backfill_subscriptions_from_clerk_api(account) -> dict[str, Any]:
    clerk_user_id = str(account.profile.clerk_user_id or account.external_customer_id or "").strip()
    if not clerk_user_id:
        return {
            "success": False,
            "reason_code": "missing_clerk_user_id",
            "error_code": "missing_clerk_user_id",
            "detail": "Account is missing Clerk user id.",
        }

    try:
        client = get_clerk_client()
        response = client.users.get_billing_subscription(user_id=clerk_user_id)
    except ClerkClientError as exc:
        logger.debug(
            "Skipping direct Clerk subscription sync for account %s: %s",
            account.id,
            exc,
        )
        return {
            "success": False,
            "reason_code": "clerk_client_unavailable",
            "error_code": "clerk_client_unavailable",
            "detail": str(exc),
        }
    except Exception as exc:
        logger.exception(
            "Direct Clerk subscription sync failed for account %s (clerk_user_id=%s).",
            account.id,
            clerk_user_id,
        )
        return {
            "success": False,
            "reason_code": "clerk_api_error",
            "error_code": "clerk_api_error",
            "detail": str(exc),
        }

    subscription_payloads = _extract_subscription_payloads_from_clerk_response(response)
    if not subscription_payloads:
        if _clerk_response_explicitly_has_no_subscription(response):
            existing_rows = Subscription.objects.filter(customer_account=account).exclude(clerk_subscription_id__isnull=True)
            for row in existing_rows:
                if row.status == Subscription.Status.CANCELED:
                    continue
                handle_billing_subscription_canceled(
                    {
                        "id": row.clerk_subscription_id,
                        "user_id": clerk_user_id,
                        "canceled_at": django_timezone.now().isoformat(),
                    }
                )
            return {
                "success": True,
                "reason_code": "no_active_subscription",
                "error_code": "",
                "detail": "",
                "synced_count": 0,
            }
        logger.debug(
            "Direct Clerk subscription sync returned no subscription payloads for account %s.",
            account.id,
        )
        return {
            "success": True,
            "reason_code": "no_subscription_payload",
            "error_code": "",
            "detail": "",
            "synced_count": 0,
        }

    synced_count = 0
    failed_count = 0
    for payload in subscription_payloads:
        normalized_payload = dict(payload)
        if not _extract_clerk_user_id_from_subscription_payload(normalized_payload):
            normalized_payload["user_id"] = clerk_user_id

        try:
            handle_billing_subscription_upsert(normalized_payload)
            synced_count += 1
        except Exception:
            failed_count += 1
            logger.exception(
                "Failed to upsert Clerk billing subscription payload for account %s during direct sync.",
                account.id,
            )

    if synced_count:
        logger.info(
            "Direct Clerk subscription sync upserted %s payload(s) for account %s.",
            synced_count,
            account.id,
        )

    if synced_count == 0 and failed_count > 0:
        return {
            "success": False,
            "reason_code": "subscription_upsert_failed",
            "error_code": "subscription_upsert_failed",
            "detail": "Clerk subscription payloads could not be applied to local records.",
            "synced_count": 0,
        }

    if failed_count > 0:
        return {
            "success": True,
            "reason_code": "synced_with_partial_errors",
            "error_code": "",
            "detail": "",
            "synced_count": synced_count,
        }

    return {
        "success": True,
        "reason_code": "synced",
        "error_code": "",
        "detail": "",
        "synced_count": synced_count,
    }


def ensure_billing_sync(account, *, force: bool = False) -> dict[str, Any]:
    now = django_timezone.now()
    status_before = get_billing_sync_status(account, now=now)
    if not force and status_before["state"] == BILLING_SYNC_STATE_FRESH:
        return status_before

    _backfill_subscriptions_from_webhook_history(account)
    outcome = _backfill_subscriptions_from_clerk_api(account)
    attempted_at = django_timezone.now()
    _record_billing_sync_attempt(
        account,
        attempted_at=attempted_at,
        success=bool(outcome.get("success")),
        reason_code=str(outcome.get("reason_code") or ""),
        error_code=str(outcome.get("error_code") or ""),
        detail=str(outcome.get("detail") or ""),
    )
    return get_billing_sync_status(account, now=attempted_at)


class AccountCustomerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        account = get_request_customer_account(request)
        return Response(CustomerAccountSerializer(account).data)

    def patch(self, request):
        account = get_request_customer_account(request)
        serializer = CustomerAccountSerializer(account, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AccountPreflightEmailTestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not resend_is_configured():
            logger.warning("Preflight email test requested without Resend configuration.")
            return Response(
                {
                    "sent": False,
                    "detail": (
                        "Resend is not configured. Set RESEND_API_KEY and RESEND_FROM_EMAIL in backend/.env."
                    ),
                },
                status=400,
            )

        account = get_request_customer_account(request)
        sent, recipient = send_preflight_test_email(account)
        if not sent:
            logger.warning("Preflight email send failed for account %s.", account.id)
            return Response(
                {
                    "sent": False,
                    "detail": (
                        "Preflight email failed. Check sender verification, recipient email, and backend logs."
                    ),
                },
                status=502,
            )

        sent_at = django_timezone.now()
        metadata = account.metadata if isinstance(account.metadata, dict) else {}
        metadata["preflight_email_last_sent_at"] = sent_at.isoformat()
        metadata["preflight_email_last_recipient"] = recipient
        account.metadata = metadata
        account.save(update_fields=["metadata", "updated_at"])
        logger.info("Preflight email send succeeded for account %s to %s.", account.id, recipient)

        return Response(
            {
                "sent": True,
                "detail": f"Preflight email sent to {recipient}.",
                "recipient_email": recipient,
                "sent_at": sent_at.isoformat(),
            }
        )


class AccountOrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        account = get_request_customer_account(self.request)
        return (
            Order.objects.filter(customer_account=account)
            .prefetch_related("items__product", "items__price")
            .order_by("-created_at")
        )


class AccountOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "checkout_create"

    @transaction.atomic
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        price = get_object_or_404(
            Price.objects.select_related("product"),
            pk=serializer.validated_data["price_id"],
            is_active=True,
            product__visibility=Product.Visibility.PUBLISHED,
        )
        quantity = serializer.validated_data["quantity"]
        notes = _safe_str(serializer.validated_data.get("notes"))

        subtotal_cents = price.amount_cents * quantity
        account = get_request_customer_account(request)

        order = Order.objects.create(
            customer_account=account,
            status=Order.Status.PENDING_PAYMENT,
            currency=price.currency,
            subtotal_cents=subtotal_cents,
            tax_cents=0,
            total_cents=subtotal_cents,
            notes=notes,
        )
        OrderItem.objects.create(
            order=order,
            product=price.product,
            price=price,
            quantity=quantity,
            unit_amount_cents=price.amount_cents,
            product_name_snapshot=price.product.name,
            price_name_snapshot=price.name or price.get_billing_period_display(),
        )

        checkout_url = ""
        metadata = price.metadata if isinstance(price.metadata, dict) else {}
        checkout_url = _safe_str(metadata.get("checkout_url"))
        logger.info(
            "Created pending order %s for account %s (price_id=%s, quantity=%s).",
            order.public_id,
            account.id,
            price.id,
            quantity,
        )

        return Response(
            {
                "order": OrderSerializer(order).data,
                "checkout": {
                    "checkout_url": checkout_url,
                    "provider": "clerk",
                },
            },
            status=201,
        )


class AccountOrderConfirmView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "order_confirm"

    @transaction.atomic
    def post(self, request, public_id):
        account = get_request_customer_account(request)
        order = get_object_or_404(
            Order.objects.select_for_update()
            .select_related("customer_account")
            .prefetch_related("items__product", "items__price"),
            public_id=public_id,
            customer_account=account,
        )

        serializer = OrderConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data["provider"]
        external_id = _safe_str(serializer.validated_data.get("external_id"))
        clerk_checkout_id = _safe_str(serializer.validated_data.get("clerk_checkout_id"))
        raw_payload = _safe_dict(serializer.validated_data.get("raw_payload"))

        if order.status == Order.Status.PENDING_PAYMENT:
            if provider == PaymentTransaction.Provider.MANUAL and not settings.ORDER_CONFIRM_ALLOW_MANUAL:
                return Response(
                    {
                        "detail": (
                            "Manual order confirmation is disabled. "
                            "Set ORDER_CONFIRM_ALLOW_MANUAL=True for controlled development use."
                        )
                    },
                    status=403,
                )
            if (
                provider == PaymentTransaction.Provider.CLERK
                and not settings.ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM
            ):
                return Response(
                    {
                        "detail": (
                            "Direct client-side Clerk confirmation is disabled. "
                            "Wait for a verified payment webhook to mark this order paid."
                        ),
                        "pending_verification": True,
                    },
                    status=409,
                )
            if not _order_confirm_secret_valid(request):
                return Response(
                    {
                        "detail": (
                            "Invalid order confirmation secret. "
                            "Pass X-Order-Confirm-Secret with a valid server-side value."
                        )
                    },
                    status=403,
                )

        order, already_confirmed = confirm_order_payment(
            order,
            provider=provider,
            external_id=external_id,
            clerk_checkout_id=clerk_checkout_id,
            raw_payload=raw_payload,
        )
        logger.info(
            "Order confirmation requested for %s by account %s via %s (already_confirmed=%s).",
            order.public_id,
            account.id,
            provider,
            already_confirmed,
        )
        return Response({"order": OrderSerializer(order).data, "already_confirmed": already_confirmed})


class AccountSubscriptionListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        account = get_request_customer_account(self.request)
        return Subscription.objects.filter(customer_account=account).select_related("product", "price")


class AccountSubscriptionSyncStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        account = get_request_customer_account(request)
        refresh_requested = _is_truthy_query_flag(request.query_params.get("refresh"))
        if refresh_requested:
            return Response(ensure_billing_sync(account, force=True))
        return Response(get_billing_sync_status(account))


class AccountEntitlementListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EntitlementSerializer

    def get_queryset(self):
        account = get_request_customer_account(self.request)
        queryset = Entitlement.objects.filter(customer_account=account).order_by("feature_key")
        current_only = str(self.request.query_params.get("current", "true")).lower() in {"1", "true", "yes"}
        if current_only:
            now = django_timezone.now()
            queryset = queryset.filter(
                is_active=True,
                starts_at__lte=now,
            ).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        return queryset


class AccountDownloadGrantListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DownloadGrantSerializer

    def get_queryset(self):
        account = get_request_customer_account(self.request)
        return (
            DownloadGrant.objects.filter(customer_account=account)
            .select_related("asset", "asset__product", "order_item")
            .order_by("-created_at")
        )


class AccountDownloadAccessView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "download_access"

    def post(self, request, token):
        account = get_request_customer_account(request)
        grant = get_object_or_404(
            DownloadGrant.objects.select_related("asset", "asset__product"),
            token=token,
            customer_account=account,
        )

        if not grant.can_download:
            logger.warning("Blocked download attempt for inactive grant %s (account=%s).", grant.token, account.id)
            return Response(
                {
                    "detail": "Download grant is inactive, expired, or out of attempts.",
                    "grant": DownloadGrantSerializer(grant).data,
                },
                status=403,
            )

        try:
            download_url = build_digital_asset_download_url(grant.asset.file_path)
        except BlockStorageConfigurationError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except BlockStorageError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        now = django_timezone.now()
        grant.download_count += 1
        grant.last_downloaded_at = now
        grant.save(update_fields=["download_count", "last_downloaded_at", "updated_at"])
        logger.info("Created download link for grant %s (account=%s).", grant.token, account.id)

        return Response(
            {
                "download_url": download_url,
                "grant": DownloadGrantSerializer(grant).data,
            }
        )


class AccountFulfillmentOrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FulfillmentOrderSerializer

    def get_queryset(self):
        account = get_request_customer_account(self.request)
        return (
            FulfillmentOrder.objects.filter(customer_account=account)
            .select_related("product", "order_item", "download_grant", "download_grant__asset")
            .order_by("-created_at")
        )


class AccountBookingListCreateView(AccountFulfillmentOrderListView):
    """
    Deprecated endpoint alias.
    Keep GET compatibility for existing clients on /account/bookings/.
    """
