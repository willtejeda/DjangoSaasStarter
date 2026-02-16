from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from api.models import Profile, Project


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
        with patch("api.tools.auth.authentication.decode_clerk_token", return_value=self.claims):
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

    @override_settings(
        OPENROUTER_API_KEY="or_test_key",
        OPENROUTER_BASE_URL="https://openrouter.ai/api/v1",
        OPENROUTER_DEFAULT_MODEL="openai/gpt-4.1-mini",
        OLLAMA_BASE_URL="http://127.0.0.1:11434",
        OLLAMA_MODEL="llama3.2",
    )
    def test_ai_provider_endpoint_returns_env_configured_providers(self):
        response = self._request("get", "/api/ai/providers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        openrouter = next(item for item in response.data if item["key"] == "openrouter")
        ollama = next(item for item in response.data if item["key"] == "ollama")
        self.assertTrue(openrouter["enabled"])
        self.assertEqual(openrouter["base_url"], "https://openrouter.ai/api/v1")
        self.assertEqual(openrouter["model_hint"], "openai/gpt-4.1-mini")
        self.assertTrue(ollama["enabled"])
        self.assertEqual(ollama["base_url"], "http://127.0.0.1:11434")

    def test_ai_usage_summary_returns_buckets(self):
        response = self._request("get", "/api/ai/usage/summary/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["plan_tier"], "pro")
        self.assertEqual(len(response.data["buckets"]), 3)
        self.assertEqual({bucket["key"] for bucket in response.data["buckets"]}, {"tokens", "images", "videos"})
        self.assertIn("notes", response.data)

    def test_supabase_profile_probe_returns_soft_failure_when_unconfigured(self):
        response = self._request("get", "/api/supabase/profile/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["ok"])
        self.assertIn("Supabase probe failed", response.data["detail"])

    @override_settings(
        SUPABASE_URL="https://demo-project.supabase.co",
        SUPABASE_ANON_KEY="anon-key",
    )
    @patch("api.views_modules.common.get_supabase_client")
    def test_supabase_profile_probe_returns_profile_when_query_succeeds(self, mock_get_supabase_client):
        result = Mock()
        result.data = [{"id": 1, "clerk_user_id": "user_123"}]
        supabase = Mock()
        supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = result
        mock_get_supabase_client.return_value = supabase

        response = self._request("get", "/api/supabase/profile/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["ok"])
        self.assertEqual(response.data["profile"]["clerk_user_id"], "user_123")
        mock_get_supabase_client.assert_called_once_with(access_token="unit-test-token")

    def test_preflight_email_test_requires_resend_config(self):
        response = self._request("post", "/api/account/preflight/email-test/")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["sent"])

    @override_settings(
        RESEND_API_KEY="re_test_key",
        RESEND_FROM_EMAIL="Acme <updates@example.com>",
    )
    @patch("api.views_modules.account.send_preflight_test_email")
    def test_preflight_email_test_updates_customer_metadata(self, mock_send_preflight):
        mock_send_preflight.return_value = (True, "owner@example.com")

        response = self._request("post", "/api/account/preflight/email-test/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["sent"])
        self.assertEqual(response.data["recipient_email"], "owner@example.com")

        profile = Profile.objects.get(clerk_user_id="user_123")
        account = profile.customer_account
        self.assertIn("preflight_email_last_sent_at", account.metadata)
        self.assertEqual(account.metadata.get("preflight_email_last_recipient"), "owner@example.com")
        mock_send_preflight.assert_called_once_with(account)

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
