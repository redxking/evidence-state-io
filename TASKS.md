# Tasks

## Active

- [ ] **Define and bind the governed coverage/finality profile** - Add profile ID, version, digest, issuer/authority, validity, late-arrival and reopen assumptions, and exact query/certificate binding; treat the profile as a governed assertion, not proof that the source behavior is true.
- [ ] **Build the complete deterministic certificate** - Bind schema, evaluator and policy versions, origin classification, canonical input, verdict, reasons, qualification, and evaluation time; keep digest and signature semantics separate.
- [ ] **Separate the EmptyBench oracle** - Move expected outcomes outside executable request fixtures, freeze corpus and oracle digests, and add source/finality fault families without using the gate as its own truth source.

## Waiting On

- [ ] **Owner licensing decision** - Required before public distribution or package publication.
- [ ] **Owner approval for external discovery** - Required before contacting design partners or using any real workflow data.

## Someday

- [ ] **Evaluate an MCP interoperability profile** - Begin only after the contract survives a real read-only adapter and the frozen benchmark.
- [ ] **Evaluate trusted-time integration** - Keep separate from P0 evidence-coverage semantics.

## Done

- [x] ~~Derive declared finality chronology explicitly~~ (2026-08-21)
  - Package `0.3.0`, policy `1.0-candidate.2`, and evaluator
    `esio-evaluator-1.0-candidate.2` enforce a query-bound declared finality
    horizon without reading the wall clock.
  - A permit requires `query.time_end <= finality_horizon <= index_as_of <=
    observed_at <= evaluated_at <= valid_until`; waiting cannot upgrade an old
    snapshot.
  - Missing/null horizon, exact below/equal/above boundaries, malformed time,
    wait-only reuse, old policy, policy relaxation, stale fingerprint, digest
    mutation, reason ordering, CLI behavior, and offset normalization are tested.
  - EmptyBench now contains seven matched pairs/fourteen cases; its finality pair
    keeps the query, horizon, evaluation time, and visible zero constant while
    the source index moves by one microsecond.
  - Python 3.13 source/installed and Python 3.11 source suites passed 244/244;
    cross-runtime seed output passed 14/14 and was byte-identical.
  - Independent read-only review reproduced and corrected the legacy-fingerprint
    compatibility contradiction, then accepted the bounded fail-closed result.
  - This closes the evaluator chronology increment only. Governed profile
    authority, watermark authenticity, and source completeness remain open.
  - Candidate implementation checkpoint:
    `7deaea1dd79eacd2c4f3ebbef87a314e5293f1f6`.

- [x] ~~Add required and observed source accounting~~ (2026-08-21)
  - Package `0.2.0` accepts only the schema `1.0` candidate; query requirements and runtime observations are distinct and deterministically ordered.
  - Missing, non-observed, inaccessible, pending, stale, failed, contradictory, unknown, population-mismatched, and error-bearing required sources reject with source-attributed reasons.
  - The P0 candidate accepts exactly one declared `REQUIRED` source. Optional and multi-source declarations are rejected because one aggregate coverage object cannot establish source composition.
  - Required system, locator, adapter ID/version, authorization context, population, and detection assumptions are matched to the observation; coverage and observations are bound to a canonical query fingerprint.
  - Policy ID/version and evaluator version are explicit; certificate-level version binding remains open.
  - The schema `0.1` fixture, digests, and pinned `b6fac87` replay boundary are preserved without auto-migration. This is historical local evidence, not a current permit.
  - Python 3.13 source and installed-package verification and Python 3.11 source-overlay verification passed 224/224; the Python 3.11 source and Python 3.13 installed seed runs passed 12/12 and were byte-identical.
  - Candidate implementation checkpoint: `bdd7c1e15c45f8d9940fc76604b3dde1fa953faa`.

- [x] ~~Initial local covered-versus-partial demonstration~~ (2026-08-21)
  - Python 3.13.0 source and installed suites and the Python 3.11 suite passed 171/171; the synthetic demonstrations passed 2/2 and 10/10.
  - Proposed 79-, 114-, 168-, and 169-test baselines were rejected after adversarial review. Reproduced defects were converted to regressions before the 171-test baseline was accepted locally.
  - Final replay passed the 98/98 core CLI exploit set across source/installed paths, 30/30 EmptyBench adversarial executions, 38/38 direct-library checks, and 6/6 source-index chronology probes.
  - The stale installed command was detected, the candidate package was reinstalled, and source/install package-file and deterministic-demo parity passed with `PYTHONPATH` unset.
  - The initial local commit binds the first accepted schema `0.1` and canonicalization-profile `0.1` snapshot; no earlier proposal was released or certificate-bearing.
  - This is locally tested, not a frozen benchmark or external reproduction.
