"""CSV export service for VeriGate MIS reports.

Reusable utility that converts structured data (list of dicts) into CSV format.
This service does NOT call the repository — it receives data from MisService and
handles flattening of Mongo _id fields plus CSV formatting.
"""

import csv
import io
from typing import Any, Dict, List, Optional


class CsvExportService:
    """Convert structured MIS data into a CSV string ready for download."""

    def generate(
        self,
        headers: List[str],
        data: List[Dict[str, Any]],
        column_map: Optional[Dict[str, str]] = None,
    ) -> str:
        """Produce a CSV string with the given headers and rows.

        Args:
            headers: Ordered list of column names for the CSV header row.
            data: List of dicts to serialize. Each dict should contain the
                source keys. If empty, only the header row is returned.
            column_map: Optional mapping from source dict keys to output
                header names. When provided, values are looked up using the
                source key but the header row uses the mapped display name.

        Returns:
            A CSV string with headers and data rows.
        """
        column_map = column_map or {}
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=headers,
            extrasaction="ignore",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for row in data:
            mapped_row = {}
            for header in headers:
                source_key = column_map.get(header, header)
                mapped_row[header] = row.get(source_key, "")
            writer.writerow(mapped_row)
        return output.getvalue()

    def export_usage(
        self,
        data: List[Dict[str, Any]],
        group_by: str = "client",
    ) -> str:
        """Flatten usage report data and return CSV.

        Args:
            data: Raw aggregation results from MisService.usage_report().
            group_by: The grouping used in the aggregation (client, user, day).

        Returns:
            CSV string with flattened usage columns.
        """
        if group_by == "user":
            headers = ["client_id", "user_id", "total", "success", "success_via_fallback", "not_verified", "failed", "avg_latency_ms"]
            column_map = {h: h for h in headers}
            flattened = [
                {
                    "client_id": row.get("_id", {}).get("client_id", ""),
                    "user_id": row.get("_id", {}).get("user_id", ""),
                    **{k: row.get(k, 0) for k in ["total", "success", "success_via_fallback", "not_verified", "failed", "avg_latency_ms"]},
                }
                for row in data
            ]
        elif group_by == "day":
            headers = ["day", "total", "success", "success_via_fallback", "not_verified", "failed", "avg_latency_ms"]
            column_map = {h: h for h in headers}
            flattened = [
                {
                    "day": row.get("_id", ""),
                    **{k: row.get(k, 0) for k in ["total", "success", "success_via_fallback", "not_verified", "failed", "avg_latency_ms"]},
                }
                for row in data
            ]
        else:
            headers = ["client_id", "total", "success", "success_via_fallback", "not_verified", "failed", "avg_latency_ms"]
            column_map = {h: h for h in headers}
            flattened = [
                {
                    "client_id": row.get("_id", ""),
                    **{k: row.get(k, 0) for k in ["total", "success", "success_via_fallback", "not_verified", "failed", "avg_latency_ms"]},
                }
                for row in data
            ]
        return self.generate(headers, flattened, column_map)

    def export_errors(self, data: List[Dict[str, Any]]) -> str:
        """Flatten error distribution data and return CSV.

        Args:
            data: Raw aggregation results from MisService.error_distribution().

        Returns:
            CSV string with error_code distribution columns.
        """
        headers = ["client_id", "error_code", "count"]
        column_map = {h: h for h in headers}
        flattened = [
            {
                "client_id": row.get("_id", {}).get("client_id", ""),
                "error_code": row.get("_id", {}).get("error_code", ""),
                "count": row.get("count", 0),
            }
            for row in data
        ]
        return self.generate(headers, flattened, column_map)

    def export_tps(self, data: List[Dict[str, Any]]) -> str:
        """Flatten TPS metrics data and return CSV.

        Args:
            data: Raw aggregation results from MisService.tps_metrics().

        Returns:
            CSV string with TPS metric columns.
        """
        headers = ["client_id", "peak_tps", "peak_second", "avg_tps", "p95_latency_ms"]
        column_map = {h: h for h in headers}
        return self.generate(headers, data, column_map)

    def export_fallback(self, data: List[Dict[str, Any]]) -> str:
        """Flatten fallback metrics data and return CSV.

        Args:
            data: Raw aggregation results from MisService.fallback_metrics().

        Returns:
            CSV string with fallback ratio columns.
        """
        headers = ["client_id", "total_success", "served_by_fallback", "fallback_ratio_pct"]
        column_map = {h: h for h in headers}
        return self.generate(headers, data, column_map)

    def export_ips(self, data: List[Dict[str, Any]]) -> str:
        """Flatten IP report data and return CSV.

        Args:
            data: Raw aggregation results from MisService.ip_report().

        Returns:
            CSV string with IP activity columns.
        """
        headers = ["client_id", "ip", "total_hits", "blocked_hits", "whitelisted"]
        column_map = {h: h for h in headers}
        return self.generate(headers, data, column_map)
