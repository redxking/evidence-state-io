# Project Status

**Status date:** 2026-08-21
**Lifecycle stage:** schema `1.0` source-accounting candidate, locally tested
**Claim level:** local research prototype only

## Current objective

Produce a reproducible laptop-based gateway that permits a bounded negative
only when the supplied evidence state, query scope, coverage, and required
source observation satisfy an explicit fail-closed contract. The next
increment must add explicit source finality; an index timestamp is not a
finality watermark.

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

- Package `0.2.0` accepts exactly active schema `1.0`, policy
  `esio-p0-safety-floor/1.0-candidate.1`, and evaluator
  `esio-evaluator-1.0-candidate.1`.
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
- An observed source must provide `index_as_of`, and it must not precede the
  query interval end or postdate the observation. This is a necessary
  chronology/currentness condition only; it does not prove late-arrival
  finality or completeness.
- EmptyBench contains six matched pairs/twelve synthetic cases, including a
  required-source observed-versus-missing pair.
- The hash-bound schema `0.1` fixture and decision digest remain available for
  historical replay only at commit `b6fac87`; the active parser rejects `0.1`
  and performs no implicit migration.

## Verification record

On 2026-08-21, the current schema `1.0` candidate produced the following local
results:

- Candidate implementation checkpoint:
  `bdd7c1e15c45f8d9940fc76604b3dde1fa953faa` (`contract: bind schema 1.0 to required source evidence`).
- `env -u PYTHONPATH ./scripts/check.sh` — passed static checks, local-link
  checks, shell/Compose validation, source-versus-installed package snapshots,
  and deterministic demonstration parity.
- `env -u PYTHONPATH ./scripts/test.sh` — 224/224 passed on Python 3.13.0.
- `env -u PYTHONPATH ./.venv/bin/python -m pytest -q` — 224/224 passed against
  the installed `site-packages` copy with `PYTHONPATH` unset.
- `PYTHONPATH=src /opt/homebrew/bin/python3.11 -m unittest discover -s tests -q`
  — 224/224 passed against the checked-out source on Python 3.11.
- `env -u PYTHONPATH ./scripts/demo.sh --pretty` — 2/2 synthetic operator cases
  passed.
- The Python 3.11 source seed and Python 3.13 installed-package seed runs passed
  12/12 and were byte-identical. The custom EmptyBench example passed 2/2 and
  retained `EmptyBench-custom` provenance.
- Direct installed CLI evaluation produced `PERMIT_SCOPED_NEGATIVE` for the
  fully bound covered example and `REJECT_NEGATIVE` for the matched partial
  example.
- `scripts/setup.sh` now verifies equality among the project, imported module,
  and installed-distribution versions. A stale `0.1.0` metadata directory was
  detected during review, moved recoverably to
  `/private/tmp/evidence-state-io-stale-0.1.0.dist-info`, and the clean
  `0.2.0` installation passed the complete replay.
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

The historical 171-test snapshot remains the first accepted **local** schema
`0.1` and canonicalization-profile `0.1` freeze at `b6fac87`. The 224-test
schema `1.0` state is a candidate source-accounting checkpoint, not a frozen
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
- No explicit finality horizon, late-arrival model, snapshot-consistency model,
  blind-interval model, or multi-source composition exists.
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

Implement explicit, supplied finality with exact below/equal/above boundary
tests and no wall-clock dependency. Then bind a complete deterministic
certificate and separate/freeze the EmptyBench oracle before any market,
benchmark, production-readiness, or external-validation claim.
