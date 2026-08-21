# Changelog

All notable project changes should be recorded here. Dates use ISO 8601.

## Unreleased

### Added

- Initial product, architecture, research, validation, operating, and implementation handoff.
- Reference evidence-state schema, deterministic gate, CLI, seed EmptyBench cases, and automated tests.
- Persistent adversarial review log and installed-command verification record.

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

### Boundaries

- Initial results are local and synthetic unless explicitly recorded otherwise.
- No production-readiness, operational-effectiveness, market-validation, or standards-adoption claim is made.
- The local commit and SHA-256 digests provide recoverability and integrity comparison, not independent custody, authentication, or signature semantics.
