"""Service layer composition root for VeriGate.

Provides factory helpers that wire services together with their repositories.
Centralising construction here keeps routes thin (they ask for a ready-made
service instead of assembling dependencies) and gives a single place to swap
implementations — e.g. replace the in-memory/PyMongo repositories with mocked
ones in tests.
"""

from .auth_service import AuthService
from .ip_whitelist_service import IpWhitelistService
from .rate_limiter_service import RateLimiterService
from .payload_validation_service import PayloadValidationService
from .vendor_service import VendorService, VendorA, VendorB
from ..repositories.client_repository import ClientRepository
from ..repositories.user_repository import UserRepository
from ..config import Config


def build_auth_service() -> AuthService:
    """Construct an AuthService with its default repositories."""
    return AuthService(
        client_repository=ClientRepository(),
        user_repository=UserRepository(),
    )


def build_ip_whitelist_service() -> IpWhitelistService:
    """Construct an IpWhitelistService (stateless, no dependencies)."""
    return IpWhitelistService()


def build_rate_limiter_service() -> RateLimiterService:
    """Construct the in-memory RateLimiterService (single shared instance)."""
    return RateLimiterService()


def build_payload_validation_service() -> PayloadValidationService:
    """Construct a PayloadValidationService (stateless, no dependencies)."""
    return PayloadValidationService()


def build_vendor_service() -> VendorService:
    """Construct VendorService with Vendor A/B configured from Config."""
    config = Config()
    vendor_a = VendorA(
        failure_rate=config.VENDOR_A_FAILURE_RATE,
        timeout_rate=config.VENDOR_A_TIMEOUT_RATE,
        min_latency_ms=config.VENDOR_MIN_LATENCY_MS,
        max_latency_ms=config.VENDOR_MAX_LATENCY_MS,
    )
    vendor_b = VendorB(
        failure_rate=config.VENDOR_B_FAILURE_RATE,
        min_latency_ms=config.VENDOR_MIN_LATENCY_MS,
        max_latency_ms=config.VENDOR_MAX_LATENCY_MS,
    )
    return VendorService(vendor_a=vendor_a, vendor_b=vendor_b)
