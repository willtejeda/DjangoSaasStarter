from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .supabase_client import SupabaseConfigurationError, get_supabase_client


def extract_billing_features(claims: dict[str, Any]) -> list[str]:
    claim_name = getattr(settings, "CLERK_BILLING_CLAIM", "entitlements")
    value = claims.get(claim_name)

    if isinstance(value, list):
        return [str(item) for item in value if item]

    if isinstance(value, dict):
        return [str(feature) for feature, enabled in value.items() if enabled]

    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]

    return []


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
        claims = getattr(request, "clerk_claims", request.auth or {})
        billing_features = extract_billing_features(claims)

        return Response(
            {
                "clerk_user_id": claims.get("sub"),
                "email": claims.get("email"),
                "org_id": claims.get("org_id"),
                "billing_features": billing_features,
            }
        )


class BillingFeatureView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = getattr(request, "clerk_claims", request.auth or {})
        enabled_features = set(extract_billing_features(claims))
        requested_feature = request.query_params.get("feature")

        if requested_feature:
            return Response(
                {
                    "feature": requested_feature,
                    "enabled": requested_feature in enabled_features,
                }
            )

        return Response({"enabled_features": sorted(enabled_features)})


class SupabaseProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = getattr(request, "clerk_claims", request.auth or {})
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
        claims = getattr(request, "clerk_claims", request.auth or {})
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

