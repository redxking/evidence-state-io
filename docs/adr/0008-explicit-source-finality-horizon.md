# ADR-0008: Require an Explicit Source Finality Horizon for Negative Claims

**Status:** Accepted for candidate implementation; not a schema freeze
**Date:** 2026-08-21
**Deciders:** Project owner; architecture maintainer

## Context

The schema `1.0` source-accounting candidate distinguishes the source a query
requires from the source observation returned at runtime. It also requires an
`index_as_of` timestamp and rejects an index that precedes `query.time_end`.
Those controls establish source identity and snapshot chronology, but they do
not establish finality. A source may accept an event before the query interval
ends and index it later. An empty snapshot taken at the interval end can
therefore be current in a clock sense while still being open to in-scope late
arrivals.

A particularly unsafe implementation would compare only the caller-supplied
`evaluated_at` time with a delay threshold. That would allow an unchanged,
pre-finality empty snapshot to become sufficient merely because the caller
waited. The evidence-bearing source snapshot, not just the evaluator's clock,
must have advanced through the closure threshold.

The project does not yet have a governed coverage-profile registry capable of
validating a source's late-arrival distribution, correction behavior, or clock
domain. This decision therefore adds deterministic enforcement of a declared
horizon without claiming that the declaration is independently true.

## Decision

Add `finality_horizon` to each `SourceRequirement`.

`finality_horizon` is the earliest declared source-system time at which a newly
acquired snapshot of the configured source may, under the declared late-arrival
assumption, be treated as having incorporated all in-scope observations whose
event time is at or before `query.time_end`.

The field belongs to the requirement, not the runtime observation:

- A source owner defines late-arrival and correction behavior.
- Trusted configuration will eventually resolve that behavior from a governed,
  versioned source profile into an absolute horizon for the exact query.
- The caller supplies the resolved horizon as part of the query requirement.
- The adapter independently reports the snapshot watermark as `index_as_of`.
- The envelope reports `observed_at` and `valid_until`.
- The decision request supplies `evaluated_at`.
- The evaluator compares supplied values and never reads ambient time.

For a permitted scoped negative, the following inclusive chronology must hold:

```text
query.time_end
    <= source_requirement.finality_horizon
    <= source_observation.descriptor.index_as_of
    <= envelope.observed_at
    <= request.evaluated_at
    <= envelope.valid_until
```

The existing observation-age, index-age, coverage, source status, error, and
validity rules remain additional requirements. Equality is accepted at every
edge. The timestamp grammar retains microsecond precision, so boundary tests
use one microsecond below, equal to, and one microsecond above a threshold.

### Schema and policy compatibility

Schema `1.0` remains an unfrozen candidate. To preserve its already accepted
syntax while adding a fail-closed semantic control, `finality_horizon` is
syntactically optional and nullable in `SourceRequirement`. A declared horizon
serializes as normalized UTC; omitted and null horizons both canonicalize by
omitting the field. This preserves the legacy schema `1.0` query fingerprint
for an undeclared horizon and lets historical candidate objects be parsed and
diagnosed rather than silently reinterpreted.

Policy `esio-p0-safety-floor/1.0-candidate.2` makes a declared horizon a
non-relaxable safety requirement. No supported policy can permit a request with
an omitted or null horizon. The evaluator becomes
`esio-evaluator-1.0-candidate.2`, and the package becomes `0.3.0`. The previous
policy candidate is rejected explicitly. The wire schema remains `1.0`
candidate and canonicalization remains `esio-canonical-json-0.1` because the
encoding algorithm does not change.

This compatibility choice does not weaken the authorization path: parsing an
envelope is not permission to issue a negative claim. A supported gate decision
requires candidate.2 policy semantics and fails closed on a missing horizon.

### Validation and stable reasons

- A non-null horizon must be an offset-aware timestamp accepted by the strict
  RFC 3339 parser.
- `finality_horizon < query.time_end` is structurally invalid because it is an
  internally contradictory requirement.
- An omitted or null horizon is structurally parseable but produces
  `FINALITY_HORIZON_UNDECLARED` under the safety-floor policy.
- A reported index earlier than the horizon produces
  `INDEX_PRECEDES_FINALITY_HORIZON`.
- A reported index earlier than both the query end and horizon produces both
  `INDEX_PRECEDES_QUERY_END` and `INDEX_PRECEDES_FINALITY_HORIZON` in the stable
  evaluator reason order.
- A missing index continues to produce `INDEX_TIMESTAMP_UNDECLARED`.
- Producer state and source status do not override these comparisons. A
  favorable `ABSENT_WITHIN_SCOPE`/`OBSERVED` record still rejects when its
  index is pre-horizon; a producer-labeled `PENDING_WINDOW` still rejects even
  after the chronology closes.

No separate `EVALUATION_PRECEDES_FINALITY_HORIZON` reason is introduced. Under
the enforced `index_as_of <= observed_at <= evaluated_at` chronology, a valid
snapshot cannot reach the horizon while evaluation remains before it. The
decisive evidence question is whether the source snapshot itself reached the
declared horizon.

### Query binding and reproducibility

Because the field is inside `SourceRequirement`, it is included in the
normalized query when declared, query fingerprint, coverage binding, source-observation
binding, canonical request, and request digest. Changing only the horizon must
change the query fingerprint and decision input digest. Coverage or observations
retaining a fingerprint for the old horizon are invalid.

The frozen schema `0.1` fixture and commit `b6fac87` are unchanged. Active
schema `1.0` fingerprints, examples, benchmark cases, and cross-runtime vectors
are regenerated for package `0.3.0`.

## Failure Modes and Security Properties

| Failure or attack | Candidate behavior | Residual risk |
|---|---|---|
| Caller waits past the horizon but reuses an old empty snapshot | Reject while `index_as_of < finality_horizon` | A producer can still lie about its index watermark |
| Runtime producer chooses a favorable horizon | Horizon is query-owned and fingerprint-bound, separate from observation | The caller/configuration authority is not authenticated in P0 |
| Horizon is missing | Reject with an explicit reason | Old objects remain parseable for diagnosis |
| Index is missing | Reject with the existing index reason | No proof that a supplied index is truthful |
| Source reopens, backfills, corrects, deletes, or retracts after closure | Decision remains bounded by its validity window and limitations | No governed reopen/correction model exists yet |
| Horizon is later than `valid_until` | No time can satisfy both finality and validity; gate remains closed | Configuration error is not automatically repaired |
| Clock domains disagree | Strict UTC normalization makes comparison deterministic | P0 does not authenticate or calibrate source clocks |
| Query horizon changes without rebinding evidence | Fingerprint validation fails | Trusted expected digests and signatures remain future work |

The evaluator remains pure and constant-time for the one-source candidate. A
future multi-source implementation will require explicit finality composition,
not merely an iteration over individually closed sources.

## Options Considered

### Compare only `evaluated_at` with a horizon

**Rejected.** It is vulnerable to the wait-only exploit: elapsed caller time
would bless an unchanged pre-horizon snapshot.

### Put the horizon in `SourceObservation`

**Rejected.** The runtime producer would control both the threshold and the
watermark offered as evidence that the threshold was satisfied.

### Treat `index_as_of >= query.time_end` as finality

**Rejected.** Index chronology does not describe late-arrival behavior or prove
that all events through the interval end have been incorporated.

### Trust `PENDING_WINDOW` or `OBSERVED` state labels

**Rejected.** Producer labels are observations, not independently derived gate
conditions. The evaluator must reject an optimistic label when chronology is
insufficient.

### Make the new field structurally required under the existing schema string

**Rejected for this increment.** That would make already accepted schema `1.0`
candidate syntax incompatible without changing the wire-schema major, contrary
to ADR-0007. Nullable syntax plus a non-relaxable, versioned policy preserves
diagnostic parsing and fail-closed authorization.

### Implement the full profile registry first

**Deferred, not rejected.** Profile IDs, versions, digests, issuers, validity,
and attestation are required before schema freeze and external assurance claims.
They are separable from the immediate correctness defect in the evaluator.

## Consequences

- A reported source watermark must reach the declared query-bound horizon; time
  passage alone cannot upgrade old evidence.
- Permitted wording may state that the reported index reached the declared
  horizon. It must not call the source complete, truthful, externally validated,
  or globally exhaustive.
- Existing schema `1.0` candidate inputs without a horizon become explicit
  rejections under the only supported policy rather than implicit permits.
- The policy, evaluator, package, examples, benchmark corpus, and active digest
  vectors change. The canonicalization algorithm and historical `0.1` freeze do
  not.
- Full source-profile governance, authenticated watermarks, snapshot
  consistency, correction/reopen semantics, complete certificates, multi-source
  composition, and the independent EmptyBench oracle remain open blockers.

## Acceptance Evidence

This candidate increment is accepted only when all of the following pass:

1. Missing/null, malformed, naive, and submicrosecond horizons fail closed.
2. Horizon and index comparisons pass exact below/equal/above boundary tests.
3. A fixed pre-horizon index remains rejected when only evaluation time advances.
4. Horizon mutation changes query fingerprints and request digests; stale
   bindings fail validation.
5. Parsed and programmatic policies cannot disable the horizon requirement, and
   the prior policy candidate is rejected.
6. Exact multi-fault reason ordering is tested.
7. EmptyBench adds a matched pair with the same query, horizon, visible zero,
   observation, and evaluation time while the source index varies immediately
   below versus equal to the horizon.
8. Source and installed tests pass on the primary Python runtime, source tests
   pass on every supported Python runtime, and seed output is byte-identical.
9. Static review confirms that the evaluator does not read ambient time.
10. Claims and status documents retain the profile, certificate, oracle,
    external-validation, and production-readiness limitations.

Meeting these criteria completes the explicit-horizon increment. It does not
freeze schema `1.0` or establish a complete evidence certificate.
