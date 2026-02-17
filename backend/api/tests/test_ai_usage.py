from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import AiUsageEvent, Profile, Subscription
from api.tools.auth.clerk import ClerkClientError


@override_settings(
    AI_SIMULATOR_ENABLED=True,
    AI_PROVIDER_CALLS_ENABLED=False,
    AI_USAGE_ENFORCEMENT_ENABLED=True,
    AI_DEFAULT_CHAT_MODEL="gpt-3.5-turbo",
)
class AiUsageApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.auth_headers = {"HTTP_AUTHORIZATION": "Bearer unit-test-token"}
        self.claims = {
            "sub": "ai_user_1",
            "email": "ai-user@example.com",
            "given_name": "Ai",
            "family_name": "User",
            "entitlements": ["free"],
        }

    def _request(
        self,
        method: str,
        path: str,
        data=None,
        *,
        billing_error: Exception | None = None,
        billing_response: dict | None = None,
    ):
        with patch("api.tools.auth.authentication.decode_clerk_token", return_value=self.claims), patch(
            "api.views_modules.account.get_clerk_client"
        ) as mock_get_clerk_client:
            if billing_error is not None:
                mock_get_clerk_client.side_effect = billing_error
            else:
                mock_client = Mock()
                mock_client.users.get_billing_subscription.return_value = billing_response or {
                    "data": {
                        "id": "ai_user_1",
                        "billing": {"subscription": None},
                    }
                }
                mock_get_clerk_client.return_value = mock_client
            handler = getattr(self.client, method)
            return handler(path, data=data, format="json", **self.auth_headers)

    def test_token_estimate_endpoint_returns_nonzero_total(self):
        response = self._request(
            "post",
            "/api/ai/tokens/estimate/",
            {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Count my tokens"}],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data["estimated_tokens"]["messages"], 0)
        self.assertGreater(response.data["estimated_tokens"]["total"], 0)

    @override_settings(AI_USAGE_LIMIT_FREE_TOKENS=40)
    def test_chat_simulator_enforces_server_side_token_quota(self):
        first_response = self._request(
            "post",
            "/api/ai/chat/complete/",
            {
                "provider": "simulator",
                "model": "gpt-3.5-turbo",
                "max_output_tokens": 8,
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(AiUsageEvent.objects.filter(metric="tokens").count(), 2)

        second_response = self._request(
            "post",
            "/api/ai/chat/complete/",
            {
                "provider": "simulator",
                "model": "gpt-3.5-turbo",
                "max_output_tokens": 200,
                "messages": [{"role": "user", "content": "Please return a longer response for quota testing."}],
            },
        )
        self.assertEqual(second_response.status_code, 429)
        self.assertIn("quota exceeded", str(second_response.data.get("detail", "")).lower())
        self.assertEqual(AiUsageEvent.objects.filter(metric="tokens").count(), 2)

    @override_settings(
        BILLING_SYNC_SOFT_STALE_SECONDS=900,
        BILLING_SYNC_HARD_TTL_SECONDS=10800,
    )
    def test_chat_allows_soft_stale_billing_state_with_warning(self):
        self._request("get", "/api/me/")
        profile = Profile.objects.get(clerk_user_id="ai_user_1")
        account = profile.customer_account
        account.metadata = {
            "billing_sync": {
                "last_success_at": (timezone.now() - timedelta(minutes=30)).isoformat(),
                "last_attempt_at": timezone.now().isoformat(),
                "last_attempt_succeeded": True,
                "last_reason_code": "synced",
                "last_error_code": "",
            }
        }
        account.save(update_fields=["metadata", "updated_at"])

        response = self._request(
            "post",
            "/api/ai/chat/complete/",
            {
                "provider": "simulator",
                "model": "gpt-3.5-turbo",
                "max_output_tokens": 8,
                "messages": [{"role": "user", "content": "hello"}],
            },
            billing_error=ClerkClientError("client-unavailable"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["billing_sync"]["state"], "soft_stale")
        self.assertFalse(response.data["billing_sync"]["blocking"])
        self.assertEqual(response.data["billing_sync"]["error_code"], "clerk_client_unavailable")

    @override_settings(
        BILLING_SYNC_SOFT_STALE_SECONDS=900,
        BILLING_SYNC_HARD_TTL_SECONDS=10800,
    )
    def test_chat_blocks_when_billing_sync_is_hard_stale(self):
        response = self._request(
            "post",
            "/api/ai/chat/complete/",
            {
                "provider": "simulator",
                "model": "gpt-3.5-turbo",
                "max_output_tokens": 8,
                "messages": [{"role": "user", "content": "hello"}],
            },
            billing_error=ClerkClientError("client-unavailable"),
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["error_code"], "billing_sync_hard_stale")
        self.assertTrue(response.data["billing_sync"]["blocking"])

    @override_settings(AI_USAGE_LIMIT_FREE_IMAGES=2)
    def test_image_generation_uses_one_unit_per_image(self):
        first_response = self._request(
            "post",
            "/api/ai/images/generate/",
            {
                "provider": "simulator",
                "prompt": "A mountain at sunrise",
                "count": 2,
            },
        )
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(first_response.data["usage"]["images_generated"], 2)
        self.assertEqual(AiUsageEvent.objects.filter(metric="images").count(), 1)

        second_response = self._request(
            "post",
            "/api/ai/images/generate/",
            {
                "provider": "simulator",
                "prompt": "Another mountain",
                "count": 1,
            },
        )
        self.assertEqual(second_response.status_code, 429)
        self.assertIn("quota exceeded", str(second_response.data.get("detail", "")).lower())
        self.assertEqual(AiUsageEvent.objects.filter(metric="images").count(), 1)

    def test_usage_summary_uses_subscription_cycle_window(self):
        self._request("get", "/api/me/")
        profile = Profile.objects.get(clerk_user_id="ai_user_1")
        account = profile.customer_account
        now = timezone.now()
        period_start = now - timedelta(days=3)
        period_end = now + timedelta(days=27)
        Subscription.objects.create(
            customer_account=account,
            status=Subscription.Status.ACTIVE,
            current_period_start=period_start,
            current_period_end=period_end,
        )

        in_cycle_event = AiUsageEvent.objects.create(
            customer_account=account,
            metric=AiUsageEvent.Metric.TOKENS,
            direction=AiUsageEvent.Direction.TOTAL,
            amount=111,
            provider="simulator",
            model_name="gpt-3.5-turbo",
            period_start=period_start,
            period_end=period_end,
        )
        out_of_cycle_event = AiUsageEvent.objects.create(
            customer_account=account,
            metric=AiUsageEvent.Metric.TOKENS,
            direction=AiUsageEvent.Direction.TOTAL,
            amount=999,
            provider="simulator",
            model_name="gpt-3.5-turbo",
            period_start=period_start - timedelta(days=30),
            period_end=period_end - timedelta(days=30),
        )
        AiUsageEvent.objects.filter(pk=in_cycle_event.pk).update(created_at=now - timedelta(hours=2))
        AiUsageEvent.objects.filter(pk=out_of_cycle_event.pk).update(created_at=now - timedelta(days=45))

        response = self._request(
            "get",
            "/api/ai/usage/summary/",
            billing_response={
                "data": {
                    "id": "ai_user_1",
                    "billing": {
                        "subscription": {
                            "id": "sub_usage_summary_1",
                            "status": "active",
                            "current_period_start": period_start.isoformat(),
                            "current_period_end": period_end.isoformat(),
                            "cancel_at_period_end": False,
                        }
                    },
                }
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["period_source"], "subscription_cycle")
        token_bucket = next(bucket for bucket in response.data["buckets"] if bucket["key"] == "tokens")
        self.assertEqual(token_bucket["used"], 111)
