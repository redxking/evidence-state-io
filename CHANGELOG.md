# Changelog

All notable project changes should be recorded here. Dates use ISO 8601.

## Unreleased

The current working target is package `0.6.0` with unfrozen schema `1.0`.
Implementation and moving-tree review have advanced; final stable-revision
acceptance, installed-package parity, supported-runtime replay, and custody
binding remain open.

### Added

- Initial product, architecture, research, validation, operating, and implementation handoff.
- Reference evidence-state schema, deterministic gate, CLI, seed EmptyBench cases, and automated tests.
- Persistent adversarial review log and installed-command verification record.
- Schema `1.0` candidate source requirements, source observations, deterministic source-accounting assessment, and source-attributed gate reasons.
- A sixth EmptyBench seed pair that holds the empty result constant while removing the required source observation.
- Historical schema `0.1` replay fixture, pinned baseline metadata, and downgrade/relabel rejection tests.
- ADR-0007 defining schema, policy, evaluator, profile, certificate, canonicalization, and package-version boundaries.
- ADR-0008 defining requirement-owned source finality, the inclusive chronology,
  the wait-only threat, compatibility behavior, and remaining profile trust boundary.
- A seventh EmptyBench pair that holds the query, horizon, evaluation time, and
  visible zero constant while moving the reported source index one microsecond
  below versus exactly to the finality horizon.
- ADR-0009 and the governed coverage/finality profile path: exact profile
  references, a materialized registry snapshot, a separately supplied trust
  selection, deterministic resolution, applicability, retention, blind
  intervals, freshness, revocation, and profile-derived finality.
- An exact `selected_profile_reference` in
  `esio-profile-trust-selection/1.0-candidate.2`, allowing the relying
  application to select one profile rather than trusting every active profile
  in a pinned snapshot.
- ADR-0010 and `esio-evidence-certificate/1.0-candidate.2`, an unsigned
  deterministic replay record that binds the request, trusted context,
  resolved profile references, version boundaries, origin, implementation
  assertion, times, decision, qualification, and limitations.
- Independent certificate verification dimensions for structure, outer and
  embedded integrity, deterministic replay, expected context, separately
  retained expected digest, historical reproducibility, and current local use
  at an explicit relying-party time.
- Checked-in synthetic profile-registry, trust-selection, request, certificate,
  and matched benchmark vectors for the active candidate contracts.
- Apache License 2.0, NOTICE, governance, conduct, support, citation, contribution,
  security, issue, pull-request, ownership, dependency, CI, CodeQL, Pages, and
  tag-gated release infrastructure for the public pre-alpha repository.
- Versioned `esio-evidence-state-transition-model/1.0-candidate.1`,
  `esio-authorization-context-identifier/1.0-candidate.1`, and
  `esio-validation-error/1.0-candidate.1` contracts with executable tests and
  ADRs.

### Hardened

- Required safety-relevant coverage, error, schema-version, and temporal fields instead of defaulting omitted facts to benign values.
- Made the P0 coverage and error/validity safety floor non-relaxable in parsed and programmatic policy paths.
- Bounded and safely quoted claim subjects and rejected control-line and absolute-negative formulations.
- Required coherent query, observation, and evaluation timestamps.
- Rejected duplicate JSON keys, non-standard numeric constants, excessive nesting, and conflicting full-request CLI overrides with structured errors.
- Required explicit coverage lower-bound attestation for estimated or unknown populations.
- Enforced paired benchmark structure in both CLI and library paths, exact reason-oracle equality, and distinct seed/custom provenance labels.
- Replaced rounded coverage decisions with exact rational comparisons and conservative rendering so a one-unit deficit cannot be promoted to complete coverage.
- Bounded numeric tokens and semantic integers; made decimal parsing context-independent and canonical replay stable.
- Enforced strict microsecond-resolution timestamp grammar, UTC representability, exact age comparisons, DST-fold normalization, coherent observation/evaluation intervals, and source-index chronology.
- Rejected invalid UTF-8 and half-specified pagination/partition facts; normalized caller-owned sequences into immutable values and aligned programmatic construction with parsed-input safety.
- Preserved explicitly supplied falsy CLI values for validation, bounded and sanitized custom benchmark metadata, and made JSON output atomic and ASCII-safe.
- Added source-versus-installed package-file and deterministic-demo parity checks to detect stale operator installations.
- Preserved rejected 79-, 114-, 168-, and 169-test proposals and established the 171-test snapshot as the first accepted local schema/profile `0.1` freeze.
- Replaced the singular source descriptor with explicit declared requirements and runtime observations; rejected missing, malformed, duplicate, undeclared, over-limit, non-observed, inaccessible, pending, stale, failed, contradictory, unknown, population-mismatched, and error-bearing required-source states.
- Restricted the P0 candidate to exactly one declared `REQUIRED` source and reject optional or multi-source declarations because cross-source population, overlap, temporal, and finality composition are not yet specified.
- Bound the required system, locator, adapter ID/version, non-secret authorization context, observation, and aggregate coverage to the normalized query contract and its canonical fingerprint.
- Required parsed requests to identify the supported policy ID/version and exposed the evaluator version in every gate decision.
- Moved the active implementation to package `0.2.0` and schema `1.0` candidate without altering or auto-migrating the frozen local schema `0.1` baseline.
- Required observed-source index chronology through the query interval while explicitly retaining late-arrival finality as an unresolved limitation in permitted output.
- Made setup fail when project, imported-module, and installed-distribution versions disagree.
- Rejected literal placeholder values in safety-bearing subject, query, exclusion, source/adapter identity, authorization-context, population, and detection-assumption declarations.
- Added a query-bound `finality_horizon` to source requirements, made it
  non-relaxable under policy `1.0-candidate.2`, and required the reported source
  index to reach the horizon before a scoped negative can pass.
- Added exact missing/null, malformed, below/equal/above, wait-only,
  offset-normalization, fingerprint/digest, downgrade, stable-reason-order, and
  CLI finality tests without introducing an evaluator wall-clock dependency.
- Moved the active implementation to package `0.3.0` and evaluator
  `esio-evaluator-1.0-candidate.2`; preserved canonicalization profile `0.1`
  and the immutable schema `0.1` replay baseline.
- Advanced the working implementation to package `0.6.0`, policy
  `esio-p0-safety-floor/1.0-candidate.4`, evaluator
  `esio-evaluator-1.0-candidate.5`, and profile, registry-snapshot,
  trust-selection, evaluation-input, and certificate contracts
  `1.0-candidate.2`. Schema `1.0` remains unfrozen.
- Closed the weak/strong sibling-profile downgrade: a producer-selected
  profile must equal the exact application-selected reference, not merely be
  present in a trusted snapshot.
- Prevented digest-, identity-, issuer-, time-, authority-, or
  revocation-invalid snapshot/profile content from influencing resolution,
  applicability, freshness, or finality diagnostics before its trust boundary
  passes.
- Required profile issue time not to follow the snapshot as-of time and
  rejected floating labels, aliases, ranges, and abbreviated Git object IDs in
  fields that require an exact version token.
- Added direct snapshot/profile/trust failure, exact applicability mutation,
  rehash substitution, composite-digest, equivalent-offset, ordering, and
  one-microsecond retention, blind-interval, freshness, validity, and derived
  finality regression coverage.
- Derived certificate `effective_valid_until_exclusive` from the earliest
  applicable evidence validity, snapshot next update, resolved-profile expiry
  or revocation, and policy/profile observation and index freshness deadline.
- Hardened certificate parsing and replay against Decimal-versus-float
  equivalence, boolean-as-integer confusion, invalid coverage-domain values,
  nested typed-object mutation, stale context, and unsigned-certificate
  overclaiming.
- Required current local-use verification to combine intact structure and
  bindings, deterministic replay, a permitted decision, an exact separately
  supplied expected context, a separately retained expected certificate digest,
  and an explicit relying-party time within the certificate's conservative
  exclusive boundary.
- Replaced overloadable typed profile-reference equality with canonical primitive
  comparison, eliminating subclass-defined equality from the trust decision.
- Made every rejected decision render a deterministic insufficiency statement
  that preserves the ordered reason codes and never establishes the positive
  opposite claim.

### Fixed

- `ProjectController.reconcile` no longer writes the tracked control ledgers
  before a bounded verification command runs. Reconciled state and the
  `reconciled` progress event are buffered and flushed after the command has
  observed the worktree, so a task whose custody precondition is a clean tree
  can actually pass. The `dirty` value bound into acceptance evidence is still
  sampled before that write.
- The CI `quality` job now provisions the repository-local environment with
  `./scripts/setup.sh` before invoking `./scripts/check.sh`, which requires it
  in order to compare the source tree with the installed package. The
  comparison itself is unchanged.
- The hero section now clips its decorative radial pseudo-element. `.hero::after`
  is 520px wide at `right: -120px`, which made the page body scroll
  horizontally on a narrow viewport: at 375px the document scroll width was
  495px. Measured in a real browser against the deployed bytes, the document
  scroll width now equals the client width.

### Boundaries

- Initial results are local and synthetic unless explicitly recorded otherwise.
- No production-readiness, operational-effectiveness, market-validation, or standards-adoption claim is made.
- The local commit and SHA-256 digests provide recoverability and integrity comparison, not independent custody, authentication, or signature semantics.
- The registry snapshot and trust selection require application-controlled,
  producer-unwritable configuration custody. Replacing and rehashing both
  files is outside the protection offered by unsigned P0 digests.
- Profile and adapter identities, source clocks, index watermarks,
  late-arrival/reopen limits, and ingestion completeness remain declarative or
  unvalidated. Certificate replay does not upgrade those assertions.
