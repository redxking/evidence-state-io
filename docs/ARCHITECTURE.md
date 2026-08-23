# Architecture

## Purpose

Evidence-State I/O is a laptop-first Python library and JSON command-line
application that prevents an empty observation from being promoted into an
unsupported negative factual claim. The 0.6.0 development candidate evaluates
one query-bound source against an application-controlled coverage/finality
profile, gates the proposed negative claim, and emits a deterministic unsigned
evidence certificate containing the complete replay input and decision.

The trusted decision path is deterministic: the same supported contracts,
normalized request, trusted profile context, evaluation time, issuance time,
origin, and implementation identity produce the same canonical certificate
bytes and SHA-256 digest. Determinism establishes reproducibility of supplied
facts; it does not authenticate those facts or establish that the source
observed the world completely.

The P0 architecture remains a modular monolith. It runs in one Python process,
requires no network service, and keeps domain behavior independent of the CLI,
files, databases, and source-specific adapters. Schema `1.0` and all contracts
identified as candidates below remain unfrozen research contracts.

## Active candidate contracts

| Contract | Exact supported identifier |
|---|---|
| Package | `evidence-state-io 0.6.0` |
| Wire schema | `1.0` (unfrozen candidate) |
| Policy | `esio-p0-safety-floor` / `1.0-candidate.4` |
| Evaluator | `esio-evaluator-1.0-candidate.5` |
| Evaluation input | `esio-evaluation-input/1.0-candidate.2` |
| Coverage/finality profile | `esio-coverage-finality-profile/1.0-candidate.2` |
| Registry snapshot | `esio-profile-registry-snapshot/1.0-candidate.2` |
| Trust selection | `esio-profile-trust-selection/1.0-candidate.2` |
| Evidence certificate | `esio-evidence-certificate/1.0-candidate.2` |
| Evidence-state transitions | `esio-evidence-state-transition-model/1.0-candidate.1` |
| Authorization-context identifier | `esio-authorization-context-identifier/1.0-candidate.1` |
| Validation error | `esio-validation-error/1.0-candidate.1` |
| EmptyBench corpus | `esio-emptybench-corpus/1.0-candidate.1` |
| EmptyBench oracle | `esio-emptybench-oracle/1.0-candidate.1` |
| EmptyBench report | `esio-emptybench-report/1.0-candidate.1` |
| Canonical JSON profile | `esio-canonical-json-0.1` |
| Digest algorithm | `sha256` |

The parser accepts only these exact identifiers. Numeric versions, floating
aliases, ranges, unknown revisions, and silent downgrade/fallback behavior are
not supported. The historical schema `0.1` fixture remains hash-bound for
replay at its historical checkpoint; it is not an active 0.6.0 input contract.

Historical pre-integration implementation evidence is bound to
`be0774680aa83052eeecab29e1a0ab38824f2860` and retained in
`TRACEABILITY.md`. It is not current custody. The successor implementation and
documentation revisions remain `PENDING POST-REMEDIATION CUSTODY` after the
typed EmptyBench scoring boundary was hardened. No implementation checkpoint
freezes schema `1.0` or EmptyBench, establishes external validation, or
authorizes production use.

## Goals

- Distinguish `ABSENT_WITHIN_SCOPE` from incomplete, stale, inaccessible,
  pending, failed, contradictory, or otherwise indeterminate observation.
- Make the scope, profile, source, freshness, finality, and trust assumptions
  behind every permitted negative conclusion explicit and machine-readable.
- Keep language models outside the verdict path.
- Produce self-contained replay records with stable reason codes, exact
  contract identifiers, canonical bytes, and integrity metadata.
- Support matched EmptyBench cases in which the visible result is the same but
  coverage differs.
- Run the core library, CLI, demo, and tests on Python 3.11, 3.12, or 3.13 on a laptop without
  Docker or external services.

### Integration surface

`evidence_state_io.mcp_server` is a stdio MCP server over the same pure
evaluator the CLI and library use. It adds no evaluation logic: the acceptance
gate replays a fixed frame sequence through the installed server and requires
the served decision to equal one computed directly from the library, so the
transport cannot become a second evaluator.

It has no SDK dependency, in keeping with the package's zero-runtime-dependency
property, and answers both the pre-`2026-07-28` `initialize` handshake and the
stateless `server/discover` path that replaced it.

## Non-goals for P0

- Proving universal or metaphysical absence.
- Establishing that source, profile, registry, issuer, approval, or trust
  declarations are independently true or authenticated.
- Discovering all enterprise data sources, or composing coverage across
  sources that cover disjoint parts of a population. Schema `1.1` composes only
  corroborating sources, whose coverage never accumulates.
- Allowing an LLM to override coverage policy or verdicts.
- Providing signatures, trusted timestamps, independent custody,
  non-repudiation, or action authorization.
- Providing a hosted API, distributed control plane, dashboard, or production
  integration.
- Handling non-public, personal, regulated, classified, proprietary, or
  export-controlled data. The current self-contained certificate embeds the
  full normalized request and trusted profile context; current fixtures and
  use must therefore remain synthetic and non-sensitive.

## System and trust context

```text
 producer request (untrusted)                application configuration
 envelope + exact profile reference          registry snapshot + trust selection
                    \                         /
                     \                       /
                      v                     v
                 +----------------------------------+
                 | Evidence-State I/O process       |
                 | strict parse and normalize       |
                 | staged profile trust             |
                 | source and coverage evaluation   |
                 | negative-claim gate              |
                 | builder-owned evaluation         |
                 | canonical certificate issuance   |
                 +----------------------------------+
                                  |
                                  v
                    unsigned replay certificate
```

The producer request carries only an exact `CoverageProfileReference`. It does
not carry the profile body, registry snapshot, or trust selection. The
application supplies those objects on a separate boundary and selects the
single exact profile reference in the trust selection. A request cannot choose
a different, weaker profile merely because that profile also appears in the
trusted snapshot.

The producer still supplies the aggregate evidence state and observation
facts. The gate checks their internal consistency, source accounting, profile
applicability, coverage, freshness, finality, and policy; it does not derive
source truth independently. That remains a deliberate evidence boundary.

## Modular monolith

| Module | Responsibility | Must not do |
|---|---|---|
| Contract model | Strictly parse and validate requests, profiles, snapshots, trust selections, decisions, and certificates. | Perform I/O or guess unsupported versions. |
| Canonicalizer | Normalize supported JSON values and produce stable bytes and digests. | Accept NaN, infinity, duplicate keys, lossy numbers, or environment-dependent values. |
| Profile resolver | Apply staged snapshot and profile trust, exact reference resolution, applicability, finality, retention, blind-interval, and freshness checks. | Use untrusted snapshot/profile semantics to drive a favorable decision. |
| Source-accounting evaluator | Compare the one declared source with runtime identity, adapter, authorization context, population, status, errors, and query binding. | Compose multiple sources or treat matching labels as proof of truth. |
| Evidence evaluator | Produce a deterministic decision and complete stable reasons from explicit inputs. | Read the wall clock, network, filesystem, or mutable global state. |
| Negative-claim gate | Permit only the generated bounded negative when every required check passes. | Rewrite indeterminate evidence as absence. |
| Certificate builder | Own evaluation and bind request, trusted context, contract IDs, origin, times, decision, implementation identity, and validity boundary. | Accept a caller-created decision or call a digest a signature. |
| Certificate verifier | Reparse, check structural support and bindings, reproduce the decision, and report separately supplied custody-comparison and current-use dimensions. | Emit one aggregate `valid` assertion or establish issuer identity/authorization. |
| Benchmark harness | Compare paired cases with a separately stored, versioned, corpus-bound expected-outcome oracle. | Use the implementation verdict as its own ground truth or describe author-controlled separation as independent adjudication. |
| CLI adapter | Read strict JSON, supply application context, call domain services, and separate stdout from diagnostics. | Contain domain policy or require a network service. |

## Core contracts

### Query and source requirement

A schema `1.0` candidate query declares target, predicate, descriptive
authorization boundary, stable non-secret authorization-context ID, time
interval, exclusions, and exactly one required source. The source requirement
binds source/system/locator, exact adapter ID and immutable version, accessible
population, nonempty detection assumptions, an exact profile reference, and a
profile-derived finality horizon.

A schema `1.1` query additionally declares `composition` and may name up to
four required sources. Each source observation then carries its own coverage,
state, match count, and observation time, and each source is checked against
its own profile-derived horizon. Schema `1.0` may declare neither, and every
`1.1` field is omitted from the canonical form when absent, so a `1.0` record
keeps its exact meaning, fingerprint, and digest.

The normalized query has a canonical SHA-256 fingerprint. Aggregate coverage
and every source observation must carry that exact fingerprint. A free-form
question, matching source label, or empty record set is not sufficient.

### Governed profile context

The profile declares source identity and adapter applicability, authoritative
scope, population basis, retention, blind intervals, exclusions, freshness
caps, finality delay, effective/expiry times, issuer, and approval authority.
The registry snapshot binds exact profile records and digests under a named
issuer and closed-open validity interval. The trust selection pins the exact
snapshot digest, trusted issuer/authority sets, and the one application-selected
profile reference.

Resolution is staged:

1. Validate snapshot/trust contract identifiers and their self-digests.
2. Validate registry/snapshot identity, exact digest, selected reference,
   snapshot issuer, and snapshot time window.
3. If any snapshot trust check fails, stop before using contained profile
   semantics for applicability, freshness, or finality diagnostics.
4. Resolve the application-selected exact profile ID, immutable version, and
   digest.
5. Validate profile issuer, approval authority, effective/expiry interval, and
   inclusive revocation before applying its semantics.
6. Compare the request and runtime observation with the trusted profile.

The staged order is security-significant: untrusted content may be parseable,
but it cannot select the rule set used to evaluate the claim.

Profiles, snapshots, and trust selections contain declarative identities and
canonical integrity bindings. They are not signed in P0, and their truth and
custody must be established outside this process.

### Evaluation and gate result

The evaluator uses policy `1.0-candidate.4` and emits evaluator
`esio-evaluator-1.0-candidate.5`. It checks the supplied aggregate state,
matches, source accounting, profile applicability, coverage, freshness,
finality horizon, index chronology, and validity. It returns all applicable
stable reasons, a permit/reject disposition, bounded scope/qualification text,
profile assessment, and the composite evaluation-input digest.

The external gate remains intentionally smaller than the state vocabulary:

| Evidence result | Negative-claim disposition |
|---|---|
| `ABSENT_WITHIN_SCOPE` with no disqualifying reason | Permit only the generated scoped negative. |
| `PRESENT` | Reject the negative; positive evidence exists. |
| Any indeterminate, failed, or contradictory state | Reject an unqualified negative and retain the unresolved reasons. |

Explanatory language may be generated outside the trusted decision path, but
it may not broaden the structured disposition or strip qualifications.

### Evidence certificate

`EvidenceCertificate` is a self-contained, unsigned replay record. The builder
has no caller-supplied `GateDecision` parameter: it evaluates the request
itself and records the complete decision. The certificate binds:

- every active contract identifier and the SHA-256/canonicalization profiles;
- normalized request and policy digest;
- complete trusted profile context and its context binding;
- composite evaluation-input digest;
- evaluation, issuance, and effective-validity times;
- explicit evidence origin and asserted implementation identity;
- complete permit or rejection decision; and
- an outer digest over the canonical payload.

The Python dataclasses are frozen only at the top level; nested mappings are
not a deep immutability guarantee. The immutable verification record is the
canonical serialized JSON. Verification therefore serializes and strictly
reparses even a caller-supplied typed `EvidenceCertificate` before inspecting
it.

Structural parsing rejects duplicate/unknown fields, booleans in numeric
positions, out-of-range bounds, non-finite values, and decimal values that
cannot round-trip exactly through the supported binary64 canonical JSON model.
Replay compares canonical JSON bytes, so JSON numeric types remain significant
(`1` and `1.0` are not interchangeable decision records).

Verification reports separate dimensions rather than one `valid` flag:

- structural support;
- outer certificate-digest integrity;
- embedded digest/binding integrity;
- deterministic replay and historical reproducibility;
- optional exact expected-context match;
- optional expected-certificate-digest match;
- optional current-local-reliance eligibility; and
- issuer authentication and authorization, which remain `false` in P0.

Expected context and expected digest must come from outside the certificate.
Absence of either is unestablished (`null`), not success. Current local reliance
is evaluated only when an external expected context, a separately retained
expected certificate digest, and an explicit relying-party time are all
supplied. Any mismatch fails that dimension and current reliance.

The effective current-reliance boundary is the earliest applicable deadline:

- registry snapshot `next_update_at`;
- evidence envelope `valid_until`;
- policy observation- and index-freshness deadlines;
- resolved profile expiry and effective revocation; and
- resolved profile observation- and index-freshness deadlines.

The interval is closed-open and also requires
`issued_at <= relying_party_at`. A rejection certificate can reproduce
historically but can never become eligible for current reliance. P0 does not
consult a monotonic registry head or online revocation service after issuance;
the caller must supply the currently expected context.

## Data flow

1. The caller supplies a schema `1.0` request with the exact policy and profile
   reference. The application separately supplies the registry snapshot and
   trust selection.
2. The CLI parser rejects ambiguous, oversized, deeply nested, duplicate-key,
   nonstandard, or unsupported JSON before domain evaluation.
3. Models normalize time, identifiers, sets, counts, exact supported numbers,
   and immutable version strings.
4. Profile resolution validates the snapshot trust boundary first, then the
   exact selected profile and its trust/applicability boundaries.
5. Source accounting and coverage evaluation compare request-bound facts with
   the trusted profile and policy.
6. The gate evaluates the supplied state and emits a deterministic decision.
7. The certificate builder binds that decision and all replay inputs into one
   canonical payload and computes the unsigned outer digest.
8. The CLI writes the certificate to stdout and structured invalid-input
   diagnostics to stderr.
9. Verification strictly reparses the artifact, recomputes all bindings,
   reevaluates, and compares canonical decision bytes. Optional external
   context, digest, and relying-party time add separate custody/current-use
   assessments.

## Determinism and time

- Domain functions receive evaluation, issuance, and relying-party times; they
  do not read the ambient clock.
- RFC 3339 timestamps require explicit offsets and normalize to canonical UTC.
- Policy/profile/finality boundaries use exact integer/microsecond arithmetic.
- Profile/snapshot/revocation/current-use intervals are tested at the adjacent
  microsecond and use the documented inclusive or closed-open semantics.
- Semantically unordered collections are sorted before hashing.
- Supported JSON numbers must preserve their exact canonical meaning; lossy
  Decimal-to-binary64 normalization is rejected.
- Decision replay is canonical-byte exact, and reason ordering is deterministic.

## CLI boundary

The installed command is `evidence-state`:

- `evidence-state evaluate --input <path-or-> --registry <path> --trust
  <path> --issued-at <RFC3339> --origin <class>` evaluates and writes a
  certificate. Implementation revision/tree-state inputs are explicit; no
  ambient Git lookup occurs.
- `evidence-state verify-certificate --input <path-or->` performs structural,
  integrity, and replay checks. `--registry` and `--trust` must be supplied as a
  pair for expected-context comparison; `--expected-digest` and
  `--relying-party-at` enable their independent dimensions.
- `evidence-state emptybench --input <path> --registry <path> --trust <path>`
  runs caller-supplied benchmark cases under application-controlled context.
- `evidence-state demo`, `evidence-state coverage`, and `evidence-state --help`
  retain their bounded local roles.

`-` denotes stdin where supported. Structured output goes to stdout;
diagnostics go to stderr. A valid rejection certificate is a successful
evaluation operation, so its decision is communicated in JSON rather than by a
process failure. Invalid input returns exit `2`; certificate verification
dimension failure returns exit `1`.

## Persistence and laptop deployment

P0 requires no database. Commands operate on explicit local JSON inputs and
outputs. A laptop or VM can run the complete core path offline. Optional
Postgres/Toxiproxy containers are a disposable synthetic adapter/fault lab, not
a P0 dependency or production environment.

If persistence is later added, certificates must be append-only. A correction
creates a successor linked to the prior artifact; it does not mutate an issued
record. A retained expected digest enables comparison only. Independent custody
requires organizationally independent control and is not supplied by a local
file or by an author-retained digest alone.

## Security boundaries and failure behavior

- Producer request and certificate JSON are untrusted.
- Registry and trust inputs are privileged application configuration, but P0
  self-digests do not authenticate their declarative issuers.
- Source observations can be incomplete, stale, forged, or produced under
  insufficient access.
- Any unsupported schema, policy, evaluator, profile, registry, trust,
  evaluation-input, certificate, canonicalization, or digest identifier rejects
  without fallback.
- Snapshot trust failure stops profile-semantic use. Exact profile mismatch,
  untrusted issuer/authority, expiry, revocation, applicability failure,
  freshness failure, finality failure, source mismatch, or coverage failure
  blocks the negative claim.
- Certificate integrity or replay failure is reported independently; it cannot
  establish authentication or authorization.
- A single laptop process does not provide independent observation, protected
  custody, multi-party authorization, non-repudiation, external validation, or
  production readiness.

The full threat model is in [../SECURITY.md](../SECURITY.md).

## Evolution rules

- Schema `1.0` and candidate contracts remain unfrozen unless a separate,
  owner-approved, versioned freeze decision is recorded. Local acceptance and
  custody evidence alone do not freeze them.
- New required fields, changed state meanings, comparison boundaries, numeric
  semantics, trust ordering, or canonicalization require governed version
  evolution.
- New evidence states require an ADR, gate mapping, matched benchmark cases,
  and compatibility tests.
- New adapters begin read-only and synthetic; real-data use crosses an explicit
  owner and data-boundary approval.
- A future service may wrap the application layer but must not move policy into
  handlers or make network availability a core dependency.

## Related decisions

- [ADR-0001](adr/0001-laptop-first-modular-monolith.md)
- [ADR-0002](adr/0002-versioned-json-and-pure-evaluator.md)
- [ADR-0003](adr/0003-fail-closed-scoped-negative-gate.md)
- [ADR-0004](adr/0004-separate-coverage-declarations-from-observations.md)
- [ADR-0005](adr/0005-canonical-certificates-and-digest-boundary.md)
- [ADR-0006](adr/0006-disposable-opt-in-fault-lab.md)
- [ADR-0007](adr/0007-schema-1-source-accounting-and-version-boundaries.md)
- [ADR-0008](adr/0008-explicit-source-finality-horizon.md)
- [ADR-0009](adr/0009-governed-profile-resolution-and-trust-selection.md)
- [ADR-0010](adr/0010-certificates-are-replay-records-not-authorization-tokens.md)
- [ADR-0011](adr/0011-adversarial-trust-and-replay-hardening.md)
- [ADR-0012](adr/0012-version-state-transitions-and-validation-errors.md)
- [ADR-0013](adr/0013-python-trust-boundary-and-reliance-custody.md)
