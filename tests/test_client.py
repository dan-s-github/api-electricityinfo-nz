import json
from datetime import datetime

import pytest
import requests

from electricityinfo_nz.auth import OAuth2ClientCredentials
from electricityinfo_nz.client import MarketPricesClient
from electricityinfo_nz.endpoints.nodes import list_nodes
from electricityinfo_nz.endpoints.prices import get_prices, get_schedule_prices
from electricityinfo_nz.endpoints.schedules import list_schedules
from electricityinfo_nz.exceptions import (
    AuthenticationError,
    MarketPricesAPIError,
    NotFoundError,
    RateLimitError,
    ResponseFormatError,
    TransportError,
    ValidationError,
)
from electricityinfo_nz.models import PriceDetail, Schedule, ScheduleDetails
from electricityinfo_nz.schedule_names import resolve_schedule_name

TEST_CLIENT_SECRET = "test-client-secret"  # noqa: S105
TOKEN_VALUE = "token-value"  # noqa: S105
BASE_URL = "https://api.electricityinfo.co.nz/api/market-prices/v1"


class DummyResponse:
    def __init__(self, status_code=200, payload=None, text=None, json_error=None):
        self.status_code = status_code
        self._payload = payload or []
        self.text = text if text is not None else json.dumps(self._payload)
        self._json_error = json_error

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error


class DummySession:
    def __init__(self, get_map=None, post_response=None, get_error=None, post_error=None):
        self.get_map = get_map or {}
        self.post_response = post_response or DummyResponse(
            payload={"access_token": TOKEN_VALUE, "expires_in": 3600}
        )
        self.get_error = get_error
        self.post_error = post_error
        self.last_get = None
        self.last_post = None

    def get(self, url, params=None, headers=None, timeout=None):
        self.last_get = {
            "url": url,
            "params": params,
            "headers": headers,
            "timeout": timeout,
        }
        if self.get_error is not None:
            raise self.get_error
        return self.get_map.get(url, DummyResponse(payload=[]))

    def post(self, url, data=None, auth=None, timeout=None):
        self.last_post = {
            "url": url,
            "data": data,
            "auth": auth,
            "timeout": timeout,
        }
        if self.post_error is not None:
            raise self.post_error
        return self.post_response


class DummyAuth:
    def __init__(self):
        self.calls = 0

    def get_token(self):
        self.calls += 1
        return TOKEN_VALUE


@pytest.fixture
def client(monkeypatch):
    session = DummySession(
        get_map={
            "https://api.electricityinfo.co.nz/api/market-prices/v1/schedules": DummyResponse(
                payload=[{"schedule": "RTP", "runType": "short", "marketType": "E"}]
            )
        }
    )

    c = MarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=session,
    )

    dummy_auth = DummyAuth()
    monkeypatch.setattr(c, "auth", dummy_auth)
    return c


def test_get_schedules(client):
    schedules = client.get_schedules()
    assert len(schedules) == 1
    assert schedules[0].schedule == "RTP"
    assert client.session.last_get["headers"] == {"Authorization": f"Bearer {TOKEN_VALUE}"}
    assert client.session.last_get["timeout"] == 30.0


def test_get_nodes_returns_node_dictionaries(monkeypatch):
    session = DummySession(
        get_map={
            "https://api.electricityinfo.co.nz/api/market-prices/v1/nodes": DummyResponse(
                payload=[{"node": "OTA2201", "island": "NI"}]
            )
        }
    )
    client = MarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=session,
    )
    monkeypatch.setattr(client, "auth", DummyAuth())

    nodes = client.get_nodes()

    assert nodes == [{"node": "OTA2201", "island": "NI"}]


def test_get_prices_rejects_invalid_market_type(monkeypatch):
    client = MarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=DummySession(),
    )
    monkeypatch.setattr(client, "auth", DummyAuth())

    with pytest.raises(ValidationError, match="market_type"):
        client.get_prices(["RTP"], market_type="X", back=4)


def test_get_prices_rejects_mixed_range_filters(monkeypatch):
    client = MarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=DummySession(),
    )
    monkeypatch.setattr(client, "auth", DummyAuth())

    with pytest.raises(ValidationError, match="from/to cannot be combined"):
        client.get_prices(
            ["RTP"],
            market_type="E",
            from_datetime="2026-01-01T00:00:00Z",
            back=1,
        )


def test_get_prices_invalid_payload_raises_response_format_error(monkeypatch):
    session = DummySession(
        get_map={
            "https://api.electricityinfo.co.nz/api/market-prices/v1/prices": DummyResponse(
                payload="invalid"
            )
        }
    )
    client = MarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=session,
    )
    monkeypatch.setattr(client, "auth", DummyAuth())

    with pytest.raises(ResponseFormatError, match="Invalid prices payload"):
        client.get_prices(["RTP"], market_type="E", back=1)


def test_get_prices_invalid_datetime_raises_response_format_error(monkeypatch):
    session = DummySession(
        get_map={
            "https://api.electricityinfo.co.nz/api/market-prices/v1/prices": DummyResponse(
                payload={
                    "schedules": [
                        {
                            "schedule": "RTP",
                            "prices": [
                                {
                                    "tradingDateTime": "not-a-date",
                                    "tradingPeriod": 1,
                                    "node": "OTA2201",
                                }
                            ],
                        }
                    ]
                }
            )
        }
    )
    client = MarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=session,
    )
    monkeypatch.setattr(client, "auth", DummyAuth())

    with pytest.raises(ResponseFormatError, match="Invalid datetime value"):
        client.get_prices(["RTP"], market_type="E", back=1)


def test_get_schedules_maps_network_errors(monkeypatch):
    client = MarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=DummySession(get_error=requests.Timeout("timed out")),
    )
    monkeypatch.setattr(client, "auth", DummyAuth())

    with pytest.raises(TransportError, match="Request failed"):
        client.get_schedules()


def test_get_prices_maps_http_faults_to_validation_error(monkeypatch):
    session = DummySession(
        get_map={
            "https://api.electricityinfo.co.nz/api/market-prices/v1/prices": DummyResponse(
                status_code=400,
                payload={
                    "message": "Invalid Request",
                    "detail": "back must be between 1 and 48",
                    "code": "BAD_REQUEST",
                },
            )
        }
    )
    client = MarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=session,
    )
    monkeypatch.setattr(client, "auth", DummyAuth())

    with pytest.raises(ValidationError, match=r"Invalid Request .*BAD_REQUEST"):
        client.get_prices(["RTP"], market_type="E", back=1)


def test_get_schedule_prices_with_single_node_sends_node_filter(monkeypatch):
    session = DummySession(
        get_map={
            "https://api.electricityinfo.co.nz/api/market-prices/v1/schedules/RTP/prices": (
                DummyResponse(
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
    client = MarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=session,
    )
    monkeypatch.setattr(client, "auth", DummyAuth())

    result = client.get_schedule_prices(
        schedule="RTP",
        market_type="E",
        nodes=["OTA2201"],
        forward=1,
    )

    assert session.last_get["params"] == {
        "marketType": "E",
        "nodes": "OTA2201",
        "forward": 1,
    }
    assert [price.node for price in result.prices] == ["OTA2201"]


def test_schedule_models_expose_human_readable_schedule_names():
    schedule = Schedule(schedule="PRSS", run_type="short", market_type="E")
    details = ScheduleDetails(schedule="RTD", prices=[])
    price = PriceDetail(
        trading_datetime=datetime.fromisoformat("2026-01-01T00:00:00+00:00"),
        trading_period=1,
        node="OTA2201",
        schedule="WDS",
    )

    assert schedule.schedule_name == "Price-responsive short schedule"
    assert details.schedule_name == "Real-time dispatch"
    assert price.schedule_name == "Weekly dispatch schedule"


def test_resolve_schedule_name_falls_back_to_raw_code_for_unknown_values():
    assert resolve_schedule_name("UNKNOWN") == "UNKNOWN"


def test_auth_fetch_uses_timeout_and_caches_token():
    session = DummySession()
    auth = OAuth2ClientCredentials(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        base_url="https://api.electricityinfo.co.nz",
        session=session,
        timeout=12.5,
    )

    token = auth.get_token()
    cached_token = auth.get_token()

    assert token == TOKEN_VALUE
    assert cached_token == TOKEN_VALUE
    assert session.last_post["timeout"] == 12.5
    assert session.last_post["auth"] == ("id", TEST_CLIENT_SECRET)


def test_auth_timeout_raises_authentication_error():
    auth = OAuth2ClientCredentials(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        base_url="https://api.electricityinfo.co.nz",
        session=DummySession(post_error=requests.Timeout("timed out")),
    )

    with pytest.raises(AuthenticationError, match="Failed to obtain access token"):
        auth.get_token()


def test_auth_invalid_json_raises_authentication_error():
    auth = OAuth2ClientCredentials(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        base_url="https://api.electricityinfo.co.nz",
        session=DummySession(post_response=DummyResponse(json_error=ValueError("bad json"))),
    )

    with pytest.raises(AuthenticationError, match="invalid JSON"):
        auth.get_token()


def _session_returning(path, response):
    return DummySession(get_map={f"{BASE_URL}{path}": response})


def _http_error_response(status_code, payload):
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(payload).encode()
    return response


def test_client_requires_credentials(monkeypatch):
    monkeypatch.delenv("WITS_CLIENT_ID", raising=False)
    monkeypatch.delenv("WITS_CLIENT_SECRET", raising=False)

    with pytest.raises(AuthenticationError, match="client_id and client_secret"):
        MarketPricesClient()


def test_client_reads_credentials_from_environment(monkeypatch):
    monkeypatch.setenv("WITS_CLIENT_ID", "env-id")
    monkeypatch.setenv("WITS_CLIENT_SECRET", TEST_CLIENT_SECRET)

    client = MarketPricesClient(session=DummySession())

    assert client.client_id == "env-id"
    assert client.auth.base_url == "https://api.electricityinfo.co.nz"


def test_client_rejects_non_positive_timeout():
    with pytest.raises(ValidationError, match="timeout"):
        MarketPricesClient(client_id="id", client_secret=TEST_CLIENT_SECRET, timeout=0)


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (401, AuthenticationError),
        (403, AuthenticationError),
        (404, NotFoundError),
        (400, ValidationError),
        (429, RateLimitError),
        (500, MarketPricesAPIError),
    ],
)
def test_wrap_maps_http_status_to_exception(monkeypatch, status_code, expected):
    response = _http_error_response(status_code, {"message": "Boom"})
    client = MarketPricesClient(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        session=_session_returning("/schedules", response),
    )
    monkeypatch.setattr(client, "auth", DummyAuth())

    with pytest.raises(expected, match="Boom") as exc_info:
        client.get_schedules()

    assert type(exc_info.value) is expected


def test_wrap_handles_http_error_without_response():
    client = MarketPricesClient(client_id="id", client_secret=TEST_CLIENT_SECRET)

    def fail():
        raise requests.HTTPError("no response")

    with pytest.raises(MarketPricesAPIError, match="no response"):
        client._wrap(fail)


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (DummyResponse(json_error=ValueError("bad json")), "fallback"),
        (DummyResponse(payload=["not", "a", "dict"]), "fallback"),
        (DummyResponse(payload={"detail": "no message"}), "fallback"),
        (DummyResponse(payload={"message": "Only message"}), "Only message"),
        (DummyResponse(payload={"message": "Msg", "code": "CODE"}), "Msg [CODE]"),
    ],
)
def test_response_message(response, expected):
    client = MarketPricesClient(client_id="id", client_secret=TEST_CLIENT_SECRET)

    assert client._response_message(response, "fallback") == expected


def test_get_prices_accepts_list_payload_and_sends_all_filters(monkeypatch):
    session = _session_returning(
        "/prices",
        DummyResponse(
            payload=[
                {
                    "schedule": "RTP",
                    "prices": [
                        {
                            "tradingDateTime": "2026-01-01T00:00:00+13:00",
                            "tradingPeriod": "2",
                            "node": "OTA2201",
                            "price": "10.5",
                            "schedule": "RTP",
                            "lastRunTime": "2026-01-01T00:05:00Z",
                        }
                    ],
                }
            ]
        ),
    )
    client = MarketPricesClient(client_id="id", client_secret=TEST_CLIENT_SECRET, session=session)
    monkeypatch.setattr(client, "auth", DummyAuth())

    result = client.get_prices(
        ["RTP", "PRSS"],
        market_type="R",
        nodes=["OTA2201", "BEN2201"],
        from_datetime="2026-01-01T00:00:00Z",
        to_datetime="2026-01-02T00:00:00Z",
        island="SI",
        offset=0,
    )

    assert session.last_get["params"] == {
        "schedules": "RTP,PRSS",
        "marketType": "R",
        "nodes": "OTA2201,BEN2201",
        "from": "2026-01-01T00:00:00Z",
        "to": "2026-01-02T00:00:00Z",
        "island": "SI",
        "offset": 0,
    }
    price = result[0].prices[0]
    assert price.trading_period == 2
    assert price.price == 10.5
    assert price.last_run_time is not None
    assert price.run_type is None


def test_price_detail_schedule_name_is_none_without_schedule():
    price = PriceDetail(
        trading_datetime=datetime.fromisoformat("2026-01-01T00:00:00+00:00"),
        trading_period=1,
        node="OTA2201",
    )

    assert price.schedule_name is None


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"island": "XX"}, "island"),
        ({"back": 0}, "back"),
        ({"forward": 49}, "forward"),
        ({"offset": -1}, "offset"),
        ({"from_datetime": "not-a-date"}, "'from' datetime"),
        ({"to_datetime": "not-a-date"}, "'to' datetime"),
        ({"nodes": ["OTA2201", ""]}, "nodes"),
    ],
)
def test_price_filter_validation(kwargs, match):
    with pytest.raises(ValidationError, match=match):
        get_prices(DummySession(), BASE_URL, ["RTP"], "E", **kwargs)


@pytest.mark.parametrize("schedules", [[], ["RTP", ""]])
def test_get_prices_requires_schedules(schedules):
    with pytest.raises(ValidationError, match="schedules must contain"):
        get_prices(DummySession(), BASE_URL, schedules, "E")


def test_get_schedule_prices_requires_schedule():
    with pytest.raises(ValidationError, match="schedule is required"):
        get_schedule_prices(DummySession(), BASE_URL, "", "E")


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ({"schedules": "invalid"}, "Invalid 'schedules' payload"),
        (["invalid"], "Invalid schedule details payload"),
        ([{"schedule": ""}], "Invalid or missing 'schedule'"),
        ([{"schedule": "RTP", "prices": "invalid"}], "Invalid 'prices' payload"),
    ],
)
def test_get_prices_rejects_malformed_payloads(payload, match):
    session = _session_returning("/prices", DummyResponse(payload=payload))

    with pytest.raises(ResponseFormatError, match=match):
        get_prices(session, BASE_URL, ["RTP"], "E")


VALID_PRICE = {"tradingDateTime": "2026-01-01T00:00:00Z", "tradingPeriod": 1, "node": "OTA2201"}


@pytest.mark.parametrize(
    ("price", "match"),
    [
        ("invalid", "expected an object"),
        ({**VALID_PRICE, "node": ""}, "Invalid or missing 'node'"),
        ({k: v for k, v in VALID_PRICE.items() if k != "tradingPeriod"}, "missing 'tradingPeriod'"),
        ({**VALID_PRICE, "tradingPeriod": "one"}, "Invalid 'tradingPeriod'"),
        ({**VALID_PRICE, "tradingPeriod": None}, "Invalid 'tradingPeriod'"),
        ({**VALID_PRICE, "runType": 5}, "Invalid 'runType'"),
        ({**VALID_PRICE, "price": "abc"}, "Invalid 'price'"),
    ],
)
def test_get_schedule_prices_rejects_malformed_price_entries(price, match):
    session = _session_returning(
        "/schedules/RTP/prices", DummyResponse(payload={"prices": [price]})
    )

    with pytest.raises(ResponseFormatError, match=match):
        get_schedule_prices(session, BASE_URL, "RTP", "E")


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ({"node": "OTA2201"}, "Invalid nodes payload"),
        (["invalid"], "Invalid node entry"),
        ([{"node": "", "island": "NI"}], "Invalid or missing 'node'"),
        ([{"node": "OTA2201", "island": None}], "Invalid or missing 'island'"),
    ],
)
def test_list_nodes_rejects_malformed_payloads(payload, match):
    session = _session_returning("/nodes", DummyResponse(payload=payload))

    with pytest.raises(ResponseFormatError, match=match):
        list_nodes(session, BASE_URL)


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ({"schedule": "RTP"}, "Invalid schedules payload"),
        (["invalid"], "Invalid schedule entry"),
        ([{"schedule": ""}], "Invalid or missing 'schedule'"),
        ([{"schedule": "RTP", "runType": 1}], "Invalid 'runType'"),
        ([{"schedule": "RTP", "marketType": 1}], "Invalid 'marketType'"),
    ],
)
def test_list_schedules_rejects_malformed_payloads(payload, match):
    session = _session_returning("/schedules", DummyResponse(payload=payload))

    with pytest.raises(ResponseFormatError, match=match):
        list_schedules(session, BASE_URL)


def _auth_with_response(response):
    return OAuth2ClientCredentials(
        client_id="id",
        client_secret=TEST_CLIENT_SECRET,
        base_url="https://api.electricityinfo.co.nz",
        session=DummySession(post_response=response),
    )


@pytest.mark.parametrize(
    ("response", "match"),
    [
        (DummyResponse(status_code=401, text="denied"), r"status 401\): denied"),
        (DummyResponse(payload=["token"]), "unexpected payload"),
        (DummyResponse(payload={"expires_in": 3600}), "did not return an access_token"),
        (
            DummyResponse(payload={"access_token": TOKEN_VALUE, "expires_in": "soon"}),
            "invalid expires_in",
        ),
    ],
)
def test_auth_rejects_bad_token_responses(response, match):
    with pytest.raises(AuthenticationError, match=match):
        _auth_with_response(response).get_token()
