import json
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from .authentication import ClerkJWTAuthentication
from .supabase_client import _ensure_https
from .views import extract_billing_features
from .webhooks import ClerkWebhookView, WebhookVerificationError, _verify_webhook


class ClerkJWTAuthenticationTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.authentication = ClerkJWTAuthentication()

    def test_returns_none_without_token(self):
        request = self.factory.get("/api/me/")
        self.assertIsNone(self.authentication.authenticate(request))

    @patch("api.authentication.decode_clerk_token")
    def test_reads_bearer_token(self, decode_token):
        decode_token.return_value = {"sub": "user_123", "email": "person@example.com"}
        request = self.factory.get(
            "/api/me/",
            HTTP_AUTHORIZATION="Bearer test-token",
        )
        user, claims = self.authentication.authenticate(request)

        self.assertEqual(user.clerk_user_id, "user_123")
        self.assertEqual(claims["email"], "person@example.com")
        self.assertEqual(request.clerk_token, "test-token")

    @patch("api.authentication.decode_clerk_token")
    def test_reads_session_cookie_token(self, decode_token):
        decode_token.return_value = {"sub": "user_cookie"}
        request = self.factory.get("/api/me/")
        request.COOKIES["__session"] = "cookie-token"
        user, _ = self.authentication.authenticate(request)

        self.assertEqual(user.clerk_user_id, "user_cookie")
        self.assertEqual(request.clerk_token, "cookie-token")

    def test_invalid_authorization_header_missing_token(self):
        request = self.factory.get(
            "/api/me/",
            HTTP_AUTHORIZATION="Bearer",
        )
        with self.assertRaises(AuthenticationFailed):
            self.authentication.authenticate(request)


class BillingFeaturesTests(SimpleTestCase):
    @override_settings(CLERK_BILLING_CLAIM="entitlements")
    def test_extracts_features_from_list(self):
        claims = {"entitlements": ["pro", "analytics"]}
        self.assertEqual(extract_billing_features(claims), ["pro", "analytics"])

    @override_settings(CLERK_BILLING_CLAIM="entitlements")
    def test_extracts_features_from_dictionary(self):
        claims = {"entitlements": {"pro": True, "team": False, "reports": 1}}
        self.assertEqual(extract_billing_features(claims), ["pro", "reports"])

    @override_settings(CLERK_BILLING_CLAIM="entitlements")
    def test_extracts_features_from_csv_string(self):
        claims = {"entitlements": "pro, analytics , team"}
        self.assertEqual(extract_billing_features(claims), ["pro", "analytics", "team"])


class SupabaseUrlTests(SimpleTestCase):
    def test_adds_https_prefix(self):
        self.assertEqual(_ensure_https("db.example.supabase.co"), "https://db.example.supabase.co")

    def test_preserves_existing_https(self):
        self.assertEqual(_ensure_https("https://db.example.supabase.co"), "https://db.example.supabase.co")

    def test_preserves_existing_http(self):
        self.assertEqual(_ensure_https("http://localhost:54321"), "http://localhost:54321")

    def test_handles_empty_string(self):
        self.assertEqual(_ensure_https(""), "")


class ClerkWebhookViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(CLERK_WEBHOOK_SIGNING_SECRET="whsec_test123")
    @patch("api.webhooks._verify_webhook")
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
    @patch("api.webhooks._verify_webhook")
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
