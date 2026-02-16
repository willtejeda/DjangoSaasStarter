from __future__ import annotations

from typing import Any

from django.conf import settings


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
