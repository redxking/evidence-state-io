# ADR-0002: Use Versioned JSON Contracts and a Pure Evaluator

**Status:** Accepted
**Date:** 2026-08-21
**Deciders:** Project owner; architecture maintainer

## Context

Evidence-State I/O must support replay, paired comparisons, shell automation, and cross-language inspection. Hidden wall-clock reads, implicit defaults, or environment-dependent serialization would make published decisions difficult to reproduce.

## Decision

Use versioned JSON as the P0 interchange format. Pass the registry snapshot, policy version, and evaluation time explicitly into a side-effect-free evaluator. Reject unknown required semantics rather than guessing. Canonicalize supported JSON values before calculating fingerprints.

## Options Considered

### Option A: Versioned JSON plus pure functions

| Dimension | Assessment |
|---|---|
| Interoperability | High |
| Human inspectability | High |
| Deterministic testing | High |
| Schema expressiveness | Medium-high |

**Pros:** Portable fixtures, straightforward CLI, easy property testing.
**Cons:** Requires disciplined schema evolution and canonicalization.

### Option B: Python object/pickle interface

| Dimension | Assessment |
|---|---|
| Interoperability | Low |
| Human inspectability | Low |
| Security | Poor for untrusted input |
| Implementation effort | Low |

**Pros:** Minimal mapping code.
**Cons:** Unsafe for untrusted data and tightly coupled to Python implementation details.

### Option C: Protobuf/gRPC first

| Dimension | Assessment |
|---|---|
| Interoperability | High |
| Human inspectability | Medium |
| Tooling complexity | Medium-high |
| P0 fit | Low |

**Pros:** Strong schemas and generated clients.
**Cons:** Adds build tooling and service assumptions before the contract stabilizes.

## Trade-off Analysis

JSON provides the lowest-friction independent inspection surface. Its ambiguity is controlled with strict validation, explicit versions, portable timestamps, prohibited non-finite numbers, and a tested canonicalization profile.

## Consequences

- The same input can be used by the CLI, tests, benchmark, and future adapters.
- The evaluator cannot directly read the wall clock, environment variables, filesystem, or network.
- Schema and policy versions become evidence-bearing fields.
- A future binary protocol may wrap, but must not redefine, domain semantics.

## Initial Freeze and Evolution Boundary

The 79-, 114-, 168-, and 169-test snapshots were rejected development
proposals. They were never released, published as a benchmark, treated as an
accepted schema contract, or used to issue a certificate. The 171-test snapshot
is therefore the first accepted local freeze of schema `0.1` and
canonicalization profile `0.1`; the hardening that preceded it did not revise an
accepted version in place.

After this freeze, an incompatible accepted input, output, reason, or
canonicalization change requires a new applicable version and compatibility
evidence. An implementation version alone must not be used to hide a contract
change. Policy and certificate version binding is still incomplete and remains
a P0 requirement before any external certificate claim.

## Action Items

1. [x] Establish the first local schema `0.1` fixture and invalid-input freeze in the 171-test commit-bound snapshot.
2. [x] Add local replay tests across supported Python 3.11 and 3.13 versions. The hosted CI job remains unexecuted.
3. [ ] Document the exact canonicalization profile before any external certificate claim.
