import time
from dataclasses import dataclass
from typing import Optional
import requests

from .exceptions import AuthenticationError


DEFAULT_TOKEN_PATH = "/login/oauth2/token"


@dataclass
class OAuth2ClientCredentials:
    client_id: str
    client_secret: str
    base_url: str
    token_path: str = DEFAULT_TOKEN_PATH

    _access_token: Optional[str] = None
    _expires_at: float = 0.0

    def _token_url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.token_path}"

    def _is_valid(self) -> bool:
        # Pad by 30 seconds to avoid using an about-to-expire token.
        return bool(self._access_token) and time.time() < self._expires_at - 30

    def get_token(self) -> str:
        if self._is_valid():
            return self._access_token or ""

        response = requests.post(
            self._token_url(),
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
        )

        if response.status_code != 200:
            raise AuthenticationError(
                f"Failed to obtain access token (status {response.status_code}): {response.text}"
            )

        payload = response.json()
        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in", 0)

        if not access_token:
            raise AuthenticationError("Token endpoint did not return an access_token")

        self._access_token = access_token
        self._expires_at = time.time() + float(expires_in or 0)
        return self._access_token
