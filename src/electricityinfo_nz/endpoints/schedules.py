from typing import Any, Dict, List
import requests

from ..models import Schedule


def list_schedules(session: requests.Session, base_url: str) -> List[Schedule]:
    url = f"{base_url}/schedules"
    resp = session.get(url)
    resp.raise_for_status()
    items = resp.json()
    return [
        Schedule(
            schedule=item.get("schedule", ""),
            run_type=item.get("runType"),
            market_type=item.get("marketType"),
        )
        for item in items
    ]
