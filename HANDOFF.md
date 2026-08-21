# Project Handoff

## Mission

Create and validate an open evidence-state contract and reference gateway that prevent AI systems from turning non-observation into an unsupported negative conclusion.

This file is the entry point for a human engineer or an autonomous coding agent continuing the project.

## What exists at handoff

The repository is expected to contain:

- a product requirements document with explicit goals and non-goals;
- architecture decisions and a laptop-first deployment design;
- a typed evidence-envelope model;
- a deterministic coverage evaluator and negative-claim gate;
- a command-line interface suitable for scripts and demonstrations;
- paired benchmark fixtures covering at least one supported-negative and one partial-coverage case;
- automated tests and continuous integration;
- a staged engineering and research backlog;
- explicit claim, safety, security, and approval boundaries.

Use `PROJECT_STATUS.md` and the test results to determine what is actually implemented. This document describes the intended handoff package; it does not substitute for verification.

## First operating instruction

Do not begin by adding features. Begin by running the existing checks, reading the open risks, and reproducing the paired-case demonstration.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install '.[dev]'
pytest
env -u PYTHONPATH .venv/bin/evidence-state demo
```

If the test command or documented demonstration fails, repair or accurately document that failure before taking new backlog work. Run the installed-command check with `PYTHONPATH` unset: the repository wrappers intentionally exercise current `src/`, while the installed command verifies the package an operator will actually invoke.

## Continuous work loop

An active Codex heartbeat named **Advance Evidence-State I/O** is attached to the originating task and scheduled daily at 9:00 AM in the task's local timezone. Its automation identifier is `advance-evidence-state-i-o`. The heartbeat follows the loop and approval boundaries below; it does not create authority to publish, deploy, spend materially, or use sensitive data.

For every continuation cycle:

1. **Observe** — inspect `PROJECT_STATUS.md`, the highest-priority backlog items, recent changes, test results, and unresolved risks.
2. **Select** — choose one bounded, unblocked work item that advances a P0 acceptance criterion or tests a kill condition.
3. **State the claim** — write down what the change is expected to establish and what it cannot establish.
4. **Implement** — make the smallest coherent change, including negative and fault-path behavior.
5. **Verify** — run focused tests, then the full local suite. Record exact commands and outcomes.
6. **Adversarially review** — attempt to produce an unsupported `ABSENT_WITHIN_SCOPE`, bypass the gate, or create an unverifiable certificate.
7. **Update custody** — update status, backlog, decisions, risks, and reproducibility notes in the same change.
8. **Stop or continue** — stop at an approval boundary; otherwise begin the next highest-value cycle.

Never report “done” solely because code was written or a test was green. Use the delivery states below.

## Delivery states

- **Specified:** requirement and acceptance criteria exist.
- **Implemented:** code exists and was locally inspected.
- **Tested:** named automated tests passed in a recorded environment.
- **Benchmarked:** a frozen campaign produced reproducible measurements.
- **Externally reproduced:** an independent party reran the frozen campaign.
- **Operationally evaluated:** tested with authorized real workflows and bounded claims.
- **Production ready:** requires a separate security, reliability, legal, operational, and deployment decision.

No state implies the next one.

## Priority order

Unless evidence changes the plan, work in this order:

1. Preserve the first local schema `0.1` freeze while adding explicit required-versus-observed source accounting.
2. Add a supplied finality horizon and exact below/equal/above boundary behavior.
3. Complete the deterministic evidence certificate and bind policy/evaluator versions; keep digest and signature semantics separate.
4. Freeze a minimum paired EmptyBench corpus with a separately governed scoring oracle.
5. Establish baseline model/tool behavior on that frozen corpus and apply the go/no-go thresholds without reinterpretation.
6. If the gate passes, add one real read-only adapter and a source-coverage profile under owner-approved authority and data boundaries.
7. Run approved discovery and shadow evaluation with design partners, then seek external reproduction.
8. Consider signing, protocol proposals, and additional domains only after the first evidence package is frozen and the applicable approval gates are crossed.

## Approval boundaries

Continue autonomously through local, reversible, non-sensitive development and testing. Stop and obtain explicit owner approval before:

- publishing or distributing the repository;
- selecting or changing a license;
- creating external accounts, repositories, issues, pull requests, or messages;
- deploying into a production or third-party environment;
- ingesting non-public, personal, regulated, proprietary, classified, or export-controlled data;
- scanning or testing systems that were not explicitly placed in scope;
- incurring material cloud or API cost;
- changing acceptance thresholds or claim language to make results appear stronger;
- representing synthetic, replayed, or local evidence as customer or operational validation.

## Definition of a useful increment

A useful increment must do at least one of the following:

- close a P0 acceptance criterion;
- add a fault class plus matched control and scoring rule;
- reduce an identified false-absence path;
- improve reproducibility or tamper resistance;
- test a project-killing assumption;
- produce evidence from an authorized design-partner workflow.

Pure refactoring, dashboards, branding, and broad framework integrations do not take priority while a P0 evidence or falsification item remains open.

## Decision authority

The project owner retains authority over external release, licensing, commercial positioning, real-data use, deployment, partnerships, and claims. Agents may maintain proposed recommendations in the repository but may not silently convert proposals into owner decisions.
