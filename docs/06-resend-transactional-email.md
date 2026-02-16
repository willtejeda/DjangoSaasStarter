# 06 Resend Transactional Email

Goal: configure, verify, and ship buyer transactional email safely.

## 1. What is implemented

Resend sends are triggered from backend workflows:

- Order fulfillment confirmation email
- Booking request confirmation email

Code path: `backend/api/emails.py`

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

## 4. Local verification flow

Order confirmation:

1. Complete a purchase flow that reaches fulfilled status.
2. Confirm Resend activity shows an accepted send for event `order_fulfilled`.

Booking confirmation:

1. Create a booking via `POST /api/account/bookings/` or `/account/bookings` UI.
2. Confirm Resend activity shows an accepted send for event `booking_requested`.

Expected behavior:

- API success does not depend on email provider success.
- Checkout and booking flows stay source-of-truth even if email send fails.

## 5. How recipients are resolved

Recipient list is built from:

1. `customer_account.billing_email`
2. fallback `customer_account.profile.email`

Duplicates are removed and values are normalized before send.

## 6. Idempotency and duplicate control

Resend requests include idempotency keys:

- `order-fulfilled-<order_public_id>`
- `booking-requested-<booking_id>`

This reduces duplicate sends during retries.

## 7. Production checklist

1. Verify sender domain and from address are valid in Resend.
2. Set `FRONTEND_APP_URL` to your production frontend origin.
3. Run one paid order test and one booking test in staging.
4. Confirm both sends appear in Resend activity.
5. Keep payment confirmation webhook-driven and server-side.

## 8. Fast troubleshooting

No email received after successful order or booking:

- Check `RESEND_API_KEY` and `RESEND_FROM_EMAIL`.
- Check sender identity verification in Resend.
- Check recipient email exists on customer account or profile.
- Check backend logs for Resend warning responses.
- Re-run test flow after env updates and backend restart.
