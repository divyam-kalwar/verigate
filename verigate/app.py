"""VeriGate application entrypoint.

This module implements the Flask Application Factory pattern. `create_app`
builds and configures the Flask application, wires up configuration, initialises
the MongoDB connection and registers all Blueprints. The module-level `app`
instance is kept for simple WSGI / `flask run` usage, while `create_app` is the
preferred, configurable entry point (e.g. for tests and multiple app instances).
"""

import os

from flask import Flask

from config import Config
from database.mongo import init_mongo
from routes import register_blueprints


def create_app(config: "Config | None" = None) -> Flask:
    """Create and configure the VeriGate Flask application.

    Args:
        config: Optional pre-built Config instance. When omitted, a new Config
            is constructed from environment variables (loaded via python-dotenv
            in config.py).

    Returns:
        A fully configured Flask application instance.
    """
    app = Flask(__name__)

    app_config = config or Config()
    app.config.from_mapping(app_config.to_mapping())

    init_mongo(app)

    register_blueprints(app)

    @app.get("/health")
    def health() -> dict:
        """Liveness probe used by load balancers and orchestrators."""
        return {"status": "healthy", "application": "VeriGate"}

    return app


app = create_app()
if __name__ == '__main__':
    app.run(debug=True)