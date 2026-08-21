# Evidence-State I/O

Evidence-State I/O is a laptop-buildable research and product project for one narrow but consequential problem:

> A valid empty result is not, by itself, evidence that the thing being sought is absent.

The project defines a machine-readable evidence envelope, a deterministic negative-claim gate, and a paired benchmark for distinguishing a coverage-supported negative conclusion from partial, stale, inaccessible, failed, or otherwise indeterminate observation.

## Current status

**Stage:** pre-alpha research prototype and implementation handoff; schema `1.0` candidate
**Intended use:** local research, synthetic evaluation, adapter development, and design-partner discovery
**Not established:** production readiness, operational effectiveness, legal sufficiency, universal query completeness, market demand, protocol adoption, or independent validation

The active package is `0.3.0`. It accepts only the schema `1.0` candidate and
the explicit `esio-p0-safety-floor/1.0-candidate.2` policy. The first accepted local
schema `0.1` baseline remains immutable at commit `b6fac87`; it is preserved as
historical replay evidence and is not a current permit or compatibility mode.

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
carries a query-bound, declared finality horizon and requires the reported
source index to reach it. The gateway does not attest that the source's
late-arrival assumption or index watermark is true, and the candidate is not a
frozen contract. No version of this state is proof of absolute absence.

## Product direction

The project builds toward three connected products:

1. **EmptyBench** — matched test cases that hold the visible observations constant while varying whether the observation scope is complete.
2. **Evidence-State Gateway** — a deterministic runtime between agents and tools that qualifies or blocks unsupported negative conclusions.
3. **Coverage Registry** — enterprise source profiles describing ownership, population, retention, freshness, blind intervals, permissions, and detection assumptions.

The first vertical profile is cyber investigation and threat hunting. The underlying contract is intended to remain domain-neutral.

## Start here

1. Read [HANDOFF.md](HANDOFF.md).
2. Read [docs/PRD.md](docs/PRD.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
3. Review [docs/CLAIMS_AND_BOUNDARIES.md](docs/CLAIMS_AND_BOUNDARIES.md) before changing external-facing claims.
4. Select the highest-priority unblocked item in [docs/BACKLOG.md](docs/BACKLOG.md).
5. Run the repository checks before and after making a change.

## Local quick start

The supported baseline is Python 3.11 or newer. The reference implementation is intentionally dependency-light and does not require a GPU.

```bash
./scripts/setup.sh
source .venv/bin/activate
./scripts/test.sh
evidence-state --help
```

The setup uses a regular local install because the Python 3.13 runtime used to verify this handoff skips setuptools' hidden editable-install `.pth` file. Run `./scripts/setup.sh` again after source changes before testing the installed command; the repository wrappers also put `src/` first so development checks exercise the current checkout.

See [docs/LAPTOP_LAB.md](docs/LAPTOP_LAB.md) for the VM/container fault-injection environment and the exact demonstration sequence.

## Demonstration thesis and current slice

The target paired experiment asks the same question against the same visible empty result:

- **Covered case:** all required sources are available, current, query-covering, and past their finality horizons.
- **Partial case:** one or more required sources are unavailable, stale, filtered, incompletely paginated, or still pending.

The baseline agent may answer “none found” in both cases. The gateway must permit a scoped negative only in the first case and preserve indeterminacy in the second.

The checked-in P0 operator pair is narrower: it compares one explicitly
required and observed source whose current coverage and pagination facts pass
with the same empty result from an incompletely paginated execution. The full
seed adds missing-required-source and explicit-finality pairs. The candidate rejects missing,
inaccessible, pending, stale, failed, contradictory, unknown,
identity-mismatched, adapter-mismatched, authorization-mismatched,
population-mismatched, error-bearing, or pre-finality required sources.
Observations and coverage must match a canonical query fingerprint. A permit
requires the declared finality horizon to be at or after the query end and the
reported source index to reach that horizon; advancing evaluation time alone
cannot repair an older snapshot. Because population
composition is not yet defined, the candidate accepts exactly one declared
`REQUIRED` source and rejects multi-source input before evaluation. Governed
source profiles, authenticated watermarks, and correction/reopen semantics
remain active gaps.

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
HANDOFF.md              Exact continuation instructions
TASKS.md                Current bounded work queue
dashboard.html          Local task-board view backed by TASKS.md
```

## Working discipline

- Separate implemented, tested, benchmarked, externally reproduced, and production-proven states.
- Treat source health as necessary but not sufficient evidence of detection coverage.
- Keep the verdict path deterministic; language models may propose or explain but may not silently override coverage policy.
- Preserve raw observations, declared assumptions, evaluator version, and policy version in every certificate.
- Keep schema, policy, evaluator, profile, certificate, canonicalization, and package versions distinct.
- Add a matched negative control for each new fault class.
- Treat a source-overlay pass and an installed-command pass as separate evidence; `./scripts/check.sh` compares source and installed package file snapshots, then compares deterministic demos, and fails if the installed package is stale.
- Stop and request owner approval before public release, licensing, deployment into a real environment, handling sensitive data, or making external claims.

## Licensing

No public license has been selected. All rights remain with the project owner until an explicit licensing decision is recorded.
