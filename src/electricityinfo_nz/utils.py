from datetime import datetime
from typing import Any, Dict

from .models import PriceDetail


def parse_datetime(value: str) -> datetime:
    # Expect ISO 8601; fall back to naive parse.
    return datetime.fromisoformat(value)


def parse_price_detail(item: Dict[str, Any]) -> PriceDetail:
    return PriceDetail(
        trading_datetime=parse_datetime(item["tradingDateTime"]),
        trading_period=int(item["tradingPeriod"]),
        node=item["node"],
        price=item.get("price"),
        price6s=item.get("price6s"),
        price60s=item.get("price60s"),
        schedule=item.get("schedule"),
        run_type=item.get("runType"),
        last_run_time=parse_datetime(item["lastRunTime"]) if item.get("lastRunTime") else None,
        reserve_node=item.get("reserveNode"),
    )
