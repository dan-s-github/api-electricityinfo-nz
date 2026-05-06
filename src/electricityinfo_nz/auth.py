import time
from dataclasses import dataclass, field

import requests

from .constants import DEFAULT_TIMEOUT
from .exceptions import AuthenticationError

DEFAULT_TOKEN_PATH = "/login/oauth2/token"  # noqa: S105


@dataclass
class OAuth2ClientCredentials:
    """Fetch and cache OAuth2 client-credentials access tokens."""

    client_id: str
    client_secret: str
    base_url: str
    token_path: str = DEFAULT_TOKEN_PATH
    session: requests.Session = field(default_factory=requests.Session)
    timeout: float = DEFAULT_TIMEOUT

    _access_token: str | None = None
    _expires_at: float = 0.0

    def _token_url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.token_path}"

    def _is_valid(self) -> bool:
        # Pad by 30 seconds to avoid using an about-to-expire token.
        return bool(self._access_token) and time.time() < self._expires_at - 30

    def get_token(self) -> str:
        """Return a cached access token or fetch a new one."""
        if self._is_valid():
            return self._access_token or ""

        try:
            response = self.session.post(
                self._token_url(),
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise AuthenticationError(f"Failed to obtain access token: {exc}") from exc

        if response.status_code != 200:
            raise AuthenticationError(
                f"Failed to obtain access token (status {response.status_code}): {response.text}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise AuthenticationError("Token endpoint returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise AuthenticationError("Token endpoint returned an unexpected payload")

        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in", 0)

        if not isinstance(access_token, str) or not access_token:
            raise AuthenticationError("Token endpoint did not return an access_token")

        self._access_token = access_token
        try:
            self._expires_at = time.time() + float(expires_in or 0)
        except (TypeError, ValueError) as exc:
            raise AuthenticationError(
                "Token endpoint returned an invalid expires_in value"
            ) from exc
        return self._access_token
