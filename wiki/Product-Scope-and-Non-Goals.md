# Product scope and non-goals

The MVP is a machine-readable evidence envelope, coverage evaluator,
negative-claim gate, qualified renderer, unsigned deterministic replay
certificate, paired EmptyBench corpus, and application-controlled local profile
custody. P0 supports exactly one required source.

It is not proof of absolute nonexistence, a hallucination detector, a source or
sensor certification system, an action-authorization gateway, an effect
verifier, a SIEM, a search engine, an observability platform, or an agent
framework. It is not production ready or independently validated.

A permit supports only the generated statement bounded to the declared query,
population, source, access boundary, filters, and interval. A rejection says
the evidence is insufficient; it does not establish the opposite positive
claim.
