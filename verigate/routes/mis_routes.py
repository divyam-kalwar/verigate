"""MIS & Analytics API routes for VeriGate.

Thin Blueprint that exposes Management Information System endpoints backed by
MongoDB aggregation pipelines. This initial scaffold registers `mis_bp`; the
reporting logic will be implemented later in the service and repository layers
per CLAUDE.md's layered architecture.
"""

from flask import Blueprint

mis_bp = Blueprint("mis", __name__, url_prefix="/api/v1/mis")
