"""Centralised configuration for VeriGate.

Configuration is sourced from environment variables. python-dotenv loads a local
`.env` file (never committed) so that the same code runs locally and in
production without hardcoded secrets. Values can also be injected directly via
the real environment, which takes precedence.
"""

import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    """Typed container for application configuration.

    Reading configuration in one place keeps secrets out of the rest of the
    codebase and makes the set of required environment variables explicit.
    """

    def __init__(self) -> None:
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
        self.MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.DATABASE_NAME: str = os.getenv("DATABASE_NAME", "verigate")
        self.ADMIN_KEY: str = os.getenv("ADMIN_KEY", "")

    def to_mapping(self) -> dict:
        """Expose configuration as a mapping suitable for Flask's config."""
        return {
            "SECRET_KEY": self.SECRET_KEY,
            "MONGO_URI": self.MONGO_URI,
            "DATABASE_NAME": self.DATABASE_NAME,
            "ADMIN_KEY": self.ADMIN_KEY,
        }
