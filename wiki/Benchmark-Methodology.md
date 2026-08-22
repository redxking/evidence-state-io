# Benchmark methodology

EmptyBench uses matched pairs with the same visible zero-result observation.
The control has sufficient evidence; the paired fault changes one evidence
condition such as access, pagination, freshness, finality, failure, or
contradiction. Correctness is reported before performance.

The versioned corpus is separated from the declarative oracle and bound by
digests. The current 24-case, 12-pair seed is implementation-owned; passing it
is bounded regression evidence, not a frozen held-out campaign or independent
adjudication. See [EmptyBench Research Program](EmptyBench-Research-Program)
and the [validation plan](https://github.com/redxking/evidence-state-io/blob/main/docs/VALIDATION_PLAN.md).
