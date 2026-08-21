# ADR-0005: Use Canonical Certificates and Treat Digests as Integrity Metadata

**Status:** Accepted
**Date:** 2026-08-21
**Deciders:** Project owner; architecture maintainer

## Context

Reproduction requires a stable binding among inputs, versions, verdict, and evaluation time. A hash can reveal that bytes changed relative to a trusted expected value, but it does not identify the author, prove independent custody, or prevent an attacker from replacing both payload and hash.

## Decision

Build a canonical JSON certificate and compute a versioned SHA-256 digest over its unsigned payload for P0. Name it an integrity digest, not a signature. Defer asymmetric signing, trusted timestamps, transparency logs, and independent custody until their trust and key-management models are specified and tested.

## Options Considered

### Option A: Canonical payload plus digest

| Dimension | Assessment |
|---|---|
| Reproducibility | High |
| Complexity | Low-medium |
| Authentication | None |
| Laptop fit | High |

**Pros:** Supports deterministic replay and tamper tests without external infrastructure.
**Cons:** Does not prove issuer identity or custody.

### Option B: Sign certificates in P0

| Dimension | Assessment |
|---|---|
| Reproducibility | Medium-high |
| Complexity | High |
| Authentication | Depends on key custody |
| Laptop fit | Medium |

**Pros:** Can authenticate an issuer under a defined PKI.
**Cons:** Encourages overstated assurance unless keys, rotation, revocation, and verification are designed.

### Option C: Store ordinary logs only

| Dimension | Assessment |
|---|---|
| Reproducibility | Low-medium |
| Complexity | Low |
| Binding | Weak |
| Portability | Low |

**Pros:** Familiar.
**Cons:** Logs do not define a stable evidence object or replay contract.

## Trade-off Analysis

The digest is sufficient to test deterministic packaging while keeping claims honest. Signing is valuable only after issuer identity and custody are real, not simulated by a key stored beside the evidence.

## Consequences

- Canonicalization becomes security-sensitive code with test vectors.
- Certificates include algorithm and canonicalization profile identifiers.
- Documentation must not use “signed” until a signing ADR is accepted and implemented.
- External evidence claims require independent custody beyond P0.

## Action Items

1. [ ] Publish canonicalization test vectors.
2. [ ] Add byte-level tamper and replay tests.
3. [ ] Create a separate ADR before adding signatures or remote timestamping.
