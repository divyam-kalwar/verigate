"""Payload validation service for VeriGate.

Owns all request-body validation for the verification endpoint (CLAUDE.md:
business logic belongs in services, routes stay thin). It validates ONLY what the
assignment specifies and nothing more — no PAN/DL/Voter-ID format checks, no
client_ref_id format rules, since the assignment does not define them.

Validation rules applied (fail-fast on the first failure, no error aggregation):
    * Each required field must be present: client_ref_id, id_type, id_number,
      name.
    * Each required field must be a string.
    * Each required field must be non-empty after stripping whitespace.
    * id_type must be one of: PAN, DL, VOTER (exact spelling from the
      assignment).

On the first violation it raises PayloadValidationException (VP4022 / 422).
"""

from typing import Any, List, Set

from ..exceptions.api_exception import PayloadValidationException

REQUIRED_FIELDS: List[str] = ["client_ref_id", "id_type", "id_number", "name"]
ALLOWED_ID_TYPES: Set[str] = {"PAN", "DL", "VOTER"}


class PayloadValidationService:
    """Validates verification request payloads against assignment rules."""

    def validate_verify_request(self, payload: Any) -> None:
        """Validate the verification request payload.

        Args:
            payload: The parsed JSON body (typically a dict). May be None if the
                request had no valid JSON body.

        Raises:
            PayloadValidationException: On the first validation failure
                (VP4022 / HTTP 422).
        """
        if not isinstance(payload, dict):
            raise PayloadValidationException("Request body must be a JSON object.")

        for field in REQUIRED_FIELDS:
            if field not in payload:
                raise PayloadValidationException(
                    f"Missing required field: '{field}'."
                )

            value = payload[field]
            if not isinstance(value, str):
                raise PayloadValidationException(
                    f"Field '{field}' must be a string."
                )

            if value.strip() == "":
                raise PayloadValidationException(
                    f"Field '{field}' must not be empty."
                )

        if payload["id_type"] not in ALLOWED_ID_TYPES:
            raise PayloadValidationException(
                f"Field '{payload[id_type]}' must be one of: "
                f"{', '.join(sorted(ALLOWED_ID_TYPES))}."
            )
