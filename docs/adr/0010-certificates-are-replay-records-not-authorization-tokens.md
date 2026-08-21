# ADR-0010: Treat P0 Certificates as Deterministic Replay Records, Not Authorization Tokens

**Status:** Accepted for candidate implementation; not a signature or production authorization design  
**Date:** 2026-08-21  
**Deciders:** Project owner; architecture maintainer

> **Revision note:** ADR-0011 supersedes the candidate.1 verification and
> current-reliance details in this record. Commit `e8c3bea` is a rejected
> pre-acceptance checkpoint, not accepted evidence for this ADR. The current
> local candidate is candidate.2 and treats the canonical serialized record as
> immutable; the in-memory Python representation is not claimed to be deeply
> immutable and is strictly reparsed during verification.

## Context

The current `GateDecision` is a useful deterministic result but is not a
complete evidence certificate. It is freely constructible, its historical
input digest covers only the request, and it does not bind the governed profile
context, schema, policy digest, evidence origin, certificate format, issuance
metadata, or every decision field in one mutation-detecting canonical record.

A certificate builder that accepts a caller-created decision would permit a
real rejection to be repackaged as an apparent permit. A verifier that checks
only an embedded payload digest would likewise accept a changed payload when an
attacker can recompute that unkeyed digest. Finally, an embedded evaluation time
is not a trusted clock, and an unsigned artifact cannot authenticate its
issuer.

P0 needs a complete deterministic replay artifact without overstating those
properties. Live authorization, signatures, trusted time, nonce enforcement,
and operational revocation are separate protocols.

## Decision

### 1. Certificate format and ownership of evaluation

Introduce `esio-evidence-certificate/1.0-candidate.1` as an outer object with:

```json
{
  "certificate": { "...normalized payload...": "..." },
  "certificate_digest": "sha256:<digest-of-certificate-payload>"
}
```

The builder accepts a `NegativeClaimRequest`, the separately controlled
`TrustedProfileContext`, a supplied issuance time, an evidence-origin value,
and an implementation identity. It invokes `evaluate_negative_claim` itself.
It does not accept a `GateDecision` argument.

The digest covers every normalized certificate-payload field and excludes only
the outer digest. The format discriminator provides digest domain separation.
No signature, key, algorithm-negotiation, or `alg:none` field exists in this
candidate.

### 2. Complete payload binding

The normalized payload binds:

- certificate format, canonicalization profile, and digest algorithm;
- wire schema version;
- exact policy ID/version and canonical policy digest;
- exact evaluator version;
- the normalized request;
- the composite evaluation-input digest;
- the complete embedded profile registry and trust-selection context used for
  evaluation;
- exact resolved profile and registry references/digests;
- request evaluation time and separately supplied issuance time;
- a conservative effective-validity boundary;
- evidence origin;
- the complete derived decision, including permit/reject, disposition, all
  reasons, coverage assessment, source-accounting assessment, profile
  assessment, qualified statement, and every limitation; and
- package name/version, repository revision, and working-tree state.

Embedding the evaluation context makes historical replay self-contained. It
does not make that embedded context trusted. A relying party supplies its
expected context separately when it wants a trust-context comparison.

The policy digest is over the normalized policy object. The composite input
digest is over the domain-separated request, registry snapshot, and trust
selection defined by ADR-0009. Repeated copies of a value are cross-checked;
they are not independent authorities.

### 3. Evidence origin

The required origin is one of:

- `SYNTHETIC`
- `REPLAYED`
- `LAB_OBSERVED`
- `SHADOW_OBSERVED`
- `EXTERNALLY_REPRODUCED`
- `OPERATIONAL`

Origin is descriptive provenance. No origin value upgrades insufficient
evidence, authenticates an issuer, proves external reproduction, or grants
permission. The builder never infers origin from notes or environment.

### 4. Deterministic issuance metadata

`evaluated_at` comes from the normalized request. `issued_at` is an explicit
builder input, normalized to UTC, and must not precede `evaluated_at`. Neither
is a trusted timestamp.

Implementation identity is an explicit assertion rather than an ambient Git
or filesystem lookup. This preserves purity and makes dirty or unbound builds
visible. Repository revision and working-tree state are provenance fields, not
contract negotiation or authentication.

The certificate records an `effective_valid_until_exclusive` equal to the
earliest of the evidence validity declaration and the resolved profile,
registry-snapshot, and trust boundaries available to the candidate. Treating
the evidence's inclusive `valid_until` as exclusive here is deliberately
conservative. The original envelope field remains embedded for exact replay.

### 5. Verification dimensions

Verification reports independent dimensions rather than one ambiguous
`valid` flag:

1. **Structural support:** exact supported certificate, schema, policy,
   evaluator, profile, registry, trust, canonicalization, and digest contracts;
   strict field and value validation.
2. **Certificate digest integrity:** recomputation matches the embedded outer
   digest.
3. **Embedded digest integrity:** request, policy, profile, registry, trust, and
   composite input digests recompute under their declared domains.
4. **Deterministic replay:** re-evaluation of the embedded request under the
   embedded context exactly reproduces every decision field.
5. **Expected-context match:** an independently supplied relying-party context
   exactly matches the embedded registry and trust digests.
6. **Expected-certificate-digest match:** when a separately retained expected
   digest is supplied, it matches the recomputed certificate digest.
7. **Historical reproducibility:** the original evaluation remains
   reproducible under its embedded time and context.
8. **Current local reliance eligibility:** a separately supplied relying-party
   time is inside the conservative validity boundary, the original decision
   permitted, replay succeeds, and the separately supplied current context
   matches.

Absence of an expected context or expected certificate digest is reported as
unestablished, not success. Even when both match, the P0 result demonstrates
local configuration custody and mutation detection; it does not demonstrate a
cryptographically authenticated issuer.

Verification never trusts embedded `allowed`, reasons, qualification,
limitations, input digest, profile digest, registry digest, or certificate
digest without recomputation. A forged decision with a recomputed certificate
digest fails deterministic replay.

### 6. Historical replay versus current use

An expired certificate may remain exactly reproducible as a historical record.
It is never converted back into a current permit by replaying an old embedded
evaluation time. Current local reliance eligibility requires a relying-party
time supplied outside the certificate and an externally supplied expected
profile context.

A later registry snapshot does not mutate the historical certificate. P1
current-use verification will require a monotonic trusted registry head and
operational revocation semantics. Candidate.1 only compares the exact pinned
context supplied by the relying application.

Certificates are not one-time or reusable action authorizations. A future
authorization protocol requires at least audience, action, resource, nonce,
trusted time, replay state, issuer authentication, and explicit failure
semantics in a separate ADR.

### 7. Strict parsing and downgrade behavior

The existing strict JSON boundary rejects duplicate keys, nonfinite numbers,
excessive size/depth, malformed UTF-8, unknown fields, invalid identifiers,
invalid timestamp precision, and unsupported numeric forms before semantic
verification.

All version and algorithm identifiers use exact allowlists. The verifier does
not select an implementation from certificate-controlled package metadata, try
an older evaluator to recover a permit, substitute raw bytes for normalized
semantics, or fall back to another canonicalization or digest algorithm.

The certificate parser may represent a syntactically valid but digest-invalid
artifact so the verifier can report the failed integrity dimension. Profile,
registry, and trust payloads embedded inside it still receive strict structural
validation.

## Options Considered

### Serialize a supplied `GateDecision`

**Rejected.** The decision is constructible and is not an authority. The
certificate builder must own evaluation.

### Verify only the outer SHA-256 digest

**Rejected.** An attacker that changes both payload and unkeyed digest can
produce a self-consistent forgery. Semantic replay and separate expected-state
comparisons are necessary.

### Omit the profile payload and rely only on its reference

**Rejected for P0 replay.** It would make historical reproduction depend on a
mutable or unavailable registry. The embedded payload supports replay while
remaining explicitly untrusted absent external comparison.

### Treat certificates as bearer authorization tokens

**Rejected.** The candidate lacks authenticated issuers, audience, action,
nonce, trusted time, and replay storage.

### Infer issuance time, Git revision, tree state, or origin from the runtime

**Rejected.** Ambient reads make the builder impure and can hide unbound or
misclassified provenance. Inputs are explicit and certificate-bound.

## Consequences

- Permit and rejection certificates are both first-class replay artifacts.
- Every safety-bearing input and derived output is mutation-sensitive under the
  certificate digest.
- A caller cannot package a forged decision through the supported builder.
- A verifier can distinguish internal consistency, deterministic replay,
  expected-context agreement, expected-digest custody, historical
  reproducibility, and current local reliance eligibility.
- The CLI may emit certificates from `evaluate` and provide a separate
  `verify-certificate` command. Valid gate rejection remains a successful
  evaluation operation; malformed inputs remain command errors; verification
  failures are reported distinctly.
- The candidate remains unsigned and unauthenticated. Digests are integrity
  metadata, not signatures.
- Signed attestations, trusted timestamps, key purpose/rotation/revocation,
  monotonic registry heads, external custody, and action authorization remain
  outside P0.

## Acceptance Evidence

Candidate.1 is accepted only when:

1. certificate construction always performs evaluation and exposes no
   decision-injection path;
2. canonical permit and rejection bytes/digests reproduce across supported
   runtimes;
3. mutation of every request, context, version, origin, time, result,
   qualification, limitation, and implementation field changes the certificate
   digest;
4. unchanged-digest tampering fails integrity verification;
5. changed decision plus recomputed outer digest fails deterministic replay;
6. embedded-context replacement plus recomputed internal digests is reported as
   a different/untrusted context unless it matches separately supplied state;
7. unknown or downgraded certificate, schema, policy, evaluator, profile,
   registry, trust, canonicalization, and digest identifiers reject without
   fallback;
8. absent and mismatched expected context/digest states are reported
   independently;
9. expiry preserves historical replay but prevents current local reliance;
10. strict CLI parsing and exit behavior have direct tests; and
11. documentation states that the artifact is a deterministic unsigned replay
    record, not authenticated custody, a source-truth proof, or an
    authorization token.

Passing these checks completes the P0 certificate format candidate. It does not
freeze schema `1.0`, authenticate an issuer, establish external validation, or
authorize production use.
