from __future__ import annotations

from collections.abc import Mapping

import requests

from ..constants import DEFAULT_TIMEOUT
from ..exceptions import ResponseFormatError
from ..models import Schedule


def list_schedules(
    session: requests.Session,
    base_url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[Schedule]:
    """Return schedules available from the API."""
    url = f"{base_url}/schedules"
    resp = session.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    items = resp.json()

    if not isinstance(items, list):
        raise ResponseFormatError("Invalid schedules payload in API response")

    schedules: list[Schedule] = []
    for item in items:
        if not isinstance(item, dict):
            raise ResponseFormatError("Invalid schedule entry in API response")

        schedule = item.get("schedule")
        run_type = item.get("runType")
        market_type = item.get("marketType")
        if not isinstance(schedule, str) or not schedule:
            raise ResponseFormatError("Invalid or missing 'schedule' in API response")
        if run_type is not None and not isinstance(run_type, str):
            raise ResponseFormatError("Invalid 'runType' value in API response")
        if market_type is not None and not isinstance(market_type, str):
            raise ResponseFormatError("Invalid 'marketType' value in API response")

        schedules.append(
            Schedule(
                schedule=schedule,
                run_type=run_type,
                market_type=market_type,
            )
        )

    return schedules
