"""Blueprint registration for VeriGate.

This package groups all route Blueprints. Keeping registration in one place
means `create_app` only needs a single call and new Blueprints are wired up
consistently. Routes stay thin; business logic lives in services/repositories.
"""

from flask import Flask

from verigate.routes.mis_routes import mis_bp
from verigate.routes.verify_routes import verify_bp


def register_blueprints(app: Flask) -> None:
    """Register all application Blueprints on the given Flask app."""
    app.register_blueprint(verify_bp)
    app.register_blueprint(mis_bp)
