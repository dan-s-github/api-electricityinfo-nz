from typing import Dict, List, Optional
import requests

from ..models import ScheduleDetails
from ..utils import parse_price_detail


QueryParams = Dict[str, object]


def _clean_params(params: QueryParams) -> QueryParams:
    return {k: v for k, v in params.items() if v is not None}


def _format_array(values: Optional[List[str]]) -> Optional[str]:
    if values is None:
        return None
    return ",".join(values)


def get_schedule_prices(
    session: requests.Session,
    base_url: str,
    schedule: str,
    market_type: str,
    nodes: Optional[List[str]] = None,
    from_datetime: Optional[str] = None,
    to_datetime: Optional[str] = None,
    back: Optional[int] = None,
    forward: Optional[int] = None,
    island: Optional[str] = None,
    offset: Optional[int] = None,
) -> ScheduleDetails:
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
    resp = session.get(url, params=params)
    resp.raise_for_status()
    payload = resp.json()
    prices = [parse_price_detail(item) for item in payload.get("prices", [])]
    return ScheduleDetails(schedule=payload.get("schedule", schedule), prices=prices)


def get_prices(
    session: requests.Session,
    base_url: str,
    schedules: List[str],
    market_type: str,
    nodes: Optional[List[str]] = None,
    from_datetime: Optional[str] = None,
    to_datetime: Optional[str] = None,
    back: Optional[int] = None,
    forward: Optional[int] = None,
    island: Optional[str] = None,
    offset: Optional[int] = None,
) -> List[ScheduleDetails]:
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
    resp = session.get(url, params=params)
    resp.raise_for_status()
    payload = resp.json()
    # API can return either {"schedules": [...]} or directly [...]
    if isinstance(payload, list):
        schedules_payload = payload
    elif isinstance(payload, dict):
        schedules_payload = payload.get("schedules", [])
    else:
        schedules_payload = []
    return [
        ScheduleDetails(
            schedule=item.get("schedule", ""),
            prices=[parse_price_detail(p) for p in item.get("prices", [])],
        )
        for item in schedules_payload
    ]
