# Project control records

This directory is the machine-readable control plane for continued project
delivery. It is operational metadata, not part of the deterministic gateway
decision path.

- `state.json` records the observed local and remote lifecycle state.
- `tasks.json` links bounded work to stable acceptance identifiers.
- `acceptance.json` uses only `PASS`, `FAIL`, `BLOCKED`, `UNVERIFIED`, and
  `STALE`; every pass requires evidence and a watched-input fingerprint.
- `progress.jsonl` is append-only evidence and progress history.

Run the bounded controller from the repository root:

```bash
python -m evidence_state_io.advance --repo . --status
python -m evidence_state_io.advance --repo . --reconcile --remote
python -m evidence_state_io.advance --repo . --reconcile --remote \
  --until-blocked --max-iterations 1
```

The controller acquires a lock under `.git`, invalidates a passed row when its
declared watched inputs change, and stops when the next task needs engineering,
owner authority, or external verification. It does not invent an implementation
or convert a successful command into broader evidence than the task declares.
The four tracked control records are excluded from watched-content fingerprints
because embedding a digest of an evidence ledger inside that same ledger is
self-referential. Their exact custody is instead bound by the Git commit and
remote/ref checks recorded for publication and release.
