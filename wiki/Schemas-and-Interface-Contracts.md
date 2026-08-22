# Schemas and interface contracts

The candidate uses closed, versioned JSON contracts. Unknown fields, version
aliases, duplicate keys, ambiguous numeric values, invalid primitive subclasses,
and missing required fields fail closed. Canonical JSON and SHA-256 bind the
request, evidence, policy, profile, registry snapshot, trust selection,
evaluation input, decision, and certificate.

The importable Python API and `evidence-state` CLI are authoritative. Active
contract identifiers are listed in the
[README](https://github.com/redxking/evidence-state-io#active-contract-set), and
compatibility rules are recorded in
[ADR 0007](https://github.com/redxking/evidence-state-io/blob/main/docs/adr/0007-schema-1-source-accounting-and-version-boundaries.md).
