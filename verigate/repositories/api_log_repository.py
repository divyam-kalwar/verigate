"""API log data access for VeriGate.

Repository for the `api_logs` collection. Per CLAUDE.md all MongoDB access lives
in repositories and the service layer owns business logic. This module performs
inserts, index creation, and the MIS aggregation pipelines. The required indexes
(`client_id + created_at`, `error_code`) make the date/client range `$match`
stages and the error_distribution grouping efficient.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from pymongo.collection import Collection
from pymongo.database import Database

from ..database.mongo import get_db
from ..exceptions.error_codes import ErrorCodes

# Error codes that represent a successful verification (used by MIS reports).
SUCCESS_CODES = {
    ErrorCodes.VERIFIED_PRIMARY,
    ErrorCodes.VERIFIED_FALLBACK,
    ErrorCodes.NOT_VERIFIED,
}


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO date (YYYY-MM-DD) into a UTC datetime at midnight.

    Args:
        value: The date string, or None.

    Returns:
        A timezone-aware UTC datetime, or None when value is missing/invalid.
    """
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _date_match(from_date: Optional[str], to_date: Optional[str]) -> Dict[str, Any]:
    """Build a `created_at` range filter from optional from/to ISO dates.

    `from` is inclusive at 00:00 UTC; `to` is inclusive through 23:59:59.999
    (i.e. the following day, exclusive). Returns an empty filter if neither is
    provided.
    """
    match: Dict[str, Any] = {}
    start = _parse_date(from_date)
    end = _parse_date(to_date)
    if start is None and end is None:
        return match
    condition: Dict[str, Any] = {}
    if start is not None:
        condition["$gte"] = start
    if end is not None:
        condition["$lt"] = end + timedelta(days=1)
    match["created_at"] = condition
    return match


def _client_match(client_id: Optional[str]) -> Dict[str, Any]:
    """Build a `client_id` equality filter when a client is specified."""
    if client_id:
        return {"client_id": client_id}
    return {}


class ApiLogRepository:
    """Read/write access to the `api_logs` collection."""

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

    # ── MIS aggregation pipelines ─────────────────────────────────────────────
    # Each method owns its pipeline and returns already-shaped result documents.
    # The service layer simply forwards these; no aggregation lives in services.

    def get_usage_report(
        self,
        group_by: str = "client",
        client_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Aggregate request usage grouped by client, user, or day.

        Pipeline:
            1. $match  - optional client_id + date range.
            2. $addFields - derive booleans: is_success (VP200x), is_fallback
               (fallback_used true), is_not_verified (VP2002), is_failed (any
               error code that is not a success code).
            3. $group  - by the requested key; sum the boolean flags into totals
               and average latency.
            4. $sort   - by total descending.
        """
        match: Dict[str, Any] = {**_date_match(from_date, to_date), **_client_match(client_id)}

        if group_by == "user":
            group_id = {"client_id": "$client_id", "user_id": "$user_id"}
        elif group_by == "day":
            group_id = {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}
        else:
            group_id = "$client_id"

        pipeline = [
            {"$match": match},
            {
                "$addFields": {
                    "is_success": {"$in": ["$error_code", list(SUCCESS_CODES)]},
                    "is_fallback": {"$eq": ["$fallback_used", True]},
                    "is_not_verified": {"$eq": ["$error_code", "VP2002"]},
                    "is_failed": {
                        "$and": [
                            {"$ne": ["$error_code", None]},
                            {"$not": {"$in": ["$error_code", list(SUCCESS_CODES)]}},
                        ]
                    },
                }
            },
            {
                "$group": {
                    "_id": group_id,
                    "total": {"$sum": 1},
                    "success": {"$sum": {"$cond": ["$is_success", 1, 0]}},
                    "success_via_fallback": {
                        "$sum": {"$cond": [{"$and": ["$is_success", "$is_fallback"]}, 1, 0]}
                    },
                    "not_verified": {"$sum": {"$cond": ["$is_not_verified", 1, 0]}},
                    "failed": {"$sum": {"$cond": ["$is_failed", 1, 0]}},
                    "avg_latency_ms": {"$avg": "$latency_ms"},
                }
            },
            {"$sort": {"total": -1}},
        ]
        return list(self._collection.aggregate(pipeline))

    def get_error_distribution(
        self,
        client_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Count requests per error code, optionally per client.

        Pipeline:
            1. $match - date range + optional client_id + only docs that have an
               error_code (excludes successful requests).
            2. $group - by {client_id, error_code}, count occurrences.
            3. $sort  - by count descending.
        """
        match: Dict[str, Any] = {
            **_date_match(from_date, to_date),
            **_client_match(client_id),
            "error_code": {"$nin": list(SUCCESS_CODES) + [None]},
        }
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {"client_id": "$client_id", "error_code": "$error_code"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1}},
        ]
        return list(self._collection.aggregate(pipeline))

    def get_tps_metrics(
        self,
        client_id: Optional[str] = None,
        date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Compute peak TPS, average TPS and p95 latency for a client on a day.

        Pipeline:
            1. $match - client_id + the given day's range (from/to default to
               `date` when provided).
            2. $group - by second ($dateTrunc) counting requests and collecting
               latencies.
            3. $group - at client level: peak_tps = max(per-second count),
               total = sum(counts), seconds = number of distinct seconds, and
               keep the latencies array for p95.
        The peak_second and p95 are resolved in Python from the single aggregated
        document (no large in-Python loops).
        """
        from_date = date
        to_date = date
        match: Dict[str, Any] = {
            **_date_match(from_date, to_date),
            **_client_match(client_id),
        }
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {"$dateTrunc": {"date": "$created_at", "unit": "second"}},
                    "count": {"$sum": 1},
                    "latencies": {"$push": "$latency_ms"},
                }
            },
            {"$sort": {"count": -1, "_id": 1}},
            {
                "$group": {
                    "_id": None,
                    "peak_tps": {"$first": "$count"},
                    "peak_second": {"$first": "$_id"},
                    "total": {"$sum": "$count"},
                    "seconds": {"$sum": 1},
                    "all_latencies": {"$push": "$latencies"},
                }
            },
        ]
        docs = list(self._collection.aggregate(pipeline))
        results: List[Dict[str, Any]] = []
        for doc in docs:
            latencies = [l for group in doc.get("all_latencies", []) for l in group]
            p95 = _percentile(latencies, 95) if latencies else 0
            avg_tps = round(doc["total"] / doc["seconds"], 2) if doc["seconds"] else 0
            results.append(
                {
                    "client_id": client_id,
                    "peak_tps": doc["peak_tps"],
                    "peak_second": _format_utc_second(doc.get("peak_second")),
                    "avg_tps": avg_tps,
                    "p95_latency_ms": p95,
                }
            )
        return results

    def get_fallback_metrics(
        self,
        client_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Per-client fallback usage and ratio.

        Pipeline:
            1. $match - date range + optional client_id.
            2. $group - by client_id: total_success (successful requests) and
               served_by_fallback (requests where fallback_used is true).
            3. $project - fallback_ratio_pct, guarding against divide-by-zero.
        """
        match: Dict[str, Any] = {**_date_match(from_date, to_date), **_client_match(client_id)}
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$client_id",
                    "total_success": {
                        "$sum": {"$cond": [{"$in": ["$error_code", list(SUCCESS_CODES)]}, 1, 0]}
                    },
                    "served_by_fallback": {"$sum": {"$cond": ["$fallback_used", 1, 0]}},
                }
            },
            {
                "$project": {
                    "client_id": "$_id",
                    "total_success": 1,
                    "served_by_fallback": 1,
                    "fallback_ratio_pct": {
                        "$cond": [
                            {"$eq": ["$total_success", 0]},
                            0,
                            {
                                "$round": [
                                    {"$multiply": [{"$divide": ["$served_by_fallback", "$total_success"]}, 100]},
                                    2,
                                ]
                            },
                        ]
                    },
                }
            },
        ]
        return list(self._collection.aggregate(pipeline))

    def get_ip_report(
        self,
        client_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Per-IP activity and blocking for one or all clients.

        Pipeline:
            1. $match - date range + optional client_id.
            2. $group - by {client_id, ip}: total_hits and blocked_hits (requests
               whose error_code is VP4003).
            3. $project - whitelisted = (never blocked). An IP that was ever
               blocked is surfaced as non-whitelisted (the security signal the
               assignment asks for); true membership lives in `clients`.
        """
        match: Dict[str, Any] = {**_date_match(from_date, to_date), **_client_match(client_id)}
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {"client_id": "$client_id", "ip": "$ip"},
                    "total_hits": {"$sum": 1},
                    "blocked_hits": {"$sum": {"$cond": [{"$eq": ["$error_code", "VP4003"]}, 1, 0]}},
                }
            },
            {
                "$project": {
                    "client_id": "$_id.client_id",
                    "ip": "$_id.ip",
                    "total_hits": 1,
                    "blocked_hits": 1,
                    "whitelisted": {"$eq": ["$blocked_hits", 0]},
                }
            },
            {"$sort": {"blocked_hits": -1, "total_hits": -1}},
        ]
        return list(self._collection.aggregate(pipeline))

    @property
    def _collection(self) -> Collection:
        return get_db()["api_logs"]


def _percentile(values: List[float], percentile: int) -> float:
    """Return the given percentile of a list using linear interpolation.

    Args:
        values: Numeric samples (unsorted is fine).
        percentile: Integer percentile 0-100.

    Returns:
        The interpolated percentile value.
    """
    if not values:
        return 0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (percentile / 100) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def _format_utc_second(value: Optional[datetime]) -> Optional[str]:
    """Format a Mongo datetime as an ISO UTC second with Z suffix."""
    if value is None:
        return None
    return value.replace(microsecond=0).isoformat().replace("+00:00", "") + "Z"
