# Concepts and State Semantics

## The core distinction

“No matches were returned” is an observation. “The subject is absent” is a
claim. The latter requires evidence that the search was applicable, complete,
fresh, authorized, final, and free of material failure for its declared scope.

## Evidence states

| State | Meaning at the gateway boundary |
|---|---|
| `PRESENT` | One or more relevant observations exist. |
| `ABSENT_WITHIN_SCOPE` | Zero matches under a declared scope that claims complete evidence. This state is necessary but not sufficient for a permit. |
| `NOT_OBSERVED` | No usable observation was made. |
| `PARTIAL` | Some required population, page, partition, field, or source remains unobserved. |
| `STALE` | The observation is outside a required freshness boundary. |
| `INACCESSIBLE` | Required evidence was outside the effective access boundary. |
| `PENDING_WINDOW` | Ingestion, correction, or finality remains open. |
| `FAILED` | A required operation failed. |
| `CONTRADICTORY` | Material observations cannot be reconciled under the active contract. |

Only `ABSENT_WITHIN_SCOPE` can enter the permit path. It still must pass source
accounting, coverage, profile, chronology, freshness, finality, error, and
policy checks. Every other state fails closed.

## Claim strength

The candidate can emit a bounded statement such as “zero observed matches
within the declared query scope.” It does not emit universal or metaphysical
absence. A rejection says the evidence is insufficient and names the material
reasons; it does not assert that the positive opposite is true.

## Why deterministic evaluation matters

Language models may explain a decision, but they do not decide whether the
evidence is sufficient. Identical normalized inputs under the same exact
contracts produce identical decision and certificate bytes. That supports
replay and falsification; it does not authenticate the inputs.
