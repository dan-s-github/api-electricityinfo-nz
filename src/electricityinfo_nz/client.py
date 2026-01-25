import os
from typing import List, Optional
import requests

from .auth import OAuth2ClientCredentials
from .endpoints.nodes import list_nodes
from .endpoints.prices import get_prices, get_schedule_prices
from .endpoints.schedules import list_schedules
from .exceptions import AuthenticationError, MarketPricesAPIError, NotFoundError, RateLimitError, ValidationError
from .models import Schedule, ScheduleDetails

DEFAULT_BASE_URL = "https://api.electricityinfo.co.nz/api/market-prices/v1"


class MarketPricesClient:
    """Client for the WITS Market Prices API."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.client_id = client_id or os.getenv("WITS_CLIENT_ID") or ""
        self.client_secret = client_secret or os.getenv("WITS_CLIENT_SECRET") or ""
        if not self.client_id or not self.client_secret:
            raise AuthenticationError("client_id and client_secret are required")
        self.auth = OAuth2ClientCredentials(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url=self.base_url.split("/api/market-prices/v1")[0],
        )

    def _authorized_session(self) -> requests.Session:
        token = self.auth.get_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        return self.session

    def _wrap(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.HTTPError as exc:  # pragma: no cover - thin mapping
            status = exc.response.status_code if exc.response else 0
            if status in (401, 403):
                raise AuthenticationError(str(exc)) from exc
            if status == 404:
                raise NotFoundError(str(exc)) from exc
            if status == 400:
                raise ValidationError(str(exc)) from exc
            if status == 429:
                raise RateLimitError(str(exc)) from exc
            raise MarketPricesAPIError(str(exc)) from exc

    def get_schedules(self) -> List[Schedule]:
        session = self._authorized_session()
        return self._wrap(list_schedules, session, self.base_url)

    def get_nodes(self) -> List[str]:
        session = self._authorized_session()
        return self._wrap(list_nodes, session, self.base_url)

    def get_schedule_prices(
        self,
        schedule: str,
        market_type: str,
        nodes: Optional[List[str]] = None,
        from_datetime: Optional[str] = None,
        to_datetime: Optional[str] = None,
        back: Optional[int] = None,
        forward: Optional[int] = None,
        island: Optional[str] = None,
        offset: Optional[int] = None,
    ) -> ScheduleDetails:
        session = self._authorized_session()
        return self._wrap(
            get_schedule_prices,
            session,
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
        )

    def get_prices(
        self,
        schedules: List[str],
        market_type: str,
        nodes: Optional[List[str]] = None,
        from_datetime: Optional[str] = None,
        to_datetime: Optional[str] = None,
        back: Optional[int] = None,
        forward: Optional[int] = None,
        island: Optional[str] = None,
        offset: Optional[int] = None,
    ) -> List[ScheduleDetails]:
        session = self._authorized_session()
        return self._wrap(
            get_prices,
            session,
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
        )
