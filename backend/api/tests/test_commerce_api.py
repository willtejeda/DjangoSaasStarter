from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from api.models import (
    DigitalAsset,
    DownloadGrant,
    Entitlement,
    FulfillmentOrder,
    Order,
    PaymentTransaction,
    Price,
    Product,
    Profile,
    ServiceOffer,
    Subscription,
    WebhookEvent,
)
from api.webhooks import handle_billing_checkout_upsert, handle_billing_payment_attempt_upsert


@override_settings(
    ORDER_CONFIRM_ALLOW_MANUAL=True,
    ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM=True,
)
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
        with patch("api.tools.auth.authentication.decode_clerk_token", return_value=self.claims):
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

    def _create_pending_order(self, *, amount_cents: int = 4900):
        owner = Profile.objects.create(
            clerk_user_id=f"seller_pending_{Product.objects.count() + 1}",
            email=f"seller-pending-{Product.objects.count() + 1}@example.com",
        )
        product = Product.objects.create(
            owner=owner,
            name=f"Pending Offer {Product.objects.count() + 1}",
            slug=f"pending-offer-{Product.objects.count() + 1}",
            visibility=Product.Visibility.PUBLISHED,
            product_type=Product.ProductType.DIGITAL,
            feature_keys=["priority_support"],
        )
        price = Price.objects.create(
            product=product,
            name="One-time",
            amount_cents=amount_cents,
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
        return Order.objects.get(public_id=public_id)

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

    def test_digital_purchase_without_assets_creates_locked_download_object(self):
        owner = Profile.objects.create(clerk_user_id="seller_digital_no_asset", email="seller-no-asset@example.com")
        product = Product.objects.create(
            owner=owner,
            name="Template Pack Placeholder",
            slug="template-pack-placeholder",
            visibility=Product.Visibility.PUBLISHED,
            product_type=Product.ProductType.DIGITAL,
        )
        price = Price.objects.create(
            product=product,
            name="One-time",
            amount_cents=1900,
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
            {"provider": "manual", "external_id": "txn_no_asset_1"},
        )
        self.assertEqual(confirm_response.status_code, 200)
        self.assertEqual(confirm_response.data["order"]["status"], Order.Status.FULFILLED)

        buyer_profile = Profile.objects.get(clerk_user_id="buyer_123")
        grant = DownloadGrant.objects.get(
            customer_account=buyer_profile.customer_account,
            order_item__order__public_id=public_id,
        )
        self.assertFalse(grant.can_download)
        self.assertFalse(grant.asset.is_active)
        self.assertEqual(grant.asset.metadata.get("pending_reason"), "missing_digital_asset")

    @patch("api.views_modules.account.send_order_fulfilled_email")
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

    @patch("api.views_modules.account.send_fulfillment_order_requested_email")
    def test_service_purchase_creates_downloadable_fulfillment_order_and_pending_download(
        self,
        mock_send_fulfillment_email,
    ):
        owner = Profile.objects.create(clerk_user_id="seller_service_1", email="seller-service@example.com")
        service_product = Product.objects.create(
            owner=owner,
            name="Founder Advisory Session",
            slug="founder-advisory-session",
            visibility=Product.Visibility.PUBLISHED,
            product_type=Product.ProductType.SERVICE,
        )
        price = Price.objects.create(
            product=service_product,
            name="Service",
            amount_cents=15000,
            currency="USD",
            billing_period=Price.BillingPeriod.ONE_TIME,
            is_default=True,
            is_active=True,
        )
        ServiceOffer.objects.create(
            product=service_product,
            session_minutes=45,
            delivery_days=3,
            revision_count=1,
            onboarding_instructions="Share your current revenue funnel before session.",
            metadata={"delivery_mode": "downloadable"},
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
            {"provider": "manual", "external_id": "txn_service_1"},
        )
        self.assertEqual(confirm_response.status_code, 200)
        self.assertEqual(confirm_response.data["order"]["status"], Order.Status.FULFILLED)

        fulfillment_order = FulfillmentOrder.objects.get(order_item__order__public_id=public_id)
        self.assertEqual(fulfillment_order.status, FulfillmentOrder.Status.REQUESTED)
        self.assertEqual(fulfillment_order.delivery_mode, FulfillmentOrder.DeliveryMode.DOWNLOADABLE)
        self.assertIsNotNone(fulfillment_order.download_grant_id)
        self.assertFalse(fulfillment_order.download_grant.can_download)
        self.assertFalse(fulfillment_order.download_grant.asset.is_active)
        mock_send_fulfillment_email.assert_called_once()

    def test_service_purchase_with_physical_delivery_creates_work_order_without_download(self):
        owner = Profile.objects.create(clerk_user_id="seller_service_2", email="seller-service-2@example.com")
        service_product = Product.objects.create(
            owner=owner,
            name="Print and Ship Package",
            slug="print-and-ship-package",
            visibility=Product.Visibility.PUBLISHED,
            product_type=Product.ProductType.SERVICE,
        )
        price = Price.objects.create(
            product=service_product,
            name="Physical",
            amount_cents=22000,
            currency="USD",
            billing_period=Price.BillingPeriod.ONE_TIME,
            is_default=True,
            is_active=True,
        )
        ServiceOffer.objects.create(
            product=service_product,
            session_minutes=0,
            delivery_days=5,
            revision_count=0,
            onboarding_instructions="Provide shipping address after checkout.",
            metadata={"delivery_mode": "physical_shipped"},
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
            {"provider": "manual", "external_id": "txn_service_2"},
        )
        self.assertEqual(confirm_response.status_code, 200)

        fulfillment_order = FulfillmentOrder.objects.get(order_item__order__public_id=public_id)
        self.assertEqual(fulfillment_order.delivery_mode, FulfillmentOrder.DeliveryMode.PHYSICAL_SHIPPED)
        self.assertIsNone(fulfillment_order.download_grant)

    @override_settings(
        ASSET_STORAGE_BACKEND="supabase",
        ASSET_STORAGE_BUCKET="digital-assets",
        ASSET_STORAGE_SIGNED_URL_TTL_SECONDS=900,
        SUPABASE_URL="https://demo-project.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="service-role-key",
        SUPABASE_ANON_KEY="anon-key",
    )
    @patch("api.tools.storage.block_storage.get_supabase_client")
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
    @patch("api.tools.storage.block_storage._cached_s3_client")
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

    def test_subscription_list_backfills_from_webhook_history_for_current_user(self):
        WebhookEvent.objects.create(
            provider=WebhookEvent.Provider.CLERK,
            event_id="evt_sub_backfill_1",
            event_type="subscription.active",
            status=WebhookEvent.Status.PROCESSED,
            payload={
                "type": "subscription.active",
                "data": {
                    "id": "sub_backfill_1",
                    "status": "active",
                    "payer": {"id": "payer_backfill_1", "user_id": "buyer_123"},
                },
            },
        )

        response = self._request("get", "/api/account/subscriptions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["clerk_subscription_id"], "sub_backfill_1")
        self.assertEqual(response.data[0]["status"], Subscription.Status.ACTIVE)

    def test_subscription_list_backfill_refreshes_existing_subscription_rows(self):
        initial_response = self._request("get", "/api/account/subscriptions/")
        self.assertEqual(initial_response.status_code, 200)

        buyer_profile = Profile.objects.get(clerk_user_id="buyer_123")
        existing_subscription = Subscription.objects.create(
            customer_account=buyer_profile.customer_account,
            status=Subscription.Status.CANCELED,
            clerk_subscription_id="sub_backfill_existing_1",
        )

        WebhookEvent.objects.create(
            provider=WebhookEvent.Provider.CLERK,
            event_id="evt_sub_backfill_existing_1",
            event_type="subscription.active",
            status=WebhookEvent.Status.PROCESSED,
            payload={
                "type": "subscription.active",
                "data": {
                    "id": "sub_backfill_existing_1",
                    "status": "active",
                    "payer": {"id": "payer_existing_1", "user_id": "buyer_123"},
                },
            },
        )

        refreshed_response = self._request("get", "/api/account/subscriptions/")
        self.assertEqual(refreshed_response.status_code, 200)

        existing_subscription.refresh_from_db()
        self.assertEqual(existing_subscription.status, Subscription.Status.ACTIVE)
        self.assertTrue(
            any(
                row.get("clerk_subscription_id") == "sub_backfill_existing_1"
                and row.get("status") == Subscription.Status.ACTIVE
                for row in refreshed_response.data
            )
        )

    def test_payment_attempt_webhook_fulfills_pending_order(self):
        order = self._create_pending_order()

        handle_billing_payment_attempt_upsert(
            {
                "id": "pay_attempt_123",
                "status": "succeeded",
                "checkout_id": "checkout_abc",
                "metadata": {"order_public_id": str(order.public_id)},
            }
        )

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.FULFILLED)
        self.assertEqual(order.clerk_checkout_id, "checkout_abc")
        self.assertEqual(order.external_reference, "pay_attempt_123")
        self.assertTrue(
            PaymentTransaction.objects.filter(
                provider=PaymentTransaction.Provider.CLERK,
                external_id="pay_attempt_123",
                order=order,
                status=PaymentTransaction.Status.SUCCEEDED,
            ).exists()
        )

    def test_checkout_webhook_fulfills_pending_order(self):
        order = self._create_pending_order(amount_cents=7900)

        handle_billing_checkout_upsert(
            {
                "id": "checkout_xyz",
                "status": "completed",
                "metadata": {"order_public_id": str(order.public_id)},
            }
        )

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.FULFILLED)
        self.assertEqual(order.clerk_checkout_id, "checkout_xyz")
        self.assertEqual(order.external_reference, "checkout_xyz")
        self.assertTrue(
            PaymentTransaction.objects.filter(
                provider=PaymentTransaction.Provider.CLERK,
                external_id="checkout_xyz",
                order=order,
                status=PaymentTransaction.Status.SUCCEEDED,
            ).exists()
        )

    def test_failed_payment_attempt_webhook_does_not_fulfill_order(self):
        order = self._create_pending_order()

        handle_billing_payment_attempt_upsert(
            {
                "id": "pay_attempt_failed",
                "status": "failed",
                "metadata": {"order_public_id": str(order.public_id)},
            }
        )

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING_PAYMENT)
        self.assertTrue(
            PaymentTransaction.objects.filter(
                provider=PaymentTransaction.Provider.CLERK,
                external_id="pay_attempt_failed",
                order=order,
                status=PaymentTransaction.Status.FAILED,
            ).exists()
        )


@override_settings(
    ORDER_CONFIRM_ALLOW_MANUAL=False,
    ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM=False,
)
class OrderConfirmSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.auth_headers = {"HTTP_AUTHORIZATION": "Bearer unit-test-token"}
        self.claims = {
            "sub": "buyer_security_1",
            "email": "security@example.com",
            "given_name": "Secure",
            "family_name": "Buyer",
            "entitlements": ["free"],
        }

        owner = Profile.objects.create(clerk_user_id="seller_security_1", email="seller-security@example.com")
        product = Product.objects.create(
            owner=owner,
            name="Security Offer",
            slug="security-offer",
            visibility=Product.Visibility.PUBLISHED,
            product_type=Product.ProductType.DIGITAL,
        )
        self.price = Price.objects.create(
            product=product,
            name="One-time",
            amount_cents=3300,
            currency="USD",
            billing_period=Price.BillingPeriod.ONE_TIME,
            is_default=True,
            is_active=True,
        )

    def _request(self, method: str, path: str, data=None):
        with patch("api.tools.auth.authentication.decode_clerk_token", return_value=self.claims):
            handler = getattr(self.client, method)
            return handler(path, data=data, format="json", **self.auth_headers)

    def test_manual_confirm_disabled_by_default(self):
        create_response = self._request(
            "post",
            "/api/account/orders/create/",
            {"price_id": self.price.id, "quantity": 1},
        )
        self.assertEqual(create_response.status_code, 201)

        public_id = create_response.data["order"]["public_id"]
        confirm_response = self._request(
            "post",
            f"/api/account/orders/{public_id}/confirm/",
            {"provider": "manual", "external_id": "txn_manual"},
        )
        self.assertEqual(confirm_response.status_code, 403)
        self.assertTrue(confirm_response.data["detail"].startswith("Manual order confirmation is disabled"))

    def test_direct_clerk_confirm_disabled_by_default(self):
        create_response = self._request(
            "post",
            "/api/account/orders/create/",
            {"price_id": self.price.id, "quantity": 1},
        )
        self.assertEqual(create_response.status_code, 201)

        public_id = create_response.data["order"]["public_id"]
        confirm_response = self._request(
            "post",
            f"/api/account/orders/{public_id}/confirm/",
            {"provider": "clerk", "external_id": "pay_direct"},
        )
        self.assertEqual(confirm_response.status_code, 409)
        self.assertTrue(confirm_response.data["pending_verification"])
