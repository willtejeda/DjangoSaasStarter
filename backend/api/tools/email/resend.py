from __future__ import annotations

import json
import logging
from html import escape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from ...models import CustomerAccount, FulfillmentOrder, Order

try:
    from premailer import transform as premailer_transform
except Exception:  # pragma: no cover
    premailer_transform = None

logger = logging.getLogger(__name__)

RESEND_EMAILS_ENDPOINT = "https://api.resend.com/emails"


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


def _normalize_url(value: object) -> str:
    return _normalize_text(value).rstrip("/")


def _normalize_email_candidates(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for raw in values:
        candidate = _normalize_text(raw).lower()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


def _resend_enabled() -> bool:
    api_key = _normalize_text(getattr(settings, "RESEND_API_KEY", ""))
    sender = _normalize_text(getattr(settings, "RESEND_FROM_EMAIL", ""))
    return bool(api_key and sender)


def resend_is_configured() -> bool:
    return _resend_enabled()


def _inline_email_html(html_body: str) -> str:
    if premailer_transform is None:
        return html_body

    try:
        return premailer_transform(
            html_body,
            keep_style_tags=False,
            remove_classes=True,
            disable_validation=True,
        )
    except Exception:  # pragma: no cover
        logger.exception("Failed to inline CSS with premailer. Sending original HTML.")
        return html_body


def _format_currency(cents: int, currency: str) -> str:
    normalized_currency = _normalize_text(currency).upper() or "USD"
    amount = (int(cents or 0)) / 100
    return f"{normalized_currency} {amount:,.2f}"


def _send_resend_email(
    *,
    recipients: list[str],
    subject: str,
    html_body: str,
    text_body: str,
    tags: dict[str, str] | None = None,
    idempotency_key: str | None = None,
) -> bool:
    if not recipients:
        logger.debug("Skipping Resend email with no recipients.")
        return False

    if not _resend_enabled():
        logger.debug("Skipping Resend email because API key or sender is missing.")
        return False

    payload: dict[str, object] = {
        "from": _normalize_text(getattr(settings, "RESEND_FROM_EMAIL", "")),
        "to": recipients,
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }

    reply_to = _normalize_text(getattr(settings, "RESEND_REPLY_TO_EMAIL", ""))
    if reply_to:
        payload["reply_to"] = [reply_to]

    if tags:
        payload["tags"] = [
            {"name": _normalize_text(name), "value": _normalize_text(value)}
            for name, value in tags.items()
            if _normalize_text(name) and _normalize_text(value)
        ]

    request_headers = {
        "Authorization": f"Bearer {_normalize_text(getattr(settings, 'RESEND_API_KEY', ''))}",
        "Content-Type": "application/json",
    }
    if idempotency_key:
        request_headers["Idempotency-Key"] = idempotency_key

    timeout_seconds = int(getattr(settings, "RESEND_TIMEOUT_SECONDS", 10))
    request_body = json.dumps(payload).encode("utf-8")
    request = Request(
        RESEND_EMAILS_ENDPOINT,
        data=request_body,
        headers=request_headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = int(getattr(response, "status", 200))
            body = response.read().decode("utf-8", errors="ignore")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        logger.warning("Resend request failed with status %s: %s", exc.code, error_body)
        return False
    except URLError as exc:
        logger.warning("Resend request failed: %s", exc.reason)
        return False
    except Exception:
        logger.exception("Unexpected error while sending email through Resend.")
        return False

    if status < 200 or status >= 300:
        logger.warning("Resend returned unexpected status %s: %s", status, body)
        return False

    logger.info("Resend accepted email request: %s", body)
    return True


def send_order_fulfilled_email(order: Order) -> bool:
    recipients = _normalize_email_candidates(
        [
            getattr(order.customer_account, "billing_email", ""),
            getattr(order.customer_account.profile, "email", ""),
        ]
    )
    if not recipients:
        return False

    order_id = str(order.public_id)
    short_order_id = order_id[:8]
    frontend_url = _normalize_url(getattr(settings, "FRONTEND_APP_URL", ""))
    purchases_url = f"{frontend_url}/account/purchases" if frontend_url else ""
    downloads_url = f"{frontend_url}/account/downloads" if frontend_url else ""

    items = list(order.items.select_related("product", "price").order_by("id"))
    item_lines_text = [
        f"- {item.product_name_snapshot} x{item.quantity} ({_format_currency(item.total_amount_cents, order.currency)})"
        for item in items
    ]
    item_lines_html = "".join(
        (
            "<li>"
            f"{escape(item.product_name_snapshot)} x{item.quantity}"
            f" ({escape(_format_currency(item.total_amount_cents, order.currency))})"
            "</li>"
        )
        for item in items
    )

    subject = f"Your order {short_order_id} is fulfilled"

    text_sections = [
        "Your purchase is confirmed and fulfillment is complete.",
        "",
        f"Order: {order_id}",
        f"Total: {_format_currency(order.total_cents, order.currency)}",
        "",
        "Items:",
        *(item_lines_text or ["- No item details available"]),
    ]
    if purchases_url:
        text_sections.extend(["", f"View purchases: {purchases_url}"])
    if downloads_url:
        text_sections.extend([f"View downloads: {downloads_url}"])

    html_body = f"""
      <div style="font-family: Arial, sans-serif; line-height: 1.5; color: #111827;">
        <h2 style="margin: 0 0 12px;">Purchase confirmed</h2>
        <p style="margin: 0 0 8px;">Your order has been fulfilled.</p>
        <p style="margin: 0 0 16px;"><strong>Order:</strong> {escape(order_id)}<br /><strong>Total:</strong> {escape(_format_currency(order.total_cents, order.currency))}</p>
        <h3 style="margin: 0 0 8px; font-size: 16px;">Items</h3>
        <ul style="margin: 0 0 16px 20px; padding: 0;">
          {item_lines_html or "<li>No item details available</li>"}
        </ul>
        {"<p style='margin: 0 0 8px;'><a href='" + escape(purchases_url) + "'>Open purchases</a></p>" if purchases_url else ""}
        {"<p style='margin: 0;'><a href='" + escape(downloads_url) + "'>Open downloads</a></p>" if downloads_url else ""}
      </div>
    """.strip()

    return _send_resend_email(
        recipients=recipients,
        subject=subject,
        html_body=html_body,
        text_body="\n".join(text_sections).strip(),
        tags={"event": "order_fulfilled", "source": "django_starter"},
        idempotency_key=f"order-fulfilled-{order_id}",
    )


def send_fulfillment_order_requested_email(work_order: FulfillmentOrder) -> bool:
    recipients = _normalize_email_candidates(
        [
            getattr(work_order.customer_account, "billing_email", ""),
            getattr(work_order.customer_account.profile, "email", ""),
        ]
    )
    if not recipients:
        return False

    product_name = _normalize_text(getattr(work_order.product, "name", "Custom order"))
    delivery_mode = _normalize_text(getattr(work_order, "delivery_mode", "downloadable")).replace("_", " ")
    frontend_url = _normalize_url(getattr(settings, "FRONTEND_APP_URL", ""))
    orders_url = f"{frontend_url}/account/orders/work" if frontend_url else ""

    notes = _normalize_text(getattr(work_order, "customer_request", ""))
    notes_markup = escape(notes) if notes else "No additional notes"

    subject = f"Work order received for {product_name}"
    text_sections = [
        f"We received your order request for {product_name}.",
        f"Delivery mode: {delivery_mode}",
        f"Work order id: {work_order.id}",
    ]
    if notes:
        text_sections.extend(["", f"Your notes: {notes}"])
    if orders_url:
        text_sections.extend(["", f"Track order status: {orders_url}"])

    html_body = f"""
      <div style="font-family: Arial, sans-serif; line-height: 1.5; color: #111827;">
        <h2 style="margin: 0 0 12px;">Work order received</h2>
        <p style="margin: 0 0 8px;">We logged your request for <strong>{escape(product_name)}</strong>.</p>
        <p style="margin: 0 0 8px;"><strong>Delivery mode:</strong> {escape(delivery_mode)}</p>
        <p style="margin: 0 0 16px;"><strong>Work order id:</strong> {work_order.id}</p>
        <p style="margin: 0 0 16px;"><strong>Your notes:</strong> {notes_markup}</p>
        {"<p style='margin: 0;'><a href='" + escape(orders_url) + "'>Open work orders</a></p>" if orders_url else ""}
      </div>
    """.strip()

    return _send_resend_email(
        recipients=recipients,
        subject=subject,
        html_body=html_body,
        text_body="\n".join(text_sections).strip(),
        tags={"event": "fulfillment_order_requested", "source": "django_starter"},
        idempotency_key=f"fulfillment-order-requested-{work_order.id}",
    )


def send_booking_requested_email(_booking) -> bool:
    """Deprecated compatibility wrapper."""
    return False


def send_preflight_test_email(account: CustomerAccount) -> tuple[bool, str]:
    recipients = _normalize_email_candidates(
        [
            getattr(account, "billing_email", ""),
            getattr(account.profile, "email", ""),
        ]
    )
    if not recipients:
        return False, ""

    recipient = recipients[0]
    now = timezone.now()
    frontend_url = _normalize_url(getattr(settings, "FRONTEND_APP_URL", ""))
    dashboard_url = f"{frontend_url}/app" if frontend_url else ""

    subject = "DjangoStarter preflight email test"
    text_body = "\n".join(
        [
            "This is a preflight delivery test from DjangoStarter.",
            "",
            "If you received this email, Resend API, sender identity, and recipient resolution are working.",
            "",
            f"Timestamp: {now.isoformat()}",
            f"Recipient: {recipient}",
            f"Dashboard: {dashboard_url}" if dashboard_url else "",
        ]
    ).strip()

    utility_like_css = """
      .bg-slate-100 { background-color: #f1f5f9; }
      .bg-slate-950 { background-color: #020617; }
      .text-slate-900 { color: #0f172a; }
      .text-slate-100 { color: #f8fafc; }
      .text-slate-600 { color: #475569; }
      .text-cyan-700 { color: #0e7490; }
      .rounded-xl { border-radius: 12px; }
      .border { border: 1px solid #cbd5e1; }
      .p-24 { padding: 24px; }
      .mb-16 { margin-bottom: 16px; }
      .inline-block { display: inline-block; }
      .font-bold { font-weight: 700; }
      .font-semibold { font-weight: 600; }
      .text-sm { font-size: 14px; line-height: 20px; }
      .text-xs { font-size: 12px; line-height: 16px; }
      .button { background: #020617; color: #f8fafc; text-decoration: none; padding: 10px 14px; border-radius: 10px; }
    """.strip()

    html_template = f"""
      <html>
        <head>
          <meta charset="utf-8" />
          <style>{utility_like_css}</style>
        </head>
        <body class="bg-slate-100 text-slate-900" style="margin: 0; padding: 24px; font-family: Arial, sans-serif;">
          <div class="rounded-xl border p-24" style="max-width: 560px; margin: 0 auto; background: #ffffff;">
            <p class="text-xs font-semibold text-cyan-700 mb-16">DjangoStarter Preflight</p>
            <h2 class="font-bold mb-16" style="margin-top: 0;">Resend delivery test passed request stage</h2>
            <p class="text-sm text-slate-600 mb-16">
              This test validates your outbound email route before building product features.
            </p>
            <p class="text-sm text-slate-600 mb-16">
              <strong>Timestamp:</strong> {escape(now.isoformat())}<br />
              <strong>Recipient:</strong> {escape(recipient)}
            </p>
            {f'<a class="button inline-block" href="{escape(dashboard_url)}">Open Dashboard</a>' if dashboard_url else ''}
          </div>
        </body>
      </html>
    """.strip()

    html_body = _inline_email_html(html_template)

    sent = _send_resend_email(
        recipients=recipients,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        tags={"event": "preflight_email_test", "source": "django_starter"},
        idempotency_key=f"preflight-email-{account.id}-{now.strftime('%Y%m%d%H%M%S')}",
    )
    return sent, recipient
