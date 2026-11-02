SCHEDULE_NAMES: dict[str, str] = {
    "Final": "Final settled prices",
    "Interim": "Interim prices",
    "NRSL": "Non-responsive long schedule",
    "NRSS": "Non-responsive short schedule",
    "PRSL": "Price-responsive long schedule",
    "PRSS": "Price-responsive short schedule",
    "RTD": "Real-time dispatch",
    "WDS": "Weekly dispatch schedule",
}


def resolve_schedule_name(schedule: str) -> str:
    """Return a human-readable schedule name for a WITS schedule code."""
    return SCHEDULE_NAMES.get(schedule, schedule)
