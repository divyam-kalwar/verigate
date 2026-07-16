"""Verification API routes for VeriGate.

Thin Blueprint for verification endpoints. Authentication is enforced here via a
`before_request` hook that delegates entirely to AuthService — the route layer
performs no business logic, it only translates an AuthResult into a JSON error
envelope (ErrorCodes.INVALID_API_KEY) when authentication fails. Later steps
(IP whitelisting, TPS limiting, vendor fallback, logging) will be layered in
the same way.
"""

import uuid

from flask import Blueprint, abort, current_app, g, request

from verigate.exceptions.error_codes import ErrorCodes, HttpStatus

verify_bp = Blueprint("verify", __name__, url_prefix="/api/v1")


@verify_bp.before_request
def require_auth() -> None:
    """Authenticate every request to this blueprint.

    Delegates to the already-instantiated AuthService stored in the Flask app's
    extensions. On failure, aborts with a uniform error envelope using the
    standard ErrorCodes.INVALID_API_KEY code. On success the authenticated
    client_id/user_id are stored on Flask `g` for downstream handlers.
    """
    auth_service = current_app.extensions.get("auth_service")
    if auth_service is None:
        # This should never happen if the app is set up correctly via create_app()
        raise RuntimeError("AuthService not initialized in app.extensions")

    result = auth_service.authenticate(
        api_key=request.headers.get("X-API-Key"),
        user_id=request.headers.get("X-User-Id"),
    )

    if not result.success:
        error_code = result.error_code or ErrorCodes.INVALID_API_KEY
        status = result.http_status or HttpStatus.UNAUTHORIZED
        response = current_app.response_class(
            response={
                "request_id": f"req_{uuid.uuid4().hex[:8]}",
                "status": "FAILED",
                "error_code": error_code,
                "message": "Missing or invalid API key",
            },
            status=status,
            mimetype="application/json",
        )
        abort(response)

    g.client_id = result.client_id
    g.user_id = result.user_id
