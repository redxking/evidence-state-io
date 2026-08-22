# Contributing

## Current contribution boundary

Evidence-State I/O is an Apache-2.0 open-source pre-alpha research project.
Issues, discussions, and pull requests are welcome within the documented claim,
data, and safety boundaries. Public availability is not a stable release,
standard, production authorization, or claim of independent validation.

By contributing, you agree that your contribution is licensed under the
project's [Apache License 2.0](LICENSE). Follow the
[Code of Conduct](CODE_OF_CONDUCT.md) and [governance model](GOVERNANCE.md).

## Before you begin

Read:

1. [PROJECT_STATUS.md](PROJECT_STATUS.md)
2. [docs/PRD.md](docs/PRD.md)
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
4. [docs/BACKLOG.md](docs/BACKLOG.md)
5. [SECURITY.md](SECURITY.md)
6. [GOVERNANCE.md](GOVERNANCE.md)

Confirm the task, file ownership, acceptance criteria, and approval boundary before editing. Preserve unrelated or concurrent changes.

## Development setup

Use Python 3.11, 3.12, or 3.13 and the repository-local environment:

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

The current `evaluate` interface also requires application-controlled registry
and trust files plus explicit issuance time and origin. For the synthetic
checked-in permit vector:

```bash
evidence-state evaluate \
  --input examples/covered_request.json \
  --registry examples/profile_registry.json \
  --trust examples/profile_trust.json \
  --issued-at 2026-08-21T12:06:00Z \
  --origin SYNTHETIC
```

Do not make the registry snapshot, trust selection, or their exact selected
profile reference writable by the producer under test. These files provide a
local application custody boundary, not authenticated registry or source
evidence.

## Code design expectations

- Domain models are immutable where practical.
- The evaluator is pure: no wall-clock, network, filesystem, environment, or mutable-global reads.
- JSON decoding is strict and rejects unknown evidence-bearing fields unless a versioned compatibility rule explicitly allows them.
- `evaluated_at` is supplied, normalized, and certificate-bound.
- Collections that are semantically unordered have deterministic ordering.
- Schema `1.0` candidate requests declare exactly one `REQUIRED` source; do not add optional or multi-source behavior without a new composition decision.
- Source identity, adapter identity/version, authorization context, and accessible population must match; observations and aggregate coverage bind to the normalized query fingerprint.
- The relying application selects one exact immutable profile reference through a separately supplied registry/trust context. Producers cannot select another profile, use floating/range versions, or cause untrusted profile content to be evaluated before exact trust resolution.
- Adapters implement narrow read-only ports and expose pagination, partitions, access limits, finality, freshness, and errors.
- P0 certificates are unsigned deterministic replay records, not authenticated attestations or authorization tokens. Current local reliance and historical replay are separate verification dimensions.
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
- an exact evidence-origin label (`SYNTHETIC`, `REPLAYED`, `LAB_OBSERVED`,
  `SHADOW_OBSERVED`, `EXTERNALLY_REPRODUCED`, or `OPERATIONAL`), without
  treating the unauthenticated label as proof;
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

The P0 certificate embeds the complete normalized request, registry snapshot,
trust selection, context binding, decision, limitations, origin, and
implementation metadata. It is not data-minimized. Use only synthetic/public-
safe or owner-approved nonsensitive content, and review every embedded field
before retaining or sharing a certificate. Non-public workflows require a P1
authenticated registry/source-evidence design and a separately versioned
redaction, reference, minimization, or selective-disclosure profile.

## Tests

Tests should cover:

- all normative state meanings and gate mappings;
- invalid state/schema/policy versions;
- zero, null, unknown, empty, duplicate, and non-finite values;
- wrong source/adapter/auth context, stale query fingerprints, and optional/multi-source downgrade attempts;
- producer-selected weak profiles; snapshot/profile identity, digest, issuer, authority, validity, and revocation failures; immutable-version downgrade attempts; and proof that trust failures short-circuit before profile semantics;
- coverage/freshness/finality values below, at, and above thresholds;
- input key and semantically unordered collection reordering;
- permit and rejection certificate vectors; deterministic replay; one-field certificate mutation; forged-decision replay; expected-context/digest mismatch; freshness expiry; and current-local-reliance boundaries;
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
- Were registry/trust/profile inputs supplied through the application-controlled, producer-unwritable boundary?
- Does any self-contained certificate expose data that is not approved for its destination?
- What was actually run and observed?

Use a focused branch and open a pull request with the repository template. A
pull request is a proposal: review, green automation, or maintainer discussion
does not by itself establish acceptance, contract freeze, or release approval.

## Reporting security concerns

Follow [SECURITY.md](SECURITY.md). Do not place exploit details, sensitive fixtures, credentials, or private-system information in a public issue or chat.
