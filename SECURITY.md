# Security Model and Reporting

## Security posture

Evidence-State I/O is a pre-alpha local research prototype for synthetic evaluation. It has not undergone an independent security assessment and is not approved for production, safety-critical decisions, sensitive data, or autonomous investigation closure. P0 inputs, configuration, fixtures, and certificates are limited to synthetic/public-safe data or owner-approved nonsensitive data.

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
  producer request / caller / agent / adapter response
                    | cannot select or overwrite relying-party configuration
                    |
APPLICATION-CONTROLLED P0 CONFIGURATION
  producer-unwritable registry snapshot + trust selection
  + exact selected profile reference
                    |
                    v
TRUSTED COMPUTING BASE (P0)
  strict decoder -> canonicalizer -> profile resolver -> evaluator -> gate
  -> certificate builder/verifier
                    |
                    v
CONDITIONALLY TRUSTED
  local filesystem custody / terminal / test oracle / application operator
  / policy and registry maintainers

OPTIONAL LAB BOUNDARY
  read-only adapter -> loopback Toxiproxy -> synthetic Postgres
```

The application must fix the registry snapshot, trust selection, and exact selected profile reference outside the producer request and prevent the producer from modifying those files or in-memory objects. This creates a deterministic local configuration boundary, not authenticated governance. Issuer, approval-authority, source-owner, evidence-origin, repository-revision, and working-tree labels remain unauthenticated assertions in P0.

The local operator can replace code, policy, configuration, fixtures, outputs, and digests. Therefore a result produced and stored on one laptop does not provide independent custody or non-repudiation.

## Target security invariants

These are required end-state properties. Current implementation status and
known gaps are recorded in `docs/TRACEABILITY.md`. Package `0.6.0` uses policy
`esio-p0-safety-floor/1.0-candidate.4`, evaluator
`esio-evaluator-1.0-candidate.5`, and candidate.2 profile, registry, trust,
evaluation-input, and certificate contracts. The candidate performs bounded
single-source accounting, binds the request to an application-selected exact
profile, derives finality from that profile, and emits an unsigned deterministic
replay record. A narrow candidate.1 authorization-context identifier profile
rejects recognized credential-like shapes; it is not a general secret detector.
Authenticated profile/source evidence, independent source attestation, and
multi-source composition are not complete. Schema `1.0` is not frozen.

1. Unknown or malformed evidence-bearing input is rejected, not coerced.
2. No disqualifying state permits `PERMIT_SCOPED_NEGATIVE`.
3. Missing time, version, scope, or required coverage facts fail closed.
4. Language-model output cannot alter a verdict.
5. Adapters cannot grant `ABSENT_WITHIN_SCOPE` directly.
6. The evaluator does not consult network, filesystem, environment, wall clock, or mutable global state.
7. Recognized credential-like authorization-context identifier shapes reject;
   this narrow guardrail is not exhaustive secret detection.
8. A certificate digest is never described as authentication, signature, independent custody, or proof that a source declaration is true.
9. The core demo works without network access.
10. Optional lab services bind to loopback and contain synthetic data only.
11. The producer cannot supply, replace, or select the application-controlled registry, trust selection, or exact selected profile reference used to authorize profile resolution.
12. Snapshot trust failures stop before record resolution; profile identity, digest, issuer, authority, time, or revocation failures stop before profile applicability and finality semantics are consulted.
13. Floating aliases, ranges, branch names, and other mutable profile or adapter versions fail closed; only immutable exact versions are accepted.
14. Current local reliance on a certificate requires successful structural, digest, embedded-binding, deterministic-replay, separately supplied expected-context, separately retained expected-certificate-digest, and relying-party-time checks. A rejection certificate can never become a permit.

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
| Weak-profile selection | Producer selects a permissive profile that is present in an otherwise trusted snapshot | Application-controlled trust selection pins one exact profile reference; producer reference must match; no fallback or automatic upgrade/downgrade | P0 custody is local configuration, not authenticated issuer governance |
| Untrusted-profile diagnostic influence | Invalid snapshot or profile content is consulted to derive a favorable finality or applicability result | Trust and exact-resolution failures short-circuit before profile semantics and do not populate resolved references | Correct application configuration and code integrity still depend on the local operator |
| Staleness/finality bypass | Caller advances evaluation time while reusing a pre-horizon empty snapshot, omits the horizon, or chooses a favorable horizon | Profile-derived exact horizon; reported index must reach it; explicit evaluation time; exact boundary tests | Profile assertions and source index declarations are not authenticated or proven true in P0 |
| Contract downgrade | Input requests `latest`, a version range, a branch name, or an older/unknown active contract | Exact allowlists and immutable-version validation; no fallback or package-version negotiation | Pre-freeze candidates can still change only through an explicitly recorded contract bump |
| State confusion | Unknown state coerced to success or generic empty | Closed enums, unsupported-version rejection, invariant tests | Future compatibility requires careful versioning |
| Parser resource exhaustion | Deep/large JSON or huge arrays | Input-size and nesting limits, bounded collections, predictable errors | The CLI bounds bytes, nesting, numeric tokens, and integer magnitude; comprehensive collection and semantic limits require continued testing |
| Output injection | Untrusted text reaches terminal/log | JSON encoding; diagnostics separation; no shell interpolation | Human viewers may still render hostile strings unsafely |
| Path traversal | Caller-controlled path escapes expected location | CLI treats paths as explicit user input, opens files read-only, avoids derived write paths | Local user already has filesystem authority |
| Oracle leakage | Benchmark includes expected answer in model-visible input | Separate oracle storage and scorer; review frozen corpus | Subtle fixture cues may still permit gaming |
| Universal abstention | Gate appears safe by rejecting every negative | Matched covered controls and supported-negative-retention metric | Corpus may not represent real workload distribution |
| Certificate replacement or context substitution | Attacker changes payload/context and recomputes unkeyed digests | Complete payload binding, deterministic replay, separately retained expected digest/context, distinct verification dimensions | P0 has no signature, authenticated issuer, trusted timestamp, monotonic registry head, or independent store |
| Stale certificate reuse | Historically reproducible permit is presented after evidence, profile, snapshot, or freshness expiry | Conservative exclusive validity boundary and separately supplied relying-party time; rejection and expiry block current local reliance | P0 does not distribute live revocation state or establish trusted time |
| Dependency compromise | Malicious package/action enters build | Minimal dependencies, pinned/reviewed changes, least CI permissions | Tags and registries remain external trust dependencies |
| Lab escape/mis-targeting | Fault script affects a real service | Fixed Compose project, loopback ports, named proxy, explicit commands | Docker daemon access is privileged on the host |
| Sensitive-data leakage | Real query, source metadata, authorization labels, or observations enter a self-contained certificate, fixture, CI log, or repository | Synthetic/approved-nonsensitive P0 boundary, data review, no credentials, restricted custody | The P0 certificate intentionally embeds the full request, registry/trust context, and decision; it is not data-minimized and can duplicate sensitive material |

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

P0 fixtures and certificates are synthetic/public-safe or specifically approved as nonsensitive. The candidate certificate is deliberately self-contained for deterministic replay: it embeds the normalized request, complete registry snapshot and trust selection, context bindings, decision, qualifications, limitations, origin, and implementation metadata. It is not a redacted, reference-only, or selectively disclosed artifact. Treat a certificate at least as sensitively as every embedded input and do not place one in source control, CI artifacts, chat, tickets, or external evidence packages unless every field is approved for that destination.

Before any real-data evaluation, document and approve:

- data owner and system owner;
- legal/contractual authority and intended use;
- classification and regulated-data categories;
- exact fields collected and redacted;
- storage, encryption, access, retention, and deletion;
- whether prompts, errors, or certificates could reproduce source content;
- incident and breach response contacts.

Do not use production or customer data merely because an adapter is read-only.

P1 must define a separately versioned operational certificate/data-handling profile before non-public use. That design must cover authenticated registry and source evidence, field minimization, redaction, reference resolution, selective disclosure where appropriate, encrypted custody, access control, retention, deletion, and the effect of redaction on deterministic replay. P0 self-contained certificates must not be silently transformed into that profile.

## Certificate and cryptography boundary

P0 emits an unsigned `esio-evidence-certificate/1.0-candidate.2` replay record and calculates SHA-256 integrity digests over canonical payloads. Verification separates structural support, certificate-digest integrity, embedded bindings, deterministic historical replay, expected-context comparison, expected-digest comparison, and time-bounded current local reliance. These are local integrity and reproducibility results. They do not authenticate the issuer, registry, profile authority, source, origin label, implementation identity, or timestamp, and they never authorize an action.

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
- Ordinary push and pull-request CI does not publish packages, images, reports, or releases. An owner-created, version-matching tag can invoke the separately permissioned prerelease workflow; it does not publish to a package registry.
- Pull-request code must not receive production secrets.
- Core runtime dependencies remain minimal; every addition needs purpose, maintenance, license, and security review.
- Development checks compile the package, run tests, exercise CLI help/demo, validate shell syntax, and validate Compose configuration without starting services.
- Third-party actions are pinned by reviewed immutable commits and monitored by Dependabot. Before an owner-authorized release, review the dependency inventory/SBOM and build-isolation inputs; the current tag workflow produces provenance evidence but does not claim bit-for-bit reproducible builds.

## Out of scope for P0

- Protection against a privileged local or host compromise.
- Independent source attestation or proof that registry declarations are true.
- Authenticated registry heads, source-owner evidence, profile approvals, origin labels, or source clocks.
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
- authenticated registry/profile/source evidence with rollback and revocation handling;
- source credential lifecycle and least privilege;
- a separately reviewed minimization/redaction/reference/selective-disclosure design for certificates containing non-public data;
- durable audit custody and incident response;
- backup, recovery, retention, and verified deletion;
- operational monitoring and safe failure modes;
- legal, privacy, records, and sector-specific review;
- documented residual-risk acceptance by the owner.

## Reporting a vulnerability

Do not publish exploit details, credentials, sensitive fixtures, or private-system information in a public issue.

Use GitHub's private vulnerability reporting for this repository. If that
facility is unavailable, notify the maintainer through an existing private
coordination channel. In either case:

1. Stop testing once the minimum safe reproduction is established.
2. Preserve the exact version, synthetic reproduction, expected versus actual result, and impact.
3. Notify the project owner through the existing private coordination channel.
4. Do not access additional data, expand scope, contact third parties, or attempt persistence.
5. Coordinate disclosure and remediation timing with the owner.

If a discovered issue affects an external dependency or system, follow that owner’s authorized disclosure process without sending repository or user data.
