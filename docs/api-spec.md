# OpenAPI specification

The upstream WITS Market Prices OpenAPI specification is included in this repository as:

- [`docs/market-prices.yaml`](market-prices.yaml)

You can also browse the source API documentation at:

- <https://developer.electricityinfo.co.nz/WITS/documentation/market-prices>

The Python client in this repository wraps the following endpoints from that API:

- `GET /schedules`
- `GET /nodes`
- `GET /schedules/{schedule}/prices`
- `GET /prices`
