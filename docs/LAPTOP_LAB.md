# Laptop and Fault-Injection Lab

## Outcome

The core lab currently demonstrates two observationally identical empty results
with different coverage and pagination sufficiency for one declared source:

- a current case whose implemented coverage and pagination conditions pass and
  permit a scoped negative; and
- an incompletely paginated case that blocks it.

The core demonstration uses local synthetic JSON only. Docker, network access, API keys, and a model are not required.

Package `0.6.0` implements single required-versus-observed source accounting,
query binding, exact application-selected profile resolution, profile-derived
finality, unsigned deterministic replay certificates, and a separated
EmptyBench seed corpus/oracle under the current candidate contracts. The
operator demonstration still changes pagination only; the full regression seed
adds 11 other matched fault families. Independent oracle adjudication, a frozen
held-out campaign, external reproduction, and schema freeze remain target
evidence, not achieved benchmark claims.

## Safety boundary

This lab is for local research with synthetic/public-safe data or owner-approved nonsensitive data. It does not establish source completeness, authenticated profile or source evidence, operational effectiveness, independent validation, legal sufficiency, or production readiness.

Do not point the lab at a real source, reuse production credentials, ingest non-public data, expose container ports beyond loopback, or inject faults outside this repository's named Compose project without explicit owner and system-owner approval.

The relying application, not the observation producer, controls `examples/profile_registry.json` and `examples/profile_trust.json`. In any derived deployment, keep the registry snapshot, trust selection, and exact selected profile reference producer-unwritable. Their issuer, authority, source-owner, time, origin, revision, and tree-state labels remain unauthenticated assertions in P0.

## Prerequisites

Required:

- macOS, Linux, or a Linux VM;
- Python 3.11, 3.12, or 3.13;
- a POSIX shell;
- approximately 250 MB free disk for the Python environment.

Optional fault lab:

- Docker Engine or Docker Desktop with Compose v2;
- approximately 1 GB additional disk and 1 GB available memory;
- `curl` for controlling the local Toxiproxy API.

No GPU is required.

## Core setup

From the repository root:

```bash
./scripts/setup.sh
```

The script creates or reuses `.venv` inside the repository and installs a
non-editable project snapshot with its declared development extra. It validates the
installed console entry point and does not modify global Python packages or delete an
existing environment. The check, test, and demo wrappers put the current checkout's
`src` directory first on `PYTHONPATH`, so source changes are exercised offline after
initial setup. Rerun setup after any source change before relying on the installed-
package check or invoking the command with `PYTHONPATH` unset.

Activate the environment if you want to call the CLI directly:

```bash
source .venv/bin/activate
evidence-state --help
```

## Verify before demonstrating

```bash
./scripts/check.sh
./scripts/test.sh
```

Record the Python version and exact command output for any result that will be cited. An interrupted test is unresolved.

## Run the paired demonstration

```bash
./scripts/demo.sh
```

The wrapper calls the repository-local `evidence-state` entry point with the
current `src` tree overlaid. It must work without network access. Machine-readable
results are written by the CLI to stdout; wrapper diagnostics go to stderr. Use
`env -u PYTHONPATH .venv/bin/evidence-state demo` to exercise the installed copy
directly; `scripts/check.sh` requires the two package snapshots and demos to match.

The expected semantic comparison is:

| Case | Visible matches | Coverage condition | Expected negative-claim disposition |
|---|---:|---|---|
| Covered zero | 0 | All currently implemented coverage/pagination conditions pass | `PERMIT_SCOPED_NEGATIVE` |
| Matched partial | 0 | Pagination is incomplete and coverage is below policy | `REJECT_NEGATIVE` |

Do not treat process exit `0` as a permit decision. A valid evaluation that rejects a negative is still a successfully executed CLI command; inspect its JSON verdict.

## Evaluate a single JSON envelope

```bash
evidence-state evaluate \
  --input examples/covered_request.json \
  --registry examples/profile_registry.json \
  --trust examples/profile_trust.json \
  --issued-at 2026-08-21T12:06:00Z \
  --origin SYNTHETIC

evidence-state evaluate \
  --input examples/partial_request.json \
  --registry examples/profile_registry.json \
  --trust examples/profile_trust.json \
  --issued-at 2026-08-21T12:06:00Z \
  --origin SYNTHETIC

cat examples/covered_request.json | evidence-state evaluate \
  --input - \
  --registry examples/profile_registry.json \
  --trust examples/profile_trust.json \
  --issued-at 2026-08-21T12:06:00Z \
  --origin SYNTHETIC
```

The first request should return `PERMIT_SCOPED_NEGATIVE`; the second should return
`REJECT_NEGATIVE` with structured reasons while still exiting successfully. The
checked-in examples, `evidence-state --help`, and the JSON schema implemented by the
package are authoritative for the current interface. Use `./scripts/demo.sh` for the
canonical paired demonstration.

Each `evaluate` result is a self-contained certificate. It duplicates the full
normalized request, registry snapshot, trust selection, context bindings,
decision, limitations, origin, and implementation metadata. The SHA-256 digest
is integrity metadata, not a signature. Do not copy a certificate into source
control, CI artifacts, tickets, chat, or an external package unless every
embedded field is approved for that destination.

Replay-check the checked-in permit certificate against separately supplied
expected state:

```bash
evidence-state verify-certificate \
  --input examples/covered_certificate.json \
  --registry examples/profile_registry.json \
  --trust examples/profile_trust.json \
  --expected-digest sha256:5683e522aa22f08145658d49452a4c044d7cf562a6a3987da364b3322d4aab17 \
  --relying-party-at 2026-08-21T12:30:00Z
```

Verification reports structural, digest, embedded-binding, replay,
expected-context, expected-digest, and current-local-reliance dimensions. It
does not authenticate an issuer or authorize an action. The conservative
exclusive boundary accounts for evidence validity, snapshot next update,
applicable resolved-profile expiry/revocation, and policy/profile observation
and index age deadlines; candidate.2 trust selection has no separate expiration
field.

## Target P0 fault matrix

Each disqualifying case needs a covered control with the same visible result.

| Fault | Evidence change | Required result |
|---|---|---|
| Missing required source | Required source absent or unknown | Preserve partial/indeterminate state; reject negative |
| Wrong source/query binding | Identity, adapter, authorization context, population, or query fingerprint differs | reject or invalidate before negative evaluation |
| Producer-selected weak profile | Request reference differs from the application's exact selected profile, or tries an alias/range/fallback | reject before profile content or derived finality can influence the result |
| Untrusted or stale profile context | Snapshot/profile digest, issuer, authority, validity, or revocation check fails | reject; do not populate resolved references or consult applicability/finality semantics |
| Truncated pagination | Incomplete pages or continuation remains | `PARTIAL`; reject negative |
| Missing partition | One required partition incomplete | `PARTIAL`; reject negative |
| Stale evidence | Freshness limit exceeded at supplied evaluation time | `STALE`; reject negative |
| Inaccessible evidence | Required source cannot be read under declared boundary | `INACCESSIBLE`; reject negative |
| Pending finality | Reported source index remains before the declared late-arrival/finality horizon, even if evaluation time has advanced | `PENDING_WINDOW`; reject negative |
| Source/query failure | Disqualifying structured error remains | `FAILED`; reject negative |
| Contradictory evidence | Required observations cannot both be true under policy | `CONTRADICTORY`; reject negative |
| Positive match | At least one in-scope match | `PRESENT`; reject negative |

The exact aggregate state for simultaneous faults is policy-versioned. All underlying reason codes must remain visible.

## Optional container fault lab

The Compose `lab` profile provides:

- a loopback-bound Postgres instance containing synthetic source records; and
- Toxiproxy, which can introduce a timeout or latency between a future read-only adapter and that source.

It is not used by the core demo.

### Start

```bash
./scripts/lab.sh up
./scripts/lab.sh status
```

The script uses a fixed Compose project name, waits for local health checks, and creates only the named `source-db` proxy. It does not remove existing volumes or contact an external system.

### Inject one bounded fault

```bash
./scripts/lab.sh latency
./scripts/lab.sh timeout
```

Only one named toxic is maintained by the script. Applying a new supported fault first clears the prior scripted toxic.

### Clear and stop

```bash
./scripts/lab.sh clear
./scripts/lab.sh down
```

`down` stops and removes the lab containers and network but intentionally preserves the named volume. There is no automatic purge command. Delete the volume only through an explicit, separately reviewed action.

## Fault-to-state mapping

Transport failures do not inherently determine the domain state. The adapter mapping must be explicit and tested:

- inability to establish authorized access may map to `INACCESSIBLE`;
- a started observation that fails to complete may map to `FAILED`;
- a completed but truncated response maps to `PARTIAL`;
- a successful response older than the policy limit maps to `STALE`.

Do not infer `ABSENT_WITHIN_SCOPE` from a database connection, health check, HTTP success, or empty result.

## VM option

For stronger process isolation, run the same repository in a disposable Linux VM:

1. Create a non-privileged user.
2. Copy only the repository and synthetic fixtures.
3. Disable shared clipboard/folders if the lab is being used to test untrusted inputs.
4. Install a supported Python version (3.11, 3.12, or 3.13) and optionally Docker.
5. Run setup, checks, tests, and demo.
6. Export only the explicitly reviewed JSON result and runtime-version record.
7. Destroy the VM through the hypervisor after retaining required evidence.

VM destruction is intentionally not automated by repository scripts.

## Reproducibility record

For a citable local campaign, retain:

- repository commit or archive digest and dirty-state note;
- Python, operating system, and dependency versions;
- schema, evaluator, policy, evaluation-input, profile, registry, trust, certificate, canonicalization, digest, and fixture versions;
- supplied evaluation, issuance, and relying-party times;
- exact commands and exit codes;
- canonical inputs, JSON outputs, and digests;
- random seeds, if any;
- excluded or infrastructure-failed runs with reasons;
- exact origin label, such as `SYNTHETIC`, `REPLAYED`, or `LAB_OBSERVED`; the label is descriptive and unauthenticated.

A local record is not an independent reproduction merely because it was run in a VM or container.

## Troubleshooting

### Setup refuses the Python version

Install Python 3.11, 3.12, or 3.13 and set `PYTHON_BIN` explicitly:

```bash
PYTHON_BIN=python3.12 ./scripts/setup.sh
```

### The CLI is not found

Run setup, activate `.venv`, or use the wrappers, which call the repository-local executable directly.

### Docker is unavailable

Skip the optional fault lab. The core tests and demo must still work.

### A Compose port is occupied

Stop the conflicting local service or override the documented `ESIO_LAB_*_PORT` environment variable for this invocation. Do not bind the lab to a non-loopback address.

### A fault remains active

```bash
./scripts/lab.sh clear
./scripts/lab.sh status
```

If the local proxy is unhealthy, stop the lab and preserve logs before restarting. Do not reinterpret an infrastructure failure as a passed fault case.
