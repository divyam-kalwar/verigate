"""User data access for VeriGate.

Repository for the `users` collection. It provides the lookup needed to confirm
that a sub-user (`X-User-Id`) belongs to the authenticated client. Like all
repositories it owns its own database access and exposes only domain-friendly
methods.
"""

from typing import Optional

from pymongo.collection import Collection

from ..database.mongo import get_db


class UserRepository:
    """Read access to sub-user records belonging to a client."""

    @property
    def _collection(self) -> Collection:
        return get_db()["users"]

    def find_by_client_and_user(
        self, client_id: str, user_id: str
    ) -> Optional[dict]:
        """Return the user document scoped to a specific client.

        Args:
            client_id: The authenticated client's identifier.
            user_id: The sub-user identifier from the `X-User-Id` header.

        Returns:
            The user document, or None if the user is unknown or not owned by
            the client.
        """
        return self._collection.find_one({"client_id": client_id, "user_id": user_id})
