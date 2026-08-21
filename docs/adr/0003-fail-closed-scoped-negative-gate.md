# ADR-0003: Fail Closed on Negative Claims and Permit Only Scoped Absence

**Status:** Accepted
**Date:** 2026-08-21
**Deciders:** Project owner; architecture maintainer

## Context

An empty result can arise from true absence, missing sources, inadequate permissions, filtering, pagination truncation, staleness, late-arriving data, source failure, or contradiction. Treating all empty results as equivalent creates the failure this project exists to measure.

## Decision

Only `ABSENT_WITHIN_SCOPE` may authorize a negative factual claim, and only with the exact evaluated scope and assumptions. `PRESENT` rejects the negative because contrary evidence exists. Every other evidence state blocks an unqualified negative and returns structured unresolved conditions.

The gate is deterministic and cannot be overridden by explanatory text or a model response.

## Options Considered

### Option A: Fail-closed scoped gate

| Dimension | Assessment |
|---|---|
| False-absence resistance | High |
| Benign negative retention | Policy-dependent |
| Explainability | High with reason codes |
| Operational friction | Medium |

**Pros:** Preserves uncertainty and makes negative claims auditable.
**Cons:** Poor coverage profiles may cause excessive blocking.

### Option B: Confidence threshold

| Dimension | Assessment |
|---|---|
| False-absence resistance | Variable |
| Determinism | Medium |
| Calibration burden | High |
| Explainability | Medium-low |

**Pros:** Flexible.
**Cons:** A scalar confidence can hide qualitatively different missing-coverage conditions.

### Option C: Warning-only output

| Dimension | Assessment |
|---|---|
| False-absence resistance | Low |
| Integration friction | Low |
| User discretion | High |
| Testability | Medium |

**Pros:** Easy adoption.
**Cons:** Callers may ignore warnings and emit the unsupported claim unchanged.

## Trade-off Analysis

The research thesis requires a control, not an annotation. Excessive abstention is addressed through matched controls and supported-negative retention metrics rather than weakening the gate.

## Consequences

- Every state and reason code needs an explicit gate mapping.
- New fault classes require a matched supported control.
- The system must measure both false negatives and unnecessary abstention.
- Policy owners must improve coverage declarations rather than bypass the gate.

## Action Items

1. [ ] Add invariant tests that no indeterminate state permits a negative.
2. [ ] Add mutation/property tests around freshness and finality boundaries.
3. [ ] Measure supported-negative retention in every benchmark release.
