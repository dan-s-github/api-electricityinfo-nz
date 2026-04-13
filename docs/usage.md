# Usage

## Quick start

```python
from electricityinfo_nz import MarketPricesClient

client = MarketPricesClient()

schedules = client.get_schedules()
for schedule in schedules:
    print(schedule.schedule, "-", schedule.schedule_name)

prices = client.get_prices(
    schedules=["PRSL"],
    market_type="E",
    nodes=["OTA2201"],
    forward=48,
)
```

## Client configuration

You can configure the client with a custom timeout or a custom `requests.Session`.

### Custom timeout

```python
from electricityinfo_nz import MarketPricesClient

client = MarketPricesClient(timeout=15.0)
```

### Custom requests session

```python
import requests

from electricityinfo_nz import MarketPricesClient

session = requests.Session()
client = MarketPricesClient(session=session)
```

## Choosing a schedule

If you need a **next-24h electricity price forecast**, use **`PRSL`** by default.

- `PRSL` = **Price-responsive long schedule**
- `NRSL` = non-responsive long schedule
- `PRSS` and `NRSS` are better suited to shorter horizons
- `WDS` is a broader longer-range planning view
- `RTD`, `Interim`, and `Final` are not the recommended schedules for a 24-hour forecast

## Market type

`market_type` selects which market you want to query:

- `E` = **Energy**
- `R` = **Reserve**

For most spot price use cases in this library, you will usually want `market_type="E"`.

## Price units

Price fields such as `price`, `price6s`, and `price60s` are expressed in **NZD/MWh**.

## Schedule names

| Code    | Name                            |
| ------- | ------------------------------- |
| Final   | Final settled prices            |
| Interim | Interim prices                  |
| NRSL    | Non-responsive long schedule    |
| NRSS    | Non-responsive short schedule   |
| PRSL    | Price-responsive long schedule  |
| PRSS    | Price-responsive short schedule |
| RTD     | Real-time dispatch              |
| WDS     | Weekly dispatch schedule        |

## Common usage patterns

### Next 24h forecast for one node

```python
from electricityinfo_nz import MarketPricesClient

client = MarketPricesClient()

result = client.get_schedule_prices(
    schedule="PRSL",
    market_type="E",
    nodes=["OTA2201"],
    forward=48,
)

for price in result.prices:
    print(price.trading_datetime, price.node, price.price)
```

### Historical prices

```python
from electricityinfo_nz import MarketPricesClient

client = MarketPricesClient()

results = client.get_prices(
    schedules=["Final"],
    market_type="E",
    nodes=["OTA2201"],
    back=10,
)
```

### Discover nodes

```python
from electricityinfo_nz import MarketPricesClient

client = MarketPricesClient()

nodes = client.get_nodes()

for node in nodes[:5]:
    print(node["node"], node["island"])
```

## Query parameters

Both `get_prices()` and `get_schedule_prices()` support the same filters:

| Parameter                       | Meaning                                         |
| ------------------------------- | ----------------------------------------------- |
| `market_type`                   | Market type: `E` for energy or `R` for reserve. |
| `nodes`                         | List of node codes such as `["OTA2201"]`.       |
| `from_datetime` / `to_datetime` | Explicit datetime range.                        |
| `back`                          | Number of past trading periods to fetch.        |
| `forward`                       | Number of future trading periods to fetch.      |
| `island`                        | Island filter: `NI` or `SI`.                    |
| `offset`                        | Pagination offset.                              |

`from_datetime` / `to_datetime` cannot be combined with `back` / `forward`.

### Datetime format

Use ISO 8601 datetimes such as:

```python
from electricityinfo_nz import MarketPricesClient

client = MarketPricesClient()

results = client.get_prices(
    schedules=["Final"],
    market_type="E",
    from_datetime="2026-04-12T00:00:00Z",
    to_datetime="2026-04-12T12:00:00Z",
)
```

## Returned objects

### `get_schedules()`

Returns `Schedule` objects with:

- `schedule`
- `schedule_name`
- `run_type`
- `market_type`

### `get_schedule_prices()` and `get_prices()`

Return `ScheduleDetails` objects containing:

- `schedule`
- `schedule_name`
- `prices`

Each `prices` entry is a `PriceDetail` with fields including:

- `trading_datetime`
- `trading_period`
- `node`
- `price`
- `price6s`
- `price60s`
- `schedule`
- `schedule_name`
- `run_type`
- `last_run_time`
- `reserve_node`

## Error handling

The client raises typed exceptions:

- `AuthenticationError`
- `ValidationError`
- `NotFoundError`
- `RateLimitError`
- `TransportError`
- `ResponseFormatError`

```python
from electricityinfo_nz import MarketPricesClient, ValidationError

client = MarketPricesClient()

try:
    client.get_prices(schedules=["PRSL"], market_type="E", back=4, forward=4)
except ValidationError as exc:
    print(f"Invalid request: {exc}")
```

## OpenAPI specification

For the bundled OpenAPI file and upstream API reference, see the [API spec page](api-spec.md).
