# Quick start

```bash
git clone https://github.com/redxking/evidence-state-io.git
cd evidence-state-io
./scripts/setup.sh
source .venv/bin/activate
./scripts/test.sh
evidence-state demo --all --pretty
```

Run `./scripts/acceptance.sh` for the isolated local acceptance gate. The core
requires no GPU, credentials, network service, or external model. See
[Reproducing the Candidate](Reproducing-the-Candidate) for exact verification
and benchmark commands.
