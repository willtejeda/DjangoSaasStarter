from __future__ import annotations

import logging

from django.http import HttpRequest, JsonResponse
from django.utils import timezone as django_timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import WebhookEvent
from .handlers import EVENT_HANDLERS
from .verification import WebhookVerificationError, _verify_webhook

logger = logging.getLogger(__name__)


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
