# Continuous Project Operation

## Purpose

Evidence-State I/O is maintained as a bounded research and engineering program,
not as an unattended feature factory. A recurring agent may advance one
highest-priority unblocked item at a time, but it must preserve the evidence,
authorization, and release boundaries in this repository.

The owner's current Codex workspace has a daily recurring task named
`Advance Evidence-State I/O`. The task is an execution aid, not part of the
protocol and not evidence that work, review, or publication occurred. This file
is the portable handoff for recreating the operating loop in another scheduler.

## Recurring run contract

Each run shall:

1. Read `AGENTS.md`, `PROJECT_STATUS.md`, `TASKS.md`, `docs/BACKLOG.md`, and the
   applicable ADRs.
2. Inspect repository, remote, issue, project, workflow, and Pages state before
   making a claim about them.
3. Select one highest-priority unblocked item whose inputs and decision rights
   are available.
4. State the bounded claim, disproof test, affected contracts, and what the work
   cannot establish.
5. Implement a reversible increment; add matched controls for any new fault.
6. Run focused tests and then the repository checks required by `AGENTS.md`.
7. Attempt an adversarial bypass appropriate to the change.
8. Record exact evidence and limitations in `PROJECT_STATUS.md`, `TASKS.md`, and
   `docs/REVIEW_LOG.md` when applicable.
9. Push only a coherent, verified commit. Use issues and the project board to
   reflect work state; do not equate a closed issue with validated evidence.
10. Stop at an approval boundary or after the same unexplained failure repeats
    twice. Preserve the failure instead of weakening a test or claim.

## Inputs and outputs

Required inputs are the repository at a known revision, the current task and
backlog records, local supported Python runtimes, and GitHub state for the
authorized public repository. Network access is optional for local engineering
and required only for explicitly authorized synchronization with GitHub.

A useful run produces one or more of:

- a verified local increment and its tests;
- a falsifying fixture or preserved failure;
- an updated ADR or acceptance record;
- an issue or project-state update grounded in the actual revision;
- a pushed commit whose checks can be independently inspected.

A run must not report publication, workflow success, Pages availability,
benchmark custody, or external reproduction unless that state was independently
observed during the run.

## Portable recurring prompt

The scheduler-ready prompt is versioned at
[`automation/heartbeat_prompt.md`](../automation/heartbeat_prompt.md). Keep that
prompt short; the repository documents are the source of truth.

## Stop conditions

Pause and report instead of improvising when:

- a required oracle, expected digest, authority input, runtime, or external
  observation is unavailable;
- the working tree contains overlapping changes whose ownership is unclear;
- tests expose a contract ambiguity requiring a version decision;
- work would use sensitive data, write to an external source, incur cost, create
  a release/tag, contact people, or make a production-readiness claim;
- GitHub state cannot be verified after a requested synchronization.

These stop conditions keep continuity from becoming accidental autonomy.
