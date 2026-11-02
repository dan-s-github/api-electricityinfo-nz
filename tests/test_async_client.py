import json
from unittest.mock import MagicMock

import aiohttp
import pytest

from electricityinfo_nz import async_client as async_client_module
from electricityinfo_nz.async_auth import AsyncOAuth2ClientCredentials
from electricityinfo_nz.async_client import AsyncMarketPricesClient
from electricityinfo_nz.endpoints.async_nodes import list_nodes
from electricityinfo_nz.endpoints.async_prices import get_prices, get_schedule_prices
from electricityinfo_nz.endpoints.async_schedules import list_schedules
from electricityinfo_nz.exceptions import (
    AuthenticationError,
    MarketPricesAPIError,
    NotFoundError,
    RateLimitError,
    ResponseFormatError,
    TransportError,
    ValidationError,
)

TEST_CLIENT_SECRET = "test-client-secret"  # noqa: S105
TOKEN_VALUE = "async-token-value"  # noqa: S105
BASE_URL = "https://api.electricityinfo.co.nz/api/market-prices/v1"


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


async def test_async_get_schedules_maps_json_decode_error(monkeypatch):
    session = AsyncDummySession(
        get_map={
            "https://api.electricityinfo.co.nz/api/market-prices/v1/schedules": AsyncDummyResponse(
                json_error=ValueError("No JSON object could be decoded")
            )
        }
    )
    client = AsyncMarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=session,
    )
    monkeypatch.setattr(client, "auth", AsyncDummyAuth())

    with pytest.raises(ResponseFormatError, match="Invalid JSON"):
        await client.get_schedules()


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


def _session_returning(path, response):
    return AsyncDummySession(get_map={f"{BASE_URL}{path}": response})


def test_async_client_requires_credentials(monkeypatch):
    monkeypatch.delenv("WITS_CLIENT_ID", raising=False)
    monkeypatch.delenv("WITS_CLIENT_SECRET", raising=False)

    with pytest.raises(AuthenticationError, match="client_id and client_secret"):
        AsyncMarketPricesClient()


def test_async_client_rejects_non_positive_timeout():
    with pytest.raises(ValidationError, match="timeout"):
        AsyncMarketPricesClient(client_id="id", client_secret=TEST_CLIENT_SECRET, timeout=-1)


async def test_async_client_creates_and_closes_owned_session(monkeypatch):
    created = []

    class TrackingSession(AsyncDummySession):
        def __init__(self):
            super().__init__(
                get_map={f"{BASE_URL}/schedules": AsyncDummyResponse(payload=[{"schedule": "RTP"}])}
            )
            self.closed = False
            created.append(self)

        async def close(self):
            self.closed = True

    monkeypatch.setattr(async_client_module.aiohttp, "ClientSession", TrackingSession)

    async with AsyncMarketPricesClient(client_id="id", client_secret=TEST_CLIENT_SECRET) as client:
        assert client.session is None
        assert client.auth is None
        schedules = await client.get_schedules()

    assert [s.schedule for s in schedules] == ["RTP"]
    assert len(created) == 1
    assert created[0].closed
    assert created[0].last_get["headers"] == {"Authorization": f"Bearer {TOKEN_VALUE}"}
    assert created[0].last_post["url"] == "https://api.electricityinfo.co.nz/login/oauth2/token"


async def test_async_client_close_without_session_is_noop():
    client = AsyncMarketPricesClient(client_id="id", client_secret=TEST_CLIENT_SECRET)

    await client.close()

    assert client.session is None


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, AuthenticationError),
        (403, AuthenticationError),
        (404, NotFoundError),
        (400, ValidationError),
        (429, RateLimitError),
        (500, MarketPricesAPIError),
    ],
)
async def test_async_wrap_maps_http_status_to_exception(monkeypatch, status, expected):
    client = AsyncMarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=_session_returning("/nodes", AsyncDummyResponse(status=status)),
    )
    monkeypatch.setattr(client, "auth", AsyncDummyAuth())

    with pytest.raises(expected) as exc_info:
        await client.get_nodes()

    assert type(exc_info.value) is expected


async def test_async_get_prices_accepts_list_payload_and_sends_all_filters(monkeypatch):
    session = _session_returning(
        "/prices",
        AsyncDummyResponse(
            payload=[
                {
                    "schedule": "RTP",
                    "prices": [
                        {
                            "tradingDateTime": "2026-01-01T00:00:00Z",
                            "tradingPeriod": 1,
                            "node": "OTA2201",
                        }
                    ],
                }
            ]
        ),
    )
    client = AsyncMarketPricesClient(
        client_id="id", client_secret=TEST_CLIENT_SECRET, session=session
    )
    monkeypatch.setattr(client, "auth", AsyncDummyAuth())

    result = await client.get_prices(
        ["RTP", "PRSS"],
        market_type="R",
        nodes=["OTA2201"],
        from_datetime="2026-01-01T00:00:00Z",
        to_datetime="2026-01-02T00:00:00Z",
        island="NI",
        offset=5,
    )

    assert session.last_get["params"] == {
        "schedules": "RTP,PRSS",
        "marketType": "R",
        "nodes": "OTA2201",
        "from": "2026-01-01T00:00:00Z",
        "to": "2026-01-02T00:00:00Z",
        "island": "NI",
        "offset": 5,
    }
    assert result[0].prices[0].node == "OTA2201"


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"island": "XX"}, "island"),
        ({"back": 49}, "back"),
        ({"forward": 0}, "forward"),
        ({"offset": -1}, "offset"),
        ({"from_datetime": "not-a-date"}, "'from' datetime"),
        ({"to_datetime": "not-a-date"}, "'to' datetime"),
        ({"nodes": [""]}, "nodes"),
    ],
)
async def test_async_price_filter_validation(kwargs, match):
    with pytest.raises(ValidationError, match=match):
        await get_prices(AsyncDummySession(), BASE_URL, ["RTP"], "E", **kwargs)


@pytest.mark.parametrize("schedules", [[], [""]])
async def test_async_get_prices_requires_schedules(schedules):
    with pytest.raises(ValidationError, match="schedules must contain"):
        await get_prices(AsyncDummySession(), BASE_URL, schedules, "E")


async def test_async_get_schedule_prices_requires_schedule():
    with pytest.raises(ValidationError, match="schedule is required"):
        await get_schedule_prices(AsyncDummySession(), BASE_URL, "", "E")


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ({"schedules": "invalid"}, "Invalid 'schedules' payload"),
        (["invalid"], "Invalid schedule details payload"),
        ([{"schedule": 1}], "Invalid or missing 'schedule'"),
        ([{"schedule": "RTP", "prices": {}}], "Invalid 'prices' payload"),
    ],
)
async def test_async_get_prices_rejects_malformed_payloads(payload, match):
    session = _session_returning("/prices", AsyncDummyResponse(payload=payload))

    with pytest.raises(ResponseFormatError, match=match):
        await get_prices(session, BASE_URL, ["RTP"], "E")


@pytest.mark.parametrize(
    ("call", "path"),
    [
        (lambda s: get_prices(s, BASE_URL, ["RTP"], "E"), "/prices"),
        (lambda s: get_schedule_prices(s, BASE_URL, "RTP", "E"), "/schedules/RTP/prices"),
        (lambda s: list_nodes(s, BASE_URL), "/nodes"),
    ],
)
async def test_async_endpoints_map_json_decode_errors(call, path):
    session = _session_returning(path, AsyncDummyResponse(json_error=ValueError("bad json")))

    with pytest.raises(ResponseFormatError, match="Invalid JSON"):
        await call(session)


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ({"node": "OTA2201"}, "Invalid nodes payload"),
        (["invalid"], "Invalid node entry"),
        ([{"island": "NI"}], "Invalid or missing 'node'"),
        ([{"node": "OTA2201", "island": ""}], "Invalid or missing 'island'"),
    ],
)
async def test_async_list_nodes_rejects_malformed_payloads(payload, match):
    session = _session_returning("/nodes", AsyncDummyResponse(payload=payload))

    with pytest.raises(ResponseFormatError, match=match):
        await list_nodes(session, BASE_URL)


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ({"schedule": "RTP"}, "Invalid schedules payload"),
        (["invalid"], "Invalid schedule entry"),
        ([{"runType": "short"}], "Invalid or missing 'schedule'"),
        ([{"schedule": "RTP", "runType": 1}], "Invalid 'runType'"),
        ([{"schedule": "RTP", "marketType": 1}], "Invalid 'marketType'"),
    ],
)
async def test_async_list_schedules_rejects_malformed_payloads(payload, match):
    session = _session_returning("/schedules", AsyncDummyResponse(payload=payload))

    with pytest.raises(ResponseFormatError, match=match):
        await list_schedules(session, BASE_URL)


@pytest.mark.parametrize(
    ("response", "match"),
    [
        (AsyncDummyResponse(status=401, text_val="denied"), r"status 401\): denied"),
        (AsyncDummyResponse(json_error=ValueError("bad json")), "invalid JSON"),
        (AsyncDummyResponse(payload=["token"]), "unexpected payload"),
        (AsyncDummyResponse(payload={"access_token": ""}), "did not return an access_token"),
        (
            AsyncDummyResponse(payload={"access_token": TOKEN_VALUE, "expires_in": "soon"}),
            "invalid expires_in",
        ),
    ],
)
async def test_async_auth_rejects_bad_token_responses(response, match):
    auth = AsyncOAuth2ClientCredentials(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        base_url="https://api.electricityinfo.co.nz",
        session=AsyncDummySession(post_response=response),
    )

    with pytest.raises(AuthenticationError, match=match):
        await auth.get_token()
