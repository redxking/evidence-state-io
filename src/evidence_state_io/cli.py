"""JSON command-line interface for Evidence-State I/O."""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sys
from typing import Any, Sequence, TextIO

from .coverage import CoveragePolicy, evaluate_coverage
from .emptybench import parse_cases, run_emptybench, run_seed_emptybench
from .gate import NegativeClaimRequest, NegativeClaimPolicy, evaluate_negative_claim
from .models import (
    ClaimMode,
    CoverageEvidence,
    EvidenceEnvelope,
    MAX_INTEGER_DECIMAL_DIGITS,
    ModelValidationError,
    parse_datetime,
)

MAX_INPUT_BYTES = 1_048_576
MAX_JSON_DEPTH = 128
MAX_JSON_NUMBER_TOKEN_CHARS = MAX_INTEGER_DECIMAL_DIGITS


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ModelValidationError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ModelValidationError(f"non-standard JSON numeric constant is not allowed: {value}")


def _check_json_number_token(value: str) -> None:
    if len(value) > MAX_JSON_NUMBER_TOKEN_CHARS:
        raise ModelValidationError(
            "JSON numeric token exceeds the supported "
            f"{MAX_JSON_NUMBER_TOKEN_CHARS}-character limit"
        )


def _parse_json_int(value: str) -> int:
    _check_json_number_token(value)
    try:
        return int(value)
    except ValueError as exc:
        raise ModelValidationError("JSON integer could not be decoded safely") from exc


def _parse_json_float(value: str) -> Decimal:
    _check_json_number_token(value)
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ModelValidationError("JSON number could not be decoded safely") from exc


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
        raise ModelValidationError("JSON nesting exceeds the supported parser depth") from exc
    except ModelValidationError:
        raise
    except json.JSONDecodeError:
        raise
    except ValueError as exc:
        raise ModelValidationError("JSON numeric token could not be decoded safely") from exc
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise ModelValidationError(
                f"JSON nesting exceeds the supported depth of {MAX_JSON_DEPTH}"
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
            raise ModelValidationError("JSON input must be valid UTF-8") from exc
        if not isinstance(text, str):
            raise ModelValidationError("JSON input stream must provide decoded text")
        try:
            encoded = text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ModelValidationError("JSON input must be valid UTF-8") from exc
        if len(encoded) > MAX_INPUT_BYTES:
            raise ModelValidationError(
                f"JSON input exceeds the {MAX_INPUT_BYTES}-byte limit"
            )
        return _strict_json_loads(text)
    raw = Path(path).read_bytes()
    if len(raw) > MAX_INPUT_BYTES:
        raise ModelValidationError(f"JSON input exceeds the {MAX_INPUT_BYTES}-byte limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ModelValidationError("JSON input must be valid UTF-8") from exc
    return _strict_json_loads(text)


def _write_json(value: Any, stream: TextIO, pretty: bool) -> None:
    try:
        if pretty:
            payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True)
        else:
            payload = json.dumps(
                value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            )
        payload.encode("utf-8")
    except (TypeError, UnicodeError, ValueError) as exc:
        raise ModelValidationError("JSON output could not be encoded safely") from exc
    stream.write(payload + "\n")


def _evaluate_input(data: Any, args: argparse.Namespace) -> dict[str, Any]:
    if isinstance(data, dict) and "envelope" in data:
        supplied_overrides = [
            name
            for name in ("evaluated_at", "subject", "mode")
            if getattr(args, name) is not None
        ]
        if supplied_overrides:
            raise ModelValidationError(
                "full request JSON cannot be combined with CLI overrides: "
                + ", ".join(f"--{name.replace('_', '-')}" for name in supplied_overrides)
            )
        return evaluate_negative_claim(NegativeClaimRequest.from_dict(data)).to_dict()

    if args.evaluated_at is None:
        raise ModelValidationError(
            "a bare envelope requires --evaluated-at; the CLI never falls back to wall-clock time"
        )
    envelope = EvidenceEnvelope.from_dict(data)
    try:
        mode = ClaimMode(
            ClaimMode.SCOPED.value if args.mode is None else args.mode
        )
    except ValueError as exc:  # argparse choices should make this unreachable
        raise ModelValidationError("--mode must be SCOPED or ABSOLUTE") from exc
    request = NegativeClaimRequest(
        envelope=envelope,
        subject=(
            "records matching the query"
            if args.subject is None
            else args.subject
        ),
        mode=mode,
        evaluated_at=parse_datetime(args.evaluated_at, "--evaluated-at"),
        policy=NegativeClaimPolicy(),
    )
    return evaluate_negative_claim(request).to_dict()


def _coverage_input(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ModelValidationError("coverage input must be a JSON object")
    unknown = sorted(set(data) - {"coverage", "policy"})
    if unknown:
        raise ModelValidationError(
            f"coverage input has unknown fields: {', '.join(unknown)}"
        )
    evidence = CoverageEvidence.from_dict(data.get("coverage"))
    policy = CoveragePolicy.from_dict(data.get("policy"))
    return evaluate_coverage(evidence, policy).to_dict()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evidence-state",
        description="Evaluate evidence-state envelopes without inferring global absence.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate = subparsers.add_parser(
        "evaluate", help="Evaluate one deterministic negative-claim request or envelope."
    )
    evaluate.add_argument("--input", required=True, help="JSON file, or - for stdin")
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
        "emptybench", help="Run EmptyBench cases supplied as JSON."
    )
    benchmark.add_argument("--input", required=True, help="JSON file, or - for stdin")
    benchmark.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    coverage = subparsers.add_parser(
        "coverage", help="Evaluate coverage evidence independently of a claim."
    )
    coverage.add_argument("--input", required=True, help="JSON file, or - for stdin")
    coverage.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
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
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.command == "evaluate":
            result = _evaluate_input(_read_json(args.input, input_stream), args)
            _write_json(result, output_stream, args.pretty)
            return 0
        if args.command == "demo":
            report = run_seed_emptybench(all_cases=args.all)
            _write_json(report.to_dict(), output_stream, args.pretty)
            return 0 if report.all_passed else 1
        if args.command == "emptybench":
            cases = parse_cases(_read_json(args.input, input_stream))
            report = run_emptybench(cases)
            _write_json(report.to_dict(), output_stream, args.pretty)
            return 0 if report.all_passed else 1
        if args.command == "coverage":
            result = _coverage_input(_read_json(args.input, input_stream))
            _write_json(result, output_stream, args.pretty)
            return 0
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
            {"error": {"type": type(exc).__name__, "message": str(exc)}},
            error_stream,
            False,
        )
        return 2


if __name__ == "__main__":  # pragma: no cover - exercised through __main__
    raise SystemExit(main())
