"""A dependency-free MCP stdio server for the negative-claim gate.

The product sits between an agent and its tools, which is an MCP server's job
description. This is that server: an agent about to conclude "no results were
found, so there are none" routes the claim through here first.

No SDK dependency. The package has no runtime dependencies and that is a
deliberate property, not an accident: a deterministic evaluator that pulls in a
transitive dependency tree is harder to audit and easier to break. A tools-only
stdio server is a small JSON-RPC surface, so it is implemented directly.

Two protocol generations are served from one implementation. Revision
`2026-07-28` removed the `initialize` handshake and made every request carry its
own protocol version, and it requires `server/discover`. Earlier revisions
require `initialize`. Both paths are answered, because a server that only spoke
the newest revision would be unreachable from most clients in use.

Nothing here consults the wall clock, the network, the filesystem, the
environment, or any mutable global state. `evaluated_at` remains a required
input on every request, exactly as it is in the library: a gate that reads the
clock cannot be replayed, and a decision that cannot be replayed is not
evidence. stdout carries protocol frames only; diagnostics go to stderr.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Callable, Mapping, TextIO

from .certificates import EvidenceCertificate
from .errors import ModelValidationError, public_validation_error
from .gate import NegativeClaimRequest, evaluate_negative_claim
from .models import (
    EVIDENCE_STATE_INTERPRETATIONS,
    SCHEMA_VERSION_COMPOSED,
    SCHEMA_VERSION_SINGLE_SOURCE,
)
from .profiles import (
    ProfileRegistrySnapshot,
    ProfileTrustSelection,
    TrustedProfileContext,
)
from .remedy import DisclosureLevel, derive_remedy, derive_remedy_from_certificate

MCP_SERVER_NAME = "evidence-state-io"

#: Newest first.  A client's requested version is echoed back when it is one of
#: these; otherwise the newest is offered and the client decides.
SUPPORTED_PROTOCOL_VERSIONS: tuple[str, ...] = (
    "2026-07-28",
    "2025-11-25",
    "2025-06-18",
    "2025-03-26",
)
LATEST_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]

#: The tool list is a pure function of the code, so it is cacheable for a long
#: time.  It contains nothing caller-specific, hence a public scope.
_TOOL_LIST_TTL_MS = 3_600_000

_JSONRPC_PARSE_ERROR = -32700
_JSONRPC_INVALID_REQUEST = -32600
_JSONRPC_METHOD_NOT_FOUND = -32601
_JSONRPC_INVALID_PARAMS = -32602

_ENVELOPE_DESCRIPTION = (
    "The evidence envelope. Must declare schema_version "
    f"('{SCHEMA_VERSION_SINGLE_SOURCE}' for one source, "
    f"'{SCHEMA_VERSION_COMPOSED}' for several corroborating sources), the "
    "observed state, the query scope, coverage evidence, the matched count, "
    "the observation time, and one observation per declared source."
)

_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "request": {
            "type": "object",
            "description": (
                "A complete negative-claim request: subject, mode, evaluated_at, "
                "optional policy, and envelope. " + _ENVELOPE_DESCRIPTION
            ),
        },
        "registry_snapshot": {
            "type": "object",
            "description": (
                "The relying application's governed profile registry snapshot. "
                "Supplied separately from the request on purpose: the producer "
                "names which profile it used, and the relying application "
                "decides which profiles it trusts. Omitting it means no "
                "governed profile is resolved and the claim is assessed "
                "without one."
            ),
        },
        "trust_selection": {
            "type": "object",
            "description": (
                "The relying application's trust selection over that snapshot. "
                "Required whenever registry_snapshot is supplied."
            ),
        },
    },
    "required": ["request"],
    "additionalProperties": False,
}


def _tool_definitions() -> list[dict[str, Any]]:
    """Return the tools in a fixed order.

    Deterministic ordering is required by the newest revision for client-side
    caching, and it is what lets a recorded session be replayed byte for byte.
    """

    explain_schema = json.loads(json.dumps(_REQUEST_SCHEMA))
    explain_schema["properties"]["disclosure"] = {
        "type": "string",
        "enum": [level.value for level in DisclosureLevel],
        "description": (
            "CONSTRAINT_ONLY (default) names the failing constraint without "
            "the governed value behind it. WITH_GOVERNED_VALUES adds those "
            "values and records in the remedy that returning it to the result "
            "producer supplies what a self-consistent fabrication would need."
        ),
    }
    explain_schema["properties"]["certificate"] = {
        "type": "object",
        "description": (
            "A rejection certificate to explain instead of a request. The "
            "certificate already binds its request and trusted context, so no "
            "registry or trust selection is needed. Mutually exclusive with "
            "'request'."
        ),
    }
    explain_schema["required"] = []

    return [
        {
            "name": "assess_negative_claim",
            "title": "Assess a scoped negative claim",
            "description": (
                "Decide whether declared evidence supports a scoped negative "
                "claim. Call this before concluding that something does not "
                "exist because a tool returned nothing: an empty result is not "
                "evidence of absence. Returns PERMIT_SCOPED_NEGATIVE with a "
                "qualified claim naming the scope and coverage the conclusion "
                "is conditional on, or REJECT_NEGATIVE with ordered reason "
                "codes. A rejection never establishes that the opposite is "
                "true. Absolute or universal negatives are never supported."
            ),
            "inputSchema": _REQUEST_SCHEMA,
        },
        {
            "name": "explain_rejection",
            "title": "Explain what would make a rejection assessable",
            "description": (
                "Turn a rejection into the conditions that would have to "
                "become true, one per material reason, each classified as "
                "await source state, obtain a fresh observation, complete "
                "enumeration, obtain a missing declaration, resolve source "
                "availability, use the governed scope, resolve governance "
                "trust, or UNSATISFIABLE. Conditions describe the world and "
                "the evidence; they never instruct you to edit a request "
                "field, and editing one to obtain a permit is fabrication. On "
                "a composed claim each condition names the sources it was "
                "raised for."
            ),
            "inputSchema": explain_schema,
        },
        {
            "name": "describe_evidence_requirements",
            "title": "Describe what an assessable envelope must carry",
            "description": (
                "Return the evidence states and their meanings, what an "
                "envelope must declare for a negative claim to be assessable "
                "at all, and the boundary of what a permit does and does not "
                "establish. Call this first when you do not yet know what "
                "evidence to gather."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    ]


def _context(arguments: Mapping[str, Any]) -> TrustedProfileContext | None:
    snapshot = arguments.get("registry_snapshot")
    trust = arguments.get("trust_selection")
    if snapshot is None and trust is None:
        return None
    if snapshot is None or trust is None:
        raise ModelValidationError(
            "registry_snapshot and trust_selection must be supplied together; "
            "a snapshot with no trust selection pins nothing, and a trust "
            "selection with no snapshot resolves nothing"
        )
    return TrustedProfileContext(
        snapshot=ProfileRegistrySnapshot.from_dict(snapshot),
        trust_selection=ProfileTrustSelection.from_dict(trust),
    )


def _assess(arguments: Mapping[str, Any]) -> dict[str, Any]:
    request = NegativeClaimRequest.from_dict(arguments["request"])
    return evaluate_negative_claim(request, _context(arguments)).to_dict()


def _explain(arguments: Mapping[str, Any]) -> dict[str, Any]:
    disclosure = DisclosureLevel(arguments.get("disclosure", DisclosureLevel.CONSTRAINT_ONLY.value))
    certificate = arguments.get("certificate")
    if certificate is not None:
        if "request" in arguments:
            raise ModelValidationError(
                "supply either a certificate or a request, not both; a "
                "certificate already binds the request it records"
            )
        return derive_remedy_from_certificate(
            EvidenceCertificate.from_dict(certificate),
            disclosure=disclosure,
        ).to_dict()
    if "request" not in arguments:
        raise ModelValidationError("explain_rejection requires a request or a certificate")
    request = NegativeClaimRequest.from_dict(arguments["request"])
    context = _context(arguments)
    decision = evaluate_negative_claim(request, context)
    return derive_remedy(decision, request, context, disclosure=disclosure).to_dict()


def _describe(_arguments: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "evidence_states": {
            state.value: interpretation
            for state, interpretation in EVIDENCE_STATE_INTERPRETATIONS.items()
        },
        "schema_versions": {
            SCHEMA_VERSION_SINGLE_SOURCE: "One required source.",
            SCHEMA_VERSION_COMPOSED: (
                "Up to four required sources under a declared CORROBORATION "
                "mode, each carrying its own coverage, state, match count, and "
                "observation time. Corroborated coverage composes by maximum "
                "and never by sum, and disagreement composes to CONTRADICTORY "
                "rather than being resolved by counting."
            ),
        },
        "an_assessable_request_must_declare": [
            "subject, and mode SCOPED — an absolute or universal negative is never supported",
            "evaluated_at, because the gate never reads a clock",
            "query scope: target, predicate, authorization boundary and context, "
            "time interval, exclusions, and one requirement per source",
            "coverage evidence: units examined against a declared denominator, "
            "pagination and partition completion, continuation state, and "
            "whether the run timed out, was interrupted, or was permission-limited",
            "matched_count, and a state consistent with it",
            "observed_at, and one source observation per declared source",
            "a finality horizon per required source, and the index state the observation reflects",
        ],
        "a_permit_does_not_establish": [
            "that the subject does not exist outside the declared scope",
            "that any declared fact is true; the gate does not authenticate sources",
            "that the source was complete, only that it declared coverage meeting the policy",
            "authorization to act; a decision is not a permission",
        ],
        "a_rejection_does_not_establish": [
            "that the positive opposite is true",
        ],
        "if_you_do_not_have_this_evidence": (
            "Say that absence was not established, and say what was actually "
            "observed. Do not assert absence, and do not edit a request to "
            "obtain a permit: the conditions in a remedy describe the world, "
            "not fields to change."
        ),
    }


_TOOLS: dict[str, Callable[[Mapping[str, Any]], dict[str, Any]]] = {
    "assess_negative_claim": _assess,
    "explain_rejection": _explain,
    "describe_evidence_requirements": _describe,
}


def _server_identity() -> dict[str, Any]:
    from . import __version__

    return {"name": MCP_SERVER_NAME, "version": __version__}


def _negotiated_version(requested: Any) -> str:
    if isinstance(requested, str) and requested in SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return LATEST_PROTOCOL_VERSION


def _tool_result(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "resultType": "complete",
        "content": [{"type": "text", "text": text}],
        "structuredContent": payload,
        "isError": is_error,
    }


def _handle(method: str, params: Mapping[str, Any]) -> dict[str, Any]:
    if method == "server/discover":
        return {
            "resultType": "complete",
            "protocolVersions": list(SUPPORTED_PROTOCOL_VERSIONS),
            "capabilities": {"tools": {}},
            "serverInfo": _server_identity(),
        }
    if method == "initialize":
        return {
            "resultType": "complete",
            "protocolVersion": _negotiated_version(params.get("protocolVersion")),
            "capabilities": {"tools": {}},
            "serverInfo": _server_identity(),
        }
    if method == "ping":
        return {"resultType": "complete"}
    if method == "tools/list":
        return {
            "resultType": "complete",
            "tools": _tool_definitions(),
            "ttlMs": _TOOL_LIST_TTL_MS,
            "cacheScope": "public",
        }
    if method == "tools/call":
        name = params.get("name")
        if not isinstance(name, str) or name not in _TOOLS:
            raise _MethodError(_JSONRPC_INVALID_PARAMS, f"unknown tool: {name!r}")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, Mapping):
            raise _MethodError(_JSONRPC_INVALID_PARAMS, "tool arguments must be an object")
        try:
            return _tool_result(_TOOLS[name](arguments))
        except Exception as exc:  # noqa: BLE001 - surfaced to the caller as a tool error
            # A refusal is the product working, so it is returned as a tool
            # error the model can read and act on, never as a transport fault.
            return _tool_result(public_validation_error(exc), is_error=True)
    raise _MethodError(_JSONRPC_METHOD_NOT_FOUND, f"unsupported method: {method!r}")


class _MethodError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_message(raw: str) -> dict[str, Any] | None:
    """Handle one JSON-RPC frame, returning the response or None for a notification.

    Pure: the same frame always produces the same response.
    """

    try:
        message = json.loads(raw)
    except json.JSONDecodeError:
        return _error(None, _JSONRPC_PARSE_ERROR, "invalid JSON")
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _error(None, _JSONRPC_INVALID_REQUEST, "not a JSON-RPC 2.0 message")
    method = message.get("method")
    if not isinstance(method, str):
        return _error(message.get("id"), _JSONRPC_INVALID_REQUEST, "missing method")
    params = message.get("params") or {}
    if not isinstance(params, Mapping):
        return _error(message.get("id"), _JSONRPC_INVALID_PARAMS, "params must be an object")

    if "id" not in message:
        # A notification. `notifications/initialized` is the only one older
        # clients send to a tools-only server; anything else is ignored rather
        # than answered, because a notification must never draw a response.
        return None
    try:
        return {"jsonrpc": "2.0", "id": message["id"], "result": _handle(method, params)}
    except _MethodError as exc:
        return _error(message["id"], exc.code, exc.message)


def serve(stdin: TextIO | None = None, stdout: TextIO | None = None) -> int:
    """Serve newline-delimited JSON-RPC frames until stdin closes."""

    source = sys.stdin if stdin is None else stdin
    sink = sys.stdout if stdout is None else stdout
    for raw in source:
        line = raw.strip()
        if not line:
            continue
        response = handle_message(line)
        if response is None:
            continue
        sink.write(json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n")
        sink.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments and arguments[0] in {"-h", "--help"}:
        sys.stderr.write(
            "evidence-state-mcp: MCP stdio server for the negative-claim gate.\n"
            "Reads newline-delimited JSON-RPC 2.0 on stdin, writes responses on stdout.\n"
            "No network, no clock, no configuration. Point an MCP client at this command.\n"
        )
        return 0
    if arguments:
        sys.stderr.write(f"unexpected arguments: {' '.join(arguments)}\n")
        return 2
    return serve()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
