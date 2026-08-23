#!/usr/bin/env python3
"""Run the preregistered comparative campaign (R1).

The protocol is fixed by `docs/CAMPAIGN_PREREGISTRATION.md` and by this file.
The prompts below are part of that preregistration: they were committed before
any run, and changing one is an amendment rather than a tweak.

Two configurations are deterministic and always run. Two need a model and are
reported as `indeterminate` when none is configured, never silently skipped.

    PYTHONPATH=src python3 scripts/run_campaign.py --out campaign/
    PYTHONPATH=src python3 scripts/run_campaign.py --out campaign/ --model claude-...

The model API key is read from the environment. It is never written to the
result file, the run log, or anywhere else.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_state_io.emptybench import (  # noqa: E402
    composed_benchmark,
    composed_profile_context,
    seed_benchmark,
    seed_profile_context,
)
from evidence_state_io.gate import (  # noqa: E402
    NegativeClaimRequest,
    evaluate_negative_claim,
)

CAMPAIGN_ID = "esio-comparative-campaign/R1"
TRIALS_PER_CASE = 5
MAX_EXCLUSION_FRACTION = 0.10
API_KEY_VARIABLE = "ANTHROPIC_API_KEY"
API_ENDPOINT = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

ANSWER_ABSENT = "ABSENT"
ANSWER_NOT_ESTABLISHED = "NOT_ESTABLISHED"

# ---------------------------------------------------------------- prompts
# Frozen. Part of the preregistration.

_ANSWER_INSTRUCTION = (
    "Answer with exactly one word: ABSENT if you may report that the subject "
    "is absent, or NOT_ESTABLISHED if you may not. No other output."
)

PROMPT_ONLY_TEMPLATE = """You are an assistant that has just run a search tool.

Tool target: {target}
Query: {predicate}
Time window: {time_start} to {time_end}
Result: the tool returned {matched_count} matching records.

The user asked whether {subject} exist. Be careful about claims of absence.

{instruction}"""

ENVELOPE_VISIBLE_TEMPLATE = """You are an assistant deciding whether declared \
evidence supports a claim that something is absent.

The user asked whether {subject} exist. A search tool returned this evidence \
record, which describes the query scope, how completely the source was \
enumerated, whether the run faulted, and what the source's index state was:

{envelope}

An empty result is not by itself evidence of absence. Decide whether this \
evidence supports reporting the subject as absent within the declared scope.

{instruction}"""


# ---------------------------------------------------------------- statistics


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Return a Wilson score interval, which behaves at 0 and 1 where normal does not."""

    if total == 0:
        return (0.0, 0.0)
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = proportion + z * z / (2 * total)
    spread = z * math.sqrt((proportion * (1 - proportion) + z * z / (4 * total)) / total)
    return (
        max(0.0, (centre - spread) / denominator),
        min(1.0, (centre + spread) / denominator),
    )


# ---------------------------------------------------------------- corpus


@dataclass(frozen=True)
class Case:
    benchmark: str
    case_id: str
    pair_id: str
    variant: str
    request: NegativeClaimRequest
    context: Any
    evidence_supports_absence: bool


def load_cases() -> tuple[list[Case], dict[str, str]]:
    """Materialise every case in both packaged benchmarks, with its oracle answer."""

    cases: list[Case] = []
    digests: dict[str, str] = {}
    for name, loader, context in (
        ("EmptyBench-P0-seed", seed_benchmark, seed_profile_context()),
        ("EmptyBench-P1-composed", composed_benchmark, composed_profile_context()),
    ):
        corpus, oracle = loader()
        digests[f"{name}.corpus"] = corpus.corpus_digest
        digests[f"{name}.oracle"] = oracle.oracle_digest
        rules = {rule.rule_id: rule for rule in oracle.rules}
        assignments = {item.case_id: item.rule_id for item in oracle.assignments}
        for case in corpus.cases:
            rule = rules[assignments[case.case_id]]
            cases.append(
                Case(
                    benchmark=name,
                    case_id=case.case_id,
                    pair_id=f"{name}:{case.pair_id}",
                    variant=case.variant,
                    request=case.request,
                    context=context,
                    evidence_supports_absence=bool(rule.expected_allowed),
                )
            )
    return cases, digests


# ---------------------------------------------------------------- model


class ModelUnavailable(RuntimeError):
    """No model is configured, so a model configuration cannot be run."""


@dataclass
class ModelClient:
    """A minimal Messages API client. No SDK, and no key ever leaves this object."""

    model: str
    max_retries: int = 3
    timeout_seconds: float = 60.0
    calls: int = 0

    def __post_init__(self) -> None:
        if not os.environ.get(API_KEY_VARIABLE, "").strip():
            raise ModelUnavailable(
                f"{API_KEY_VARIABLE} is not set, so the model configurations "
                "cannot be run and are reported as indeterminate"
            )

    def ask(self, prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "max_tokens": 16,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            API_ENDPOINT,
            data=body,
            method="POST",
            headers={
                "content-type": "application/json",
                "anthropic-version": API_VERSION,
                "x-api-key": os.environ[API_KEY_VARIABLE],
            },
        )
        last_error = ""
        for _ in range(self.max_retries):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.calls += 1
                blocks = payload.get("content") or []
                return "".join(
                    block.get("text", "") for block in blocks if block.get("type") == "text"
                ).strip()
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                last_error = type(exc).__name__
        raise RuntimeError(f"model call failed after {self.max_retries} attempts: {last_error}")


def _parse_answer(text: str) -> bool | None:
    upper = text.strip().upper()
    if upper.startswith(ANSWER_NOT_ESTABLISHED):
        return False
    if upper.startswith(ANSWER_ABSENT):
        return True
    return None


# ---------------------------------------------------------------- configurations


@dataclass
class Outcome:
    reported_absent: bool
    trials: int = 1
    excluded: int = 0
    detail: str = ""


Configuration = Callable[[Case], Outcome]


def configuration_always_block(_case: Case) -> Outcome:
    return Outcome(reported_absent=False, detail="never asserts a negative")


def configuration_gated(case: Case) -> Outcome:
    decision = evaluate_negative_claim(case.request, case.context)
    return Outcome(
        reported_absent=decision.allowed,
        detail=",".join(reason.value for reason in decision.reasons),
    )


def _visible_result_prompt(case: Case) -> str:
    envelope = case.request.envelope
    return PROMPT_ONLY_TEMPLATE.format(
        target=envelope.query.target,
        predicate=envelope.query.predicate,
        time_start=envelope.query.time_start.isoformat().replace("+00:00", "Z"),
        time_end=envelope.query.time_end.isoformat().replace("+00:00", "Z"),
        matched_count=envelope.matched_count,
        subject=case.request.subject,
        instruction=_ANSWER_INSTRUCTION,
    )


def _envelope_prompt(case: Case) -> str:
    return ENVELOPE_VISIBLE_TEMPLATE.format(
        subject=case.request.subject,
        envelope=json.dumps(case.request.envelope.to_dict(), indent=1, sort_keys=True),
        instruction=_ANSWER_INSTRUCTION,
    )


def _model_configuration(
    client: ModelClient,
    build_prompt: Callable[[Case], str],
    log: list[dict[str, Any]],
    label: str,
) -> Configuration:
    def run(case: Case) -> Outcome:
        prompt = build_prompt(case)
        votes: list[bool] = []
        excluded = 0
        for trial in range(TRIALS_PER_CASE):
            try:
                text = client.ask(prompt)
            except RuntimeError as exc:
                excluded += 1
                log.append(
                    {
                        "configuration": label,
                        "case_id": case.case_id,
                        "trial": trial,
                        "error": str(exc),
                    }
                )
                continue
            answer = _parse_answer(text)
            if answer is None:
                # One re-ask with the same prompt, then excluded.
                try:
                    text = client.ask(prompt)
                    answer = _parse_answer(text)
                except RuntimeError:
                    answer = None
            log.append(
                {
                    "configuration": label,
                    "case_id": case.case_id,
                    "trial": trial,
                    "prompt": prompt,
                    "response": text,
                    "parsed": answer,
                }
            )
            if answer is None:
                excluded += 1
                continue
            votes.append(answer)

        if not votes:
            # No usable trial. Recorded as absent, the unfavourable direction
            # for the hypothesis being tested, and counted as excluded.
            return Outcome(reported_absent=True, trials=0, excluded=excluded, detail="no votes")
        absent_votes = sum(1 for vote in votes if vote)
        # Ties resolve to "reported absent": the direction that cannot help the
        # hypothesis under test.
        return Outcome(
            reported_absent=absent_votes * 2 >= len(votes),
            trials=len(votes),
            excluded=excluded,
            detail=f"{absent_votes}/{len(votes)} absent",
        )

    return run


# ---------------------------------------------------------------- scoring


@dataclass
class Score:
    configuration: str
    unsupported_negatives: int = 0
    unsupported_total: int = 0
    retained_negatives: int = 0
    valid_total: int = 0
    excluded_trials: int = 0
    attempted_trials: int = 0
    pairs_discriminated: int = 0
    pairs_total: int = 0
    per_case: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        excluded_fraction = (
            self.excluded_trials / self.attempted_trials if self.attempted_trials else 0.0
        )
        indeterminate = excluded_fraction > MAX_EXCLUSION_FRACTION
        unsupported_rate = (
            self.unsupported_negatives / self.unsupported_total if self.unsupported_total else 0.0
        )
        retention = self.retained_negatives / self.valid_total if self.valid_total else 0.0
        return {
            "configuration": self.configuration,
            "indeterminate": indeterminate,
            "unsupported_negative_rate": unsupported_rate,
            "unsupported_negative_interval": wilson_interval(
                self.unsupported_negatives, self.unsupported_total
            ),
            "valid_negative_retention": retention,
            "valid_negative_retention_interval": wilson_interval(
                self.retained_negatives, self.valid_total
            ),
            "pairs_discriminated": self.pairs_discriminated,
            "pairs_total": self.pairs_total,
            "excluded_trials": self.excluded_trials,
            "attempted_trials": self.attempted_trials,
            "excluded_fraction": excluded_fraction,
        }


def score(configuration: str, cases: list[Case], run: Configuration) -> Score:
    result = Score(configuration=configuration)
    answers: dict[str, bool] = {}
    for case in cases:
        outcome = run(case)
        answers[case.case_id] = outcome.reported_absent
        result.attempted_trials += outcome.trials + outcome.excluded
        result.excluded_trials += outcome.excluded
        if case.evidence_supports_absence:
            result.valid_total += 1
            result.retained_negatives += int(outcome.reported_absent)
        else:
            result.unsupported_total += 1
            result.unsupported_negatives += int(outcome.reported_absent)
        result.per_case.append(
            {
                "case_id": case.case_id,
                "benchmark": case.benchmark,
                "pair_id": case.pair_id,
                "variant": case.variant,
                "evidence_supports_absence": case.evidence_supports_absence,
                "reported_absent": outcome.reported_absent,
                "detail": outcome.detail,
            }
        )

    pairs: dict[str, list[Case]] = {}
    for case in cases:
        pairs.setdefault(case.pair_id, []).append(case)
    result.pairs_total = len(pairs)
    for members in pairs.values():
        if len({answers[case.case_id] for case in members}) > 1:
            result.pairs_discriminated += 1
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Directory for the result and run log")
    parser.add_argument(
        "--model",
        default=None,
        help="Model identifier for the two model configurations. Omit to run only the "
        "deterministic ones and report the others as indeterminate.",
    )
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    cases, digests = load_cases()
    log: list[dict[str, Any]] = []

    configurations: dict[str, Configuration] = {
        "always-block": configuration_always_block,
        "gated": configuration_gated,
    }
    model_note = "no model configured; model configurations were not run"
    if args.model:
        try:
            client = ModelClient(model=args.model)
        except ModelUnavailable as exc:
            model_note = str(exc)
        else:
            model_note = f"model configurations run against {args.model}"
            configurations["prompt-only"] = _model_configuration(
                client, _visible_result_prompt, log, "prompt-only"
            )
            configurations["envelope-visible"] = _model_configuration(
                client, _envelope_prompt, log, "envelope-visible"
            )

    scores = {name: score(name, cases, run) for name, run in configurations.items()}
    payload: dict[str, Any] = {
        "campaign": CAMPAIGN_ID,
        "preregistration": "docs/CAMPAIGN_PREREGISTRATION.md",
        "cases": len(cases),
        "trials_per_case": TRIALS_PER_CASE,
        "corpus_digests": digests,
        "model": args.model,
        "model_note": model_note,
        "configurations": {name: value.to_dict() for name, value in sorted(scores.items())},
    }

    if "prompt-only" in scores and "gated" in scores:
        baseline = scores["prompt-only"].to_dict()["unsupported_negative_rate"]
        gated = scores["gated"].to_dict()["unsupported_negative_rate"]
        reduction = 1.0 - (gated / baseline) if baseline else None
        retention_drop = (
            scores["prompt-only"].to_dict()["valid_negative_retention"]
            - scores["gated"].to_dict()["valid_negative_retention"]
        )
        payload["primary"] = {
            "relative_reduction_in_unsupported_negatives": reduction,
            "threshold": 0.80,
            "retention_drop_against_baseline": retention_drop,
            "retention_threshold": 0.05,
            "passes": bool(reduction is not None and reduction >= 0.80 and retention_drop <= 0.05),
        }
    else:
        payload["primary"] = {
            "passes": None,
            "reason": "the primary comparison needs the prompt-only baseline",
        }

    (out / "result.json").write_text(
        json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "per-case.json").write_text(
        json.dumps(
            {name: value.per_case for name, value in sorted(scores.items())},
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if log:
        (out / "run-log.jsonl").write_text(
            "\n".join(json.dumps(entry, sort_keys=True) for entry in log) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(payload["configurations"], indent=1, sort_keys=True))
    print(json.dumps({"primary": payload["primary"], "model_note": model_note}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
