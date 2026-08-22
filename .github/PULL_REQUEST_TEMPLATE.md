## Purpose

Describe the problem, the intended outcome, and why this change is the smallest coherent increment.

## Scope

- In scope:
- Deliberately out of scope:
- Requirement, issue, ADR, or kill condition:

## Change type

- [ ] Defect correction
- [ ] Research-gap or benchmark work
- [ ] Contract, policy, profile, or architecture change
- [ ] Feature or adapter
- [ ] Documentation, governance, or tooling only

## Evidence and claim boundary

- Safety invariant or failure mode affected:
- New evidence this change establishes:
- What this change does **not** establish:
- Trust, authorization, data-handling, or compatibility impact:

If this changes a state meaning, gate disposition, wire contract, policy, profile,
certificate, or trust boundary, link the accepted ADR and migration analysis.

## Verification

List the exact commands run and observed outcomes. Identify anything not run and why.

```text
# command -> observed result
```

- [ ] Positive and matched negative controls are present where applicable.
- [ ] Boundary, malformed-input, deterministic, and replay cases were considered.
- [ ] Golden outputs were reviewed semantically rather than accepted blindly.
- [ ] Supported Python 3.11, 3.12, and 3.13 behavior was considered.

## Security and data review

- [ ] No credentials, secrets, private-system details, or unapproved data are included.
- [ ] New dependencies and actions have a stated purpose, license, and security review.
- [ ] Untrusted input cannot upgrade an unsupported negative to a permit.
- [ ] Outputs do not claim authentication, authorization, production readiness, or
      external validation beyond the evidence actually supplied.

## Documentation and delivery

- [ ] User-facing behavior and interfaces are documented in the same change.
- [ ] Tasks, backlog, milestone, or project status is updated when scope changed.
- [ ] Release notes are needed, or the reason they are not needed is stated below.

## Reviewer focus

Call out the highest-risk assumption, the easiest way to falsify the change, and any
follow-on decision that should not be bundled into this pull request.
