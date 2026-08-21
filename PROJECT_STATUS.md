# Project Status

**Status date:** 2026-08-21
**Lifecycle stage:** schema `1.0` source-accounting and finality candidate, locally tested
**Claim level:** local research prototype only

## Current objective

Produce a reproducible laptop-based gateway that permits a bounded negative
only when the supplied evidence state, query scope, coverage, and required
source observation satisfy an explicit fail-closed contract. Declared-horizon
chronology is now enforced; profile-governed finality remains open. The next
increment must define and bind the governed coverage/finality profile needed by
a complete canonical decision certificate, without confusing a digest with a
signature.

## Continuation mechanism

- Active goal: complete the runnable handoff and advance the MVP until its
  defined acceptance criteria are met.
- Active daily heartbeat: `advance-evidence-state-i-o`, scheduled for 9:00 AM
  in the task's local timezone.
- The heartbeat is bounded by `HANDOFF.md` and may not cross release,
  licensing, external-deployment, sensitive-data, or material-cost approval
  boundaries.
- The ordered implementation queue and restart instructions are in `TASKS.md`
  and `HANDOFF.md`; every increment must leave the repository recoverable and
  update this evidence record.

## Current implementation

- Package `0.3.0` accepts exactly active schema `1.0`, policy
  `esio-p0-safety-floor/1.0-candidate.2`, and evaluator
  `esio-evaluator-1.0-candidate.2`.
- Query scope includes a stable authorization-context ID and is normalized to
  a canonical SHA-256 fingerprint. The coverage object and every source
  observation must carry that fingerprint.
- The candidate accepts exactly one declared `REQUIRED` source. The source
  requirement and observation must match on source ID, system, locator,
  adapter ID/version, authorization context, and accessible population.
  Detection assumptions must be explicit, nonempty, unique, and canonical.
- Missing and every non-observed source status reject. Identity, adapter,
  authorization, population, observation-error, and query-binding mismatches
  also reject with source-attributed reasons.
- Literal `unknown`, `unspecified`, `none`, and `n/a` placeholders reject across
  the safety-bearing subject, query, exclusion, source/adapter identity,
  authorization context, population, and detection-assumption fields. Exact
  `*` and `all` also reject where a bounded identity, population, exclusion, or
  subject is required; they remain valid explicit target/predicate expressions
  whose meaning is still bounded by the query's authorization, source, and
  time contract. This does not prove broader semantic correctness.
- A source requirement can carry a query-bound `finality_horizon`. It is
  syntactically optional/null-compatible for the unfrozen schema `1.0`
  candidate, but policy candidate.2 makes it a non-relaxable permit condition.
  Missing/null values reject with `FINALITY_HORIZON_UNDECLARED`.
- A permit requires the inclusive chronology `query.time_end <= horizon <=
  index_as_of <= observed_at <= evaluated_at <= valid_until`. Advancing only
  evaluation time cannot repair a pre-horizon snapshot. The comparison proves
  consistency with supplied declarations, not source completeness or honesty.
- Omitted and null horizons canonicalize by omission. This preserves the actual
  pre-finality schema `1.0` query fingerprint so an older bound object can be
  diagnosed under candidate.2; it still rejects and is not auto-upgraded.
- EmptyBench contains seven matched pairs/fourteen synthetic cases, including
  required-source observed-versus-missing and index-at-versus-before-finality
  pairs.
- The hash-bound schema `0.1` fixture and decision digest remain available for
  historical replay only at commit `b6fac87`; the active parser rejects `0.1`
  and performs no implicit migration.

## Verification record

On 2026-08-21, the current schema `1.0` candidate produced the following local
results:

- Finality implementation checkpoint:
  `7deaea1dd79eacd2c4f3ebbef87a314e5293f1f6` (`contract: enforce explicit source finality`).
- Finality documentation/custody checkpoint:
  `bac04fabfa5dbcf6a7e639217ee345f9c8ceb645` (`docs: record finality checkpoint custody`).
- Prior source-accounting checkpoint:
  `bdd7c1e15c45f8d9940fc76604b3dde1fa953faa` (`contract: bind schema 1.0 to required source evidence`).
- `env -u PYTHONPATH ./scripts/check.sh` — passed static checks, local-link
  checks, shell/Compose validation, source-versus-installed package snapshots,
  and deterministic demonstration parity.
- `env -u PYTHONPATH ./scripts/test.sh` — 244/244 passed on Python 3.13.0.
- `env -u PYTHONPATH ./.venv/bin/python -m pytest -q` — 244/244 passed against
  the installed `site-packages` copy with `PYTHONPATH` unset.
- `PYTHONPATH=src /opt/homebrew/bin/python3.11 -m unittest discover -s tests -q`
  — 244/244 passed against the checked-out source on Python 3.11.
- `env -u PYTHONPATH ./scripts/demo.sh --pretty` — 2/2 synthetic operator cases
  passed.
- The Python 3.11 source seed and Python 3.13 installed-package seed runs passed
  14/14 and were byte-identical. The custom EmptyBench example passed 2/2 and
  retained `EmptyBench-custom` provenance.
- Direct installed CLI evaluation produced `PERMIT_SCOPED_NEGATIVE` for the
  fully bound covered example and `REJECT_NEGATIVE` for the matched partial
  example.
- `scripts/setup.sh` now verifies equality among the project, imported module,
  and installed-distribution versions. A stale `0.1.0` metadata directory was
  detected during review, moved recoverably to
  `/private/tmp/evidence-state-io-stale-0.1.0.dist-info`, and the clean
  `0.3.0` installation passed the complete replay.
- `git diff --check` and `bash -n scripts/*.sh` passed.

An internal read-only adversarial review rejected the first green 215-test
schema `1.0` proposal. It reproduced permits with the wrong source descriptor,
missing adapter identity, conflicting authorization context, empty detection
assumptions, hidden optional-source failure, unbound coverage/observation
objects, and missing or pre-query source-index timestamps. Those paths were
converted to regressions before the 224-test candidate checkpoint was accepted
for continued local development.

The final candidate audit also caught source/install drift after a late output
edit and a self-consistent placeholder-declaration permit path. The package was
reinstalled, exact parity was restored, and the placeholder mutations were
converted into existing-suite regressions before custody binding.

The explicit-finality audit first caught an unsafe design possibility—the
wait-only upgrade of an old empty snapshot—and required the source index itself
to reach the horizon. Its post-implementation pass then found that unconditional
serialization of an undeclared horizon as `null` changed actual pre-finality
schema `1.0` query fingerprints before the intended diagnostic could run.
Omitted/null horizons now normalize by omission, and a regression using the
actual `example-0.2` fingerprint proves that the object parses and rejects solely
with `FINALITY_HORIZON_UNDECLARED`. The final read-only adversarial audit passed
164/164 focused Python 3.13 checks and 37/37 Python 3.11 finality/benchmark
checks without reproducing a fail-open.

The historical 171-test snapshot remains the first accepted **local** schema
`0.1` and canonicalization-profile `0.1` freeze at `b6fac87`. The 244-test
schema `1.0` state is a candidate source-accounting/finality checkpoint, not a frozen
schema, benchmark, release, certificate, or external validation result.

These results are local synthetic evidence. GitHub Actions was not executed,
containers were not started, and no external or operational system was
evaluated.

## Known limitations

- The aggregate evidence state and coverage facts are producer-supplied. The
  gateway validates their internal contract but does not independently derive
  or attest their truth.
- Query fingerprints reduce wrong-object and accidental substitution risk; a
  self-consistent malicious producer can still forge declarations without an
  authenticated adapter or attestation profile.
- The gate enforces a declared horizon but does not validate its late-arrival
  model, authenticate the reported index, calibrate clocks, or model exceptional
  backfill, correction, deletion, retraction, or source reopening.
- No governed profile registry, snapshot-consistency model, blind-interval
  model, or multi-source composition exists.
- No complete certificate binding schema, policy/evaluator versions, origin,
  input, verdict, reasons, qualification, and issue time exists.
- The SHA-256 input digest is integrity metadata, not a signature or independent
  evidence custody.
- The EmptyBench corpus and oracle are implementation-owned, not independently
  governed, preregistered, or frozen.
- No design-partner evidence, real adapter, independently reproduced benchmark,
  operational deployment, or external security assessment exists.
- Credential-like identifier detection, governed adapter/profile registries,
  comprehensive per-collection bounds, and broad fuzzing remain open.
- No licensing decision has been made. Public-search absence does not prove no
  private implementation exists.

## Next decision

Define and bind the governed coverage/finality profile, build the complete
deterministic certificate, then separate and freeze the EmptyBench oracle before
any market, benchmark, production-readiness, or external-validation claim.
