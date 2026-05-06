import time
from dataclasses import dataclass, field

import aiohttp

from .constants import DEFAULT_TIMEOUT
from .exceptions import AuthenticationError

DEFAULT_TOKEN_PATH = "/login/oauth2/token"  # noqa: S105


@dataclass
class AsyncOAuth2ClientCredentials:
    """Fetch and cache OAuth2 client-credentials access tokens asynchronously."""

    client_id: str
    client_secret: str
    base_url: str
    token_path: str = DEFAULT_TOKEN_PATH
    session: aiohttp.ClientSession = field(default_factory=aiohttp.ClientSession)
    timeout: float = DEFAULT_TIMEOUT

    _access_token: str | None = None
    _expires_at: float = 0.0

    def _token_url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.token_path}"

    def _is_valid(self) -> bool:
        # Pad by 30 seconds to avoid using an about-to-expire token.
        return bool(self._access_token) and time.time() < self._expires_at - 30

    async def get_token(self) -> str:
        """Return a cached access token or fetch a new one."""
        if self._is_valid():
            return self._access_token or ""

        aio_timeout = aiohttp.ClientTimeout(total=self.timeout)
        try:
            async with self.session.post(
                self._token_url(),
                data={"grant_type": "client_credentials"},
                auth=aiohttp.BasicAuth(self.client_id, self.client_secret),
                timeout=aio_timeout,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise AuthenticationError(
                        f"Failed to obtain access token (status {resp.status}): {text}"
                    )

                try:
                    payload = await resp.json(content_type=None)
                except ValueError as exc:
                    raise AuthenticationError("Token endpoint returned invalid JSON") from exc
        except AuthenticationError:
            raise
        except aiohttp.ClientError as exc:
            raise AuthenticationError(f"Failed to obtain access token: {exc}") from exc

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
