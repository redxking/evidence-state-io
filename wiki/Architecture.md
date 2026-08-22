# Architecture

Evidence-State I/O is a dependency-light Python 3.11–3.13 modular monolith with
an offline deterministic core. The application supplies the producer request,
registry snapshot, trust selection, named policy, and explicit evaluation time.
The core validates closed schemas, canonicalizes inputs, resolves the selected
profile, evaluates evidence, renders a bounded statement, and emits a replay
certificate.

Network access, ambient time, host state, LLM output, and unseeded randomness
are excluded from the decision path. Operational metadata remains outside the
deterministic payload. See [Architecture and Trust Boundaries](Architecture-and-Trust-Boundaries)
and the authoritative [repository architecture](https://github.com/redxking/evidence-state-io/blob/main/docs/ARCHITECTURE.md).
