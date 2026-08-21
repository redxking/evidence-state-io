# Changelog

All notable project changes should be recorded here. Dates use ISO 8601.

## Unreleased

### Added

- Initial product, architecture, research, validation, operating, and implementation handoff.
- Reference evidence-state schema, deterministic gate, CLI, seed EmptyBench cases, and automated tests.
- Persistent adversarial review log and installed-command verification record.
- Schema `1.0` candidate source requirements, source observations, deterministic source-accounting assessment, and source-attributed gate reasons.
- A sixth EmptyBench seed pair that holds the empty result constant while removing the required source observation.
- Historical schema `0.1` replay fixture, pinned baseline metadata, and downgrade/relabel rejection tests.
- ADR-0007 defining schema, policy, evaluator, profile, certificate, canonicalization, and package-version boundaries.

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

### Boundaries

- Initial results are local and synthetic unless explicitly recorded otherwise.
- No production-readiness, operational-effectiveness, market-validation, or standards-adoption claim is made.
- The local commit and SHA-256 digests provide recoverability and integrity comparison, not independent custody, authentication, or signature semantics.
