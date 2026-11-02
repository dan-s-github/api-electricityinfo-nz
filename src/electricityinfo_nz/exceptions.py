class MarketPricesAPIError(Exception):
    """Base exception for the Market Prices client."""


class AuthenticationError(MarketPricesAPIError):
    """Raised when authentication fails."""


class NotFoundError(MarketPricesAPIError):
    """Raised when a requested resource is not found."""


class ValidationError(MarketPricesAPIError):
    """Raised when the API returns a validation error (HTTP 400)."""


class RateLimitError(MarketPricesAPIError):
    """Raised when rate limits are exceeded."""


class ResponseFormatError(MarketPricesAPIError):
    """Raised when the API response cannot be parsed safely."""


class TransportError(MarketPricesAPIError):
    """Raised when a network or request transport error occurs."""
