from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, CSRFCheck, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .clerk import ClerkConfigurationError, decode_clerk_token


@dataclass(frozen=True)
class ClerkPrincipal:
    clerk_user_id: str
    claims: dict[str, Any]

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    @property
    def id(self) -> str:
        return self.clerk_user_id

    @property
    def pk(self) -> str:
        return self.clerk_user_id

    @property
    def username(self) -> str:
        return self.clerk_user_id


class ClerkJWTAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        token, source = self._extract_token(request)
        if token is None:
            return None

        if source == "cookie":
            self._enforce_csrf(request)

        try:
            claims = decode_clerk_token(token)
        except ClerkConfigurationError as exc:
            raise AuthenticationFailed(str(exc)) from exc

        request.clerk_token = token
        request.clerk_claims = claims
        return ClerkPrincipal(clerk_user_id=claims["sub"], claims=claims), claims

    def _extract_token(self, request) -> tuple[str | None, str | None]:
        auth = get_authorization_header(request).split()
        if auth:
            keyword = auth[0].decode("utf-8").lower()
            if keyword != self.keyword.lower():
                return None, None
            if len(auth) == 1:
                raise AuthenticationFailed("Invalid Authorization header: missing token.")
            if len(auth) > 2:
                raise AuthenticationFailed("Invalid Authorization header: token has spaces.")
            return auth[1].decode("utf-8"), "header"

        cookie_token = request.COOKIES.get("__session")
        if cookie_token:
            return cookie_token, "cookie"

        return None, None

    def _enforce_csrf(self, request) -> None:
        def dummy_get_response(_request):  # pragma: no cover
            return None

        check = CSRFCheck(dummy_get_response)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")
