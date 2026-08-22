# Gateway processing pipeline

1. Strictly parse the request, registry, and trust inputs; reject duplicate keys and unsupported versions.
2. Canonicalize the bounded inputs and compute their digests.
3. Validate the application-selected snapshot and exact profile reference.
4. Materialize source accounting for exactly one required source.
5. Evaluate access, population, query binding, coverage, completion, errors, freshness, retention, blind intervals, and finality.
6. Derive the evidence state and stable reason-code set.
7. Reject absolute negatives; otherwise permit only when every required condition passes.
8. Render the qualified statement and issue the unsigned deterministic replay certificate.

No step performs a live operational action. Replaying identical canonical
inputs produces the same deterministic decision and certificate digest.
