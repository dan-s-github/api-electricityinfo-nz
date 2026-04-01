# Copilot Instructions

## Project Overview

Python client library for the WITS Market Prices API (`/api/market-prices/v1`) — the New Zealand wholesale electricity market. Wraps three endpoints: schedules, nodes, and prices. Published to PyPI as `electricityinfo-nz`.

## Commands

```bash
uv sync                          # Install all dependencies (creates .venv)

uv run pytest                    # Run all tests
uv run pytest tests/test_client.py      # Run a single test file
uv run pytest -k "test_get_prices"      # Run a single test by name

uv run pre-commit run -a         # Run all linters/formatters
uv run ruff check src/ tests/    # Lint only
uv run ruff format src/ tests/   # Format only
uv run mypy src/                 # Type-check

uv build                         # Build distribution
```

## Architecture

```
src/electricityinfo_nz/
├── client.py        # MarketPricesClient — public entry point; wraps all endpoint calls
├── auth.py          # OAuth2ClientCredentials — fetches/caches tokens with 30s expiry buffer
├── endpoints/
│   ├── prices.py    # get_prices(), get_schedule_prices()
│   ├── schedules.py # list_schedules()
│   └── nodes.py     # list_nodes()
├── models.py        # Dataclasses: Schedule, PriceDetail, ScheduleDetails
├── exceptions.py    # Exception hierarchy rooted at MarketPricesAPIError
└── utils.py         # Parsing helpers
```

`MarketPricesClient` accepts an optional `requests.Session` for dependency injection in tests. All API calls go through `client._wrap()` which maps HTTP status codes to typed exceptions (`AuthenticationError`, `NotFoundError`, `RateLimitError`, etc.).

## Key Conventions

**Parameter handling:** Every endpoint function calls `_clean_params()` to strip `None` values before building the query string. Lists are serialized to comma-separated strings via `_format_array()`. Follow this pattern when adding new parameters.

**Models:** Use `@dataclass` throughout. API JSON keys (camelCase) are mapped to snake_case Python fields in `utils.py`.

**Type hints:** All public functions are fully annotated. Strict mypy is enforced (`disallow_untyped_defs`, `disallow_any_generics`); tests are exempt.

**Line length:** 100 characters (ruff configured for this).

**Error handling:** Raise specific exception subclasses from `exceptions.py`, never raw `requests.HTTPError`. The `_wrap()` pattern in `client.py` is the canonical place for HTTP-to-exception mapping.

## Testing

Integration tests require real credentials in `tests/secrets.yaml` (see `tests/secrets.yaml.example`). Tests skip gracefully when this file is absent. `conftest.py` loads secrets at module scope and creates a shared client fixture.

`test_client.py` is the only unit test; it uses `DummySession`/`DummyAuth`/`DummyResponse` inline classes — follow this pattern for new unit tests that don't need real credentials.

## Keeping These Instructions Current

When making changes that affect architecture, commands, conventions, or testing patterns, update this file in the same commit.

## `prices.py` (root)

Standalone data-extraction script — not part of the installable library. Downloads historical spot price CSVs from the Electricity Authority's Azure blob storage, handles schema variations between old and new datasets, and produces charts via matplotlib/pandas. Edit `START_DATE`, `END_DATE`, and `NODE` at the top to change the query range.
