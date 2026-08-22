# Operating Model

## Operating objective

The repository is operated as a falsifiable research and engineering program. Every work cycle should either close a named acceptance criterion, expose a failure mode, improve reproducibility, or test a project-killing assumption. Activity, code volume, and green tests are not substitutes for evidence.

The owner retains authority over official project tags/releases and
announcements, license changes, real-data use, deployment, partnerships,
thresholds, and project claims. This governance does not restrict third-party
rights granted by Apache License 2.0.

## Roles and decision rights

One person may hold several roles, but the decision rights remain distinct.

| Role | May decide | Must escalate |
|---|---|---|
| Project owner | Product direction, claims, thresholds, license changes, official releases, design-partner scope | None within the project charter |
| Architecture maintainer | Internal interfaces, accepted ADR implementation, dependency-light design | New trust claims, incompatible schema changes, distributed deployment |
| Work-item agent | Bounded local implementation and tests inside assigned files | Scope expansion, destructive changes, external actions, threshold changes |
| Evidence reviewer | Verify fixtures, oracle independence, commands, outputs, and claim language | Conflicts that would change a published conclusion |
| Security reviewer | Threat model, dependency and input risks, release security gates | Acceptance of residual production risk |
| Release custodian | Assemble an owner-authorized release from verified artifacts | License changes, official publication, signing identity, production designation |

No agent or maintainer may infer an owner decision from a proposed ADR, passing test, local benchmark, or packaged artifact.

## Work states

Use the following states precisely:

- **Proposed:** written idea or task; not accepted.
- **Specified:** requirement and acceptance criteria exist.
- **Implemented:** code or documentation exists and was inspected locally.
- **Tested:** named checks passed in a recorded environment.
- **Benchmarked:** a version-frozen campaign produced reproducible measurements.
- **Externally reproduced:** an independent party reran the frozen campaign.
- **Operationally evaluated:** an authorized real workflow was evaluated under bounded conditions.
- **Production ready:** a separate security, reliability, legal, operational, and deployment decision was approved.

Each state requires its own evidence. No state implies the next one.

## Continuous-agent loop

Agents may continue autonomously through bounded, reversible, non-sensitive local work using this loop:

```text
OBSERVE -> SELECT -> STATE CLAIM -> PLAN -> IMPLEMENT
   ^                                      |
   |                                      v
RECORD <- ADVERSARIAL REVIEW <- VERIFY <- CHECK SCOPE
   |
   +-> STOP / REQUEST APPROVAL / SELECT NEXT ITEM
```

### 1. Observe

- Read `AGENTS.md`, `PROJECT_STATUS.md`, `TASKS.md`, this operating model, and applicable ADRs.
- Inspect the working tree before editing; preserve concurrent and unrelated work.
- Reproduce the current failure or run the current checks before adding features.
- Confirm that the implementation matches the documented Python and CLI contract.

### 2. Select

- Choose the highest-priority unblocked item in [BACKLOG.md](BACKLOG.md) that fits the assigned file ownership.
- Prefer P0 acceptance and kill-condition work over dashboards, integrations, refactoring, or branding.
- Claim one bounded item at a time. Do not silently take files assigned to another agent.

### 3. State the claim

Before editing, state:

- what the change is intended to establish;
- its inputs and expected observable output;
- the test or inspection that could disprove it;
- what the result will not establish.

Example: “This change establishes that an unresolved continuation token blocks a scoped negative in the seed fixture. It does not establish complete pagination for any real search system.”

### 4. Plan

- Identify dependencies, affected contracts, matched controls, and rollback.
- Use the smallest coherent change that can satisfy the definition of done.
- Add an ADR before changing a semantic invariant, canonicalization rule, trust boundary, or deployment model.

### 5. Implement

- Keep the evaluator deterministic and free of I/O.
- Preserve unknown, stale, partial, inaccessible, pending, failed, and contradictory states.
- Add a matched supported-negative control for each disqualifying fault.
- Keep diagnostics free of credentials and sensitive payloads.
- Use synthetic fixtures unless the owner has approved a specific real-data scope.

### 6. Verify

Run the narrowest relevant test first, followed by the repository checks:

```bash
./scripts/test.sh tests/path_or_test.py
./scripts/check.sh
./scripts/test.sh
./scripts/demo.sh
```

Record exact commands, runtime versions, and outcomes in the designated status or task record. A test that was not run is not passing. An interrupted run is unresolved.

### 7. Adversarial review

Attempt at least one misuse relevant to the change:

- obtain `ABSENT_WITHIN_SCOPE` with a missing required source;
- hide an unresolved continuation token;
- cross a freshness or finality boundary by one unit;
- reorder data and alter a supposedly deterministic digest;
- inject malformed, oversized, duplicate, or unexpected fields;
- strip evidence metadata between producer and gate;
- make the implementation score itself as the benchmark oracle.

### 8. Record custody

- Update the work item and status with what is implemented and verified.
- Preserve failing cases and seeds that exposed a defect.
- Update an ADR when a decision changes; do not rewrite historical rationale silently.
- Label evidence `synthetic`, `replayed`, or `directly_observed` as appropriate.
- Record limitations and excluded runs, not only successful results.

### 9. Stop or continue

Stop when the bounded item is done, an approval boundary is reached, or the same unexplained failure repeats twice. At that point, preserve evidence and request direction rather than broadening scope or weakening the check. Otherwise select the next unblocked item.

## Approval boundaries

Routine maintenance of the authorized public `redxking/evidence-state-io`
repository—including verified commits, issues, Discussions, Wiki, Pages,
project/roadmap state, metadata, and protections—is within the current owner
authorization. Explicit owner approval is required before any of the following:

- creating an unrelated external repository, message, package publication,
  official version tag/release, or project announcement;
- changing or replacing the Apache-2.0 license;
- contacting a person, vendor, design partner, or standards body;
- creating an external account or incurring cloud/API cost;
- introducing a required network, hosted-model, or external-service dependency into the core demo;
- reading non-public, personal, regulated, proprietary, classified, controlled, or export-controlled data;
- scanning, querying, faulting, or testing a system not explicitly placed in scope;
- using write-capable credentials or enabling a source adapter to mutate its target;
- deleting evidence, fixtures, volumes, branches, or user data;
- changing a P0 threshold, oracle label, exclusion rule, or claim boundary after seeing results;
- representing local, synthetic, replayed, or self-authored evidence as independent or operational validation;
- designating the project production ready.

## Safe autonomous boundary

Without additional approval, agents may:

- edit files explicitly assigned to them;
- run local read-only inspections;
- create synthetic fixtures and disposable temporary files;
- install declared development dependencies into the repository-local `.venv`;
- run unit, contract, benchmark, lint, and local demo commands;
- start the explicitly named, loopback-bound Compose lab when needed for an assigned local test;
- stop the lab without deleting its named volume.

Starting containers changes local state, so it should be announced in the work record. Fault injection must target only the Compose project defined in this repository.

## Change classification

| Change | Required treatment |
|---|---|
| Typo or link correction | Review plus documentation check |
| Internal refactor with unchanged output | Focused tests, full suite, deterministic replay |
| New fault fixture | Matched control, oracle label, gate test, benchmark inclusion |
| New adapter | Read-only design, recorded/replayed contract tests, security review |
| New state or changed state meaning | ADR, schema/policy version analysis, compatibility tests |
| Changed canonicalization or digest | ADR update, published test vectors, tamper/replay tests |
| New dependency | Justification, license/security review, owner approval if core/networked |
| Real-data or external-system use | Written scope and explicit owner approval |
| Public release or protocol proposal | Owner-authorized release process |

## Definition of done for an increment

An increment is done only when:

1. The work item has a bounded requirement and item-specific definition of done.
2. Code, schema, fixtures, tests, and documentation agree.
3. Every new fault has a matched control.
4. Focused and full checks pass, or unresolved failures are accurately recorded.
5. The core demo still runs without Docker, network, or a model.
6. Outputs remain deterministic for identical canonical inputs.
7. Security and claims boundaries were reviewed.
8. Status records say what was actually established and what was not.
9. No approval boundary was crossed.

## Handoff format

A useful agent handoff contains:

- work-item identifier and concise outcome;
- files changed;
- exact verification commands and results;
- new or remaining risks;
- assumptions and unverified behavior;
- next unblocked dependency;
- whether owner approval is required.

Avoid “complete” when the result is only specified, implemented, or locally tested.
