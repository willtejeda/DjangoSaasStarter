from __future__ import annotations

from functools import lru_cache
from typing import Any

from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed


class ClerkConfigurationError(RuntimeError):
    pass


def _get_required_setting(name: str) -> str:
    value = getattr(settings, name, "")
    if not value:
        raise ClerkConfigurationError(f"{name} is not configured.")
    return value


@lru_cache(maxsize=2)
def _build_jwks_client(jwks_url: str):
    jwt_lib = _get_jwt_library()
    return jwt_lib.PyJWKClient(jwks_url)


def _get_jwt_library():
    try:
        import jwt

        return jwt
    except Exception as exc:
        raise ClerkConfigurationError(
            "PyJWT with crypto backend is required for Clerk token verification."
        ) from exc


def decode_clerk_token(token: str) -> dict[str, Any]:
    jwt_lib = _get_jwt_library()
    jwks_url = _get_required_setting("CLERK_JWKS_URL")
    issuer = getattr(settings, "CLERK_JWT_ISSUER", "") or None
    audience = getattr(settings, "CLERK_JWT_AUDIENCE", "") or None
    authorized_parties = [
        party for party in getattr(settings, "CLERK_AUTHORIZED_PARTIES", []) if party
    ]

    try:
        signing_key = _build_jwks_client(jwks_url).get_signing_key_from_jwt(token)
        payload = jwt_lib.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "EdDSA"],
            issuer=issuer,
            audience=audience,
            options={
                "verify_aud": bool(audience),
                "verify_iss": bool(issuer),
            },
        )
    except jwt_lib.InvalidTokenError as exc:
        raise AuthenticationFailed("Invalid Clerk token.") from exc

    if not payload.get("sub"):
        raise AuthenticationFailed("Token is missing sub claim.")

    if authorized_parties:
        azp = payload.get("azp")
        if azp not in authorized_parties:
            raise AuthenticationFailed("Token authorized party is not allowed.")

    return payload
