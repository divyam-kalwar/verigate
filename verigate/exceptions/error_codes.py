"""Centralised error-code registry for VeriGate.

Every VP-prefixed code that can appear in an API response is defined here as a
class attribute of ErrorCodes. Using a single class means:

- IDE auto-complete works everywhere.
- Changing a code value requires only one line change.
- Typo-safe: if you misspell `ErrorCodes.INVALID_AP_KEY`, Python raises an
  AttributeError instead of silently returning a wrong string.

HTTP status codes that pair with each error code are grouped in HttpStatus so
that routes and services stay consistent without magic numbers.

Usage:
    from verigate.exceptions.error_codes import ErrorCodes, HttpStatus

    return AuthResult(
        success=False,
        error_code=ErrorCodes.INVALID_API_KEY,
        http_status=HttpStatus.UNAUTHORIZED,
    )
"""


class ErrorCodes:
    """Standard VeriGate application error codes (VP-prefix).

    | Code   | HTTP | Meaning                                           |
    |--------|------|---------------------------------------------------|
    | VP2000 | 200  | Verified via primary vendor                       |
    | VP2001 | 200  | Verified via fallback vendor                      |
    | VP2002 | 200  | Processed, not verified (not found/name mismatch) |
    | VP4001 | 401  | Missing or invalid API key                        |
    | VP4003 | 403  | Source IP not whitelisted                         |
    | VP4022 | 422  | Request payload validation failed                 |
    | VP4029 | 429  | Client TPS limit exceeded                         |
    | VP5001 | 502  | Primary and fallback vendor both failed           |
    | VP5000 | 500  | Unhandled internal error                          |
    """

    # ── 2xx — success ────────────────────────────────────────────────────────
    VERIFIED_PRIMARY: str = "VP2000"
    VERIFIED_FALLBACK: str = "VP2001"
    NOT_VERIFIED: str = "VP2002"

    # ── 4xx — client errors ───────────────────────────────────────────────────
    INVALID_API_KEY: str = "VP4001"
    INVALID_IP: str = "VP4003"
    VALIDATION_FAILED: str = "VP4022"
    TPS_LIMIT_EXCEEDED: str = "VP4029"

    # ── 5xx — server / vendor errors ─────────────────────────────────────────
    VENDOR_ALL_FAILED: str = "VP5001"
    INTERNAL_ERROR: str = "VP5000"


class HttpStatus:
    """HTTP status codes paired with VeriGate error codes.

    Keeping these constants alongside ErrorCodes avoids magic numbers in routes
    and services and makes the pairing explicit.
    """

    OK: int = 200
    UNAUTHORIZED: int = 401
    FORBIDDEN: int = 403
    UNPROCESSABLE: int = 422
    TOO_MANY_REQUESTS: int = 429
    BAD_GATEWAY: int = 502
    INTERNAL_SERVER_ERROR: int = 500
