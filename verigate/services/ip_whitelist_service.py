"""IP whitelisting service for VeriGate.

Owns all IP-whitelisting logic for a request (CLAUDE.md: business logic belongs in
services, routes stay thin). It does NOT query MongoDB — the authenticated client
document is passed in from the authentication step, so the IP check reuses data
already loaded and performs zero extra database reads.

Client IP resolution follows the assignment rules:
    * Prefer the first entry of `X-Forwarded-For` (the original client behind a
      proxy/load balancer).
    * Fall back to `request.remote_addr` when that header is absent.
The first IP of `X-Forwarded-For` is used because, in the standard proxy chain,
the leftmost address is the originating client; downstream proxies append to the
right. (In production this header is only trusted behind a trusted LB/ALB.)
"""

from typing import List, Optional

from flask import Request

from ..exceptions.api_exception import IpNotWhitelistedException


class IpWhitelistService:
    """Validates that a request's source IP is whitelisted for its client."""

    def resolve_client_ip(self, request: Request) -> str:
        """Extract the originating client IP from the request.

        Args:
            request: The active Flask request.

        Returns:
            The resolved client IP string.
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP; the remainder are intermediate proxies.
            return forwarded.split(",")[0].strip()
        return request.remote_addr or ""

    def enforce(
        self, request: Request, client_id: str, whitelisted_ips: List[str]
    ) -> str:
        """Ensure the request IP is in the client's whitelist.

        Args:
            request: The active Flask request.
            client_id: The authenticated client identifier (for the error
                message and audit context).
            whitelisted_ips: The client's whitelisted IP list, already loaded
                during authentication.

        Returns:
            The resolved client IP (so callers can log/audit it).

        Raises:
            IpNotWhitelistedException: If the resolved IP is not whitelisted
                (maps to VP4003 / HTTP 403).
        """
        client_ip = self.resolve_client_ip(request)
        if client_ip not in whitelisted_ips:
            raise IpNotWhitelistedException(ip_address=client_ip, client_id=client_id)
        return client_ip
