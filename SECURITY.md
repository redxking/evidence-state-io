# Security Model and Reporting

## Security posture

Evidence-State I/O is a pre-alpha local research prototype for synthetic evaluation. It has not undergone an independent security assessment and is not approved for production, safety-critical decisions, sensitive data, or autonomous investigation closure.

The primary P0 security objective is narrow: untrusted input, incomplete evidence, or a failed component must not cause the deterministic gate to permit an unsupported negative claim.

## Protected assets

- Integrity of evidence envelopes, policies, registry snapshots, oracle labels, verdicts, and certificates.
- Correctness and determinism of coverage evaluation and gate behavior.
- Confidentiality of source metadata, query scope, authorization-boundary identifiers, and observations.
- Separation between benchmark ground truth and implementation output.
- Reproducibility records, including versions, evaluation times, exclusions, and failed runs.
- Future source credentials and signing keys, which must never enter ordinary envelopes or fixtures.

## Trust boundaries

```text
UNTRUSTED
  caller / agent / JSON file / adapter response
                    |
                    v
TRUSTED COMPUTING BASE (P0)
  strict decoder -> canonicalizer -> evaluator -> gate -> certificate builder
                    |
                    v
CONDITIONALLY TRUSTED
  local filesystem / terminal / test oracle / policy and registry maintainers

OPTIONAL LAB BOUNDARY
  read-only adapter -> loopback Toxiproxy -> synthetic Postgres
```

The local operator can replace code, policy, fixtures, outputs, and digests. Therefore a result produced and stored on one laptop does not provide independent custody or non-repudiation.

## Target security invariants

These are required end-state properties. Current implementation status and
known gaps are recorded in `docs/TRACEABILITY.md`. The schema `1.0` candidate
now performs bounded single-source accounting and query binding; credential-like
field detection, explicit finality, profile governance, independent source
attestation, and multi-source composition are not complete.

1. Unknown or malformed evidence-bearing input is rejected, not coerced.
2. No disqualifying state permits `PERMIT_SCOPED_NEGATIVE`.
3. Missing time, version, scope, or required coverage facts fail closed.
4. Language-model output cannot alter a verdict.
5. Adapters cannot grant `ABSENT_WITHIN_SCOPE` directly.
6. The evaluator does not consult network, filesystem, environment, wall clock, or mutable global state.
7. Secrets and raw credentials are not accepted as authorization-context identifiers.
8. A certificate digest is never described as authentication, signature, independent custody, or proof that a source declaration is true.
9. The core demo works without network access.
10. Optional lab services bind to loopback and contain synthetic data only.

## Threat actors and capabilities

The P0 model considers:

- a caller trying to obtain a clearance from incomplete evidence;
- a malformed or malicious JSON producer;
- a buggy or compromised source adapter suppressing errors or truncation;
- a policy/registry maintainer making an overbroad or stale declaration;
- a benchmark implementer leaking oracle labels or changing cases after results;
- a local user or process modifying stored evidence and its adjacent digest;
- a dependency or CI compromise;
- accidental disclosure through stdout, stderr, test fixtures, logs, or version control.

It does not claim to withstand a privileged attacker controlling the host, interpreter, code, policy, and expected digest.

## Threat analysis

| Threat | Example | Required control | Residual risk |
|---|---|---|---|
| Scope omission | Caller omits a tenant or time range | Strict required fields; scoped renderer; missing-field rejection | A declared scope can still be misleading or semantically wrong |
| Completion spoofing | Adapter hides continuation token or failed shard | Independent completion fields, consistency checks, adapter contract tests | A malicious adapter can lie unless corroborated |
| Wrong-observation substitution | Coverage or an observation from another query/source is relabeled for the current query | Exact source/adapter/auth/population matching and canonical query fingerprints on coverage and observation | A malicious producer can still forge a self-consistent envelope without independent attestation |
| Permission laundering | Empty accessible subset is described as the whole population | Explicit authorization/access boundary and policy | Registry owner may overstate accessible population |
| Staleness/finality bypass | Caller supplies favorable current time or omits late-arrival horizon | Explicit evaluation time and policy; boundary tests; certificate binding | Trusted time is not established in P0 |
| State confusion | Unknown state coerced to success or generic empty | Closed enums, unsupported-version rejection, invariant tests | Future compatibility requires careful versioning |
| Parser resource exhaustion | Deep/large JSON or huge arrays | Input-size and nesting limits, bounded collections, predictable errors | The CLI bounds bytes, nesting, numeric tokens, and integer magnitude; comprehensive collection and semantic limits require continued testing |
| Output injection | Untrusted text reaches terminal/log | JSON encoding; diagnostics separation; no shell interpolation | Human viewers may still render hostile strings unsafely |
| Path traversal | Caller-controlled path escapes expected location | CLI treats paths as explicit user input, opens files read-only, avoids derived write paths | Local user already has filesystem authority |
| Oracle leakage | Benchmark includes expected answer in model-visible input | Separate oracle storage and scorer; review frozen corpus | Subtle fixture cues may still permit gaming |
| Universal abstention | Gate appears safe by rejecting every negative | Matched covered controls and supported-negative-retention metric | Corpus may not represent real workload distribution |
| Certificate replacement | Attacker changes payload and adjacent digest | Trusted expected digest, append-oriented custody, tamper tests | P0 has no independent store or signature |
| Dependency compromise | Malicious package/action enters build | Minimal dependencies, pinned/reviewed changes, least CI permissions | Tags and registries remain external trust dependencies |
| Lab escape/mis-targeting | Fault script affects a real service | Fixed Compose project, loopback ports, named proxy, explicit commands | Docker daemon access is privileged on the host |
| Sensitive-data leakage | Real query content enters fixtures or CI logs | Synthetic-only default, data review, no credentials, approval boundary | Human error remains possible |

## Input handling requirements

- The current CLI rejects inputs above 1 MiB and nesting deeper than 128; retain boundary tests for both.
- Reject non-finite numbers, duplicate identifiers, optional/multi-source candidate declarations, unsupported fields/versions, literal placeholder scope/identity declarations, invalid query fingerprints or timestamp offsets, and inconsistent completion facts.
- Bound numeric tokens, collection length, string length, and reason-code count; string bounds are partial and comprehensive collection/reason bounds remain backlog work.
- Do not deserialize pickle or execute caller-provided code, templates, expressions, regular expressions, SQL, or shell fragments.
- Treat a filename as an operator-selected local input, never as a destination derived from envelope content.
- Do not emit Python stack traces or local paths in machine-readable stdout.

## Secrets and authorization context

Envelopes may include a stable authorization-context identifier or access-boundary label, but never:

- passwords, API keys, bearer tokens, cookies, session material, private keys, or database connection strings;
- raw identity-provider assertions;
- sensitive headers or signed URLs;
- credentials embedded in exception messages.

Future adapters must obtain credentials through an approved runtime mechanism and use least-privilege read-only identities. Secret scanning and redaction should be release gates, but a scanner result is not proof that no secret exists.

## Data classification and retention

P0 fixtures are synthetic and public-safe. Before any real-data evaluation, document and approve:

- data owner and system owner;
- legal/contractual authority and intended use;
- classification and regulated-data categories;
- exact fields collected and redacted;
- storage, encryption, access, retention, and deletion;
- whether prompts, errors, or certificates could reproduce source content;
- incident and breach response contacts.

Do not use production or customer data merely because an adapter is read-only.

## Certificate and cryptography boundary

P0 may calculate a SHA-256 integrity digest over a canonical payload. This supports deterministic replay and comparison only when a trusted party already has the expected value.

Adding signatures requires a new ADR and security design covering issuer identity, key generation, protected storage, rotation, revocation, algorithm agility, verification policy, timestamps, and compromised-key response. A valid signature must never upgrade insufficient evidence into `ABSENT_WITHIN_SCOPE`.

## Optional container lab

- Services are opt in and not required by the core suite.
- Published ports bind to `127.0.0.1` only.
- Credentials are fixed synthetic lab values and must not be reused.
- Containers run with dropped capabilities and `no-new-privileges` where the image permits.
- The fault script targets only the named local proxy and does not expose a generic host/port argument.
- `down` preserves the named volume; no repository script purges it.
- Image tags are reviewed and intentionally pinned before a release. A tag is not an immutable supply-chain guarantee.

## CI and dependencies

- CI receives read-only repository permissions unless a separately approved job needs more.
- CI does not publish packages, images, reports, or releases automatically.
- Pull-request code must not receive production secrets.
- Core runtime dependencies remain minimal; every addition needs purpose, maintenance, license, and security review.
- Development checks compile the package, run tests, exercise CLI help/demo, validate shell syntax, and validate Compose configuration without starting services.
- Before an owner-authorized release, pin third-party actions by reviewed immutable commit, generate dependency inventory/SBOM, and perform a reproducible build review.

## Out of scope for P0

- Protection against a privileged local or host compromise.
- Independent source attestation or proof that registry declarations are true.
- Multi-party evidence custody, transparency logging, trusted timestamps, HSM-backed signing, or non-repudiation.
- Production availability, tenant isolation, disaster recovery, or regulatory compliance certification.
- Write-capable remediation, automated investigation closure, or consequential-action authorization.

## Security release gates

Production or sensitive-data use requires a separately approved design that includes at least:

- independent threat modeling and code review;
- parser and resource-limit tests, fuzzing, and dependency review;
- authenticated authorization for configuration and evidence access;
- tenant/data isolation and encrypted storage/transport;
- trusted policy/registry change control;
- source credential lifecycle and least privilege;
- durable audit custody and incident response;
- backup, recovery, retention, and verified deletion;
- operational monitoring and safe failure modes;
- legal, privacy, records, and sector-specific review;
- documented residual-risk acceptance by the owner.

## Reporting a vulnerability

Do not publish exploit details, credentials, sensitive fixtures, or private-system information in a public issue.

Until the owner establishes a public reporting channel:

1. Stop testing once the minimum safe reproduction is established.
2. Preserve the exact version, synthetic reproduction, expected versus actual result, and impact.
3. Notify the project owner through the existing private coordination channel.
4. Do not access additional data, expand scope, contact third parties, or attempt persistence.
5. Coordinate disclosure and remediation timing with the owner.

If a discovered issue affects an external dependency or system, follow that owner’s authorized disclosure process without sending repository or user data.
