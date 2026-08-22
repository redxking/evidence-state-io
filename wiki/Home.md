# Evidence-State I/O Wiki

Evidence-State I/O is an open research and engineering project for a narrow
failure mode: an empty observation is often converted into an unsupported
negative conclusion.

The project makes the conditions behind a negative conclusion explicit,
machine-readable, deterministic, and replayable. It is organized around three
connected product surfaces:

1. **EmptyBench** — matched cases that hold the visible empty result constant
   while changing evidence sufficiency.
2. **Evidence-State Gateway** — a deterministic gate that permits only a
   generated, scope-preserving negative when every required condition passes.
3. **Coverage Registry** — governed source profiles for population, access,
   retention, blind intervals, freshness, and finality.

## Start here

- Leaders: [Executive overview](Executive-Overview) and [product scope](Product-Scope-and-Non-Goals)
- Architects: [Architecture](Architecture), [pipeline](Gateway-Processing-Pipeline), and [integration guide](Integration-Guide)
- Security and assurance: [Threat model](Security-and-Threat-Model) and [governance](Governance-and-Assurance)
- Engineers and operators: [Quick start](Quick-Start), [contracts](Schemas-and-Interface-Contracts), and [operations](Operations-and-Troubleshooting)
- Researchers: [Benchmark methodology](Benchmark-Methodology), [verification strategy](Test-and-Verification-Strategy), and [open questions](Known-Limitations-and-Open-Questions)
- [Frequently asked questions](FAQ)

## Current evidence boundary

This repository is a pre-alpha research candidate. Local deterministic tests
can establish behavior for an exact revision, runtime, fixture, and
configuration. They do not establish source truth, production readiness,
operational effectiveness, market demand, legal sufficiency, or independent
validation.

The authoritative engineering record remains in the main repository. The wiki
is an orientation and collaboration surface; if it conflicts with the versioned
contracts, ADRs, `PROJECT_STATUS.md`, or `docs/TRACEABILITY.md`, the repository
record controls.
