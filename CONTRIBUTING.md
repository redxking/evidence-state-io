# Contributing

## Current contribution boundary

Evidence-State I/O is a pre-alpha research prototype. No owner-approved public license has been selected. Do not publish, redistribute, package, or treat the repository as open source unless the project owner records a licensing and release decision.

This guide supports owner-authorized local contributors. External contribution mechanics may be added after a release decision.

## Before you begin

Read:

1. [AGENTS.md](AGENTS.md)
2. [PROJECT_STATUS.md](PROJECT_STATUS.md)
3. [docs/PRD.md](docs/PRD.md)
4. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
5. [docs/BACKLOG.md](docs/BACKLOG.md)
6. [SECURITY.md](SECURITY.md)

Confirm the task, file ownership, acceptance criteria, and approval boundary before editing. Preserve unrelated or concurrent changes.

## Development setup

Use Python 3.11 or newer and the repository-local environment:

```bash
./scripts/setup.sh
source .venv/bin/activate
```

The setup installs a non-editable package snapshot inside `.venv`; it does not
modify global Python packages. The check, test, and demo wrappers then put the
current checkout's `src` directory first on `PYTHONPATH`, so normal source edits can
be exercised offline while still using the installed console entry point. Rerun
setup after changing dependencies, packaging metadata, or entry points.
Editable-install support is not currently claimed.

The core package deliberately has no required network, model, database, or container dependency. Docker is optional and used only for the bounded fault lab.

## Development workflow

1. Reproduce the current behavior or failure.
2. Select one unblocked backlog item.
3. Define the claim and falsification test for the change.
4. Implement the smallest coherent increment.
5. Add positive, negative, boundary, malformed-input, and deterministic tests as applicable.
6. Add a matched supported-negative control for each new fault fixture.
7. Run focused tests, then the full checks and demo.
8. Update the applicable task/status record and documentation without overstating evidence.

```bash
./scripts/test.sh tests/path_or_test.py
./scripts/check.sh
./scripts/test.sh
./scripts/demo.sh
```

## Code design expectations

- Domain models are immutable where practical.
- The evaluator is pure: no wall-clock, network, filesystem, environment, or mutable-global reads.
- JSON decoding is strict and rejects unknown evidence-bearing fields unless a versioned compatibility rule explicitly allows them.
- `evaluation_time` is supplied, normalized, and certificate-bound.
- Collections that are semantically unordered have deterministic ordering.
- Schema `1.0` candidate requests declare exactly one `REQUIRED` source; do not add optional or multi-source behavior without a new composition decision.
- Source identity, adapter identity/version, authorization context, and accessible population must match; observations and aggregate coverage bind to the normalized query fingerprint.
- Adapters implement narrow read-only ports and expose pagination, partitions, access limits, finality, freshness, and errors.
- Explanatory prose cannot upgrade or override the structured gate decision.
- Diagnostics go to stderr; machine-readable results go to stdout.

## Adding or changing an evidence state

A new state or changed meaning requires:

1. an accepted ADR;
2. schema and policy compatibility analysis;
3. a documented gate disposition;
4. validation and transition invariants;
5. one or more disqualifying fixtures plus matched controls;
6. oracle and benchmark updates;
7. deterministic serialization tests;
8. a clear migration or unsupported-version behavior.

Do not map a novel failure silently to a convenient existing state merely to avoid a schema decision.

## Adding a fault fixture

Each fault case must record:

- the single coverage condition changed from its control;
- identical visible result and user question where the paired design requires it;
- expected state, gate disposition, and stable reason codes;
- evidence origin (`synthetic`, `replayed`, or `directly_observed`);
- policy, fixture, and schema versions;
- whether the case is included in the frozen campaign.

The expected-outcome oracle must remain independent of the implementation under test.

## Adding a source adapter

Adapters begin read-only and synthetic/replayed. Document:

- authorization and accessible-population boundary;
- population and field semantics;
- pagination, partition, snapshot, and continuation behavior;
- retention, freshness, blind intervals, and finality;
- truncation, rate-limit, timeout, permission, parsing, and query errors;
- data classification and redaction;
- why an empty response does not self-certify completeness.

Accessing a real service, using an account, or handling non-public data requires explicit approval.

## Tests

Tests should cover:

- all normative state meanings and gate mappings;
- invalid state/schema/policy versions;
- zero, null, unknown, empty, duplicate, and non-finite values;
- wrong source/adapter/auth context, stale query fingerprints, and optional/multi-source downgrade attempts;
- coverage/freshness/finality values below, at, and above thresholds;
- input key and semantically unordered collection reordering;
- deterministic replay and one-field certificate mutation;
- malformed and oversized input without stdout stack traces;
- universal-abstention and naive-empty baselines;
- adapter-specific partial and failure paths.

Do not update golden files blindly. Review semantic differences before accepting a new output.

## Documentation and ADRs

- Update docs in the same change as externally observable behavior.
- Link rather than duplicate normative definitions.
- Use “proposed,” “implemented,” “tested,” or “benchmarked” precisely.
- ADR filenames use `NNNN-short-title.md` and retain historical context.
- Supersede an accepted ADR with a new ADR or explicit status change; do not erase its rationale.

## Commit and review guidance

Keep changes reviewable and scoped. A useful commit message names the behavior, for example:

```text
gate: reject unresolved continuation tokens
```

An owner-authorized review should answer:

- Which requirement or kill condition does this address?
- Can the change accidentally permit an unsupported negative?
- Is there a matched control?
- Are oracle, policy, and implementation independent?
- Is output deterministic?
- Did the security or claims boundary change?
- What was actually run and observed?

Do not create an external pull request or publish a branch without owner approval.

## Reporting security concerns

Follow [SECURITY.md](SECURITY.md). Do not place exploit details, sensitive fixtures, credentials, or private-system information in a public issue or chat.
