# Reproducing the Candidate

## Supported environment

- Python 3.11, 3.12, or 3.13
- Git
- a laptop or VM
- network access only for initial dependency installation

The core evaluator, tests, and seed demonstration run without a model API,
GPU, database, or network service.

## Local sequence

```bash
git clone https://github.com/redxking/evidence-state-io.git
cd evidence-state-io
./scripts/setup.sh
source .venv/bin/activate
env -u PYTHONPATH ./scripts/check.sh
./scripts/test.sh
evidence-state demo --all
```

## Evidence discipline

Record the complete commit hash, worktree state, Python and dependency versions,
command, exit status, test count, fixture digest, and any skipped or blocked
step. A green run supports only the named behavior in that environment.

The checked-in permit and rejection examples are revision-neutral contract
vectors when their implementation assertion is `UNBOUND`. They are not proof
that a particular code revision produced them. Implementation custody comes
from the named Git revision and the separately recorded source/installed parity
run.

Follow the exact current sequence in
[`HANDOFF.md`](https://github.com/redxking/evidence-state-io/blob/main/HANDOFF.md)
and interpret results through
[`docs/CLAIMS_AND_BOUNDARIES.md`](https://github.com/redxking/evidence-state-io/blob/main/docs/CLAIMS_AND_BOUNDARIES.md).
