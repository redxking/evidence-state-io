# ADR-0015: Multi-Source Composition

**Status:** Accepted for local candidate implementation and wired into
envelope schema `1.1`, `CORROBORATION` only; not a schema freeze and not a
release decision
**Date:** 2026-08-22
**Deciders:** Project owner (pending); architecture maintainer

## Status update, 2026-08-22

Composition is now reachable from an envelope. Schema `1.1` is additive and
`1.0` is unchanged: a `1.0` envelope may not declare a composition mode or
carry a per-source assessment, every new field is omitted from the canonical
form when absent, and every recorded `1.0` fingerprint, digest, and
certificate still verifies.

The three structural facts named in the Context below were resolved rather
than worked around.

*One envelope-level `CoverageEvidence`.* `SourceObservation` now carries its
own optional assessment: `coverage`, `state`, `matched_count`, `observed_at`,
and `valid_until`. A composed envelope must supply the first four for every
required source, because composition is a conclusion drawn from per-source
evidence and cannot be drawn from evidence that was never supplied. A source's
declared state must also be compatible with its runtime status, so a producer
cannot relabel a failed fetch as an in-scope absence.

*One `selected_profile_reference`.* `ProfileTrustSelection` gained
`additional_selected_profile_references`. The singular field remains the
schema `1.0` form and stays first, so a single-source selection keeps its exact
canonical form and digest, and governance now matches a producer's reference
against any profile the relying application selected.

*One finality horizon.* Each source is checked against **its own** horizon and
the composed claim binds on the latest of them. Freshness now ages from the
stalest contributing observation rather than from the envelope timestamp, so a
late-sealed envelope cannot hide a source that was read hours earlier.

Two conditions were added at the gate that the composer alone could not
express: an envelope may not declare a coverage floor above what the sources
jointly guarantee (`COMPOSED_COVERAGE_OVERSTATED`), and it may not remain
valid past the earliest boundary any contributing source declared
(`COMPOSED_VALIDITY_OVERSTATED`).

`PARTITION` and `OPTIONAL` sources remain deferred for the reasons recorded
below.

## Context

`QueryScope` rejects any query that does not declare exactly one `REQUIRED`
source. That restriction is honest rather than arbitrary: nothing in the
current contract says what a negative claim across several sources would mean.

It is also the ceiling on the product. A real absence question in the first
vertical does not live in one system. "No lateral movement from this host in
this window" is answered from endpoint telemetry *and* proxy logs *and* DNS,
and each of those covers a different slice of the population with a different
retention window, a different index lag, and a different late-arrival profile.

Three structural facts make this more than relaxing a length check.

`CoverageEvidence` is a single envelope-level record, not one per source.
There is one `examined_units`, one `population_units`, one pagination state.
With two sources present, every one of those fields becomes ambiguous.

`ProfileTrustSelection` pins exactly one `selected_profile_reference`. Coverage
and finality semantics come from that profile. Two sources need two governed
profiles, so the relying application's trust selection has to become a mapping
rather than a single reference.

The finality horizon is derived per source from that source's profile. Two
sources settle at different times, so "when is this claim final" stops having
one answer.

## The failure this must not repeat

The project exists because an empty result is not evidence of absence. The
multi-source analogue is close enough to be worth stating outright.

If source A covers 60% of the population and source B covers 60% of the same
population, the union is covered somewhere between 60% and 100%. Which of those
it actually is depends on the overlap between A and B, and the overlap is not
observed. Any rule that adds the two — or averages them, or treats agreement as
a coverage bonus — manufactures coverage out of an overlap nobody measured.

"Two sources both returned nothing" is not "the union was covered." It is the
original error wearing a second source as a disguise, and it is more persuasive
than the original because it looks like corroboration.

## Decision

### 1. Composition intent is declared, never inferred

A multi-source query declares exactly one composition mode. The evaluator never
guesses which was meant, and a query that mixes them rejects.

**`PARTITION`** — the declared population is divided among the sources, each
covering a disjoint part. This is the only mode in which coverage accumulates.
Each source declares its accessible subpopulation; the subpopulations must be
declared disjoint and their union must equal the query's declared population.
An undeclared or non-exhaustive partition rejects: a gap between the parts and
the whole is exactly an uncovered region, and an uncovered region is why
`ABSENT_WITHIN_SCOPE` would be unsupportable.

**`CORROBORATION`** — every source claims to observe the same declared
population. Coverage does **not** accumulate.

### 2. Corroboration composes by maximum, never by sum

Under `CORROBORATION` the composed coverage lower bound is the **maximum** of
the per-source lower bounds, not the sum, not the mean, and not a function that
rewards agreement.

This follows from what a lower bound is. Each source's bound is a guarantee
about that source alone. The union is guaranteed to be at least as covered as
the best single source, and nothing observed licenses more than that. The
conservative floor is therefore the maximum, and the existing evaluator already
takes the minimum across a single source's own component bounds, so the
composed rule extends the same conservatism outward rather than reversing it.

Additional corroborating sources buy robustness against one source being wrong,
unavailable, or dishonest. They do not buy coverage. A design that let them buy
coverage would let a caller reach a permit by adding sources rather than by
observing more.

### 3. Optional sources may veto and may never authorize

A source declared `OPTIONAL` never raises composed coverage, never contributes
to a partition, and never helps satisfy finality. It can do exactly one thing:
contradict. An optional source reporting in-scope matches, or reporting
evidence inconsistent with the required sources, forces `CONTRADICTORY` and a
rejection.

This asymmetry is the point. Evidence that is not good enough to be required is
not good enough to authorize, but it is always good enough to raise doubt. It
extends the existing rule that a healthy source and an empty payload are not
coverage proof.

### 4. Finality binds on the slowest source

The composed finality horizon is the **latest** horizon across required
sources, and each required source's reported index must independently reach
**its own** horizon.

Taking the earliest, or a single shared horizon, would permit a claim during a
window in which a lagging source could still receive a late arrival for the
queried interval. The claim is not final until every required source has
settled, and a source is settled only against its own governed bounds.

### 5. Freshness composes on the worst source

Composed observation age and index age are the **maximum** ages across required
sources; the composed validity boundary is the **earliest** `valid_until`. A
multi-source claim is exactly as fresh as its stalest constituent.

### 6. Disagreement rejects; it is never resolved by counting

If required sources disagree about the same population — one reporting
`PRESENT` or nonzero matches while another reports `ABSENT_WITHIN_SCOPE` — the
composed state is `CONTRADICTORY` and the claim rejects.

There is no majority rule, no confidence weighting, and no tie-break. Voting
would convert a contradiction into a permit whenever the fabricating side
brought more sources, and the gate has no authenticated adapter evidence with
which to tell an honest minority from a dishonest majority.

### 7. Trust selection becomes a mapping, and must be total

`ProfileTrustSelection` gains a mapping from `source_id` to a pinned profile
reference. Every required source must have a selected profile; a partial
selection rejects rather than falling back to a default, to any other profile
in the snapshot, or to the single-source behaviour.

The ADR-0009 separation is preserved per source: the producer's request carries
each source's exact profile reference inside the query fingerprint, and the
relying application separately pins which profile it selected for that source.

### 8. Coverage evidence becomes per-source

`CoverageEvidence` moves inside each source observation. The envelope carries
the composed assessment, derived by the evaluator, and never a
producer-supplied composite. A producer that supplies a composite coverage
figure for a multi-source query rejects: the composition is the evaluator's
conclusion, not the producer's assertion.

### 9. The query fingerprint binds the whole set

The normalized fingerprint binds the complete ordered set of source
requirements and the declared composition mode, so a source cannot be dropped,
added, or re-roled after the fact without invalidating the request.

### 10. Single-source behaviour is unchanged

A query declaring one `REQUIRED` source evaluates exactly as it does today and
produces byte-identical output. Multi-source is a new capability under a new
schema version, not a reinterpretation of existing records.

## Consequences

The gate can answer questions it currently refuses, which is the point. It also
acquires several ways to be wrong that it does not have today, and the rules
above are deliberately the conservative branch at every fork: maximum for
corroborated coverage, latest for finality, worst for freshness, earliest for
validity, reject for disagreement, veto-only for optional sources.

`PARTITION` will be hard to satisfy in practice, because declaring a disjoint
exhaustive partition of a real population is hard. That difficulty is
information: if the partition cannot be declared honestly, the negative claim
across those sources was not supportable to begin with, and the gate should say
so rather than approximate.

Two sources will frequently produce a *lower* composed permit rate than one,
because finality binds on the slowest and freshness on the stalest. Callers who
expect more sources to mean more permits will be surprised. That expectation is
the error this ADR is written against.

The changes to `CoverageEvidence`, `ProfileTrustSelection`, and the query
fingerprint are breaking, so this is a new schema candidate rather than an
amendment to schema `1.0`.

## What this does not decide

This ADR is **Proposed**. It authorizes no implementation. It does not select a
schema version, define wire shapes, or commit to a delivery order.

It does not address cross-source identity — whether two sources referring to
"the same host" are referring to the same entity is an unsolved problem this
design assumes away by requiring the declared population to be stated in terms
the profiles already govern.

It does not weaken the standing limits. Composition does not authenticate any
source, does not establish that a declared partition is truthful, does not
prove ingestion completeness for any constituent, and does not make a composed
`ABSENT_WITHIN_SCOPE` mean anything beyond the union of the declared,
governed, accessible populations over the declared interval.

## Owner decisions, 2026-08-22

The three questions this ADR closed with were answered as follows.

**`CORROBORATION` ships alone.** `PARTITION` is the only mode in which coverage
accumulates, and it requires each source to declare a disjoint accessible
subpopulation whose union equals the queried population. Nothing in the
governed profile expresses that today, so admitting the mode before it can be
checked would mean accepting an undeclared partition — which is exactly an
uncovered region, and exactly what a supportable negative may not contain.
The cost is real and is accepted: corroboration cannot answer a question that
no single source covers, which is much of why one wants multi-source at all.

**`OPTIONAL` sources are deferred.** Their only power is to reject, and every
rejection they could cause is already reachable by declaring the source
`REQUIRED`. A role that can never contribute to a permit is a real and useful
concept, but it adds contract surface to the first candidate for no
permit-side benefit. `SourceRole.OPTIONAL` continues to reject as it does
today. The veto-never-authorize rule in section 3 remains the design for when
the role arrives.

**Required sources are capped at four.** This is a fail-closed bound chosen so
a composed assessment stays reviewable by hand, in keeping with the other
explicit bounds in the contract. It is not a performance limit.

## Delivery

Semantics land before schema. `src/evidence_state_io/composition.py`
implements the rules above as pure functions over per-source contributions,
under `esio-multi-source-composition/1.0-candidate.1`, and is not yet reachable
from an envelope. The schema wiring is deliberately separate work: the
envelope's `schema_version` is pinned to `1.0`, `CoverageEvidence` is a single
envelope-level record, and `ProfileTrustSelection` pins one profile, so
admitting a multi-source envelope is a breaking change to three contracts at
once.

Ordering it this way means the schema change lands on rules already pinned by
property tests and mutation testing, rather than the semantics being settled
under the pressure of a half-finished migration.
