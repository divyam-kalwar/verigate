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
from ..repositories.client_repository import ClientRepository
from ..repositories.user_repository import UserRepository


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
