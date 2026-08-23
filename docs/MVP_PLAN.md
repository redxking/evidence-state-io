# Plan: from correct library to real MVP

**Date:** 2026-08-22
**Status:** Accepted and in execution. The three authorizations this plan
asked for were granted by the project owner on 2026-08-22 and are recorded
below.

## Authorization record, 2026-08-22

The owner extended the original mandate on three specific points. Everything
the original mandate withholds and that is not listed here remains withheld.

| Item | Decision | Scope of what was authorized |
|---|---|---|
| Package registry | **Authorized** | Publish to TestPyPI first, verify a clean install from it, then publish to PyPI. |
| Live source access | **Authorized** | Read-only calls to GitHub's public search API. Public data only, no writes, no credentials beyond a rate-limit token. |
| Comparative campaign | **Authorized** | The campaign may call an LLM API, so prompt-only and envelope-visible baselines can be measured. |

Still withheld, and not requested: registering or purchasing a domain,
incurring material cost, using sensitive, customer, proprietary, classified,
CUI, export-controlled or operational data, faulting a live operational system,
adding a write-capable adapter, contacting people or organizations, announcing
outside the repository, and claiming production readiness, certification,
independent validation, authenticated evidence, source truth, market demand, or
operational effectiveness.

Credentials for the registry and the LLM API stay with the owner and are set in
the owner's own environment. They are not handled here and never appear in the
repository, in a commit, or in a session transcript.

## Where the project actually is

What exists is good and is not a product.

`evidence-state-io 0.7.0` is a deterministic negative-claim gateway with 521
tests, two packaged benchmarks, replay certificates, insufficiency remedies,
governed coverage/finality profiles, multi-source composition, a clean local
acceptance gate, a published repository, wiki, and Pages site. The engineering
is sound. Six defects and two security findings were caught by running the
mechanisms rather than reading them.

None of that is adoption. The honest summary of the product position:

| Question | Answer today |
|---|---|
| Can someone install it? | Only `pip install git+…` from a checkout |
| Can an agent call it? | No. There is no integration surface |
| Can someone produce an envelope without hand-writing JSON? | No |
| Has it ever run against a real source? | No |
| Is there evidence it reduces unsupported negatives? | No |
| Has anyone outside the project used it? | No |

The gap between here and an MVP is not more correctness. It is that nothing
can *call* this yet, nothing *produces* input for it, and nothing shows it
*works*.

## What "MVP" means for this specific product

The thesis is that an empty tool result is not evidence of absence. The person
who feels that pain is someone running LLM agents against real systems whose
agent confidently reported "no results found, so it does not exist" and was
wrong in a way that mattered.

That tells us exactly what the minimum viable product is:

1. **An agent can route a negative claim through the gate without code
   changes.** Today that means an MCP server. The product's own description —
   "a deterministic runtime between agents and tools" — is an MCP server's job
   description. This is the wedge.
2. **Producing the evidence is not harder than the problem it solves.** A
   hand-authored envelope is roughly a hundred lines of JSON. Nobody will write
   one. There must be a builder API and at least one adapter that produces a
   real envelope from a real query.
3. **There is evidence the thing works.** The project's own PRD sets the bar:
   at least an 80% relative reduction in unsupported negative conclusions
   against a baseline. Until that is measured, every claim is "we built a
   thing," not "this helps."

Anything beyond those three is not MVP.

## Phase 1 — Make it callable (no new authorization needed)

Everything in this phase runs offline, uses no real data, and stays inside the
current mandate. I can do all of it now.

### 1.1 MCP server

Ship `evidence-state-mcp` in the package: a stdio MCP server exposing

- `assess_negative_claim` — envelope in, decision out, with the qualified claim
  or the insufficiency statement
- `explain_rejection` — the remedy for a rejection, including which source fell
  short on a composed claim
- `describe_evidence_requirements` — what an envelope must contain for a claim
  in a given scope to be assessable at all

The server is a thin transport over the existing pure evaluator. It holds no
state, opens no sockets outward, and consults no clock: `evaluated_at` stays a
required input. Determinism is a property of the library and must survive the
wrapper, so the acceptance gate will replay a fixed request through the server
and require byte-identical output.

**Done when:** an MCP-capable agent can be pointed at the server and reject a
scoped negative it would otherwise have asserted, with a test proving the
server's decision equals the library's for the same input.

### 1.2 Envelope builder

A producer-side API — `EvidenceBuilder` — that accumulates a query scope, source
observations, and coverage facts and emits a valid envelope, refusing to emit
one whose coverage the caller has not actually declared. Right now the hardest
part of adoption is authoring the input, and that is the wrong place for the
difficulty to sit.

**Done when:** the quickstart produces a working envelope in under twenty lines
of Python, and the builder refuses to fabricate any coverage fact the caller
did not supply.

### 1.3 Adapter interface and a recorded adapter

Define the read-only adapter contract — what an adapter must report about
pagination, partitions, permission limits, timeouts, and index state — and ship
one adapter that replays *recorded* GitHub search responses from disk. No
network, no credentials, no live system.

This closes the loop end to end without touching anything the mandate
withholds, and it makes the live adapter in Phase 4 a change of transport
rather than a change of design.

**Done when:** `evidence-state assess --adapter recorded-github --query …`
produces a real decision from a recorded response, and the adapter cannot
report coverage the recorded response does not support.

### 1.4 Quickstart

One page, five minutes, copy-pasteable: install, run the demo, route one claim
through MCP, read the rejection and its remedy. This is the highest-leverage
document in the repository and it does not exist yet.

**Done when:** a reader who has never seen the project reaches a rejected
negative claim and understands why it was rejected, without reading the PRD.

## Phase 2 — Make it obtainable (authorized)

**Authorized 2026-08-22: TestPyPI first, then PyPI.**

`pip install evidence-state-io` is the difference between a repository and a
tool. Until it exists, every prospective user pays a checkout tax that most
will not pay.

The sequence is: build from a clean tree at a tagged commit, publish to
TestPyPI, install *from TestPyPI* into a fresh virtual environment outside any
checkout, run the packaged benchmarks from that install, and only then publish
to PyPI. A first release cannot be replaced — PyPI does not allow a version to
be reused — so the verification happens before the irreversible step, not after.

Publication happens after Phase 1 completes. Publishing a package whose only
interface is hand-authored JSON would spend the one first impression the name
gets on the version least worth installing.

There are no registry tokens. Publication uses PyPI trusted publishing, so
each publish job receives a short-lived OIDC identity scoped to this repository,
this workflow file, and a named environment. Nothing holds a publishing
credential, and the tagged commit is the only thing that can become a release.

The pipeline is built and committed. What remains is a web-UI step only the
owner can perform: registering a pending trusted publisher on TestPyPI and on
PyPI. `docs/PUBLISHING.md` has the exact fields.

## Phase 3 — Make it credible (authorized)

**Authorized 2026-08-22: the campaign may call an LLM API.** This closes the
owner decision that open issue #4 was waiting on.

The claim that matters is not "the gate is deterministic." It is "routing
negative claims through this gate reduces unsupported negatives without
destroying useful ones." That is a measurement, and it must be preregistered
before it is run or it is worthless.

The campaign compares four configurations on a frozen corpus:

1. prompt-only baseline (an agent told to be careful about absence)
2. always-block baseline (reject every negative — the trivially safe strawman
   that shows what retention costs)
3. envelope-visible (the agent sees the evidence but decides itself)
4. gated (the evaluator decides)

Two metrics, both preregistered: unsupported-negative rate, and valid-negative
retention. Config 2 exists precisely so that a good unsupported-negative number
cannot be bought by rejecting everything.

Configurations 1, 3, and 4 need a model, which is why the authorization
mattered: without it the campaign could only compare deterministic
configurations, which measures the gate against itself.

The protocol, the corpus, the configurations, the metrics, the sample size, and
the analysis are frozen and committed **before** the first run. A campaign whose
design can move after the results are seen measures the designer, not the gate.

**Whatever it shows gets published.** A campaign whose result is only published
when favourable measures nothing.

## Phase 4 — Make it real (authorized)

**Authorized 2026-08-22: read-only, public-data-only calls to GitHub's public
search API.**

One read-only adapter against GitHub's public code search: public data only, no
credentials beyond a rate-limit token, no writes, nothing operational. It is
the difference between "the design supports real sources" and "here is a real
negative claim about a real system, with its coverage bound and its finality
horizon."

The adapter's real work is reporting what GitHub's search will not tell you.
The API caps results at 1000 regardless of how many matched, returns
`incomplete_results` when it times out internally, applies rate limits that
truncate pagination, and indexes asynchronously with no published watermark.
Every one of those is a coverage fact, and an adapter that quietly returns an
empty list without them is exactly the failure this project exists to stop. The
adapter must decline to claim a coverage bound it cannot support, which means
some real queries will produce `NOT_OBSERVED` rather than `ABSENT_WITHIN_SCOPE`.
That is the correct outcome and it must not be tuned away.

## What this plan will not do

It will not claim production readiness, certification, independent validation,
authenticated evidence, source truth, market demand, or operational
effectiveness, and shipping an MVP does not change that. The gate has no
authenticated adapter evidence: a self-consistent producer that fabricates a
coverage bound is not detected by anything in this system, and no phase here
fixes that. That limit is stated in the decision's own limitations and stays
there.

Nor will it contact anyone, register a domain, incur cost, or announce anything
outside the repository, unless the owner authorizes those separately.

## Sequence and current position

| Order | Item | Authorization | State |
|---|---|---|---|
| 1 | 1.1 MCP server | none needed | **done** |
| 2 | 1.2 Envelope builder | none needed | **done** |
| 3 | 1.3 Adapter contract + recorded adapter | none needed | **done** |
| 4 | 4 Live public read-only GitHub adapter | granted 2026-08-22 | **done** |
| 5 | 1.4 Quickstart | none needed | **done** |
| 6 | 2 TestPyPI, verify, then PyPI | granted 2026-08-22 | **built, awaiting owner registration** |
| 7 | 3 Preregister, then run the campaign | granted 2026-08-22 | queued |

### What the first live reading established, 2026-08-23

The first call to a real system returned zero results cleanly, and the claim
was still refused. Three of the four reasons are the caller's to fix: supply a
governed profile, supply a registry snapshot, declare a validity boundary. The
fourth is not fixable by any caller — GitHub publishes no index watermark — and
that is the honest finding. A negative claim about GitHub search cannot reach
the P0 safety floor, and the system says precisely why instead of quietly
permitting it.

The recorded response is committed under `examples/recorded/`, so the finding is
reproducible without network access.

The live adapter follows the recorded one immediately because it is the same
contract with a different transport, and building the recorded one first means
the live version is a transport change rather than a design change.

Distribution comes after the interfaces exist: a first published version whose
only interface is hand-authored JSON would spend the one first impression the
name gets on the version least worth installing.

The campaign comes last because it measures the finished thing, and its design
is frozen before it runs.
