from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.test import APIRequestFactory

from api.tools.auth.authentication import ClerkJWTAuthentication
from api.tools.auth.clerk import authorized_party_matches
from api.tools.database.supabase import _ensure_https
from api.views import extract_billing_features


class ClerkJWTAuthenticationTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory(enforce_csrf_checks=True)
        self.authentication = ClerkJWTAuthentication()

    def test_returns_none_without_token(self):
        request = self.factory.get("/api/me/")
        self.assertIsNone(self.authentication.authenticate(request))

    @patch("api.tools.auth.authentication.decode_clerk_token")
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

    @patch("api.tools.auth.authentication.decode_clerk_token")
    def test_reads_session_cookie_token(self, decode_token):
        decode_token.return_value = {"sub": "user_cookie"}
        request = self.factory.get("/api/me/")
        request.COOKIES["__session"] = "cookie-token"
        user, _ = self.authentication.authenticate(request)

        self.assertEqual(user.clerk_user_id, "user_cookie")
        self.assertEqual(request.clerk_token, "cookie-token")

    @patch("api.tools.auth.authentication.decode_clerk_token")
    def test_cookie_auth_requires_csrf_for_unsafe_method(self, decode_token):
        decode_token.return_value = {"sub": "user_cookie"}
        request = self.factory.post("/api/projects/", data={"name": "x"}, format="json")
        request.COOKIES["__session"] = "cookie-token"

        with self.assertRaises(PermissionDenied):
            self.authentication.authenticate(request)

    @patch("api.tools.auth.authentication.decode_clerk_token")
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

    @override_settings(CLERK_BILLING_CLAIM="entitlements")
    def test_normalizes_and_deduplicates_features(self):
        claims = {"entitlements": [" Pro ", "pro", "ANALYTICS", "analytics"]}
        self.assertEqual(extract_billing_features(claims), ["pro", "analytics"])


class AuthorizedPartiesTests(SimpleTestCase):
    def test_matches_exact_origin(self):
        self.assertTrue(
            authorized_party_matches(
                "http://localhost:5173",
                ["http://localhost:5173"],
            )
        )

    def test_matches_with_trailing_slash(self):
        self.assertTrue(
            authorized_party_matches(
                "http://localhost:5173",
                ["http://localhost:5173/"],
            )
        )

    def test_matches_loopback_aliases(self):
        self.assertTrue(
            authorized_party_matches(
                "http://127.0.0.1:5173",
                ["http://localhost:5173"],
            )
        )

    def test_rejects_different_ports(self):
        self.assertFalse(
            authorized_party_matches(
                "http://127.0.0.1:5173",
                ["http://localhost:3000"],
            )
        )

    def test_rejects_unlisted_non_loopback_host(self):
        self.assertFalse(
            authorized_party_matches(
                "https://app.example.com",
                ["https://admin.example.com"],
            )
        )


class SupabaseUrlTests(SimpleTestCase):
    def test_adds_https_prefix(self):
        self.assertEqual(_ensure_https("db.example.supabase.co"), "https://db.example.supabase.co")

    def test_preserves_existing_https(self):
        self.assertEqual(_ensure_https("https://db.example.supabase.co"), "https://db.example.supabase.co")

    def test_preserves_existing_http(self):
        self.assertEqual(_ensure_https("http://localhost:54321"), "http://localhost:54321")

    def test_handles_empty_string(self):
        self.assertEqual(_ensure_https(""), "")
