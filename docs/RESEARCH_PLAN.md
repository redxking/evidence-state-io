# Evidence-State I/O Research Plan

**Status:** preregistration draft
**Version:** 0.1-draft
**Date:** 2026-08-21
**Research stage:** concept definition and local prototype
**Primary research domain:** cyber investigation and threat hunting

## Research objective

Determine whether a typed evidence-state envelope plus a deterministic gate can reduce unsupported negative conclusions from AI tool workflows while preserving useful, coverage-supported scoped negatives.

The central research question is not whether an AI model can be prompted to say “I am uncertain.” It is whether evidence sufficiency can be represented at the tool boundary, evaluated independently of model prose, carried through downstream handoffs, and maintained at acceptable integration and operating cost.

## Current evidentiary position

The starting point is a bounded scan of public papers, protocol specifications, open-source repositories, issues, discussions, and official product documentation. That scan identified adjacent work on structured tool results, protocol completion, caching, conformance, uncertainty propagation, provenance, and action/outcome governance. It did not identify a mature, widely adopted, cross-platform implementation of the exact evidence-state and negative-claim contract proposed here.

That observation supports further investigation; it does **not** prove that nobody is working on the problem. Private research, internal enterprise systems, unpublished programs, differently named work, and sources outside the scan remain unknown. The public scan must be refreshed at every major investment decision.

## Research questions

### RQ1 — Failure prevalence

How often do baseline AI/tool workflows turn observationally identical empty results into the same negative conclusion despite different coverage, access, freshness, pagination, finality, or error conditions?

### RQ2 — Semantic sufficiency

Is the proposed state model sufficient to distinguish `PRESENT`, coverage-supported `ABSENT_WITHIN_SCOPE`, and the major classes of indeterminate non-observation without excessive ambiguity or domain-specific exceptions?

### RQ3 — Safety/utility tradeoff

Does deterministic gating reduce unsupported negatives relative to naive and prompt-only baselines without collapsing valid scoped negatives into universal abstention?

### RQ4 — Qualification retention

Can the required scope, time, access, and limitation qualifiers survive one or more model, agent, API, and human handoffs?

### RQ5 — Adapter feasibility

Can real tool APIs supply and maintain the evidence metadata required by the contract, including honest pagination, rate-limit, authorization, time, error, and population facts?

### RQ6 — Operational value

Do investigation leads recognize a recurring, consequential false-absence pattern for which the added metadata and gate would change a real decision or prevent premature closure?

### RQ7 — Differentiation

Does Evidence-State I/O add measurable value beyond existing structured outputs, protocol `resultType`, caching/freshness hints, error envelopes, generic provenance, uncertainty wrappers, and a simple conservative prompt?

## Hypotheses and falsification conditions

| ID | Hypothesis | Falsifying result | Required evidence |
|---|---|---|---|
| H1 | Baseline systems will produce materially more unsupported negatives on incomplete/stale/inaccessible paired cases than on a deterministic evidence-state gate. | The baseline already distinguishes the pairs, or the gate improves unsupported-negative rate by less than 80% relative on the frozen corpus. | Preregistered paired EmptyBench run. |
| H2 | The proposed state and reason-code model can classify the P0 fault taxonomy with high agreement. | Two independent expert annotators cannot reach Cohen’s kappa >= 0.80 after one rubric revision, or recurrent cases require incompatible state meanings. | Blind annotation study plus adjudication log. |
| H3 | The gate can preserve at least 90% of oracle-valid scoped negatives while permitting zero declared disqualifying cases. | Valid-negative retention is below 90%, or any disqualifying case is permitted. | Deterministic unit/fault tests and held-out benchmark. |
| H4 | Typed evidence metadata adds value beyond a prompt-only warning and an always-block policy. | Prompt-only matches the gate’s safety/utility frontier, or always-block yields equivalent operational utility at lower cost. | Three-baseline comparative study. |
| H5 | Required metadata can be derived from representative read-only APIs without unverifiable assumptions dominating the verdict. | At least two of three target adapter classes cannot expose required pagination/access/freshness/completion facts, or source-owner effort makes profiles unsustainable. | Adapter contract matrix, owner interviews, replay evidence. |
| H6 | Qualification can survive a downstream handoff when carried as machine-readable evidence. | Fewer than 95% of permitted claims preserve all policy-required qualifiers after one handoff, and middleware cannot enforce retention. | Controlled model/API/human transfer study. |
| H7 | The problem is consequential enough to support a product wedge. | Fewer than 3 of 10 qualified interviews identify a costly case, or no bounded shadow evaluation is available. | Interview protocol, de-identified coding, partner decision record. |

Targets are prospective. They are not claims about current performance.

## Operational definitions

### Observation

A recorded result from an explicitly identified source/query execution. An observation is not automatically evidence of source truth or real-world detection completeness.

### Negative-claim opportunity

A task in which the system is asked, directly or indirectly, whether a target item, event, record, condition, or class exists within some universe.

### Unsupported negative

A statement that asserts or materially implies absence beyond the population, fields, time interval, access boundary, detection assumptions, and finality supported by the available evidence.

### Valid scoped negative

A statement limited to the declared query and scope for which the independent oracle confirms zero matches and every policy-required coverage, completion, access, freshness, finality, exclusion, and error condition passes.

### Coverage lower bound

A conservative, reproducible lower bound on the fraction of the policy-required addressable population or required units that were successfully evaluated. It is not a probability that the real-world phenomenon is absent.

### Finality

The time after which the selected source is expected, under a declared assumption or service contract, to have incorporated observations for the requested interval. Finality is source-specific and can remain uncertain.

### Qualification retention

The fraction of policy-required scope, source, time, and limitation elements present and materially unchanged in the downstream representation.

## Conceptual model to test

The initial envelope must distinguish result presence from evidence sufficiency. The normative states are:

- `PRESENT`
- `ABSENT_WITHIN_SCOPE`
- `NOT_OBSERVED`
- `PARTIAL`
- `STALE`
- `INACCESSIBLE`
- `PENDING_WINDOW`
- `FAILED`
- `CONTRADICTORY`

The research must test whether these states are mutually understandable, whether priority rules are needed when multiple failures coexist, and whether stable reason codes should carry the multi-causal detail rather than expanding the top-level enumeration.

## Research work packages

### WP0 — Adjacent-work and novelty falsification

**Purpose:** prevent investment based on an overstated whitespace claim.

Activities:

- Maintain the primary-source register in `SOURCE_REGISTER.md`.
- Search protocol repositories, conformance suites, benchmarks, academic indexes, and product documentation using terminology beyond “evidence state,” including empty-result semantics, negative claims, query completeness, non-observation, search coverage, epistemic status, finality, and inaccessible evidence.
- Record the closest functionality and the exact residual gap; do not classify adjacent work as irrelevant merely because terminology differs.
- Contact maintainers or researchers only with owner approval.

Exit evidence:

- A dated search protocol, source list, inclusion/exclusion criteria, and candidate matrix.
- A decision on whether the project remains differentiated, should contribute to an existing effort, or should stop.

### WP1 — State semantics and annotation reliability

**Purpose:** determine whether independent experts can apply the state model consistently.

Method:

1. Create 40 short vignettes spanning covered zero, positive match, incomplete pagination, missing partition, limited authorization, stale cache, pending ingestion, query failure, rate limit, contradiction, unknown overlap, and multiple simultaneous faults.
2. Have two independent reviewers assign a top-level state, reason codes, and permitted claim class using a frozen rubric.
3. Measure raw agreement and Cohen’s kappa for state and permit/reject decisions.
4. Conduct one adjudication/rubric revision cycle, then test on a new held-out set.

Success condition: kappa >= 0.80 on held-out state labels and 100% agreement on whether a scoped negative may pass. If agreement remains low, revise or reduce the state model before expanding implementation.

### WP2 — EmptyBench construction

**Purpose:** isolate evidence sufficiency from visible result content.

Design principles:

- Pair cases so the user/model sees the same empty item list while machine-readable evidence differs.
- Include one-variable perturbations and multi-fault cases.
- Assign ground truth through a deterministic simulator/oracle, not model judgment.
- Freeze development and held-out partitions by digest before baseline evaluation.
- Add adversarial cases where a producer claims `ABSENT_WITHIN_SCOPE` but invariant fields contradict it.

Initial scenario families:

1. complete zero vs unresolved continuation cursor;
2. all required partitions vs one missing partition;
3. full authorization vs filtered authorization scope;
4. fresh snapshot vs expired freshness;
5. closed finality window vs pending ingestion/finality;
6. successful zero vs rate limit, timeout, query, or parse error;
7. known addressable population vs unknown population denominator;
8. consistent sources vs contradictory sources;
9. valid zero vs one in-scope positive observation;
10. semantically correct query vs query that omits a required field or synonym;
11. stable snapshot vs cross-page mutation and gap risk;
12. single fault vs co-occurring faults with reason-code ordering pressure.

### WP3 — Comparative baseline study

**Purpose:** test whether the contract adds value beyond simpler controls.

Conditions:

- **B0 naive:** raw tool result and normal system behavior.
- **B1 prompt-only:** raw result plus a concise instruction not to confuse “not found” with “does not exist.”
- **B2 always-block:** no negative conclusion is ever permitted.
- **E1 envelope-visible:** model sees the typed envelope but no deterministic gate.
- **E2 Evidence-State gate:** deterministic verdict and qualification-preserving rendering.

Where models are evaluated, freeze model/provider version, prompt, decoding parameters, tool transcript, retry policy, and evaluation date. Use at least five independent runs per model/case condition if nondeterminism remains. Report every model separately; do not average away a weak model or provider-specific failure.

Primary outcomes are unsupported-negative rate and valid scoped-negative retention. Secondary outcomes include claim specificity, reason correctness, abstention, latency, token/byte overhead, and qualification retention.

### WP4 — Adapter feasibility and replay

**Purpose:** determine whether the semantics survive real APIs.

Target classes:

- GitHub Search or equivalent paginated public repository search;
- SQL over a bounded table with known snapshot and row-level access conditions;
- Elasticsearch, Microsoft Sentinel, or comparable operational search with time, index, role, timeout, and shard/partition considerations.

For each adapter, create a contract matrix for:

- addressable and accessible populations;
- authorization identity without embedding credentials;
- query/filter and time-window identity;
- page, cursor, partition, shard, and continuation behavior;
- result caps and total-count accuracy;
- rate limit, timeout, and partial-error behavior;
- snapshot consistency and source mutation;
- retention, ingestion delay, freshness, and finality;
- exclusions and detection assumptions.

Use recorded/replayed, non-sensitive fixtures first. A live call demonstrates connectivity and adapter behavior only for that call; it does not establish general completeness.

### WP5 — Problem discovery and human-factors study

**Purpose:** establish whether the workflow pain and qualification are meaningful to practitioners.

Recruit 10 qualified participants across investigation leads, threat hunters, security platform engineers, source owners, and assurance architects. Use critical-incident interviews focused on a specific past “none found,” “no exposure,” “no affected assets,” or “no evidence” decision. Do not ask leading questions about the proposed product before the participant describes the workflow and consequence.

Code:

- decision terminated or continued;
- evidence sources expected and actually queried;
- known/unknown access and coverage gaps;
- consequence of a false clearance;
- current workaround and labor cost;
- whether a qualified negative would change action;
- willingness and ability to maintain source profiles.

The human-factors test will compare raw empty results, prose caveats, and structured evidence certificates. Measure whether participants correctly decide “close bounded question,” “continue investigation,” or “escalate evidence gap,” plus time and confidence calibration.

### WP6 — Authorized shadow evaluation and independent reproduction

**Purpose:** move beyond local synthetic behavior without allowing the prototype to control operations.

- Run the gateway in read-only shadow mode on an approved workflow.
- Preserve the operator’s normal decision, gateway recommendation, source-state evidence, disagreements, and later adjudication.
- Do not expose non-public data outside the authorized environment.
- Freeze a de-identified or synthetic reproduction package where permitted.
- Invite an independent team to rerun the frozen benchmark and verify certificate determinism.

External reproduction is a distinct delivery state. A partner observing or reviewing a demonstration is not independent reproduction.

## Benchmark corpus and sampling

### Seed corpus

The P0 repository includes a minimal covered-zero control and matched cases for every disqualifying state. Its purpose is regression prevention, not a publishable performance estimate.

### Research corpus

Construct 12 scenario families with eight controlled perturbations each for at least 96 deterministic cases. Reserve 20% of family-stratified cases as held out before model or prompt tuning. Add a separate adversarial set with malformed, contradictory, and tampered envelopes.

The final sample size for model comparisons will be set by an a priori power analysis using pilot discordance rates. The 96-case design is a minimum coverage target, not a substitute for power analysis.

### Operational corpus

Operational cases are sampled prospectively from an authorized shadow workflow. Selection rules, excluded cases, missing data, and operator overrides must be logged. Convenience cases chosen after observing results cannot support a general effectiveness claim.

## Analysis plan

- Report confusion matrices for the oracle claim class and gate/baseline decision.
- Primary safety metric: unsupported-negative rate.
- Primary utility metric: valid scoped-negative retention.
- Use paired McNemar tests for binary decisions on matched cases and report effect size with 95% confidence intervals.
- Use cluster-aware bootstrap confidence intervals by scenario family so many perturbations of one family do not create false precision.
- For nondeterministic model runs, use a mixed-effects logistic model or family/model-stratified estimates with run as a repeated measure.
- Report the always-block baseline explicitly to show whether improvement is more than abstention.
- Report failures and missing runs in the denominator according to a frozen policy; do not discard timeouts or invalid outputs.
- Preserve per-case results so aggregate success cannot hide a catastrophic fault class.

No statistical significance result establishes operational safety. The study tests bounded hypotheses under its frozen conditions.

## Threat model

The research must include the following adversaries and faults:

- a buggy producer that marks partial results complete;
- a malicious producer that fabricates coverage or freshness;
- a gateway caller that omits or reorders failure metadata;
- a model that removes qualifiers or asserts a broader claim than permitted;
- stale or poisoned source profiles;
- mismatched evaluation time or clock skew;
- pagination loops, dropped pages, duplicate pages, and mid-query source mutation;
- rate limits, soft errors, HTTP success with incomplete application data, and swallowed exceptions;
- row-level or tenant-level authorization filters that make the accessible population smaller than the intended population;
- semantically incomplete queries that technically scan every returned page;
- certificate mutation, replay, downgrade, and unknown schema/policy versions.

P0 does not solve Byzantine source trust. It must surface that reliance as an explicit assumption and fail closed when required attestations are absent.

## Validity limitations

### Construct validity

- A coverage lower bound measures the declared addressable universe, not the probability that the real-world phenomenon is absent.
- “Complete” at the transport or pagination layer does not establish query semantic completeness.
- State labels may compress multiple simultaneous causes; reason codes and raw evidence remain necessary.

### Internal validity

- Benchmark authors may encode the proposed contract into the oracle and favor the gateway by construction.
- Prompt-only baselines may be underoptimized or model selection may bias results.
- Synthetic faults may be cleaner than real API behavior.

Mitigations include preregistration, independent review of the oracle, strong baselines, held-out families, mutation testing, and publication of all exclusions.

### External validity

- Cyber search does not establish usefulness in finance, critical infrastructure, PNT/RF, compliance, or other domains.
- A few adapters do not establish cross-platform interoperability.
- Design partners are likely to be more governance-mature than the broader market.
- Lab, replay, and synthetic results are **not external validation**, customer validation, or production evidence.

### Temporal validity

- Protocols, APIs, caches, permissions, source schemas, and adjacent products change.
- A correct absence certificate can become stale immediately after evaluation.
- The public whitespace scan can become outdated and never covers private/internal work.

### Ecological validity

- Operators may ignore or misunderstand qualified statements under incident pressure.
- Real investigations contain changing hypotheses, source dependencies, and tacit knowledge that a static benchmark omits.

## Security, ethics, and data boundaries

- Use synthetic or public data by default.
- Obtain explicit owner approval before any external contact, live third-party testing, real partner data, deployment, versioned/package release, or claims beyond the public pre-alpha boundary.
- The repository is public under Apache License 2.0; public availability is not evidence of a stable protocol, external reproduction, operational validation, or production readiness.
- Do not ingest personal, proprietary, regulated, classified, export-controlled, or operationally sensitive data without an approved handling plan.
- Limit adapters to authorized read-only queries during research.
- Do not represent an evidence permit as permission to take action, close an incident, or satisfy a legal burden.
- Record model/provider data-retention implications before submitting any non-public transcript.
- De-identify interview records and obtain informed consent for recording or quotation.

## Reproducibility package

Every frozen campaign must include:

- corpus and split digests;
- schema, policy, evaluator, adapter, and reason-code versions;
- complete prompts and model/provider identifiers;
- decoding, retry, timeout, and concurrency settings;
- runtime and dependency lock information;
- oracle and scorer source;
- per-case inputs, outputs, verdicts, errors, and exclusions;
- analysis code and generated summary;
- explicit origin classification: synthetic, replayed, directly observed, or externally reproduced;
- claims file stating what the package does and does not establish.

## Decision gates

### Gate A — semantics

Proceed to adapter work only if the P0 invariant suite passes and independent annotation reaches the agreement threshold.

### Gate B — incremental value

Proceed to design-partner shadow mode only if the frozen benchmark clears both the safety and valid-negative-retention thresholds and outperforms prompt-only and always-block baselines on the preregistered utility function.

### Gate C — feasibility and demand

Proceed toward a maintained product only if at least one real adapter can populate required metadata honestly, 3 of 10 interviews identify material pain, and a bounded shadow workflow is approved.

### Gate D — externalization

Consider a frozen public protocol proposal or versioned/package release only after independent reproduction, security review, documented governance, and owner approval.

## 90-day research schedule

| Period | Work | Decision output |
|---|---|---|
| Days 0–15 | Freeze constructs, state rubric, reason codes, P0 schema, seed cases, and adjacent-work protocol | Gate A readiness |
| Days 16–30 | Implement and mutation-test deterministic gate; build annotation set; establish baselines | Semantics and baseline report |
| Days 31–45 | Build first read-only adapter and replay faults; begin discovery interviews | Adapter feasibility memo |
| Days 46–60 | Expand corpus, freeze held-out split, complete discovery, select shadow workflow | Gate B/C preregistration |
| Days 61–75 | Run frozen comparative study and authorized shadow setup/evaluation | Per-case evidence package |
| Days 76–90 | Independent rerun attempt, security/claims review, stop/narrow/continue decision | Research decision record |

## Required conclusion format

Every research report must separate:

1. verified implementation facts;
2. observations from the exact test campaign;
3. statistical estimates and uncertainty;
4. design-partner or operator observations;
5. hypotheses and proposed interpretations;
6. untested assumptions;
7. prohibited generalizations.

The conclusion must never state that nobody else is working on the problem, that synthetic results constitute external validation, or that a gate certificate proves real-world absence.
