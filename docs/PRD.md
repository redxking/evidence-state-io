# Evidence-State I/O Product Requirements Document

**Status:** implementation handoff, pre-alpha research prototype
**Version:** 0.2-draft
**Date:** 2026-08-21
**Decision owner:** project owner
**First vertical:** cyber investigation and threat hunting
**Reference implementation:** dependency-light Python 3.11-3.13
**Distribution/licensing:** public under Apache License 2.0; pre-alpha status is
not a production authorization or stable protocol release

## Executive decision

Build a narrow evidence-state contract and deterministic gateway that prevents an empty or incomplete tool result from being rendered as an unqualified negative factual claim. The initial product is not a truth oracle. It permits only a qualified `ABSENT_WITHIN_SCOPE` conclusion when the declared scope, access boundary, coverage, pagination or partition completion, freshness, finality, exclusions, and errors satisfy an explicit policy at a supplied evaluation time.

The product advances beyond prototype only if it materially reduces unsupported negative conclusions without degenerating into universal abstention. The first decision gate is a frozen paired benchmark plus discovery evidence, not a public launch.

## Problem statement

AI systems commonly receive a valid-looking empty result from search, retrieval, monitoring, or inventory tools. The empty payload does not disclose whether the query covered the relevant population, all pages and partitions completed, the caller could access the target records, the data was current, the observation window had finalized, or an upstream failure was suppressed. A downstream model can therefore convert “not observed in this execution” into “does not exist.”

Existing tool protocols provide structured data, protocol completion, errors, caching hints, and optional metadata, but those primitives do not by themselves establish the evidence conditions for a defensible scoped negative claim. The cost is highest where a false clearance can terminate investigation, suppress escalation, or misstate risk.

## Product thesis and boundary

Evidence-State I/O makes the epistemic state of a result explicit at the tool boundary. It consists of:

1. **Evidence envelope:** typed observation state and the declared conditions under which it was produced.
2. **Coverage evaluator:** deterministic calculation of whether the evidence satisfies a named policy.
3. **Negative-claim gate:** stable permit/reject verdict and reason codes for requested negative claims.
4. **Qualified renderer:** wording that preserves scope and time instead of emitting “nothing exists.”
5. **EmptyBench:** matched cases with identical visible observations but different evidence sufficiency.
6. **P0 local profile custody:** an application-controlled materialized registry snapshot, trust selection, and exact selected profile reference for population, retention, freshness, blind intervals, permissions, detection assumptions, and finality.
7. **P1 operational governance:** authenticated registry/source evidence, lifecycle and rollback controls, and privacy-preserving certificate handling.

The contract describes evidence sufficiency. It does not prove that a producer is honest, that a query is semantically correct, that a source detects every real-world event, or that an open-world population is complete. P0 issuer, approval-authority, source-owner, origin, implementation, and time labels are declarative rather than authenticated.

## Personas and jobs to be done

### Investigation lead or threat hunter

**JTBD:** When an agent reports that it found nothing, determine whether the result supports closing a bounded investigative question or only supports continued uncertainty.

- As an investigation lead, I want a negative conclusion to name the sources, population, filters, and time window searched so I can understand exactly what was cleared.
- As a threat hunter, I want missing, stale, unauthorized, contradictory, or still-finalizing sources to block clearance so an empty result does not prematurely end the hunt.
- As an incident reviewer, I want the gate inputs, policy version, reason codes, and output qualification preserved so I can reproduce the decision.

### Agent or platform engineer

**JTBD:** Integrate search and retrieval tools without writing one-off logic for every way an empty result can be misleading.

- As a platform engineer, I want a dependency-light schema and JSON codec so existing tools can emit evidence state without adopting a full governance platform.
- As an agent engineer, I want a deterministic gate that the model cannot silently override so prompt variation does not change evidence policy.
- As an adapter author, I want conformance fixtures for pagination, rate limits, access filtering, stale caches, and errors so I can prove the adapter fails closed.

### Source owner or data steward

**JTBD:** Declare what a source can and cannot support without implying universal completeness.

- As a source owner, I want to describe population, retention, freshness, authorization context, exclusions, and blind intervals so consumers do not overinterpret a successful query.
- As a data steward, I want invalid or internally inconsistent coverage claims rejected with actionable reason codes.

### Assurance architect or evaluator

**JTBD:** Measure whether an AI workflow preserves evidence qualification across tool, model, and human handoffs.

- As an assurance architect, I want a frozen, machine-readable certificate so a verdict can be traced to exact evidence and policy versions.
- As an evaluator, I want paired cases and an independent scoring oracle so I can compare the gateway with naive and conservative baselines.

## Goals

The thresholds below are proposed go/no-go criteria, not achieved results.

1. Reduce unsupported negative conclusions by **at least 80% relative** to a preregistered model/tool baseline on the frozen paired benchmark.
2. Produce **zero `ABSENT_WITHIN_SCOPE` verdicts** when any policy-required source is missing, inaccessible, stale beyond policy, contradictory, incompletely paginated or partitioned, failed, or before its finality horizon.
3. Retain **at least 90%** of valid scoped-negative conclusions on cases that satisfy every declared policy condition.
4. Reproduce verdict, stable reason-code set, qualified statement, and certificate digest **bit-for-bit** for identical canonical input, evaluator version, policy version, and evaluation time.
5. Obtain problem evidence: at least **3 of 10 qualified discovery interviews** must identify a costly false-absence or false-clearance pattern and provide a workflow suitable for an authorized shadow evaluation.

## Non-goals

- **Absolute proof of nonexistence.** Open-world absence is generally not provable; the product only supports a negative within an explicit bounded scope.
- **A general factuality or hallucination detector.** The gate evaluates declared evidence conditions for a narrow claim class; it does not judge arbitrary model prose.
- **Source truth or sensor performance certification.** A source can be completely queried yet fail to detect the underlying phenomenon.
- **Authorization, action governance, or policy replacement.** Evidence sufficiency does not authorize a consequential action, data access, or investigation closure.
- **A full SIEM, search engine, observability platform, or agent framework.** P0 is an interoperable contract, evaluator, CLI, and benchmark.
- **Cryptographic proof in P0.** Deterministic digests support reproducibility; producer identity and signed attestations are P1.
- **Production readiness or external validation.** Local and synthetic results establish only behavior in the tested environment.
- **Public protocol standardization in the first phase.** A standards proposal is premature until the schema survives real adapters and independent critique.

## Core semantics

### Initial evidence states

| State | Required interpretation |
|---|---|
| `PRESENT` | One or more in-scope matches were observed. It does not imply completeness. |
| `ABSENT_WITHIN_SCOPE` | Zero matches were observed and every condition required by the named coverage policy passed for the declared scope and evaluation time. |
| `NOT_OBSERVED` | No match was observed, but sufficient absence conditions were not established. |
| `PARTIAL` | Only a known subset of the required population, pages, partitions, fields, or time range was evaluated. |
| `STALE` | Evidence exceeded the applicable freshness condition at evaluation time. |
| `INACCESSIBLE` | Required evidence could not be accessed within the declared authorization or policy boundary. |
| `PENDING_WINDOW` | The applicable observation or finality horizon had not closed. |
| `FAILED` | The observation operation did not complete successfully or returned a disqualifying error. |
| `CONTRADICTORY` | Required evidence sources or claims are mutually inconsistent under the policy. |

`ABSENT_WITHIN_SCOPE` is a derived, policy-dependent state. Producers may propose it, but the evaluator must independently verify its invariants before the gate can permit a scoped-negative claim.

### Negative-claim rule

An **absolute negative** such as “no such event exists” is always rejected. A **scoped negative** may pass only when all of the following are true:

- the requested claim explicitly identifies a bounded subject, population, query, filters, and time interval;
- `matched_count == 0`;
- state is evaluable as `ABSENT_WITHIN_SCOPE` under the named policy;
- the authorization and accessible-population boundary are declared;
- coverage meets or exceeds the policy threshold and its derivation is available;
- required pages and partitions are complete, with no unresolved continuation token or snapshot ambiguity;
- no disqualifying timeout, rate-limit, query, transport, parsing, or source error remains;
- freshness and finality conditions pass at an explicitly supplied evaluation time;
- the producer's exact profile reference matches the relying application's separately supplied, producer-unwritable selected profile reference and resolves under that registry/trust context; and
- the output renderer preserves the scope and material limitations.

## Primary workflows

### Producer workflow

1. Execute an authorized read-only observation.
2. Capture raw result count, source and query identifiers, declared scope, authorization boundary, coverage facts, completion facts, time facts, exclusions, and errors.
3. Emit a versioned evidence envelope.
4. Validate the envelope locally; invalid or inconsistent envelopes cannot claim `ABSENT_WITHIN_SCOPE`.

### Consumer workflow

1. Fix an application-controlled registry snapshot, trust selection, and exact selected profile reference outside the producer boundary; the producer must not be able to write or replace them.
2. Supply the request, coverage policy, explicit evaluation/issuance times, evidence-origin label, and the separate registry/trust files to the gate and certificate builder.
3. Receive an unsigned deterministic replay certificate containing a `PERMIT_SCOPED_NEGATIVE` or `REJECT_NEGATIVE` disposition, stable reason codes, and a qualification-preserving statement.
4. Preserve it only in approved custody. The P0 artifact embeds the full request, registry/trust context, decision, and implementation metadata and is not data-minimized.
5. Treat rejection as evidence insufficiency, not evidence that the positive claim is true; treat a permit, digest match, or replay match as neither source truth nor action authorization.

## Requirements

### P0 — minimum falsifiable product

#### ESIO-P0-001: Versioned evidence-state model

The library shall expose immutable typed values for all initial evidence states and a schema version.

**Acceptance criteria**

- Every state in the table above round-trips through JSON without aliasing or case ambiguity.
- An unknown state or unsupported major schema version is rejected, not coerced to `NOT_OBSERVED` or `FAILED`.
- Unit tests assert the normative interpretation and allowed transitions for each state.

#### ESIO-P0-002: Declared scope and access boundary

An envelope shall identify the subject or query, population or resource universe, applicable filters, time interval, sources, authorization context identifier, accessible population, exclusions, and detection assumptions needed by the selected policy.

**Acceptance criteria**

- A scoped-negative evaluation with any policy-required scope field absent returns `REJECT_NEGATIVE` and a stable missing-field reason code.
- The schema distinguishes “not applicable,” “unknown,” zero, and an empty collection; these values are not silently collapsed.
- Secret credentials and raw tokens are rejected from fields intended for authorization-context identifiers.

**Current candidate note:** Schema `1.0` implements one required source with a
source ID, system, locator, adapter ID/version, stable non-secret authorization
context, accessible population, and nonempty detection assumptions. The
requirement and observation are matched exactly. Schema `1.1` admits up to four
required sources under a declared `CORROBORATION` mode, each with its own
governed profile and its own evidence; a source's declared state must be
compatible with its runtime status, so a failed or pending source cannot be
relabelled as an in-scope absence. Credential-like-content detection and richer
field/projection semantics remain open.

#### ESIO-P0-003: Coverage and completion facts

An envelope shall represent a coverage lower bound and derivation, required/observed sources, page and partition completion, continuation status, finality horizon, freshness interval, exclusions, and structured errors.

**Acceptance criteria**

- Coverage is constrained to `[0, 1]`; invalid numeric values, NaN, and infinity are rejected.
- Any unresolved continuation token, incomplete required partition, unknown required-source status, or disqualifying error prevents `ABSENT_WITHIN_SCOPE`.
- A claimed coverage lower bound cannot exceed a deterministic bound computed from declared required and completed units under the P0 coverage method.

**Current candidate note:** Aggregate coverage and every source observation
must match the canonical normalized-query fingerprint. Optional-role sources
remain rejected. Schema `1.1` represents coverage per source and composes
corroborating sources conservatively: the composed floor is the strongest
single-source bound, and an envelope may not declare a bound above it.
`PARTITION`, the only mode in which coverage would accumulate, stays rejected
because no governed profile can yet express the disjoint accessible
subpopulation it would require. The requirement carries an exact profile reference and an exact finality
horizon. The horizon must equal the query end plus the larger of the selected
profile's late-arrival and reopen bounds, is query-bound, and must be reached by
the reported source index. The local profile is application-selected but its
publisher, authority, assertions, and source behavior are not authenticated or
independently validated in P0.

#### ESIO-P0-004: Fail-closed envelope validation

The validator shall reject internally inconsistent or ambiguous envelopes before claim evaluation.

**Acceptance criteria**

- `PRESENT` with `matched_count == 0`, or a proposed `ABSENT_WITHIN_SCOPE` with `matched_count > 0`, is invalid.
- A freshness expiry before observation time, an interval with end before start, duplicate required-source identifiers, and contradictory completion flags are rejected.
- Validation returns stable machine-readable reason codes and never repairs evidence-bearing values silently.

#### ESIO-P0-005: Deterministic policy and coverage evaluator

The evaluator shall decide whether an envelope satisfies a named, versioned policy without model inference.

**Acceptance criteria**

- Identical canonical envelope, policy, evaluator version, and supplied evaluation time produce identical evaluation output across repeated runs.
- System wall-clock time is not consulted when an evaluation time is supplied; absence of required time input fails closed.
- Policy threshold boundary tests cover values immediately below, equal to, and immediately above the configured coverage and freshness limits.

#### ESIO-P0-006: Negative-claim gate

The gate shall reject every absolute negative and permit a scoped negative only when all normative rule conditions pass.

**Acceptance criteria**

- Every absolute-negative fixture returns `REJECT_NEGATIVE` regardless of envelope state.
- Every fault fixture—partial page, missing partition, stale result, inaccessible source, pending finality, failure, contradiction, or unresolved error—returns `REJECT_NEGATIVE`.
- A conforming covered-zero fixture returns `PERMIT_SCOPED_NEGATIVE` with no disqualifying reason code.
- Reordering input collections or JSON object keys does not change the verdict or stable reason-code set.

#### ESIO-P0-007: Qualification-preserving output

For a permitted scoped negative, the library shall render a statement that includes the bounded scope and temporal qualification and never emits an absolute “nothing exists” formulation.

**Acceptance criteria**

- Golden tests verify that output identifies the searched population or sources, query/filter identity, time window, and evaluation time or freshness boundary.
- For rejected claims, the output says the evidence is insufficient and names the material reasons; it does not assert the positive opposite.
- A prohibited-phrase test rejects configured universal formulations such as “no instances exist anywhere.”

#### ESIO-P0-007A: Governed coverage/finality profile selection

The evaluator shall resolve an exact request profile reference only under a separately supplied, application-controlled registry snapshot and trust selection that pin the relying application's exact selected profile reference.

**Acceptance criteria**

- The producer cannot embed, select, replace, or override the registry snapshot, trust selection, or application-selected profile reference used for evaluation.
- Request and application-selected references match exactly on registry, profile ID/version, and digest; zero matches, digest mismatch, untrusted issuer/authority, invalid time, or revocation reject without fallback.
- Floating aliases, ranges, branch names, automatic upgrade/downgrade, and nearest-version selection are rejected.
- Snapshot trust failures stop before record resolution; profile trust/resolution failures stop before applicability, coverage, or finality content is consulted and do not populate resolved references.
- Matching local identifiers and digests establish deterministic configuration binding only. They do not authenticate a publisher, authority, source owner, profile assertion, source index, or source observation.

#### ESIO-P0-008: Deterministic evidence certificate

Each evaluation shall emit a canonical unsigned replay certificate containing the certificate/schema/evaluation-input/profile/registry/trust/evaluator/policy/canonicalization/digest contracts; complete normalized request and registry/trust context; exact context bindings; evaluation and issuance times; origin; implementation identity; complete decision, reasons, qualification, and limitations; and a conservative current-use boundary.

**Acceptance criteria**

- Two runs on identical canonical inputs yield byte-identical certificate JSON and digest.
- A one-field request, context, version, origin, time, result, qualification, limitation, or implementation mutation changes the digest; unchanged-digest tampering and forged decisions fail the appropriate integrity or replay dimension.
- Permit and rejection certificates reproduce byte-for-byte on every supported runtime and are retained as separate canonical vectors.
- Verification reports structural support, outer and embedded integrity, deterministic historical replay, expected-context and expected-digest comparison, and time-bounded current local reliance separately; it never reports issuer authentication or action authorization.
- The certificate states one exact origin label. The label is descriptive and unauthenticated; it cannot upgrade insufficient evidence.
- The effective exclusive boundary conservatively includes evidence `valid_until`, snapshot `next_update_at`, resolved-profile expiry/revocation where applicable, and policy/profile observation and index age deadlines. Candidate.2 trust selection has no independent expiration field.
- P0 certificates are restricted to synthetic/public-safe or owner-approved nonsensitive content because the self-contained replay payload is not data-minimized.

#### ESIO-P0-009: JSON CLI and library interface

The reference implementation shall accept JSON from a file or standard input and emit only documented JSON to standard output, with diagnostics on standard error.

**Acceptance criteria**

- Valid envelope/evaluation inputs exit `0` and emit schema-valid output.
- Invalid input, unsupported versions, or evaluation rejection use documented distinct status fields and stable process exit behavior; a rejected claim is not confused with a program crash.
- Malformed JSON, oversized input under the configured limit, and unexpected fields are handled deterministically without stack traces or secret leakage on standard output.
- `evaluate` requires separate operator-controlled `--registry` and `--trust` files plus explicit `--issued-at` and `--origin`; no wall-clock or origin inference is permitted. `verify-certificate` accepts separate expected registry/trust state, an expected digest, and a relying-party time without treating omitted custody evidence as success.

#### ESIO-P0-010: Seed EmptyBench corpus and oracle

The repository shall include matched cases whose visible result is the same while evidence sufficiency differs.

**Acceptance criteria**

- The seed corpus contains at least one covered-zero control and one matched case for each P0 fault class.
- Expected verdicts are assigned by a deterministic oracle independent of the model under evaluation.
- The test suite fails if the gate permits a scoped negative for any disqualifying case or rejects the canonical covered-zero control.

**Current candidate note:** A second packaged benchmark, `EmptyBench-P1-composed`, covers the multi-source path with one pair per composition rule: disagreement, per-source coverage, the composed floor, each source's own finality horizon, the stalest contributing observation, and the earliest source validity boundary. Its expected outcomes are written by hand and its generator refuses to write artifacts the gate disagrees with, so the oracle is a claim about what the gate should do rather than a transcript of what it does.

#### ESIO-P0-011: Reproducibility and security baseline

The P0 package shall run locally without network or model access and shall document security assumptions.

**Acceptance criteria**

- Clean Python 3.11, 3.12, and 3.13 environments can install and execute the unit, integration, contract, and benchmark tests using the documented commands. Other Python versions are not in the supported P0 set.
- CI runs the same frozen checks and records tool/runtime versions.
- Tests cover untrusted strings, path-like values, oversized collections, duplicate identifiers, numeric edge cases, and deterministic serialization.

### P1 — evidence from real integrations

#### ESIO-P1-001: Read-only source adapters

Implement adapters for GitHub Search, SQL, and one operational-search interface such as Elasticsearch or Microsoft Sentinel.

**Acceptance criteria**

- Each adapter maps pagination, rate limits, authorization scope, time range, partitioning, and errors into the evidence envelope.
- Recorded/replayed contract tests include complete-zero and each adapter-specific partial/failure path.
- No adapter labels a result `ABSENT_WITHIN_SCOPE` solely because the returned item list is empty.

#### ESIO-P1-002: Authenticated coverage profiles, registry, and source evidence

Extend the P0 materialized local context with authenticated registry heads, profile/source-owner evidence, rollback resistance, lifecycle distribution, and versioned source profiles covering ownership, addressable population, retention, freshness, blind intervals, permissions, finality, and detection assumptions.

**Acceptance criteria**

- A profile change changes its digest and invalidates certificates that require the prior profile unless explicitly pinned.
- Missing or expired required profiles cause the gate to reject a scoped negative.
- Profile review ownership and effective dates are machine-readable.
- Authentication, delegated authority, monotonic-head/rollback behavior, revocation distribution, source-clock evidence, and compromised-credential recovery are explicitly designed and tested; a signature never upgrades insufficient evidence.

#### ESIO-P1-003: Multi-source composition

Define deterministic rules for composing source evidence without double-counting overlapping populations.

**Acceptance criteria**

- Identical source records cannot increase coverage through duplication.
- Unknown overlap yields a conservative lower bound or `NOT_OBSERVED`, never an optimistic sum.
- Contradictory source states produce `CONTRADICTORY` with source-specific reason codes.

#### ESIO-P1-004: Framework middleware

Provide thin integrations for MCP tool results and at least one agent runtime while preserving the base envelope.

**Acceptance criteria**

- Middleware carries the envelope as structured content without relying on model prose to reconstruct fields.
- If a client strips or mutates required evidence metadata, the downstream gate rejects the claim.
- Integration tests distinguish MCP protocol completion from evidence coverage completion.

#### ESIO-P1-005: Signed attestations

Support optional producer and evaluator signatures over canonical certificates.

**Acceptance criteria**

- Verification fails after any signed field mutation or when the signer is outside the configured trust policy.
- Signature validity does not change an insufficient evidence verdict to sufficient.
- Key rotation and revoked-key behavior are covered by tests.

#### ESIO-P1-006: Expanded benchmark and design-partner shadow mode

Expand EmptyBench and run read-only, authorized shadow evaluations without controlling operational decisions.

**Acceptance criteria**

- The benchmark, baseline prompts/configurations, oracle, and scoring scripts are version-frozen before the held-out run.
- Shadow reports separate synthetic, replayed, and directly observed cases.
- No operational action or investigation closure depends solely on the research prototype.

#### ESIO-P1-007: Privacy-preserving operational certificate profile

Define a separately versioned profile for non-public workflows that can minimize, redact, reference, or selectively disclose sensitive request and context fields without silently changing P0 replay semantics.

**Acceptance criteria**

- The profile identifies which fields remain embedded, redacted, externally referenced, or selectively disclosed and how each choice affects replay and verification.
- References are authenticated, access-controlled, retention-bound, and fail closed when unavailable or mismatched.
- Redaction cannot hide a safety-bearing input, reason, limitation, or trust decision from an authorized verifier.
- P0 self-contained certificates are never relabeled as minimized operational artifacts.

### P2 — ecosystem and formalization

- **ESIO-P2-001:** Formal semantics and property-based verification for state transitions, coverage composition, and non-bypass invariants.
- **ESIO-P2-002:** Cross-language schema and conformance kits for TypeScript, Go, and Java.
- **ESIO-P2-003:** Protocol-extension proposals only after two independent implementations and one external reproduction.
- **ESIO-P2-004:** Governed enterprise Coverage Registry service with review workflows, revocation, and policy distribution.
- **ESIO-P2-005:** Additional vertical profiles for software supply chain, financial reconciliation, critical-infrastructure monitoring, PNT/RF observation, and compliance evidence.
- **ESIO-P2-006:** Multi-hop qualification tracking that detects scope loss across agent-to-agent summaries.

## Nonfunctional constraints

- **Determinism:** model output cannot alter a gate verdict; wall-clock dependence must be explicit.
- **Fail closed:** unknown schema, state, policy, time, source, coverage, or continuation facts cannot produce `ABSENT_WITHIN_SCOPE`.
- **Dependency minimization:** P0 core must remain usable offline and avoid an agent-framework dependency.
- **P0 certificate disclosure:** the candidate self-contained replay certificate embeds the full normalized request, registry/trust context, decision, and implementation metadata. It is not data-minimized and is limited to synthetic/public-safe or owner-approved nonsensitive content.
- **P1 data minimization:** non-public use requires a separately versioned redaction/reference/selective-disclosure profile with authenticated custody and explicit replay consequences.
- **Untrusted producer model:** source-provided hints and annotations are evidence inputs, not trusted proof.
- **Backward compatibility:** an incompatible change to an accepted frozen schema requires a major schema version. Before schema `1.0` is frozen, defect corrections still require explicit candidate-contract bumps, downgrade tests, historical hash-bound custody, and an ADR; the package version never negotiates semantics.
- **Auditability:** every verdict must be explainable through stable reason codes, not only prose.
- **Separation of concerns:** an evidence permit is neither action authorization nor permission to close an investigation.

## Metrics and decision thresholds

| Metric | Definition | Prototype success threshold | Measurement stage |
|---|---|---:|---|
| Unsupported-negative rate | Unsupported negative conclusions / opportunities for a negative conclusion | At least 80% relative reduction vs preregistered baseline | Frozen EmptyBench |
| Unsafe gate permits | Disqualifying cases permitted as `ABSENT_WITHIN_SCOPE` | 0 | Unit, fault, and held-out benchmark |
| Supported-negative retention | Valid scoped negatives permitted / oracle-valid scoped negatives | At least 90% | Frozen EmptyBench |
| Pair discrimination | Matched pairs for which covered and insufficient cases receive the correct different verdicts | 100% for P0 deterministic gate | Seed and held-out corpus |
| Deterministic reproduction | Byte-identical certificates / identical reruns | 100% | CI across supported Python versions |
| Qualification retention | Permitted statements retaining all required scope/time qualifiers after one downstream handoff | At least 95% in P1 study | Model and human study |
| Adapter mapping completeness | Required adapter fault paths mapped to non-permit states | 100% of declared contract matrix | P1 replay tests |
| Evaluation overhead | Added local gate latency, excluding source query | Record p50/p95 and establish use-case budget before P1; no performance claim in P0 | Controlled benchmark |
| Problem incidence | Qualified discovery interviews identifying costly false-absence pattern | At least 3 of 10 | Discovery gate |

## Kill or pivot criteria

Stop or materially narrow the project if any of the following occurs:

1. The frozen deterministic gate produces any scoped-negative permit for a declared missing, inaccessible, stale, contradictory, incomplete, failed, or pending condition and the failure cannot be removed without universal blocking.
2. The gateway fails to achieve an 80% relative reduction in unsupported negatives or retains fewer than 90% of valid scoped negatives after one preregistered remediation cycle.
3. A simple competing control—such as a short prompt rule or existing protocol primitive—matches the safety/utility result without the evidence envelope or coverage model.
4. Required metadata cannot be obtained from real source APIs or maintained by source owners at acceptable operational cost.
5. Fewer than 3 of 10 qualified interviews reveal a material problem, or no partner will permit a bounded shadow evaluation.
6. By the P1 decision date, an adopted open protocol or mature product provides equivalent evidence-state semantics, conformance tests, and integration coverage; reassess differentiation before continuing.
7. Qualification is routinely stripped by downstream systems and no enforceable machine boundary can preserve it.
8. The only demonstrable benefit remains synthetic after attempts at authorized replay and independent reproduction.

Thresholds are frozen before the corresponding evaluation. They may be changed only prospectively with the owner’s approval, never to reinterpret a failed campaign.

## Delivery phases

### Phase 0 — 0 to 30 days: falsifiable core

- Preserve the accepted local schema `0.1` replay baseline and the hash-bound
  `0.6.0` local implementation record. Schema `1.0`, candidate contracts, and
  EmptyBench remain unfrozen unless separately approved.
- Draft the first implementation-owned comparative campaign preregistration
  for owner review.
- Establish naive, prompt-only, and always-block baselines.

### Phase 1 — 31 to 60 days: comparative decision gate

- After recorded owner approval, freeze and run the preregistered comparative
  campaign without reinterpretation.
- Decide stop, narrow, continue, or revise prospectively from the declared
  thresholds.
- Do not treat an implementation-owned campaign as independent adjudication or
  external reproduction.

### Phase 2 — 61 to 90 days: conditional adapter pressure test

- Begin only if the Phase 1 comparative gate passes.
- Implement one read-only adapter, then consider GitHub, SQL, or operational
  search profiles if the contract survives.
- Freeze recorded/replayed fixtures for pagination, rate limits, permissions,
  stale caches, and query failures.
- Run approved discovery interviews and select an authorized shadow workflow.
- Add certificate signing only if deterministic semantics are stable.
- Conduct an authorized shadow evaluation and seek independent reproduction.
- Decide whether to prepare a protocol proposal.

## Open decisions

- **[Owner, blocking for P1]** Which cyber workflow supplies the first authorized shadow case: threat hunting, vulnerability inventory, alert triage, or evidence collection?
- **[Research, blocking before held-out run]** What constitutes the minimum practically useful coverage lower bound for the selected workflow?
- **[Engineering, non-blocking for P0]** Should canonical JSON follow an existing standard or a narrowly documented project profile?
- **[Security, blocking before signatures]** What producer identities and trust roots are acceptable for source and evaluator attestations?
- **[Legal/data, blocking before real data]** What data classifications, retention rules, and export/privacy restrictions apply to the first design-partner corpus?
- **[Standards, P2]** Should the envelope be proposed as MCP structured content, an extension, or a protocol-independent companion specification?

## Readiness statement

At this stage, Evidence-State I/O is an implemented pre-alpha working candidate,
not a frozen or released contract. Named local tests can establish only the
enumerated deterministic behaviors for an exact hash, runtime, fixtures, and
configuration. The seed corpus and declarative oracle are separately versioned
and digest-bound, but both remain implementation-owned; independent
adjudication, a preregistered frozen campaign, the final hash-bound acceptance
record, authenticated registry/source evidence, and an operational redaction
profile remain open. No current result establishes source truth, real-world
detection completeness, production safety, market demand, protocol adoption,
independent validation, legal sufficiency, or action authority.
