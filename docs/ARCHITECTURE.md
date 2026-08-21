# Architecture

## Purpose

Evidence-State I/O is a laptop-first Python library and JSON command-line application that prevents an empty observation from being promoted into an unsupported negative factual claim. Its trusted decision path is deterministic: given the same schema version, policy ID/version, evaluator version, coverage declarations, evidence envelope, and evaluation time, it must emit the same verdict and reason codes. A complete certificate payload remains a P0 backlog item.

The P0 architecture is a modular monolith. It runs in one Python process, requires no network service, and keeps the domain model independent of the CLI, files, databases, and source-specific adapters.

This document describes the intended design. The schemas and behavior actually present in `src/evidence_state_io/`, together with passing contract tests, remain the implementation truth.

## Goals

- Distinguish `ABSENT_WITHIN_SCOPE` from incomplete, stale, inaccessible, pending, failed, contradictory, or otherwise indeterminate observation.
- Make the coverage assumptions behind every permitted negative conclusion explicit and machine-readable.
- Keep language models outside the verdict path.
- Produce replayable JSON decisions with stable reason codes and integrity metadata.
- Support matched EmptyBench cases in which the visible result is the same but coverage differs.
- Allow source adapters and storage backends to be added without changing domain semantics.
- Run the core library, CLI, demo, and tests on a Python 3.11+ laptop without Docker or external services.

## Non-goals for P0

- Proving universal or metaphysical absence.
- Discovering all enterprise data sources automatically.
- Establishing that a source's own collection or detection logic is complete.
- Allowing an LLM to override coverage policy or verdicts.
- Providing a hosted API, distributed control plane, dashboard, or production SIEM integration.
- Treating a digest as a digital signature or a local process boundary as independent custody.
- Handling non-public, personal, regulated, classified, proprietary, or export-controlled data.

## Architectural constraints

| Constraint | Consequence |
|---|---|
| Python 3.11 or newer | Type-rich standard-library-first implementation is possible. |
| JSON CLI is the P0 external interface | No HTTP server or message broker is required. |
| Core demo must work offline | Fixtures and policies are local and synthetic. |
| Verdicts must be reproducible | Time, policy, and registry versions are explicit inputs. |
| Empty results are untrusted | Coverage is evaluated separately from returned records. |
| The repository is pre-alpha research | Documentation and output must not imply operational validation. |

## System context

```text
  untrusted caller / agent / script
                 |
                 | versioned JSON evidence envelope
                 v
      +-----------------------------+
      | Evidence-State I/O process  |
      |                             |
      | parse -> normalize ->       |
      | resolve coverage ->         |
      | evaluate -> gate -> certify |
      +-----------------------------+
          |                  |
          |                  +----> deterministic JSON decision/certificate
          |
          +----> optional read-only source adapters
                     |
                     +----> synthetic fixtures in P0
                     +----> disposable laptop lab in P1
```

The caller may propose a negative claim. In the current candidate, the producer
also supplies an aggregate evidence state; the gate validates that state against
matches, coverage, source accounting, time, and policy rather than deriving the
state independently. State derivation therefore remains an explicit gap. Source
adapters report observations and collection metadata; they do not decide whether
coverage is sufficient. A future coverage registry will declare what a source is
expected to cover; it will not prove that the source actually collected every
relevant event.

## Modular monolith

The package should preserve the following logical modules even if the initial implementation uses fewer physical files.

| Module | Responsibility | Must not do |
|---|---|---|
| Contract model | Parse and validate versioned envelopes, source profiles, policies, decisions, and certificates. | Perform I/O or infer missing coverage. |
| Canonicalizer | Normalize supported JSON values and create stable bytes for comparison and hashing. | Accept NaN, infinity, unordered timestamps, or environment-dependent values. |
| Source-accounting evaluator | For the schema `1.0` candidate, compare one declared required source with its runtime identity, adapter, authorization context, accessible population, status, and errors. | Compose multiple sources or treat a matching label as proof of source honesty. |
| Coverage resolver | Compare coverage facts with the query-bound coverage object and policy; later compare against governed source profiles. | Treat source health alone as proof of query coverage. |
| Evidence evaluator | Produce an evidence state and complete set of stable reason codes from explicit inputs. | Call an LLM, current-time function, network, or mutable global state. |
| Negative-claim gate | Permit only a bounded, scoped negative when the evaluator returns `ABSENT_WITHIN_SCOPE`; block or qualify all other negative claims. | Rewrite an indeterminate state as absence. |
| Certificate builder | Bind normalized inputs, versions, decision, evaluation time, and integrity digest into replayable output. | Call a digest a signature unless an actual signing profile is implemented. |
| Benchmark harness | Run paired cases and compare the gate with baselines using an independent expected-outcome oracle. | Use the implementation's verdict as its own ground truth. |
| CLI adapter | Read JSON, select a command, call application services, and write JSON to stdout with diagnostics on stderr. | Contain domain decisions or require a network service. |
| Source adapters | Translate source-specific observations into the common envelope through read-only interfaces. | Grant `ABSENT_WITHIN_SCOPE` directly. |
| Repository adapters | Optionally persist registries, envelopes, and certificates. | Change an already issued certificate in place. |

## Core conceptual contracts

Field names below are conceptual. The versioned JSON schema in the implementation is authoritative.

### Query specification

A query must identify enough scope to evaluate coverage:

- target and predicate;
- descriptive authorization boundary and a stable non-secret authorization-context identifier;
- start and end of the observation interval;
- exclusions;
- exactly one schema `1.0` candidate source requirement, including source ID,
  system, locator, adapter ID/version, accessible population, and nonempty
  detection assumptions.

The normalized query has a canonical SHA-256 fingerprint. Both runtime source
observations and aggregate coverage must carry that fingerprint. Multiple
sources, per-source coverage, fields/projection structure, profile references,
and an explicit finality horizon remain later contract work.

A free-form natural-language question alone is not a query specification.

### Source coverage profile

A registry profile declares:

- source identifier and profile version;
- owning authority and declared authoritative scope;
- populations and fields collected;
- retention and known blind intervals;
- maximum acceptable freshness and expected update cadence;
- access and tenant/partition assumptions;
- pagination or completeness mechanism;
- detection assumptions and known exclusions;
- finality or late-arrival behavior.

Profiles are assertions under configuration control. Their truth must be validated separately; the gateway only evaluates whether runtime evidence satisfies the declared profile and policy.

### Source observation

Each source observation should bind:

- source identity, adapter ID/version, and eventually a profile version;
- canonical query fingerprint and effective filters;
- observation interval;
- access identity or access-boundary label, without embedding credentials;
- page/cursor completion evidence when applicable;
- source timestamp, retrieval timestamp, and declared clock basis;
- records or a stable summary of the visible result;
- adapter outcome and structured fault information;
- known exclusions, truncation, or transformation notes.

An empty record list is only an observation. It is not an evidence-state verdict.

The active candidate implements source/adapter identity, authorization-context,
population, status, error, query-fingerprint, and index-timestamp checks. It does
not yet implement a profile registry, independently attested source identity, or
explicit finality semantics.

### Evaluation result

The current gate decision returns:

- a permit/reject disposition after checking the producer-supplied aggregate state;
- all applicable stable reason codes, not only the highest-priority reason;
- a gate disposition;
- the precise scope text or structured scope allowed for a supported negative;
- an explicit evaluator version;
- a deterministic digest of the normalized request, which includes schema,
  policy, source bindings, and caller-supplied evaluation time.

The complete self-describing certificate still needs to expose and bind schema,
policy, evaluator, profile, origin, evaluation time, decision, and certificate
format as one canonical issued object.

Initial states are `PRESENT`, `ABSENT_WITHIN_SCOPE`, `NOT_OBSERVED`, `PARTIAL`, `STALE`, `INACCESSIBLE`, `PENDING_WINDOW`, `FAILED`, and `CONTRADICTORY`.

### Gate disposition

The external disposition is intentionally smaller than the evidence vocabulary:

| Evidence result | Negative-claim disposition |
|---|---|
| `ABSENT_WITHIN_SCOPE` | Permit only the generated scoped negative. |
| `PRESENT` | Refuse the negative claim; positive evidence exists. |
| Any indeterminate or contradictory state | Block an unqualified negative and return the unresolved conditions. |

Explanatory language may be generated outside the trusted decision path, but it must quote or reference the structured disposition and may not broaden it.

## Data flow

1. The caller supplies a schema `1.0` candidate request and its explicit policy identity/configuration.
2. The contract layer rejects unknown schemas/policies, malformed time, missing scope, any source count other than one required source, duplicate/undeclared observations, and unsupported JSON values.
3. The query model creates a canonical fingerprint; the envelope rejects coverage or observations bound to another query.
4. Source accounting compares declared identity, adapter, authorization context, accessible population, status, and errors.
5. Coverage evaluation checks the query-bound aggregate coverage facts under the named policy.
6. The gate checks the producer-supplied aggregate state, matches, source and coverage assessments, freshness, index chronology, and validity. Only an entirely reason-free request permits a scoped negative.
7. The current decision includes the normalized-request digest and evaluator version. The complete certificate builder is not yet implemented.
8. The CLI writes machine-readable output to stdout and structured invalid-input diagnostics to stderr.
9. Replaying the same normalized request reproduces the same decision and digest.

## Determinism and time

- Domain functions receive `evaluation_time`; they do not read the wall clock.
- Timestamps use RFC 3339 with an explicit offset and are normalized before comparison.
- Policies define boundary behavior, including whether equality at a freshness or finality limit is accepted.
- JSON canonicalization rejects values that do not have portable representations.
- Collections that are semantically unordered are sorted by stable identifiers before hashing.
- Reason-code ordering is defined and tested.
- Randomized tests must record seeds.

Determinism establishes reproducibility of the implementation. It does not establish that a coverage declaration is true or that a source observed the world completely.

## Persistence

P0 requires no database. Commands operate on explicit JSON inputs and emit explicit JSON outputs. Fixtures live in the repository, and callers choose whether to persist outputs.

An optional repository port may later support SQLite for a single-user laptop ledger. Postgres in `compose.yaml` is a disposable adapter/fault laboratory, not a P0 runtime dependency. Any persistent implementation must be append-oriented: a correction creates a new version that links to the superseded object rather than silently changing an issued certificate.

## Adapter boundary

The application layer should define small protocols similar to:

```python
class CoverageRegistryPort(Protocol):
    def resolve(self, query: QuerySpec) -> RegistrySnapshot: ...

class SourceObserverPort(Protocol):
    def observe(self, query: QuerySpec) -> SourceObservation: ...

class CertificateRepositoryPort(Protocol):
    def append(self, certificate: EvidenceCertificate) -> None: ...
```

Adapters translate; they do not decide. A source-specific `200 OK`, empty array, successful search job, or healthy status endpoint cannot bypass the coverage evaluator.

## CLI boundary

The installed command is `evidence-state`. The P0 command contract is:

- `evidence-state evaluate --input <path-or->` evaluates one envelope and writes JSON.
- `evidence-state demo` runs the local paired covered/partial demonstration.
- `evidence-state --help` is side-effect free.

`-` denotes stdin where supported. Structured output goes to stdout; diagnostics go to stderr. Successful evaluation may still produce a blocked negative claim, so the JSON disposition—not process exit status—communicates the evidence decision. Nonzero exit status is reserved for invalid input, unavailable local dependencies, or internal execution failure.

## EmptyBench isolation

EmptyBench fixtures and their expected outcomes are test inputs, not runtime policy. The expected-outcome oracle must be stored independently from generated decisions. Paired cases should hold the visible records and user question constant while changing one coverage condition. Each new fault case requires a matched control so a system cannot score well by refusing every negative conclusion.

## Laptop deployment

```text
Host Python process
  evidence-state CLI
    -> in-process contracts/evaluator/gate/certificate
    -> local JSON fixtures
    -> stdout JSON

Optional Compose profile `lab`
  Postgres synthetic source <- Toxiproxy fault boundary
```

The optional containers bind only to loopback, contain synthetic data, and are not required by the core suite. See [LAPTOP_LAB.md](LAPTOP_LAB.md).

## Security boundaries

- Caller-provided JSON is untrusted.
- Registry profiles and policies are privileged configuration and require review/versioning.
- Source observations may be incomplete, forged, stale, or produced with insufficient access.
- The evaluator and canonicalizer form the P0 trusted computing base.
- Local digests detect accidental or subsequent modification only when a trusted copy of the expected digest exists.
- A single laptop process does not provide independent observation, tamper-proof custody, multi-party authorization, or non-repudiation.

The full threat model is in [../SECURITY.md](../SECURITY.md).

## Failure behavior

| Failure | Required behavior |
|---|---|
| Unknown schema/policy version | Reject input; do not evaluate under guessed semantics. |
| Coverage or observation bound to another query | Reject input before evaluation. |
| Source identity, adapter, authorization context, or population mismatch | Block negative with a source-attributed reason. |
| Missing required source | Preserve `PARTIAL` or the policy-defined indeterminate state; block negative. |
| Source inaccessible | Preserve `INACCESSIBLE`; block negative. |
| Observation older than policy | Preserve `STALE`; block negative. |
| Incomplete pagination or filtered population | Preserve `PARTIAL`; block negative. |
| Finality horizon not reached | Preserve `PENDING_WINDOW`; block negative. |
| Adapter failure | Preserve `FAILED`; block negative. |
| Conflicting authoritative observations | Preserve `CONTRADICTORY`; block negative. |
| Optional or multiple declared sources in schema `1.0` candidate | Reject input; multi-source coverage composition is not defined. |
| Unexpected internal exception | Return a nonzero CLI status without emitting a permitted negative. |
| Certificate persistence failure | Report failure; do not claim durable custody. |

When several failures apply, the output retains all reason codes. Aggregate-state precedence is versioned policy and must be contract-tested; it must never erase the underlying reasons.

## Evolution rules

- Additive optional JSON fields may remain within a schema version only when old implementations can ignore them safely.
- New required fields, changed state meanings, changed boundary comparisons, or changed canonicalization require a new schema or policy version.
- New evidence states require an ADR, gate mapping, matched benchmark cases, and compatibility tests.
- New adapters begin read-only and synthetic. Real-data use crosses an owner approval boundary.
- A future HTTP service should wrap the application layer; it must not move policy into handlers or make network availability a core requirement.

## Related decisions

- [ADR-0001](adr/0001-laptop-first-modular-monolith.md)
- [ADR-0002](adr/0002-versioned-json-and-pure-evaluator.md)
- [ADR-0003](adr/0003-fail-closed-scoped-negative-gate.md)
- [ADR-0004](adr/0004-separate-coverage-declarations-from-observations.md)
- [ADR-0005](adr/0005-canonical-certificates-and-digest-boundary.md)
- [ADR-0006](adr/0006-disposable-opt-in-fault-lab.md)
- [ADR-0007](adr/0007-schema-1-source-accounting-and-version-boundaries.md)
