# Evidence-State I/O Source Register

**Register date:** 2026-08-21
**Purpose:** primary-source traceability and novelty falsification
**Scope:** public specifications, official repositories/documentation, author preprints, and first-party product materials surfaced in the bounded scan

## How to use this register

This is a working evidence register, not an exhaustive systematic review, patent search, freedom-to-operate opinion, market census, or proof of novelty. A source being absent from this register does not mean it does not exist. Public search cannot reveal private/internal work, unpublished research, differently named systems, or material outside the search boundary.

The project itself has no selected public license. Listing public sources here neither imports their licenses nor authorizes distribution or reuse of this repository.

Source observations below are deliberately narrow:

- **Supports** records the specific fact or design pressure for which the source is relevant.
- **Does not establish** prevents the source from being used to make a broader claim.
- Preprints are author primary sources but may not be peer reviewed.
- Repository issues and discussions document public implementation concerns; they are not standards or consensus findings.
- Product pages and project READMEs are first-party descriptions, not independent validation.
- “Residual question” is an analytical judgment to test, not an established research gap.

All links were surfaced during the 2026-08-21 research thread. Links and source contents can change; pin commit/version identifiers before using a source in a publication or frozen campaign.

## Core protocol and implementation sources

### S-001 — MCP tools specification, dated 2026-07-28

**Source:** [Model Context Protocol — Tools](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx)
**Type:** official protocol specification in the project repository
**Observed relevance:** Defines model-controlled tools, input/output schemas, structured and unstructured results, protocol result types, pagination, authorization-dependent tool visibility, and the trust boundary for tool annotations. It shows that Evidence-State I/O can be carried as structured output and must coexist with existing protocol-completion semantics.
**Does not establish:** That MCP lacks every possible extension or application schema for evidence state; that a protocol `complete` result proves query, population, or real-world completeness; or that Evidence-State I/O is MCP-endorsed.
**Residual question:** Can a portable evidence envelope cleanly separate protocol completion from negative-claim evidence sufficiency without conflicting with MCP semantics?
**Refresh trigger:** any new dated MCP release, change to result types, pagination, output schemas, or annotations.

### S-002 — MCP caching draft

**Source:** [Model Context Protocol — Caching](https://modelcontextprotocol.io/specification/draft/server/utilities/caching)
**Type:** official draft specification
**Observed relevance:** Defines cache TTL hints, public/private cache scope, freshness calculation, and page-level caching. It explicitly describes TTL as a hint and notes that paginated pages can lack cross-page consistency. These are direct inputs to the `STALE`, access-boundary, and pagination/snapshot portions of the proposed contract.
**Does not establish:** Source truth, immutable data during TTL, a consistent multi-page snapshot, query semantic completeness, or evidence sufficiency for a negative claim.
**Residual question:** What additional time and snapshot fields are necessary to turn cache/pagination hints into a conservative evidence decision?
**Refresh trigger:** draft promotion or changes to TTL, cache scope, or pagination interaction.

### S-003 — MCP conformance framework

**Source:** [modelcontextprotocol/conformance](https://github.com/modelcontextprotocol/conformance)
**Type:** official conformance-test repository
**Observed relevance:** Provides a useful pattern for versioned client/server scenarios, wire-schema checks, expected failures, and frozen requirement revisions. It is a direct design reference for an Evidence-State conformance kit.
**Does not establish:** Application-level truth, source coverage, correct negative conclusions, or conformance of this project.
**Residual question:** Can evidence-state scenarios be layered on protocol conformance without confusing wire validity with semantic sufficiency?
**Refresh trigger:** evidence-related scenarios or extension conformance are added.

### S-004 — MCP validator discussion #2733

**Source:** [What should a stdio MCP validator check beyond initialize and tools/list?](https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/2733)
**Type:** public project discussion; not normative
**Observed relevance:** Discusses separating install/runtime, transport, protocol, schema-quality, live-call, timeout, and observability failure classes. This supports keeping execution failure reason codes distinct rather than collapsing every empty/no-response condition.
**Does not establish:** MCP consensus, adoption, or a standard evidence-state taxonomy.
**Residual question:** Which live-call failure classes must be represented to prevent an empty or missing result from being mistaken for absence?

### S-005 — MCP filesystem annotation issue #2988

**Source:** [Add ToolAnnotations to Filesystem tools for accurate UI and safer retries](https://github.com/modelcontextprotocol/servers/issues/2988)
**Type:** official-repository issue; contributor proposal, not normative
**Observed relevance:** Shows a concrete integration consequence when tool semantics are not emitted in structured annotations and clients must default conservatively. It is an analogy for machine-readable evidence semantics and a reminder that producer hints require client policy.
**Does not establish:** A negative-claim gap, protocol consensus, or the correctness of the proposed issue mapping.
**Residual question:** Can evidence-state metadata remain useful while still treating producer annotations as untrusted?

### S-006 — Genkit agent error handling

**Source:** [Genkit — Handle Errors in Agentic Flows](https://genkit.dev/docs/agents/errors/)
**Type:** official framework documentation
**Observed relevance:** Screening source for structured agent/tool error behavior and how application errors reach a model or orchestrator.
**Access note:** The live page timed out during the 2026-08-21 verification pass; do not rely on a detailed content claim until it is re-opened and captured.
**Does not establish:** Evidence completeness or negative-claim safety.
**Residual question:** Do common framework error envelopes preserve partial-result, continuation, access, and freshness distinctions end to end?

### S-007 — Agent2Agent protocol schema

**Source:** [A2A protocol buffer specification](https://github.com/a2aproject/A2A/blob/main/specification/a2a.proto)
**Type:** official project specification
**Observed relevance:** Screening source for task/result states, artifacts, extensions, and metadata in agent-to-agent exchange. It is relevant to qualification retention and cross-agent transport.
**Does not establish:** A standardized evidence-state or negative-claim contract, nor that arbitrary metadata will be preserved or interpreted consistently.
**Residual question:** What minimum typed subset must be normative so agents cannot silently reinterpret or discard evidence qualification?

## Closest research sources

### S-008 — Evidentiary adequacy for agent oversight

**Source:** [From Runtime Records to Legal Findings: An Evidentiary-Adequacy Criterion for Agentic AI Oversight](https://arxiv.org/abs/2607.00941)
**Type:** author preprint/technical report
**Observed relevance:** Argues that records or integrity alone are insufficient for bounded findings of fact unless the record carries the typing and relations—such as provenance, authority, derivation, or temporal validity—on which the finding depends. This is the closest theoretical basis in the scanned set for claim-specific evidence adequacy.
**Does not establish:** Sufficiency of the Evidence-State I/O fields, product feasibility, negative-search completeness, or peer-reviewed consensus. The paper’s criterion is described as necessary rather than sufficient.
**Residual question:** Can the necessity argument be operationalized for negative search claims with a practical, testable coverage contract?

### S-009 — Situation-awareness uncertainty propagation

**Source:** [SAUP: Situation Awareness Uncertainty Propagation on LLM Agent](https://arxiv.org/abs/2412.01033)
**Type:** author preprint
**Observed relevance:** Adjacent work on carrying uncertainty through an LLM agent rather than treating a result as unqualified fact. It is a direct comparator for the “envelope-visible” experimental condition.
**Does not establish:** Population coverage, pagination/finality semantics, or a deterministic permit rule for scoped negative claims.
**Residual question:** Does typed evidence sufficiency outperform generic or scalar uncertainty for empty-result decisions?

### S-010 — Relational uncertainty propagation

**Source:** [From Sequence to Structure: Relational Uncertainty Propagation for LLM Agents](https://arxiv.org/abs/2608.16002)
**Type:** author preprint
**Observed relevance:** Adjacent work treating uncertainty as structured and relational across agent reasoning. It challenges any claim that structured uncertainty itself is novel.
**Does not establish:** A source-coverage contract, absence semantics, or deterministic negative-claim enforcement.
**Residual question:** Which parts of the proposed evidence envelope are genuinely distinct from relational uncertainty representations?

### S-011 — Commit-time authorization

**Source:** [Temporary Authority, Permanent Effects: Commit-Time Authorization for LLM Agents](https://arxiv.org/abs/2607.10487)
**Type:** author preprint
**Observed relevance:** Demonstrates a fail-closed runtime boundary where stale or ineligible evidence must be refreshed, rebound, or refused before a durable action. It supplies an architectural analogue for evaluating freshness and eligibility at claim time rather than trusting earlier evidence.
**Does not establish:** Negative-result semantics, search coverage, or Evidence-State I/O effectiveness. Its protected property is authorization of effects.
**Residual question:** Can the same boundary discipline be applied to factual claim issuance without conflating evidence sufficiency with action authority?

### S-012 — Proof of execution

**Source:** [Proof of Execution: Runtime Verification for Governed AI Agent Actions](https://arxiv.org/abs/2607.05397)
**Type:** author preprint
**Observed relevance:** Formalizes contract, causal record, replay context, validation invariants, and attestable execution. It is close prior art for deterministic certificates, replayability, and the separation of enforcement/effect/recordkeeping.
**Does not establish:** That recorded execution supports a negative factual claim, that sources were complete, or that a signed/valid record is true.
**Residual question:** What evidence-state certificate semantics complement execution attestations without duplicating them?

### S-013 — Temporal constraints for LLM agents

**Source:** [Enforcing Temporal Constraints for LLM Agents](https://arxiv.org/abs/2512.23738)
**Type:** author preprint
**Observed relevance:** Shows deterministic/formal enforcement of sequence-dependent agent policy and provides a strong comparator against natural-language guardrails. It supports testing a deterministic gate against prompt-only controls.
**Does not establish:** Freshness/finality of evidence, query completeness, or negative-claim adequacy.
**Residual question:** Can the Evidence-State policy be formalized with similar rigor while remaining source- and framework-neutral?

### S-014 — Audit trails for accountability

**Source:** [Audit Trails for Accountability in Large Language Models](https://arxiv.org/abs/2601.20727)
**Type:** author preprint with described reference implementation
**Observed relevance:** Defines context-rich, tamper-evident lifecycle audit trails that connect technical provenance and governance records. It is adjacent to certificate custody and traceability.
**Does not establish:** Claim truth, negative evidence sufficiency, source completeness, or that provenance alone is adequate.
**Residual question:** Which evidence-state facts belong in a durable audit trail, and which must be reevaluated at claim time?

### S-015 — Agent Audit

**Source:** [Agent Audit: A Security Analysis System for LLM Agent Applications](https://arxiv.org/abs/2603.22853)
**Type:** author preprint
**Observed relevance:** Adjacent work on analyzing agent applications and audit evidence. It is a comparator for observer independence and post-hoc analysis.
**Does not establish:** Portable empty-result semantics or a deterministic negative-claim gate.
**Residual question:** Can an external auditor reconstruct whether the original tool evidence ever justified the emitted negative claim?

### S-016 — Provenance sensitivity in agent action selection

**Source:** [Auditing Provenance Sensitivity in LLM Agent Action Selection](https://arxiv.org/abs/2607.20827)
**Type:** author preprint
**Observed relevance:** Uses matched conditions that hold task/proposition/policy fixed while changing source authority and reports that textual source-authority cues do not fully prevent untrusted evidence from influencing action. This is a useful design analogue for matched EmptyBench cases and machine-enforced metadata.
**Does not establish:** Prevalence in deployment, negative-search completeness, or performance of this project.
**Residual question:** Does a deterministic evidence gate outperform textual evidence-authority cues for claim selection?

## Official and first-party governance/product sources

### S-017 — Microsoft Agent Governance Toolkit limitations

**Source:** [Known Limitations & Design Boundaries](https://github.com/microsoft/agent-governance-toolkit/blob/main/docs/LIMITATIONS.md)
**Type:** official project documentation; first-party limitation statement
**Observed relevance:** Explicitly separates action attempts from external outcomes and identifies gaps in knowledge provenance, freshness, authorization, and source influence. It is evidence that adjacent governance systems recognize evidence/outcome limitations and a warning not to position Evidence-State I/O as general action governance.
**Does not establish:** Independent effectiveness of the toolkit, market demand, or that no other implementation addresses the gap. Roadmap statements are plans, not shipped evidence.
**Residual question:** Can Evidence-State I/O interoperate as a narrow knowledge/evidence layer rather than competing with action governance?

### S-018 — Anthropic autonomy measurement

**Source:** [Measuring AI agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy)
**Type:** official lab research report
**Observed relevance:** Screening source for the difference between observed tool activity, apparent task progress, and independently knowable real-world outcomes in deployed agent traces. It reinforces the need to state what observations can and cannot establish.
**Does not establish:** Negative-claim prevalence, source completeness, or the proposed product’s effectiveness.
**Residual question:** What evidence can a platform provider actually observe, and which state fields must remain unknown or externally attested?

### S-019 — AgentPass

**Source:** [dinpd/AgentPass](https://github.com/dinpd/AgentPass)
**Type:** public open-source project README and repository; first-party claims
**Observed relevance:** Direct adjacent implementation for action authorization, execution evidence, outcome observations, immutable evidence snapshots, and MCP gateway interception. It falsifies any broad claim that runtime evidence gates or outcome assurance are untouched territory.
**Does not establish:** Independent performance, adoption, or an evidence contract for negative search completeness. Its stated center of gravity is whether a specific tool call may execute.
**Residual question:** Is negative-claim evidence sufficiency a distinct composable layer, or should it be contributed to an existing action/evidence gateway?

### S-020 — SINT protocol

**Source:** [pshkv/sint-protocol](https://github.com/pshkv/sint-protocol)
**Type:** public open-source project README and repository; first-party claims
**Observed relevance:** Adjacent work on runtime authorization, audit, capability tokens, and bridges for physical AI. It is relevant to critical-system enforcement and protocol interoperability.
**Does not establish:** Negative-result evidence semantics, independent validation, or adoption.
**Residual question:** Would a typed evidence-state envelope complement authorization tokens at observation/claim boundaries?

### S-021 — Other outcome/evidence entrants surfaced for screening

**Sources:** [Postcept](https://postcept.com/), [Provy](https://www.provy.ai/), [TrustRail / Kaarna documentation](https://kaarna.ai/docs)
**Type:** first-party product/project materials
**Observed relevance:** Screening set for post-action verification, receipts, outcome proof, governance, and agent runtime evidence. These are competitive-adjacency checks, not independent market evidence.
**Access note:** Postcept opened during the 2026-08-21 verification pass. The Provy and Kaarna URLs could not be fetched by the available verifier and must be revalidated before any detailed claim relies on them.
**Does not establish:** Product effectiveness, adoption, or absence/presence of the proposed negative-claim semantics.
**Residual question:** Do any current or planned schemas already encode population, accessible scope, coverage lower bound, pagination/partition completion, freshness/finality, exclusions, and a deterministic negative-claim rule?

## Source-to-requirement mapping

| Design concern | Sources | Requirement impact |
|---|---|---|
| Structured tool output and versioned schema | S-001, S-003, S-007 | ESIO-P0-001, P0-009, P1-004 |
| Pagination and snapshot ambiguity | S-001, S-002 | ESIO-P0-003, P0-006, P1-001 |
| Freshness and cache scope | S-002, S-011 | ESIO-P0-002, P0-003, P0-005 |
| Error/failure separation | S-004, S-006 | ESIO-P0-003, P0-009, P1-001 |
| Untrusted annotations and metadata | S-001, S-005 | ESIO-P0-004, P1-005; source trust boundary |
| Claim-specific evidence adequacy | S-008 | Entire core thesis; ESIO-P0-002–008 |
| Uncertainty propagation comparator | S-009, S-010 | EmptyBench E1 baseline and qualification-retention study |
| Deterministic boundary enforcement | S-011, S-013 | ESIO-P0-005–007 |
| Certificates, replay, and audit custody | S-012, S-014, S-015 | ESIO-P0-008, P1-005, validation evidence package |
| Evidence authority/provenance sensitivity | S-016, S-017 | Producer trust and one-hop propagation tests |
| Action/outcome governance adjacency | S-017–S-021 | Non-goals, integration strategy, novelty falsification |

## What the current source set supports

The source set supports these bounded observations:

1. Modern agent protocols already provide structured results, versioned schemas, pagination, errors, caching, and extensibility. Evidence-State I/O must build on, not deny, those primitives.
2. Protocol completion, wire conformance, a successful endpoint response, an audit record, and a valid signature each answer different questions from whether an empty observation justifies a scoped negative claim.
3. Adjacent research and products actively address uncertainty, provenance, action authorization, execution verification, outcomes, auditability, and temporal policy. Broad “AI evidence/governance is untouched” positioning is false.
4. The bounded scan did not identify a mature, widely adopted public implementation that combines the exact proposed negative-result state taxonomy, declared coverage/access/finality conditions, deterministic negative-claim gate, and paired conformance benchmark.

Observation 4 is provisional and search-bound. It must never be restated as proof that no one is working privately or that the project is first, unique, patentable, or commercially uncontested.

## Missing evidence and search backlog

Before a publication, patent, standards, or major investment decision, expand the register with:

- database literature on certain answers, query completeness, incomplete information, closed-world assumptions, data provenance, and completeness statements;
- information-retrieval literature on corpus coverage, recall estimation, zero-result queries, and missing-not-at-random retrieval;
- observability/SIEM documentation for partial shards, timeouts, approximate totals, delayed ingestion, retention, and role-based filtering;
- formal epistemic-logic work on non-observation and negative evidence;
- standards and implementations for evidence bags, verifiable credentials, in-toto/SLSA-style attestations, and supply-chain negative claims;
- patent and non-public competitive research performed by qualified professionals if an IP decision is contemplated;
- practitioner evidence from bounded, authorized workflows.

## Refresh protocol

At each 30/60/90-day gate:

1. Re-open every core specification and repository at a pinned version or commit.
2. Search titles, abstracts, repositories, issues, and product docs using: `empty result`, `negative claim`, `absence`, `non-observation`, `query completeness`, `search coverage`, `partial result`, `accessible population`, `evidence state`, `epistemic status`, `finality`, and `coverage certificate`.
3. Record new closest work even if it weakens the project thesis.
4. Update the residual-gap statement and product differentiation.
5. If equivalent semantics and conformance tests exist, evaluate contribution/integration before parallel implementation.
6. Preserve the prior register with the frozen campaign rather than rewriting history.
