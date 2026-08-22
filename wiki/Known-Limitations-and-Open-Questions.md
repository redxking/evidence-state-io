# Known limitations and open questions

- P0 supports exactly one required source; multi-source composition rejects.
- Registry snapshots, source identity, watermarks, clocks, and profile claims are not cryptographically authenticated.
- Replay certificates are unsigned deterministic records, not attestations.
- The current benchmark and oracle are implementation-owned and not independently adjudicated.
- The browser reference demonstrates parity on synthetic vectors; it is not the Python runtime or a production service.
- Real adapter feasibility, profile maintenance cost, market demand, and operational effectiveness remain unproven.

Open research questions include how to measure honest accessible population,
bind authenticated source/index evidence, manage profile revocation, compose
overlapping sources, and preserve qualifications through downstream AI and
human workflows without unacceptable integration cost.
