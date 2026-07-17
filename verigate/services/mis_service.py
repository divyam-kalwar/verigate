"""MIS/Analytics service for VeriGate.

Thin service layer for Management Information System reports. Per CLAUDE.md the
aggregation logic lives in the repository, so this service does NOT build
pipelines — it only forwards calls to ApiLogRepository and returns the already
shaped result documents. Keeping it pass-through means routes stay thin and the
data-access logic remains testable in one place.
"""

from typing import Any, Dict, List, Optional

from ..repositories.api_log_repository import ApiLogRepository


class MisService:
    """Serves MIS reports by delegating to the API log repository."""

    def __init__(self, repository: ApiLogRepository) -> None:
        self._repository = repository

    def usage_report(
        self,
        group_by: str = "client",
        client_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Client/user/day usage breakdown."""
        return self._repository.get_usage_report(group_by, client_id, from_date, to_date)

    def error_distribution(
        self,
        client_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Error-code distribution."""
        return self._repository.get_error_distribution(client_id, from_date, to_date)

    def tps_metrics(
        self,
        client_id: Optional[str] = None,
        date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Peak/avg TPS and p95 latency for a client on a day."""
        return self._repository.get_tps_metrics(client_id, date)

    def fallback_metrics(
        self,
        client_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Per-client fallback usage and ratio."""
        return self._repository.get_fallback_metrics(client_id, from_date, to_date)

    def ip_report(
        self,
        client_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Per-IP activity and blocking report."""
        return self._repository.get_ip_report(client_id, from_date, to_date)
