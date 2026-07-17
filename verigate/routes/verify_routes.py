"""Verification API routes for VeriGate.

Thin Blueprint for verification endpoints. Cross-cutting request checks are
enforced in a `before_request` hook that delegates entirely to the service
layer, in order: authentication (AuthService), IP whitelisting
(IpWhitelistService), TPS limiting (RateLimiterService) and payload validation
(PayloadValidationService). The route performs no business logic; it only stores
the authenticated context on Flask `g` and translates service-raised exceptions
into the uniform JSON envelope via the global ApiException handler in app.py.

Request logging is centralised in a `teardown_request` hook that delegates to
LoggingService once per request, so EVERY outcome (success, fallback, and every
rejection path) is recorded with masked PII. The route itself contains no
log-building logic.
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
    g.request_id = f"req_{uuid.uuid4().hex[:8]}"

    auth_service = current_app.extensions.get("auth_service")
    if auth_service is None:
        raise RuntimeError("AuthService not initialized in app.extensions")

    result = auth_service.authenticate(
        api_key=request.headers.get("X-API-Key"),
        user_id=request.headers.get("X-User-Id"),
    )

    # Store client context as soon as it is known so every rejection path
    # (IP / TPS / payload) is still logged with client_id, user_id and ip.
    g.client = result.client
    g.user = result.user

    ip_service = current_app.extensions.get("ip_whitelist_service")
    if ip_service is None:
        raise RuntimeError("IpWhitelistService not initialized in app.extensions")

    # Resolve and store the client IP first so a rejected (non-whitelisted) IP
    # is still recorded in the request log for the MIS IP report.
    g.client_ip = ip_service.resolve_client_ip(request)

    ip_service.enforce(
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

    g.payload = payload


@verify_bp.post("/verify")
def verify():
    vendor_service = current_app.extensions.get("vendor_service")
    if vendor_service is None:
        raise RuntimeError("VendorService not initialized in app.extensions")

    result = vendor_service.verify(g.payload)

    g.vendor_used = result.source
    g.fallback_used = result.source == "FALLBACK"
    g.latency_ms = result.latency_ms
    g.error_code = None

    error_code = "VP2000" if result.source == "PRIMARY" else "VP2001"
    return jsonify(
        {
            "request_id": g.request_id,
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


@verify_bp.teardown_request
def log_request(exception) -> None:
    """Log every request (success or failure) via LoggingService.

    Reads the request context accumulated on `g`. For failures, the error code
    and HTTP status were stashed on `g` by the global ApiException handler.
    """
    logging_service = current_app.extensions.get("logging_service")
    if logging_service is None:
        return

    client = getattr(g, "client", None)
    payload = getattr(g, "payload", None)

    logging_service.log_request(
        request_id=getattr(g, "request_id", "unknown"),
        client_id=client["client_id"] if client else None,
        user_id=getattr(g, "user", None)["user_id"] if getattr(g, "user", None) else None,
        ip=getattr(g, "client_ip", None),
        endpoint=request.path,
        id_type=payload.get("id_type") if payload else None,
        http_status=getattr(g, "log_status", 200 if exception is None else 500),
        error_code=getattr(g, "log_error_code", getattr(g, "error_code", None)),
        vendor_used=getattr(g, "vendor_used", None),
        fallback_used=getattr(g, "fallback_used", False),
        latency_ms=getattr(g, "latency_ms", 0),
        payload=payload,
    )
