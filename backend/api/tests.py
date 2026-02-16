import json
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.test import APIRequestFactory, APIClient

from .authentication import ClerkJWTAuthentication
from .models import Profile, Project
from .supabase_client import _ensure_https
from .views import extract_billing_features
from .webhooks import (
    ClerkWebhookView,
    WebhookVerificationError,
    _verify_webhook,
    handle_user_created,
    handle_user_deleted,
)


class ClerkJWTAuthenticationTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory(enforce_csrf_checks=True)
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

    @patch("api.authentication.decode_clerk_token")
    def test_cookie_auth_requires_csrf_for_unsafe_method(self, decode_token):
        decode_token.return_value = {"sub": "user_cookie"}
        request = self.factory.post("/api/projects/", data={"name": "x"}, format="json")
        request.COOKIES["__session"] = "cookie-token"

        with self.assertRaises(PermissionDenied):
            self.authentication.authenticate(request)

    @patch("api.authentication.decode_clerk_token")
    def test_cookie_auth_accepts_valid_csrf_for_unsafe_method(self, decode_token):
        decode_token.return_value = {"sub": "user_cookie"}
        csrf_token = "a" * 32
        request = self.factory.post(
            "/api/projects/",
            data={"name": "x"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        request.COOKIES["__session"] = "cookie-token"
        request.COOKIES["csrftoken"] = csrf_token

        user, _ = self.authentication.authenticate(request)
        self.assertEqual(user.clerk_user_id, "user_cookie")

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
    @patch("api.webhooks.EVENT_HANDLERS", {"user.created": lambda data: None})
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
        profile = Profile.objects.create(clerk_user_id="user_test_2", email="alive@example.com")

        handle_user_deleted({"id": "user_test_2"})

        profile.refresh_from_db()
        self.assertFalse(profile.is_active)
        self.assertEqual(profile.email, "")


class ProjectApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.auth_headers = {"HTTP_AUTHORIZATION": "Bearer unit-test-token"}
        self.claims = {
            "sub": "user_123",
            "email": "owner@example.com",
            "given_name": "Owner",
            "family_name": "User",
            "entitlements": ["pro"],
        }

    def _request(self, method: str, path: str, data=None):
        with patch("api.authentication.decode_clerk_token", return_value=self.claims):
            handler = getattr(self.client, method)
            return handler(path, data=data, format="json", **self.auth_headers)

    def test_me_endpoint_syncs_profile(self):
        response = self._request("get", "/api/me/")

        self.assertEqual(response.status_code, 200)
        profile = Profile.objects.get(clerk_user_id="user_123")
        self.assertEqual(profile.email, "owner@example.com")
        self.assertEqual(profile.plan_tier, Profile.PlanTier.PRO)

    def test_create_and_list_projects_scoped_by_profile(self):
        create_response = self._request(
            "post",
            "/api/projects/",
            {
                "name": "Ship Faster",
                "slug": "Ship Faster",
                "summary": "Core SaaS template",
                "status": "building",
                "monthly_recurring_revenue": "499.99",
            },
        )
        self.assertEqual(create_response.status_code, 201)

        own_profile = Profile.objects.get(clerk_user_id="user_123")
        other_profile = Profile.objects.create(clerk_user_id="user_999", email="other@example.com")
        Project.objects.create(owner=other_profile, name="Other", slug="other")

        list_response = self._request("get", "/api/projects/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["name"], "Ship Faster")

        own_project = Project.objects.get(owner=own_profile, slug="ship-faster")
        detail_response = self._request("get", f"/api/projects/{own_project.id}/")
        self.assertEqual(detail_response.status_code, 200)

    def test_cannot_access_other_users_project(self):
        other_profile = Profile.objects.create(clerk_user_id="user_999", email="other@example.com")
        other_project = Project.objects.create(owner=other_profile, name="Other", slug="other")

        response = self._request("get", f"/api/projects/{other_project.id}/")
        self.assertEqual(response.status_code, 404)
