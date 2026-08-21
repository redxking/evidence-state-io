# ADR-0009: Resolve Coverage and Finality Profiles from a Separately Controlled Trust Context

**Status:** Accepted for candidate implementation; not a schema freeze or trust claim  
**Date:** 2026-08-21  
**Deciders:** Project owner; architecture maintainer

> **Revision note:** ADR-0011 supersedes the candidate.1/candidate.3
> selection and verification details in this record. Commit `f7d8bca` is a
> rejected pre-acceptance checkpoint, not accepted evidence for this ADR. The
> current local candidate uses an application-selected exact profile reference
> and staged trust processing under the candidate.2/candidate.4 contracts.

## Context

ADR-0008 closed the wait-only finality defect by requiring a query-bound
`finality_horizon` and a source-reported index watermark that reaches it. That
increment still permits the request author to select the horizon. A caller can
therefore choose `finality_horizon == query.time_end`, obtain a new snapshot at
that time, rebind the query fingerprints, and satisfy the candidate.2 gate even
when the source's real late-arrival or reopen behavior would require a longer
wait.

Putting a profile body, a claimed digest, or a registry snapshot inside the same
producer request does not solve the problem. The producer could choose all of
them together. A governed profile has meaning only when the application that is
relying on the decision selects the registry and trust context separately from
the observation producer.

The P0 environment is intentionally laptop- and VM-capable. It has no required
network service, database, public-key infrastructure, source-owner
attestation, trusted timestamp, or ambient clock read. The architecture must
therefore distinguish deterministic configuration custody from proof that the
configuration is true.

The PRD previously placed the full profile-registry lifecycle in P1 while the
schema-freeze criteria and P0 backlog require an exact profile binding. This
ADR separates those scopes:

- P0 implements an immutable local profile, a materialized registry snapshot,
  a separately pinned trust selection, deterministic resolution, and
  fail-closed enforcement.
- P1 retains operational storage, authenticated issuers and source owners,
  delegation, monotonic registry heads, revocation distribution, drift
  monitoring, and empirical validation of the profile assertions.

## Decision

### 1. Query-bound reference, not an inline profile

Add an optional and nullable `profile_ref` to `SourceRequirement`:

```json
{
  "registry_id": "org.example.coverage-registry",
  "profile_id": "source.example.search",
  "profile_version": "1.0.0",
  "profile_digest": "sha256:<64-lowercase-hex>"
}
```

The reference is exact. `latest`, version ranges, aliases, fallback, and
best-effort selection are not supported. A declared reference participates in
the canonical query fingerprint and is therefore bound by aggregate coverage
and every source observation.

To preserve the accepted schema `1.0` candidate syntax, omitted and null
references parse and canonicalize by omission. Policy
`esio-p0-safety-floor/1.0-candidate.3` makes the reference non-relaxable and
rejects it with `PROFILE_REFERENCE_UNDECLARED`. Candidate.2 remains
reproducible only at its hash-bound implementation.

### 2. Immutable coverage/finality profile

The first profile contract is
`esio-coverage-finality-profile/1.0-candidate.1`. Its normalized unsigned
payload includes:

- profile ID and exact version;
- source-owner, approval-authority, and publisher/issuer IDs;
- issue, effective, and expiry times;
- exact source ID, system, locator, adapter ID/version, authorization-context
  ID, and accessible-population declaration;
- exact query target, predicate, authorization boundary, required exclusions,
  and detection assumptions;
- an exact population denominator, optional exact page and partition counts,
  an exact permission-limited flag, retention, blind intervals, and maximum
  observation/index ages; and
- the fixed finality method `QUERY_END_PLUS_MAX_DELAY`, a late-arrival bound,
  and a reopen bound.

The P0 profile permits only `population_basis == EXACT`. Estimated, unknown,
dynamic, or externally resolved denominators require a separately versioned
resolver contract. A source-supplied `declared_lower_bound` cannot substitute
for a governed denominator.

The profile digest is SHA-256 over the complete normalized profile payload.
The mandatory profile-schema discriminator supplies domain separation. The
digest is carried outside the payload and is recomputed; it is never accepted
as proof merely because the profile repeats it.

Profile identities are declarative under P0 configuration custody. They do not
authenticate a source owner, approver, or issuer.

### 3. Separately supplied registry and trust selection

The evaluator receives a `TrustedProfileContext` as a separate argument from
`NegativeClaimRequest`. It contains:

1. an `esio-profile-registry-snapshot/1.0-candidate.1` materialized snapshot;
2. an `esio-profile-trust-selection/1.0-candidate.1` relying-party selection.

The snapshot binds registry ID, snapshot ID/version, issuer, `as_of`, next
update time, normalized profile records, their validated digests, and
ACTIVE/REVOKED state. Its own digest covers the complete normalized snapshot
payload and excludes only the outer snapshot digest.

The trust selection pins the exact registry ID, snapshot ID/version/digest and
allowlists registry issuers, profile issuers, and approval authorities. Its
digest covers the complete normalized trust payload and excludes only its own
outer digest.

The producer request cannot embed or override either object. The library API
keeps them separate; the CLI requires separate operator-controlled files. A
local deployment may place those files under read-only configuration custody.
The pure evaluator performs no filesystem, network, or wall-clock lookup.

For every required source, resolution by
`(registry_id, profile_id, profile_version, profile_digest)` must yield exactly
one active record. Zero or multiple records reject. A snapshot mapping the same
profile ID/version to different digests is structurally invalid. There is no
automatic upgrade, downgrade, nearest-version, or latest-version behavior.

### 4. Exact applicability and coverage rules

After trusted resolution succeeds, the evaluator requires exact equality for:

- source ID, system, locator, adapter ID/version;
- authorization-context ID and accessible-population declaration;
- query target, predicate, and authorization boundary;
- detection assumptions;
- exact population basis and denominator;
- page and partition counts when the profile declares them; and
- permission-limited behavior.

The query exclusions must contain every profile-required exclusion. Additional
query exclusions are conservative and do not by themselves invalidate the
profile. All collection-valued fields normalize into deterministic lexical
order.

Retention is evaluated against the independently reported index watermark:

```text
query.time_start >= index_as_of - retention_seconds
```

Blind intervals use closed-open `[start, end)` semantics. The existing query
interval includes both endpoints; a blind interval intersects the query when
`blind.start <= query.time_end` and `query.time_start < blind.end`.

Profile maximum observation and index ages are additional safety ceilings.
They cannot be weakened by omitting the analogous inline policy thresholds.

### 5. Derived finality

The only candidate.1 finality rule is:

```text
required_delay = max(late_arrival_bound_seconds, reopen_bound_seconds)
derived_horizon = query.time_end + required_delay
source_requirement.finality_horizon == derived_horizon
derived_horizon <= source_observation.index_as_of
```

Every delay bound is measured from `query.time_end`, which makes `max` the
defined composition rule. Both an earlier caller-favorable horizon and a later
caller-selected horizon reject with `FINALITY_HORIZON_PROFILE_MISMATCH`.
Additional conservatism must be represented by a versioned profile or policy,
not an arbitrary request field.

The existing query/finality chronology remains inclusive. A profile is never
used to derive a horizon until exact trusted resolution and digest validation
succeed.

### 6. Time, revocation, and replay semantics

Governance intervals are half-open:

```text
profile usable: profile.effective_at <= evaluated_at < profile.expires_at
snapshot usable: snapshot.as_of <= evaluated_at < snapshot.next_update_at
```

Structural invariants require
`issued_at <= effective_at < expires_at` and
`as_of < next_update_at`.

An ACTIVE registry record has null revocation fields. A REVOKED record carries
an effective time, record time, and reason; the effective time may be
retroactive but must not follow its record time or snapshot `as_of`. An
evaluation at or after the revocation-effective time rejects. Historical
reproduction before that time is not current authorization.

The request's `evaluated_at` remains an explicit deterministic input, not a
trusted timestamp. Later certificate verification must distinguish:

- structural and digest integrity;
- deterministic historical replay under the embedded evaluation time; and
- current usability under a separately supplied relying-party time and trusted
  registry head.

No unsigned P0 certificate is an authorization token. If certificates later
control one-time or live actions, audience, action, nonce, trusted time, replay
storage, and authenticated issuers require a separate ADR.

### 7. Stable failure contract

Candidate.3 adds deterministic reasons in this group order:

1. trust and registry identity, digest, issuer, and time failures;
2. profile reference, resolution, digest, issuer, authority, validity, and
   revocation failures;
3. source, adapter, authorization, population, query, assumptions, coverage,
   retention, blind-interval, freshness, and derived-finality failures;
4. the existing state, coverage, source-accounting, request-time, validity,
   index, and finality failures.

Malformed JSON, duplicate keys, invalid timestamps/digests, duplicate profile
records, contradictory revocation fields, arithmetic overflow, and unknown
contract identifiers are model-validation errors. Semantically valid but
untrusted, unavailable, expired, revoked, mismatched, stale, or insufficient
inputs are gate rejections.

The minimum reason vocabulary is:

- `PROFILE_REFERENCE_UNDECLARED`
- `REGISTRY_SNAPSHOT_UNDECLARED`
- `REGISTRY_SNAPSHOT_IDENTITY_MISMATCH`
- `REGISTRY_SNAPSHOT_DIGEST_MISMATCH`
- `REGISTRY_SNAPSHOT_ISSUER_UNTRUSTED`
- `REGISTRY_SNAPSHOT_NOT_YET_EFFECTIVE`
- `REGISTRY_SNAPSHOT_EXPIRED`
- `PROFILE_NOT_FOUND`
- `PROFILE_RESOLUTION_AMBIGUOUS`
- `PROFILE_DIGEST_MISMATCH`
- `PROFILE_ISSUER_UNTRUSTED`
- `PROFILE_AUTHORITY_UNTRUSTED`
- `PROFILE_NOT_YET_EFFECTIVE`
- `PROFILE_EXPIRED`
- `PROFILE_REVOKED`
- `PROFILE_SOURCE_MISMATCH`
- `PROFILE_ADAPTER_MISMATCH`
- `PROFILE_AUTHORIZATION_MISMATCH`
- `PROFILE_POPULATION_MISMATCH`
- `PROFILE_QUERY_APPLICABILITY_MISMATCH`
- `PROFILE_DETECTION_ASSUMPTIONS_MISMATCH`
- `PROFILE_COVERAGE_BASIS_MISMATCH`
- `PROFILE_RETENTION_EXCEEDED`
- `PROFILE_BLIND_INTERVAL_INTERSECTS_QUERY`
- `PROFILE_OBSERVATION_TOO_OLD`
- `PROFILE_INDEX_TOO_OLD`
- `FINALITY_HORIZON_PROFILE_MISMATCH`

Unknown, missing, ambiguous, or untrusted profile resolution must not feed a
derived-horizon comparison.

### 8. Composite evaluation digest and version boundaries

The decision input digest changes from request-only hashing to a
domain-separated composite over:

- the normalized request;
- the exact normalized registry snapshot; and
- the exact normalized trust selection.

Changing any profile, registry, revocation, trust, query, policy, observation,
or evaluation-time field changes the composite digest. The decision continues
to expose the canonicalization and digest identifiers explicitly.

This increment uses:

| Contract | Identifier |
|---|---|
| Package | `0.4.0` |
| Wire schema | `1.0` candidate |
| Policy | `esio-p0-safety-floor/1.0-candidate.3` |
| Evaluator | `esio-evaluator-1.0-candidate.3` |
| Profile | `esio-coverage-finality-profile/1.0-candidate.1` |
| Registry snapshot | `esio-profile-registry-snapshot/1.0-candidate.1` |
| Trust selection | `esio-profile-trust-selection/1.0-candidate.1` |
| Evaluation input | `esio-evaluation-input/1.0-candidate.1` |
| Canonicalization | `esio-canonical-json-0.1` |
| Digest | SHA-256 |

Package version never negotiates another contract. Unknown, older, or newer
active versions reject without fallback.

## Options Considered

### Inline profile plus self-declared digest

**Rejected.** The request author controls both values and can select favorable
late-arrival, reopen, population, or freshness claims.

### Registry snapshot inside the producer request

**Rejected.** A registry is not a trust boundary when the observation producer
selects the registry and the expected digest in the same object.

### Dynamic network registry lookup

**Deferred.** It expands availability, rollback, authentication, cache, and
time dependencies without being necessary to prove the deterministic P0
contract on a laptop or VM.

### Accept unknown populations with a declared lower bound

**Rejected for the governed P0 path.** A source assertion of 100 percent cannot
replace a governed exact denominator. Dynamic population resolution remains a
future independently versioned contract.

### Accept any horizon at or after the derived horizon

**Rejected.** It creates two authorities for the safety boundary and weakens
replay comparability. A deliberately longer horizon belongs in the profile or
policy that owns the rule.

### Make `profile_ref` structurally required under schema `1.0`

**Rejected.** It would silently make accepted schema `1.0` candidate syntax
incompatible. Nullable syntax plus non-relaxable candidate.3 semantics keeps
diagnostic parsing honest.

## Consequences

- A caller can no longer permit a negative claim by selecting a favorable
  finality horizon and rebinding its own fingerprints.
- The seed benchmark's prior unknown-population/declared-lower-bound permit is
  removed. Governed P0 permits only an exact profile-bound denominator.
- Applications must supply registry and trust configuration separately from
  producer evidence. This is operationally feasible with local read-only files
  on a laptop or VM.
- Profile, snapshot, trust, and composite-evaluation canonical vectors become
  required test and release artifacts.
- The complete evidence certificate must bind the exact profile reference,
  snapshot ID/version/digest, trust-selection digest, schema, policy,
  evaluator, canonicalization, digest algorithm, normalized request, complete
  decision, evaluation time, origin, and limitations.
- P0 still does not authenticate profile identities, prove source behavior,
  establish source truth, validate source clocks, prevent exceptional late
  data, compose multiple sources, or provide external custody.
- Schema `1.0` remains a candidate after this increment. Certificate
  completion, an independent frozen EmptyBench oracle/campaign, downgrade
  vectors, cross-runtime vectors, and the exact freeze audit remain open.

## Acceptance Evidence

The increment is accepted only when:

1. missing/null and exact declared references follow the transition rule;
2. inline or request-selected governance cannot authorize evaluation;
3. snapshot/trust/profile identity, digest, issuer, authority, validity,
   revocation, unknown, ambiguity, and downgrade cases fail closed;
4. source, adapter, authorization, population, query, exclusions, assumptions,
   coverage, retention, blind intervals, and freshness have direct boundary and
   mutation tests;
5. derived-horizon minus one microsecond, equality, and plus one microsecond
   behave exactly as specified;
6. profile and snapshot time boundaries are tested at minus one microsecond,
   equality, and plus one microsecond;
7. the composite input digest changes for every governed input class and is
   invariant to object order and equivalent UTC offsets;
8. strict parsing, duplicate-key, arithmetic-overflow, and unsupported-version
   behavior remain fail closed;
9. source and installed suites pass on the primary runtime, supported-runtime
   tests pass, and benchmark output is byte-identical; and
10. an independent adversarial review confirms that profile content is not
    consulted before trusted exact resolution.

Passing these checks establishes deterministic local governance binding. It
does not establish profile truth, external validation, production readiness,
or a schema freeze.
