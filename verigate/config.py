"""Centralised configuration for VeriGate.

Configuration is sourced from environment variables. python-dotenv loads a local
`.env` file (never committed) so that the same code runs locally and in
production without hardcoded secrets. Values can also be injected directly via
the real environment, which takes precedence.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(dotenv_path=Path(__file__).with_name(".env"))


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
        self.VENDOR_A_FAILURE_RATE: float = float(os.getenv("VENDOR_A_FAILURE_RATE", "0.2"))
        self.VENDOR_A_TIMEOUT_RATE: float = float(os.getenv("VENDOR_A_TIMEOUT_RATE", "0.1"))
        self.VENDOR_MIN_LATENCY_MS: int = int(os.getenv("VENDOR_MIN_LATENCY_MS", "100"))
        self.VENDOR_MAX_LATENCY_MS: int = int(os.getenv("VENDOR_MAX_LATENCY_MS", "800"))
        self.VENDOR_B_FAILURE_RATE: float = float(os.getenv("VENDOR_B_FAILURE_RATE", "0.0"))

    def to_mapping(self) -> dict:
        """Expose configuration as a mapping suitable for Flask's config."""
        return {
            "SECRET_KEY": self.SECRET_KEY,
            "MONGO_URI": self.MONGO_URI,
            "DATABASE_NAME": self.DATABASE_NAME,
            "ADMIN_KEY": self.ADMIN_KEY,
            "VENDOR_A_FAILURE_RATE": self.VENDOR_A_FAILURE_RATE,
            "VENDOR_A_TIMEOUT_RATE": self.VENDOR_A_TIMEOUT_RATE,
            "VENDOR_MIN_LATENCY_MS": self.VENDOR_MIN_LATENCY_MS,
            "VENDOR_MAX_LATENCY_MS": self.VENDOR_MAX_LATENCY_MS,
            "VENDOR_B_FAILURE_RATE": self.VENDOR_B_FAILURE_RATE,
        }
