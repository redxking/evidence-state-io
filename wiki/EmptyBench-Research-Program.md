# EmptyBench Research Program

EmptyBench is designed to isolate evidence sufficiency from visible result
content. Each matched pair asks the same question and exposes the same empty
item list while changing one or more machine-readable sufficiency facts.

## Initial fault families

- complete traversal versus unresolved continuation;
- all required partitions versus a missing partition;
- full declared access versus a filtered or mismatched boundary;
- fresh snapshot versus expired evidence;
- closed finality horizon versus pending ingestion;
- successful zero versus timeout, rate limit, query, or parse error;
- known population denominator versus unknown denominator;
- consistent evidence versus contradiction;
- zero matches versus an in-scope positive observation;
- semantically complete query versus omitted required semantics;
- stable pagination snapshot versus cross-page mutation; and
- single faults versus co-occurring faults with ordered reasons.

## Oracle discipline

The corpus, expected outcomes, scoring logic, policy, evaluator, and analysis
plan must be versioned and frozen before a baseline campaign. The oracle may not
derive its expected verdict from the implementation under test. Development
dry runs remain distinct from a frozen benchmark and from independent external
reproduction.

## Comparative conditions

The research plan compares naive tool use, prompt-only caution, always-block,
envelope-visible, and deterministic-gate conditions. Primary outcomes are the
unsupported-negative rate and valid scoped-negative retention. A system cannot
look successful merely because it refuses every negative claim.

See the full
[`docs/RESEARCH_PLAN.md`](https://github.com/redxking/evidence-state-io/blob/main/docs/RESEARCH_PLAN.md)
and
[`docs/VALIDATION_PLAN.md`](https://github.com/redxking/evidence-state-io/blob/main/docs/VALIDATION_PLAN.md).
