"""Hashing utilities for VeriGate.

Centralises cryptographic hashing so PII is never stored in raw form. Keeping the
implementation in one place avoids duplicated or inconsistent hashing across the
codebase (used by logging/PII masking today).
"""

import hashlib


def sha256_hash(value: str) -> str:
    """Return the hex SHA-256 digest of `value`.

    Args:
        value: The string to hash (e.g. a raw id_number or name).

    Returns:
        Lowercase hex digest.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
