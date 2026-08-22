"""JSON command-line interface for Evidence-State I/O."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, NoReturn, Sequence, TextIO

from .certificates import (
    EvidenceCertificate,
    EvidenceOrigin,
    ImplementationIdentity,
    WorkingTreeState,
    build_evidence_certificate,
    verify_evidence_certificate,
)
from .coverage import CoveragePolicy, evaluate_coverage
from .emptybench import parse_corpus, parse_oracle, run_emptybench, run_seed_emptybench
from .errors import (
    ModelValidationError,
    ValidationErrorCode,
    public_validation_error,
)
from .gate import NegativeClaimPolicy, NegativeClaimRequest, evaluate_negative_claim
from .models import (
    MAX_INTEGER_DECIMAL_DIGITS,
    ClaimMode,
    CoverageEvidence,
    EvidenceEnvelope,
    parse_datetime,
)
from .profiles import (
    ProfileRegistrySnapshot,
    ProfileTrustSelection,
    TrustedProfileContext,
)
from .remedy import DisclosureLevel, derive_remedy, derive_remedy_from_certificate

MAX_INPUT_BYTES = 1_048_576
MAX_JSON_DEPTH = 128
MAX_JSON_NUMBER_TOKEN_CHARS = MAX_INTEGER_DECIMAL_DIGITS
PACKAGE_VERSION = "0.6.0"


class _JsonArgumentParser(argparse.ArgumentParser):
    """Route command-usage failures through the public JSON error contract."""

    def error(self, message: str) -> NoReturn:
        raise ModelValidationError(
            "command arguments are invalid",
            code=ValidationErrorCode.CLI_ARGUMENT_INVALID,
        )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ModelValidationError(
                "JSON contains a duplicate object key",
                code=ValidationErrorCode.JSON_DUPLICATE_KEY,
            )
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ModelValidationError(
        "JSON contains a non-standard numeric constant",
        code=ValidationErrorCode.JSON_NUMBER_INVALID,
    )


def _check_json_number_token(value: str) -> None:
    if len(value) > MAX_JSON_NUMBER_TOKEN_CHARS:
        raise ModelValidationError(
            "JSON numeric token exceeds the supported "
            f"{MAX_JSON_NUMBER_TOKEN_CHARS}-character limit",
            code=ValidationErrorCode.JSON_NUMBER_INVALID,
        )


def _parse_json_int(value: str) -> int:
    _check_json_number_token(value)
    try:
        return int(value)
    except ValueError as exc:
        raise ModelValidationError(
            "JSON integer could not be decoded safely",
            code=ValidationErrorCode.JSON_NUMBER_INVALID,
        ) from exc


def _parse_json_float(value: str) -> Decimal:
    _check_json_number_token(value)
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ModelValidationError(
            "JSON number could not be decoded safely",
            code=ValidationErrorCode.JSON_NUMBER_INVALID,
        ) from exc


def _strict_json_loads(text: str) -> Any:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
            parse_float=_parse_json_float,
            parse_int=_parse_json_int,
        )
    except RecursionError as exc:
        raise ModelValidationError(
            "JSON nesting exceeds the supported parser depth",
            code=ValidationErrorCode.JSON_DEPTH_EXCEEDED,
        ) from exc
    except ModelValidationError:
        raise
    except json.JSONDecodeError:
        raise
    except ValueError as exc:
        raise ModelValidationError(
            "JSON numeric token could not be decoded safely",
            code=ValidationErrorCode.JSON_NUMBER_INVALID,
        ) from exc
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise ModelValidationError(
                f"JSON nesting exceeds the supported depth of {MAX_JSON_DEPTH}",
                code=ValidationErrorCode.JSON_DEPTH_EXCEEDED,
            )
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
    return value


def _read_json(path: str, stdin: TextIO) -> Any:
    if path == "-":
        try:
            text = stdin.read(MAX_INPUT_BYTES + 1)
        except UnicodeError as exc:
            raise ModelValidationError(
                "JSON input must be valid UTF-8",
                code=ValidationErrorCode.INPUT_ENCODING_INVALID,
            ) from exc
        except (OSError, ValueError) as exc:
            raise ModelValidationError(
                "JSON input could not be read",
                code=ValidationErrorCode.INPUT_READ_FAILED,
            ) from exc
        if type(text) is not str:
            raise ModelValidationError(
                "JSON input stream must provide decoded text",
                code=ValidationErrorCode.INPUT_ENCODING_INVALID,
            )
        try:
            encoded = text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ModelValidationError(
                "JSON input must be valid UTF-8",
                code=ValidationErrorCode.INPUT_ENCODING_INVALID,
            ) from exc
        if len(encoded) > MAX_INPUT_BYTES:
            raise ModelValidationError(
                f"JSON input exceeds the {MAX_INPUT_BYTES}-byte limit",
                code=ValidationErrorCode.INPUT_SIZE_EXCEEDED,
            )
        return _strict_json_loads(text)
    raw = Path(path).read_bytes()
    if len(raw) > MAX_INPUT_BYTES:
        raise ModelValidationError(
            f"JSON input exceeds the {MAX_INPUT_BYTES}-byte limit",
            code=ValidationErrorCode.INPUT_SIZE_EXCEEDED,
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ModelValidationError(
            "JSON input must be valid UTF-8",
            code=ValidationErrorCode.INPUT_ENCODING_INVALID,
        ) from exc
    return _strict_json_loads(text)


def _write_json(value: Any, stream: TextIO, pretty: bool) -> None:
    try:
        if pretty:
            payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True)
        else:
            payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        payload.encode("utf-8")
    except (TypeError, UnicodeError, ValueError) as exc:
        raise ModelValidationError(
            "JSON output could not be encoded safely",
            code=ValidationErrorCode.OUTPUT_ENCODING_FAILED,
        ) from exc
    try:
        stream.write(payload + "\n")
    except (OSError, UnicodeError, ValueError) as exc:
        raise ModelValidationError(
            "JSON output could not be written safely",
            code=ValidationErrorCode.OUTPUT_ENCODING_FAILED,
        ) from exc


def _trusted_profile_context(
    args: argparse.Namespace,
    stdin: TextIO,
) -> TrustedProfileContext:
    if args.registry == "-" or args.trust == "-":
        raise ModelValidationError(
            "--registry and --trust must be separate files; stdin is reserved for --input",
            code=ValidationErrorCode.CLI_ARGUMENT_INVALID,
        )
    return TrustedProfileContext(
        snapshot=ProfileRegistrySnapshot.from_dict(_read_json(args.registry, stdin)),
        trust_selection=ProfileTrustSelection.from_dict(_read_json(args.trust, stdin)),
    )


def _request_input(
    data: Any,
    args: argparse.Namespace,
) -> NegativeClaimRequest:
    if isinstance(data, dict) and "envelope" in data:
        supplied_overrides = [
            name for name in ("evaluated_at", "subject", "mode") if getattr(args, name) is not None
        ]
        if supplied_overrides:
            raise ModelValidationError(
                "full request JSON cannot be combined with CLI overrides: "
                + ", ".join(f"--{name.replace('_', '-')}" for name in supplied_overrides),
                code=ValidationErrorCode.CLI_ARGUMENT_INVALID,
            )
        return NegativeClaimRequest.from_dict(data)

    if args.evaluated_at is None:
        raise ModelValidationError(
            "a bare envelope requires --evaluated-at; the CLI never falls back to wall-clock time",
            code=ValidationErrorCode.CLI_ARGUMENT_INVALID,
        )
    envelope = EvidenceEnvelope.from_dict(data)
    try:
        mode = ClaimMode(ClaimMode.SCOPED.value if args.mode is None else args.mode)
    except ValueError as exc:  # argparse choices should make this unreachable
        raise ModelValidationError(
            "--mode must be SCOPED or ABSOLUTE",
            code=ValidationErrorCode.CLI_ARGUMENT_INVALID,
        ) from exc
    request = NegativeClaimRequest(
        envelope=envelope,
        subject=("records matching the query" if args.subject is None else args.subject),
        mode=mode,
        evaluated_at=parse_datetime(args.evaluated_at, "--evaluated-at"),
        policy=NegativeClaimPolicy(),
    )
    return request


def _implementation_identity(args: argparse.Namespace) -> ImplementationIdentity:
    try:
        state = WorkingTreeState(args.working_tree_state)
    except (TypeError, ValueError) as exc:
        raise ModelValidationError(
            "--working-tree-state must be CLEAN, DIRTY, or UNBOUND",
            code=ValidationErrorCode.CLI_ARGUMENT_INVALID,
        ) from exc
    return ImplementationIdentity(
        package_name="evidence-state-io",
        package_version=PACKAGE_VERSION,
        repository_revision=args.repository_revision,
        working_tree_state=state,
    )


def _coverage_input(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ModelValidationError("coverage input must be a JSON object")
    unknown = sorted(set(data) - {"coverage", "policy"})
    if unknown:
        raise ModelValidationError(f"coverage input has unknown fields: {', '.join(unknown)}")
    evidence = CoverageEvidence.from_dict(data.get("coverage"))
    policy = CoveragePolicy.from_dict(data.get("policy"))
    return evaluate_coverage(evidence, policy).to_dict()


def build_parser() -> argparse.ArgumentParser:
    parser = _JsonArgumentParser(
        prog="evidence-state",
        description="Evaluate evidence-state envelopes without inferring global absence.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate = subparsers.add_parser(
        "evaluate", help="Evaluate one deterministic negative-claim request or envelope."
    )
    evaluate.add_argument("--input", required=True, help="JSON file, or - for stdin")
    evaluate.add_argument(
        "--registry",
        required=True,
        help="Operator-controlled profile registry snapshot JSON file",
    )
    evaluate.add_argument(
        "--trust",
        required=True,
        help="Operator-controlled profile trust-selection JSON file",
    )
    evaluate.add_argument(
        "--issued-at",
        required=True,
        help="Explicit ISO-8601 certificate issuance time; no wall-clock fallback",
    )
    evaluate.add_argument(
        "--origin",
        required=True,
        choices=[origin.value for origin in EvidenceOrigin],
        help="Descriptive evidence origin; it does not upgrade sufficiency",
    )
    evaluate.add_argument(
        "--working-tree-state",
        choices=[state.value for state in WorkingTreeState],
        default=WorkingTreeState.UNBOUND.value,
        help="Explicit implementation tree state (default: UNBOUND)",
    )
    evaluate.add_argument(
        "--repository-revision",
        default=None,
        help="Full lowercase Git revision required for CLEAN or DIRTY builds",
    )
    evaluate.add_argument(
        "--evaluated-at",
        help="ISO-8601 evaluation time; required only when --input is a bare envelope",
    )
    evaluate.add_argument(
        "--subject",
        default=None,
        help="Claim subject used only with a bare envelope",
    )
    evaluate.add_argument(
        "--mode",
        choices=[mode.value for mode in ClaimMode],
        default=None,
        help="Claim mode used only with a bare envelope",
    )
    evaluate.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    demo = subparsers.add_parser(
        "demo", help="Run the paired covered-versus-partial EmptyBench demonstration."
    )
    demo.add_argument(
        "--all",
        action="store_true",
        help="Run every built-in seed pair instead of the P0 operator pair",
    )
    demo.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    benchmark = subparsers.add_parser(
        "emptybench", help="Run a versioned EmptyBench corpus and separate oracle."
    )
    benchmark.add_argument(
        "--input", required=True, help="Versioned corpus JSON file, or - for stdin"
    )
    benchmark.add_argument(
        "--oracle",
        required=True,
        help="Separately stored versioned oracle JSON file",
    )
    benchmark.add_argument(
        "--expected-oracle-digest",
        required=True,
        help="Separately retained lowercase SHA-256 digest for the oracle",
    )
    benchmark.add_argument(
        "--registry",
        required=True,
        help="Operator-controlled profile registry snapshot JSON file",
    )
    benchmark.add_argument(
        "--trust",
        required=True,
        help="Operator-controlled profile trust-selection JSON file",
    )
    benchmark.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    explain = subparsers.add_parser(
        "explain",
        help="Explain a rejected negative claim as conditions that would have to become true.",
    )
    explain.add_argument("--input", required=True, help="JSON file, or - for stdin")
    explain.add_argument(
        "--registry",
        help="Operator-controlled profile registry snapshot JSON file; not needed for a certificate, which carries its own trusted context",
    )
    explain.add_argument(
        "--trust",
        help="Operator-controlled profile trust-selection JSON file; not needed for a certificate",
    )
    explain.add_argument(
        "--disclosure",
        choices=[level.value for level in DisclosureLevel],
        default=DisclosureLevel.CONSTRAINT_ONLY.value,
        help=(
            "Governed-value disclosure. CONSTRAINT_ONLY (default) names the failing "
            "constraint without its threshold. WITH_GOVERNED_VALUES additionally carries "
            "the governed values and is only appropriate for a caller that already holds "
            "the profile; returning it to the result producer hands that party the values "
            "it would need to construct a self-consistent fabrication."
        ),
    )
    explain.add_argument(
        "--evaluated-at",
        help="ISO-8601 evaluation time; required only when --input is a bare envelope",
    )
    explain.add_argument(
        "--subject",
        default=None,
        help="Claim subject used only with a bare envelope",
    )
    explain.add_argument(
        "--mode",
        choices=[mode.value for mode in ClaimMode],
        default=None,
        help="Claim mode used only with a bare envelope (default: SCOPED)",
    )
    explain.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    coverage = subparsers.add_parser(
        "coverage", help="Evaluate coverage evidence independently of a claim."
    )
    coverage.add_argument("--input", required=True, help="JSON file, or - for stdin")
    coverage.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    verify = subparsers.add_parser(
        "verify-certificate",
        help="Verify an unsigned certificate's independent replay and custody dimensions.",
    )
    verify.add_argument("--input", required=True, help="Certificate JSON file, or - for stdin")
    verify.add_argument(
        "--registry",
        help="Separately controlled expected registry snapshot JSON file",
    )
    verify.add_argument(
        "--trust",
        help="Separately controlled expected trust-selection JSON file",
    )
    verify.add_argument(
        "--expected-digest",
        help="Separately retained expected lowercase SHA-256 certificate digest",
    )
    verify.add_argument(
        "--relying-party-at",
        help="Explicit relying-party time for current local-reliance assessment",
    )
    verify.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    input_stream = sys.stdin if stdin is None else stdin
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr
    parser = build_parser()

    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
        if args.command == "evaluate":
            context = _trusted_profile_context(args, input_stream)
            request = _request_input(_read_json(args.input, input_stream), args)
            artifact = build_evidence_certificate(
                request,
                context,
                issued_at=parse_datetime(args.issued_at, "--issued-at"),
                origin=EvidenceOrigin(args.origin),
                implementation=_implementation_identity(args),
            )
            _write_json(artifact.to_dict(), output_stream, args.pretty)
            return 0
        if args.command == "demo":
            demo_report = run_seed_emptybench(all_cases=args.all)
            _write_json(demo_report.to_dict(), output_stream, args.pretty)
            return 0 if demo_report.all_passed else 1
        if args.command == "emptybench":
            if args.oracle == "-":
                raise ModelValidationError(
                    "--oracle must be a separate file; stdin is reserved for --input",
                    code=ValidationErrorCode.CLI_ARGUMENT_INVALID,
                )
            context = _trusted_profile_context(args, input_stream)
            corpus = parse_corpus(_read_json(args.input, input_stream))
            oracle = parse_oracle(
                _read_json(args.oracle, input_stream),
                corpus,
                expected_digest=args.expected_oracle_digest,
            )
            emptybench_report = run_emptybench(
                corpus,
                oracle,
                context,
                expected_oracle_digest=args.expected_oracle_digest,
            )
            _write_json(emptybench_report.to_dict(), output_stream, args.pretty)
            return 0 if emptybench_report.all_passed else 1
        if args.command == "explain":
            payload = _read_json(args.input, input_stream)
            disclosure = DisclosureLevel(args.disclosure)
            # A certificate is what a relying party actually holds, so accept it
            # directly rather than making the caller reconstruct the request.
            if isinstance(payload, dict) and "certificate" in payload:
                certificate_remedy = derive_remedy_from_certificate(
                    EvidenceCertificate.from_dict(payload),
                    disclosure=disclosure,
                )
                _write_json(certificate_remedy.to_dict(), output_stream, args.pretty)
                return 0
            context = _trusted_profile_context(args, input_stream)
            request = _request_input(payload, args)
            decision = evaluate_negative_claim(request, context)
            if decision.allowed:
                raise ModelValidationError(
                    "explain describes an insufficiency; this request is permitted and has "
                    "none. Use evaluate to issue its certificate.",
                    code=ValidationErrorCode.CLI_ARGUMENT_INVALID,
                )
            remedy = derive_remedy(decision, request, context, disclosure=disclosure)
            _write_json(remedy.to_dict(), output_stream, args.pretty)
            return 0
        if args.command == "coverage":
            result = _coverage_input(_read_json(args.input, input_stream))
            _write_json(result, output_stream, args.pretty)
            return 0
        if args.command == "verify-certificate":
            if (args.registry is None) != (args.trust is None):
                raise ModelValidationError(
                    "--registry and --trust must be supplied together for expected-context verification",
                    code=ValidationErrorCode.CLI_ARGUMENT_INVALID,
                )
            expected_context = (
                None if args.registry is None else _trusted_profile_context(args, input_stream)
            )
            verification = verify_evidence_certificate(
                _read_json(args.input, input_stream),
                expected_context=expected_context,
                expected_certificate_digest=args.expected_digest,
                relying_party_at=(
                    None
                    if args.relying_party_at is None
                    else parse_datetime(args.relying_party_at, "--relying-party-at")
                ),
            )
            _write_json(verification.to_dict(), output_stream, args.pretty)
            checks = (
                verification.structural_support,
                verification.certificate_digest_integrity,
                verification.embedded_digest_integrity,
                verification.deterministic_replay,
                verification.expected_context_match is not False,
                verification.expected_certificate_digest_match is not False,
                verification.current_local_reliance_eligible is not False,
            )
            return 0 if all(checks) else 1
        parser.error(f"unknown command: {args.command}")
        return 2
    except (
        ModelValidationError,
        json.JSONDecodeError,
        OSError,
        OverflowError,
        RecursionError,
        UnicodeError,
    ) as exc:
        _write_json(
            public_validation_error(exc),
            error_stream,
            False,
        )
        return 2


if __name__ == "__main__":  # pragma: no cover - exercised through __main__
    raise SystemExit(main())
