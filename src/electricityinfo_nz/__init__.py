"""Electricity Info NZ Market Prices API client."""

from .client import MarketPricesClient
from .exceptions import AuthenticationError, MarketPricesAPIError, NotFoundError, RateLimitError, ValidationError

__version__ = "0.1.0"

__all__ = [
    "MarketPricesClient",
    "MarketPricesAPIError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
]
