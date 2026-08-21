# ADR-0007: Introduce Schema 1.0 Source Accounting and Keep Version Boundaries Explicit

**Status:** Accepted for implementation; schema `1.0` remains a candidate contract
**Date:** 2026-08-21
**Deciders:** Project owner; architecture maintainer

## Context

The frozen schema `0.1` envelope carried one `source` descriptor but did not
state which sources the query required or distinguish that declared scope from
the sources actually observed at runtime. A complete-looking empty result could
therefore be evaluated without proving that every required source participated.
Closing that gap changes the accepted meaning and shape of the input contract:
the query now declares source requirements, while the envelope reports separate
source observations and their status.

Schema `0.1` was first frozen in commit
`b6fac8706fc3496ceb46003c0d5b836a3dc23096` (`b6fac87`). It must remain a
reproducible historical baseline rather than be revised in place. The active
implementation is package version `0.2.0`, but a package version is not an
interchange-schema version, policy version, evaluator version, canonicalization
profile, or assurance claim.

The source-accounting change is intentionally incomplete in one important
respect: the project does not yet have defensible composition semantics for a
negative claim that depends on more than one required source. It also does not
yet have the explicit finality model and fully version-bound certificate needed
to freeze the new contract.

## Decision

Adopt schema `1.0` as the only schema accepted by the active parser and
evaluator. Treat it as a candidate until the freeze criteria in this ADR are
satisfied.

Schema `1.0` makes source accounting explicit:

- `query.source_requirements` declares the visible source scope, including each
  source identifier, system, locator, adapter identity/version, non-secret
  authorization-context identifier, accessible population, and nonempty
  detection assumptions.
- `envelope.source_observations` records runtime facts separately, including
  the source identifier, observation status, descriptor, accessible population,
  authorization context, canonical query fingerprint, and errors. Aggregate
  coverage carries the same query fingerprint.
- Missing, inaccessible, pending, stale, failed, contradictory, unknown,
  identity-mismatched, adapter-mismatched, authorization-mismatched,
  population-mismatched, or error-bearing required sources fail closed.
- An `OBSERVED` status means only that a source observation exists. It does not
  prove query coverage, index finality, detection effectiveness, or real-world
  absence.
- Exactly one declared source is supported in the candidate, and its role must
  be `REQUIRED`. Inputs declaring more than one source or an optional source are
  rejected before evaluation. This avoids pretending that one aggregate
  coverage object can be composed across several sources before population,
  overlap, temporal, and finality semantics exist.

The active implementation rejects schema `0.1` and every other unknown schema
version. It does not auto-migrate `0.1`: converting a singular descriptor into
a source requirement and a runtime observation would require claims about
population, source role, status, and detection assumptions that are not present
in the old record.

Historical schema `0.1` replay is preserved through the frozen
`examples/legacy/schema-0.1-covered-request.json` fixture and a checkout of
commit `b6fac87`. That path reproduces the historical implementation; it must
not be used to issue or imply a current schema `1.0` decision or certificate.

## Version Responsibility Boundaries

Each identifier answers a different question and must remain independently
visible and certificate-bound:

| Identifier | Responsibility | Must not be used to represent |
|---|---|---|
| Schema version | JSON structure, required fields, domain values, and the meaning of source requirements and observations | Policy thresholds, evaluator implementation, package release, or byte encoding |
| Policy ID and version | Decision thresholds, safety floors, and permitted decision behavior for an otherwise valid schema object | Schema compatibility, source truth, evaluator identity, or canonicalization |
| Evaluator version | The deterministic algorithm and reason-producing implementation applied to a schema object under a policy | A hidden schema or policy change, or evidence that source assertions are true |
| Coverage-profile ID, version, and digest | Governed assertions about a source's population, retention, access, finality, blind intervals, and detection assumptions | Runtime observation status, policy thresholds, or independent validation of the profile's truth |
| Certificate format/version | The immutable replay container binding exact inputs, versions, decision, evaluation time, reasons, and integrity metadata | Improved evidence sufficiency, issuer authentication, independent custody, or proof of real-world absence |
| Canonicalization profile | Deterministic conversion of supported data to bytes for hashing and replay | Domain semantics, policy behavior, source validity, or a digital signature |
| Package version | Distribution and implementation release coordination | Interchange compatibility, downgrade negotiation, certificate trust, or schema stability |

The candidate continues to use canonicalization profile
`esio-canonical-json-0.1` and SHA-256 integrity digests. Retaining that profile
does not retain schema `0.1`: the same byte-encoding rules can canonicalize a
different domain contract. A canonicalization change requires a new profile and
new test vectors; it must not be hidden in a schema, evaluator, or package bump.

Coverage profiles remain governed assertions rather than self-proving facts.
When the profile registry is implemented, missing, expired, mismatched, or
unknown required profiles must block a negative claim. The certificate must pin
their exact identifiers, versions, and digests. A certificate records the
decision boundary; it does not make an insufficient input sufficient, and its
digest is not a signature.

## Downgrade and Compatibility Rules

1. The active parser accepts exactly schema `1.0`; it rejects `0.1`, future
   versions, numeric substitutes, and unknown values before evaluation.
2. There is no implicit compatibility mode, field defaulting, version fallback,
   or best-effort interpretation for evidence-bearing fields.
3. The evaluator accepts only its explicitly supported policy ID and version.
   An older, newer, missing, or unknown policy cannot be selected as a fallback,
   and a policy revision cannot relax the P0 safety floor silently.
4. A verifier must use the certificate's exact schema, policy, evaluator,
   coverage-profile, certificate-format, digest-algorithm, and canonicalization
   identifiers. It must not re-canonicalize under another profile or choose an
   older evaluator merely to reproduce an allowed result.
5. Package version `0.2.0` is never used to negotiate any of these contracts.
6. Any future migration utility must be explicit and separate from parsing. It
   must record the original artifact and digest, the migration tool/version,
   every supplied assumption, and a new artifact and digest. A migrated record
   is a derived artifact, not proof that schema `0.1` contained schema `1.0`
   semantics.
7. Historical replay runs the historical fixture against the hash-bound
   historical code. Its verdict is labeled historical and cannot be promoted to
   a current decision without a new schema `1.0` observation and evaluation.

## Options Considered

### Option A: Major schema change with strict active rejection

| Dimension | Assessment |
|---|---|
| Semantic honesty | High |
| Downgrade resistance | High |
| Implementation complexity | Medium |
| Backward convenience | Low |

**Pros:** Makes required-versus-observed source accounting machine-checkable,
preserves the frozen baseline, and prevents invented migration semantics.
**Cons:** Existing `0.1` inputs require historical replay or deliberate
re-authoring under the new contract.

### Option B: Revise schema `0.1` in place

| Dimension | Assessment |
|---|---|
| Semantic honesty | Low |
| Reproducibility | Low |
| Implementation complexity | Low |
| Compatibility appearance | High but misleading |

**Rejected:** The same version would describe incompatible structures and
meanings, invalidating the accepted freeze and its replay evidence.

### Option C: Publish the breaking contract as schema `0.2`

| Dimension | Assessment |
|---|---|
| Change signaling | Weak |
| Reproducibility | Medium |
| Convention alignment | Low |
| Implementation complexity | Low |

**Rejected:** Project versioning rules require a major schema change for an
incompatible semantic contract. A minor number would understate the boundary.

### Option D: Accept both schemas and silently translate `0.1`

| Dimension | Assessment |
|---|---|
| User convenience | High |
| Semantic integrity | Low |
| Attack surface | High |
| Auditability | Low |

**Rejected:** The old descriptor cannot determine required source role,
accessible population equivalence, observation status, or detection
assumptions. Silent translation could turn missing evidence into asserted
coverage.

### Option E: Infer multi-source composition in schema `1.0`

| Dimension | Assessment |
|---|---|
| Feature breadth | High |
| Correctness confidence | Low |
| Research burden | High |
| Fail-closed behavior | Low |

**Rejected for the candidate:** Individually complete sources do not establish
joint population coverage, deduplication, temporal alignment, or finality. The
candidate exposes the unsupported case rather than inventing a union rule.

## Trade-off Analysis

The decision favors semantic traceability over transparent backward
compatibility. It deliberately incurs a breaking schema boundary now, while
the project is pre-alpha, rather than allowing ambiguous source semantics into
future certificates and benchmark fixtures. Keeping canonicalization,
evaluation, policy, profiles, certificates, and package releases independently
versioned adds bookkeeping, but it prevents any one version number from hiding
a change in another trust boundary.

Rejecting multiple declared sources limits early adapter breadth. That
constraint is preferable to issuing a negative claim from an undefined
composition rule. Multi-source support can be added only after the project
defines and tests population algebra, overlap and deduplication, temporal
alignment, cross-source error propagation, and joint finality.

## Consequences

- Schema `0.1` remains immutable and reproducible at `b6fac87`.
- Active examples, tests, CLI inputs, and candidate benchmark cases use schema
  `1.0` and explicit policy identity.
- Old inputs fail visibly instead of being accepted with weaker semantics.
- Input and decision digests change when source requirements, source
  observations, status, population, policy, or other evidence-bearing fields
  change.
- Adapter authors must declare required source scope separately from reporting
  runtime observations, bind both observations and coverage to the canonical
  query fingerprint, and report the expected adapter and authorization context.
- The candidate can establish deterministic source-accounting behavior, but it
  cannot yet claim a frozen schema, complete finality semantics, certificate
  completeness, multi-source support, external validation, or production
  readiness.
- A future compatible extension may retain schema `1.x` only if it preserves
  accepted syntax and semantics. Any incompatible required field, state meaning,
  boundary comparison, reason contract, or source-composition rule requires the
  next applicable major schema or independently versioned contract.

## Criteria Before Freezing Schema 1.0

Schema `1.0` may move from candidate to a hash-bound accepted freeze only when
all of the following are true:

1. Source-requirement and source-observation validation, status mapping,
   population matching, duplicate/undeclared-source rejection, ordering
   invariance, mutation sensitivity, and fail-closed multi-source behavior have
   direct tests.
2. Explicit finality semantics are implemented and tested. `index_as_of`, an
   empty response, transport completion, or `OBSERVED` status is not treated as
   an implicit completeness watermark.
3. A complete canonical certificate binds the schema, exact policy ID/version,
   evaluator version, applicable coverage-profile identifiers/versions/digests,
   canonicalization profile, digest algorithm, canonical input digest,
   evaluation time, evidence origin, verdict, reasons, and qualified statement.
4. Published canonical bytes and digest vectors reproduce across every
   supported Python version; one-field mutations and version substitutions fail
   verification.
5. The active suite proves rejection of schema `0.1` while the legacy fixture
   reproduces against `b6fac87` without modifying either historical artifact.
6. EmptyBench contains frozen source-accounting and finality matched pairs whose
   expected outcomes come from an independent oracle, including missing,
   mismatched, failed, and unsupported multi-source cases.
7. Schema, policy, evaluator, profile, certificate, and canonicalization
   downgrade tests fail closed, and no unresolved P0 correctness defect remains.
8. Architecture, traceability, claims, operating guidance, examples, and
   adapter contracts agree with the implemented candidate, and an independent
   review records the exact freeze commit and test evidence.

Until these criteria are met, `1.0` is an active development candidate and must
not be described as externally validated, certificate-complete, released, or
production-ready.

## Action Items

1. [x] Replace the singular source descriptor with separate query requirements
   and envelope observations in the schema `1.0` candidate.
2. [x] Give the active policy and evaluator explicit supported identifiers.
3. [x] Reject more than one declared source until composition exists.
4. [x] Preserve and test the schema `0.1` fixture/commit replay boundary.
5. [x] Implement explicit finality under ADR-0008.
6. [ ] Complete certificate/version and governed profile binding.
7. [ ] Freeze independent EmptyBench oracle outputs and cross-version canonical
   vectors before accepting schema `1.0`.

## 2026-08-21 Candidate Addendum

ADR-0008 adds a nullable source-requirement horizon to the schema `1.0`
candidate and makes it non-relaxable under policy `1.0-candidate.2`. A permit
now requires the reported source index to reach that query-bound horizon. This
closes the evaluator's wait-only finality defect but does not satisfy the
profile, certificate, independent-oracle, external-review, or schema-freeze
criteria above.
