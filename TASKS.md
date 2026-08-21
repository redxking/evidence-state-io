# Tasks

## Active

- [ ] **Add required and observed source accounting** - Close the narrowest remaining ESIO-P0-002/003 gap with explicit required-source identity, observed status, accessible population, strict validation, and matched missing-source tests.
- [ ] **Derive pending finality explicitly** - Add a supplied finality horizon and exact below/equal/above boundary tests; do not consult wall-clock time.
- [ ] **Build the complete deterministic certificate** - Bind schema, evaluator and policy versions, origin classification, canonical input, verdict, reasons, qualification, and evaluation time; keep digest and signature semantics separate.

## Waiting On

- [ ] **Owner licensing decision** - Required before public distribution or package publication.
- [ ] **Owner approval for external discovery** - Required before contacting design partners or using any real workflow data.

## Someday

- [ ] **Evaluate an MCP interoperability profile** - Begin only after the contract survives a real read-only adapter and the frozen benchmark.
- [ ] **Evaluate trusted-time integration** - Keep separate from P0 evidence-coverage semantics.

## Done

- [x] ~~Initial local covered-versus-partial demonstration~~ (2026-08-21)
  - Python 3.13.0 source and installed suites and the Python 3.11 suite passed 171/171; the synthetic demonstrations passed 2/2 and 10/10.
  - Proposed 79-, 114-, 168-, and 169-test baselines were rejected after adversarial review. Reproduced defects were converted to regressions before the 171-test baseline was accepted locally.
  - Final replay passed the 98/98 core CLI exploit set across source/installed paths, 30/30 EmptyBench adversarial executions, 38/38 direct-library checks, and 6/6 source-index chronology probes.
  - The stale installed command was detected, the candidate package was reinstalled, and source/install package-file and deterministic-demo parity passed with `PYTHONPATH` unset.
  - The initial local commit binds the first accepted schema `0.1` and canonicalization-profile `0.1` snapshot; no earlier proposal was released or certificate-bearing.
  - This is locally tested, not a frozen benchmark or external reproduction.
