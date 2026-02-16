"""Clerk webhook receiver with Svix signature verification.

Clerk sends webhooks for events like ``user.created``, ``user.updated``,
``user.deleted``, etc. Each event is signed using Svix, so we verify
the signature before processing.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import Profile

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

    entitlements = public_metadata.get("entitlements")
    if isinstance(entitlements, list):
        return [str(item).strip() for item in entitlements if item]
    if isinstance(entitlements, dict):
        return [str(feature).strip() for feature, enabled in entitlements.items() if enabled]
    if isinstance(entitlements, str):
        return [segment.strip() for segment in entitlements.split(",") if segment.strip()]
    return []


def _infer_plan_tier(features: list[str]) -> str:
    normalized = {feature.lower() for feature in features}
    if "enterprise" in normalized:
        return Profile.PlanTier.ENTERPRISE
    if {"pro", "premium", "growth"} & normalized:
        return Profile.PlanTier.PRO
    return Profile.PlanTier.FREE


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


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

def handle_user_created(data: dict[str, Any]) -> None:
    clerk_user_id = str(data.get("id") or "").strip()
    if not clerk_user_id:
        logger.warning("Cannot create profile from webhook without Clerk user id.")
        return

    Profile.objects.update_or_create(
        clerk_user_id=clerk_user_id,
        defaults=_profile_defaults_from_clerk_user(data),
    )
    logger.info("Clerk user created: %s", clerk_user_id)


def handle_user_updated(data: dict[str, Any]) -> None:
    clerk_user_id = str(data.get("id") or "").strip()
    if not clerk_user_id:
        logger.warning("Cannot update profile from webhook without Clerk user id.")
        return

    Profile.objects.update_or_create(
        clerk_user_id=clerk_user_id,
        defaults=_profile_defaults_from_clerk_user(data),
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
    )
    logger.info("Clerk user deleted: %s", clerk_user_id)


def handle_session_created(data: dict[str, Any]) -> None:
    user_id = data.get("user_id", "")
    logger.info("Clerk session created for user: %s", user_id)


EVENT_HANDLERS: dict[str, Any] = {
    "user.created": handle_user_created,
    "user.updated": handle_user_updated,
    "user.deleted": handle_user_deleted,
    "session.created": handle_session_created,
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

        event_type = event.get("type", "")
        data = event.get("data", {})

        handler = EVENT_HANDLERS.get(event_type)
        if handler:
            try:
                handler(data)
            except Exception:
                logger.exception("Error processing webhook event: %s", event_type)
                return JsonResponse({"error": "Internal handler error"}, status=500)
        else:
            logger.debug("Unhandled Clerk webhook event type: %s", event_type)

        return JsonResponse({"status": "ok"})
