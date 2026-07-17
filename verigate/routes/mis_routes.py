"""MIS & Analytics API routes for VeriGate.

Thin Blueprint exposing Management Information System endpoints backed by
MongoDB aggregation pipelines (CLAUDE.md: routes stay thin; aggregation logic
lives in the repository, the service is a pass-through). Each handler only reads
optional query parameters (client_id, from, to, group_by, date), delegates to
MisService, and returns the structured JSON result.
"""

from flask import Blueprint, current_app, jsonify, request

from verigate.exceptions.api_exception import InvalidAdminKeyException

mis_bp = Blueprint("mis", __name__, url_prefix="/api/v1/mis")


def _mis_service():
    service = current_app.extensions.get("mis_service")
    if service is None:
        raise RuntimeError("MisService not initialized in app.extensions")
    return service


@mis_bp.before_request
def require_admin_key() -> None:
    """Require X-Admin-Key for all MIS endpoints."""
    configured_key = current_app.config.get("ADMIN_KEY")
    if not configured_key or request.headers.get("X-Admin-Key") != configured_key:
        raise InvalidAdminKeyException()


@mis_bp.get("/usage")
def usage():
    group_by = request.args.get("group_by", "client")
    return jsonify(
        _mis_service().usage_report(
            group_by=group_by,
            client_id=request.args.get("client_id"),
            from_date=request.args.get("from"),
            to_date=request.args.get("to"),
        )
    )


@mis_bp.get("/errors")
def errors():
    return jsonify(
        _mis_service().error_distribution(
            client_id=request.args.get("client_id"),
            from_date=request.args.get("from"),
            to_date=request.args.get("to"),
        )
    )


@mis_bp.get("/tps")
def tps():
    return jsonify(
        _mis_service().tps_metrics(
            client_id=request.args.get("client_id"),
            date=request.args.get("date"),
        )
    )


@mis_bp.get("/fallback")
def fallback():
    return jsonify(
        _mis_service().fallback_metrics(
            client_id=request.args.get("client_id"),
            from_date=request.args.get("from"),
            to_date=request.args.get("to"),
        )
    )


@mis_bp.get("/ips")
def ips():
    return jsonify(
        _mis_service().ip_report(
            client_id=request.args.get("client_id"),
            from_date=request.args.get("from"),
            to_date=request.args.get("to"),
        )
    )
