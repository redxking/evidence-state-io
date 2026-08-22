# Architecture and Trust Boundaries

## P0 topology

The P0 implementation is a dependency-light Python modular monolith. It runs on
a laptop or VM without a network service, database, model API, or GPU.

```text
producer request                         relying application
query + source facts + profile ref       registry snapshot + trust selection
             \                           /
              strict parsing and normalization
                           |
                  staged trust resolution
                           |
          source + coverage + finality evaluation
                           |
                  deterministic claim gate
                           |
               unsigned replay certificate
```

## Security-significant sequence

1. The producer pins an exact profile reference in the normalized query.
2. The relying application supplies the registry snapshot and trust selection
   outside the request.
3. Snapshot identity, digest, issuer, and time checks pass before record content
   can influence evaluation.
4. The exact application-selected profile resolves and crosses issuer,
   authority, validity, and revocation checks before its semantics are used.
5. Runtime facts must match the governed source, adapter, population, query,
   access, detection, coverage, retention, blind-interval, freshness, and
   finality constraints.

## What the certificate is

The certificate is a self-contained, deterministic, unsigned replay record. It
separates structural support, outer and embedded integrity, deterministic
replay, expected-context comparison, expected-digest comparison, historical
reproducibility, and time-bounded current local use.

## What the certificate is not

It is not a signature, authentication token, authorization, trusted timestamp,
proof of source truth, non-repudiation mechanism, or independent custody store.
Those require separate architecture and governance decisions.

For the normative design, read the repository’s
[`docs/ARCHITECTURE.md`](https://github.com/redxking/evidence-state-io/blob/main/docs/ARCHITECTURE.md)
and architecture decision records.
