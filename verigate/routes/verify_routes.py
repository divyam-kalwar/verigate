"""Verification API routes for VeriGate.

Thin Blueprint for verification endpoints. Authentication is enforced here via
a `before_request` hook that delegates entirely to AuthService. Authentication
failures are raised as ApiException subclasses and converted into a uniform JSON
response by the global Flask error handler. Later steps (IP whitelisting, TPS
limiting, vendor fallback, logging) can use the same exception path.
"""

from flask import Blueprint, current_app, g, request

verify_bp = Blueprint("verify", __name__, url_prefix="/api/v1")


@verify_bp.before_request
def require_auth() -> None:
    """Authenticate every request to this blueprint."""
    auth_service = current_app.extensions.get("auth_service")
    if auth_service is None:
        raise RuntimeError("AuthService not initialized in app.extensions")

    result = auth_service.authenticate(
        api_key=request.headers.get("X-API-Key"),
        user_id=request.headers.get("X-User-Id"),
    )

    g.client_id = result.client_id
    g.user_id = result.user_id


@verify_bp.post("/verify")
def verify():
    return {
        "message": "Authentication successful",
        "client_id": g.client_id,
        "user_id": g.user_id,
    }, 200
