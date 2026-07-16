"""Authentication service for VeriGate.

Owns all API-key authentication and sub-user validation logic. It depends on
repositories for data access and returns the authenticated context on success.
On failure it raises a custom ApiException subclass, which the global Flask
error handler converts into a uniform JSON response.
"""

from dataclasses import dataclass
from typing import Optional

from ..exceptions.api_exception import InvalidApiException
from ..repositories.client_repository import ClientRepository
from ..repositories.user_repository import UserRepository


@dataclass
class AuthResult:
    """Authenticated request context.

    Attributes:
        client_id: The authenticated client identifier.
        user_id: The validated sub-user identifier.
        client: The full client document loaded during authentication. It is
            carried forward so later steps (e.g. IP whitelisting) can reuse the
            data without querying MongoDB again.
        user: The full user document loaded during authentication.
    """

    client_id: str
    user_id: str
    client: dict
    user: dict


class AuthService:
    """Validates API keys and sub-user association for incoming requests."""

    def __init__(
        self,
        client_repository: ClientRepository,
        user_repository: UserRepository,
    ) -> None:
        self._clients = client_repository
        self._users = user_repository

    def authenticate(
        self, api_key: Optional[str], user_id: Optional[str]
    ) -> AuthResult:
        """Authenticate a request from its API key and sub-user id.

        Raises:
            InvalidApiKeyException: If the API key is missing/invalid, or the
                user id is missing/does not belong to the authenticated client.
        """
        if not api_key:
            raise InvalidApiException()

        client = self._clients.find_by_api_key(api_key)
        if client is None:
            raise InvalidApiException()

        if not user_id:
            raise InvalidApiException()

        user = self._users.find_by_client_and_user(client["client_id"], user_id)
        if user is None:
            raise InvalidApiException()

        return AuthResult(
            client_id=client["client_id"],
            user_id=user_id,
            client=client,
            user=user,
        )
