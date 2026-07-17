"""Custom API exceptions for consistent JSON error responses."""

from verigate.exceptions.error_codes import ErrorCodes, HttpStatus


class ApiException(Exception):
    """Base exception for all API errors returned to clients."""

    def __init__(self, error_code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status = status


class InvalidApiException(ApiException):
    """Raised when API-key or sub-user authentication fails."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCodes.INVALID_API_KEY,
            message="Missing fields or invalid API key.",
            status=HttpStatus.UNAUTHORIZED,
        )


class InvalidAdminKeyException(ApiException):
    """Raised when MIS admin authentication fails."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCodes.INVALID_API_KEY,
            message="Missing or invalid admin key.",
            status=HttpStatus.UNAUTHORIZED,
        )


class IpNotWhitelistedException(ApiException):
    """Raised when the request IP is not allowed for the client."""

    def __init__(self, ip_address: str, client_id: str) -> None:
        super().__init__(
            error_code=ErrorCodes.INVALID_IP,
            message=f"Access denied. Source IP '{ip_address}' is not authorized for client '{client_id}'.",
            status=HttpStatus.FORBIDDEN,
        )


class PayloadValidationException(ApiException):
    """Raised when the verification request payload is invalid."""

    def __init__(self, message: str = "Request payload validation failed.") -> None:
        super().__init__(
            error_code=ErrorCodes.VALIDATION_FAILED,
            message=message,
            status=HttpStatus.UNPROCESSABLE,
        )


class RateLimitExceededException(ApiException):
    """Raised when a client exceeds its configured TPS limit."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCodes.TPS_LIMIT_EXCEEDED,
            message="Client TPS limit exceeded.",
            status=HttpStatus.TOO_MANY_REQUESTS,
        )


class VendorFailureException(ApiException):
    """Raised when all verification vendors fail."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCodes.VENDOR_ALL_FAILED,
            message="Primary and fallback vendors failed.",
            status=HttpStatus.BAD_GATEWAY,
        )
