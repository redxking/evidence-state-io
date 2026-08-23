# Quickstart

Your agent searched, got nothing back, and told someone it does not exist.

An empty tool result is not evidence of absence. It might mean the thing is not
there. It might mean the search timed out, or was rate limited, or stopped at
page one of fifty, or that the index has not caught up yet. The result looks
identical in every case.

This turns that into a checkable claim: either a statement of absence that names
the scope it is conditional on, or a precise account of what is missing.

Five minutes, start to finish.

## Install

```bash
pip install evidence-state-io
```

Python 3.11, 3.12, or 3.13. No runtime dependencies, no network, no
configuration, no services.

## Thirty seconds: see it discriminate

```bash
evidence-state demo --all --pretty
```

Twenty-four cases in twelve pairs. Each pair shows the *same* empty result twice
— once where the evidence supports absence and once where it does not — and the
gate has to tell them apart. `pairs_discriminated: 12` means it did.

```bash
evidence-state demo --benchmark composed --all --pretty
```

Six more pairs for claims resting on several sources at once, including the one
a majority vote gets wrong: three sources agreeing that something is absent do
not outvote a fourth that saw it.

## Two minutes: a real claim about a real system

```bash
python3 examples/quickstart.py
```

It reads a recorded GitHub search that returned zero results, describes the
scope the claim would be about, and asks whether that supports "no such
repository exists." Add `--live` to make the call yourself; the answer is the
same, because what the adapter concludes about coverage does not depend on where
the bytes came from.

The claim is refused, and the last reason is the interesting one:

```
[OBTAIN_MISSING_DECLARATION]
  the source must report the time its index was current as of
```

GitHub publishes no watermark saying when its index last ingested. So nothing
can distinguish *the index does not contain it* from *it does not exist*. That
is a property of the source, not a gap in the request, and an adapter that
invented a timestamp there would be fabricating the one fact that separates
those two statements.

**A rejection does not mean the thing exists.** It means absence was not
established. That is a different, and more honest, thing to say.

## Two minutes: wire it into your agent

```jsonc
// In your MCP client's server configuration
{
  "mcpServers": {
    "evidence-state": { "command": "evidence-state-mcp" }
  }
}
```

The server is a local stdio process. It opens no socket, reads no clock, and
makes no network call.

Three tools:

| Tool | Use it when |
|---|---|
| `describe_evidence_requirements` | You are about to claim absence and want to know what evidence that needs. Start here. |
| `assess_negative_claim` | You have the evidence and want to know whether it supports the claim. |
| `explain_rejection` | It said no and you want to know what would change that. |

The conditions in a remedy describe the world and the evidence. They never name
a request field to edit — editing a request until it produces a permit is
fabrication, not remediation.

## Building the evidence

The adapter does this for GitHub search. For any other source, describe what you
did:

```python
from evidence_state_io import EvidenceBuilder, SourceReading

request = (
    EvidenceBuilder(
        target="customer support tickets",
        predicate="subject contains 'data breach'",
        authorization_boundary="tickets visible to the support-read role",
        authorization_context_id="support-read",
        time_start=window_start,
        time_end=window_end,
        exclusions=("deleted tickets", "tickets in draft"),
    )
    .require_source(
        source_id="helpdesk",
        system="helpdesk-api",
        locator="tickets/search",
        adapter_id="helpdesk-adapter",
        adapter_version="1.0.0",
        accessible_population="tickets-visible-to-support-read",
        detection_assumptions=("a ticket is searchable once indexed",),
        finality_horizon=horizon,
    )
    .record(
        SourceReading(
            source_id="helpdesk",
            matched_count=0,
            examined_units=1_284,
            population_basis=PopulationBasis.EXACT,
            population_units=1_284,
            pagination_complete=True,
            continuation_token_present=False,
            partitions_complete=True,
            timed_out=False,
            interrupted=False,
            permission_limited=True,
            observed_at=read_at,
            index_as_of=index_time,
        )
    )
    .request(subject="tickets mentioning a data breach", evaluated_at=now)
)
```

None of the completeness fields has a default. That is deliberate: a builder
whose defaults were all optimistic would manufacture exactly the coverage this
is meant to refuse. If you do not know whether your pagination drained, you have
to write down that you do not know.

You never declare the evidence state. It is derived from the facts, and the
derivation cannot be talked into reaching in-scope absence from facts that do
not support it.

## What a permit does and does not establish

A permit says: within this declared scope, over this interval, under this
authorization boundary, with coverage at least this good, zero matches were
observed.

It does not say the thing does not exist. It does not say the source told the
truth — nothing here authenticates a source, and a producer that fabricates a
coverage figure consistently is not detected. It does not authorize any action.

Those limits are printed in the decision itself, every time.

## Where to go next

- [README.md](README.md) — what the system is and what it deliberately is not
- [docs/CLAIMS_AND_BOUNDARIES.md](docs/CLAIMS_AND_BOUNDARIES.md) — what may and may not be claimed about it
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how it fits together
- [docs/MVP_PLAN.md](docs/MVP_PLAN.md) — what is built, what is next
