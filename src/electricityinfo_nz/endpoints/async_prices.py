from __future__ import annotations

from collections.abc import Mapping

import aiohttp

from ..constants import DEFAULT_TIMEOUT
from ..exceptions import ResponseFormatError, ValidationError
from ..models import ScheduleDetails
from ..utils import parse_datetime, parse_price_detail

QueryParamValue = str | int | float
QueryParams = dict[str, QueryParamValue | None]
ResolvedQueryParams = dict[str, QueryParamValue]
VALID_MARKET_TYPES = {"E", "R"}
VALID_ISLANDS = {"NI", "SI"}


def _clean_params(params: QueryParams) -> ResolvedQueryParams:
    return {k: v for k, v in params.items() if v is not None}


def _format_array(values: list[str] | None) -> str | None:
    if not values:
        return None
    return ",".join(values)


def _validate_datetime_parameter(name: str, value: str | None) -> None:
    if value is None:
        return

    try:
        parse_datetime(value)
    except ResponseFormatError as exc:
        raise ValidationError(f"Invalid {name!r} datetime parameter: {value!r}") from exc


def _validate_common_price_filters(
    market_type: str,
    nodes: list[str] | None,
    from_datetime: str | None,
    to_datetime: str | None,
    back: int | None,
    forward: int | None,
    island: str | None,
    offset: int | None,
) -> None:
    if market_type not in VALID_MARKET_TYPES:
        raise ValidationError("market_type must be one of: E, R")

    if island is not None and island not in VALID_ISLANDS:
        raise ValidationError("island must be one of: NI, SI")

    if back is not None and not 1 <= back <= 48:
        raise ValidationError("back must be between 1 and 48")

    if forward is not None and not 1 <= forward <= 48:
        raise ValidationError("forward must be between 1 and 48")

    if offset is not None and offset < 0:
        raise ValidationError("offset must be greater than or equal to 0")

    if (from_datetime is not None or to_datetime is not None) and (
        back is not None or forward is not None
    ):
        raise ValidationError("from/to cannot be combined with back/forward")

    _validate_datetime_parameter("from", from_datetime)
    _validate_datetime_parameter("to", to_datetime)

    if nodes is not None and any(not isinstance(node, str) or not node for node in nodes):
        raise ValidationError("nodes must contain only non-empty strings")


def _parse_schedule_details(payload: object, *, default_schedule: str = "") -> ScheduleDetails:
    if not isinstance(payload, dict):
        raise ResponseFormatError("Invalid schedule details payload in API response")

    schedule = payload.get("schedule", default_schedule)
    if not isinstance(schedule, str) or not schedule:
        raise ResponseFormatError("Invalid or missing 'schedule' in API response")

    prices_payload = payload.get("prices", [])
    if not isinstance(prices_payload, list):
        raise ResponseFormatError("Invalid 'prices' payload in API response")

    return ScheduleDetails(
        schedule=schedule,
        prices=[parse_price_detail(item) for item in prices_payload],
    )


async def get_schedule_prices(
    session: aiohttp.ClientSession,
    base_url: str,
    schedule: str,
    market_type: str,
    nodes: list[str] | None = None,
    from_datetime: str | None = None,
    to_datetime: str | None = None,
    back: int | None = None,
    forward: int | None = None,
    island: str | None = None,
    offset: int | None = None,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> ScheduleDetails:
    """Return prices for a single schedule."""
    if not schedule:
        raise ValidationError("schedule is required")

    _validate_common_price_filters(
        market_type,
        nodes,
        from_datetime,
        to_datetime,
        back,
        forward,
        island,
        offset,
    )

    url = f"{base_url}/schedules/{schedule}/prices"
    params = _clean_params(
        {
            "marketType": market_type,
            "nodes": _format_array(nodes),
            "from": from_datetime,
            "to": to_datetime,
            "back": back,
            "forward": forward,
            "island": island,
            "offset": offset,
        }
    )
    aio_timeout = aiohttp.ClientTimeout(total=timeout)
    async with session.get(url, params=params, headers=headers, timeout=aio_timeout) as resp:
        resp.raise_for_status()
        payload = await resp.json(content_type=None)

    return _parse_schedule_details(payload, default_schedule=schedule)


async def get_prices(
    session: aiohttp.ClientSession,
    base_url: str,
    schedules: list[str],
    market_type: str,
    nodes: list[str] | None = None,
    from_datetime: str | None = None,
    to_datetime: str | None = None,
    back: int | None = None,
    forward: int | None = None,
    island: str | None = None,
    offset: int | None = None,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[ScheduleDetails]:
    """Return prices across one or more schedules."""
    if not schedules or any(
        not isinstance(schedule, str) or not schedule for schedule in schedules
    ):
        raise ValidationError("schedules must contain at least one non-empty schedule")

    _validate_common_price_filters(
        market_type,
        nodes,
        from_datetime,
        to_datetime,
        back,
        forward,
        island,
        offset,
    )

    url = f"{base_url}/prices"
    params = _clean_params(
        {
            "schedules": _format_array(schedules),
            "marketType": market_type,
            "nodes": _format_array(nodes),
            "from": from_datetime,
            "to": to_datetime,
            "back": back,
            "forward": forward,
            "island": island,
            "offset": offset,
        }
    )
    aio_timeout = aiohttp.ClientTimeout(total=timeout)
    async with session.get(url, params=params, headers=headers, timeout=aio_timeout) as resp:
        resp.raise_for_status()
        payload = await resp.json(content_type=None)

    if isinstance(payload, list):
        schedules_payload = payload
    elif isinstance(payload, dict):
        schedules_payload = payload.get("schedules", [])
    else:
        raise ResponseFormatError("Invalid prices payload in API response")

    if not isinstance(schedules_payload, list):
        raise ResponseFormatError("Invalid 'schedules' payload in API response")

    return [_parse_schedule_details(item) for item in schedules_payload]
