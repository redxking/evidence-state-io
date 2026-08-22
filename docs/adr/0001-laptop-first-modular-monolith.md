# ADR-0001: Use a Laptop-First Modular Monolith

**Status:** Accepted
**Date:** 2026-08-21
**Deciders:** Project owner; architecture maintainer

## Context

The first product question is whether a deterministic evidence-state gate can reduce unsupported negative conclusions on a frozen paired benchmark. The project needs rapid local iteration, inspectable state transitions, reproducible tests, and a low-friction external reproduction path. It does not yet need independent scaling of services, a hosted API, or distributed operations.

## Decision

Implement P0 as one Python package supporting exactly Python 3.11, 3.12, and 3.13, with internal module boundaries for contracts, coverage resolution, evaluation, gating, certification, benchmarks, adapters, and CLI. The core library and `evidence-state` JSON CLI run without containers or network services.

Optional adapters use ports defined by the application layer. Compose is reserved for an opt-in disposable fault lab.

## Options Considered

### Option A: Modular monolith

| Dimension | Assessment |
|---|---|
| Complexity | Low |
| Laptop reproducibility | High |
| Failure isolation | In-process only |
| Scaling | Vertical; sufficient for P0 |
| Debuggability | High |

**Pros:** Fast tests, transactional reasoning, simple installation, fewer false infrastructure failures.
**Cons:** Does not demonstrate distributed independence or service-level scaling.

### Option B: Microservices and message bus

| Dimension | Assessment |
|---|---|
| Complexity | High |
| Laptop reproducibility | Medium-low |
| Failure isolation | Stronger at runtime |
| Scaling | Independent |
| Debuggability | Lower initially |

**Pros:** Production-shaped boundaries and independent deployment.
**Cons:** Adds network, orchestration, and custody claims before the core evaluator is validated.

### Option C: Hosted serverless API

| Dimension | Assessment |
|---|---|
| Complexity | Medium |
| Laptop reproducibility | Low |
| Cost | Usage-dependent |
| Vendor portability | Lower |
| Time to first experiment | Medium |

**Pros:** Easy remote access.
**Cons:** Requires accounts, network, deployment, and cost; conflicts with offline reproduction.

## Trade-off Analysis

The current risk is semantic correctness, not throughput. A monolith minimizes unrelated variables while preserving interfaces that permit later extraction. Distributed deployment would not make an incorrect coverage model more trustworthy.

## Consequences

- Contributors can reproduce the core experiment with Python alone.
- Domain functions must remain independent of CLI and storage modules.
- Process separation, independent custody, and high availability remain explicitly unproven.
- A service split requires new evidence that independent scaling or trust separation is needed.

## Action Items

1. [ ] Keep the evaluator callable as a pure library function.
2. [ ] Add import-boundary tests that prevent adapters from leaking into the domain layer.
3. [ ] Revisit only after P0 falsification gates pass or a real adapter imposes a demonstrated boundary.
