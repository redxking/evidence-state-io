# Adversarial Review Log

This log preserves material review outcomes, including superseded green test
runs. A passing local suite is evidence about the cases it executes; it is not
evidence that the fail-closed contract is complete.

## 2026-08-21 — Initial handoff rejected

**Review disposition:** changes required
**Evidence class:** local, synthetic, self-authored implementation with an
separate in-project read-only code and adversarial-input review
**Pre-review verification:** 79/79 tests and 2/2 operator demonstration cases
passed

The reviewer reproduced reachable paths that could emit
`PERMIT_SCOPED_NEGATIVE` without adequate evidence. The green suite was
therefore rejected as insufficient for the published contract.

### Material findings

1. Omitted evidence facts were normalized to benign false or empty values.
2. Caller-controlled inline policy could weaken the P0 safety floor.
3. Free-form subject text could inject an absolute claim into qualified output.
4. Query time bounds were optional and could extend beyond observation time.
5. EmptyBench accepted singleton or weakly paired custom corpora and mislabeled
   them as the seed benchmark.
6. Missing schema versions were silently defaulted.
7. Expected EmptyBench reasons were checked as a subset rather than exactly.
8. Unknown populations could receive full coverage without an explicit declared
   lower-bound attestation.
9. Duplicate JSON keys, silently ignored full-request CLI overrides, and deeply
   nested input created ambiguity or unstructured failure.

### Required remediation

- Make safety-relevant evidence facts and schema version explicitly required.
- Enforce a non-relaxable P0 policy floor in both parsed and programmatic paths.
- Bound and safely render claim subjects.
- Require coherent query, observation, and evaluation times.
- Strengthen benchmark pairing, provenance labels, and exact oracle comparison.
- Require explicit lower-bound attestation for unknown or estimated populations.
- Reject ambiguous JSON and conflicting CLI input; return structured failures.

The initial 79-test result is retained here for traceability and must not be
presented as the accepted baseline.

## 2026-08-21 — Delivery mismatch rejected and repaired

After the hardened source suite reached 114 passing tests, a direct invocation
of the repository `.venv` imported a pre-hardening `site-packages` copy. The
source-overlay wrappers were green while the installed operator command still
used the old renderer and retained the old unsafe behavior. This state was not
accepted.

The candidate package was reinstalled into the repository virtual environment.
With `PYTHONPATH` unset, the installed interpreter then imported the package
from `.venv/lib/python3.13/site-packages`, passed 114/114 tests, and reproduced
the hardened demo, covered request, partial request, and custom benchmark.

## 2026-08-21 — Second proposed baseline rejected

**Review disposition:** rejected after expanded numeric and parser-bound review
**Evidence class:** local, synthetic, self-authored; separate in-project read-only
review within the project team, not external reproduction

Verification before rejection:

- Source suite: 114/114 on Python 3.13.
- Installed suite with `PYTHONPATH` unset: 114/114 on Python 3.13.
- Python 3.11 unittest discovery: 114/114.
- Focused adversarial selection: 27/27.
- Operator demonstration: 2/2; complete seed: 10/10.
- Covered example: `PERMIT_SCOPED_NEGATIVE`.
- Partial example: `REJECT_NEGATIVE`.
- Custom example: 2/2 and labeled `EmptyBench-custom`.

The original exploit families—omitted facts, policy relaxation, subject
injection, missing or future time scope, unversioned input, unknown coverage,
ambiguous JSON, conflicting overrides, weak reason comparison, and singleton
benchmark bypass—were rerun and did not reproduce. The expanded review then
found additional defects across the numeric, temporal, parser, model, and
benchmark boundaries:

1. Coverage ratios were rounded to 12 decimal places. With
   `2,999,999,999,999` examined units out of `3,000,000,000,000`, the
   one-unit-short ratio rounded to `1.0`, satisfied the exact safety floor, and
   emitted `PERMIT_SCOPED_NEGATIVE` with a 100.000% rendering.
2. A 5,000-digit JSON integer crossed Python's integer-conversion limit and
   escaped the CLI's structured error boundary with a traceback.
3. High-precision declared coverage bounds could be rounded into a different
   semantic value, compare differently under ambient decimal contexts, or
   collide under the canonical digest.
4. Submicrosecond timestamps could be silently truncated; floating-point
   `total_seconds()` calculations lost exact boundary information; extreme
   offsets could overflow during UTC normalization; and permissive timestamp
   grammar accepted ambiguous offset forms including `-00:00`.
5. A direct-library daylight-saving fold case, oversized programmatic integer,
   half-specified page/partition pair, and caller-owned mutable list exposed
   inconsistent behavior between parsed and programmatic paths.
6. Invalid UTF-8 could escape the intended machine-readable failure boundary,
   and output metadata supplied to EmptyBench was not sufficiently bounded and
   sanitized.

The 114-test result is retained as remediation evidence for the first review,
but it is not an accepted project baseline. Hardening introduced exact rational
coverage evaluation, bounded and context-independent numeric handling, strict
timestamp normalization, exact microsecond age evaluation, immutable normalized
models, atomic ASCII-safe CLI output, and aligned parser/library invariants.

## 2026-08-21 — Later proposed baselines rejected

The broadly hardened source reached 168 passing tests. An explicit
bare-envelope command-line override, `--subject ''`, was treated as if the
option had not been supplied. The fallback subject was inserted and the request
could permit. This was a falsy-input repair defect, so the 168-test state was
rejected. The CLI now distinguishes absence from an explicitly supplied empty
value and lets validation reject the latter.

After that repair, the 169-test proposed state still allowed
`source.index_as_of` to postdate `observed_at`. That chronology could make an
earlier observation appear to have a later, favorable source index. The state
was rejected. Validation now requires `index_as_of <= observed_at` and tests the
before, equal, and after boundaries in both source and installed paths.

Mixed source/installed states encountered during this sequence were also not
accepted. Every material reproduction was converted into a regression before
the final replay.

## Accepted baseline

**Review disposition:** accepted as a local runtime baseline with explicit
product and evidence limitations
**Snapshot:** 171 tests; schema `0.1`; canonicalization profile `0.1`
**Evidence class:** local, synthetic, self-authored implementation; independent
read-only adversarial review within the project team

Final unchanged-snapshot results:

- Source suite on Python 3.13: 171/171.
- Installed suite with `PYTHONPATH` unset on Python 3.13: 171/171.
- Python 3.11 unittest discovery: 171/171.
- Source and installed package-file snapshots and deterministic demos matched.
- The 98/98 core CLI exploit replay set passed across source and installed
  execution paths.
- EmptyBench adversarial executions passed 30/30; seed demonstrations passed
  2/2 and 10/10; custom provenance remained `EmptyBench-custom`.
- Direct-library checks passed 38/38.
- Explicit source-index chronology probes passed 6/6: before/equal observation
  were accepted and post-observation input was rejected during validation.
- No unsupported permit or unstructured traceback was reproduced.

This is the first accepted local freeze of schema `0.1` and canonicalization
profile `0.1`. The 79-, 114-, 168-, and 169-test snapshots were development
proposals, not accepted contract versions. None was released, published,
benchmark-frozen, or used to issue a certificate. From this freeze forward,
incompatible changes require governed version evolution.

Acceptance is narrow. Required-versus-observed source accounting, an explicit
finality/completeness model, complete certificate and policy-version binding,
an independent oracle and frozen benchmark campaign, credential-like field
detection, broad fuzzing, real adapters, CI execution, external reproduction,
and operational validation remain open. `index_as_of` currently records source
currentness; it is not a completeness watermark, so `index_as_of` earlier than
the query interval end remains part of the explicit finality gap.

The separate in-project review is not an external security assessment,
independent evidence custody, or production-readiness determination. The local
commit makes the snapshot recoverable; it does not authenticate its claims.

## 2026-08-21 — Schema 1.0 source-accounting candidate review

**Review disposition:** initial proposal rejected; repaired increment accepted
as a local candidate checkpoint only
**Evidence class:** local, synthetic, self-authored implementation; independent
read-only adversarial review within the project team

### Rejected 215-test proposal

The first green schema `1.0` implementation separated declared source
requirements from runtime observations, but its enforcement was not sufficient
to support a bounded negative. Adversarial mutations reproduced unsafe permits
or admitted structurally ambiguous evidence when:

1. The observation named the required source ID but supplied a different
   system or locator.
2. Adapter identity/version was absent or mismatched.
3. The observation used an authorization context inconsistent with the query
   and declared requirement.
4. Detection assumptions were empty.
5. An optional-source failure could be hidden behind favorable aggregate
   coverage.
6. Aggregate coverage or source observations came from a different query but
   were not cryptographically bound to the normalized query scope.
7. `index_as_of` was absent or preceded the end of the requested interval.

The proposed 215-test state was rejected. It must not be described as a
baseline, schema freeze, or source-accounting completion point.

### Remediation

- The P0 candidate now permits exactly one declared source and requires its
  role to be `REQUIRED`; optional and multi-source input reject until coverage
  can be modeled per source and composed explicitly.
- Requirement/observation matching covers source ID, system, locator, adapter
  ID/version, authorization context, and accessible population. Detection
  assumptions are explicit, nonempty, unique, and canonical.
- Query scope has a canonical SHA-256 fingerprint. Both aggregate coverage and
  every source observation must carry the matching fingerprint.
- Missing sources, all non-observed statuses, mismatches, and observation
  errors produce source-attributed rejection reasons.
- Observed sources require `index_as_of`; it must be at or after the query end
  and no later than `observed_at`. This closes the reproduced chronology permit
  but remains only a necessary currentness test, not a finality proof.
- Active requests require exact policy ID/version, and decisions expose the
  evaluator version. Complete certificate binding remains open.
- Schema `0.1` is retained only as a hash-bound fixture and historical replay
  instruction pinned to `b6fac87`; active schema `1.0` parsing rejects legacy,
  relabeled, downgraded, numeric, and unknown versions without migration.
- Installation review found stale `0.1.0` distribution metadata beside the
  `0.2.0` package. The stale directory was moved recoverably to
  `/private/tmp/evidence-state-io-stale-0.1.0.dist-info`, the package was
  reinstalled, and `scripts/setup.sh` now fails unless project, module, and
  installed-distribution versions agree.
- Final candidate review found that self-consistent literal placeholders such
  as `unknown` could still occupy the subject, query, exclusion, source,
  adapter, authorization-context, and detection-assumption fields and reach a
  permit. Concrete-declaration validation now rejects those values. This is a
  narrow syntactic safety control, not proof that a plausible-looking
  declaration is semantically correct.
- A finality-limitation output edit briefly made the installed package stale
  relative to source. Parity review caught the drift before commit; the package
  was reinstalled and source/installed output was rechecked.

### Repaired-candidate verification

- Reviewed implementation checkpoint:
  `bdd7c1e15c45f8d9940fc76604b3dde1fa953faa`.
- Source suite on Python 3.13: 224/224.
- Installed suite with `PYTHONPATH` unset on Python 3.13: 224/224.
- Python 3.11 source-overlay unittest discovery: 224/224.
- Source and installed package-file snapshots matched.
- The Python 3.11 source and Python 3.13 installed built-in seed runs passed
  12/12 and were byte-identical.
- Operator demonstration passed 2/2; the custom example passed 2/2 with
  `EmptyBench-custom` provenance.
- Static checks, local-link checks, shell syntax, optional Compose validation,
  installed CLI evaluation, and package-version consistency checks passed.
- The reproduced source identity, adapter, authorization, assumption, optional
  source, query binding, placeholder-declaration, and index chronology paths
  are regression-tested.

Acceptance is deliberately narrow: this is a recoverable, locally tested
schema `1.0` **candidate source-accounting checkpoint**. It is not a schema or
benchmark freeze, a finality/completeness proof, a complete certificate, an
independent oracle, an authenticated adapter, external reproduction, an
operational evaluation, or a production-readiness determination. The gateway
still evaluates producer-supplied state and facts; it does not independently
establish their truth.

## 2026-08-21 — Explicit source-finality candidate review

**Review disposition:** initial semantic and compatibility proposals rejected;
repaired increment accepted as a local candidate checkpoint only
**Evidence class:** local synthetic implementation; separate in-project read-only
adversarial and contract review within the project team

### Rejected finality designs and candidate state

The first tempting design compared only `evaluated_at` with a finality delay.
It was rejected before acceptance because an unchanged pre-horizon empty
snapshot could become sufficient merely by waiting. The source snapshot itself
must advance through the horizon.

The first integrated implementation enforced that safe comparison and passed
243 source tests, but its canonical representation emitted an undeclared
horizon as `"finality_horizon": null`. That changed the query fingerprint of an
actual pre-finality schema `1.0` candidate object. The object therefore failed
at fingerprint validation before producing the intended
`FINALITY_HORIZON_UNDECLARED` diagnosis. Safety remained fail-closed, but the
documented parse-and-diagnose compatibility claim was false. That candidate
state was rejected.

### Accepted contract and remediation

- The source requirement owns the per-query declared horizon. The runtime
  observation independently reports `index_as_of`.
- A permit requires the inclusive chain `query.time_end <= finality_horizon <=
  index_as_of <= observed_at <= evaluated_at <= valid_until` plus every existing
  coverage, source, freshness, validity, and error condition.
- Missing and null horizons are syntactically accepted but semantically
  insufficient under non-relaxable policy `1.0-candidate.2`; both normalize by
  omitting the undeclared field and reject with
  `FINALITY_HORIZON_UNDECLARED`.
- A declared horizon is normalized to UTC and bound into the query fingerprint,
  coverage and observation bindings, normalized request, and input digest.
- A source index below both the query end and finality horizon retains both
  applicable reasons in deterministic order.
- A regression reconstructs the actual pre-finality `example-0.2` query
  fingerprint without rebinding. It parses under candidate.2 and rejects solely
  for undeclared finality.
- Package, policy, and evaluator advanced to `0.3.0`,
  `1.0-candidate.2`, and `esio-evaluator-1.0-candidate.2`. Schema `1.0` remains
  an unfrozen candidate; canonicalization profile `0.1` and the hash-bound
  schema `0.1` replay remain unchanged.
- EmptyBench gained a seventh pair. Its query, horizon, evaluation time, and
  visible zero remain fixed while the reported source index moves one
  microsecond below versus exactly to the horizon.

### Verification and in-project read-only review

- Reviewed implementation checkpoint:
  `7deaea1dd79eacd2c4f3ebbef87a314e5293f1f6`.
- Documentation/custody checkpoint:
  `bac04fabfa5dbcf6a7e639217ee345f9c8ceb645`.
- Python 3.13 source suite: 244/244.
- Python 3.13 installed-package suite with `PYTHONPATH` unset: 244/244.
- Python 3.11 source unittest discovery: 244/244.
- Python 3.11 source and Python 3.13 installed seed outputs passed 14/14 and
  were byte-identical.
- Operator demonstration passed 2/2; custom example passed 2/2 with
  `EmptyBench-custom` provenance.
- `scripts/check.sh`, package/source snapshot parity, local links, shell syntax,
  Compose validation, version equality, and no-ambient-clock scan passed.
- Final in-project adversarial review passed 164/164 focused Python 3.13
  checks and 37/37 Python 3.11 finality/benchmark checks. It directly probed
  missing/null/malformed horizons, horizon-before-query, pre-horizon and missing
  indexes, optimistic state, wait-only evaluation advancement, stale
  fingerprints, policy downgrade/relaxation, non-observed statuses, reason
  ordering, and the actual legacy candidate fingerprint without reproducing a
  permit.

### Bounded acceptance

This checkpoint establishes deterministic consistency with supplied finality
declarations. It does not establish who was authorized to declare the horizon,
that the lateness model is accurate, that the reported index is authentic, that
clocks are calibrated, or that exceptional backfill, correction, deletion,
retraction, reopening, or cross-page inconsistency cannot occur. Governed
profiles, multi-source composition, the complete certificate, independent
oracle custody, external validation, operational evaluation, and production
readiness remain open.

## 2026-08-21 to 2026-08-22 — Governed-profile and certificate review (historical)

**Review disposition:** checkpoints `f7d8bca` and `e8c3bea` rejected; 0.6.0
remediation accepted as a local implementation checkpoint

**Evidence class:** local, synthetic, self-authored implementation; separate
in-project read-only adversarial and contract review

**Implementation custody:**
`be0774680aa83052eeecab29e1a0ab38824f2860`

**Documentation custody at that historical checkpoint:** `PENDING`

**Permit certificate digest:**
`sha256:5f28ba99baf2c45828ffa04bff60c480aa9ccf131e97ad1bb4ed9347b85aff6f`

**Rejection certificate digest shown in abbreviated form:**
`sha256:3224...c059`

These reviews were acceptance gates, not release reviews. Neither rejected
checkpoint was schema-frozen, externally validated, operationally evaluated,
or production-approved.

### Rejected checkpoint `f7d8bca` — governed coverage profiles

Checkpoint `f7d8bca` introduced profile, registry, and trust contracts, but its
green tests did not close the application-selection and staged-trust boundary.
The review found that:

1. A producer could reference another profile contained in an otherwise
   accepted registry snapshot. Trusting a snapshot was therefore broader than
   the application's intended selection of the exact policy profile for the
   evaluation.
2. Snapshot trust failures did not form a complete stage boundary before
   record resolution. Untrusted snapshot/profile content could influence
   applicability, freshness, or finality diagnostics before trust was fully
   established.
3. Profile, snapshot, trust, and adapter version fields required an immutable
   exact-version rule. Floating aliases or ranges would make later replay
   dependent on ambient resolution.
4. Registry chronology needed to reject a profile issued after the snapshot's
   own `as_of` time.

These were contract and trust-order defects even where the resulting decision
remained fail-closed. The checkpoint was rejected because the declared
application-controlled profile semantics were not actually enforced.

### Profile/trust remediation in 0.6.0

- Trust selection now binds one
  `selected_profile_reference`—registry ID, profile ID, immutable version, and
  digest—and the producer request must carry that exact reference.
- Snapshot identity, digest, issuer, effective time, and next-update boundary
  are checked as the first trust stage. Any failure returns before contained
  profile semantics are used.
- Exact record/digest resolution precedes profile-semantic use. Profile issuer,
  approval authority, effective/expiry interval, and inclusive revocation are
  then checked before applicability, finality, retention, blind-interval, or
  freshness rules are applied.
- Floating/ranged versions reject, and a snapshot cannot contain a profile
  issued after the snapshot `as_of` time.
- At this historical checkpoint, profile, registry-snapshot, and trust-selection
  contracts advanced to `1.0-candidate.2`; policy and evaluator were
  `1.0-candidate.4`; and evaluation input advanced to `1.0-candidate.2`.
  The evaluator later advanced separately to `esio-evaluator-1.0-candidate.5`.
  Wire schema `1.0` remains unfrozen.

Focused regressions cover an alternate weaker profile in the same snapshot,
untrusted snapshot content attempting to drive finality diagnostics, untrusted
profile content attempting to drive finality diagnostics, exact profile digest
selection, snapshot/profile time boundaries, revocation, and contract
downgrades.

### Rejected checkpoint `e8c3bea` — unsigned replay certificates

Checkpoint `e8c3bea` introduced the self-contained unsigned certificate and a
green local suite. Adversarial verification then reproduced four defects that
precluded acceptance:

1. **Incomplete current-use expiry.** The certificate's effective boundary
   included envelope/snapshot/profile validity but omitted policy and profile
   observation/index freshness deadlines. A historically reproducible permit
   could therefore remain marked eligible for current local reliance after its
   supporting observation or index was stale.
2. **Lossy numeric normalization.** A high-precision `Decimal` in a parsed
   decision could collapse through binary64 conversion to the original numeric
   value, allowing a semantically changed input to collide with canonical
   replay or digest expectations.
3. **Typed-artifact parser bypass.** A frozen certificate object still
   contained a mutable nested decision mapping. Mutating an integer-valued leaf
   to a boolean could exploit Python's loose `True == 1` equality when the typed
   object bypassed strict mapping reparsing.
4. **Incomplete decision-domain validation.** Finite coverage bounds outside
   `[0, 1]` were structurally accepted by the certificate decision parser. Replay
   later failed, but structural support was overstated.

The certificate checkpoint was rejected even though outer-digest mutation,
embedded-binding checks, and replay blocked several direct forgeries. A failed
attack family does not compensate for a reproduced bypass in a separate
verification dimension.

### Certificate remediation in 0.6.0

- `effective_valid_until_exclusive` is now the earliest applicable evidence
  `valid_until`, registry snapshot `next_update_at`, resolved profile expiry or
  effective revocation, and policy/profile observation/index age deadline.
- Every verification entry point converts a typed certificate to its public
  representation and reparses it through the same strict structural and
  numeric boundary used for JSON-derived mappings.
- Decimal inputs are accepted only when they round-trip exactly through the
  supported binary64/canonical JSON model; lossy values reject.
- Deterministic replay compares canonical JSON bytes, preserving JSON type
  distinctions such as integer `1` versus floating-point `1.0`.
- Decision coverage lower/upper bounds must be finite numbers within `[0, 1]`;
  booleans and out-of-range values are structurally unsupported.
- The certificate builder continues to own evaluation and exposes no
  caller-created decision parameter. Permit and rejection decisions are both
  self-contained replay records.
- The certificate contract advanced to
  `esio-evidence-certificate/1.0-candidate.2`. The exact active policy,
  evaluator, evaluation-input, profile, registry, trust, schema,
  canonicalization, and digest identifiers are embedded and reject downgrade
  or fallback.

The verifier continues to report structural support, outer integrity, embedded
binding integrity, deterministic replay, historical reproducibility, expected
context, expected digest, and current local reliance separately. It has no
aggregate `valid` flag. Expected context and expected certificate digest are
external custody inputs; absent values remain unestablished. Issuer
authentication and action authorization remain false.

The Python dataclasses are only shallowly frozen because nested mappings can be
mutable. The canonical serialized certificate, followed by strict reparse, is
the immutable verification record. This is a deliberate correction to any
earlier documentation that described the in-memory object as deeply immutable.

### Custody-bound local verification result

Implementation checkpoint `be0774680aa83052eeecab29e1a0ab38824f2860` passed:

- `325/325` source tests on Python 3.11.16, 3.12.14, and 3.13.15;
- `325/325` installed-package tests on virtual-environment Python 3.13.0;
- setup after network permission was granted; and
- byte-identical source/installed permit, rejection, and `demo --all` 14-case
  seed-suite outputs.

The permit certificate digest was
`sha256:5f28ba99baf2c45828ffa04bff60c480aa9ccf131e97ad1bb4ed9347b85aff6f`.
The rejection certificate digest was `sha256:3224...c059` (abbreviated here).
Focused reruns no longer reproduced the application-profile selection,
staged-trust, current-freshness, lossy-numeric, typed-artifact, loose numeric
replay, or out-of-range decision defects above. Additional attempted forgeries
also remained blocked:

- mutating `allowed`, reasons, result, qualifications, limitations, or
  implementation identity and recomputing only the outer digest failed replay
  or embedded binding;
- replacing the embedded context and recomputing profile/snapshot/trust,
  evaluation-input, decision, and outer digests could create a different
  internally reproducible record but could not match the separately retained
  expected context or expected certificate digest;
- supplied expected digests were compared with the recomputed certificate
  digest, not trusted from the embedded outer value;
- pre-issuance, expiry, revocation, snapshot-next-update, and freshness-boundary
  current-reliance probes failed at the closed-open boundary; and
- downgrade attempts across the active contract identifiers did not fall back
  to another interpretation.

This evidence accepts the named code revision as a local 0.6.0 implementation
checkpoint. Documentation custody remains pending until the later documentation
commit exists. This acceptance is not a release, schema or benchmark freeze,
external validation claim, operational authorization, or production-readiness
determination.

The residual assurance boundary is explicit: canonical self-digests and
deterministic replay detect inconsistency relative to retained expectations;
they do not authenticate declarative issuers, prove source truth, monitor a
newer registry head or revocation state, supply independent custody, or
authorize an action.

## 2026-08-22 — Public-handoff and EmptyBench typed-boundary review

**Review disposition:** public-handoff checkpoint
`8231d783bf5f61b69b2df556d8934863b2fe3861` rejected before push; remediation
implemented; successor custody pending

**Evidence class:** local, synthetic, self-authored implementation; separate
in-project read-only security and documentation/claims review

**External delivery state:** not pushed at the time of rejection

### Reproduced blocker

The committed checkpoint reparsed corpus and oracle files at the CLI boundary,
but its public typed `run_emptybench` API trusted already constructed Python
objects. Frozen dataclasses did not provide deep immutability or durable parse
custody. Two attacks were reproduced:

1. Replacing the parsed oracle schema with an unsupported predecessor and its
   digest with an all-zero value still produced `all_passed=true` and reported
   the attacker-controlled schema/digest.
2. Mutating the pagination fault request into the control request, assigning it
   to the permit rule, and replacing the oracle digest produced two passing
   permits with `pairs_discriminated=0` while `all_passed` remained true.

This was a P0 custody and scoring-boundary defect. File-level parsing tests did
not compensate for a bypass in the typed public API.

### Remediation

- `run_emptybench` now requires the separately retained expected oracle digest
  again at the point of scoring.
- Exact corpus, oracle, and trusted-context types are serialized and strictly
  reparsed before use; non-plain JSON containers reject.
- `parse_oracle` reparses its supplied corpus rather than trusting prior parse
  state.
- Experimental `control`/`fault` roles no longer determine oracle polarity.
  Machine-scored verdict and reason expectations remain in the separately
  stored oracle.
- `all_passed` now also requires every selected complete pair to discriminate.
- Regression tests preserve schema/digest downgrade, post-parse
  request/assignment mutation, corpus mutation, swapped-oracle retained-digest,
  and non-discriminating report failures.

### Read-only retest

- Original downgrade and post-parse substitution probes rejected before a
  report was produced.
- Rehashed swapped assignments rejected against the retained seed oracle
  digest.
- Focused trust/certificate/CLI/EmptyBench review passed `217/217`.
- Full Python 3.11 source review passed `371/371`.
- Certificate tampering, missing reliance prerequisites, and CLI error-redaction
  probes remained fail closed.

No surviving P0 bypass was found in the remediated moving tree. This is not
final custody: the successor implementation must be committed, installed, and
rerun across every supported runtime before local acceptance is recorded. The
seed remains implementation-owned synthetic evidence, not independent
adjudication, a frozen campaign, or external reproduction.

## MVP continuation and publication-gate review (2026-08-22)

Scope: the bounded continuation controller and the CI definition, reviewed
against implementation checkpoint `cf03ffd`. This review was triggered by
running the documented entry points rather than by reading them.

### Established before the review

`./scripts/setup.sh` followed by `./scripts/acceptance.sh` completed with exit
status `0` on a clean worktree at `cf03ffd`. The stale repository-local package
snapshot reported in the previous handoff was caused by an out-of-date `.venv`,
not by a source defect; reinstalling reproduced source/installed equality
without weakening `scripts/check.sh`.

### Defect 1 — reconciliation invalidated its own verification precondition

`python -m evidence_state_io.advance --repo . --reconcile --remote
--until-blocked --max-iterations 1` failed immediately with
`acceptance: the acceptance worktree must be clean`.

`ProjectController.reconcile` persisted the four tracked control records and
appended a `reconciled` progress event *before* `run_task` executed
`./scripts/acceptance.sh`. That gate requires a clean worktree as its custody
precondition, so the controller could never verify `MVP-TASK-001` in its own
documented reconcile mode. The failure is preserved in `project/progress.jsonl`
as a `verification_failed` event.

The comment already present in `run_task` states the intended invariant. The
defect was that `reconcile` did not honour it.

### Defect 2 — the CI repository-check step could not pass

`.github/workflows/ci.yml` ran `./scripts/check.sh` in the `quality` job, but
that script requires a repository-local `.venv` in order to compare the source
tree against the installed package. A hosted runner installs the project into
the job interpreter and never creates `.venv`. Removing `.venv` locally and
rerunning `./scripts/check.sh` reproduced the exact failure
(`check: repository-local environment not found`, exit `1`), so the step could
not have passed at any commit.

### Remediation

- `reconcile` accepts `persist`. When a bounded verification task may run in the
  same invocation, the reconciled ledgers and the `reconciled` event are
  buffered and flushed only after the verification command has observed the
  worktree, preserving chronological order in `project/progress.jsonl`.
- The `dirty` value bound into acceptance evidence is still sampled before the
  buffered write, so the recorded custody state describes the tree the command
  actually saw.
- `main` flushes any buffered reconciliation even when no bounded task runs.
- CI provisions the repository-local environment with `./scripts/setup.sh`
  before invoking `./scripts/check.sh`, and invokes it with `env -u PYTHONPATH`
  as the acceptance gate does. The source/installed comparison itself is
  unchanged.

Neither change alters a gateway decision path, a schema, a policy, an evaluator,
a canonicalization rule, or a claim boundary. `advance.py` remains outside the
deterministic core and outside its coverage boundary.

### Regressions added

- `test_reconcile_does_not_dirty_the_tree_before_a_clean_tree_verification`
  drives `main` end to end and asserts the criterion reaches `PASS` with
  `evidence.dirty == false` and the progress log ordered
  `reconciled` then `task_verified`.
- `test_deferred_reconciliation_is_persisted_when_no_task_runs` asserts the
  buffered state is still written when the next task needs external action.

### What this establishes and does not establish

This establishes that the continuation controller and the CI definition can
reach their declared outcomes in the tested environment. It does not establish
CI success at any commit, remote publication, Pages availability, Wiki
completeness, benchmark custody, independent adjudication, external
reproduction, or production readiness. Those remain separately observed states.

### Deployed-demonstration review (2026-08-22, `8ee09e1`)

The published Pages site was exercised in a real browser engine rather than
inspected as source. All nine deployed assets were fetched unauthenticated from
`https://redxking.github.io/evidence-state-io/` and their SHA-256 digests
matched, byte for byte, a site built from an independent clean clone of the
remote — so the artifacts under test were the deployed artifacts.

Observed across the seven published scenarios: `valid` produced
`PERMIT_SCOPED_NEGATIVE` with `ABSENT_WITHIN_SCOPE`; `incomplete`, `stale`,
`ambiguous`, and `conflicting` produced `REJECT_NEGATIVE` with `PARTIAL`,
`ABSENT_WITHIN_SCOPE`, `NOT_OBSERVED`, and `CONTRADICTORY` respectively;
`tampered` produced `REJECT_UNVERIFIED_INPUT` and `invalid` produced
`REJECT_INVALID_INPUT`, keeping input rejection distinct from a gate rejection.
No console error, page error, or failed request was recorded, and no internal
anchor was broken. The run control is reachable by keyboard alone and activates
with Enter.

One defect was found. At a 375px viewport the document scroll width was 495px,
so the page body scrolled horizontally on a phone. The cause was the decorative
`.hero::after` radial, 520px wide at `right: -120px`, which extended past the
hero without being clipped. `.hero` now sets `overflow: clip`; the re-measured
document scroll width equals the client width, and every scenario, the keyboard
path, and the clean console were re-confirmed afterwards.

This establishes deployed-artifact behaviour in one browser engine at two
viewports. It does not establish cross-browser behaviour, an accessibility
audit, assistive-technology testing, or that any displayed conclusion is true
of any real system.

### Continuation-controller staleness review (2026-08-22)

Editing a watched input after a successful verification exposed a third gap in
the same mechanism. `reconcile` marked the affected acceptance rows `STALE` but
left the task that produced them at `status: "verified"`. Because `next_task`
skips verified tasks, the controller would never re-run the gate that had
produced the invalidated evidence, and would instead select a dependent task
whose own dependency was no longer supported.

`reconcile` now reopens any verified task holding a newly stale pass criterion,
clears its `verified_at` and `verified_commit`, and reports the affected task
identifiers as `reopened_tasks` on the `reconciled` event. A regression drives
verify, mutate a watched input, reconcile, and asserts the row is `STALE`, the
task is `pending` without its verification stamps, and the task is selected
again.

This establishes that invalidated evidence is re-queued rather than silently
retained. It does not establish that any re-run will pass, nor does it change
what a passing gate means.

### Publication review (2026-08-22)

The wiki and the GitHub Project were both reported earlier in this cycle as
external blockers. Both were cleared and then verified against GitHub rather
than against configuration.

The wiki Git repository did not exist: `git ls-remote` on
`evidence-state-io.wiki.git` returned `Repository not found` over SSH and over
authenticated HTTPS, and no REST or GraphQL endpoint creates a wiki's first
page. After that page was created, the canonical `wiki/` directory was pushed
over it as a mirror. All 24 required pages and the 5 additional canonical pages
return HTTP 200 with rendered content to unauthenticated requests; `Home`
returns 301 to `/wiki`, which returns 200 with content and the custom sidebar;
29 internal wiki links resolve.

The maintainer's CLI token lacks the `project` scope, so `gh project` and the
GraphQL `projectItems` fields are unavailable. A public Project linked to this
repository was created instead and carries the six open MVP issues. It is
reachable unauthenticated and appears under **Repository projects** on the
repository's Projects tab. Its README states that item state is work state and
not validated evidence.

The tag ruleset blocks deletion, update, and non-fast-forward on `refs/tags/v*`
with no bypass actor, so an authorised release tag is immutable once created.
The branch ruleset grants the repository-admin role an `always` bypass; this is
deliberate, because the bounded continuation controller pushes reconciled
ledgers directly to the default branch. The required status checks therefore
gate contributors and pull requests, not the maintainer's own pushes, and that
limit is recorded in the MVP-ACC-024 evidence rather than described as stronger
than it is.

This establishes the state of the published surfaces at a known commit. It does
not establish that any published claim is correct, that anyone has read the
wiki, or that the roadmap reflects validated work.

### Externally verified tasks and staleness (2026-08-22)

Recording the externally observed publication evidence exposed the same
staleness gap one level out. `MVP-TASK-002` through `MVP-TASK-005` run in
`external` mode: the controller never sets their rows itself, so those rows are
recorded by hand and the task is marked `verified` by hand. Those tasks declare
`acceptance` but no separate `pass_criteria`, and the reopen rule introduced
earlier keyed only on `pass_criteria`. A documentation change therefore left
three externally recorded rows `STALE` behind a task still marked `verified`,
and `next_task` returned nothing at all.

`reconcile` now treats a task with no declared `pass_criteria` as owning every
acceptance row it links, so an externally verified task is reopened on the same
terms as a machine-verified one. A regression asserts that a verified task
without `pass_criteria` is reopened and loses its verification stamps when a row
it links goes `STALE`.

This closes the rule for both task modes. It does not change what any row
means, and it does not make an externally recorded row into machine-verified
evidence: those rows still depend on observations a human or agent made against
GitHub and recorded deliberately.

### Release-gate self-reference (2026-08-22)

Preparing the authorized `v0.6.0` tag exposed a fifth mechanism that could not
reach its declared outcome. The `Run release checks` step in
`.github/workflows/release.yml` refused to publish while any row in
`project/acceptance.json` was not `PASS`, including `MVP-ACC-025` itself.

`MVP-ACC-025` is the row the release establishes: it binds the tag, generated
notes, checksums, evidence manifest, SPDX SBOM, limitations, and accepted
commit, none of which exist until the release has been published. Requiring it
to be `PASS` beforehand made every release impossible, and satisfying it by
marking the row `PASS` in advance would have been a fabricated claim about
artifacts that did not exist.

The check now excludes `MVP-ACC-025` from the all-rows requirement and instead
refuses to publish if that row carries an adverse status — `FAIL`, `BLOCKED`,
or `STALE`. `PASS` and `UNVERIFIED` both proceed. The row is recorded as `PASS`
only from the published release, against the observed tag, assets, and digests.

Every other row is still required to be `PASS` at the tagged commit, and the
workflow still verifies that the tag is stable SemVer, that it matches the
package version, and that the tagged commit is an ancestor of the default
branch.

### ESIO-DEF-001 - the installed package read its oracle from the caller's directory (2026-08-22)

Found immediately after publishing `v0.6.0`, by installing the released wheel
into a fresh virtual environment and running the documented command from a
directory that is not a checkout.

```
$ evidence-state demo --all
{"error":{"code":"MODEL_INVALID", ...}}   rc=2
```

`_seed_artifact_directory` searched `Path(__file__).resolve().parents[2] /
"benchmarks"` and then `Path.cwd().resolve() / "benchmarks"`. For an installed
package the first candidate resolves inside the interpreter's library
directory and never exists, so the only working path was the current working
directory. The wheel shipped no benchmark artifacts at all: `unzip -l` matched
zero `emptybench-p0` entries, and `[tool.setuptools.package-data]` declared
only `py.typed`. The dependence was demonstrated directly: the installed CLI
exits 2 in an empty directory and exits 0 in a directory that contains a
`benchmarks/` folder holding the two JSON files.

Two things make this worse than a packaging slip. First, it contradicts the
project's own invariant that the deterministic core must not depend on host
paths, filesystem discovery, or the working directory. Second, this project's
whole argument is that an oracle must be separately stored, digest-bound, and
outside producer control; reading it from an undeclared `./benchmarks/` is the
wrong custody story even though the separately retained `SEED_ORACLE_DIGEST`
would still reject a swapped oracle.

The gates could not have caught it. `scripts/acceptance.sh`,
`.github/workflows/ci.yml`, and `.github/workflows/release.yml` each invoked
the wheel-environment CLI with the repository root as the working directory, so
every one of them exercised the source tree's `benchmarks/` while reporting
that it had verified the installed package in isolation. This is precisely the
failure the product exists to detect: a green result that does not establish
what it appears to.

### Remediation

- The corpus and oracle ship inside the package at
  `src/evidence_state_io/benchmarks/`, declared as package data, and are
  present in both the wheel and the source distribution.
- `_seed_artifact_directory` resolves from the imported module alone. The
  working-directory candidate is gone; a missing packaged artifact fails closed
  with an explicit message rather than falling back to a search.
- All three gates now run the installed CLI from a directory outside the
  checkout with a decoy `benchmarks/` planted beside the caller, and the
  acceptance gate additionally requires byte-identical output from inside and
  outside the repository.
- `tests/test_seed_artifact_resolution.py` asserts that resolution lands inside
  the package, that a decoy artifact directory is ignored, and that the report
  is identical whatever the working directory is.

### Verification

A freshly built wheel and source distribution each contain both artifacts. The
installed CLI, run from an isolated directory containing a decoy `benchmarks/`,
exits 0 and reports 24/24 cases, 12/12 matched pairs discriminated, zero unsafe
permits, and zero false rejections, byte-identical to the output produced from
the repository root.

### Boundaries

`v0.6.0` is immutable and still carries this defect; it is superseded by
`v0.6.1`. `MVP-ACC-009`, `MVP-ACC-013`, and `MVP-ACC-014` were set to `FAIL`
with this reproduction recorded before any fix was written. This remediation
establishes that the installed distribution now behaves identically wherever it
is run. It does not establish source truth, independent custody, or that any
other gate is stronger than it was.

### A green workflow is not an empty alert surface (2026-08-22)

`MVP-ACC-020` was recorded as `PASS` on the basis that every required check run
at the accepted commit reported conclusion `success`. That was true and
verifiable, and it was not the whole question. Querying
`repos/redxking/evidence-state-io/code-scanning/alerts` afterwards returned one
open alert at high severity.

The alert is CodeQL `js/bad-tag-filter` at `tests/test_dashboard.js`: the
pattern used to pull the dashboard's inline scripts out of the document was
case-sensitive, so a `<SCRIPT>` or `</SCRIPT>` region would not have matched.
The pattern is not a sanitiser and never filtered untrusted input; it feeds the
safe-render regression that executes those scripts under a hostile fixture. The
consequence is narrower than the severity label but is exactly the failure this
project is about: a script region could have dropped out of the regression's
coverage while the regression continued to report success. Demonstrated on a
three-tag sample, the old pattern extracted one region of three.

### Remediation

- Extraction is case-insensitive, and the closing tag tolerates trailing
  whitespace.
- A new assertion requires the number of extracted blocks to equal the number
  of opening `<script` tags found case-insensitively, so a region that is not
  covered fails the test instead of disappearing from it.
- The `MVP-ACC-020` evidence now separates two distinct observations: the
  conclusion of each required check run, and the count of open code-scanning
  and Dependabot alerts. Its recorded procedure queries both. The earlier
  record overstated what had been checked, and this is a correction rather than
  an addition.

This establishes that the regression covers every script region in the
document, and that the alert surface is now part of what the row asserts. It
does not establish that CodeQL has found every defect, nor that an empty alert
surface means the code is safe.

### The end-tag half of the same defect (2026-08-22)

Making script extraction case-insensitive closed alert #1 and immediately
opened alert #2, the same rule on the replacement pattern: *this regular
expression does not match script end tags like `</script\t\n bar>`*.

That is correct. An HTML end tag may carry content after the tag name, which
the parser ignores, so `</script foo="bar">` closes a script block. The
replacement matched only `</script\s*>`, so a block closed that way would have
been skipped exactly as the uppercase case was. Fixing half of a tag-matching
defect and declaring it closed would have repeated the original mistake in a
smaller form.

The end tag now uses the same shape as the opening tag,
`<\/script(?:\s[^>]*)?>`, and the behaviour is checked against five forms:
lowercase, uppercase, an end tag with attributes, an end tag with whitespace
and a newline before the bracket, and an opening tag with attributes. All five
extract exactly one block.

The general warning behind the rule still stands: matching HTML with regular
expressions is hard to do right. It is tolerable here only because the input is
a project-controlled file, the extraction feeds a regression rather than a
sanitiser, and an assertion now requires the extracted count to equal the
number of opening tags, so a missed region fails loudly rather than quietly.

### Dependency range discipline (2026-08-22)

Dependabot proposed widening `pytest>=8,<9` to `pytest>=8,<10`. Its CI passed,
and the change was still declined.

Every development dependency in this project occupies a single major band:
`build>=1.5,<2`, `coverage>=7.15,<8`, `mypy>=2.3,<3`, `ruff>=0.16,<0.17`. A
range spanning two majors would mean that a fresh `pip install .[dev]` need not
receive the version the acceptance record describes. With pytest `9.1.1`
current, `<10` would have resolved to pytest 9 while the recorded evidence had
been collected on pytest 8 — a quiet gap between what was tested and what a
reader would install.

`main` declares `pytest>=9,<10` instead, and the gate was re-run so the
recorded evidence describes the version a fresh install actually receives.
This establishes that the suite passes on pytest 9.1.1. It does not establish
anything about pytest 10, which is why the upper bound stays.

### Adversarial review of the insufficiency remedy (2026-08-22)

The obvious way to build this feature is also the dangerous one. A rejection
that printed "set the reported index to `2026-08-21T13:05:00Z` and coverage to
`0.995`" would be a working recipe for fabricating a permit, handed to the one
party the design deliberately keeps away from the governance bundle. The review
below is what the implementation was attacked with.

**Can a remedy be turned into a permit?** No path exists. `derive_remedy`
refuses an allowed decision outright, so a permit never carries a remedy that
could be read as conditional. A remedy is not an input to any evaluation: the
gate takes a request and a trusted context and nothing else, and the remedy
record is excluded from the decision payload and from the evaluation-input
digest. It is bound to the decision it explains by that decision's
`input_digest`, so a remedy cannot be moved onto a different evaluation and
presented as its explanation.

**Can a remedy be read as an instruction to edit a request?** A regression
scans every condition string for instruction wording — `set `, `change the`,
`edit `, `update the request`, `modify the`, `resubmit with` — and fails if any
appears. `PROFILE_POPULATION_MISMATCH` therefore reads "the query must target
the accessible population the governed profile declares" and never names the
value that would satisfy it.

**Can a remedy leak governed thresholds to the producer?** Not at the default
level. `CONSTRAINT_ONLY` emits `governed_value: null` for every item, and a
regression asserts that across the whole record. `WITH_GOVERNED_VALUES` is an
explicit choice by the relying application, is recorded in the record, and adds
a limitation naming exactly what the disclosure hands over. A paired regression
asserts that changing the level changes the values and never the set of
constraints reported, so the level cannot be used to hide or invent a failure.

**Can a reason acquire a remedy by accident?** Every `GateReason` is
classified, and a regression iterates the whole enum to prove it. Removing an
entry from the table makes `_classify` raise rather than fall back to a default,
so a gate reason added later cannot silently inherit a wrong class.

**Can an unsupportable rejection be presented as fixable?** The classes that
mean "no further evidence of the same kind helps" are computed, not assumed.
Matched pairs hold the request constant and move one field: a `PARTIAL`
observation is remediable, a `PRESENT` one is `UNSATISFIABLE`; zero matches is
remediable, nonzero is not; a scoped claim is remediable, an absolute one is
not. `satisfiable` is derived from the items rather than stored, so it cannot
disagree with them.

Determinism was checked by rendering each disclosure level one hundred times
and asserting a single distinct result, and the CLI path was checked the same
way across repeated invocations.

### What this establishes and does not establish

This establishes that a rejection can be explained without the explanation
becoming authority, and that the disclosure boundary is enforced rather than
merely documented. It does not make the gate safe against a self-consistent
malicious producer: that still requires authenticated adapter evidence, which
P0 does not have. It does not establish that any remedy's conditions can be
met, that meeting them would produce a permit, or that the underlying fact is
true. And at `WITH_GOVERNED_VALUES` the disclosure risk is not removed, only
made an explicit and recorded choice.

### Mutation testing the composition rules (2026-08-22)

The composition rules in ADR-0015 are each a choice between a conservative
branch and a plausible-looking one, and the plausible-looking branch is the
error the project exists to prevent. Passing tests are weak evidence for rules
like that: a test suite can agree with an implementation and still agree with
its naive alternative. So the implementation was mutated into each naive form
in turn, on disk, with the suite re-run against it and the file restored
afterwards.

| Mutation | Failures | First test to catch it |
|---|---|---|
| coverage by sum instead of max | 6 | `test_adding_a_source_never_increases_composed_coverage_above_the_best` |
| coverage by mean instead of max | 4 | `test_adding_a_source_never_increases_composed_coverage_above_the_best` |
| one shared earliest horizon for all sources | 1 | `test_each_source_must_reach_its_own_horizon_not_the_earliest` |
| one shared latest horizon for all sources | 1 | `test_each_source_must_reach_its_own_horizon_not_the_earliest` |
| binding horizon taken as earliest | 2 | `test_adding_a_source_never_moves_the_binding_horizon_earlier` |
| freshest observation instead of stalest | 2 | `test_adding_a_source_never_moves_the_binding_horizon_earlier` |
| latest validity instead of earliest | 2 | `test_adding_a_source_never_moves_the_binding_horizon_earlier` |
| strongest index reported instead of weakest | 1 | `test_the_weakest_index_is_reported_not_the_strongest` |
| required-source cap removed | 1 | `test_more_sources_than_the_cap_are_refused` |
| input order respected instead of canonicalised | 1 | `test_the_assessment_is_a_property_of_the_set_not_the_order` |
| majority vote instead of contradiction | 3 | `test_presence_against_absence_is_contradictory_not_a_vote` |

Eleven mutants, eleven caught, no survivors. The baseline and the restored file
both ran clean, and the restored file's SHA-256 matched the original byte for
byte.

Two of these are worth naming. The shared-horizon mutants are caught by a
fixture in which one source's index is past the earliest horizon in the set but
short of its own: a composition using a single shared horizon, in either
direction, would permit a claim while a lagging source could still receive a
late arrival for the queried interval. And the sum and mean mutants are caught
by the property that adding weaker corroborating sources never moves the
composed floor, which is the property that stops coverage being bought by
adding sources rather than by observing more.

### What this establishes and does not establish

This establishes that the composition rules are pinned by the tests rather
than merely consistent with them, and that each naive alternative is detected.
It does not establish that the rules are the right ones — mutation testing
measures whether a suite defends a decision, not whether the decision is
correct. It establishes nothing about envelopes: the composition is not yet
reachable from one, so no multi-source request can be evaluated, and no claim
about multi-source behaviour of the gate follows from it.

## 2026-08-22 — Composition wired into envelope schema 1.1

The entry above closed on the observation that the composition was not
reachable from an envelope. Semantics nothing can call are a promise, not a
capability, so the remaining wiring was done.

### What was added

`SourceObservation` gained an optional per-source assessment: `coverage`,
`state`, `matched_count`, `observed_at`, and `valid_until`. A composed envelope
must supply the first four for every required source. Per-source `state` and
`matched_count` are what make disagreement detectable at all; without them the
contradiction rule would have nothing to compare and would never fire.

A source's declared state must be compatible with its runtime status. Without
that table a producer could label a `FAILED`, `PENDING`, or `INACCESSIBLE`
source as `ABSENT_WITHIN_SCOPE`, and a composed envelope could reach a permit
from sources that returned nothing because they broke.

`ProfileTrustSelection` gained `additional_selected_profile_references` so the
relying application can select one governed profile per required source. The
singular field remains the schema `1.0` form and stays first.

Two conditions were added at the gate that the composer alone could not
express, because they compare a composed conclusion with what the envelope
itself declared: an envelope may not declare a coverage floor above the
composed floor, and it may not remain valid past the earliest boundary any
contributing source declared. Freshness now ages a composed claim from its
stalest contributing observation rather than from the envelope timestamp, so a
late-sealed envelope cannot hide a source that was read hours earlier.

### What this establishes and does not establish

A composed claim can now be permitted and rejected through the public gate,
with the composed assessment recorded in the decision. Fifteen envelope-level
tests exercise the permit, the maximum-not-sum rule, per-source horizons, the
stalest-observation rule, the earliest-validity rule, and a dissenting source
that three agreeing sources do not outvote.

It does not establish that the composition is correct for any real system.
Every source in these tests is synthetic and every profile is locally
authored. No adapter evidence is authenticated, so a self-consistent producer
that fabricates several agreeing sources is not detected by anything here.
Corroboration establishes agreement among the declared sources and never
independence between them: sources drawing on a common upstream record can
agree while all being wrong, and the decision's limitations now say so.
