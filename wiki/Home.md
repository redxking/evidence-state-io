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

- [Concepts and state semantics](Concepts-and-State-Semantics)
- [Architecture and trust boundaries](Architecture-and-Trust-Boundaries)
- [EmptyBench research program](EmptyBench-Research-Program)
- [Roadmap and contribution paths](Roadmap-and-Contribution-Paths)
- [Reproducing the candidate](Reproducing-the-Candidate)
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
