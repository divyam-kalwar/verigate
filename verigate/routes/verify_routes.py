"""Verification API routes for VeriGate.

Thin Blueprint for verification endpoints. Cross-cutting request checks are
enforced in a `before_request` hook that delegates entirely to the service
layer — authentication (AuthService) and IP whitelisting (IpWhitelistService).
The route performs no business logic; it only stores the authenticated context
on Flask `g` and translates service-raised exceptions into the uniform JSON
envelope via the global ApiException handler in app.py.
"""

from flask import Blueprint, current_app, g, request

verify_bp = Blueprint("verify", __name__, url_prefix="/api/v1")


@verify_bp.before_request
def enforce_access_control() -> None:
    """Authenticate the request, then enforce IP whitelisting.

    Both steps run through services. The authenticated client document (already
    loaded by AuthService) is reused for the IP check so no extra MongoDB query
    is made. On any failure a service raises an ApiException subclass, which the
    global error handler converts to the standard error envelope.
    """
    auth_service = current_app.extensions.get("auth_service")
    if auth_service is None:
        raise RuntimeError("AuthService not initialized in app.extensions")

    result = auth_service.authenticate(
        api_key=request.headers.get("X-API-Key"),
        user_id=request.headers.get("X-User-Id"),
    )

    ip_service = current_app.extensions.get("ip_whitelist_service")
    if ip_service is None:
        raise RuntimeError("IpWhitelistService not initialized in app.extensions")

    client_ip = ip_service.enforce(
        request=request,
        client_id=result.client_id,
        whitelisted_ips=result.client["whitelisted_ips"],
    )

    g.request_context = {
        "client": result.client,
        "user": result.user,
        "client_ip": client_ip,
    }


@verify_bp.post("/verify")
def verify():
    return {
        "message": "Access granted",
        "client_id": g.request_context["client"]["client_id"],
        "user_id": g.request_context["user"]["user_id"],
    }, 200
