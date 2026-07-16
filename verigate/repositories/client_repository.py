"""Client data access for VeriGate.

Repository for the `clients` collection. Per CLAUDE.md, all MongoDB access lives
in repositories; services and routes never touch the database directly. Keeping
this thin data-access object makes it trivial to unit-test the auth service by
mocking the repository rather than the database.
"""

from typing import Optional

from pymongo.collection import Collection

from ..database.mongo import get_db


class ClientRepository:
    """Read-only access to client records used for API-key authentication."""

    @property
    def _collection(self) -> Collection:
        return get_db()["clients"]

    def find_by_api_key(self, api_key: str) -> Optional[dict]:
        """Return the client document matching the given API key.

        Args:
            api_key: The raw API key sent in the `X-API-Key` header.

        Returns:
            The client document, or None if no active client matches.
        """
        return self._collection.find_one({"api_key": api_key, "status": "active"})
