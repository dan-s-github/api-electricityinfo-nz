import json
import types
import pytest

from electricityinfo_nz.client import MarketPricesClient


class DummyResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or []
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class DummySession:
    def __init__(self, payload_map):
        self.payload_map = payload_map
        self.headers = {}

    def get(self, url, params=None):
        payload = self.payload_map.get(url, [])
        return DummyResponse(payload=payload)


class DummyAuth:
    def __init__(self):
        self.calls = 0

    def get_token(self):
        self.calls += 1
        return "token"


@pytest.fixture
def client(monkeypatch):
    payload_map = {
        "https://api.electricityinfo.co.nz/api/market-prices/v1/schedules": [
            {"schedule": "RTP", "runType": "short", "marketType": "E"}
        ]
    }
    session = DummySession(payload_map)

    c = MarketPricesClient(
        client_id="id",
        client_secret="secret",
        session=session,
    )

    dummy_auth = DummyAuth()
    monkeypatch.setattr(c, "auth", dummy_auth)
    return c


def test_get_schedules(client):
    schedules = client.get_schedules()
    assert len(schedules) == 1
    assert schedules[0].schedule == "RTP"
