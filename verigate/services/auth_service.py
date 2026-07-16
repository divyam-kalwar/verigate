"""Authentication service for VeriGate.

Owns all API-key authentication and sub-user validation logic (CLAUDE.md: "Keep
all business logic inside AuthService"). It depends on the repositories for data
access and returns a small result object so routes stay thin and free of
decision-making. The service decides *what* failed (missing key, invalid key,
unknown/mismatched user) and maps it to the assignment's standard error codes,
but it does not build HTTP responses itself — that remains the route's job.
"""

from dataclasses import dataclass
from typing import Optional

from ..repositories.client_repository import ClientRepository
from ..repositories.user_repository import UserRepository
from ..exceptions.error_codes import ErrorCodes, HttpStatus


@dataclass
class AuthResult:
    """Outcome of an authentication attempt.

    Attributes:
        success: Whether the request is authenticated.
        client_id: The authenticated client id (None when not authenticated).
        user_id: The validated sub-user id (None when not authenticated).
        error_code: Standard VeriGate error code on failure (None on success).
        http_status: HTTP status to return on failure (None on success).
    """

    success: bool
    client_id: Optional[str] = None
    user_id: Optional[str] = None
    error_code: Optional[str] = None
    http_status: Optional[int] = None


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

        Flow:
            1. Both headers must be present (VP4001 if the key is missing).
            2. The key must match an active client (VP4001 if not).
            3. The user id must belong to that client (VP4001 if not).

        We intentionally reuse VP4001 ("Missing or invalid API key") for the
        missing-user case as well, because a request without a valid
        client/user context is rejected at the authentication boundary; the
        assignment also lists "Invalid User" only under testing, not as a
        separate error code. Surfacing the same code avoids leaking which
        clients exist.

        Args:
            api_key: Value of the `X-API-Key` header (may be None).
            user_id: Value of the `X-User-Id` header (may be None).

        Returns:
            An AuthResult describing success or the reason for rejection.
        """
        if not api_key:
            return AuthResult(
                success=False,
                error_code=ErrorCodes.INVALID_API_KEY,
                http_status=HttpStatus.UNAUTHORIZED,
            )

        client = self._clients.find_by_api_key(api_key)
        if client is None:
            return AuthResult(
                success=False,
                error_code=ErrorCodes.INVALID_API_KEY,
                http_status=HttpStatus.UNAUTHORIZED,
            )

        if not user_id:
            return AuthResult(
                success=False,
                error_code=ErrorCodes.INVALID_API_KEY,
                http_status=HttpStatus.UNAUTHORIZED,
            )

        user = self._users.find_by_client_and_user(client["client_id"], user_id)
        if user is None:
            return AuthResult(
                success=False,
                error_code=ErrorCodes.INVALID_API_KEY,
                http_status=HttpStatus.UNAUTHORIZED,
            )

        return AuthResult(
            success=True,
            client_id=client["client_id"],
            user_id=user_id,
        )
