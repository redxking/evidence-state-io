# Frequently Asked Questions

## Is this another provenance format?

It overlaps with provenance and attestation work but focuses on a claim-specific
decision: whether the available evidence is sufficient to support a bounded
negative conclusion. It records scope, access, coverage, source state,
freshness, finality, and limitations as inputs to that decision.

## Does `ABSENT_WITHIN_SCOPE` prove absence?

No. It is a producer-declared evidence state and only one prerequisite for a
permit. The gate still checks the complete contract, and the resulting claim is
bounded to the declared scope.

## Does a valid certificate authenticate the source?

No. P0 certificates are unsigned replay records. Digest and replay checks do
not authenticate the issuer, source, profile, clock, or origin label.

## Why not let an LLM make the judgment?

Evidence sufficiency is a safety-relevant policy decision that should be
reproducible and falsifiable. A model may explain the result, but it cannot
silently override the deterministic verdict or remove qualifications.

## Can this run on a laptop or in VMs?

Yes. The core path is a dependency-light Python package supporting 3.11–3.13.
The optional container lab is for bounded synthetic fault injection.

## Is it production ready?

No. The project is a pre-alpha research candidate. It lacks authenticated
source evidence, trusted time, independent registry custody, operational
validation, and a completed frozen benchmark campaign.

## Where should an open question go?

Use [Discussions](https://github.com/redxking/evidence-state-io/discussions)
for open-ended research conversation and
[Issues](https://github.com/redxking/evidence-state-io/issues/new/choose)
for bounded implementation, benchmark, or defect work.
