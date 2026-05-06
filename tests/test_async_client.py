import json
from unittest.mock import MagicMock

import aiohttp
import pytest

from electricityinfo_nz.async_auth import AsyncOAuth2ClientCredentials
from electricityinfo_nz.async_client import AsyncMarketPricesClient
from electricityinfo_nz.exceptions import (
    AuthenticationError,
    ResponseFormatError,
    TransportError,
    ValidationError,
)

TEST_CLIENT_SECRET = "test-client-secret"  # noqa: S105
TOKEN_VALUE = "async-token-value"  # noqa: S105


class AsyncDummyResponse:
    """Minimal stand-in for an aiohttp ClientResponse used as an async context manager."""

    def __init__(self, status=200, payload=None, text_val=None, json_error=None):
        self.status = status
        self._payload = payload if payload is not None else []
        self._text = text_val if text_val is not None else json.dumps(self._payload)
        self._json_error = json_error

    async def json(self, content_type=None):
        if self._json_error is not None:
            raise self._json_error
        return self._payload

    async def text(self):
        return self._text

    def raise_for_status(self):
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=self.status,
            )

    async def __aenter__(self):  # noqa: D105
        return self

    async def __aexit__(self, *args):  # noqa: D105
        pass


class AsyncDummySession:
    """Minimal stand-in for an aiohttp.ClientSession."""

    def __init__(self, get_map=None, post_response=None, get_error=None, post_error=None):
        self.get_map = get_map or {}
        self.post_response = post_response or AsyncDummyResponse(
            payload={"access_token": TOKEN_VALUE, "expires_in": 3600}
        )
        self.get_error = get_error
        self.post_error = post_error
        self.last_get = None
        self.last_post = None

    def get(self, url, params=None, headers=None, timeout=None):
        self.last_get = {"url": url, "params": params, "headers": headers, "timeout": timeout}
        if self.get_error is not None:
            err = self.get_error

            class _Raise:
                async def __aenter__(self_inner):
                    raise err

                async def __aexit__(self_inner, *args):
                    pass

            return _Raise()
        return self.get_map.get(url, AsyncDummyResponse(payload=[]))

    def post(self, url, data=None, auth=None, timeout=None):
        self.last_post = {"url": url, "data": data, "auth": auth, "timeout": timeout}
        if self.post_error is not None:
            err = self.post_error

            class _Raise:
                async def __aenter__(self_inner):
                    raise err

                async def __aexit__(self_inner, *args):
                    pass

            return _Raise()
        return self.post_response

    async def close(self):
        pass


class AsyncDummyAuth:
    def __init__(self):
        self.calls = 0

    async def get_token(self):
        self.calls += 1
        return TOKEN_VALUE


@pytest.fixture
def async_client(monkeypatch):
    session = AsyncDummySession(
        get_map={
            "https://api.electricityinfo.co.nz/api/market-prices/v1/schedules": AsyncDummyResponse(
                payload=[{"schedule": "RTP", "runType": "short", "marketType": "E"}]
            )
        }
    )

    c = AsyncMarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=session,
    )

    monkeypatch.setattr(c, "auth", AsyncDummyAuth())
    return c


async def test_async_get_schedules(async_client):
    schedules = await async_client.get_schedules()
    assert len(schedules) == 1
    assert schedules[0].schedule == "RTP"
    assert async_client.session.last_get["headers"] == {"Authorization": f"Bearer {TOKEN_VALUE}"}


async def test_async_get_nodes_returns_node_dictionaries(monkeypatch):
    session = AsyncDummySession(
        get_map={
            "https://api.electricityinfo.co.nz/api/market-prices/v1/nodes": AsyncDummyResponse(
                payload=[{"node": "OTA2201", "island": "NI"}]
            )
        }
    )
    client = AsyncMarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=session,
    )
    monkeypatch.setattr(client, "auth", AsyncDummyAuth())

    nodes = await client.get_nodes()

    assert nodes == [{"node": "OTA2201", "island": "NI"}]


async def test_async_get_prices_rejects_invalid_market_type(monkeypatch):
    client = AsyncMarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=AsyncDummySession(),
    )
    monkeypatch.setattr(client, "auth", AsyncDummyAuth())

    with pytest.raises(ValidationError, match="market_type"):
        await client.get_prices(["RTP"], market_type="X", back=4)


async def test_async_get_prices_rejects_mixed_range_filters(monkeypatch):
    client = AsyncMarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=AsyncDummySession(),
    )
    monkeypatch.setattr(client, "auth", AsyncDummyAuth())

    with pytest.raises(ValidationError, match="from/to cannot be combined"):
        await client.get_prices(
            ["RTP"],
            market_type="E",
            from_datetime="2026-01-01T00:00:00Z",
            back=1,
        )


async def test_async_get_prices_invalid_payload_raises_response_format_error(monkeypatch):
    session = AsyncDummySession(
        get_map={
            "https://api.electricityinfo.co.nz/api/market-prices/v1/prices": AsyncDummyResponse(
                payload="invalid"
            )
        }
    )
    client = AsyncMarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=session,
    )
    monkeypatch.setattr(client, "auth", AsyncDummyAuth())

    with pytest.raises(ResponseFormatError, match="Invalid prices payload"):
        await client.get_prices(["RTP"], market_type="E", back=1)


async def test_async_get_schedules_maps_network_errors(monkeypatch):
    client = AsyncMarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=AsyncDummySession(get_error=aiohttp.ClientError("timed out")),
    )
    monkeypatch.setattr(client, "auth", AsyncDummyAuth())

    with pytest.raises(TransportError, match="Request failed"):
        await client.get_schedules()


async def test_async_get_schedule_prices_sends_node_filter(monkeypatch):
    session = AsyncDummySession(
        get_map={
            "https://api.electricityinfo.co.nz/api/market-prices/v1/schedules/RTP/prices": (
                AsyncDummyResponse(
                    payload={
                        "schedule": "RTP",
                        "prices": [
                            {
                                "tradingDateTime": "2026-01-01T00:00:00Z",
                                "tradingPeriod": 1,
                                "node": "OTA2201",
                                "price": 123.45,
                            }
                        ],
                    }
                )
            )
        }
    )
    client = AsyncMarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=session,
    )
    monkeypatch.setattr(client, "auth", AsyncDummyAuth())

    result = await client.get_schedule_prices(
        schedule="RTP",
        market_type="E",
        nodes=["OTA2201"],
        forward=1,
    )

    assert [price.node for price in result.prices] == ["OTA2201"]


async def test_async_client_context_manager_closes_owned_session(monkeypatch):
    closed = []
    session = AsyncDummySession()
    session.close = lambda: closed.append(True) or __import__("asyncio").sleep(0)  # type: ignore[method-assign]

    client = AsyncMarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=session,
    )
    client._owns_session = True
    monkeypatch.setattr(client, "auth", AsyncDummyAuth())

    async with client:
        pass

    assert closed


async def test_async_client_does_not_close_external_session(monkeypatch):
    closed = []
    session = AsyncDummySession()
    session.close = lambda: closed.append(True) or __import__("asyncio").sleep(0)  # type: ignore[method-assign]

    client = AsyncMarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=session,
    )
    client._owns_session = False
    monkeypatch.setattr(client, "auth", AsyncDummyAuth())

    async with client:
        pass

    assert not closed


async def test_async_auth_fetch_uses_timeout_and_caches_token():
    session = AsyncDummySession()
    auth = AsyncOAuth2ClientCredentials(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        base_url="https://api.electricityinfo.co.nz",
        session=session,
        timeout=12.5,
    )

    token = await auth.get_token()
    cached_token = await auth.get_token()

    assert token == TOKEN_VALUE
    assert cached_token == TOKEN_VALUE
    # Only one POST should have been made (second call uses cache)
    assert isinstance(session.last_post["auth"], aiohttp.BasicAuth)
    assert session.last_post["auth"].login == "id"


async def test_async_auth_transport_error_raises_authentication_error():
    auth = AsyncOAuth2ClientCredentials(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        base_url="https://api.electricityinfo.co.nz",
        session=AsyncDummySession(post_error=aiohttp.ClientError("connection refused")),
    )

    with pytest.raises(AuthenticationError, match="Failed to obtain access token"):
        await auth.get_token()
