"""Vendor simulation and fallback for VeriGate.

Implements the two simulated verification vendors and the fallback logic
(CLAUDE.md: business logic belongs in services, routes stay thin; vendors are
simulated internally and never call external APIs).

Components
----------
* VendorA  - primary vendor. Simulates random latency, a configurable failure
             rate and a configurable timeout rate (both via environment
             variables, read through Config). A failure or timeout is reported
             as an internal VendorError so the caller can fall back.
* VendorB  - fallback vendor. Simulates latency and succeeds by default; its
             own failure rate is configurable (default 0) so tests and future
             tuning can force it to fail.
* VendorService - owns the fallback flow: call VendorA; on any failure call
             VendorB; if both fail, raise VendorFailureException (VP5001).

Why an internal VendorError (not a public ApiException):
    A single vendor failing is NOT a client-facing error by itself — it is an
    implementation detail of the fallback. Only "both vendors failed" becomes a
    public VP5001. So vendor-internal failures are signalled with a private
    exception that VendorService catches, keeping the public error surface
    limited to what the assignment defines.

Latency and timeout handling:
    Latency is simulated as a returned number, not by sleeping. That keeps load
    tests fast while still producing realistic latency_ms values in responses
    and logs. A timeout is simulated by raising VendorError based on the
    configured timeout rate.
"""

import random
from dataclasses import dataclass
from typing import Any, Mapping


class VendorError(Exception):
    """Internal signal that a vendor attempt failed or timed out.

    Not exposed to clients; VendorService translates a final VendorError into
    the public VendorFailureException (VP5001).
    """


@dataclass
class VendorResult:
    """Outcome of a verification attempt.

    Attributes:
        verified: Whether the identity was verified.
        name_match_score: Simulated match score (0-100).
        source: "PRIMARY" (Vendor A) or "FALLBACK" (Vendor B).
        latency_ms: Simulated round-trip latency in milliseconds.
    """

    verified: bool
    name_match_score: int
    source: str
    latency_ms: int


class VendorA:
    """Primary (simulated) verification vendor."""

    def __init__(
        self,
        failure_rate: float,
        timeout_rate: float,
        min_latency_ms: int,
        max_latency_ms: int,
    ) -> None:
        self._failure_rate = failure_rate
        self._timeout_rate = timeout_rate
        self._min_latency_ms = min_latency_ms
        self._max_latency_ms = max_latency_ms

    def verify(self, payload: Mapping[str, Any]) -> VendorResult:
        """Attempt verification via the primary vendor.

        Args:
            payload: The validated verification request body. The current
                simulation does not inspect it yet, but keeping it at the
                vendor boundary mirrors a real vendor request contract.

        Raises:
            VendorError: If the attempt fails or times out (caller falls back).
        """
        latency = random.randint(self._min_latency_ms, self._max_latency_ms)

        roll = random.random()
        if roll < self._failure_rate:
            raise VendorError("Vendor A failed.")
        if roll < self._failure_rate + self._timeout_rate:
            raise VendorError("Vendor A timed out.")

        return VendorResult(
            verified=True,
            name_match_score=random.randint(80, 99),
            source="PRIMARY",
            latency_ms=latency,
        )


class VendorB:
    """Fallback (simulated) verification vendor."""

    def __init__(
        self,
        failure_rate: float,
        min_latency_ms: int,
        max_latency_ms: int,
    ) -> None:
        self._failure_rate = failure_rate
        self._min_latency_ms = min_latency_ms
        self._max_latency_ms = max_latency_ms

    def verify(self, payload: Mapping[str, Any]) -> VendorResult:
        """Attempt verification via the fallback vendor.

        Args:
            payload: The validated verification request body. The current
                simulation does not inspect it yet, but keeping it at the
                vendor boundary mirrors a real vendor request contract.

        Raises:
            VendorError: If the attempt fails (caller escalates to VP5001).
        """
        latency = random.randint(self._min_latency_ms, self._max_latency_ms)

        if random.random() < self._failure_rate:
            raise VendorError("Vendor B failed.")

        return VendorResult(
            verified=True,
            name_match_score=random.randint(80, 99),
            source="FALLBACK",
            latency_ms=latency,
        )


class VendorService:
    """Owns vendor selection and fallback logic."""

    def __init__(self, vendor_a: VendorA, vendor_b: VendorB) -> None:
        self._vendor_a = vendor_a
        self._vendor_b = vendor_b

    def verify(self, payload: Mapping[str, Any]) -> VendorResult:
        """Verify via Vendor A, falling back to Vendor B on failure.

        Args:
            payload: The validated verification request body to send to the
                simulated vendors.

        Returns:
            A VendorResult from whichever vendor succeeded.

        Raises:
            VendorFailureException: If both vendors fail (VP5001 / HTTP 502).
        """
        try:
            return self._vendor_a.verify(payload)
        except VendorError:
            pass

        try:
            return self._vendor_b.verify(payload)
        except VendorError as exc:
            from ..exceptions.api_exception import VendorFailureException

            raise VendorFailureException() from exc
