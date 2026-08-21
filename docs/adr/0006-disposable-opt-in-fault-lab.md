# ADR-0006: Keep Fault Injection Disposable, Synthetic, and Opt In

**Status:** Accepted
**Date:** 2026-08-21
**Deciders:** Project owner; architecture maintainer

## Context

Network and source faults are necessary to test `INACCESSIBLE`, `FAILED`, and partial-observation behavior. Automatically targeting live systems, reusing real data, or making containers mandatory would create safety, authorization, and reproducibility problems.

## Decision

Keep the core paired demo fixture-based and dependency-free. Provide an optional Compose `lab` profile containing only disposable, loopback-bound infrastructure and synthetic records. Fault scripts act only on the named local Compose project, require an explicit fault name, and never delete volumes automatically.

## Options Considered

### Option A: Optional local container lab

| Dimension | Assessment |
|---|---|
| Safety | High with scope checks |
| Realism | Medium |
| Laptop cost | Low-medium |
| Core dependency | None |

**Pros:** Repeatable transport faults without touching real systems.
**Cons:** Does not establish behavior against a production source.

### Option B: Fault injection against a shared cloud environment

| Dimension | Assessment |
|---|---|
| Safety | Low without extensive controls |
| Realism | High |
| Cost | Variable |
| Reproducibility | Medium-low |

**Pros:** Production-shaped infrastructure.
**Cons:** Requires accounts, authorization, cost controls, and cleanup.

### Option C: Unit-test mocks only

| Dimension | Assessment |
|---|---|
| Safety | High |
| Realism | Low |
| Cost | Low |
| Failure coverage | Medium |

**Pros:** Fast and deterministic.
**Cons:** Cannot expose adapter behavior under real connection interruption.

## Trade-off Analysis

P0 needs both fast fixture tests and a bounded path to exercise transport behavior. An optional local lab provides that path without turning a research prototype into an operational testing tool.

## Consequences

- Docker is never required for the core demo or unit suite.
- Lab data is synthetic and ports bind to `127.0.0.1`.
- Users intentionally start, fault, clear, and stop the lab.
- Results remain local lab evidence, not production validation.

## Action Items

1. [ ] Validate Compose configuration in CI without starting services.
2. [ ] Add adapter integration tests only after the adapter exists.
3. [ ] Require owner approval before any real-source fault exercise.
