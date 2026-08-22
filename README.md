# Evidence-State I/O

[![CI](https://github.com/redxking/evidence-state-io/actions/workflows/ci.yml/badge.svg)](https://github.com/redxking/evidence-state-io/actions/workflows/ci.yml)
[![CodeQL](https://github.com/redxking/evidence-state-io/actions/workflows/codeql.yml/badge.svg)](https://github.com/redxking/evidence-state-io/actions/workflows/codeql.yml)
[![Pages](https://github.com/redxking/evidence-state-io/actions/workflows/pages.yml/badge.svg)](https://redxking.github.io/evidence-state-io/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Evidence-State I/O is a laptop-buildable research and product project for one narrow but consequential problem:

> A valid empty result is not, by itself, evidence that the thing being sought is absent.

The project defines a machine-readable evidence envelope, a deterministic negative-claim gate, and a paired benchmark for distinguishing a coverage-supported negative conclusion from partial, stale, inaccessible, failed, or otherwise indeterminate observation.

## Current status

**Stage:** pre-alpha research prototype and implementation handoff; schema `1.0` candidate
**Intended use:** local research, synthetic evaluation, adapter development, and design-partner discovery
**Not established:** production readiness, operational effectiveness, legal sufficiency, universal query completeness, market demand, protocol adoption, or independent validation

The active package is `0.6.0`. It accepts only the unfrozen schema `1.0`
candidate and the explicit `esio-p0-safety-floor/1.0-candidate.4` policy. The
corresponding evaluator is `esio-evaluator-1.0-candidate.5`; the profile,
registry-snapshot, trust-selection, evaluation-input, and certificate
contracts are each `1.0-candidate.2`. A complete identifier table is below.

The application supplies the registry snapshot and trust selection separately
from the producer request. The trust selection pins both the exact snapshot
and the exact profile reference the application selected. A producer cannot
choose a weaker sibling profile from the same otherwise trusted snapshot. The
resulting `esio-evidence-certificate/1.0-candidate.2` object is an unsigned,
deterministic replay record. Its digests support exact comparison against a
separately retained expected value; they do not authenticate an issuer, prove
source truth, authorize an action, or prevent replacement of both trust files
when configuration custody is lost.

The first accepted local schema `0.1` baseline remains immutable at commit
`b6fac87`; it is preserved as historical replay evidence and is not a current
permit or compatibility mode. Schema `1.0` remains unfrozen while the final
`0.6.0` acceptance and custody run is open.

This is an independent project. It is not an extension or release claim for any earlier assurance platform.

## Core invariant

The runtime must not authorize an unqualified negative factual claim unless all required evidence sources and coverage conditions support `ABSENT_WITHIN_SCOPE` for the declared query.

The initial evidence states are:

- `PRESENT`
- `ABSENT_WITHIN_SCOPE`
- `NOT_OBSERVED`
- `PARTIAL`
- `STALE`
- `INACCESSIBLE`
- `PENDING_WINDOW`
- `FAILED`
- `CONTRADICTORY`

The target semantics make `ABSENT_WITHIN_SCOPE` conditional on the declared
population, fields, time interval, source assumptions, access boundary,
detection assumptions, and finality horizon. The current schema `1.0` candidate
binds the query to an exact governed profile reference. That profile supplies
the applicable population, authorization, detection, retention, freshness,
blind-interval, late-arrival, and reopen assumptions. The gateway derives the
required finality horizon from those assumptions and requires the reported
source index to reach it. It does not attest that the registry issuer, profile
assertions, source index, or source observations are truthful, and the
candidate is not a frozen contract. No version of this state is proof of
absolute absence.

## Active contract set

| Boundary | Active identifier |
|---|---|
| Package | `0.6.0` |
| Wire schema | `1.0` candidate, unfrozen |
| Policy | `esio-p0-safety-floor/1.0-candidate.4` |
| Evaluator | `esio-evaluator-1.0-candidate.5` |
| Coverage/finality profile | `esio-coverage-finality-profile/1.0-candidate.2` |
| Registry snapshot | `esio-profile-registry-snapshot/1.0-candidate.2` |
| Trust selection | `esio-profile-trust-selection/1.0-candidate.2` |
| Evaluation input | `esio-evaluation-input/1.0-candidate.2` |
| Evidence certificate | `esio-evidence-certificate/1.0-candidate.2` |
| Evidence-state transitions | `esio-evidence-state-transition-model/1.0-candidate.1` |
| Authorization-context identifier | `esio-authorization-context-identifier/1.0-candidate.1` |
| Validation error | `esio-validation-error/1.0-candidate.1` |
| EmptyBench corpus | `esio-emptybench-corpus/1.0-candidate.1` |
| EmptyBench oracle | `esio-emptybench-oracle/1.0-candidate.1` |
| EmptyBench report | `esio-emptybench-report/1.0-candidate.1` |
| Canonicalization | `esio-canonical-json-0.1` |
| Digest | SHA-256 |

Unknown, older, newer, aliased, ranged, or floating active contract versions
do not negotiate or fall back. Historical identifiers remain evidence of their
own recorded implementations only.

## Governed profile and trust sequence

The permit path is staged so untrusted content cannot set the safety boundary:

1. The query carries a normalized, exact
   `(registry_id, profile_id, profile_version, profile_digest)` reference.
2. The application supplies a registry snapshot and trust selection outside
   the producer-controlled request.
3. The trust selection pins the exact snapshot identity/version/digest and the
   exact application-selected profile reference, plus declarative issuer and
   approval-authority allowlists.
4. Snapshot identity, digest, issuer, effective time, and expiry must pass
   before any contained record is consulted. The selected record must then
   pass exact digest resolution, issuer, approval-authority, profile validity,
   and revocation checks before its applicability or finality content is used.
5. The request and observation must match the trusted profile's source,
   adapter, authorization, population, query, detection, coverage, retention,
   blind-interval, and freshness constraints. The required finality horizon is
   derived from the selected profile rather than chosen by the producer.

This sequence establishes deterministic local configuration binding. Profile
owners and issuers, adapter identity, source clocks, index watermarks,
late-arrival/reopen bounds, and ingestion completeness are still assertions,
not authenticated or empirically validated facts.

## Product direction

The project builds toward three connected products:

1. **EmptyBench** — matched test cases that hold the visible observations constant while varying whether the observation scope is complete.
2. **Evidence-State Gateway** — a deterministic runtime between agents and tools that qualifies or blocks unsupported negative conclusions.
3. **Coverage Registry** — enterprise source profiles describing ownership, population, retention, freshness, blind intervals, permissions, and detection assumptions.

The first vertical profile is cyber investigation and threat hunting. The underlying contract is intended to remain domain-neutral.

## Start here

1. Read [HANDOFF.md](HANDOFF.md).
2. Read [PROJECT_STATUS.md](PROJECT_STATUS.md) and [TASKS.md](TASKS.md); finish the active acceptance/custody item before taking another feature.
3. Read [docs/PRD.md](docs/PRD.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
4. Review [docs/CLAIMS_AND_BOUNDARIES.md](docs/CLAIMS_AND_BOUNDARIES.md) before changing external-facing claims.
5. After the active task closes, select the highest-priority unblocked item in [docs/BACKLOG.md](docs/BACKLOG.md).
6. Run the repository checks before and after making a change.

Public navigation: [project site](https://redxking.github.io/evidence-state-io/),
[wiki](https://github.com/redxking/evidence-state-io/wiki),
[roadmap](https://github.com/redxking/evidence-state-io/projects),
[issues](https://github.com/redxking/evidence-state-io/issues), and
[discussions](https://github.com/redxking/evidence-state-io/discussions).

## Local quick start

The supported runtime set is Python 3.11, 3.12, and 3.13. The reference implementation is intentionally dependency-light and does not require a GPU.

```bash
./scripts/setup.sh
source .venv/bin/activate
./scripts/test.sh
evidence-state --help
```

The setup uses a regular local install because the Python 3.13 runtime used to verify this handoff skips setuptools' hidden editable-install `.pth` file. Run `./scripts/setup.sh` again after source changes before testing the installed command; the repository wrappers also put `src/` first so development checks exercise the current checkout.

Issue and then independently replay-check the checked-in synthetic certificate:

```bash
evidence-state evaluate \
  --input examples/covered_request.json \
  --registry examples/profile_registry.json \
  --trust examples/profile_trust.json \
  --issued-at 2026-08-21T12:06:00Z \
  --origin SYNTHETIC \
  --pretty

evidence-state verify-certificate \
  --input examples/covered_certificate.json \
  --registry examples/profile_registry.json \
  --trust examples/profile_trust.json \
  --expected-digest sha256:5683e522aa22f08145658d49452a4c044d7cf562a6a3987da364b3322d4aab17 \
  --relying-party-at 2026-08-21T12:30:00Z \
  --pretty
```

The verifier reports separate structural, outer-digest, embedded-binding,
deterministic-replay, expected-context, expected-digest, and current-local-use
dimensions. Current local use requires an explicitly supplied relying-party
time satisfying
`issued_at <= relying_party_at < effective_valid_until_exclusive`, a permitted
replayed decision, intact bindings, and the separately supplied expected
context. The effective exclusive boundary is the earliest applicable value
among:

- the registry snapshot's `next_update_at`;
- the envelope's inclusive `valid_until`, reused conservatively as an
  exclusive certificate boundary;
- policy observation and per-source index freshness deadlines;
- each resolved profile's expiry and effective revocation time; and
- each resolved profile's observation and index freshness deadlines.

The supplied relying-party time is deterministic input, not trusted time. A
successful report remains local replay and comparison evidence, not signer
authentication, independent custody, non-repudiation, or action authority.

See [docs/LAPTOP_LAB.md](docs/LAPTOP_LAB.md) for the VM/container fault-injection environment and the exact demonstration sequence.

## Demonstration thesis and current slice

The target paired experiment asks the same question against the same visible empty result:

- **Covered case:** all required sources are available, current, query-covering, and past their finality horizons.
- **Partial case:** one or more required sources are unavailable, stale, filtered, incompletely paginated, or still pending.

The baseline agent may answer “none found” in both cases. The gateway must permit a scoped negative only in the first case and preserve indeterminacy in the second.

The checked-in P0 operator pair compares one explicitly required and observed
source whose governed profile, current coverage, and pagination facts pass with
the same empty result from an incompletely paginated execution. The complete
seed contains 12 matched control/fault families and 24 cases, stored in a
versioned corpus separately from its versioned declarative oracle. The corpus
contains no machine-scored expected verdict or reason fields; `control` and
`fault` are experimental roles and do not determine oracle polarity. The oracle
is bound to the corpus digest and must match a separately retained expected
oracle digest. This separation is an integrity boundary, not independent
adjudication or benchmark freeze. The
candidate rejects missing,
inaccessible, pending, stale, failed, contradictory, unknown,
identity-mismatched, adapter-mismatched, authorization-mismatched,
population-mismatched, error-bearing, or pre-finality required sources.
Observations and coverage must match a canonical query fingerprint. A permit
requires an application-trusted, exact, effective profile; a query outside
retention or across a blind interval rejects. Its finality horizon must equal
the query end plus the larger of the profile's late-arrival and reopen windows,
and the reported source index must reach it; advancing evaluation time alone
cannot repair an older snapshot. Because population
composition is not yet defined, the candidate accepts exactly one declared
`REQUIRED` source and rejects multi-source input before evaluation.
Authenticated registry custody, authenticated adapter and watermark evidence,
monotonic registry heads, empirical profile validation, operational revocation
distribution, and multi-source composition remain active gaps.

## Success threshold for the first gate

The project advances beyond prototype only if a frozen evaluation shows:

- at least an 80% relative reduction in unsupported negative conclusions compared with a model/tool baseline;
- zero `ABSENT_WITHIN_SCOPE` verdicts when a declared required source is missing, stale beyond policy, inaccessible, contradictory, or before its finality horizon;
- at least 90% retention of correctly supported negative conclusions in the paired benchmark;
- deterministic reproduction of every published certificate and verdict;
- at least three of ten qualified discovery interviews identify a costly false-absence or false-clearance pattern.

Failing those thresholds is a reason to narrow or stop the project, not to reinterpret the results.

## Project map

```text
src/evidence_state_io/  Reference schema, evaluator, gate, and CLI
tests/                  Unit, integration, contract, and benchmark tests
benchmarks/             Versioned EmptyBench corpus, oracle, and custody notes
examples/               Reproducible evidence-envelope and paired-case examples
examples/legacy/        Hash-bound schema 0.1 historical replay evidence
docs/PRD.md             Product requirements and acceptance criteria
docs/ARCHITECTURE.md    System boundaries, interfaces, and data flow
docs/adr/               Architecture decision records
docs/RESEARCH_PLAN.md   Research questions and study design
docs/VALIDATION_PLAN.md Verification and falsification program
docs/TRACEABILITY.md     Requirement-to-implementation status and exact local evidence
docs/REVIEW_LOG.md       Rejected baselines, reproduced defects, remediation, and review custody
docs/BACKLOG.md         Ordered implementation backlog
docs/LAPTOP_LAB.md      Laptop, VM, and container laboratory
docs/OPERATING_MODEL.md Continuous-agent working rules
docs/AUTOMATION.md      Portable recurring-operation contract and stop conditions
HANDOFF.md              Exact continuation instructions
TASKS.md                Current bounded work queue
automation/             Scheduler-ready recurring prompt
dashboard.html          Local task-board view backed by TASKS.md
site/                   Static GitHub Pages source
wiki/                   Version-controlled source mirror for the GitHub wiki
.github/                CI, security, release, Pages, and community automation
```

## Working discipline

- Separate implemented, tested, benchmarked, externally reproduced, and production-proven states.
- Treat source health as necessary but not sufficient evidence of detection coverage.
- Keep the verdict path deterministic; language models may propose or explain but may not silently override coverage policy.
- Preserve raw observations, declared assumptions, evaluator version, and policy version in every certificate.
- Keep schema, policy, evaluator, profile, certificate, canonicalization, and package versions distinct.
- Add a matched negative control for each new fault class.
- Treat a source-overlay pass and an installed-command pass as separate evidence; `./scripts/check.sh` compares source and installed package file snapshots, then compares deterministic demos, and fails if the installed package is stale.
- Stop and request owner approval before a versioned/package release, deployment into a real environment, handling sensitive data, changing the license, or making claims beyond the documented pre-alpha boundary.

## Licensing

Evidence-State I/O is open source under the [Apache License 2.0](LICENSE). See
[NOTICE](NOTICE) for attribution. Contributions are accepted under the same
license; no contributor agreement is implied beyond the terms documented in
[CONTRIBUTING.md](CONTRIBUTING.md) and [GOVERNANCE.md](GOVERNANCE.md).
