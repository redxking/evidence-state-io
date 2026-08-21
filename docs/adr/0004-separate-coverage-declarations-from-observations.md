# ADR-0004: Separate Coverage Declarations from Runtime Observations

**Status:** Accepted
**Date:** 2026-08-21
**Deciders:** Project owner; architecture maintainer

## Context

A source can be healthy and return an empty result while failing to cover the relevant population, field, interval, tenant, or detection mode. Conversely, a registry can declare broad coverage that is stale or false at runtime. Combining configuration and observations into one opaque source status would hide this distinction.

## Decision

Model source coverage profiles, query specifications, and runtime source observations as separate versioned objects. Resolve them under an explicit policy. Preserve the profile version and observation metadata in the certificate.

## Options Considered

### Option A: Separate declaration and observation

| Dimension | Assessment |
|---|---|
| Traceability | High |
| Configuration burden | Medium |
| Fault localization | High |
| Portability | High |

**Pros:** Distinguishes expected coverage from observed execution.
**Cons:** Requires registry ownership and drift management.

### Option B: Adapter returns one coverage boolean

| Dimension | Assessment |
|---|---|
| Traceability | Low |
| Implementation effort | Low |
| Adapter coupling | High |
| Independent verification | Low |

**Pros:** Simple interface.
**Cons:** Lets each adapter silently redefine completeness.

### Option C: Infer coverage from source health

| Dimension | Assessment |
|---|---|
| Traceability | Low |
| False assurance risk | High |
| Operational effort | Low |
| Query sensitivity | Low |

**Pros:** Uses common monitoring signals.
**Cons:** Health is neither query coverage nor detection adequacy.

## Trade-off Analysis

The extra configuration is the product's substantive input. Without it, the system can only restate that a query returned no rows. Registry assertions remain claims that need governance; separation makes that limitation visible.

## Consequences

- Registry changes are versioned and reviewable.
- Runtime observations bind to the exact profile used.
- Adapters remain translators rather than policy decision points.
- Coverage drift becomes a first-class operational risk and backlog item.

## Action Items

1. [ ] Define ownership and review metadata for source profiles.
2. [ ] Test mismatched query/profile versions and scope.
3. [ ] Add drift checks before any design-partner shadow evaluation.
