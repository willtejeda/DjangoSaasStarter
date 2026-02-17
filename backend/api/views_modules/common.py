from __future__ import annotations

import logging
from uuid import uuid4
from datetime import datetime, timezone
from typing import Any

from django.conf import settings
from django.utils import timezone as django_timezone
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Product, Project
from ..serializers import (
    CustomerAccountSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProfileSerializer,
    ProjectSerializer,
)
from ..tools.ai import (
    ProviderExecutionError,
    UsageLimitExceeded,
    consume_usage_events,
    count_message_tokens,
    count_text_tokens,
    get_plan_limits,
    get_usage_totals,
    resolve_usage_period,
    run_chat,
    run_images,
)
from ..tools.database.supabase import SupabaseConfigurationError, get_supabase_client
from .account import ensure_billing_sync
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


class AiChatMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["system", "user", "assistant"])
    content = serializers.CharField(max_length=20000, allow_blank=False)
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)


class AiTokenEstimateRequestSerializer(serializers.Serializer):
    model = serializers.CharField(required=False, allow_blank=True, max_length=128)
    text = serializers.CharField(required=False, allow_blank=True, max_length=50000)
    messages = AiChatMessageSerializer(many=True, required=False)

    def validate(self, attrs):
        text = str(attrs.get("text") or "").strip()
        messages = attrs.get("messages") or []
        if not text and not messages:
            raise serializers.ValidationError("Provide either text or messages.")
        return attrs


class AiChatCompleteRequestSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(
        choices=["simulator", "openai", "openrouter", "ollama"],
        required=False,
    )
    model = serializers.CharField(required=False, allow_blank=True, max_length=128)
    messages = AiChatMessageSerializer(many=True, min_length=1)
    max_output_tokens = serializers.IntegerField(required=False, min_value=1, max_value=4096, default=320)


class AiImageGenerateRequestSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(
        choices=["simulator", "openai", "openrouter", "ollama"],
        required=False,
    )
    model = serializers.CharField(required=False, allow_blank=True, max_length=128)
    prompt = serializers.CharField(max_length=5000)
    count = serializers.IntegerField(required=False, min_value=1, max_value=10, default=1)
    size = serializers.CharField(required=False, allow_blank=True, max_length=40, default="1024x1024")


def _default_chat_provider() -> str:
    if bool(getattr(settings, "AI_SIMULATOR_ENABLED", settings.DEBUG)):
        return "simulator"
    if bool(getattr(settings, "AI_PROVIDER_CALLS_ENABLED", False)):
        if str(getattr(settings, "OPENROUTER_API_KEY", "") or "").strip():
            return "openrouter"
        if str(getattr(settings, "OPENAI_API_KEY", "") or "").strip():
            return "openai"
        if str(getattr(settings, "OLLAMA_MODEL", "") or "").strip():
            return "ollama"
    return "simulator"


def _default_chat_model(provider: str) -> str:
    fallback = str(getattr(settings, "AI_DEFAULT_CHAT_MODEL", "") or "gpt-4.1-mini")
    if provider == "openrouter":
        return str(getattr(settings, "OPENROUTER_DEFAULT_MODEL", "") or fallback)
    if provider == "openai":
        return str(getattr(settings, "OPENAI_DEFAULT_MODEL", "") or fallback)
    if provider == "ollama":
        return str(getattr(settings, "OLLAMA_MODEL", "") or fallback)
    return fallback


def _default_image_model(provider: str) -> str:
    if provider == "openrouter":
        return str(getattr(settings, "OPENROUTER_IMAGE_MODEL", "") or "openai/gpt-image-1")
    if provider == "openai":
        return str(getattr(settings, "OPENAI_IMAGE_MODEL", "") or "gpt-image-1")
    if provider == "ollama":
        return str(getattr(settings, "OLLAMA_IMAGE_MODEL", "") or "")
    return "debug-image-v1"


def _ensure_provider_mode_allowed(provider: str) -> None:
    if provider == "simulator":
        if not bool(getattr(settings, "AI_SIMULATOR_ENABLED", settings.DEBUG)):
            raise serializers.ValidationError("Simulator mode is disabled. Set AI_SIMULATOR_ENABLED=True to use it.")
        return
    if not bool(getattr(settings, "AI_PROVIDER_CALLS_ENABLED", False)):
        raise serializers.ValidationError(
            "Provider calls are disabled. Set AI_PROVIDER_CALLS_ENABLED=True to route requests to external providers."
        )


def _billing_sync_blocked_response(billing_sync: dict[str, Any]) -> Response:
    return Response(
        {
            "detail": str(
                billing_sync.get("detail")
                or "Billing verification is temporarily unavailable. Retry in a moment."
            ),
            "error_code": "billing_sync_hard_stale",
            "billing_sync": billing_sync,
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


class AiUsageSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_request_profile(request)
        account = get_request_customer_account(request)
        claims = get_request_claims(request)
        billing_sync = ensure_billing_sync(account)

        plan_tier = _resolve_plan_tier(profile, claims)
        now = django_timezone.now()
        period = resolve_usage_period(account, now)
        limits = get_plan_limits(plan_tier)
        totals = get_usage_totals(account, period)

        buckets = [
            _build_usage_bucket(
                key="tokens",
                label="LLM Tokens",
                used=totals["tokens"],
                limit=limits["tokens"],
                unit="tokens",
                reset_window="billing_cycle",
            ),
            _build_usage_bucket(
                key="images",
                label="Image Generations",
                used=totals["images"],
                limit=limits["images"],
                unit="images",
                reset_window="billing_cycle",
            ),
            _build_usage_bucket(
                key="videos",
                label="Video Generations",
                used=totals["videos"],
                limit=limits["videos"],
                unit="videos",
                reset_window="billing_cycle",
            ),
        ]

        return Response(
            {
                "period": "current_billing_cycle",
                "period_start": period.start.isoformat(),
                "period_end": period.end.isoformat(),
                "period_source": period.source,
                "plan_tier": plan_tier,
                "buckets": buckets,
                "billing_sync": billing_sync,
                "notes": [
                    "Backend usage ledger is the source of truth for enforcement and dashboard reporting.",
                    "Frontend token estimation is optimistic and may differ from provider-reported usage.",
                    "Billing-cycle resets follow subscription periods when available.",
                ],
            }
        )


class AiTokenEstimateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AiTokenEstimateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        model_name = str(payload.get("model") or "").strip() or str(getattr(settings, "AI_DEFAULT_CHAT_MODEL", ""))
        messages = payload.get("messages") or []
        text = str(payload.get("text") or "")
        message_tokens = count_message_tokens(messages, model=model_name) if messages else 0
        text_tokens = count_text_tokens(text, model=model_name) if text else 0

        return Response(
            {
                "model": model_name,
                "estimated_tokens": {
                    "messages": message_tokens,
                    "text": text_tokens,
                    "total": message_tokens + text_tokens,
                },
                "notes": [
                    "Estimate uses backend tokenizer and is used for preflight checks.",
                    "Provider-reported usage still wins when available.",
                ],
            }
        )


class AiChatCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AiChatCompleteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        provider = str(payload.get("provider") or _default_chat_provider()).strip().lower()
        _ensure_provider_mode_allowed(provider)
        model_name = str(payload.get("model") or "").strip() or _default_chat_model(provider)
        max_output_tokens = int(payload.get("max_output_tokens") or 320)
        messages = [
            {
                "role": item["role"],
                "content": item["content"],
                **({"name": item["name"]} if item.get("name") else {}),
            }
            for item in payload.get("messages", [])
        ]

        profile = get_request_profile(request)
        account = get_request_customer_account(request)
        claims = get_request_claims(request)
        plan_tier = _resolve_plan_tier(profile, claims)
        billing_sync = ensure_billing_sync(account)
        if billing_sync.get("blocking"):
            return _billing_sync_blocked_response(billing_sync)

        try:
            completion = run_chat(
                provider=provider,
                messages=messages,
                model_name=model_name,
                max_output_tokens=max_output_tokens,
            )
        except ProviderExecutionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        period = resolve_usage_period(account, django_timezone.now())
        request_id = uuid4()

        try:
            usage_write = consume_usage_events(
                account=account,
                plan_tier=plan_tier,
                period=period,
                events=[
                    {
                        "request_id": request_id,
                        "metric": "tokens",
                        "direction": "input",
                        "amount": completion.input_tokens,
                        "provider": completion.provider,
                        "model_name": completion.model_name,
                        "metadata": {"endpoint": "ai/chat/complete"},
                    },
                    {
                        "request_id": request_id,
                        "metric": "tokens",
                        "direction": "output",
                        "amount": completion.output_tokens,
                        "provider": completion.provider,
                        "model_name": completion.model_name,
                        "metadata": {"endpoint": "ai/chat/complete"},
                    },
                ],
            )
        except UsageLimitExceeded as exc:
            return Response({"detail": str(exc)}, status=exc.status_code)

        limits = usage_write["limits"]
        totals = usage_write["totals"]
        token_limit = limits.get("tokens")
        token_used = totals.get("tokens", 0)
        token_remaining = None if token_limit is None else max(int(token_limit) - int(token_used), 0)

        notes = [
            "Backend usage is authoritative for quota enforcement.",
            "Requests are blocked when the cycle limit is exceeded.",
        ]
        if billing_sync.get("state") != "fresh":
            notes.append(
                f"Billing sync status is {billing_sync.get('state')} ({billing_sync.get('reason_code')})."
            )

        return Response(
            {
                "request_id": str(request_id),
                "provider": completion.provider,
                "model": completion.model_name,
                "assistant_message": completion.content,
                "usage": {
                    "input_tokens": completion.input_tokens,
                    "output_tokens": completion.output_tokens,
                    "total_tokens": completion.input_tokens + completion.output_tokens,
                    "cycle_tokens_used": token_used,
                    "cycle_tokens_limit": token_limit,
                    "cycle_tokens_remaining": token_remaining,
                    "period_start": period.start.isoformat(),
                    "period_end": period.end.isoformat(),
                },
                "billing_sync": billing_sync,
                "notes": notes,
            }
        )


class AiImageGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AiImageGenerateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        provider = str(payload.get("provider") or _default_chat_provider()).strip().lower()
        _ensure_provider_mode_allowed(provider)
        model_name = str(payload.get("model") or "").strip() or _default_image_model(provider)
        prompt = str(payload.get("prompt") or "").strip()
        count = int(payload.get("count") or 1)
        size = str(payload.get("size") or getattr(settings, "AI_DEFAULT_IMAGE_SIZE", "1024x1024")).strip()

        profile = get_request_profile(request)
        account = get_request_customer_account(request)
        claims = get_request_claims(request)
        plan_tier = _resolve_plan_tier(profile, claims)
        billing_sync = ensure_billing_sync(account)
        if billing_sync.get("blocking"):
            return _billing_sync_blocked_response(billing_sync)

        try:
            image_result = run_images(
                provider=provider,
                prompt=prompt,
                count=count,
                model_name=model_name,
                size=size,
            )
        except ProviderExecutionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        period = resolve_usage_period(account, django_timezone.now())
        request_id = uuid4()

        try:
            usage_write = consume_usage_events(
                account=account,
                plan_tier=plan_tier,
                period=period,
                events=[
                    {
                        "request_id": request_id,
                        "metric": "images",
                        "direction": "total",
                        "amount": image_result.image_units,
                        "provider": image_result.provider,
                        "model_name": image_result.model_name,
                        "metadata": {"endpoint": "ai/images/generate"},
                    }
                ],
            )
        except UsageLimitExceeded as exc:
            return Response({"detail": str(exc)}, status=exc.status_code)

        limits = usage_write["limits"]
        totals = usage_write["totals"]
        image_limit = limits.get("images")
        image_used = totals.get("images", 0)
        image_remaining = None if image_limit is None else max(int(image_limit) - int(image_used), 0)

        notes = [
            "Image quota uses one image = one usage unit.",
            "Backend usage is authoritative for enforcement.",
        ]
        if billing_sync.get("state") != "fresh":
            notes.append(
                f"Billing sync status is {billing_sync.get('state')} ({billing_sync.get('reason_code')})."
            )

        return Response(
            {
                "request_id": str(request_id),
                "provider": image_result.provider,
                "model": image_result.model_name,
                "images": image_result.images,
                "usage": {
                    "images_generated": image_result.image_units,
                    "cycle_images_used": image_used,
                    "cycle_images_limit": image_limit,
                    "cycle_images_remaining": image_remaining,
                    "period_start": period.start.isoformat(),
                    "period_end": period.end.isoformat(),
                },
                "billing_sync": billing_sync,
                "notes": notes,
            }
        )


class SupabaseProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = get_request_claims(request)
        clerk_user_id = claims.get("sub")
        if not clerk_user_id:
            return Response({"ok": False, "detail": "Missing Clerk user id in token claims."}, status=400)

        configured_table = str(getattr(settings, "SUPABASE_PROFILE_TABLE", "") or "").strip()
        probe_tables: list[str] = []
        for table_name in (configured_table, "api_profile", "profiles"):
            normalized = str(table_name or "").strip()
            if normalized and normalized not in probe_tables:
                probe_tables.append(normalized)

        try:
            logger.debug("Running Supabase profile probe for user %s.", clerk_user_id)
            # Use anon-key probe mode by default. Forwarding Clerk JWTs to
            # PostgREST can fail unless Supabase JWT verification is configured
            # for that issuer.
            supabase = get_supabase_client()
        except SupabaseConfigurationError as exc:
            logger.warning("Supabase probe failed due to configuration: %s", exc)
            return Response(
                {
                    "ok": False,
                    "detail": "Supabase probe failed. Check SUPABASE_URL and API keys.",
                    **({"error": str(exc)} if settings.DEBUG else {}),
                }
            )

        last_exception: Exception | None = None
        for table_name in probe_tables:
            try:
                result = (
                    supabase.table(table_name)
                    .select("*")
                    .eq("clerk_user_id", clerk_user_id)
                    .limit(1)
                    .execute()
                )
            except Exception as exc:  # pragma: no cover
                error_text = str(exc)
                if "PGRST205" in error_text:
                    # Table does not exist in schema cache. Try next candidate.
                    logger.debug("Supabase probe table %s unavailable for user %s.", table_name, clerk_user_id)
                    last_exception = exc
                    continue

                if "PGRST301" in error_text or "wrong key type" in error_text.lower():
                    logger.warning(
                        "Supabase probe auth rejected for user %s. Check SUPABASE_ANON_KEY and PostgREST auth settings.",
                        clerk_user_id,
                    )
                else:
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
                    "source_table": table_name,
                }
            )

        detail = "Supabase probe failed. Could not find a profile table in schema cache."
        if probe_tables:
            detail = f"{detail} Tried: {', '.join(probe_tables)}."
        return Response(
            {
                "ok": False,
                "detail": detail,
                **({"error": str(last_exception)} if settings.DEBUG and last_exception else {}),
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
