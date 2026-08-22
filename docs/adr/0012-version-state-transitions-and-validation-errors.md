# ADR-0012: Version State Transitions and Public Validation Failures

**Status:** Accepted for local candidate implementation; not a schema freeze or release decision
**Date:** 2026-08-22
**Deciders:** Project owner; architecture maintainer

## Context

The schema `1.0` candidate enumerated nine evidence states but did not expose
the allowed transition relation required by ESIO-P0-001. Authorization-context
IDs were syntactically narrow but still admitted some credential and raw-token
shapes, contrary to ESIO-P0-002 and the security invariant that credentials do
not enter evidence envelopes. Public CLI failures also exposed exception class
names and human messages without a separately versioned machine code.

These are P0 contract gaps. They can be closed without adding a service,
dependency, model, ambient clock, source adapter, or benchmark claim.

## Decision

### 1. State transitions use one exact candidate model

The supported transition model is
`esio-evidence-state-transition-model/1.0-candidate.1`. It applies only to
successive immutable envelopes in one claim lineage with the same schema,
normalized query fingerprint, and declared source set. A transition creates a
new record; it never mutates a certificate or prior envelope. The transition
check is a coarse lifecycle invariant and does not replace envelope validation,
coverage evaluation, or the negative-claim gate.

The ordered relation is:

| Prior state | Allowed successor states |
|---|---|
| `PRESENT` | `PRESENT` |
| `NOT_OBSERVED` | All nine states |
| Any other state | Every state except `NOT_OBSERVED` |

`PRESENT` is absorbing within a fixed lineage because a later empty, failed, or
weaker observation cannot erase an already observed in-scope match. A changed
scope starts a different lineage. `NOT_OBSERVED` is the entry classification;
once a specific result or fault exists, a successor must preserve that knowledge
with a more precise state. Conditional absence and every indeterminate state may
later resolve to `PRESENT` or `ABSENT_WITHIN_SCOPE`, remain unresolved, or move
to another explicit fault state as new evidence or time conditions arrive.
`ABSENT_WITHIN_SCOPE` still requires independent evaluation of every policy
invariant; an allowed transition does not grant it.

The public API returns successors in taxonomy order and supplies an immutable,
strictly parsed JSON transition record. Unknown, older, floating, or missing
model identifiers reject without fallback.

### 2. Authorization-context IDs use a narrow non-secret profile

The supported identifier profile is
`esio-authorization-context-identifier/1.0-candidate.1`. It first applies the
existing lowercase ASCII identifier grammar, then rejects only these defined
credential-like classes:

- explicit colon-delimited credential schemes such as `bearer:`, `basic:`,
  `password:`, `secret:`, `token:`, `access_token:`, `refresh_token:`,
  `api_key:`, `cookie:`, `session:`, and `authorization:`;
- known GitHub, GitLab, Slack, Google OAuth, AWS access-key, and `sk-` token
  prefix/length shapes admitted by the base identifier grammar;
- a three-segment JWT-like compact shape beginning with `eyj`; and
- an unnamespaced 48-to-128-character alphanumeric value containing both
  letters and digits.

The check is applied only to `authorization_context_id` in `QueryScope`,
`SourceRequirement`, `SourceObservation`, and `ProfileSource`, through both JSON
and typed-object construction. It does not scan authorization-boundary prose,
source locations, detection assumptions, error text, notes, or other descriptive
content. It never echoes the rejected value in the error message.

This profile is a fail-closed field invariant, not a general secret scanner.
Unrecognized secrets can still resemble ordinary identifiers. Source adapters,
repository scanning, runtime credential isolation, and data review remain
independent controls.

### 3. Validation failures have stable codes separate from messages

The public error schema is `esio-validation-error/1.0-candidate.1`. CLI exit `2`
errors retain the existing safe human `message` and exception `type` fields and
add `validation_error_schema` plus one code from this closed vocabulary:

- `MODEL_INVALID`
- `UNSUPPORTED_CONTRACT`
- `STATE_TRANSITION_INVALID`
- `CREDENTIAL_LIKE_IDENTIFIER`
- `JSON_SYNTAX_INVALID`
- `JSON_DUPLICATE_KEY`
- `JSON_NUMBER_INVALID`
- `JSON_DEPTH_EXCEEDED`
- `INPUT_SIZE_EXCEEDED`
- `INPUT_ENCODING_INVALID`
- `INPUT_READ_FAILED`
- `CLI_ARGUMENT_INVALID`
- `OUTPUT_ENCODING_FAILED`

Existing domain validators use `MODEL_INVALID` unless a narrower public class
is explicitly assigned. Human wording may become more precise without changing
the code. A changed meaning, removed code, or incompatible payload requires a
new validation-error schema. Command-usage errors now use the same JSON boundary
instead of argparse prose. Input I/O errors do not disclose a filesystem path.

## Version and downgrade boundary

This decision adds three exact candidate identifiers. It does not silently
revise the policy, canonical JSON, transition, or validation-error contract.
The transition and identifier APIs reject any other profile identifier. The
validation-error identifier is emitted in every structured CLI validation
failure.

No existing gate, policy, evaluation-input, certificate, registry, trust, or
canonicalization identifier is changed by this ADR. State-transition records
are not part of the current evidence certificate, and invalid credential-like
input is rejected before evaluation or certificate issuance. Schema `1.0`
remains unfrozen; this implementation closes already stated P0 acceptance and
security requirements and does not claim backward compatibility with rejected
pre-freeze invalid inputs.

## Consequences

- All 81 state pairs have an explicit deterministic answer.
- Known evidence cannot collapse back to generic `NOT_OBSERVED`, and observed
  positive evidence cannot be erased within a fixed claim lineage.
- Credential-like authorization IDs fail before query fingerprinting,
  evaluation, logging, or certificate generation.
- CLI consumers can branch on versioned codes rather than parsing prose.
- The heuristic cannot prove that an accepted identifier is non-secret, and the
  transition API cannot prove that a successor envelope's facts are true.
- Existing certificates and benchmark outputs are not evidence that these new
  contracts were externally reproduced or independently validated.

## Acceptance evidence required

1. Exact interpretation text exists for all nine states.
2. The complete nine-by-nine transition matrix, JSON round trip, invalid state,
   invalid transition, and version downgrade cases pass.
3. Every authorization-context model field rejects every specified credential
   class through typed and JSON boundaries, while semantic/namespaced IDs pass.
4. Tests prove descriptive content is not scanned and rejected values are not
   echoed.
5. Every public error-code value is locked; malformed, duplicate, invalid-model,
   oversized, I/O, and command-usage paths produce deterministic JSON.
6. Focused and full source suites, repository checks, and the offline demo pass
   after the installed package is refreshed.

Passing these checks establishes local implementation behavior only. It does
not freeze schema `1.0`, prove secret absence, validate source truth, establish
external custody, authorize release, or establish production readiness.
