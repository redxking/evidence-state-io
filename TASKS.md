# Tasks

## Active

- [ ] **Draft the first implementation-owned campaign preregistration**
  - Tracked publicly as
    [issue #4](https://github.com/redxking/evidence-state-io/issues/4).
  - Prepare the exact corpus, declarative oracle, separately retained digests,
    baseline configurations, scoring, exclusions, environment matrix, stop
    conditions, and custody procedure for owner review.
  - Do not freeze or run the campaign until the owner records approval.
  - Keep implementation-owned adjudication distinct from independent review,
    external custody, external reproduction, and operational validation.

## Next

- [ ] **Approve and freeze the first implementation-owned campaign** — Begin
  only after the preregistration package above is complete and the owner records
  approval. This is not independent adjudication or external custody.
- [ ] **Run the first preregistered implementation-owned baseline** — Begin only
  after the campaign freeze above. Apply thresholds without reinterpretation
  and do not call it independent reproduction.
- [ ] **Package one read-only adapter design** — Define authority, data, identity, redaction, and verification gates before implementing any real-system access.

## Waiting On

- [ ] **Owner approval for external discovery** — Required before contacting design partners or using any real workflow data.
- [ ] **Owner-approved authority and data boundary for a real read-only adapter** — Required before handling non-synthetic workflow evidence.

## Someday

- [ ] **Specify authenticated registry and adapter evidence** — Define signing roots, source-owner and approval delegation, key rotation/revocation, monotonic registry heads, trusted time, and adapter artifact/attestation identity in a separate versioned design.
- [ ] **Define multi-source composition** — Specify overlapping populations, per-source coverage, temporal alignment, finality, conflicts, and degraded-source behavior before accepting more than one required source.
- [ ] **Evaluate an MCP interoperability profile** — Begin only after the contract survives a real read-only adapter and the frozen benchmark.

## Done

- [x] ~~Fix ESIO-DEF-001 and ship `0.6.1`~~ (2026-08-22)
  - The installed distribution shipped no EmptyBench artifacts and resolved its
    corpus and oracle from the caller's working directory, so
    `evidence-state demo` failed outside a checkout and, inside one, read the
    artifacts from wherever the caller happened to be.
  - The artifacts now ship inside the package and resolve from the imported
    module alone. All three gates run the installed CLI from outside the
    checkout with a decoy artifact directory beside it, and the acceptance gate
    requires byte-identical output from both locations.
  - `MVP-ACC-009`, `MVP-ACC-013`, and `MVP-ACC-014` were recorded as `FAIL`
    with the reproduction before the fix was written, and re-earned afterwards.
  - `v0.6.0` remains published and immutable and still carries the defect.

- [x] ~~Publish and verify the MVP research candidate on GitHub~~ (2026-08-22)
  - Remote `main` equals the accepted local commit; the remote tree carries the
    same 165 tracked blobs. CI, CodeQL, and Pages all completed `success` at the
    exact commit.
  - The Pages site is deployed and publicly reachable; every deployed asset
    digest matches a site built from an independent clean clone, and those bytes
    were exercised in a browser across all seven scenarios.
  - The wiki mirrors the canonical `wiki/` source and every required page
    renders publicly. Labels, a milestone, bounded issues, rulesets, security
    settings, Discussions, and a linked public Project are populated.
  - A clean clone of the published remote reproduced setup, tests, demo,
    benchmark, and static checks.
  - Exact evidence, procedures, and fingerprints are in
    `project/acceptance.json`. This is repository and deployment evidence only.
    It is not independent reproduction, benchmark custody, or production
    readiness.

- [x] ~~Complete the `0.6.0` local acceptance and custody record~~ (2026-08-22)
  - Implementation checkpoint
    `38f390fdae6870f10e4e5bfc4fabef8db6a7c4c3` passed `372/372`
    source tests, `372/372` installed-package tests, and `372/372` tests on
    Python 3.11.16, 3.12.14, and 3.13.0.
  - Setup, static checks, local-link checks, source/installed snapshot parity,
    dashboard regression, the 24-case seed run, 12/12 pair discrimination,
    canonical permit/rejection vectors, and verifier output passed. Source,
    installed, and all three runtime outputs were byte-identical.
  - A separate in-project read-only adversarial review found no surviving P0
    bypass. The accepted boundary remains local, synthetic, self-authored,
    unsigned, and pre-alpha.
  - This record is not a schema freeze, benchmark freeze, GitHub Release,
    independent adjudication, external reproduction, production authorization,
    or proof that profile/source assertions are true.

- [x] ~~Separate the minimum EmptyBench seed corpus and scoring oracle~~
  (2026-08-22)
  - Corpus `esio-emptybench-corpus/1.0-candidate.1` contains 12 matched
    control/fault pairs and no machine-scored expectation fields. Experimental
    role does not determine expected verdict. Oracle
    `esio-emptybench-oracle/1.0-candidate.1` is stored separately, binds the
    exact corpus digest, and is checked against a separately retained expected
    digest.
  - The 24-case local regression run discriminated 12/12 pairs with zero
    unsafe permits and zero false rejections. Tamper, swap, missing/duplicate,
    downgrade, and invalid-mutation tests are checked in.
  - This closes seed separation and P0 family coverage only. The authors still
    control the corpus and oracle; no held-out benchmark campaign has been
    frozen, preregistered, independently adjudicated, or externally reproduced.

- [x] ~~Implement exact application-selected profile governance~~ (2026-08-21)
  - Package `0.6.0` uses policy `esio-p0-safety-floor/1.0-candidate.4`, evaluator `esio-evaluator-1.0-candidate.5`, profile `esio-coverage-finality-profile/1.0-candidate.2`, registry snapshot `esio-profile-registry-snapshot/1.0-candidate.2`, trust selection `esio-profile-trust-selection/1.0-candidate.2`, and evaluation input `esio-evaluation-input/1.0-candidate.2`; schema `1.0` remains unfrozen.
  - The producer request carries an exact profile reference. The separately supplied trust selection pins the exact snapshot and exact profile reference selected by the application, closing the weak/strong sibling-profile downgrade.
  - Snapshot failures return before record content is used; profile digest, issuer, authority, time, and revocation failures return before applicability, freshness, or finality content is used.
  - Exact source, adapter, authorization, population, query, assumptions, coverage, retention, blind-interval, freshness, and finality mutations fail closed. Floating/alias/range version tokens and abbreviated Git object IDs reject.
  - Focused profile tests passed `40/40`; the pre-benchmark moving-tree source suite passed `357/357`. Final local package acceptance is recorded above.

- [x] ~~Define P0 transition, validation-error, and authorization-identifier contracts~~ (2026-08-22)
  - `esio-evidence-state-transition-model/1.0-candidate.1` defines deterministic same-lineage state transitions without claiming source truth or successor-evidence validity.
  - `esio-validation-error/1.0-candidate.1` gives public CLI failures stable machine-readable codes.
  - `esio-authorization-context-identifier/1.0-candidate.1` rejects a narrow set of credential-like identifiers; it is not a general secret detector.

- [x] ~~Adopt an open-source license and public collaboration model~~ (2026-08-22)
  - Apache License 2.0 and NOTICE are present. Governance, conduct, support, security, contribution, issue, pull-request, CI, security-analysis, dependency, Pages, release, wiki-source, and roadmap materials are version controlled.
  - Public availability does not establish a stable release, frozen protocol, production readiness, external validation, or authorization for consequential use.

- [x] ~~Implement the complete deterministic unsigned certificate~~ (2026-08-21)
  - `esio-evidence-certificate/1.0-candidate.2` binds the request, trusted context, resolved profile references, policy/evaluator/evaluation-input identities, origin, implementation assertion, evaluation and issue times, complete decision, and qualification.
  - The builder derives the decision internally. Verification reparses typed or JSON input and separates structural support, digest integrity, embedded binding, deterministic replay, expected-context/digest comparison, historical reproducibility, and current local-use eligibility.
  - The exclusive current-use boundary includes snapshot update, conservative envelope validity, policy freshness, resolved-profile expiry/revocation, and resolved-profile observation/index freshness deadlines.
  - Decimal-versus-float equivalence, boolean-as-integer confusion, invalid coverage domains, typed-object mutation, stale context, and freshness-boundary attacks were converted to regressions during review.
  - The record is explicitly unsigned and does not authenticate an issuer or authorize an action. Final local package acceptance is recorded above.

- [x] ~~Derive declared finality chronology explicitly~~ (2026-08-21)
  - A query-bound horizon and source-index closure check prevent waiting alone from upgrading an old snapshot. The governed profile now owns the exact horizon calculation.

- [x] ~~Add required and observed source accounting~~ (2026-08-21)
  - Query requirements and runtime observations are distinct, fingerprint-bound, and fail closed on missing, non-observed, mismatched, or error-bearing required-source states. P0 remains single-source.

- [x] ~~Initial local covered-versus-partial demonstration~~ (2026-08-21)
  - The schema `0.1` baseline at `b6fac87` remains historical local replay evidence. The active schema `1.0` candidate and EmptyBench remain unfrozen and are not external validation.
