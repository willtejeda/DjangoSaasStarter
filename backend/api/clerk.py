from __future__ import annotations

import ipaddress
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed


class ClerkConfigurationError(RuntimeError):
    pass


def _effective_port(scheme: str, port: int | None) -> int | None:
    if port is not None:
        return port
    if scheme == "https":
        return 443
    if scheme == "http":
        return 80
    return None


def _parse_origin(value: str) -> tuple[str, str, int | None, str] | None:
    raw = str(value or "").strip()
    if not raw:
        return None

    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.hostname:
        return None

    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower()
    port = _effective_port(scheme, parsed.port)
    path = (parsed.path or "").rstrip("/")
    return scheme, host, port, path


def _is_loopback_host(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def authorized_party_matches(azp: str | None, allowed_parties: list[str]) -> bool:
    if not azp:
        return False

    parsed_azp = _parse_origin(azp)
    normalized_azp = azp.rstrip("/").lower()

    for allowed in allowed_parties:
        if not allowed:
            continue

        normalized_allowed = allowed.rstrip("/").lower()
        if normalized_azp == normalized_allowed:
            return True

        parsed_allowed = _parse_origin(allowed)
        if not parsed_azp or not parsed_allowed:
            continue

        if parsed_azp == parsed_allowed:
            return True

        azp_scheme, azp_host, azp_port, azp_path = parsed_azp
        allowed_scheme, allowed_host, allowed_port, allowed_path = parsed_allowed

        # Local development often alternates localhost and 127.0.0.1.
        # Treat loopback aliases as equivalent only when scheme/port/path match.
        if (
            azp_scheme == allowed_scheme
            and azp_port == allowed_port
            and azp_path == allowed_path
            and _is_loopback_host(azp_host)
            and _is_loopback_host(allowed_host)
        ):
            return True

    return False


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
        if not authorized_party_matches(azp, authorized_parties):
            raise AuthenticationFailed(
                "Token authorized party is not allowed. "
                "Add your frontend origin to CLERK_AUTHORIZED_PARTIES."
            )

    return payload
