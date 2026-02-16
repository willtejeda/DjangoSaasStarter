from __future__ import annotations

import logging
from datetime import datetime, timezone

from django.conf import settings
from django.db.models import Q, Sum
from django.utils import timezone as django_timezone
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import DownloadGrant, Entitlement, Order, Product, Project, Subscription
from ..serializers import (
    CustomerAccountSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProfileSerializer,
    ProjectSerializer,
)
from ..tools.database.supabase import SupabaseConfigurationError, get_supabase_client
from .helpers import (
    _build_ai_provider_payload,
    _build_usage_bucket,
    _resolve_plan_tier,
    extract_billing_features,
    get_request_claims,
    get_request_customer_account,
    get_request_profile,
    sync_profile_from_claims,
)

logger = logging.getLogger(__name__)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = get_request_claims(request)
        billing_features = extract_billing_features(claims)
        profile = sync_profile_from_claims(claims)
        customer_account = get_request_customer_account(request)

        return Response(
            {
                "clerk_user_id": claims.get("sub"),
                "email": claims.get("email"),
                "org_id": claims.get("org_id"),
                "billing_features": billing_features,
                "profile": ProfileSerializer(profile).data if profile else None,
                "customer_account": CustomerAccountSerializer(customer_account).data,
            }
        )


class BillingFeatureView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = get_request_claims(request)
        enabled_features = set(extract_billing_features(claims))
        requested_feature = request.query_params.get("feature")

        if requested_feature:
            normalized_feature = str(requested_feature).strip().lower()
            return Response(
                {
                    "feature": normalized_feature,
                    "enabled": normalized_feature in enabled_features,
                }
            )

        return Response({"enabled_features": sorted(enabled_features)})


class AiProviderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_build_ai_provider_payload())


class AiUsageSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_request_profile(request)
        account = get_request_customer_account(request)
        claims = get_request_claims(request)

        plan_tier = _resolve_plan_tier(profile, claims)
        now = django_timezone.now()
        paid_order_count = Order.objects.filter(
            customer_account=account,
            status__in=[Order.Status.PAID, Order.Status.FULFILLED],
        ).count()
        active_subscription_count = Subscription.objects.filter(
            customer_account=account,
            status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING, Subscription.Status.PAST_DUE],
        ).count()
        current_entitlement_count = Entitlement.objects.filter(
            customer_account=account,
            is_active=True,
            starts_at__lte=now,
        ).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now)).count()
        download_total = (
            DownloadGrant.objects.filter(customer_account=account).aggregate(total=Sum("download_count")).get("total")
            or 0
        )
        has_video_feature = Entitlement.objects.filter(
            customer_account=account,
            feature_key__icontains="video",
            is_active=True,
        ).exists()

        usage_seed = {
            "tokens": (active_subscription_count * 24000) + (current_entitlement_count * 1700) + (paid_order_count * 900),
            "images": (active_subscription_count * 30) + paid_order_count + download_total,
            "videos": max(active_subscription_count - 1, 0) + (1 if has_video_feature else 0),
        }

        limits_by_plan = {
            "free": {"tokens": 50000, "images": 40, "videos": 2},
            "pro": {"tokens": 1000000, "images": 600, "videos": 40},
            "enterprise": {"tokens": None, "images": None, "videos": None},
        }
        limits = limits_by_plan.get(plan_tier, limits_by_plan["free"])

        buckets = [
            _build_usage_bucket(
                key="tokens",
                label="LLM Tokens",
                used=usage_seed["tokens"],
                limit=limits["tokens"],
                unit="tokens",
                reset_window="monthly",
            ),
            _build_usage_bucket(
                key="images",
                label="Image Generations",
                used=usage_seed["images"],
                limit=limits["images"],
                unit="images",
                reset_window="monthly",
            ),
            _build_usage_bucket(
                key="videos",
                label="Video Generations",
                used=usage_seed["videos"],
                limit=limits["videos"],
                unit="videos",
                reset_window="monthly",
            ),
        ]

        return Response(
            {
                "period": "current_month",
                "plan_tier": plan_tier,
                "buckets": buckets,
                "notes": [
                    "Usage values are starter placeholders until you stream provider telemetry.",
                    "Map entitlement keys to provider limits before production launch.",
                    "Webhook-verified subscriptions should remain the billing source of truth.",
                ],
            }
        )


class SupabaseProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = get_request_claims(request)
        clerk_user_id = claims.get("sub")
        if not clerk_user_id:
            return Response({"ok": False, "detail": "Missing Clerk user id in token claims."}, status=400)

        try:
            logger.debug("Running Supabase profile probe for user %s.", clerk_user_id)
            supabase = get_supabase_client(access_token=getattr(request, "clerk_token", None))
            result = (
                supabase.table("profiles")
                .select("*")
                .eq("clerk_user_id", clerk_user_id)
                .limit(1)
                .execute()
            )
        except SupabaseConfigurationError as exc:
            logger.warning("Supabase probe failed due to configuration: %s", exc)
            return Response(
                {
                    "ok": False,
                    "detail": "Supabase probe failed. Check SUPABASE_URL and API keys.",
                    **({"error": str(exc)} if settings.DEBUG else {}),
                }
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("Unexpected error during Supabase profile probe for user %s.", clerk_user_id)
            return Response(
                {
                    "ok": False,
                    "detail": "Supabase probe failed. Confirm table and RLS setup.",
                    **({"error": str(exc)} if settings.DEBUG else {}),
                }
            )

        data = getattr(result, "data", None)
        profile = data[0] if isinstance(data, list) and data else data
        return Response(
            {
                "ok": True,
                "detail": (
                    "Supabase profile probe succeeded."
                    if profile
                    else "Supabase probe succeeded. No profile row found yet."
                ),
                "profile": profile,
            }
        )


class ClerkUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = get_request_claims(request)
        clerk_user_id = claims.get("sub")
        if not clerk_user_id:
            return Response(
                {"detail": "Missing Clerk user id in token claims."}, status=400
            )

        try:
            from ..tools.auth.clerk import ClerkClientError, get_clerk_user

            user = get_clerk_user(clerk_user_id)
        except ClerkClientError as exc:
            logger.warning("Clerk user fetch failed for %s: %s", clerk_user_id, exc)
            return Response({"detail": str(exc)}, status=500)
        except Exception as exc:
            logger.exception("Unexpected Clerk API error for %s.", clerk_user_id)
            return Response(
                {
                    "detail": "Clerk API call failed.",
                    **({"error": str(exc)} if settings.DEBUG else {}),
                },
                status=502,
            )

        email_addresses = []
        if hasattr(user, "email_addresses") and user.email_addresses:
            email_addresses = [
                {
                    "email": ea.email_address,
                    "verified": getattr(getattr(ea, "verification", None), "status", None) == "verified",
                }
                for ea in user.email_addresses
            ]

        return Response(
            {
                "clerk_user_id": user.id,
                "first_name": getattr(user, "first_name", None),
                "last_name": getattr(user, "last_name", None),
                "image_url": getattr(user, "image_url", None),
                "email_addresses": email_addresses,
                "public_metadata": getattr(user, "public_metadata", {}),
                "created_at": getattr(user, "created_at", None),
                "last_sign_in_at": getattr(user, "last_sign_in_at", None),
            }
        )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_request_profile(request)
        return Response(ProfileSerializer(profile).data)


class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        profile = get_request_profile(self.request)
        return Project.objects.filter(owner=profile)

    def perform_create(self, serializer):
        profile = get_request_profile(self.request)
        serializer.save(owner=profile)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        profile = get_request_profile(self.request)
        return Project.objects.filter(owner=profile)


class PublicProductListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        return (
            Product.objects.filter(visibility=Product.Visibility.PUBLISHED)
            .select_related("active_price")
            .prefetch_related("prices", "assets")
            .order_by("name")
        )


class PublicProductDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Product.objects.filter(visibility=Product.Visibility.PUBLISHED)
            .select_related("active_price", "service_offer")
            .prefetch_related("prices", "assets")
        )
