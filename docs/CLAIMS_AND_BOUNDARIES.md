# Evidence-State I/O Claims and Evidence Boundaries

**Status:** controlling claims policy
**Version:** 0.2
**Date:** 2026-08-22
**Current claim level:** implemented pre-alpha candidate; acceptance, benchmark, and schema freeze remain open

## Controlling statement

Evidence-State I/O is designed to prevent a narrow failure: treating an empty or incomplete observation as an unqualified negative factual claim. Its deterministic gate can establish only whether the supplied evidence envelope satisfies a named policy for a bounded scope at a supplied evaluation time.

A permit is **not proof that the thing does not exist**. A rejection is **not proof that it exists**. The gate evaluates declared evidence sufficiency; it does not establish source honesty, query semantic adequacy, sensor detection performance, open-world completeness, action authorization, legal sufficiency, or operational safety.

If another document conflicts with this file, use the more conservative claim until the project owner resolves the conflict.

## Current verified posture

As of 2026-08-22:

- The project problem, semantics, requirements, and validation plan are specified.
- The package `0.6.0` working candidate implements the schema `1.0` candidate, policy candidate.4, evaluator candidate.5, exact application-selected profile governance under candidate.2 profile/registry/trust contracts, an unsigned candidate.2 deterministic replay certificate, and candidate.1 transition, authorization-identifier, and validation-error contracts. This statement is about the inspected implementation, not an accepted freeze or release.
- Actual implementation and test status must be taken from `PROJECT_STATUS.md` and a named, hash-bound verification record; an intended handoff artifact is not evidence that it exists or passes.
- The relying application supplies the registry snapshot, trust selection, and exact selected profile reference outside the producer request and must keep them producer-unwritable. Their issuer, authority, source-owner, origin, revision, and time labels are declarative and unauthenticated in P0.
- P0 certificates are self-contained and duplicate the complete request, registry/trust context, decision, and implementation metadata. They are not data-minimized and are restricted to synthetic/public-safe or owner-approved nonsensitive content.
- The source repository is public under Apache License 2.0. Open-source availability does not establish a stable release, protocol freeze, production readiness, independent validation, or authorization for consequential use.
- A bounded public scan found relevant adjacent protocol, conformance, caching, provenance, uncertainty, and governance work. Within the searched public sources, the team did not identify a mature, widely adopted implementation of this exact negative-claim evidence contract.
- No design-partner, independently reproduced, operational, production, market-demand, certification, or legal-sufficiency evidence exists unless a later controlled evidence package explicitly records it.

The public-source observation is provisional. It does not justify “nobody is working on this,” “first,” “only,” “unique,” or “no competitors.” Private/internal work, unpublished research, differently named projects, and unsearched sources remain unknown.

## Evidence classes

| Class | Evidence type | Permitted conclusion | Explicitly not established |
|---|---|---|---|
| E0 | Design documents and bounded public scan | The project proposes a mechanism; named public sources contain the described adjacent primitives; no direct implementation was found in that bounded scan | Novelty, lack of private competition, feasibility, effectiveness |
| E1 | Reviewed implementation and passing local unit/contract tests | Named functions satisfy named tests in the recorded environment | Benchmark effectiveness, real API behavior, external validation |
| E2 | Frozen synthetic EmptyBench campaign | Comparative performance on the exact synthetic corpus, configurations, and dates | Real-world effectiveness, source completeness, customer validation |
| E3 | Recorded/replayed adapter campaign | Adapter behavior for captured responses and named versions | Current live behavior, upstream truth, operational effectiveness |
| E4 | Independent reproduction | A separate party reproduced the frozen package under documented conditions | Production readiness, broad domain generalization |
| E5 | Authorized read-only shadow evaluation | Observed decision support in a bounded real workflow without operational control | Safe automation, production approval, causal impact at scale |
| E6 | Longitudinal operational evaluation | Measured performance for the deployed scope, population, period, and controls | Universal safety, permanent validity, other domains |
| E7 | Separate readiness/certification decision | Only the exact approval or certification recorded by the authorized body | Any broader approval or guarantee |

Evidence classes do not accumulate automatically. For example, E2 plus E3 is not E4, and E5 does not imply E6 or E7.

## Origin labels

Every test result, certificate, figure, table, and external statement must label evidence origin:

- **Synthetic:** constructed data or simulator truth.
- **Replayed:** recorded interaction executed against a local or controlled replay.
- **Lab-observed:** directly observed in a controlled local/VM/container environment.
- **Shadow-observed:** directly observed in an authorized real workflow without control authority.
- **Externally reproduced:** rerun by an independent party from a frozen package.
- **Operational:** observed during an approved operational deployment.

Do not shorten synthetic, replayed, or lab-observed evidence to “validated in the real world.” Lab and synthetic results are not external validation.

## Claim taxonomy

### 1. Design claim

**Example:** “Evidence-State I/O is designed to reject a scoped negative when required pagination is incomplete.”

Minimum evidence: E0 specification. Use “designed to” until the named tests pass.

### 2. Implementation claim

**Example:** “Version 0.1 rejects the incomplete-pagination fixture in the local test suite.”

Minimum evidence: E1 with repository commit, test name, environment, and result. Do not generalize from a fixture to all pagination failures.

### 3. Benchmark claim

**Example:** “On EmptyBench v0.1, configuration X reduced unsupported negatives from A/B to C/D relative to baseline Y.”

Minimum evidence: E2 frozen package. State counts, denominators, interval estimates, model/configuration, corpus version, and evidence origin.

### 4. Adapter claim

**Example:** “The GitHub adapter mapped the recorded unresolved-cursor response to `PARTIAL` in replay campaign R.”

Minimum evidence: E3. Do not say the adapter proves GitHub search is complete or current.

### 5. External reproduction claim

**Example:** “Team Z independently reproduced the frozen EmptyBench result within the stated tolerance.”

Minimum evidence: E4 with the independent report and resolved discrepancies. A demonstration, review, or partner attendance is not reproduction.

### 6. Operational-value claim

**Example:** “In an authorized shadow evaluation of workflow W over period T, the gateway flagged N evidence gaps that expert adjudication agreed should prevent closure.”

Minimum evidence: E5. Keep the claim bounded to the workflow, period, operators, and approval conditions.

### 7. Production/readiness claim

**Example:** “Approved for production use in environment X under control set Y.”

Minimum evidence: E7 and the actual authorized decision. The engineering team cannot infer this from tests, signatures, or pilots.

## Allowed and prohibited wording

| Topic | Allowed when supported | Prohibited or requires stronger evidence |
|---|---|---|
| Core behavior | “rejects unsupported scoped-negative claims in the named test set” | “proves absence,” “guarantees truth,” “eliminates hallucinations” |
| Empty results | “distinguishes a covered zero from an incomplete observation under the declared policy” | “knows when nothing exists” |
| Coverage | “coverage lower bound for the declared addressable population” | “complete visibility,” “100% detection,” “the entire environment” unless independently established for the exact bounded population |
| Gate permit | “evidence conditions satisfy policy P at time T” | “the claim is true,” “safe to close,” “authorized to act” |
| Gate rejection | “evidence is insufficient for the requested negative” | “the target exists,” “the source failed” unless separately established |
| Public whitespace | “we did not find a mature direct implementation in the bounded sources searched as of date D” | “nobody is working on this,” “first,” “only,” “no competition” |
| Local tests | “passed named local tests on commit H” | “validated,” “battle-tested,” “production ready” without qualification |
| Synthetic benchmark | “measured on synthetic EmptyBench vX” | “external validation,” “customer-proven,” “operationally effective” |
| Replay | “mapped captured response R correctly in replay” | “works across all live APIs,” “upstream completeness verified” |
| P0 profile custody | “matched the exact application-selected local profile and trust context” | “profile issuer authenticated,” “registry truth verified,” “source owner approved” |
| P0 certificate | “unsigned deterministic replay record whose named local checks passed” | “attestation,” “authorization token,” “authenticated custody,” “trusted timestamp,” “proof of source truth” |
| Signatures | “certificate integrity and signer identity verified under trust policy P” | “evidence is true,” “tamper-proof,” “nonrepudiation” without a defined legal/technical basis |
| Protocol relationship | “can be carried in structured tool output” | “MCP standard,” “MCP compliant extension,” or “endorsed” absent formal status |
| Security | “resisted the named tests” | “secure,” “unbypassable,” “zero risk” |
| Market | “3 of 10 qualified interviews reported the pattern,” if achieved | “market validated,” “category leader,” “unmet demand” from public-post volume alone |

## Normative negative-claim boundary

### Claims always rejected

The gate must not authorize:

- universal absence: “no instances exist,” “nothing is affected,” “there are no threats anywhere”;
- a negative whose population, time interval, query/filter, or evaluation time is absent;
- a negative broader than the accessible and evaluated population;
- a negative based only on `matched_count == 0` or an empty array;
- a negative with unresolved continuation, incomplete required partitions, unknown required sources, expired freshness, pending finality, inaccessible evidence, disqualifying errors, or contradiction;
- a negative whose required qualification is stripped in rendering.

### Claims potentially permitted

A scoped negative may be permitted only in a form equivalent to:

> Within **[declared population/sources]**, using **[query and filters]** for **[time interval]**, no matching records were observed as of **[evaluation time]** under **[policy/version]**, subject to **[material exclusions and detection assumptions]**.

The exact sentence is not proof that the underlying phenomenon did not occur. It states only the bounded observation result and conditions.

## Source and producer trust boundary

Evidence-State I/O treats producer metadata as untrusted input unless a separate trust policy says otherwise. Schema validation, signatures, and conformance tests can establish structural integrity, source identity, or tested behavior. They cannot establish that:

- the producer knew the true population denominator;
- access controls did not hide relevant records;
- the query captured all semantic variants;
- a sensor or upstream source detected every event;
- pagination or partition metadata was honest;
- a source was not compromised;
- the real world remained unchanged after evaluation.

A signed false statement remains false. The gate must never elevate insufficient evidence because it is signed.

### P0 profile-selection boundary

The request producer may carry only an exact profile reference. The relying application separately fixes the materialized registry snapshot, trust selection, and one exact selected profile reference, and must prevent the producer from modifying or substituting them. The request reference must equal the application-selected reference and resolve exactly in the trusted snapshot; no `latest`, range, alias, fallback, automatic upgrade, or downgrade is supported.

This is a local deterministic custody boundary. A matching digest detects mutation relative to separately held state, but it does not authenticate the registry publisher, profile issuer, approval authority, source owner, profile assertions, or source behavior. Trust or resolution failure prevents profile applicability and derived-finality content from contributing to the decision.

## Freshness, finality, and time boundary

- Every evaluation uses an explicit evaluation time; ambient wall-clock dependence is not evidence.
- Freshness is a policy condition, not a guarantee that the underlying data did not change.
- Finality is a governed but unauthenticated profile assertion in the current candidate. The evaluator derives the exact horizon from the application-selected profile's late-arrival and reopen bounds, binds it into the request and composite evaluation digest, and requires the reported source index to reach it.
- That deterministic comparison does not validate the service's lateness model, authenticate the index watermark, or prove that corrections, retractions, or exceptional late arrivals cannot occur.
- An unsigned certificate is a point-in-time replay record. Historical reproducibility does not make it current; current local reliance requires a separately supplied expected context, a separately retained expected certificate digest, and relying-party time within the conservative validity boundary, and still does not authorize an action.
- Clock synchronization, timestamp provenance, and cross-system causal ordering are dependencies outside P0 unless explicitly measured.

## Certificate content and disclosure boundary

The candidate.2 P0 certificate is self-contained so the embedded evaluation can be reproduced without a registry lookup. It therefore includes the normalized request, complete registry snapshot and trust selection, context binding, full decision, qualification, limitations, origin, and implementation identity. Its digest covers those fields, but the artifact is not signed, authenticated, independently timestamped, or data-minimized.

P0 use is limited to synthetic/public-safe or explicitly approved nonsensitive content. A future P1 operational profile must separately define authenticated registry/source evidence and a redaction, reference, minimization, or selective-disclosure design. Removing or replacing embedded fields without a new versioned contract would break the current replay semantics.

## Protocol boundary

The MCP tools specification provides structured content/output schemas, protocol result types, pagination, authorization-dependent visibility, and caching hints. Those are important transport and interoperability primitives. Evidence-State I/O must not claim they are absent.

The residual research question is narrower: whether a portable contract can state and evaluate the population, access, coverage, semantic-query, cross-page/partition, freshness, finality, exclusion, and error conditions required for a negative factual claim. A protocol response labeled `complete` must not be described as defective merely because it does not prove real-world absence; protocol completion and evidence sufficiency are different layers.

## Governance and action boundary

An Evidence-State permit is advisory evidence for another decision process. It does not:

- grant data access;
- authorize a tool call or consequential action;
- close an incident or investigation;
- satisfy a compliance, audit, discovery, or legal burden;
- replace a human or designated decision authority;
- override domain policy, safety cases, or operational procedures.

If integrated with an action-governance system, both evidence sufficiency and action authorization must pass independently.

## Benchmark reporting rules

Any quantitative statement must include:

- exact corpus and split version;
- model/provider/configuration and evaluation date, where applicable;
- baseline definition;
- counts and denominators, not percentages alone;
- evidence origin label;
- confidence interval or explicit statement that no inferential estimate is appropriate;
- missing, invalid, timeout, and excluded cases;
- per-fault unsafe permits;
- whether thresholds were frozen before the run;
- repository commit and evidence-package digest.

Do not select the best prompt, seed, model, threshold, or subset after observing held-out results and present it as preregistered.

## Whitespace and competitive-claim rules

The source register is an evidence log, not a patent search, freedom-to-operate opinion, exhaustive systematic review, or market census.

Permitted statement:

> A bounded public scan completed on 2026-08-21 found adjacent work but did not identify a mature, widely adopted implementation of the exact Evidence-State I/O contract in the searched sources. Private, unpublished, differently named, and subsequently released work remains unknown.

Prohibited statements without separate authoritative evidence:

- “No one else is doing this.”
- “This is the first or only solution.”
- “There are no competitors.”
- “The research gap is proven.”
- “The market is uncontested.”
- “Patentable” or “freedom to operate.”

Before each external investment, publication, or standards decision, refresh the scan and record new closest work.

## Delivery-state language

Use exactly one or more of the following, backed by a record:

- **Specified:** requirements and acceptance criteria exist.
- **Implemented:** code exists and was inspected at a named commit.
- **Tested:** named tests passed in a recorded environment.
- **Benchmarked:** a frozen campaign produced reproducible measurements.
- **Adapter-validated:** named recorded/replay contract matrices passed.
- **Externally reproduced:** an independent party reran the frozen package.
- **Operationally evaluated:** an authorized bounded real workflow was observed.
- **Production ready:** a separate authorized readiness decision exists.

Never use “complete,” “done,” “validated,” or “ready” without naming the relevant state and scope.

## Current claims ledger

| ID | Claim | Current status | Maximum current wording |
|---|---|---|---|
| C-001 | Empty result alone is insufficient for a universal absence claim | Supported as the project’s logical/design premise and by documented pagination/access/freshness limitations | “An empty result does not by itself establish absence beyond its execution scope.” |
| C-002 | Existing public protocol primitives do not fully specify the proposed negative-claim evidence contract | Provisional bounded-source observation | “The reviewed specifications expose useful primitives, but the exact proposed contract was not observed in the bounded scan.” |
| C-003 | The P0 gate satisfies all invariants | Not established; named local tests support only the enumerated candidate behaviors recorded for a hash-bound revision | “The candidate passed the named tests for [enumerated behavior] on commit H”; do not generalize to all invariants |
| C-004 | The system reduces unsupported negatives by at least 80% | Prospective acceptance threshold only | “The project will continue only if a frozen benchmark demonstrates…” |
| C-005 | The system preserves at least 90% of valid scoped negatives | Prospective acceptance threshold only | Same prospective formulation |
| C-006 | Real adapters can populate the contract honestly | Untested hypothesis | “Adapter feasibility will be tested.” |
| C-007 | Practitioners will maintain coverage profiles | Untested product hypothesis | “Discovery and shadow evaluation will test…” |
| C-008 | The product is differentiated, demanded, or commercially viable | Not established | No affirmative external claim |
| C-009 | The product is externally validated or production ready | Not established | Explicitly state that it is not established |

Update this ledger only when a traceable evidence package exists. Preserve rejected or superseded claims rather than silently deleting them from frozen releases.

## Review checklist before any external statement

- [ ] Is the statement tied to a claim ID and evidence class?
- [ ] Does it name the exact scope, version, environment, time, and origin?
- [ ] Are hypothesis, vendor statement, public-scan observation, lab result, and external evidence clearly separated?
- [ ] Are counts, denominators, baselines, failures, and uncertainty included for metrics?
- [ ] Does “complete” refer only to a declared population and policy?
- [ ] Does the wording avoid absolute absence, universal safety, novelty, and market-exclusivity claims?
- [ ] Does it avoid converting a gate permit, profile match, digest match, replay result, or current-local-reliance result into truth, authenticated custody, or action authorization?
- [ ] If a certificate is shared, has every embedded request, registry/trust, decision, limitation, and implementation field been approved for that destination?
- [ ] Does it avoid calling synthetic/replay/lab results external validation?
- [ ] Has the whitespace scan been refreshed for a novelty or competition statement?
- [ ] Has the project owner approved any official release/announcement,
  external contact, license change, and use of non-public evidence?

## Approval boundary

Only the project owner may authorize an official project tag/release,
announcement, license change, external outreach, partner commitment, deployment,
use of non-public data, or claim beyond the current verified posture. P0 use
remains synthetic/public-safe or owner-approved nonsensitive. Nothing in this
project-governance boundary limits third-party rights to use, modify, or
redistribute the work under Apache License 2.0. Researchers and agents may
propose stronger project claims but may not publish them on the project's
behalf until the required evidence and approval are recorded.
