"""Clerk webhook receiver with Svix signature verification."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from django.conf import settings
from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from django.utils import timezone as django_timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .billing import extract_billing_features, infer_plan_tier
from .models import CustomerAccount, Entitlement, Price, Profile, Subscription, WebhookEvent

logger = logging.getLogger(__name__)


class WebhookVerificationError(RuntimeError):
    pass


def _verify_webhook(payload: bytes, headers: dict[str, str]) -> dict[str, Any]:
    """Verify the Svix signature and return the parsed event payload."""
    signing_secret = getattr(settings, "CLERK_WEBHOOK_SIGNING_SECRET", "")
    if not signing_secret:
        raise WebhookVerificationError("CLERK_WEBHOOK_SIGNING_SECRET is not configured.")

    try:
        from svix.webhooks import Webhook
    except ImportError as exc:
        raise WebhookVerificationError(
            "svix package is required for webhook verification. "
            "Run: pip install svix"
        ) from exc

    wh = Webhook(signing_secret)
    try:
        event = wh.verify(payload, headers)
    except Exception as exc:
        raise WebhookVerificationError(
            f"Webhook signature verification failed: {exc}"
        ) from exc

    return event


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
    ]

    subscriber = data.get("subscriber")
    if isinstance(subscriber, dict):
        candidates.extend([subscriber.get("id"), subscriber.get("user_id")])

    user = data.get("user")
    if isinstance(user, dict):
        candidates.extend([user.get("id"), user.get("user_id")])

    for value in candidates:
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    return ""


def _resolve_customer_account_from_clerk_user_id(clerk_user_id: str) -> CustomerAccount | None:
    if not clerk_user_id:
        return None

    profile = Profile.objects.filter(clerk_user_id=clerk_user_id).first()
    if profile is None:
        return None

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
    normalized = str(raw_status or "").strip().lower()
    mapping = {
        "active": Subscription.Status.ACTIVE,
        "trialing": Subscription.Status.TRIALING,
        "past_due": Subscription.Status.PAST_DUE,
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


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

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


EVENT_HANDLERS: dict[str, Any] = {
    "user.created": handle_user_created,
    "user.updated": handle_user_updated,
    "user.deleted": handle_user_deleted,
    "session.created": handle_session_created,
    "billing.subscription.created": handle_billing_subscription_upsert,
    "billing.subscription.updated": handle_billing_subscription_upsert,
    "billing.subscription.active": handle_billing_subscription_upsert,
    "billing.subscription.paused": handle_billing_subscription_upsert,
    "billing.subscription.canceled": handle_billing_subscription_canceled,
    "billing.subscription.cancelled": handle_billing_subscription_canceled,
}


@method_decorator(csrf_exempt, name="dispatch")
class ClerkWebhookView(View):
    """Receive and process Clerk webhook events."""

    def post(self, request: HttpRequest) -> JsonResponse:
        svix_headers = {
            "svix-id": request.headers.get("svix-id", ""),
            "svix-timestamp": request.headers.get("svix-timestamp", ""),
            "svix-signature": request.headers.get("svix-signature", ""),
        }

        try:
            event = _verify_webhook(request.body, svix_headers)
        except WebhookVerificationError as exc:
            logger.warning("Webhook verification failed: %s", exc)
            return JsonResponse({"error": str(exc)}, status=400)

        event_id = str(svix_headers.get("svix-id") or event.get("id") or "").strip()
        event_type = str(event.get("type") or "").strip()
        data = event.get("data", {})
        payload = event if isinstance(event, dict) else {"raw": str(event)}

        webhook_event = None
        if event_id:
            try:
                webhook_event, created = WebhookEvent.objects.get_or_create(
                    provider=WebhookEvent.Provider.CLERK,
                    event_id=event_id,
                    defaults={
                        "event_type": event_type or "unknown",
                        "payload": payload,
                        "status": WebhookEvent.Status.RECEIVED,
                    },
                )

                if not created and webhook_event.status in {
                    WebhookEvent.Status.PROCESSED,
                    WebhookEvent.Status.IGNORED,
                }:
                    return JsonResponse({"status": "ok", "deduplicated": True})

                if webhook_event.event_type != event_type or webhook_event.payload != payload:
                    webhook_event.event_type = event_type or webhook_event.event_type
                    webhook_event.payload = payload
                    webhook_event.status = WebhookEvent.Status.RECEIVED
                    webhook_event.error_message = ""
                    webhook_event.save(
                        update_fields=[
                            "event_type",
                            "payload",
                            "status",
                            "error_message",
                        ]
                    )
            except Exception:
                logger.debug(
                    "Skipping webhook event metadata persistence for %s",
                    event_id,
                )

        handler = EVENT_HANDLERS.get(event_type)
        if handler:
            try:
                handler(data if isinstance(data, dict) else {})
                if webhook_event is not None:
                    webhook_event.status = WebhookEvent.Status.PROCESSED
                    webhook_event.processed_at = django_timezone.now()
                    webhook_event.error_message = ""
                    webhook_event.save(update_fields=["status", "processed_at", "error_message"])
            except Exception as exc:
                logger.exception("Error processing webhook event: %s", event_type)
                if webhook_event is not None:
                    webhook_event.status = WebhookEvent.Status.FAILED
                    webhook_event.processed_at = django_timezone.now()
                    webhook_event.error_message = str(exc)
                    webhook_event.save(update_fields=["status", "processed_at", "error_message"])
                return JsonResponse({"error": "Internal handler error"}, status=500)
        else:
            logger.debug("Unhandled Clerk webhook event type: %s", event_type)
            if webhook_event is not None:
                webhook_event.status = WebhookEvent.Status.IGNORED
                webhook_event.processed_at = django_timezone.now()
                webhook_event.error_message = ""
                webhook_event.save(update_fields=["status", "processed_at", "error_message"])

        return JsonResponse({"status": "ok"})
