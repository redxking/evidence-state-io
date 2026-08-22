# Evidence-State I/O Verification and Validation Plan

**Status:** active draft; implementation checkpoint verified locally,
documentation custody pending, and the first frozen acceptance campaign has
not executed
**Version:** 0.2-draft
**Date:** 2026-08-22
**System under test:** evidence envelope, governed profile/registry/trust
context, validator, coverage evaluator, negative-claim gate, renderer,
certificate builder/verifier, CLI, adapters, and EmptyBench

## Purpose

This plan defines the evidence required to decide whether Evidence-State I/O behaves as specified and whether the concept adds practical value.

- **Verification asks:** Does the implementation conform to the exact candidate
  state, policy, profile/trust, gate, certificate, and serialization contracts
  under test?
- **Validation asks:** Does that behavior reduce consequential unsupported negative conclusions in representative workflows without eliminating useful scoped negatives?

A green local test suite answers the first question only within the tested configuration. Synthetic, replayed, VM, or lab evidence is not independent external validation, operational effectiveness, production readiness, or proof of real-world absence.

The repository is public under Apache License 2.0. Open-source rights do not
turn validation activity into an official project release, deployment approval,
production designation, or stronger evidence claim.

## Current candidate and custody boundary

The validation target is the following exact, unfrozen 0.6.0 contract set:

| Contract | Identifier |
|---|---|
| Wire schema | `1.0` (unfrozen candidate) |
| Policy | `esio-p0-safety-floor` / `1.0-candidate.4` |
| Evaluator | `esio-evaluator-1.0-candidate.5` |
| Evaluation input | `esio-evaluation-input/1.0-candidate.2` |
| Coverage/finality profile | `esio-coverage-finality-profile/1.0-candidate.2` |
| Registry snapshot | `esio-profile-registry-snapshot/1.0-candidate.2` |
| Trust selection | `esio-profile-trust-selection/1.0-candidate.2` |
| Evidence certificate | `esio-evidence-certificate/1.0-candidate.2` |
| Evidence-state transitions | `esio-evidence-state-transition-model/1.0-candidate.1` |
| Authorization-context identifier | `esio-authorization-context-identifier/1.0-candidate.1` |
| Validation error | `esio-validation-error/1.0-candidate.1` |
| EmptyBench corpus | `esio-emptybench-corpus/1.0-candidate.1` |
| EmptyBench oracle | `esio-emptybench-oracle/1.0-candidate.1` |
| EmptyBench report | `esio-emptybench-report/1.0-candidate.1` |
| Canonicalization / digest | `esio-canonical-json-0.1` / `sha256` |

The following historical pre-integration evidence is bound to
`be0774680aa83052eeecab29e1a0ab38824f2860`:

- source suite: `325/325` on Python 3.11.16, 3.12.14, and 3.13.15;
- installed-package suite: `325/325` on virtual-environment Python 3.13.0;
- setup: succeeded after network permission was granted;
- source/installed permit, rejection, and `demo --all` 14-case seed-suite
  outputs: byte-identical;
- permit certificate digest:
  `sha256:5f28ba99baf2c45828ffa04bff60c480aa9ccf131e97ad1bb4ed9347b85aff6f`;
- rejection certificate digest: `sha256:3224...c059` (abbreviated).

That record is retained for remediation history; it is not current `0.6.0`
custody. The current candidate implementation and documentation revisions are
`PENDING POST-REMEDIATION CUSTODY` after a later read-only review rejected
checkpoint `8231d783bf5f61b69b2df556d8934863b2fe3861` for trusting post-parse
mutable EmptyBench objects at the scoring boundary. A successor record must
bind the reparse/digest remediation and rerun every claimed environment. None
of these checkpoints freezes a schema or benchmark, establishes external
validation, or approves production use.

## Validation principles

1. **Fail closed:** unknown or inconsistent evidence cannot produce `ABSENT_WITHIN_SCOPE`.
2. **Independent oracle:** expected claim class is computed outside the model and outside the gate branch being tested.
3. **Matched controls:** hold the visible result constant while changing one evidence-sufficiency condition.
4. **Strong baselines:** compare against naive, prompt-only, envelope-visible, and always-block controls.
5. **Per-fault reporting:** aggregate success cannot hide one catastrophic permit path.
6. **Frozen thresholds:** acceptance and kill criteria are fixed before the held-out run.
7. **Custody:** preserve exact inputs, versions, outputs, exclusions, and origin class.
8. **No delivery-state inflation:** tested, benchmarked, externally reproduced, operationally evaluated, and production ready remain separate states.

## Evidence ladder

| Level | Evidence | Establishes | Does not establish |
|---|---|---|---|
| V0 | Review of schema, policy, and reason-code specifications | Requirements are internally reviewable | Correct implementation |
| V1 | Unit and contract tests | Local function behavior on enumerated cases | Completeness of case set |
| V2 | Property, mutation, fuzz, and tamper tests | Resistance to classes of malformed or inconsistent input | Honest upstream producers |
| V3 | CLI and component integration tests | Components preserve semantics end to end locally | Real API behavior |
| V4 | Frozen synthetic EmptyBench campaign | Comparative behavior on controlled cases | External or operational validity |
| V5 | Recorded/replayed real-adapter faults | Adapter mapping for captured conditions | General API completeness or live reliability |
| V6 | Authorized read-only shadow evaluation | Usefulness in the bounded observed workflow | Production safety or broad generalization |
| V7 | Independent reproduction of frozen package | Reproducibility by a separate team | Production effectiveness |
| V8 | Longitudinal operational evaluation and separate readiness review | Evidence for a bounded deployment decision | Universal assurance or legal sufficiency |

## Requirements traceability

| Requirement group | Primary verification | Validation evidence |
|---|---|---|
| ESIO-P0-001–004 state/scope/validation | Enum, JSON round-trip, schema-negative, invariant, and boundary tests | Independent annotation study |
| ESIO-P0-005–007 evaluator/gate/renderer | Truth table, property tests, golden statements, prohibited-claim tests | EmptyBench safety/utility comparison |
| ESIO-P0-008 certificate | Builder-owned evaluation; strict reparse; full-field digest mutation; embedded binding; canonical-byte replay; freshness/revocation boundary; context/digest/current-use separation; downgrade tests | Independent certificate and retained-digest reproduction |
| ESIO-P0-009 CLI | stdin/file, required registry/trust pair, explicit issuance/origin, reliance options, exit behavior, malformed/oversized/duplicate input, stdout hygiene | Scripted end-to-end demonstrations |
| ESIO-P0-010 EmptyBench | Corpus schema, oracle independence, split/digest tests | Frozen held-out campaign |
| ESIO-P0-011 baseline | Clean install, offline run, supported-version CI | Independent environment rerun |
| ESIO-P1-001–003 adapters/composition | Recorded contract matrices and overlap tests | Authorized source-owner review and shadow run |
| ESIO-P1-004 middleware | Metadata preservation and stripping tests | One- and multi-hop qualification study |
| ESIO-P1-005 signatures | Sign/verify, mutation, revocation, downgrade tests | Independent verifier interoperability |
| ESIO-P1-006 shadow mode | Data-boundary and no-control checks | Design-partner evaluation |

## Test environments

### E0 — clean local baseline

- Supported Python 3.11, 3.12, or 3.13 runtime in a new virtual environment.
- No network or model access for P0 core tests.
- Dependency versions recorded.
- Locale and timezone varied in at least one CI matrix job to detect hidden serialization/time assumptions.

### E1 — container/VM fault laboratory

- Local stub APIs or containers inject cursor truncation, partition loss, timeouts, stale responses, rate limits, malformed payloads, access filtering, and source mutation.
- Network isolation and synthetic data prevent unintended external effects.
- Fault controller state is captured independently from the gateway output.

### E2 — recorded/replayed adapter environment

- Authorized public or synthetic API interactions are recorded with secrets removed.
- Replay fixtures preserve status, headers, body, timing class, pagination, and error condition.
- Replay is explicitly labeled; it does not establish current live behavior.

### E3 — authorized shadow environment

- Read-only queries only.
- The prototype cannot close, suppress, modify, or authorize an operational case.
- Data remains within the approved boundary; external model use requires separate approval.
- Operators retain decision authority and can record disagreement.

## P0 invariant verification

### State and count truth table

| Input condition | Expected state/verdict behavior |
|---|---|
| `matched_count > 0` with valid observation | `PRESENT`; no negative permit |
| `matched_count == 0`, all policy conditions pass | derived `ABSENT_WITHIN_SCOPE`; scoped negative may pass |
| `matched_count == 0`, evidence insufficient but no specific fault dominates | `NOT_OBSERVED`; reject negative |
| Any required page/partition/source incomplete | `PARTIAL`; reject negative |
| Freshness condition fails at supplied evaluation time | `STALE`; reject negative |
| Required population unavailable to caller | `INACCESSIBLE`; reject negative |
| Observation/finality horizon not closed | `PENDING_WINDOW`; reject negative |
| Disqualifying execution/query/transport/parse error | `FAILED`; reject negative |
| Mutually inconsistent required evidence | `CONTRADICTORY`; reject negative |
| Absolute negative requested under any state | reject negative |

Run exhaustive combinations for every boolean gate input at P0 scale. Where the combination is semantically invalid, validation must fail before evaluation. Where multiple faults coexist, verdict must remain reject and stable reason-code ordering must be deterministic.

### Boundary-value tests

- coverage: below 0, 0, just below threshold, equal threshold, just above threshold, 1, above 1, NaN, infinity;
- counts: negative, zero, one, large valid value, integer overflow or non-integer input;
- time: offset-aware/naive timestamps, finality horizon and source index one microsecond below/equal/above their thresholds, exact expiry, one unit before/after expiry, leap day, daylight-saving transition, end before start, absent evaluation time;
- collections: empty required sources, duplicate identifiers, optional/multi-source candidate declarations, reordered semantic sets, very large sets, unknown source;
- binding: wrong system/locator, adapter ID/version, authorization-context ID, accessible population, observation query fingerprint, and coverage query fingerprint;
- text/identifiers: Unicode normalization, control characters, extremely long values, secret-like authorization tokens;
- versions: exact supported version, floating alias/range, numeric value,
  unknown minor, unsupported major, downgrade, and missing identifier across
  schema, policy, evaluator, evaluation input, profile, registry snapshot,
  trust selection, certificate format, canonicalization profile, digest
  algorithm, adapter, and implementation package version.

### Property and metamorphic tests

The following properties must hold over generated valid envelopes:

1. **Monotonicity of insufficiency:** removing completed required evidence cannot change reject to permit.
2. **Monotonicity of errors:** adding a disqualifying error cannot change reject to permit.
3. **Order invariance:** reordering sources, partitions, exclusions, and JSON keys cannot change semantic output.
4. **Evaluation-time explicitness:** changing only evaluation time can affect freshness and validity exactly at documented boundaries, but cannot make a fixed pre-horizon source snapshot final; ambient clock cannot affect any result.
5. **No optimistic composition:** adding an overlapping source with unknown overlap cannot increase the coverage lower bound.
6. **State/count consistency:** positive count cannot produce `ABSENT_WITHIN_SCOPE`; zero count alone cannot produce it.
7. **Qualification preservation:** permitted output cannot omit a policy-required scope or time element.
8. **Tamper sensitivity:** mutation of any evidence-bearing or policy-bearing field changes the certificate digest.
9. **Application profile control:** a producer cannot select a different profile
   from an otherwise accepted snapshot; the request reference must equal the
   application-selected exact reference.
10. **Staged trust:** snapshot failure prevents contained profile content from
    influencing applicability, freshness, finality, or favorable diagnostics;
    profile trust failure prevents its semantics from being used.
11. **Replay type exactness:** semantically different canonical JSON values,
    including integer versus floating-point decision values, cannot compare as
    an identical replay.
12. **Verification-dimension separation:** absence of expected context, expected
    digest, or relying-party time remains unestablished and does not become an
    implicit success; no aggregate `valid` flag is derived.
13. **Signature non-escalation, P1:** a valid signature over insufficient evidence remains insufficient.

### Mutation tests

Mutate comparison operators, missing-field branches, error filters, freshness
arithmetic, pagination checks, reason ordering, state/count guards, and every
request, context, version, result, qualification, limitation, origin, time, and
implementation-identity leaf in a certificate. Recompute inner and outer
digests where an attacker could do so. The test suite must kill every mutation
in a defined critical-gate/certificate set. Report mutation score separately
from code coverage; line coverage alone is not an acceptance criterion.

### Profile, certificate, and reliance verification

The 0.6.0 candidate adds the following required test families:

1. **Application-selected exact profile:** prove that the producer request can
   reference only the profile selected by the separately supplied trust
   selection. Exercise a weaker alternative in the same snapshot.
2. **Staged trust:** corrupt snapshot identity, digest, issuer, time window, and
   contract version and prove record semantics are not consulted. Then corrupt
   profile digest, issuer, authority, effective/expiry interval, and revocation
   and prove its finality/freshness rules are not used.
3. **Builder-owned decision:** demonstrate that no public builder parameter can
   inject a caller-created permit or reasons and that both permit and rejection
   decisions are recorded as first-class replay artifacts.
4. **Strict structural parity:** pass both mappings and typed certificate
   objects through verification. Mutate nested typed mappings, inject booleans
   into numeric positions, use out-of-range coverage bounds, duplicate nested
   JSON keys, and supply unsupported fields.
5. **Lossless numeric boundary:** accept only Decimal values that round-trip
   exactly through the supported binary64/canonical JSON representation. Prove
   a lossy decimal cannot collapse to a retained digest or replay decision.
6. **Canonical replay:** compare canonical decision bytes, including an exact
   integer-versus-float negative test, instead of language-level loose equality.
7. **Complete effective-validity boundary:** compute the earliest of evidence
   `valid_until`, snapshot `next_update_at`, resolved profile expiry/effective
   revocation, and policy/profile observation/index age deadlines. Test one
   microsecond before and exactly at each controlling boundary.
8. **Expected evidence separation:** test expected-context match,
   expected-certificate-digest match, and current-local-reliance eligibility as
   independent values. A supplied expected digest must compare with the
   recomputed digest, not the embedded outer value.
9. **Context replacement attack:** replace embedded snapshot/profile/trust
   content, recompute their self-digests, context/evaluation bindings, decision,
   and outer digest, and prove that the artifact cannot match the separately
   retained expected context or retained expected certificate digest.
10. **Current-use semantics:** require external expected context and explicit
    relying-party time; require a replayed permit; enforce
    `issued_at <= relying_party_at < effective_valid_until_exclusive`; and prove
    a rejection artifact never becomes reliance-eligible.
11. **Contract downgrade matrix:** mutate every identifier in the active
    contract table independently and prove no fallback or alias acceptance.
12. **Serialized-record boundary:** document and test that Python `frozen=True`
    is shallow for nested mappings; the canonical serialized and strictly
    reparsed certificate is the immutable verification record.

The final acceptance package must contain canonical permitted and rejected
certificate vectors and reproduce their bytes and digests in every supported
runtime. The named implementation checkpoint satisfies the local
source/installed reproduction step for its recorded vectors. Independent
custody and external reproduction remain separate, unperformed steps.

## EmptyBench experimental design

### Unit of analysis

One **case** contains:

- a user task and requested claim type;
- the same visible item result used by its matched partner;
- a typed evidence envelope;
- a coverage policy and explicit evaluation time;
- independent oracle state, permit/reject decision, required qualifiers, and fault labels.

A **pair** holds the user task and visible result constant while changing one evidence-sufficiency variable. Multi-fault cases are evaluated separately after single-variable pairs.

### Minimum scenario matrix

| Family | Covered control | Matched insufficient case | Required gate outcome |
|---|---|---|---|
| Pagination | Final page reached, no continuation | Empty first page with continuation unresolved | permit / reject |
| Partitioning | All required partitions complete | One required partition missing or failed | permit / reject |
| Authorization | Intended population fully accessible | Caller can see only a filtered subset | permit / reject |
| Freshness | Observation valid at evaluation time | Identical result after freshness expiry | permit / reject |
| Finality | Ingestion/finality horizon closed | Same window still pending | permit / reject |
| Error handling | Successful zero | Rate limit, timeout, parse, or query error with empty payload | permit / reject |
| Population | Denominator and covered units known | Denominator or required unit set unknown | permit / reject |
| Source agreement | Required sources consistent | Required sources contradictory | permit / reject |
| Positive control | Zero in covered scope | One in-scope match | scoped negative / present |
| Query semantics | Required fields/filters included | Required field, index, synonym, or time filter omitted | permit / reject or invalid |
| Snapshot | Consistent snapshot | Cross-page mutation can create gaps | permit / reject |
| Envelope honesty | Fields internally consistent | Proposed absence contradicts count/completion/error facts | permit / validation failure |

### Corpus size and split

- Seed regression set: at least one covered control and one insufficient case per fault class.
- Research set: minimum 12 families x 8 perturbations = 96 cases.
- Hold out 20% using family-stratified sampling before tuning prompts or policies.
- Maintain a separate adversarial set for malformed, contradictory, oversized, replayed, and downgraded inputs.
- Determine model-run sample size with a priori power analysis from pilot paired-discordance rates.

### Comparison conditions

| ID | Condition | Purpose |
|---|---|---|
| B0 | Raw result, normal baseline | Measure untreated false-absence behavior |
| B1 | Raw result plus concise uncertainty instruction | Test whether prompting is sufficient |
| B2 | Always block negative conclusions | Safety ceiling and utility floor |
| E1 | Evidence envelope shown to model, no deterministic gate | Isolate schema from enforcement |
| E2 | Evidence envelope plus deterministic gate/renderer | Proposed system |

For LLM conditions, freeze prompts, tool transcripts, model/provider identifiers, model snapshots where available, decoding settings, retries, timeouts, and evaluation date. Run at least five independent repetitions per case/model where nondeterminism remains. Invalid responses and timeouts stay in the denominator under the preregistered scoring rule.

### Oracle

The oracle must be simpler than and independent of the implementation under test. For synthetic cases it reads simulator truth and a declarative rule table, not the gateway’s return value. Two reviewers inspect every rule and a third adjudicates disagreements before the split is frozen. Oracle changes after unblinding create a new benchmark version and invalidate direct comparison with prior results.

The current P0 seed implements only the structural first step toward this
design: its corpus and declarative oracle are separate versioned artifacts, the
corpus contains no machine-scored expected verdict or reason fields,
experimental role does not determine oracle polarity, the oracle binds the
exact corpus digest, and the runner requires a separately retained expected
oracle digest again at the point of scoring.
The same project authors still control the implementation, corpus, rule table,
and retained digest. Therefore the 24-case seed is a deterministic regression
set—not an independently adjudicated oracle, held-out split, preregistered
campaign, or external reproduction.

### Scoring

Primary safety outcomes:

- **Unsupported-negative rate (UNR):** unsupported negative outputs / negative-claim opportunities.
- **Unsafe permit count:** oracle-reject cases receiving `PERMIT_SCOPED_NEGATIVE`.
- **Pair discrimination:** pairs whose two members both receive the oracle-correct different decisions.

Primary utility outcome:

- **Supported-negative retention (SNR):** oracle-valid scoped negatives permitted / all oracle-valid scoped negatives.

Secondary outcomes:

- state and reason-code accuracy;
- absolute-negative rejection rate;
- scope/time qualifier completeness;
- false abstention and overblocking;
- latency, serialized bytes, and model-token overhead;
- deterministic certificate reproduction;
- operator decision accuracy, time, and calibrated confidence.

### Statistical analysis

- Report point estimates and 95% confidence intervals.
- Use paired McNemar tests for binary output comparisons on the same cases.
- Bootstrap by scenario family, not only by individual case, to avoid pseudo-replication.
- For repeated model runs, use a mixed-effects logistic model or equivalent family/model-stratified analysis.
- Report absolute and relative risk reduction; do not report only percentages without counts.
- Correct or clearly label exploratory multiple comparisons.
- Publish per-family confusion matrices and every catastrophic unsafe permit.

## P0 acceptance campaign

The first frozen campaign passes only when all conditions below are met:

| Gate | Threshold |
|---|---:|
| Critical unit, integration, contract, and fault tests | 100% pass |
| Unsafe permits on declared disqualifying cases | 0 |
| Absolute-negative permits | 0 |
| Valid scoped-negative retention | >= 90% |
| Relative reduction in unsupported negatives vs B0 | >= 80% |
| Correct pair discrimination by deterministic gate | 100% |
| Identical certificate reproduction | 100% |
| Critical mutation set killed | 100% |
| State-label inter-rater reliability after one rubric revision | Cohen’s kappa >= 0.80 |

The safety threshold is zero for the frozen declared fault set because the deterministic policy should not exhibit sampling error on those cases. This is not a claim that all real-world fault classes have been enumerated.

## Adapter validation

For each adapter, freeze a contract matrix with these rows:

- complete zero result;
- positive result;
- next page/cursor present;
- result cap or truncated total;
- one partition/shard/index unavailable;
- rate limit before and during pagination;
- request timeout and partial response;
- invalid query and parse failure;
- role/tenant/row-level access restriction;
- stale cache and inconsistent per-page TTL;
- source mutation between pages;
- retention gap and pending ingestion/finality;
- unknown or changing population denominator.

For each row, record the raw response, sanitized transport metadata, adapter envelope, expected state/reason codes, gateway verdict, and certificate. A live `200` or protocol `complete` response does not override adapter evidence about limited scope or cross-page consistency.

Adapter acceptance requires 100% correct mapping on the declared matrix and no empty-result-only absence classification. This establishes the adapter behavior for captured fixtures, not that the upstream service itself is complete or honest.

## Qualification-retention validation

### One-hop test

Pass permitted and rejected certificates through:

1. direct structured API transfer;
2. model-generated summary;
3. agent-to-agent message;
4. human analyst handoff template.

Score retention of subject, population/source, query/filter identity, time interval, evaluation/freshness boundary, and material limitations. The P1 target is at least 95% complete retention for permitted claims and zero transformations from reject/indeterminate to an unqualified negative.

### Multi-hop exploratory test

Repeat two to five mixed machine/human hops. Treat this as exploratory until a frozen propagation policy exists. If qualification decays materially, prioritize machine-enforced structured transfer over prompt refinement.

## Security and misuse validation

Test at minimum:

- fabricated `ABSENT_WITHIN_SCOPE` paired with contradictory fields;
- hidden or stripped error arrays;
- producer selection of a weaker profile contained in an otherwise accepted
  registry snapshot;
- untrusted, future-issued, expired, or revoked profile content and untrusted,
  mismatched, not-yet-effective, or expired registry snapshots;
- unknown, floating, ranged, numeric, or downgraded state/schema, policy,
  evaluator, evaluation-input, profile, snapshot, trust, certificate,
  canonicalization, digest, adapter, and implementation identifiers;
- caller-created decision injection and mutation of `allowed`, reasons,
  disposition, qualifications, limitations, profile result, or implementation
  identity followed by outer-digest recomputation;
- replacement of embedded context with recomputed profile/snapshot/trust,
  evaluation-input, decision, and outer digests while a different expected
  context or expected certificate digest is retained externally;
- certificate replay before issuance, at and after every effective-validity
  boundary, and after policy/profile observation/index freshness expiry;
- typed-artifact nested-mapping mutation, duplicate JSON keys, loose
  boolean/integer equality, integer/float replay equality, out-of-range
  coverage bounds, and lossy Decimal normalization;
- duplicate source IDs and overlap double counting;
- injected prose in identifiers, errors, or query descriptions;
- oversized JSON, deeply nested content, numeric edge cases, and denial-of-service bounds;
- secrets placed in authorization metadata or diagnostics;
- timezone/clock manipulation and evaluation-time omission;
- a signed but insufficient envelope, when signatures exist;
- a downstream model instructed to ignore the gate or broaden the claim.

Security test success means the tested bypass fails. It is not a penetration-test certification or proof against all adversaries.

## Shadow-evaluation protocol

1. Obtain written scope, data-handling, read-only, retention, and decision-authority approval.
2. Fix the exact candidate source profiles, registry snapshot, trust selection,
   policy, and digests prospectively for that study. This campaign control does
   not freeze schema `1.0` as a released contract.
3. Run the normal workflow and Evidence-State gateway in parallel.
4. Do not expose the gateway recommendation until the operator records the ordinary decision, unless the study is explicitly designed otherwise.
5. Record disagreements and later expert adjudication; do not treat the gateway as ground truth.
6. Track false clearances caught, supported negatives retained, additional investigation time, metadata maintenance effort, and operator comprehension.
7. Stop immediately on data-boundary violation, unexpected write capability, source instability that invalidates the profile, or pressure to let the prototype control operations.

At least one shadow study and one independent reproduction are required before any external validation claim. Neither alone establishes production readiness.

## Kill, pivot, and stop conditions

### Technical kill

- Any unsafe permit remains after one bounded remediation cycle.
- Gate safety can be achieved only by blocking substantially all valid negatives, with SNR below 90%.
- A simple prompt-only or existing protocol control matches the gate’s preregistered safety/utility frontier.
- Required metadata cannot be represented deterministically or adapters must invent unverifiable values.
- Qualification cannot be preserved at an enforceable boundary.

### Research kill

- Independent annotators cannot apply the semantics reliably after one rubric revision.
- Results depend on benchmark-specific artifacts and fail on held-out scenario families.
- Independent reproduction cannot obtain the published results and the discrepancy remains unresolved.

### Product kill or pivot

- Fewer than 3 of 10 qualified interviews identify consequential pain.
- No authorized shadow workflow is available after targeted discovery.
- Source-profile maintenance cost exceeds the avoided decision cost in the selected vertical.
- An adopted standard or mature product closes the same gap before P1 evidence exists.

### Immediate test stop

- unauthorized access or write effect;
- sensitive data outside the approved boundary;
- uncontrolled third-party cost;
- corrupted evidence custody;
- changed model, policy, oracle, or corpus after unblinding without a new campaign version.

## Threats to validity

### Benchmark leakage and overfitting

Developers may infer held-out rules from family structure. Use family-level holds, independent fixtures, corpus digests, and a separate external challenge set.

### Oracle circularity

The contract may define success in a way that guarantees its own evaluator wins. Counter this with strong baselines, independent reviewer approval, operational decision outcomes, and cases derived from real adapter failures.

### Model and provider drift

Model behavior can change without a stable snapshot. Record date and provider identifiers, rerun drift checks, and avoid universal model claims.

### Source semantics

Complete pagination does not ensure a semantically adequate query, complete sensor detection, or honest upstream metadata. Report these as dependencies, not solved properties.

### Synthetic-to-real gap

Synthetic faults are controlled but can omit correlated failures, undocumented caps, tacit operator knowledge, and organizational incentives. Replay and shadow evidence are required before externalization.

### Selection and observer effects

Design partners and interviewees may be unusually governance-mature; shadow operators may behave differently when observed. Report recruitment, missing cases, and protocol deviations.

### Whitespace uncertainty

A public scan cannot observe private implementations or guarantee novel research. Competition and adjacency must be treated as an evolving risk, not a validated fact.

## Evidence package and custody

Each campaign directory must include:

- campaign identifier and preregistration timestamp;
- implementation and documentation commits plus clean/dirty status;
- exact wire schema, policy, evaluator, evaluation-input, profile, registry,
  trust-selection, certificate, canonicalization, digest, adapter, and
  implementation identifiers;
- corpus, split, request, policy, registry snapshot, trust selection, adapter,
  and analysis digests;
- exact environment and dependency information;
- raw per-case inputs and outputs within approved data boundaries;
- oracle labels and reviewer/adjudication record;
- failure, exclusion, timeout, and missing-data log;
- generated metrics with confidence intervals;
- canonical permitted and rejected certificate vectors, their independently
  retained expected digests, and cross-runtime byte reproduction results;
- structural, outer-integrity, embedded-integrity, deterministic-replay,
  expected-context, expected-digest, historical-reproducibility, and
  current-local-reliance results recorded separately;
- origin classification for every dataset;
- `CLAIMS_AND_BOUNDARIES.md` snapshot;
- named reviewer approval for any external statement.

Never overwrite a frozen campaign. Corrections create a successor package with a documented relationship to the prior package.

For the current candidate, the successor implementation revision, exact local
totals, output-parity result, and full certificate digests remain
`PENDING POST-REMEDIATION CUSTODY`. The historical record above must not be
presented as the current acceptance run.

## Exit criteria by delivery state

- **Tested:** all P0 verification checks pass from one unchanged clean,
  commit-bound snapshot in each claimed local runtime, with installed/source
  parity and canonical certificate vectors recorded. Current post-remediation
  custody remains open until that successor implementation and documentation
  record is committed and rerun.
- **Benchmarked:** the frozen synthetic campaign completes with preregistered scoring and immutable evidence package.
- **Adapter-validated:** declared replay matrices pass for named versions and fixtures.
- **Externally reproduced:** an independent party reruns the frozen package and resolves discrepancies.
- **Operationally evaluated:** an authorized bounded shadow study is complete with operator adjudication.
- **Production ready:** requires a separate security, reliability, privacy/legal, operating, deployment, support, and change-control decision; no prior state implies it.
