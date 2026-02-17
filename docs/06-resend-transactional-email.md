# 06 Resend Transactional Email

DjangoStarter uses Resend for product lifecycle emails and keeps Clerk for auth and billing-native email flows.

## Division of responsibility

- Clerk handles core auth and billing account emails
- Resend handles product lifecycle emails:
  - preflight test messages
  - order fulfilled notifications
  - work order request notifications
  - your future offers and update campaigns

## Current implementation

File: `./backend/api/tools/email/resend.py`

Highlights:

- Uses direct Resend API call with robust error handling
- Adds email tags for event classification
- Supports reply-to and idempotency keys
- Uses Premailer when installed to inline CSS

## Required env vars

```bash
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL=Acme <updates@yourdomain.com>
RESEND_REPLY_TO_EMAIL=support@yourdomain.com
FRONTEND_APP_URL=https://your-app-domain.com
```

## Tailwind-style template approach in Django

The current preflight email template uses utility-like class names in HTML and inlines with Premailer.

Pattern:

1. Write semantic HTML template
2. Add small utility CSS block (Tailwind-like naming)
3. Run Premailer transform
4. Send final inlined HTML to Resend

This keeps authoring readable while maximizing inbox client compatibility.

## Example send payload pattern

```python
params = {
    "from": "Acme <updates@yourdomain.com>",
    "to": ["customer@example.com"],
    "subject": "Your order is fulfilled",
    "html": "<strong>Ready</strong>",
    "reply_to": ["support@yourdomain.com"],
    "tags": [{"name": "event", "value": "order_fulfilled"}],
}
```

## Testing flow

1. Sign in and open `/app`
2. Run "Send test email" preflight step
3. Confirm inbox delivery and sender reputation
4. Trigger paid order and verify fulfillment email

## Common failure reasons

- Sender domain not verified in Resend
- Missing recipient email in profile/customer account
- Network egress restrictions
- Invalid API key or revoked key
