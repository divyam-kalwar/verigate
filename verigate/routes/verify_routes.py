"""Verification API routes for VeriGate.

Thin Blueprint that exposes verification endpoints. This initial scaffold
registers `verify_bp`; the actual verification logic (auth, IP whitelisting,
TPS limiting, vendor fallback, logging) will be implemented later in the
service and repository layers per CLAUDE.md's layered architecture.
"""

from flask import Blueprint

verify_bp = Blueprint("verify", __name__, url_prefix="/api/v1")
