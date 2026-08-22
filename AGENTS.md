# Agent Instructions

## Mission

Build and falsify a deterministic evidence-state contract that prevents an empty observation from becoming an unsupported negative factual claim.

The project is a pre-alpha local research prototype. A green suite establishes behavior only in the tested environment. It does not establish source completeness, market demand, legal sufficiency, operational effectiveness, external validation, or production readiness.

## Non-negotiable invariants

1. Only `ABSENT_WITHIN_SCOPE` may permit a negative claim, and the claim must preserve its exact scope and limitations.
2. Missing, partial, stale, inaccessible, pending, failed, contradictory, or otherwise indeterminate evidence fails closed.
3. An empty payload, successful request, healthy source, or protocol completion is not coverage proof.
4. The verdict path is deterministic and contains no model inference.
5. Evaluation time, schema, evaluator, policy, registry, and fixture versions are explicit evidence-bearing inputs.
6. Every disqualifying fixture has a matched supported-negative control.
7. A digest is integrity metadata, not a signature or independent custody.
8. Synthetic, replayed, directly observed, externally reproduced, and operational evidence remain distinct.

## Start every task this way

1. Read `PROJECT_STATUS.md`, `TASKS.md`, `docs/BACKLOG.md`, and the relevant ADRs.
2. Inspect the working tree and recent files before editing. Other work may be in progress; preserve it.
3. Confirm the task's exact file ownership. Do not edit another agent's files without coordination.
4. Run the narrow current check or reproduce the failure before adding features.
5. State what the task should establish, how it will be disproved, and what it will not establish.

Do not begin by broadly refactoring or adding dependencies.

Treat `TASKS.md` as the current queue and `docs/BACKLOG.md` as the dependency model.
A checked task or an implemented file is not completion evidence unless the required
verification is recorded in `PROJECT_STATUS.md` or the task record.

## Implementation rules

- Support exactly Python 3.11, 3.12, and 3.13 for P0. Reject an untested-runtime
  claim even if the implementation happens to run elsewhere.
- Keep the core package and `evidence-state demo` offline and dependency-light.
- Keep domain evaluation free of filesystem, network, environment, wall-clock, and random-state dependencies.
- Pass `evaluation_time` explicitly.
- Reject unsupported schema and policy versions; never guess semantics.
- Preserve the schema `0.1` replay boundary. The active schema `1.0` candidate accepts exactly one declared `REQUIRED` source; optional and multi-source requests are invalid until composition is specified.
- Bind source/adapter identity, non-secret authorization context, accessible population, observations, and coverage to the normalized query; never repair a fingerprint mismatch.
- Reject malformed, ambiguous, duplicate, non-finite, or internally contradictory evidence-bearing values rather than repairing them silently.
- Put structured JSON on stdout and diagnostics on stderr.
- Use nonzero process exit codes for invalid input or program failure, not for a valid gate rejection.
- Keep source adapters read-only. Adapters translate source facts; they never grant `ABSENT_WITHIN_SCOPE` directly.
- Preserve all applicable reason codes even when policy selects one aggregate state.
- Do not introduce an HTTP service, model dependency, cloud service, or required container into P0.

## Working loop

Use the loop in `docs/OPERATING_MODEL.md`:

`observe -> select -> state claim -> plan -> implement -> verify -> adversarial review -> record -> stop/continue`

Choose the highest-priority unblocked P0 or kill-condition item that fits your assigned scope. Complete one bounded work item before selecting another.

## Required checks

Use the repository wrappers so local and CI behavior stay aligned:

```bash
./scripts/check.sh
./scripts/test.sh
./scripts/demo.sh
```

During implementation, run a focused test first:

```bash
./scripts/test.sh tests/path_or_test.py
```

If a command was not run, say so. If it was interrupted, treat it as unresolved. Do not weaken or delete a failing test merely to produce green output.

## Fault and benchmark discipline

- Hold visible results constant in matched EmptyBench pairs.
- Store oracle expectations separately from generated decisions.
- Record seeds and versions.
- Add boundary cases immediately below, equal to, and above freshness, finality, and coverage thresholds.
- Test universal-abstention and empty-result baselines so the gateway cannot appear successful by refusing everything.
- Freeze corpus, policy, oracle, and thresholds before a benchmark campaign.
- Never relabel fixtures or change exclusions after seeing results without a new version and an explicit record.

## Security and data boundaries

- Use synthetic public-safe fixtures by default.
- Never place credentials, tokens, private URLs, personal data, customer data, classified data, CUI, export-controlled data, or proprietary source contents in the repository or logs.
- Do not query, scan, or fault an external system without explicit owner and system-owner authorization.
- Optional Compose faults target only the repository's loopback-bound `evidence-state-io-lab` project.
- Do not add a destructive reset/purge script. Preserve lab volumes unless the owner explicitly requests deletion.
- Treat caller JSON, source metadata, paths, filenames, and rendered text as untrusted.

## Stop and request approval before

The owner has authorized routine public maintenance of
`redxking/evidence-state-io`: pushing verified commits, maintaining its Wiki,
Pages site, Discussions, issues, project/roadmap, repository metadata, security
settings, and branch/tag protections. This standing authorization is limited to
this repository and does not authorize announcements, outreach, package-registry
publication, real-data collection, paid services, production designation, or a
versioned GitHub Release/tag. Preserve the claim and evidence gates below.

- publishing a versioned release/tag, package, or announcement outside the
  authorized repository-maintenance boundary above;
- changing or replacing the Apache-2.0 license;
- contacting a design partner or standards body;
- incurring cloud/API cost or requiring network access;
- using real or sensitive data;
- adding write-capable source behavior;
- deleting evidence, user data, branches, or volumes;
- changing acceptance thresholds, oracle labels, or external claim language;
- claiming external validation, operational effectiveness, or production readiness.

Also stop after the same unexplained failure occurs twice. Preserve the exact evidence and ask for direction instead of broadening scope.

## File and change discipline

- Use small, reversible patches.
- Do not overwrite concurrent work.
- Add an ADR for new states, changed state meanings, canonicalization changes, new trust assumptions, or deployment-model changes.
- Update historical ADR status rather than silently rewriting the original decision.
- Keep current implementation status in the designated status/task files; do not use aspirational documentation as proof of implementation.
- Do not run destructive Git commands or discard changes that you did not create.

## Handoff

Report:

- task/backlog identifier and outcome;
- files changed;
- exact checks run and results;
- assumptions and unresolved failures;
- what the evidence establishes and does not establish;
- next dependency and any owner approval needed.

Use precise states such as specified, implemented, tested, or benchmarked. Avoid “done” when only a lower state is supported.
