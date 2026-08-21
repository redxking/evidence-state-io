# Engineering and Research Backlog

## How to use this backlog

This is the dependency-ordered product backlog, not a statement of current completion. Verify actual state in `PROJECT_STATUS.md`, `TASKS.md`, the implementation, and recorded test output before changing a row.

Priority order is P0 falsification first, then real read-only adapters, then design-partner and standards work. Items marked with an approval gate must not begin solely because their dependencies are complete.

`TASKS.md` is the short current work queue. It activates a bounded slice of this
backlog but does not prove that slice is complete. Stage 0 and the first local
schema/gate hardening baseline are implemented and locally tested. The active
queue now maps to the remaining portions of P0-02/P0-03 (required-versus-observed
sources), P0-04 (explicit finality), and P0-08 (complete certificate/version
binding). Its explicit prohibition on real adapters keeps Stage 3 blocked until
the P0 falsification gate is frozen and approved.

### Status vocabulary

`PROPOSED`, `SPECIFIED`, `IMPLEMENTED`, `TESTED`, `BENCHMARKED`, `EXTERNALLY_REPRODUCED`, `BLOCKED`, or `STOPPED`. Use the most advanced state supported by evidence; do not infer a later state.

### Common definition of done

Every engineering item must satisfy all applicable conditions:

- requirement and failure behavior are explicit;
- implementation preserves the architecture and accepted ADRs;
- positive, negative, boundary, malformed-input, and deterministic tests exist;
- every disqualifying fault has a matched supported control;
- `./scripts/check.sh`, `./scripts/test.sh`, and the core demo pass in a clean Python 3.11+ environment;
- documentation and fixtures match the implemented interface;
- evidence origin and limitations are recorded;
- no external action or stronger claim was made without owner approval.

## Stage 0 — runnable repository

| ID | Item | Depends on | Item-specific definition of done | Gate |
|---|---|---|---|---|
| S0-01 | Align packaging contract | None | `pyproject.toml` requires Python 3.11+, exposes `evidence-state`, declares no unapproved license, and installs in a fresh local virtual environment. | Owner approval for license only |
| S0-02 | Establish domain-neutral package boundaries | S0-01 | Imports separate model/evaluator/gate/certificate/CLI concerns; core modules perform no network or filesystem I/O. | None |
| S0-03 | Add local operator scripts | S0-01 | Setup is idempotent, tests avoid destructive cleanup, demo needs no network, and scripts pass `bash -n`. | None |
| S0-04 | Add CI baseline | S0-01, S0-03 | CI installs `.[dev]`, compiles the package, runs pytest and CLI help on supported Python versions, and validates shell/Compose syntax. | None |
| S0-05 | Freeze claims and security boundaries | None | README, PRD, architecture, security model, and handoff consistently say pre-alpha/local/synthetic and no license is selected. | Owner for external wording |

## Stage 1 — P0 contract and evaluator

| ID | Item | Depends on | Item-specific definition of done | Gate |
|---|---|---|---|---|
| P0-01 | Freeze schema `0.1` evidence states | S0-02 | All nine initial states round-trip exactly; unsupported states/major versions fail closed; normative meanings have tests. | ADR for semantic changes |
| P0-02 | Validate query scope and access boundary | P0-01 | Required target, predicate, authorization boundary, interval, exclusions, and source identifiers distinguish null/unknown/empty; credential-like values are rejected where prohibited. | None |
| P0-03 | Validate coverage and completion facts | P0-01 | Coverage is finite and bounded; pages/partitions/continuations/errors cannot contradict each other; declared lower bounds cannot exceed computed bounds. | None |
| P0-04 | Implement freshness and finality evaluation | P0-02, P0-03 | Supplied evaluation time controls results; below/equal/above boundary tests cover freshness and finality; no wall-clock read occurs in the evaluator. | None |
| P0-05 | Implement fail-closed coverage evaluator | P0-02, P0-03, P0-04 | Missing, partial, stale, inaccessible, pending, failed, or contradictory inputs retain stable reason codes; all reasons are preserved under aggregate precedence. | ADR for precedence changes |
| P0-06 | Implement negative-claim gate | P0-05 | Absolute negatives always reject; only valid `ABSENT_WITHIN_SCOPE` permits a generated scoped negative; `PRESENT` and every indeterminate state reject. | None |
| P0-07 | Implement qualified renderer | P0-06 | Permitted output names scope, authorization boundary, interval, sources, and material exclusions; rejected output states insufficiency without asserting the positive opposite. | Claims review |
| P0-08 | Implement canonical certificate | P0-05, P0-06 | Stable payload and SHA-256 integrity digest reproduce byte-for-byte; one-field mutation changes the digest; output calls it a digest, not a signature. | ADR before signing |
| P0-09 | Implement JSON CLI | P0-06, P0-08 | Approved `evaluate` and `demo` commands work; JSON goes to stdout, diagnostics to stderr; evaluation rejection is distinct from process failure. | None |

## Stage 2 — EmptyBench and falsification gate

| ID | Item | Depends on | Item-specific definition of done | Gate |
|---|---|---|---|---|
| EB-01 | Freeze covered-zero control | P0-09 | The canonical complete/current/final empty case produces `PERMIT_SCOPED_NEGATIVE`; fixture, oracle, and digest are versioned. | Freeze before baseline |
| EB-02 | Add matched missing-source case | EB-01 | Visible result is unchanged; one required source is absent; oracle requires rejection with stable reason. | None |
| EB-03 | Add pagination and partition cases | EB-01 | Incomplete page, continuation token, missing partition, and matched controls are independently represented and rejected. | None |
| EB-04 | Add freshness and finality cases | EB-01 | Stale and pending-window pairs include exact boundary cases and supplied evaluation times. | None |
| EB-05 | Add access and failure cases | EB-01 | Permission boundary, inaccessible source, timeout, interruption, parsing/query error, and matched controls are covered. | None |
| EB-06 | Add contradiction cases | EB-01 | Mutually inconsistent required observations cannot be collapsed into absence; reason codes identify the sources. | None |
| EB-07 | Build independent scoring oracle | EB-02–EB-06 | Expected results are stored separately from generated output; tests detect if the implementation is substituted as ground truth. | Evidence review |
| EB-08 | Add naive and conservative baselines | EB-07 | Empty-result and always-abstain baselines run on identical cases; configurations are frozen. | Freeze before measurement |
| EB-09 | Run frozen P0 campaign | EB-08 | Runtime versions, inputs, outputs, exclusions, and metrics are captured reproducibly; no threshold or oracle changes occur after results without a new campaign version. | Owner approves freeze |
| GATE-01 | Decide continue, narrow, or stop | EB-09 | Compare results with every README/PRD threshold and record the decision without reinterpretation. | Owner decision |

## Stage 3 — P1 adapters and registry

These items begin only if `GATE-01` authorizes continuation.

| ID | Item | Depends on | Item-specific definition of done | Gate |
|---|---|---|---|---|
| P1-01 | Coverage profile schema and local registry | GATE-01 | Profiles version ownership, population, fields, retention, blind intervals, freshness, access, detection assumptions, and effective dates; drift or expiry blocks absence. | Owner for governance policy |
| P1-02 | Read-only SQL/Postgres adapter | P1-01 | Uses least-privilege read-only access; maps snapshots, row count, interval, pagination, timeout, and permission failures; replay tests cover all paths. | Approval for any real DB |
| P1-03 | Read-only search adapter | P1-01 | OpenSearch/Elasticsearch mapping covers shards/partitions, total-hit relation, timeouts, truncation, and authorization filters; tests use synthetic or recorded authorized data. | Approval for any real search service |
| P1-04 | Read-only GitHub Search adapter | P1-01 | Rate limits, pagination cap, query qualifiers, accessible repositories, and incomplete results are explicit; no empty result self-declares absence. | Network/account approval |
| P1-05 | Multi-source composition | P1-01, one adapter | Overlap cannot inflate coverage; unknown overlap is conservative; contradictions remain explicit. | ADR for composition semantics |
| P1-06 | MCP and agent-runtime wrappers | P0-09 | Structured envelope survives handoff; stripped/mutated metadata rejects; protocol completion is not evidence completion. | Dependency review |
| P1-07 | Optional certificate signing profile | P0-08, P1-01 | Issuer trust, keys, rotation, revocation, and verification are specified; signatures never upgrade an insufficient verdict. | Owner/security approval |

## Stage 4 — authorized shadow evaluation

| ID | Item | Depends on | Item-specific definition of done | Gate |
|---|---|---|---|---|
| R1-01 | Complete ten qualified discovery interviews | GATE-01 | Notes separate direct evidence from interpretation; at least three identify a costly false-absence pattern and a testable workflow. | Approval before contact |
| R1-02 | Select one bounded workflow | R1-01, one P1 adapter | Scope, authority, data classification, access, retention, and non-interference rules are written and approved. | Explicit owner/partner approval |
| R1-03 | Run read-only shadow evaluation | R1-02 | Gateway observes without controlling decisions; incidents and false blocks are reviewed; sensitive data stays within approved custody. | Explicit owner/partner approval |
| R1-04 | Independent reproduction package | EB-09 | A party not involved in implementation reproduces the frozen synthetic campaign and reports deviations. | External coordination approval |
| GATE-02 | Decide whether to pursue product/protocol work | R1-03, R1-04 | Decision compares measured value, integration burden, buyer commitment, false-block cost, security, and unresolved validity risks. | Owner decision |

## Cross-cutting security and quality work

| ID | Item | Depends on | Item-specific definition of done | Gate |
|---|---|---|---|---|
| Q-01 | Malformed and oversized input suite | P0-01 | Unknown fields, duplicate IDs, non-finite numbers, deep nesting, oversized strings/arrays, and path-like values fail predictably without secret leakage. | None |
| Q-02 | Property and mutation tests | P0-05, P0-08 | Reordering invariants hold; weakening one required condition never upgrades the decision; evidence mutation changes the digest. | None |
| Q-03 | Reproducibility matrix | S0-04, P0-09 | Supported Python versions produce semantically identical output and documented canonical bytes. | None |
| Q-04 | Dependency and supply-chain review | S0-01 | Direct dependencies are justified; CI permissions are minimal; release artifacts are not published automatically. | Owner before release |
| Q-05 | Optional lab adapter tests | P1-02 or P1-03 | Loopback Compose lab injects bounded faults; tests map transport behavior to evidence states without touching external systems. | Local container start only |

## Kill conditions

Stop or materially narrow the project if evidence shows any of the following:

1. The baseline does not produce a meaningful unsupported-negative problem on a preregistered corpus.
2. The gate cannot reach the reduction target without failing supported-negative retention.
3. Coverage profiles require unverifiable assertions so broad that the verdict adds no useful assurance.
4. Strong existing tools already provide equivalent portable contracts and behavior with lower integration burden.
5. Qualified buyers accept current caveats/manual review and will not allocate budget or engineering time.
6. A real adapter cannot obtain materially better coverage facts than an ordinary empty response.
7. The benchmark can be passed through universal abstention, oracle leakage, or proxy gaming that cannot be corrected cleanly.

Kill-condition evidence is a successful research result and must not be hidden by changing thresholds after measurement.
