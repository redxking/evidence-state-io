# Preregistration: comparative campaign R1

**Status:** Frozen. Committed before any run.
**Registered:** 2026-08-23
**Authorization:** Project owner, 2026-08-23, including calls to a model API.
**Closes:** open issue #4.

A campaign whose design can move after the results are seen measures the
designer, not the system. Everything below — corpus, configurations, metrics,
sample size, analysis, success thresholds, exclusions, and the conditions under
which the result is negative — is fixed by this document and by the commit that
introduces it. Any change after the first run is an amendment, recorded as one,
with the original preserved.

## The question

Does routing a negative claim through the gate reduce unsupported negative
conclusions, without destroying the useful ones?

The second half is not decoration. Refusing every negative drives unsupported
negatives to zero and is worthless, so the campaign measures both and reports
them together or not at all.

## Corpus

The two packaged benchmarks, in full and unmodified:

- `EmptyBench-P0-seed` — 24 cases, 12 pairs, single-source evidence sufficiency
- `EmptyBench-P1-composed` — 12 cases, 6 pairs, multi-source composition

**36 cases, 18 pairs.** Each pair holds the visible result constant and varies
only the evidence, which is what makes it a discrimination test rather than a
guessing game.

Corpus digests are recorded in the result file. A run against any other corpus
is a different campaign.

## Configurations

Each configuration answers one question per case: **may this be reported as
absent?**

| Id | What it sees | Who decides |
|---|---|---|
| `prompt-only` | The visible result only: the match count and the shape of what came back, with no coverage evidence. Instructed to be careful about absence. | A model |
| `always-block` | Nothing. Never asserts a negative. | Nobody |
| `envelope-visible` | The complete evidence envelope, including coverage, completeness, faults, and index state. | A model |
| `gated` | The same envelope. | The evaluator |

`prompt-only` is the honest representation of the status quo: an agent sees an
empty tool result and decides. `always-block` exists so that a good
unsupported-negative number cannot be mistaken for a good result — it will score
perfectly on one metric and worst possible on the other. `envelope-visible`
separates two different claims: that the *evidence* helps, and that *deciding
deterministically* helps. If `envelope-visible` matches `gated`, then the
envelope was the contribution and the evaluator was not.

## Metrics

Both are computed per configuration over the whole corpus.

**Unsupported-negative rate** — of the cases whose evidence does not support
absence, the fraction reported as absent. Lower is better; 0 is perfect.

**Valid-negative retention** — of the cases whose evidence does support absence,
the fraction reported as absent. Higher is better; 1 is perfect.

Ground truth is the packaged oracle's `expected_allowed`.

## Success thresholds

Fixed here, before any run.

**Primary.** Relative reduction in unsupported-negative rate of `gated` against
`prompt-only` is at least **80%**. This is the threshold already stated in the
PRD and it is not moved to fit a result.

**Secondary.** `gated` valid-negative retention is not more than **0.05** below
`prompt-only` retention. A reduction bought by refusing everything fails this
and is reported as a failure.

**Both must hold.** Either alone is not a pass.

## Sample size and sampling

- **5 trials per case per model configuration.** 36 cases × 5 = 180 calls for
  each of `prompt-only` and `envelope-visible`; 360 model calls in total.
- Temperature **0**. The exact model identifier is recorded in the result file
  and is part of the result: a different model is a different campaign.
- A configuration's answer for a case is the **majority across its 5 trials**,
  with ties resolved as "reported absent" — the unfavourable direction for the
  hypothesis, so a tie cannot help the result being tested.
- The two deterministic configurations run once per case; repeating them would
  produce identical answers and inflate nothing.

## Analysis

- Point estimates with **Wilson score 95% intervals** for both metrics.
- The primary comparison is a relative reduction with its interval.
- Per-pair discrimination is reported alongside, since a configuration can post
  respectable aggregate numbers while failing to distinguish any pair.
- Every prompt and every response is written to the run log. The result file
  carries the corpus digests, oracle digests, model identifier, configuration
  identifiers, and the count of excluded trials.

## Exclusions, fixed in advance

A trial is excluded only for:

1. A transport or API error after 3 retries.
2. A response that does not parse into the required binary answer after one
   re-ask with the same prompt.

Exclusions are counted and reported. **If more than 10% of a configuration's
trials are excluded, that configuration's result is reported as
indeterminate**, not as a number with a caveat.

No case is excluded for being difficult, surprising, or unfavourable.

## What this campaign cannot establish

Stated now rather than discovered later.

**The oracle is not independent of the gate.** It is a hand-written claim about
what each case's evidence supports, and it was verified against the gate before
being frozen. `gated` therefore agrees with it by construction and will score
close to perfectly. That is not evidence that the gate is correct. What the
campaign measures is **how far the baselines fall from that standard** — and in
particular whether a model given the same evidence reaches the same answer. The
`gated` column is a reference line, not a finding.

**The corpus is synthetic.** Every case is a mutation of a locally authored
base request, and no source in it is real. Results transfer to real systems only
to the extent the fault classes are representative, which this campaign does not
establish.

**It measures declared evidence, not truth.** Nothing here authenticates a
source. A producer that fabricates a coverage figure consistently passes every
configuration including `gated`, and the campaign cannot see it.

**It is one model, at one temperature, at one point in time.** It is not a claim
about models in general, and a different model is a different campaign.

**A pass is not operational effectiveness, external validation, or market
demand.** It is a measurement on a synthetic corpus under a preregistered
protocol, and it will be described as exactly that.

## Publication

The result is published in this repository whatever it shows, including a
negative result, an indeterminate result, or a result that fails either
threshold. That commitment is part of the preregistration, and a campaign that
is only published when favourable measures nothing.
