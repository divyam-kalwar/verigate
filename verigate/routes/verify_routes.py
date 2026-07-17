"""Verification API routes for VeriGate.

Thin Blueprint for verification endpoints. Cross-cutting request checks are
enforced in a `before_request` hook that delegates entirely to the service
layer, in order: authentication (AuthService), IP whitelisting
(IpWhitelistService), TPS limiting (RateLimiterService) and payload validation
(PayloadValidationService). The route performs no business logic; it only stores
the authenticated context on Flask `g` and translates service-raised exceptions
into the uniform JSON envelope via the global ApiException handler in app.py.

The /verify handler delegates the actual verification to VendorService and maps
the returned VendorResult onto the assignment's success envelope. Vendor
fallback logic stays inside VendorService; the route only does HTTP/JSON mapping.
"""

import uuid

from flask import Blueprint, current_app, g, jsonify, request

verify_bp = Blueprint("verify", __name__, url_prefix="/api/v1")


@verify_bp.before_request
def enforce_access_control() -> None:
    """Authenticate, enforce IP whitelist, TPS limit, then validate payload.

    Each step runs through a service, in order. The authenticated client document
    (already loaded by AuthService and stored on g) is reused for the IP check and
    the TPS limit, so no extra MongoDB query is made. On any failure a service
    raises an ApiException subclass, which the global error handler converts to
    the standard error envelope. Payload validation runs last, just before any
    verification/vendor logic.
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

    rate_limiter = current_app.extensions.get("rate_limiter_service")
    if rate_limiter is None:
        raise RuntimeError("RateLimiterService not initialized in app.extensions")

    rate_limiter.check(
        client_id=result.client_id,
        tps_limit=result.client["tps_limit"],
    )

    payload_service = current_app.extensions.get("payload_validation_service")
    if payload_service is None:
        raise RuntimeError("PayloadValidationService not initialized in app.extensions")

    payload = request.get_json(silent=True)
    payload_service.validate_verify_request(payload)

    g.client = result.client
    g.user = result.user
    g.client_ip = client_ip
    g.payload = payload


@verify_bp.post("/verify")
def verify():
    vendor_service = current_app.extensions.get("vendor_service")
    if vendor_service is None:
        raise RuntimeError("VendorService not initialized in app.extensions")

    result = vendor_service.verify(g.payload)

    error_code = "VP2000" if result.source == "PRIMARY" else "VP2001"
    return jsonify(
        {
            "request_id": f"req_{uuid.uuid4().hex[:8]}",
            "status": "SUCCESS",
            "error_code": error_code,
            "data": {
                "verified": result.verified,
                "name_match_score": result.name_match_score,
                "source": result.source,
            },
            "latency_ms": result.latency_ms,
        }
    ), 200
