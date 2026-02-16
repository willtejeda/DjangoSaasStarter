# 06 Resend Transactional Email

Goal: configure, verify, and ship buyer transactional email safely.

## 1. What is implemented

Resend sends are triggered from backend workflows:

- Order fulfillment confirmation email
- Booking request confirmation email
- Preflight test email endpoint: `POST /api/account/preflight/email-test/`

Code path: `backend/api/tools/email/resend.py`

## 2. Required and recommended env vars

Set in `backend/.env`:

Required:

```bash
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL=Acme <updates@yourdomain.com>
```

Recommended:

```bash
FRONTEND_APP_URL=https://app.yourdomain.com
RESEND_REPLY_TO_EMAIL=support@yourdomain.com
RESEND_TIMEOUT_SECONDS=10
```

Notes:

- If required values are missing, email send is skipped.
- `FRONTEND_APP_URL` is used for account deep links in email body.
- `RESEND_REPLY_TO_EMAIL` is optional.

## 3. Resend dashboard setup

1. Create and verify your sending domain in Resend.
2. Create a sender identity under that domain.
3. Generate an API key and place it in `RESEND_API_KEY`.
4. Restart backend after env changes.

## 4. Preflight verification flow

Run this after sign-in:

```bash
curl -X POST http://127.0.0.1:8000/api/account/preflight/email-test/ \
  -H "Authorization: Bearer <token>"
```

Expected response:

```json
{
  "sent": true,
  "detail": "Preflight email sent to you@example.com.",
  "recipient_email": "you@example.com",
  "sent_at": "2026-02-16T..."
}
```

This confirms:

- Resend API key is valid
- Sender identity is accepted
- Recipient resolution works from customer account/profile

## 5. Local verification flow for transactional events

Order confirmation:

1. Complete a purchase flow that reaches fulfilled status.
2. Confirm Resend activity shows an accepted send for event `order_fulfilled`.

Booking confirmation:

1. Create a booking via `POST /api/account/bookings/` or `/account/bookings` UI.
2. Confirm Resend activity shows an accepted send for event `booking_requested`.

Expected behavior:

- API success does not depend on email provider success.
- Checkout and booking flows stay source-of-truth even if email send fails.

## 6. How recipients are resolved

Recipient list is built from:

1. `customer_account.billing_email`
2. fallback `customer_account.profile.email`

Duplicates are removed and values are normalized before send.

## 7. Idempotency and duplicate control

Resend requests include idempotency keys:

- `order-fulfilled-<order_public_id>`
- `booking-requested-<booking_id>`
- `preflight-email-<account_id>-<timestamp>`

This reduces duplicate sends during retries.

## 8. Tailwind style email templates with CSS inlining

Email clients do not run Tailwind runtime CSS. Use this pattern:

1. Write utility-like class names in HTML (`bg-slate-100`, `text-slate-900`, etc).
2. Define corresponding CSS in a `<style>` block.
3. Inline styles before send using `premailer`.

The backend includes this helper flow in `backend/api/tools/email/resend.py`:

- `_inline_email_html()` uses `premailer.transform(...)`
- Falls back to raw HTML if inlining fails

Minimal pattern:

```python
from premailer import transform

raw_html = """
<html>
  <head>
    <style>
      .bg-slate-100 { background-color: #f1f5f9; }
      .text-slate-900 { color: #0f172a; }
      .rounded-xl { border-radius: 12px; }
    </style>
  </head>
  <body class="bg-slate-100 text-slate-900">
    <div class="rounded-xl">Preflight email test</div>
  </body>
</html>
"""

inlined_html = transform(raw_html, keep_style_tags=False, remove_classes=True)
```

## 9. Production checklist

1. Verify sender domain and from address are valid in Resend.
2. Set `FRONTEND_APP_URL` to your production frontend origin.
3. Run one preflight email test in staging.
4. Run one paid order test and one booking test in staging.
5. Confirm sends appear in Resend activity.
6. Keep payment confirmation webhook-driven and server-side.

## 10. Fast troubleshooting

No email received after successful order, booking, or preflight send:

- Check `RESEND_API_KEY` and `RESEND_FROM_EMAIL`.
- Check sender identity verification in Resend.
- Check recipient email exists on customer account or profile.
- Check backend logs for Resend warning responses.
- Re-run test flow after env updates and backend restart.
