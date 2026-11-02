from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict

from .schedule_names import resolve_schedule_name


class NodeInfo(TypedDict):
    """A node entry returned by the nodes endpoint."""

    node: str
    island: str


@dataclass
class Schedule:
    """Metadata describing an available schedule."""

    schedule: str
    run_type: str | None = None
    market_type: str | None = None
    schedule_name: str = field(init=False)

    def __post_init__(self) -> None:
        """Populate the human-readable schedule name from the raw schedule code."""
        self.schedule_name = resolve_schedule_name(self.schedule)


@dataclass
class PriceDetail:
    """Price information for a single trading period and node."""

    trading_datetime: datetime
    trading_period: int
    node: str
    price: float | None = None
    price6s: float | None = None
    price60s: float | None = None
    schedule: str | None = None
    run_type: str | None = None
    last_run_time: datetime | None = None
    reserve_node: str | None = None

    @property
    def schedule_name(self) -> str | None:
        """Return a human-readable schedule name when the schedule code is present."""
        if self.schedule is None:
            return None
        return resolve_schedule_name(self.schedule)


@dataclass
class ScheduleDetails:
    """A schedule paired with its returned price entries."""

    schedule: str
    prices: list[PriceDetail]
    schedule_name: str = field(init=False)

    def __post_init__(self) -> None:
        """Populate the human-readable schedule name from the raw schedule code."""
        self.schedule_name = resolve_schedule_name(self.schedule)
