import json
from datetime import datetime

import pytest
import requests

from electricityinfo_nz.auth import OAuth2ClientCredentials
from electricityinfo_nz.client import MarketPricesClient
from electricityinfo_nz.exceptions import (
    AuthenticationError,
    ResponseFormatError,
    TransportError,
    ValidationError,
)
from electricityinfo_nz.models import PriceDetail, Schedule, ScheduleDetails
from electricityinfo_nz.schedule_names import resolve_schedule_name

TEST_CLIENT_SECRET = "test-client-secret"  # noqa: S105
TOKEN_VALUE = "token-value"  # noqa: S105


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
