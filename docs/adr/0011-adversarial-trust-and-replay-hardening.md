# ADR-0011: Bind Relying-Party Selection and Harden Certificate Replay

**Status:** Accepted for local candidate implementation; not a schema freeze, release, or production authorization decision
**Date:** 2026-08-21
**Deciders:** Project owner; architecture maintainer

## Context

The first implementations of ADR-0009 and ADR-0010 passed their original unit
suites but failed independent adversarial review. Those reviews demonstrated
that a producer could choose a weaker profile from an otherwise trusted
snapshot, untrusted profile contents could affect diagnostics before trust was
established, and floating version labels could enter purportedly immutable
configuration. Certificate review found an incomplete current-reliance
freshness boundary, lossy numeric normalization, a typed-object validation
bypass, non-type-strict replay comparison, and invalid coverage bounds reported
as structurally supported.

Commits `f7d8bca` and `e8c3bea` are therefore retained only as reproducible
pre-acceptance checkpoints. Passing their then-current tests did not establish
acceptance of the profile or certificate contracts.

## Decision

### 1. The relying application selects one exact profile

`ProfileTrustSelection` pins `selected_profile_reference`, including the exact
registry ID, profile ID, immutable profile version, and profile digest. Every
request profile reference must equal that application-selected value before the
profile may influence a permit. The producer cannot select another active,
weaker profile that happens to be present in the same snapshot.

Duplicate profile ID/version records are a structural registry error. The
earlier semantic `PROFILE_RESOLUTION_AMBIGUOUS` reason is not part of the active
candidate.2 failure vocabulary because ambiguity never reaches evaluation.

### 2. Trust is processed in stages

The evaluator establishes snapshot identity, digest, issuer, and time validity
before consulting snapshot records. It then resolves the exact selected
reference and establishes profile digest, issuer, authority, time validity, and
revocation state before using applicability, population, retention, freshness,
blind-interval, or finality fields.

A failed earlier stage returns deterministic trust reasons without allowing
untrusted content to drive later semantic or finality diagnostics. This is a
control-flow safety boundary, not merely an ordering preference.

### 3. Version identifiers are immutable labels

Profile, snapshot, adapter, implementation, and related version fields accept
only exact immutable forms supported by their field contract. Branch names,
`latest`, ranges, wildcards, abbreviated Git revisions, and moving aliases are
rejected. Full Git commit identifiers and full SHA-256 identifiers may be used
where the relevant field admits them.

A snapshot cannot contain a profile issued after the snapshot's `as_of` time.
This chronology rule prevents a snapshot from claiming knowledge of a future
profile while preserving deterministic replay.

### 4. Current local reliance uses the complete freshness boundary

The certificate's `effective_valid_until_exclusive` is the earliest applicable
boundary derived from:

- evidence `valid_until`, treated conservatively as exclusive;
- profile expiration;
- registry snapshot next-update time;
- policy observation-age and index-age ceilings; and
- profile observation-age and index-age ceilings.

Historical replay can remain valid after this time. Current local reliance
cannot. It also requires a permitting decision, successful structural and
digest checks, deterministic replay, an externally supplied expected context,
a separately supplied relying-party time, and no known mismatch against a
separately retained expected certificate digest.

The resulting qualified statement identifies a source-declared evidence
envelope. It does not convert source assertions, profile assumptions,
watermarks, or local clocks into authenticated facts.

### 5. Verification is strict at every public boundary

Verification reparses both mappings and typed certificate objects through the
same strict public mapping boundary. The typed Python object is shallow-frozen,
not deeply immutable; nested dictionaries and lists may be mutated by a caller.
Safety therefore rests on strict reparsing, recomputation, semantic replay, and
expected-state comparison. The claim of immutability applies to retained
canonical serialized bytes under digest custody, not to the in-memory object
graph.

Accepted decimal values convert to binary floating point only when the
conversion is exact under the candidate's canonical round trip. Replay compares
canonical JSON bytes, preserving JSON type distinctions such as `true` versus
`1` and `1` versus `1.0`. Aggregate and component coverage lower bounds must be
finite and inside `[0,1]` before structural support can be true.

Changing embedded context and recomputing its unkeyed digests can produce a
self-consistent historical replay record. It remains a different context and
cannot qualify for current local reliance unless it matches the separately
supplied relying-party context. SHA-256 is mutation-detection metadata here,
not issuer authentication.

### 6. Active candidate version set

| Contract | Active identifier |
|---|---|
| Package | `0.6.0` |
| Wire schema | `1.0` candidate, unfrozen |
| Policy | `esio-p0-safety-floor/1.0-candidate.4` |
| Evaluator | `esio-evaluator-1.0-candidate.4` |
| Profile | `esio-coverage-finality-profile/1.0-candidate.2` |
| Registry snapshot | `esio-profile-registry-snapshot/1.0-candidate.2` |
| Trust selection | `esio-profile-trust-selection/1.0-candidate.2` |
| Evaluation input | `esio-evaluation-input/1.0-candidate.2` |
| Certificate | `esio-evidence-certificate/1.0-candidate.2` |
| Canonicalization | `esio-canonical-json-0.1` |
| Digest | SHA-256 |

The wire-schema literal remains `1.0` because it has never been frozen or
released. Pre-freeze safety corrections are tracked through the policy,
evaluator, profile, trust, evaluation-input, certificate, and package version
domains. No released schema compatibility is being rewritten.

The supported Python set for this candidate is closed at 3.11, 3.12, and 3.13
(`>=3.11,<3.14`). A future runtime requires an explicit compatibility change
and deterministic-vector replay before it joins the supported set.

### 7. Configuration custody and data handling remain explicit limits

P0 trusts a local registry/trust pair selected by the application. An actor
that can replace and rehash both files controls that local trust decision.
Deployment must therefore keep those files fixed and producer-unwritable.
Authenticated issuers, signed registry heads, monotonic update custody,
rollback resistance, and distributed revocation remain P1 work.

The self-contained certificate embeds the complete request and profile context
needed for replay. Candidate.2 is not data-minimized and may duplicate sensitive
fields. P0 use is limited to synthetic or explicitly approved nonsensitive
inputs. Redaction, selective disclosure, encryption, retention, and access
control require a separate design before sensitive or operational data is in
scope.

Profile/source identities, adapter versions, observations, watermarks, clock
values, retention, late-arrival bounds, reopen bounds, and population
declarations remain assertions. Candidate.2 binds and evaluates them; it does
not prove that they are true.

## Consequences

- Producer-controlled weak-profile selection and trust-failure semantic leakage
  are fail-closed in the supported path.
- Canonical replay and current local reliance are separate verification
  dimensions.
- A self-consistent artifact can still be untrusted when it differs from
  separately retained expected state.
- The implementation remains laptop- and VM-capable and requires no network,
  GPU, database, PKI, or trusted clock for deterministic P0 evaluation.
- Public release, licensing, deployment, external claims, real organizational
  data, and action authorization remain owner-controlled boundaries.
- Multi-source composition, authenticated source evidence, independent oracle
  custody, baseline evaluation, and schema freeze remain open.

## Acceptance Evidence

This hardening decision is accepted for local candidate implementation only
after all of the following are recorded against one frozen implementation
checkpoint:

1. exact selected-profile and staged-trust adversarial tests pass;
2. mutation, downgrade, numeric, typed-object, replay, context-replacement,
   expiry, and current-reliance certificate tests pass;
3. checked-in permit and rejection certificates reproduce byte-for-byte;
4. source and installed-package suites pass without an overlay masking stale
   installation;
5. Python 3.11, 3.12, and 3.13 produce identical deterministic vectors;
6. repository checks, CLI permit/rejection issuance, certificate verification,
   and EmptyBench demonstrations pass; and
7. documentation and custody records identify the exact implementation commit
   and retain every limitation above.

Meeting these conditions does not freeze schema `1.0`, establish external
validation, prove a profile or source assertion, authenticate an issuer,
authorize an action, or establish production readiness.
