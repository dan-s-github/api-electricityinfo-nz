# Electricity Info NZ - Market Prices Python Client

Python client for the WITS Market Prices API (`/api/market-prices/v1`). Provides thin wrappers around the schedules, nodes, and prices endpoints with OAuth2 client credentials authentication.

## Installation

```bash
pip install electricityinfo-nz
```

## Quick start

```python
from electricityinfo_nz import MarketPricesClient

client = MarketPricesClient(client_id="YOUR_CLIENT_ID", client_secret="YOUR_CLIENT_SECRET")

schedules = client.get_schedules()
prices = client.get_prices(schedules=["RTP"], market_type="E", back=4, forward=4)
```

## Authentication

The API uses OAuth2 Client Credentials. Provide `client_id` and `client_secret` when constructing `MarketPricesClient`, or set environment variables `WITS_CLIENT_ID` and `WITS_CLIENT_SECRET`.

## Endpoints covered
- `GET /schedules`
- `GET /nodes`
- `GET /schedules/{schedule}/prices`
- `GET /prices`

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Releasing

```bash
python -m build
twine upload dist/*
```
