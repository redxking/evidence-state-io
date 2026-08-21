from __future__ import annotations

from copy import deepcopy
from typing import Any

from evidence_state_io.emptybench import seed_case_dicts
from evidence_state_io.gate import NegativeClaimRequest


def request_dict() -> dict[str, Any]:
    return deepcopy(seed_case_dicts()[0]["request"])


def request(**changes: Any) -> NegativeClaimRequest:
    data = request_dict()
    for key, value in changes.items():
        data[key] = value
    return NegativeClaimRequest.from_dict(data)
