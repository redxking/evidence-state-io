# ADR-0014: Insufficiency Remedy and its Disclosure Boundary

**Status:** Accepted for local candidate implementation; not a schema freeze or release decision
**Date:** 2026-08-22
**Deciders:** Project owner; architecture maintainer

## Context

`REJECT_NEGATIVE` currently returns ordered reason codes and a deterministic
insufficiency statement. Both are correct and neither is actionable. An
operator who is told `COVERAGE_POLICY_NOT_MET` or
`INDEX_PRECEDES_FINALITY_HORIZON` still has to read the profile, the policy,
and the evaluator to work out what would have to become true.

Every constraint needed to answer that question is already resolved during
evaluation: the policy floors, the governed profile's population, retention,
blind intervals, freshness limits, and the derived finality horizon. Deriving
the answer requires no new input, no network, no clock, and no model. It is a
pure function of the decision that was already computed.

Doing this naively would be actively harmful. A rejection that also printed
"set the reported index to `2026-08-21T13:05:00Z` and coverage to `0.995`"
would be a working set of instructions for fabricating a permit. The producer
does not otherwise hold the profile: under ADR-0009 the relying application
supplies the registry snapshot and trust selection separately, precisely so
that the party producing the result does not control the whole governance
bundle. Emitting governed threshold values back to that party would erode the
separation ADR-0009 exists to create.

So the question is not whether the remedy can be computed. It is who may see
what, and how the output is prevented from reading as authority.

## Decision

### 1. A remedy is a separate derived record

The contract is `esio-insufficiency-remedy/1.0-candidate.1`. It is derived from
a completed `GateDecision` together with the request and trusted context that
produced it. It is not a decision, not an input to a decision, and not part of
the evaluation-input digest. It is bound to the decision it explains by that
decision's `input_digest`, so a remedy cannot be silently attached to a
different evaluation.

A remedy is never produced for `PERMIT_SCOPED_NEGATIVE`. There is nothing to
remedy, and emitting one would invite reading a permit as conditional.

### 2. Remedies describe conditions, never edits

Each item states a condition that would have to hold in the world or in the
observed evidence. No item instructs the caller to change a request field, and
no item echoes a value the caller did not already supply, except under the
explicit disclosure level in section 4.

The distinction is load-bearing. `PROFILE_POPULATION_MISMATCH` yields "the
query must target the population the governed profile declares", not "set
`population` to `p-2`". The first describes a constraint the caller must
genuinely satisfy; the second is a fabrication recipe.

### 3. Remedy classes

Every material reason is classified. The classes are:

| Class | Meaning |
|---|---|
| `AWAIT_SOURCE_STATE` | The source's own index must advance before the window can be closed. |
| `OBTAIN_FRESH_OBSERVATION` | The observation or index exists but is older than a governed limit. |
| `OBTAIN_COMPLETE_ENUMERATION` | Enumeration is incomplete against the declared denominator. |
| `OBTAIN_MISSING_DECLARATION` | A required declaration was never reported by the source. |
| `RESOLVE_SOURCE_AVAILABILITY` | A required source is missing, unobserved, inaccessible, pending, failed, or of unknown status. |
| `USE_GOVERNED_SCOPE` | The request's scope disagrees with the governed profile. |
| `RESOLVE_GOVERNANCE_TRUST` | Registry or profile trust failed; only the relying application can act. |
| `UNSATISFIABLE` | No further evidence about the same query and population can remove this reason. |

`UNSATISFIABLE` is reserved for reasons that assert a fact incompatible with
the requested negative: an absolute claim, a nonzero in-scope match count, or a
required source that reported contradictory evidence. Where a reason's class
depends on the observed evidence rather than the code alone, it is computed
from that evidence. `STATE_NOT_ABSENT_WITHIN_SCOPE` is `UNSATISFIABLE` when the
reported state is `PRESENT`, because presence is not an evidence shortfall, and
otherwise remediable.

A remedy carries `satisfiable: false` when any item is `UNSATISFIABLE`. A
caller must not read a satisfiable remedy as a prediction that following it
will produce a permit. Only new evidence, re-evaluated through the same gate,
produces a decision.

### 4. Disclosure is a relying-application choice, defaulting closed

Two levels:

- `CONSTRAINT_ONLY` (default) names the failing constraint and its class and
  carries no governed threshold values.
- `WITH_GOVERNED_VALUES` additionally carries the exact governed values: the
  derived finality horizon, the coverage floor, the retention window, the
  freshness limits.

`WITH_GOVERNED_VALUES` is only appropriate for a caller that already holds the
profile, which under ADR-0009 means the relying application. Passing a remedy
produced at that level back to the result producer hands it the thresholds it
would need to construct a self-consistent fabrication, and the P0 gate cannot
detect that: it has no authenticated adapter evidence. The default is closed,
the level is recorded in the record itself, and the limitation is stated in
every remedy at that level.

### 5. Determinism

Remedy derivation is a pure function of the decision, request, trusted context,
and disclosure level. Item order follows the decision's reason order, which is
already deterministic. Identical inputs produce byte-identical output under
`esio-canonical-json-0.1`.

### 6. A certificate may be explained, once its bindings hold

The artifact a relying party actually holds is a certificate, not a request, so
a remedy may be derived from one directly. The certificate already binds the
complete request and trusted context, so no registry or trust selection needs
to be supplied again.

Before anything is derived, the record's own bindings are verified: structural
support, outer digest integrity, embedded binding integrity, and deterministic
replay must all hold. A certificate that fails any of them is refused rather
than explained, because conditions derived from a record that is not what it
claims would be attributed to a claim nobody made. The resulting remedy names
the certificate digest it explains and states that replay is not issuer
authentication, source truth, or current reliance eligibility.

This addition moved the contract to `esio-insufficiency-remedy/1.0-candidate.2`,
which adds the optional `certificate_digest` field. The candidate.1 shape is
otherwise unchanged.

## Consequences

Rejections become actionable without changing what a permit means. The
evaluator is untouched; no new state, disposition, reason code, or threshold is
introduced, and no existing gate behaviour changes.

The disclosure boundary is a genuine cost. A caller at `CONSTRAINT_ONLY`
learns which constraint failed but not what value would satisfy it, which is
less useful and deliberately so. Projects that want the fuller answer must
decide that their caller is entitled to the profile's contents.

## What this does not establish

A remedy does not authorize anything, does not predict a future decision, and
does not establish that following it is possible or that the underlying fact is
true. It does not make the gate safe against a malicious producer: that still
requires authenticated adapter evidence, which P0 does not have. It does not
reduce the disclosure risk to zero at `WITH_GOVERNED_VALUES`; it makes that
risk an explicit, recorded choice instead of an accident.
