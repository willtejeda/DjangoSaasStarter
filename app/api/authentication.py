from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rest_framework.authentication import BaseAuthentication, get_authorization_header
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
    def username(self) -> str:
        return self.clerk_user_id


class ClerkJWTAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        token = self._extract_token(request)
        if token is None:
            return None

        try:
            claims = decode_clerk_token(token)
        except ClerkConfigurationError as exc:
            raise AuthenticationFailed(str(exc)) from exc

        request.clerk_token = token
        request.clerk_claims = claims
        return ClerkPrincipal(clerk_user_id=claims["sub"], claims=claims), claims

    def _extract_token(self, request) -> str | None:
        auth = get_authorization_header(request).split()
        if auth:
            keyword = auth[0].decode("utf-8").lower()
            if keyword != self.keyword.lower():
                return None
            if len(auth) == 1:
                raise AuthenticationFailed("Invalid Authorization header: missing token.")
            if len(auth) > 2:
                raise AuthenticationFailed("Invalid Authorization header: token has spaces.")
            return auth[1].decode("utf-8")

        cookie_token = request.COOKIES.get("__session")
        if cookie_token:
            return cookie_token

        return None
