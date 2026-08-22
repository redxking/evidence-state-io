# ADR-0013: Harden typed Python trust selection and current-reliance custody

**Status:** Accepted for the unfrozen `0.6.0` candidate; final custody pending

**Date:** 2026-08-22

## Context

The candidate exposes both strict JSON/CLI paths and typed Python APIs. A final
adversarial review showed that these paths did not have identical trust
semantics. `evaluate_profile_governance` compared two
`CoverageProfileReference` objects through overloadable Python equality. A
caller-created subclass could return a false equality result and make a weak
profile reference appear equal to the exact profile selected by the relying
application. Strictly parsed JSON did not permit this construction, and
certificate verification reparsed the forged result and rejected replay, but
the direct evaluator and builder could transiently emit a permit.

The same review demonstrated a separate custody ambiguity. Current-local-use
eligibility could be `true` when expected context and relying-party time were
supplied but no separately retained expected certificate digest existed. A
caller able to alter descriptive origin content and recompute the unsigned
outer digest could therefore retain a positive current-local-use field. The
report still denied issuer authentication and authorization, but the field was
too easy to misread as custody evidence.

The PRD also requires rejection output to state that evidence is insufficient
and to name the material reasons without asserting the positive opposite. The
candidate returned `qualified_claim: null` for a rejection even though stable
structured reasons were present.

## Decision

1. Exact profile selection compares the four canonical primitive fields
   directly. Digest equality uses constant-time comparison. Model-level
   `__eq__` and `__ne__` dispatch are outside the trust decision.
2. The hostile typed-subclass construction is a permanent regression case.
   Direct profile evaluation must return
   `PROFILE_TRUST_SELECTION_MISMATCH`, and downstream gate/build behavior must
   remain fail closed.
3. Current-local-reliance eligibility is evaluated only when the caller
   supplies all three external prerequisites: expected context, a separately
   retained expected certificate digest, and explicit relying-party time.
   Omission leaves the result unestablished (`null`); mismatch or an ineligible
   replay returns `false`.
4. Every rejection includes a deterministic insufficiency statement listing
   its ordered reason codes and stating that rejection does not establish the
   positive opposite.
5. Because the rendered decision bytes change, the evaluator advances from
   `esio-evaluator-1.0-candidate.4` to
   `esio-evaluator-1.0-candidate.5`. The policy, evaluation-input,
   certificate-format, schema, canonicalization, and digest contracts do not
   change. Permit and rejection certificate vectors and their expected digests
   are regenerated under the new evaluator identifier.

## Consequences

- Direct typed API and strict JSON profile-selection behavior now converge for
  the reproduced equality attack.
- A positive current-local-reliance field carries evidence of exact artifact
  comparison as well as configuration comparison and time eligibility. It is
  still local comparison evidence, not issuer authentication, source truth,
  non-repudiation, or action authorization.
- Rejection output is directly usable by downstream systems without requiring
  them to invent natural-language meaning from reason codes. Consumers must
  still preserve the structured reason list as authoritative.
- Existing candidate.4 decision and certificate vectors remain historical
  development artifacts only. No active runtime fallback is introduced.
- The repair does not claim to make arbitrary hostile Python objects safe in
  general. Public boundary models remain validated types, JSON remains the
  portable interchange boundary, and future reviews should continue testing
  subclassing, mutation, and overloaded-protocol behavior.

## Verification obligations

- Reproduce the equality-overload attack against the direct typed API and
  demonstrate exact-selection rejection.
- Demonstrate that omitted expected digest leaves current-local reliance
  unestablished, while a matching retained digest permits evaluation of that
  dimension and a mismatch blocks it.
- Demonstrate that every rejection statement contains its ordered material
  reason codes and cannot be read as proof of the positive opposite.
- Reproduce permit and rejection vectors byte-for-byte on Python 3.11, 3.12,
  and 3.13 and through the installed command before recording local custody.

## Claim boundary

This decision closes reproduced local contract defects. It does not establish
authenticated custody, trusted time, source/profile truth, external
interoperability, operational effectiveness, or production readiness.
