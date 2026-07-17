"""Request logging service for VeriGate.

Owns all request-logging logic (CLAUDE.md: business logic belongs in services,
routes stay thin). It builds the log document, masks PII and stores SHA-256
hashes instead of raw values, stamps a UTC timestamp, and persists via
ApiLogRepository. The repository performs the actual MongoDB insert; this service
never touches the database directly.

PII policy (assignment + CLAUDE.md "Never log raw PII"):
    * name and id_number are never stored in clear text.
    * We store a masked form (last 4 characters) for human-readable auditing and
      a SHA-256 hash of the original value for exact-match lookups. Raw values
      are dropped before persistence.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..repositories.api_log_repository import ApiLogRepository
from ..utils.hashing import sha256_hash


class LoggingService:
    """Builds and persists API request log documents with masked PII."""

    def __init__(self, repository: ApiLogRepository) -> None:
        self._repository = repository

    def log_request(
        self,
        request_id: str,
        client_id: Optional[str],
        user_id: Optional[str],
        ip: Optional[str],
        endpoint: str,
        id_type: Optional[str],
        http_status: int,
        error_code: Optional[str],
        vendor_used: Optional[str],
        fallback_used: bool,
        latency_ms: int,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist a single request log entry.

        Args:
            request_id: Correlation id shared with the JSON response.
            client_id: Authenticated client id (None if auth failed).
            user_id: Authenticated sub-user id (None if auth failed).
            ip: Resolved client IP (None if not yet resolved).
            endpoint: Request path (e.g. "/api/v1/verify").
            id_type: Verification id type from payload (None if not available).
            http_status: Final HTTP status of the response.
            error_code: Standard VP error code on failure (None on success).
            vendor_used: "PRIMARY"/"FALLBACK" on success (None on failure).
            fallback_used: Whether the fallback vendor served the request.
            latency_ms: Request latency in milliseconds.
            payload: Parsed request body, used only to mask PII (name/id_number).
        """
        document = {
            "request_id": request_id,
            "client_id": client_id,
            "user_id": user_id,
            "ip": ip,
            "endpoint": endpoint,
            "id_type": id_type,
            "http_status": http_status,
            "error_code": error_code,
            "vendor_used": vendor_used,
            "fallback_used": fallback_used,
            "latency_ms": latency_ms,
            "created_at": datetime.now(timezone.utc),
        }

        if payload:
            document["name"] = self.mask_name(payload.get("name"))
            document["name_hash"] = self.sha256_hash(payload.get("name", ""))
            document["id_number"] = self.mask_id_number(payload.get("id_number"))
            document["id_number_hash"] = self.sha256_hash(payload.get("id_number", ""))

        self._repository.insert(document)

    @staticmethod
    def mask_name(name: Optional[str]) -> Optional[str]:
        """Mask a person's name, keeping only the last 4 characters.

        Args:
            name: The raw name, or None.

        Returns:
            Masked form (e.g. "XXXX Sharma") or None when input is missing.
        """
        if not name:
            return None
        if len(name) <= 4:
            return "X" * len(name)
        return "X" * (len(name) - 4) + name[-4:]

    @staticmethod
    def mask_id_number(id_number: Optional[str]) -> Optional[str]:
        """Mask an ID number, keeping only the last 4 characters.

        Args:
            id_number: The raw id number, or None.

        Returns:
            Masked form (e.g. "XXXXE1234F") or None when input is missing.
        """
        if not id_number:
            return None
        if len(id_number) <= 4:
            return "X" * len(id_number)
        return "X" * (len(id_number) - 4) + id_number[-4:]

    @staticmethod
    def sha256_hash(value: str) -> str:
        """Return the SHA-256 hex digest of `value` (via utils.hashing)."""
        return sha256_hash(value)
