"""Service layer composition root for VeriGate.

Provides factory helpers that wire services together with their repositories.
Centralising construction here keeps routes thin (they ask for a ready-made
service instead of assembling dependencies) and gives a single place to swap
implementations — e.g. replace the in-memory/PyMongo repositories with mocked
ones in tests.
"""

from .auth_service import AuthService
from ..repositories.client_repository import ClientRepository
from ..repositories.user_repository import UserRepository


def build_auth_service() -> AuthService:
    """Construct an AuthService with its default repositories."""
    return AuthService(
        client_repository=ClientRepository(),
        user_repository=UserRepository(),
    )
