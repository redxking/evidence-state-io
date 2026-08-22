"""Small, versioned canonical-JSON and integrity-digest boundary.

This digest detects a changed payload only when the verifier retains a trusted
expected digest.  It is not a signature, proof of origin, or tamper-proof
custody mechanism.
"""

from __future__ import annotations

from hashlib import sha256
from hmac import compare_digest
import json
from typing import Any

from .models import ModelValidationError


CANONICALIZATION_PROFILE = "esio-canonical-json-0.1"
DIGEST_ALGORITHM = "sha256"


def canonical_json_bytes(value: Any) -> bytes:
    """Encode supported JSON values using the project's P0 canonical profile."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (OverflowError, TypeError, UnicodeError, ValueError) as exc:
        raise ModelValidationError(
            "canonical JSON input contains an unsupported value"
        ) from exc


def canonical_digest(value: Any) -> str:
    return f"{DIGEST_ALGORITHM}:{sha256(canonical_json_bytes(value)).hexdigest()}"


def verify_canonical_digest(value: Any, expected: str) -> bool:
    """Compare a recomputed digest with a previously trusted expected value."""

    if type(expected) is not str:
        return False
    return compare_digest(canonical_digest(value), expected)
