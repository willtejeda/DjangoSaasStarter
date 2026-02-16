"""Clerk webhook receiver with Svix signature verification.

Clerk sends webhooks for events like ``user.created``, ``user.updated``,
``user.deleted``, etc.  Each event is signed using Svix, so we verify
the signature before processing.

Setup:
    1. Go to Clerk Dashboard → Webhooks → Create Endpoint
    2. Set the URL to ``https://your-domain.com/api/webhooks/clerk/``
    3. Copy the **Signing Secret** and set ``CLERK_WEBHOOK_SIGNING_SECRET`` in ``.env``
    4. Select which events to subscribe to
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


class WebhookVerificationError(RuntimeError):
    pass


def _verify_webhook(payload: bytes, headers: dict[str, str]) -> dict[str, Any]:
    """Verify the Svix signature and return the parsed event payload."""
    signing_secret = getattr(settings, "CLERK_WEBHOOK_SIGNING_SECRET", "")
    if not signing_secret:
        raise WebhookVerificationError(
            "CLERK_WEBHOOK_SIGNING_SECRET is not configured."
        )

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
        raise WebhookVerificationError(f"Webhook signature verification failed: {exc}") from exc

    return event


# ---------------------------------------------------------------------------
# Event handlers — add your business logic here
# ---------------------------------------------------------------------------

def handle_user_created(data: dict[str, Any]) -> None:
    """Handle ``user.created`` event.

    This is where you would sync the new Clerk user to your database,
    create a Supabase profile row, provision resources, send a welcome
    email, etc.
    """
    clerk_user_id = data.get("id", "")
    email_addresses = data.get("email_addresses", [])
    primary_email = next(
        (e["email_address"] for e in email_addresses if e.get("id") == data.get("primary_email_address_id")),
        None,
    )
    logger.info("Clerk user created: %s (%s)", clerk_user_id, primary_email)
    # TODO: Create Supabase profile, send welcome email, etc.


def handle_user_updated(data: dict[str, Any]) -> None:
    """Handle ``user.updated`` event."""
    clerk_user_id = data.get("id", "")
    logger.info("Clerk user updated: %s", clerk_user_id)
    # TODO: Sync updated fields to your database.


def handle_user_deleted(data: dict[str, Any]) -> None:
    """Handle ``user.deleted`` event."""
    clerk_user_id = data.get("id", "")
    logger.info("Clerk user deleted: %s", clerk_user_id)
    # TODO: Soft-delete or clean up user data.


def handle_session_created(data: dict[str, Any]) -> None:
    """Handle ``session.created`` event."""
    user_id = data.get("user_id", "")
    logger.info("Clerk session created for user: %s", user_id)


# Map event types to handler functions.  Add new handlers here.
EVENT_HANDLERS: dict[str, Any] = {
    "user.created": handle_user_created,
    "user.updated": handle_user_updated,
    "user.deleted": handle_user_deleted,
    "session.created": handle_session_created,
}


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------

@method_decorator(csrf_exempt, name="dispatch")
class ClerkWebhookView(View):
    """Receive and process Clerk webhook events.

    This view is CSRF-exempt because the requests come from Clerk's
    servers, not from a browser.  Authenticity is verified via the
    Svix signature header instead.
    """

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
