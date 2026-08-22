# Evidence-State model

The normative states are `PRESENT`, `ABSENT_WITHIN_SCOPE`, `NOT_OBSERVED`,
`PARTIAL`, `STALE`, `INACCESSIBLE`, `PENDING_WINDOW`, `FAILED`, and
`CONTRADICTORY`.

`ABSENT_WITHIN_SCOPE` is derived and policy-dependent. A producer can propose
it, but the evaluator independently checks the closed request, one required
source, authorization context, governed profile, coverage, pagination,
freshness, finality, exclusions, errors, and trust selection before permitting
the claim. All universal or absolute negative modes reject.

The transition and precedence rules are versioned in the implementation and
explained further in [Concepts and State Semantics](Concepts-and-State-Semantics).
