from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .billing import (
    extract_billing_features as extract_billing_features_from_claims,
    infer_plan_tier as infer_plan_tier_from_features,
)
from .models import Profile, Project
from .serializers import ProfileSerializer, ProjectSerializer
from .supabase_client import SupabaseConfigurationError, get_supabase_client


def extract_billing_features(claims: dict[str, Any]) -> list[str]:
    """Backward-compatible local wrapper used by existing tests."""
    return extract_billing_features_from_claims(claims)


def infer_plan_tier(features: list[str]) -> str:
    """Backward-compatible local wrapper used by existing code paths."""
    return infer_plan_tier_from_features(features)


def _safe_str(value: Any) -> str:
    return str(value).strip() if value else ""


def sync_profile_from_claims(claims: dict[str, Any]) -> Profile | None:
    clerk_user_id = _safe_str(claims.get("sub"))
    if not clerk_user_id:
        return None

    billing_features = extract_billing_features(claims)
    metadata = claims.get("metadata") if isinstance(claims.get("metadata"), dict) else {}
    defaults = {
        "email": _safe_str(claims.get("email")),
        "first_name": _safe_str(claims.get("given_name") or claims.get("first_name")),
        "last_name": _safe_str(claims.get("family_name") or claims.get("last_name")),
        "image_url": _safe_str(claims.get("picture") or claims.get("image_url")),
        "plan_tier": infer_plan_tier(billing_features),
        "billing_features": billing_features,
        "is_active": True,
        "metadata": metadata,
    }
    profile, created = Profile.objects.get_or_create(
        clerk_user_id=clerk_user_id,
        defaults=defaults,
    )

    if not created:
        changed_fields: list[str] = []
        for field_name, field_value in defaults.items():
            if getattr(profile, field_name) != field_value:
                setattr(profile, field_name, field_value)
                changed_fields.append(field_name)
        if changed_fields:
            profile.save(update_fields=[*changed_fields, "updated_at"])

    return profile


def get_request_claims(request) -> dict[str, Any]:
    claims = getattr(request, "clerk_claims", request.auth or {})
    return claims if isinstance(claims, dict) else {}


def get_request_profile(request) -> Profile:
    cached_profile = getattr(request, "_cached_profile", None)
    if cached_profile is not None:
        return cached_profile

    profile = sync_profile_from_claims(get_request_claims(request))
    if profile is None:
        raise ValidationError("Missing Clerk identity in token claims.")

    request._cached_profile = profile
    return profile


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

        return Response(
            {
                "clerk_user_id": claims.get("sub"),
                "email": claims.get("email"),
                "org_id": claims.get("org_id"),
                "billing_features": billing_features,
                "profile": ProfileSerializer(profile).data if profile else None,
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


class SupabaseProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = get_request_claims(request)
        clerk_user_id = claims.get("sub")
        if not clerk_user_id:
            return Response({"detail": "Missing Clerk user id in token claims."}, status=400)

        try:
            supabase = get_supabase_client(access_token=getattr(request, "clerk_token", None))
            result = (
                supabase.table("profiles")
                .select("*")
                .eq("clerk_user_id", clerk_user_id)
                .limit(1)
                .execute()
            )
        except SupabaseConfigurationError as exc:
            return Response({"detail": str(exc)}, status=500)
        except Exception as exc:  # pragma: no cover
            return Response(
                {
                    "detail": "Supabase query failed. Confirm table and RLS setup.",
                    "error": str(exc),
                },
                status=502,
            )

        data = getattr(result, "data", None)
        profile = data[0] if isinstance(data, list) and data else data
        return Response({"profile": profile})


class ClerkUserView(APIView):
    """Look up the authenticated user's full Clerk profile.

    This fetches the complete user object from Clerk's Backend API,
    which includes metadata, email addresses, profile images, and more
    — richer than the JWT claims alone.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = get_request_claims(request)
        clerk_user_id = claims.get("sub")
        if not clerk_user_id:
            return Response(
                {"detail": "Missing Clerk user id in token claims."}, status=400
            )

        try:
            from .clerk_client import ClerkClientError, get_clerk_user

            user = get_clerk_user(clerk_user_id)
        except ClerkClientError as exc:
            return Response({"detail": str(exc)}, status=500)
        except Exception as exc:
            return Response(
                {"detail": "Clerk API call failed.", "error": str(exc)},
                status=502,
            )

        # Serialize the relevant fields from the Clerk user object.
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
                "private_metadata": getattr(user, "private_metadata", {}),
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
