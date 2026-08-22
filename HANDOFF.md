# Project Handoff

## Mission

Create and validate an open evidence-state contract and reference gateway that prevent AI systems from turning non-observation into an unsupported negative conclusion.

This is the restart document for a human engineer or autonomous coding agent. `PROJECT_STATUS.md` and verification output determine what is actually established; this handoff does not substitute for evidence.

## Restart state

The current working target is package `0.6.0` with:

| Boundary | Active identifier |
|---|---|
| Wire schema | `1.0` candidate, unfrozen |
| Policy | `esio-p0-safety-floor/1.0-candidate.4` |
| Evaluator | `esio-evaluator-1.0-candidate.5` |
| Coverage/finality profile | `esio-coverage-finality-profile/1.0-candidate.2` |
| Registry snapshot | `esio-profile-registry-snapshot/1.0-candidate.2` |
| Trust selection | `esio-profile-trust-selection/1.0-candidate.2` |
| Evaluation input | `esio-evaluation-input/1.0-candidate.2` |
| Evidence certificate | `esio-evidence-certificate/1.0-candidate.2` |
| Evidence-state transitions | `esio-evidence-state-transition-model/1.0-candidate.1` |
| Authorization-context identifier | `esio-authorization-context-identifier/1.0-candidate.1` |
| Validation error | `esio-validation-error/1.0-candidate.1` |
| EmptyBench corpus | `esio-emptybench-corpus/1.0-candidate.1` |
| EmptyBench oracle | `esio-emptybench-oracle/1.0-candidate.1` |
| EmptyBench report | `esio-emptybench-report/1.0-candidate.1` |
| Canonicalization | `esio-canonical-json-0.1` |
| Digest | SHA-256 |

The implementation and adversarial hardening work exists and the moving-tree source suite has passed. Final acceptance and custody are not complete. Do not announce a schema freeze, benchmark freeze, release, or accepted `0.6.0` checkpoint until the active task in `TASKS.md` is run against one stable revision and the exact results are recorded.

The active parser intentionally rejects schema `0.1`. Historical replay is preserved in `examples/legacy/` and requires checkout of pinned implementation `b6fac87`. Do not relabel or auto-migrate that fixture, and do not treat its local historical result as a current permit or certificate.

## What exists

- a typed schema `1.0` candidate evidence-envelope model;
- exact required-versus-observed source accounting for one `REQUIRED` source;
- a query fingerprint binding aggregate coverage, source observations, finality horizon, and exact profile reference;
- an application-supplied materialized registry snapshot and separate trust selection;
- exact selected-profile trust, validity, revocation, applicability, coverage, retention, blind-interval, freshness, and derived-finality enforcement;
- a deterministic negative-claim gate that never reads ambient time;
- an unsigned deterministic certificate builder and separate replay verifier;
- source, installed-command, benchmark, and laboratory scripts;
- a separately versioned and digest-bound EmptyBench corpus and declarative
  oracle containing 12 matched control/fault families and 24 cases;
- requirements, architecture, ADRs, validation, claims, operating, traceability, review, and backlog documents; and
- explicit approval, claim, and evidence-state boundaries.

## Trust sequence that must be preserved

The producer does not control the entire governance bundle:

1. The producer request carries an exact `(registry_id, profile_id, profile_version, profile_digest)` reference as part of the query fingerprint.
2. The relying application supplies the registry snapshot and trust selection outside that request.
3. The trust selection pins the exact snapshot identity/version/digest and the exact application-selected profile reference. Merely trusting a snapshot containing both weak and strong profiles is insufficient.
4. Snapshot identity, digest, issuer, as-of time, and expiry must pass before any record content is consulted.
5. The exact profile record and digest must resolve, and its issuer, approval authority, effective time, expiry, and revocation state must pass before profile semantics are used.
6. Request and runtime observations must match the selected profile's source, adapter, authorization, population, query, detection, coverage, retention, blind-interval, and freshness constraints.
7. The evaluator derives the finality horizon from the selected profile and requires the source-reported index to reach it.

Do not weaken these early-return boundaries to produce more diagnostics. Content that has not crossed its trust boundary must not influence applicability, freshness, or finality calculations.

This staged design is deterministic local configuration binding, not cryptographic trust. Anyone able to replace and rehash both registry and trust files can select another profile. Deployment wrappers must fix the configuration paths and place both files outside producer write authority. Signed trust selection, authenticated issuers/adapters, and a monotonic registry head remain later work.

## Certificate semantics that must be preserved

The certificate is built from the request and trusted context; callers cannot inject a precomputed decision. It binds the exact request, trusted context, resolved references, policy, evaluator, evaluation-input contract, origin classification, implementation assertion, evaluation time, issue time, complete decision, qualification, and limitations.

Verification keeps these dimensions separate:

- structural support;
- outer certificate-digest integrity;
- embedded digest and repeated-binding integrity;
- deterministic historical replay;
- separately supplied expected-context comparison;
- separately retained expected-certificate-digest comparison; and
- current local-use eligibility at an explicit relying-party time.

`effective_valid_until_exclusive` is the earliest applicable boundary among the snapshot's next update, the envelope validity boundary used conservatively as exclusive, policy observation/index age deadlines, resolved-profile expiry or revocation, and resolved-profile observation/index age deadlines. Current local use requires `issued_at <= relying_party_at < effective_valid_until_exclusive`, a replayed permit, intact bindings, and an expected-context match.

Neither the explicit relying-party time nor `issued_at` is trusted time. The certificate is unsigned. A passing verification report does not authenticate an issuer, establish independent custody, prove source truth or ingestion completeness, prevent replay, authorize an action, or establish non-repudiation.

## First operating instruction

Do not begin by adding features. Inspect the worktree, read `PROJECT_STATUS.md` and `TASKS.md`, then run the existing checks against the exact state you intend to accept:

```bash
./scripts/setup.sh
source .venv/bin/activate
env -u PYTHONPATH ./scripts/check.sh
env -u PYTHONPATH ./scripts/test.sh
PYTHONPATH=src /opt/homebrew/bin/python3.11 -m unittest discover -s tests -q
env -u PYTHONPATH .venv/bin/evidence-state demo
```

Then issue and independently compare the checked-in synthetic certificate:

```bash
env -u PYTHONPATH .venv/bin/evidence-state evaluate \
  --input examples/covered_request.json \
  --registry examples/profile_registry.json \
  --trust examples/profile_trust.json \
  --issued-at 2026-08-21T12:06:00Z \
  --origin SYNTHETIC \
  --pretty

env -u PYTHONPATH .venv/bin/evidence-state verify-certificate \
  --input examples/covered_certificate.json \
  --registry examples/profile_registry.json \
  --trust examples/profile_trust.json \
  --expected-digest sha256:5683e522aa22f08145658d49452a4c044d7cf562a6a3987da364b3322d4aab17 \
  --relying-party-at 2026-08-21T12:30:00Z \
  --pretty
```

If setup, checks, tests, demonstrations, installed-command parity, generated certificate equality, or verification fails, repair or accurately record the failure before taking new backlog work. Do not bind a moving or partially tested tree.

## Final `0.6.0` acceptance sequence

1. Resolve intended code and documentation changes and choose one stable revision.
2. Confirm the worktree/revision state that will appear in the implementation assertion.
3. Run setup and verify project, imported module, and installed distribution versions agree at `0.6.0`.
4. Run static, local-link, source-versus-installed file, deterministic-demo, source-suite, installed-suite, and supported-runtime checks.
5. Run the seed, operator, and custom paired cases; retain exact counts and byte-comparison results.
6. Regenerate the covered certificate and compare it byte-for-byte with the checked-in vector and expected digest above.
7. Run a final in-project read-only adversarial review of the stable revision,
   including exact profile selection, config rehash boundaries, trust
   short-circuiting, versions, freshness, retention, blind intervals, derived
   finality, certificate mutation, and relying-party-time boundaries.
8. Update the status, traceability, review, and custody record with the exact revision, commands, runtimes, results, and residual risks.

Only then may the project record a locally accepted `0.6.0` candidate. The repository is publicly available under Apache-2.0, but that state still does not freeze schema `1.0` or EmptyBench, authorize a versioned/package release, or approve production use.

## Continuous work loop

An active Codex heartbeat named **Advance Evidence-State I/O** is attached to the originating task and scheduled daily at 9:00 AM in the task's local timezone. Its automation identifier is `advance-evidence-state-i-o`. The heartbeat may maintain this project's public issue, roadmap, wiki, and Pages state within the approved repository scope; it does not create authority to publish releases, deploy software, spend materially, use sensitive data, or contact people outside repository collaboration.

For each continuation cycle:

1. **Observe** — inspect status, tasks, recent changes, test evidence, and unresolved risks.
2. **Select** — choose one bounded, unblocked acceptance, falsification, or research item.
3. **State the claim** — record what the change could establish and what it cannot.
4. **Implement** — make the smallest coherent change, including fault behavior.
5. **Verify** — run focused checks followed by the required full checks.
6. **Attack** — try to produce an unsupported `ABSENT_WITHIN_SCOPE`, bypass trust selection, misuse an unsigned certificate, or manufacture an unverifiable record.
7. **Update custody** — update status, tasks, decisions, risks, and reproducibility evidence in the same stable change.
8. **Stop or continue** — stop at an approval boundary; otherwise take the next highest-value item.

## Delivery states

- **Specified:** requirement and acceptance criteria exist.
- **Implemented:** code exists and was locally inspected.
- **Tested:** named automated tests passed in a recorded environment.
- **Accepted locally:** one stable, hash-bound state passed its declared local
  acceptance matrix and a separate in-project read-only review.
- **Benchmarked:** a frozen corpus and separately governed oracle produced reproducible measurements.
- **Externally reproduced:** an independent party reran the frozen campaign.
- **Operationally evaluated:** authorized real workflows were tested with bounded claims.
- **Production ready:** a separate security, reliability, legal, operational, and deployment decision was made.

No state implies the next one.

## Priority order

1. Complete and bind the active `0.6.0` local acceptance and custody evidence without changing its contract set.
2. Preregister and freeze the first implementation-owned baseline campaign,
   including baseline configurations and exclusions; do not call the current
   seed an independently governed benchmark.
3. Establish baseline model/tool behavior on that frozen campaign and apply the go/no-go thresholds without reinterpretation.
4. If the evidence supports continuation, add one real read-only adapter and empirically evaluate its profile under owner-approved authority and data boundaries.
5. Run approved discovery and shadow evaluation, then seek external reproduction.
6. Specify signing, authenticated adapter evidence, monotonic registry heads, trusted time, replay controls, and multi-source composition only through separate versioned decisions.

## Approval boundaries

Continue autonomously through local, reversible, non-sensitive development and testing. Stop and obtain explicit owner approval before:

- creating a version tag, GitHub release, or package-registry publication;
- changing the Apache-2.0 license or project governance;
- creating unrelated external accounts, repositories, pull requests, or messages outside the approved Evidence-State I/O public-maintenance scope;
- deploying into a production or third-party environment;
- ingesting non-public, personal, regulated, proprietary, classified, or export-controlled data;
- scanning or testing systems that were not explicitly placed in scope;
- incurring material cloud or API cost;
- changing acceptance thresholds or claim language to make results appear stronger; or
- representing synthetic, replayed, local, or green-test evidence as customer, operational, independent, or production validation.

## Definition of a useful increment

A useful increment must close an acceptance criterion, add a matched fault/control, reduce a reproduced false-absence path, strengthen reproducibility or custody, test a kill condition, or produce authorized evidence. Refactoring, dashboards, branding, and broad integrations do not take priority while final acceptance or benchmark falsification work remains open.

## Decision authority

The project owner retains authority over release, licensing, commercial positioning, real-data use, deployment, partnerships, and external claims. Agents may implement and test bounded local changes, but may not infer those decisions from passing tests, digests, certificates, or local review.
