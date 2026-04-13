from __future__ import annotations

from datetime import datetime
from typing import Any

from .exceptions import ResponseFormatError
from .models import PriceDetail


def parse_datetime(value: str) -> datetime:
    """Parse an API datetime string into a timezone-aware datetime."""
    normalized_value = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(normalized_value)
    except ValueError as exc:
        raise ResponseFormatError(f"Invalid datetime value in API response: {value!r}") from exc


def _require_string(item: dict[str, Any], field: str) -> str:
    value = item.get(field)
    if isinstance(value, str) and value:
        return value
    raise ResponseFormatError(f"Invalid or missing {field!r} in API response")


def _optional_string(item: dict[str, Any], field: str) -> str | None:
    value = item.get(field)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise ResponseFormatError(f"Invalid {field!r} value in API response")


def _optional_float(item: dict[str, Any], field: str) -> float | None:
    value = item.get(field)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ResponseFormatError(f"Invalid {field!r} value in API response") from exc


def parse_price_detail(item: dict[str, Any]) -> PriceDetail:
    """Parse a price detail object from the API response."""
    if not isinstance(item, dict):
        raise ResponseFormatError("Invalid price entry in API response: expected an object")

    trading_datetime_value = _require_string(item, "tradingDateTime")
    node = _require_string(item, "node")

    try:
        trading_period = int(item["tradingPeriod"])
    except KeyError as exc:
        raise ResponseFormatError("Invalid or missing 'tradingPeriod' in API response") from exc
    except (TypeError, ValueError) as exc:
        raise ResponseFormatError("Invalid 'tradingPeriod' value in API response") from exc

    last_run_time_value = _optional_string(item, "lastRunTime")
    return PriceDetail(
        trading_datetime=parse_datetime(trading_datetime_value),
        trading_period=trading_period,
        node=node,
        price=_optional_float(item, "price"),
        price6s=_optional_float(item, "price6s"),
        price60s=_optional_float(item, "price60s"),
        schedule=_optional_string(item, "schedule"),
        run_type=_optional_string(item, "runType"),
        last_run_time=parse_datetime(last_run_time_value) if last_run_time_value else None,
        reserve_node=_optional_string(item, "reserveNode"),
    )
