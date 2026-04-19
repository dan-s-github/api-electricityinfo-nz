"""Electricity Info NZ Market Prices API client."""

from .client import MarketPricesClient
from .exceptions import (
    AuthenticationError,
    MarketPricesAPIError,
    NotFoundError,
    RateLimitError,
    ResponseFormatError,
    TransportError,
    ValidationError,
)
from .schedule_names import resolve_schedule_name

__version__ = "1.0.0-rc.1"

__all__ = [
    "AuthenticationError",
    "MarketPricesAPIError",
    "MarketPricesClient",
    "NotFoundError",
    "RateLimitError",
    "ResponseFormatError",
    "TransportError",
    "ValidationError",
    "resolve_schedule_name",
]
