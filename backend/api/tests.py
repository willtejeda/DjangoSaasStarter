import json
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.test import APIRequestFactory, APIClient

from .authentication import ClerkJWTAuthentication
from .clerk import authorized_party_matches
from .models import (
    DigitalAsset,
    DownloadGrant,
    Entitlement,
    Order,
    Price,
    Product,
    Profile,
    Project,
    ServiceOffer,
    Subscription,
)
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

    def test_partial_patch_does_not_require_slug(self):
        create_response = self._request(
            "post",
            "/api/projects/",
            {
                "name": "Ship Faster",
                "summary": "Core SaaS template",
                "status": "building",
                "monthly_recurring_revenue": "499.99",
            },
        )
        self.assertEqual(create_response.status_code, 201)

        project_id = create_response.data["id"]
        original_slug = create_response.data["slug"]

        patch_response = self._request(
            "patch",
            f"/api/projects/{project_id}/",
            {"status": "live"},
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.data["status"], "live")
        self.assertEqual(patch_response.data["slug"], original_slug)

    def test_create_project_rejects_negative_mrr(self):
        response = self._request(
            "post",
            "/api/projects/",
            {
                "name": "Loss Maker",
                "summary": "Invalid payload",
                "status": "idea",
                "monthly_recurring_revenue": "-1.00",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("monthly_recurring_revenue", response.data)

    def test_feature_check_is_case_insensitive(self):
        response = self._request("get", "/api/billing/features/?feature=PrO")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["feature"], "pro")
        self.assertTrue(response.data["enabled"])

    def test_cannot_access_other_users_project(self):
        other_profile = Profile.objects.create(clerk_user_id="user_999", email="other@example.com")
        other_project = Project.objects.create(owner=other_profile, name="Other", slug="other")

        response = self._request("get", f"/api/projects/{other_project.id}/")
        self.assertEqual(response.status_code, 404)


class ProjectModelValidationTests(TestCase):
    def test_project_save_rejects_whitespace_name(self):
        owner = Profile.objects.create(clerk_user_id="user_name_invalid")

        with self.assertRaises(DjangoValidationError):
            Project.objects.create(owner=owner, name="   ", slug="")


class CommerceApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.auth_headers = {"HTTP_AUTHORIZATION": "Bearer unit-test-token"}
        self.claims = {
            "sub": "buyer_123",
            "email": "buyer@example.com",
            "given_name": "Buyer",
            "family_name": "User",
            "entitlements": ["free"],
        }

    def _request(self, method: str, path: str, data=None):
        with patch("api.authentication.decode_clerk_token", return_value=self.claims):
            handler = getattr(self.client, method)
            return handler(path, data=data, format="json", **self.auth_headers)

    def _create_fulfilled_digital_order(self):
        suffix = Product.objects.count() + 1
        owner = Profile.objects.create(
            clerk_user_id=f"seller_download_{suffix}",
            email=f"seller{suffix}@example.com",
        )
        product = Product.objects.create(
            owner=owner,
            name=f"Creator Bundle {suffix}",
            slug=f"creator-bundle-{suffix}",
            visibility=Product.Visibility.PUBLISHED,
            product_type=Product.ProductType.DIGITAL,
            feature_keys=["priority_support", "templates_pack"],
        )
        price = Price.objects.create(
            product=product,
            name="One-time",
            amount_cents=12900,
            currency="USD",
            billing_period=Price.BillingPeriod.ONE_TIME,
            is_default=True,
            is_active=True,
        )
        product.active_price = price
        product.save(update_fields=["active_price", "updated_at"])

        asset = DigitalAsset.objects.create(
            product=product,
            title="Bundle ZIP",
            file_path=f"files/creator-bundle-v{suffix}.zip",
            is_active=True,
        )

        create_response = self._request(
            "post",
            "/api/account/orders/create/",
            {"price_id": price.id, "quantity": 1, "notes": "test purchase"},
        )
        self.assertEqual(create_response.status_code, 201)

        public_id = create_response.data["order"]["public_id"]
        confirm_response = self._request(
            "post",
            f"/api/account/orders/{public_id}/confirm/",
            {"provider": "manual", "external_id": f"txn_{suffix}"},
        )
        self.assertEqual(confirm_response.status_code, 200)
        self.assertEqual(confirm_response.data["order"]["status"], Order.Status.FULFILLED)

        buyer_profile = Profile.objects.get(clerk_user_id="buyer_123")
        grant = DownloadGrant.objects.get(customer_account=buyer_profile.customer_account, asset=asset)
        return buyer_profile.customer_account, grant, asset

    def test_public_catalog_only_returns_published_products(self):
        owner = Profile.objects.create(clerk_user_id="seller_1", email="seller@example.com")
        published = Product.objects.create(
            owner=owner,
            name="Launch Kit",
            slug="launch-kit",
            visibility=Product.Visibility.PUBLISHED,
            product_type=Product.ProductType.DIGITAL,
        )
        Price.objects.create(
            product=published,
            name="One-time",
            amount_cents=4900,
            currency="USD",
            billing_period=Price.BillingPeriod.ONE_TIME,
            is_default=True,
            is_active=True,
        )

        draft = Product.objects.create(
            owner=owner,
            name="Draft Offer",
            slug="draft-offer",
            visibility=Product.Visibility.DRAFT,
            product_type=Product.ProductType.DIGITAL,
        )
        Price.objects.create(
            product=draft,
            name="Draft price",
            amount_cents=9900,
            currency="USD",
            billing_period=Price.BillingPeriod.ONE_TIME,
            is_default=True,
            is_active=True,
        )

        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        slugs = [item["slug"] for item in response.data]
        self.assertEqual(slugs, ["launch-kit"])

    def test_create_and_confirm_order_generates_entitlements_and_downloads(self):
        buyer_account, _, _ = self._create_fulfilled_digital_order()
        self.assertEqual(
            Entitlement.objects.filter(customer_account=buyer_account, feature_key="priority_support").count(),
            1,
        )
        self.assertEqual(DownloadGrant.objects.filter(customer_account=buyer_account).count(), 1)

    @patch("api.views.send_order_fulfilled_email")
    def test_confirm_order_triggers_order_fulfillment_email(self, mock_send_order_email):
        owner = Profile.objects.create(clerk_user_id="seller_email_1", email="seller-email@example.com")
        product = Product.objects.create(
            owner=owner,
            name="Email Bundle",
            slug="email-bundle",
            visibility=Product.Visibility.PUBLISHED,
            product_type=Product.ProductType.DIGITAL,
        )
        price = Price.objects.create(
            product=product,
            name="One-time",
            amount_cents=3900,
            currency="USD",
            billing_period=Price.BillingPeriod.ONE_TIME,
            is_default=True,
            is_active=True,
        )

        create_response = self._request(
            "post",
            "/api/account/orders/create/",
            {"price_id": price.id, "quantity": 1},
        )
        self.assertEqual(create_response.status_code, 201)
        public_id = create_response.data["order"]["public_id"]

        confirm_response = self._request(
            "post",
            f"/api/account/orders/{public_id}/confirm/",
            {"provider": "manual", "external_id": "txn_email_1"},
        )
        self.assertEqual(confirm_response.status_code, 200)
        self.assertEqual(confirm_response.data["order"]["status"], Order.Status.FULFILLED)
        mock_send_order_email.assert_called_once()

    @patch("api.views.send_booking_requested_email")
    def test_booking_create_triggers_booking_email(self, mock_send_booking_email):
        owner = Profile.objects.create(clerk_user_id="seller_service_1", email="seller-service@example.com")
        service_product = Product.objects.create(
            owner=owner,
            name="Founder Advisory Session",
            slug="founder-advisory-session",
            visibility=Product.Visibility.PUBLISHED,
            product_type=Product.ProductType.SERVICE,
        )
        service_offer = ServiceOffer.objects.create(
            product=service_product,
            session_minutes=45,
            delivery_days=3,
            revision_count=1,
            onboarding_instructions="Share your current revenue funnel before session.",
        )

        response = self._request(
            "post",
            "/api/account/bookings/",
            {"service_offer": service_offer.id, "customer_notes": "Need funnel teardown"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "requested")
        mock_send_booking_email.assert_called_once()

    @override_settings(
        ASSET_STORAGE_BACKEND="supabase",
        ASSET_STORAGE_BUCKET="digital-assets",
        ASSET_STORAGE_SIGNED_URL_TTL_SECONDS=900,
        SUPABASE_URL="https://demo-project.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="service-role-key",
        SUPABASE_ANON_KEY="anon-key",
    )
    @patch("api.block_storage.get_supabase_client")
    def test_download_access_returns_supabase_signed_url(self, mock_get_supabase_client):
        _, grant, asset = self._create_fulfilled_digital_order()
        storage_bucket = mock_get_supabase_client.return_value.storage.from_.return_value
        storage_bucket.create_signed_url.return_value = {
            "signedURL": (
                f"/storage/v1/object/sign/digital-assets/{asset.file_path}"
                "?token=signed-download-token"
            )
        }

        response = self._request("post", f"/api/account/downloads/{grant.token}/access/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["download_url"],
            (
                f"https://demo-project.supabase.co/storage/v1/object/sign/digital-assets/{asset.file_path}"
                "?token=signed-download-token"
            ),
        )

        grant.refresh_from_db()
        self.assertEqual(grant.download_count, 1)
        mock_get_supabase_client.assert_called_once_with(use_service_role=True)
        storage_bucket.create_signed_url.assert_called_once_with(asset.file_path, 900)

    @override_settings(
        ASSET_STORAGE_BACKEND="supabase",
        ASSET_STORAGE_BUCKET="",
    )
    def test_download_access_does_not_consume_attempt_when_storage_is_unconfigured(self):
        _, grant, _ = self._create_fulfilled_digital_order()

        response = self._request("post", f"/api/account/downloads/{grant.token}/access/")
        self.assertEqual(response.status_code, 503)
        self.assertIn("ASSET_STORAGE_BUCKET", str(response.data.get("detail", "")))

        grant.refresh_from_db()
        self.assertEqual(grant.download_count, 0)

    @override_settings(
        ASSET_STORAGE_BACKEND="s3",
        ASSET_STORAGE_BUCKET="digital-assets",
        ASSET_STORAGE_SIGNED_URL_TTL_SECONDS=600,
        ASSET_STORAGE_S3_ENDPOINT_URL="https://storage.example.com",
        ASSET_STORAGE_S3_REGION="us-east-1",
        ASSET_STORAGE_S3_ACCESS_KEY_ID="access-key",
        ASSET_STORAGE_S3_SECRET_ACCESS_KEY="secret-key",
    )
    @patch("api.block_storage._cached_s3_client")
    def test_download_access_returns_s3_compatible_signed_url(self, mock_cached_s3_client):
        _, grant, asset = self._create_fulfilled_digital_order()
        mock_cached_s3_client.return_value.generate_presigned_url.return_value = (
            "https://storage.example.com/digital-assets/signed-download-url"
        )

        response = self._request("post", f"/api/account/downloads/{grant.token}/access/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["download_url"],
            "https://storage.example.com/digital-assets/signed-download-url",
        )

        grant.refresh_from_db()
        self.assertEqual(grant.download_count, 1)
        mock_cached_s3_client.assert_called_once_with(
            "https://storage.example.com",
            "us-east-1",
            "access-key",
            "secret-key",
        )
        mock_cached_s3_client.return_value.generate_presigned_url.assert_called_once_with(
            ClientMethod="get_object",
            Params={"Bucket": "digital-assets", "Key": asset.file_path},
            ExpiresIn=600,
        )

    def test_confirm_recurring_order_creates_subscription(self):
        owner = Profile.objects.create(clerk_user_id="seller_3", email="seller3@example.com")
        product = Product.objects.create(
            owner=owner,
            name="AI Coach Pro",
            slug="ai-coach-pro",
            visibility=Product.Visibility.PUBLISHED,
            product_type=Product.ProductType.DIGITAL,
            feature_keys=["ai_coach"],
        )
        price = Price.objects.create(
            product=product,
            name="Monthly",
            amount_cents=2900,
            currency="USD",
            billing_period=Price.BillingPeriod.MONTHLY,
            is_default=True,
            is_active=True,
        )

        create_response = self._request(
            "post",
            "/api/account/orders/create/",
            {"price_id": price.id, "quantity": 1},
        )
        self.assertEqual(create_response.status_code, 201)
        public_id = create_response.data["order"]["public_id"]

        confirm_response = self._request(
            "post",
            f"/api/account/orders/{public_id}/confirm/",
            {"provider": "clerk", "external_id": "sub_clerk_123"},
        )
        self.assertEqual(confirm_response.status_code, 200)
        self.assertEqual(confirm_response.data["order"]["status"], Order.Status.FULFILLED)

        subscription = Subscription.objects.get(clerk_subscription_id="sub_clerk_123")
        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)
        self.assertEqual(subscription.price_id, price.id)
