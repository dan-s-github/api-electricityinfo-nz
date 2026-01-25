from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Schedule:
    schedule: str
    run_type: Optional[str] = None
    market_type: Optional[str] = None


@dataclass
class PriceDetail:
    trading_datetime: datetime
    trading_period: int
    node: str
    price: Optional[float] = None
    price6s: Optional[float] = None
    price60s: Optional[float] = None
    schedule: Optional[str] = None
    run_type: Optional[str] = None
    last_run_time: Optional[datetime] = None
    reserve_node: Optional[str] = None


@dataclass
class ScheduleDetails:
    schedule: str
    prices: List[PriceDetail]
