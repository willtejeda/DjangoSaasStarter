import json
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from api.models import Profile
from api.webhooks import (
    ClerkWebhookView,
    EVENT_HANDLERS,
    WebhookVerificationError,
    _verify_webhook,
    handle_user_created,
    handle_user_deleted,
)


class ClerkWebhookViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(CLERK_WEBHOOK_SIGNING_SECRET="whsec_test123")
    @patch("api.webhooks.receiver.EVENT_HANDLERS", {"user.created": lambda data: None})
    @patch("api.webhooks.receiver._verify_webhook")
    def test_valid_webhook_event(self, mock_verify):
        mock_verify.return_value = {
            "type": "user.created",
            "data": {"id": "user_abc", "email_addresses": []},
        }
        request = self.factory.post(
            "/api/webhooks/clerk/",
            data=json.dumps({"type": "user.created"}),
            content_type="application/json",
            HTTP_SVIX_ID="msg_123",
            HTTP_SVIX_TIMESTAMP="1234567890",
            HTTP_SVIX_SIGNATURE="v1,test",
        )
        response = ClerkWebhookView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(CLERK_WEBHOOK_SIGNING_SECRET="whsec_test123")
    @patch("api.webhooks.receiver._verify_webhook")
    def test_invalid_webhook_signature(self, mock_verify):
        mock_verify.side_effect = WebhookVerificationError("Bad signature")
        request = self.factory.post(
            "/api/webhooks/clerk/",
            data=b"{}",
            content_type="application/json",
            HTTP_SVIX_ID="msg_123",
            HTTP_SVIX_TIMESTAMP="1234567890",
            HTTP_SVIX_SIGNATURE="v1,bad",
        )
        response = ClerkWebhookView.as_view()(request)
        self.assertEqual(response.status_code, 400)

    @override_settings(CLERK_WEBHOOK_SIGNING_SECRET="")
    def test_missing_webhook_secret(self):
        with self.assertRaises(WebhookVerificationError):
            _verify_webhook(b"{}", {"svix-id": "", "svix-timestamp": "", "svix-signature": ""})


class ClerkWebhookEventMappingTests(SimpleTestCase):
    def test_supports_subscription_events_with_and_without_billing_prefix(self):
        self.assertIn("subscription.created", EVENT_HANDLERS)
        self.assertIn("subscription.updated", EVENT_HANDLERS)
        self.assertIn("subscription.active", EVENT_HANDLERS)
        self.assertIn("subscription.pastDue", EVENT_HANDLERS)
        self.assertIn("subscription.canceled", EVENT_HANDLERS)
        self.assertIn("billing.subscription.created", EVENT_HANDLERS)
        self.assertIn("billing.subscription.updated", EVENT_HANDLERS)
        self.assertIn("billing.subscription.active", EVENT_HANDLERS)
        self.assertIn("billing.subscription.pastDue", EVENT_HANDLERS)
        self.assertIn("billing.subscription.canceled", EVENT_HANDLERS)


class ClerkWebhookHandlerTests(TestCase):
    def test_handle_user_created_upserts_profile(self):
        handle_user_created(
            {
                "id": "user_test_1",
                "first_name": "Alex",
                "last_name": "Smith",
                "image_url": "https://img.example.com/a.png",
                "primary_email_address_id": "id_1",
                "email_addresses": [
                    {
                        "id": "id_1",
                        "email_address": "alex@example.com",
                    }
                ],
                "public_metadata": {"entitlements": ["pro", "analytics"]},
            }
        )

        profile = Profile.objects.get(clerk_user_id="user_test_1")
        self.assertEqual(profile.email, "alex@example.com")
        self.assertEqual(profile.plan_tier, Profile.PlanTier.PRO)
        self.assertEqual(profile.billing_features, ["pro", "analytics"])
        self.assertTrue(profile.is_active)

    def test_handle_user_deleted_marks_profile_inactive(self):
        profile = Profile.objects.create(
            clerk_user_id="user_test_2",
            email="alive@example.com",
            first_name="Alive",
            last_name="User",
            plan_tier=Profile.PlanTier.PRO,
            billing_features=["pro", "ai_coach"],
            metadata={"retained": True},
        )

        handle_user_deleted({"id": "user_test_2"})

        profile.refresh_from_db()
        self.assertFalse(profile.is_active)
        self.assertEqual(profile.email, "")
        self.assertEqual(profile.first_name, "")
        self.assertEqual(profile.last_name, "")
        self.assertEqual(profile.plan_tier, Profile.PlanTier.FREE)
        self.assertEqual(profile.billing_features, [])
        self.assertEqual(profile.metadata, {})

    @override_settings(CLERK_BILLING_CLAIM="billing_features")
    def test_handle_user_created_uses_configured_billing_claim(self):
        handle_user_created(
            {
                "id": "user_test_3",
                "first_name": "Taylor",
                "public_metadata": {
                    "billing_features": ["Pro", "AI_Coach"],
                    "entitlements": ["free_only"],
                },
            }
        )

        profile = Profile.objects.get(clerk_user_id="user_test_3")
        self.assertEqual(profile.billing_features, ["pro", "ai_coach"])
