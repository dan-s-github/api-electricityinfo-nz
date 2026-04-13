import os
from collections.abc import Callable
from typing import Any, Optional, TypeVar

import requests

from .auth import OAuth2ClientCredentials
from .constants import DEFAULT_TIMEOUT
from .endpoints.nodes import list_nodes
from .endpoints.prices import get_prices, get_schedule_prices
from .endpoints.schedules import list_schedules
from .exceptions import (
    AuthenticationError,
    MarketPricesAPIError,
    NotFoundError,
    RateLimitError,
    ResponseFormatError,
    TransportError,
    ValidationError,
)
from .models import NodeInfo, Schedule, ScheduleDetails

DEFAULT_BASE_URL = "https://api.electricityinfo.co.nz/api/market-prices/v1"
T = TypeVar("T")


class MarketPricesClient:
    """Client for the WITS Market Prices API."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        session: Optional[requests.Session] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout
        self.client_id = client_id or os.getenv("WITS_CLIENT_ID") or ""
        self.client_secret = client_secret or os.getenv("WITS_CLIENT_SECRET") or ""
        if not self.client_id or not self.client_secret:
            raise AuthenticationError("client_id and client_secret are required")
        if timeout <= 0:
            raise ValidationError("timeout must be greater than 0")
        self.auth = OAuth2ClientCredentials(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url=self.base_url.split("/api/market-prices/v1")[0],
            session=self.session,
            timeout=self.timeout,
        )

    def _authorized_headers(self) -> dict[str, str]:
        token = self.auth.get_token()
        return {"Authorization": f"Bearer {token}"}

    def _response_message(self, response: requests.Response | Any, fallback: str) -> str:
        try:
            payload = response.json()
        except ValueError:
            return fallback

        if not isinstance(payload, dict):
            return fallback

        message = payload.get("message")
        detail = payload.get("detail")
        code = payload.get("code")
        if not isinstance(message, str) or not message:
            return fallback

        parts = [message]
        if isinstance(detail, str) and detail:
            parts.append(detail)
        if isinstance(code, str) and code:
            parts.append(f"[{code}]")
        return " ".join(parts)

    def _wrap(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except requests.HTTPError as exc:  # pragma: no cover - thin mapping
            status = exc.response.status_code if exc.response else 0
            message = self._response_message(exc.response, str(exc)) if exc.response else str(exc)
            if status in (401, 403):
                raise AuthenticationError(message) from exc
            if status == 404:
                raise NotFoundError(message) from exc
            if status == 400:
                raise ValidationError(message) from exc
            if status == 429:
                raise RateLimitError(message) from exc
            raise MarketPricesAPIError(message) from exc
        except ResponseFormatError:
            raise
        except requests.RequestException as exc:
            raise TransportError(f"Request failed: {exc}") from exc

    def get_schedules(self) -> list[Schedule]:
        """Return the schedules currently exposed by the API."""
        return self._wrap(
            list_schedules,
            self.session,
            self.base_url,
            headers=self._authorized_headers(),
            timeout=self.timeout,
        )

    def get_nodes(self) -> list[NodeInfo]:
        """Return supported market nodes."""
        return self._wrap(
            list_nodes,
            self.session,
            self.base_url,
            headers=self._authorized_headers(),
            timeout=self.timeout,
        )

    def get_schedule_prices(
        self,
        schedule: str,
        market_type: str,
        nodes: Optional[list[str]] = None,
        from_datetime: Optional[str] = None,
        to_datetime: Optional[str] = None,
        back: Optional[int] = None,
        forward: Optional[int] = None,
        island: Optional[str] = None,
        offset: Optional[int] = None,
    ) -> ScheduleDetails:
        """Return prices for a single schedule."""
        return self._wrap(
            get_schedule_prices,
            self.session,
            self.base_url,
            schedule,
            market_type,
            nodes,
            from_datetime,
            to_datetime,
            back,
            forward,
            island,
            offset,
            headers=self._authorized_headers(),
            timeout=self.timeout,
        )

    def get_prices(
        self,
        schedules: list[str],
        market_type: str,
        nodes: Optional[list[str]] = None,
        from_datetime: Optional[str] = None,
        to_datetime: Optional[str] = None,
        back: Optional[int] = None,
        forward: Optional[int] = None,
        island: Optional[str] = None,
        offset: Optional[int] = None,
    ) -> list[ScheduleDetails]:
        """Return prices across one or more schedules."""
        return self._wrap(
            get_prices,
            self.session,
            self.base_url,
            schedules,
            market_type,
            nodes,
            from_datetime,
            to_datetime,
            back,
            forward,
            island,
            offset,
            headers=self._authorized_headers(),
            timeout=self.timeout,
        )
