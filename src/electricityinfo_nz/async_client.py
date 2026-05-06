from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import aiohttp

from .async_auth import AsyncOAuth2ClientCredentials
from .client import DEFAULT_BASE_URL
from .constants import DEFAULT_TIMEOUT
from .endpoints.async_nodes import list_nodes
from .endpoints.async_prices import get_prices, get_schedule_prices
from .endpoints.async_schedules import list_schedules
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

T = TypeVar("T")


class AsyncMarketPricesClient:
    """
    Async client for the WITS Market Prices API.

    Accepts an optional ``aiohttp.ClientSession`` so callers (e.g. Home Assistant integrations)
    can supply their own managed session.  When no session is provided the client creates and
    owns one; it is closed when the client is used as an async context manager or when
    :meth:`close` is called.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        session: aiohttp.ClientSession | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._owns_session = session is None
        self.session = session or aiohttp.ClientSession()
        self.timeout = timeout
        self.client_id = client_id or os.getenv("WITS_CLIENT_ID") or ""
        self.client_secret = client_secret or os.getenv("WITS_CLIENT_SECRET") or ""
        if not self.client_id or not self.client_secret:
            raise AuthenticationError("client_id and client_secret are required")
        if timeout <= 0:
            raise ValidationError("timeout must be greater than 0")
        self.auth = AsyncOAuth2ClientCredentials(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url=self.base_url.split("/api/market-prices/v1")[0],
            session=self.session,
            timeout=self.timeout,
        )

    async def _authorized_headers(self) -> dict[str, str]:
        token = await self.auth.get_token()
        return {"Authorization": f"Bearer {token}"}

    async def _wrap(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except aiohttp.ClientResponseError as exc:  # pragma: no cover - thin mapping
            status = exc.status
            message = str(exc)
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
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise TransportError(f"Request failed: {exc}") from exc

    async def close(self) -> None:
        """Close the underlying HTTP session if it was created by this client."""
        if self._owns_session:
            await self.session.close()

    async def __aenter__(self) -> AsyncMarketPricesClient:
        """Enter the async context manager."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit the async context manager and close the session if owned."""
        await self.close()

    async def get_schedules(self) -> list[Schedule]:
        """Return the schedules currently exposed by the API."""
        return await self._wrap(
            list_schedules,
            self.session,
            self.base_url,
            headers=await self._authorized_headers(),
            timeout=self.timeout,
        )

    async def get_nodes(self) -> list[NodeInfo]:
        """Return supported market nodes."""
        return await self._wrap(
            list_nodes,
            self.session,
            self.base_url,
            headers=await self._authorized_headers(),
            timeout=self.timeout,
        )

    async def get_schedule_prices(
        self,
        schedule: str,
        market_type: str,
        nodes: list[str] | None = None,
        from_datetime: str | None = None,
        to_datetime: str | None = None,
        back: int | None = None,
        forward: int | None = None,
        island: str | None = None,
        offset: int | None = None,
    ) -> ScheduleDetails:
        """Return prices for a single schedule."""
        return await self._wrap(
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
            headers=await self._authorized_headers(),
            timeout=self.timeout,
        )

    async def get_prices(
        self,
        schedules: list[str],
        market_type: str,
        nodes: list[str] | None = None,
        from_datetime: str | None = None,
        to_datetime: str | None = None,
        back: int | None = None,
        forward: int | None = None,
        island: str | None = None,
        offset: int | None = None,
    ) -> list[ScheduleDetails]:
        """Return prices across one or more schedules."""
        return await self._wrap(
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
            headers=await self._authorized_headers(),
            timeout=self.timeout,
        )
