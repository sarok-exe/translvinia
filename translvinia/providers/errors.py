class RequestError(Exception):
    """Exception raised when request fails."""


class RequestTimeout(RequestError):
    """Request exceeded the configured deadline."""


class NetworkError(RequestError):
    """DNS/connect/TLS/socket failure before a usable response."""


class ProviderError(Exception):
    """Exception raised when provider fails."""


class RateLimitError(ProviderError):
    """Provider is rate limiting requests."""


class InvalidResponse(ProviderError):
    """Provider returned a body that cannot be parsed."""


class UnexpectedError(ProviderError):
    """Exception raised when provider fails."""


class APIKeyRequired(ProviderError):
    """Exception raised when provider fails."""


class APIKeyInvalid(ProviderError):
    """Exception raised when provider fails."""


class InvalidLangCode(ProviderError):
    """Exception raised when provider fails."""


class BatchSizeExceeded(ProviderError):
    """Exception raised when provider fails."""


class CharactersLimitExceeded(ProviderError):
    """Exception raised when provider fails."""


class ServiceLimitReached(ProviderError):
    """Exception raised when provider fails."""
