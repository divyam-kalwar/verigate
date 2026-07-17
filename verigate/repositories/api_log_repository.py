"""API log data access for VeriGate.

Repository for the `api_logs` collection. Per CLAUDE.md all MongoDB access lives
in repositories and the service layer owns business logic, so this module only
performs inserts and index creation. The required indexes
(`client_id + created_at`, `error_code`) are created here so MIS aggregation
pipelines can use them later.
"""

from typing import Any, Dict, List

from pymongo.collection import Collection
from pymongo.database import Database

from ..database.mongo import get_db


class ApiLogRepository:
    """Write access to the `api_logs` collection."""

    def insert(self, document: Dict[str, Any]) -> None:
        """Insert a single API log document.

        Args:
            document: The fully-built log document produced by LoggingService.
        """
        self._collection.insert_one(document)

    def ensure_indexes(self) -> List[str]:
        """Create the required indexes if missing.

        Returns:
            The list of created index names.
        """
        self._collection.create_index(
            [("client_id", 1), ("created_at", 1)], name="client_id_created_at"
        )
        self._collection.create_index([("error_code", 1)], name="error_code")
        return ["client_id_created_at", "error_code"]

    @property
    def _collection(self) -> Collection:
        return get_db()["api_logs"]
