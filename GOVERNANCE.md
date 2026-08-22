# Governance

## Project model

Evidence-State I/O is an open-source, maintainer-led pre-alpha research project. Public
participation improves the evidence and implementation; it does not convert a candidate
contract into a standard, establish external validation, or authorize production or
consequential use.

The current maintainer is [@redxking](https://github.com/redxking). The maintainer is
accountable for repository administration, scope, releases, security coordination, and
final decisions on normative contracts. Contributors own the quality and traceability of
their proposals and evidence.

## How work is governed

- **Issues** are the unit of public problem definition and executable work.
- **Milestones** group issues into bounded candidate outcomes; they are plans, not delivery
  promises.
- **GitHub Projects** provide Now, Next, Later, Blocked, and Done views for public roadmap
  tracking. Repository backlog and task files remain the technical source for acceptance
  criteria and local execution state.
- **Discussions** are for questions, early research hypotheses, and design exploration that
  are not yet ready to become committed work.
- **Pull requests** carry implementation, review evidence, and explicit claim boundaries.
- **ADRs** record decisions that change state meanings, contracts, policy, trust boundaries,
  compatibility, or architecture.
- **Wiki and Pages** may explain stable public concepts and navigation. They are not
  normative when they conflict with version-controlled contracts or ADRs.

## Decision process

Routine corrections and bounded implementation changes are decided through pull-request
review. A proposal that changes a normative state, gate disposition, schema, profile,
certificate, trust boundary, or compatibility promise requires an ADR and migration or
unsupported-version analysis before implementation is accepted.

The maintainer seeks technical consensus but does not use silence, reaction counts, or a
single benchmark result as consent. When consensus is not possible, the maintainer records
the decision, rationale, objections, evidence gaps, and conditions for revisiting it.

## Review and merge

Code ownership identifies required technical attention; repository rulesets enforce the
actual approval policy. Review should examine:

1. the requirement, falsification test, and operational need;
2. whether an unsupported negative could be permitted;
3. oracle independence and matched controls;
4. deterministic behavior and supported-runtime compatibility;
5. security, data, authorization, dependency, and migration impact; and
6. the exact evidence produced and claims it does not support.

Maintainers may close or defer sound proposals that are out of scope, insufficiently
bounded, duplicative, unsafe, or unsupported by available capacity. The reason should be
recorded.

## Releases

Only the maintainer may authorize a version tag and GitHub release. Release automation
builds, tests, hashes, and attests tagged package artifacts; those controls establish build
traceability only. Until separate gates are satisfied, releases remain pre-alpha research
artifacts and do not claim production readiness, security certification, source truth,
authenticated evidence, or operational authorization.

Changing a candidate to a frozen contract or publishing to a package registry requires a
separate recorded decision. A GitHub release does not perform either action implicitly.

## Security and disclosure

Potential vulnerabilities and sensitive material follow [SECURITY.md](SECURITY.md), not a
public issue or discussion. Governance disputes follow this document and the
[Code of Conduct](CODE_OF_CONDUCT.md); they must not be disguised as security reports.

## Amendments

Governance changes are proposed by pull request and approved by the maintainer. Material
changes should explain why the prior rule was insufficient and when the new rule takes
effect.
