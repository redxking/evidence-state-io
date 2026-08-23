# Publishing

`evidence-state-io` publishes to TestPyPI and then PyPI from the tagged release
workflow, using PyPI's trusted publishing. There is no API token anywhere: not
in the repository, not in a GitHub secret, and not on a laptop. Each publish job
receives a short-lived OIDC identity minted for that job and scoped to this
repository, this workflow file, and a named environment.

That is not only a security preference. A token that lives on a maintainer's
machine is a credential that can publish something the acceptance gate never
saw. Trusted publishing makes the tagged commit the only thing that can become a
release.

## One-time setup

Two web-UI steps that only the project owner can perform. Both register a
*pending* publisher, which is how a project that does not exist on the index yet
is claimed.

### 1. TestPyPI

Go to <https://test.pypi.org/manage/account/publishing/> and add a pending
publisher:

| Field | Value |
|---|---|
| PyPI project name | `evidence-state-io` |
| Owner | `redxking` |
| Repository name | `evidence-state-io` |
| Workflow name | `release.yml` |
| Environment name | `testpypi` |

### 2. PyPI

Go to <https://pypi.org/manage/account/publishing/> and add the same publisher,
changing only the environment:

| Field | Value |
|---|---|
| Environment name | `pypi` |

Nothing else is required. GitHub environments named `testpypi` and `pypi` are
created on first use; adding a required reviewer to the `pypi` environment is
optional and makes the irreversible step a manual approval.

## What a release does

Pushing a tag `vMAJOR.MINOR.PATCH` runs, in order:

1. **build-test** — validates that the tag matches the project version and that
   the commit is an ancestor of `main`, runs the full check suite, builds the
   wheel and sdist, installs the wheel into a throwaway environment outside the
   checkout with decoy benchmark artifacts planted beside the caller, and
   generates checksums, an evidence manifest, and an SBOM.
2. **publish-testpypi** — publishes those exact artifacts to TestPyPI.
3. **verify-testpypi** — with no checkout at all, installs the package *from the
   index* into an empty directory and runs both packaged benchmarks and the MCP
   server. This step exists because a package that works inside its own source
   tree and nowhere else looks identical until you leave the tree, which is how
   ESIO-DEF-001 was found — minutes after `v0.6.0` was published.
4. **release** — attests build provenance and attaches the artifacts to a
   GitHub release.
5. **publish-pypi** — publishes to PyPI, only after steps 3 and 4 succeeded.

A PyPI version can never be replaced or reused, so the irreversible step runs
last and only after the same bytes have been installed from an index and shown
to work.

## Verifying a published release

```bash
pip download --no-deps --no-binary :all: evidence-state-io==0.7.0
sha256sum evidence_state_io-0.7.0.tar.gz
```

Compare against `SHA256SUMS` on the corresponding GitHub release. The release
also carries PEP 740 attestations produced during publication and a build
provenance attestation, both verifiable with `gh attestation verify`.

## What publication does not establish

A package on PyPI is a distribution channel, not evidence. It does not establish
production readiness, external validation, authenticated evidence, source truth,
or fitness for any consequential decision. The limitations shipped with each
release say so, and they are shipped with each release for that reason.
