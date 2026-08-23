# Changelog

All notable project changes should be recorded here. Dates use ISO 8601.

## Unreleased

### Added

- `esio-multi-source-composition/1.0-candidate.1` and
  `evidence_state_io.composition`. Several required sources compose into one
  deterministic assessment under `CORROBORATION`, where every source claims to
  observe the same declared population.
- Corroborated coverage composes by **maximum, never by sum**. If one source
  covers 60% of a population and another covers 60% of the same population,
  the union is covered somewhere between 60% and 100%, and which one depends
  on an overlap nobody measured. Each source's bound guarantees only that
  source, so the union is guaranteed at least the best single source and
  nothing observed licenses more. Extra sources buy robustness, not coverage.
- Finality binds on the slowest required source and each source must reach
  **its own** horizon, so a laggard cannot be carried by the group. Freshness
  binds on the stalest observation, validity on the earliest boundary, and the
  weakest index is what gets reported.
- Disagreement composes to `CONTRADICTORY` and rejects. There is no majority
  rule: voting would convert a contradiction into a permit whenever the
  fabricating side brought more sources.
- Composition is order-independent and capped at four required sources.
  ADR-0015 is accepted for `CORROBORATION` only; `PARTITION` and `OPTIONAL`
  sources are deferred with reasons recorded.

- **Envelope schema `1.1`, which makes composition reachable.** Semantics
  nothing can call are a promise, not a capability. A `1.1` envelope declares
  `query.composition` and carries a per-source assessment on every required
  `source_observation`: its own `coverage`, `state`, `matched_count`,
  `observed_at`, and optionally `valid_until`. Without a per-source state and
  match count, two sources cannot be seen to disagree at all, which would gut
  the contradiction rule.
- Schema `1.0` is unchanged and provably so. It may not declare a composition
  mode or carry a per-source assessment; every new field is omitted from the
  canonical form when absent, in the envelope, the trust selection, and the
  gate decision alike. Every recorded `1.0` fingerprint, digest, and
  certificate still verifies.
- A source's declared state must be compatible with its runtime status. A
  `FAILED`, `PENDING`, or `INACCESSIBLE` source cannot be relabelled
  `ABSENT_WITHIN_SCOPE`; without that table a composed envelope could reach a
  permit by declaring in-scope absence for sources that returned nothing
  because they broke.
- `ProfileTrustSelection` gained `additional_selected_profile_references`, so
  a relying application can select one governed profile per required source.
  The singular `selected_profile_reference` remains the `1.0` form and stays
  first, and its canonical form and digest are unchanged.
- Freshness now ages a composed claim from its **stalest contributing
  observation** rather than from the envelope timestamp, so a late-sealed
  envelope cannot hide a source that was read hours earlier. With no
  composition declared this is the envelope timestamp and behaviour is
  identical.
- Thirteen `COMPOSED_*` gate reasons, each with a remedy classification. Two
  are conditions the composer alone could not express: an envelope may not
  declare a coverage floor above what its sources jointly guarantee
  (`COMPOSED_COVERAGE_OVERSTATED`), nor remain valid past the earliest
  boundary any contributing source declared (`COMPOSED_VALIDITY_OVERSTATED`).
- A composed permit says in the claim itself that corroboration did not
  accumulate coverage, and the decision's limitations state that agreement
  among sources is not independence between them.
- `evidence_state_io.composition` and `evidence_state_io.remedy` are exported
  from the package root. The remedy surface was reachable only by module path
  before, which made a headline capability effectively private.

- **`EmptyBench-P1-composed`, a benchmark for the composed path.** Unit tests
  pin the composition rules; they cannot measure whether the gate
  *discriminates*. Six pairs do: disagreement, per-source coverage, the composed
  floor, each source's own horizon, the stalest contributing observation, and
  the earliest source validity boundary. Every pair presents the same visible
  result and the same evaluation time and differs in exactly one evidence fact,
  so a pair that both permits or both rejects proves the gate is not reading the
  evidence. 12 cases, 6 of 6 pairs discriminated, zero unsafe permits.
- The expected outcome of every composed case is written by hand in
  `scripts/generate_composed_benchmark.py`, which runs the gate and refuses to
  write the artifacts when the gate disagrees. An oracle derived from whatever
  the implementation happens to do agrees with it by construction and measures
  nothing. A drift test regenerates the artifacts and fails if the packaged
  copies differ, so that refusal cannot be bypassed by editing them.
- The freshness pair is the sharpest form of the rule it tests: envelope,
  evaluation time, and visible result are identical across the pair, and the
  only difference is when one source actually looked.
- `evidence-state demo --benchmark composed` runs it. The acceptance gate runs
  it from the installed wheel outside a checkout, with decoy artifacts planted
  beside the caller, and requires byte-identical output — the same isolation
  requirement that caught ESIO-DEF-001.

- **Source attribution on composed remedies**, moving the remedy contract to
  `esio-insufficiency-remedy/1.0-candidate.3`. `RemedyItem` carries
  `source_ids`. "Every corroborating source must reach its own finality
  horizon" is not an actionable condition across four sources unless the caller
  can tell which one fell short, and the composer already knew. It is empty for
  reasons that are properties of the request as a whole. A source identifier is
  a declaration the request itself carries, not a governed threshold, so it is
  reported at `CONSTRAINT_ONLY`.

- `esio-insufficiency-remedy/1.0-candidate.1` and `evidence-state explain`.
  A rejection previously returned ordered reason codes and a deterministic
  insufficiency statement, both correct and neither actionable. A remedy states,
  for each material reason, the condition that would have to become true, and
  classifies it: await source state, obtain a fresh observation, complete
  enumeration, obtain a missing declaration, resolve source availability, use
  the governed scope, resolve governance trust, or `UNSATISFIABLE`.
- The class is computed from the evidence where the code alone does not settle
  it. `STATE_NOT_ABSENT_WITHIN_SCOPE` is `UNSATISFIABLE` when the observation
  reports `PRESENT`, because presence is not an evidence shortfall.
  `NONZERO_MATCHES`, an absolute claim, a contradictory required source, an
  exceeded retention window, and a blind interval intersecting the query are
  likewise never presented as remediable.
- Disclosure defaults closed. `CONSTRAINT_ONLY` names the failing constraint and
  carries no governed threshold; `WITH_GOVERNED_VALUES` adds the values and
  records in the record itself that returning it to the result producer supplies
  what a self-consistent fabrication would need. No remedy is produced for a
  permit, and a remedy is bound to the decision it explains by that decision's
  evaluation-input digest while staying out of the decision payload.
- `evidence-state explain` also accepts a rejection certificate directly, which
  is the artifact a relying party actually holds. The certificate already binds
  the request and trusted context, so no registry or trust selection is needed.
  Structural support, outer digest integrity, embedded binding integrity, and
  deterministic replay must all hold first: a record whose bindings do not hold
  is refused rather than explained, because conditions derived from it would be
  attributed to a claim nobody made. This moved the contract to
  `1.0-candidate.2`, adding the optional `certificate_digest` field.
- ADR-0014 records the contract and the disclosure boundary.

### Fixed

- **A composed claim could be decided but not certified.** The certificate
  pinned `wire_schema_version` to the single value `1.0`, so building a
  certificate for a schema `1.1` request raised rather than producing a record.
  A certificate is the artifact a relying party actually holds, so a capability
  that cannot be certified is half a capability. The field carries the embedded
  envelope's version, not the certificate format's, and is now checked against
  the supported set. Found by building a certificate for a composed rejection,
  not by reading the code.
- **The embedded decision rejected its own composed record.** With the version
  check fixed, the certificate's decision validator refused the `composition`
  key as an unknown field. It is now accepted but not required, and its shape
  is validated: schema, mode, composed state, bounds, timestamps, source
  identifiers, and issue codes. A certificate carrying a malformed composed
  record is refused rather than replayed around.
- The certificate format identifier stays `1.0-candidate.2` deliberately. Both
  changes are additive and widening; `decision.composition` is absent from
  every single-source certificate, so their canonical form and digests are
  unchanged, and `wire_schema_version` already distinguishes a composed record.
  Bumping the identifier would have invalidated every certificate previously
  issued while adding no information the record does not already carry. A
  verifier built before the extension still fails closed on a composed record,
  because it rejects both the unknown field and the newer wire version.
- **CodeQL `js/bad-tag-filter`, high severity.** The dashboard safe-render
  regression extracted the document's inline scripts with a case-sensitive
  pattern, so a `<SCRIPT>` region would have been silently skipped while the
  test still passed. On a three-tag sample the old pattern covered one region
  of three. Extraction is now case-insensitive, and an assertion requires the
  extracted block count to equal the number of opening `<script` tags, so
  under-extraction fails loudly. The pattern is not a sanitiser and never
  filtered untrusted input; the defect was in what the regression covered.
- Recorded that a workflow concluding `success` is not the same as zero
  security findings. `MVP-ACC-020` now separates workflow conclusions from the
  open code-scanning and Dependabot alert surface, and its procedure queries
  both.
- The end-tag half of the same pattern followed suit. An HTML end tag may
  carry ignored trailing content, so `</script foo>` and `</SCRIPT\n>` both
  close a block; the pattern now matches every form, verified against five
  end-tag shapes.

### Changed

- `pytest` is pinned to `>=9,<10` rather than widened to `>=8,<10`. Every other
  development dependency here occupies a single major band, and a range
  spanning two majors would mean a fresh `pip install .[dev]` need not receive
  the version the acceptance record describes. The gate now runs on pytest
  9.1.1, which is what a fresh install resolves to. Dependabot pull request #1
  was closed in favour of this.

## 0.6.1 - 2026-08-22

### Fixed

- **ESIO-DEF-001.** The installed distribution resolved its EmptyBench corpus
  and oracle from `Path.cwd() / "benchmarks"`, and shipped neither artifact.
  `evidence-state demo` therefore exited 2 with `MODEL_INVALID` anywhere
  outside a checkout, and inside one it read the corpus and oracle from
  whatever directory the caller happened to be in. That contradicts the
  invariant that the deterministic core must not depend on host paths,
  filesystem discovery, or the working directory, and it is the wrong custody
  story for artifacts the project says must be separately governed.
  The corpus and oracle now ship inside the package at
  `src/evidence_state_io/benchmarks/` and are resolved from the imported module
  alone. The working-directory candidate is removed, so resolution fails closed
  with an explicit message when the packaged artifacts are absent.
- The gates could not have caught ESIO-DEF-001, because
  `scripts/acceptance.sh`, `.github/workflows/ci.yml`, and
  `.github/workflows/release.yml` all ran the wheel-environment CLI from the
  repository root. Each now runs it from a directory outside the checkout with
  a decoy `benchmarks/` planted beside the caller, and the acceptance gate also
  requires byte-identical output from inside and outside the repository.
- `tests/test_seed_artifact_resolution.py` pins the behaviour directly:
  resolution lands inside the package, a decoy artifact directory in the
  caller's location is ignored, and the report is identical whatever the
  working directory is.
- `tests/test_release_evidence.py` derives its fixture tag and artifact name
  from the project version instead of a hard-coded `v0.6.0`.

### Boundaries

- `v0.6.0` is published and immutable and still carries ESIO-DEF-001. It is
  superseded by this version; its release notes say so. Nothing about this fix
  changes what a passing gate establishes.

## 0.6.0 - 2026-08-22

Package `0.6.0` with unfrozen schema `1.0`, published as the first MVP
research candidate.

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
- Reconciliation now reopens a verified task whose evidence it has just
  invalidated. A `STALE` acceptance row previously sat behind a task still
  marked `verified`, so the bounded controller would never re-establish that
  evidence and would advance to a dependent task instead. The reconciled event
  records `reopened_tasks`. A task that declares no separate
  `pass_criteria` owns every acceptance row it links, which is how externally
  verified tasks are recorded, so those are reopened too.
- The hero section now clips its decorative radial pseudo-element. `.hero::after`
  is 520px wide at `right: -120px`, which made the page body scroll
  horizontally on a narrow viewport: at 375px the document scroll width was
  495px. Measured in a real browser against the deployed bytes, the document
  scroll width now equals the client width.

### Published

- The repository, its Pages demonstration, its wiki mirror, and a linked public
  roadmap Project are published at `github.com/redxking/evidence-state-io`.
  Repository governance, security, and ruleset surfaces are populated, and a
  clean clone of the published remote reproduces setup, tests, demo, benchmark,
  and static checks. Exact evidence is recorded in `project/acceptance.json`.
  Publication establishes availability, not validation.
- The owner authorized exactly one versioned artifact on 2026-08-22: the
  `v0.6.0` tag and its MVP research-candidate release, to be created only once
  every acceptance row is `PASS`. `AGENTS.md` and `HANDOFF.md` record that
  boundary.

- The release workflow no longer requires `MVP-ACC-025` to be `PASS` before
  publishing. That row is what a release establishes — tag, notes, checksums,
  evidence manifest, SBOM, limitations, and accepted commit — so requiring it
  in advance made every release impossible. It now refuses to publish if that
  row is `FAIL`, `BLOCKED`, or `STALE`, and is recorded as `PASS` from the
  published release. Every other row must still be `PASS` at the tagged commit.

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
