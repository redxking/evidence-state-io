# Security and threat model

The threat model covers malformed or ambiguous input, version downgrade,
producer-selected weaker profiles, missing or inconsistent source facts,
stale or pre-finality evidence, incomplete pagination, contradiction, record
tampering, replay mismatch, and configuration replacement within documented
local custody boundaries.

The candidate does not provide issuer authentication, trusted time,
non-repudiation, source-truth proof, credential custody, or cryptographic
attestation. Report vulnerabilities through the repository's
[private security advisory path](https://github.com/redxking/evidence-state-io/security/advisories/new),
not a public issue. See [SECURITY.md](https://github.com/redxking/evidence-state-io/blob/main/SECURITY.md).
