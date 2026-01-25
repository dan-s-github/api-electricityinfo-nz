"""
Shared fixtures for integration tests.

To run these tests, create a secrets.yaml file in the tests directory with:
  client_id: your_client_id
  client_secret: your_client_secret
"""
from pathlib import Path
import pytest
import yaml

from electricityinfo_nz.client import MarketPricesClient


def load_secrets():
    """Load credentials from secrets.yaml file."""
    secrets_path = Path(__file__).parent / "secrets.yaml"
    if not secrets_path.exists():
        return None

    with open(secrets_path, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def secrets():
    """Load secrets for integration tests."""
    creds = load_secrets()
    if not creds:
        pytest.skip("secrets.yaml not found - skipping integration tests")

    if not creds.get("client_id") or not creds.get("client_secret"):
        pytest.skip("client_id or client_secret missing in secrets.yaml")

    return creds


@pytest.fixture(scope="module")
def client(secrets):
    """Create a real client for integration tests."""
    return MarketPricesClient(
        client_id=secrets["client_id"],
        client_secret=secrets["client_secret"],
    )


@pytest.fixture(scope="module")
def all_schedules(client):
    """Get all available schedules for testing."""
    return client.get_schedules()
