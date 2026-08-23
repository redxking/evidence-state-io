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

## Rolling back a release

A PyPI version can never be replaced, deleted, and reused. Rollback is therefore
not "undo"; it is two steps.

1. **Yank the bad version.** On the project's PyPI page, mark the release
   yanked with a reason. A yanked version stays downloadable for anyone who
   pinned it exactly, so existing lockfiles do not break, but no new resolution
   will select it. This is the right tool for "this version is wrong", and it is
   reversible.
2. **Publish the fix as a new patch version.** Tag it; the same pipeline runs,
   including the install-from-the-index verification that should have caught the
   defect.

Deleting a release is almost never correct: it breaks every environment that
pinned it and it erases the record of what was published. `v0.6.0` was handled
this way — it remains published and immutable, its release notes carry a warning
banner, and `v0.6.1` supersedes it. The failure is in public history where it
belongs.

If a release is found to be wrong *before* PyPI publication, the pipeline has
already stopped: the TestPyPI install-and-verify step runs first, and PyPI is
never reached.

## Health check

There is no service to monitor. The equivalent checks are:

```bash
evidence-state demo --all                      # 12 of 12 pairs discriminated
evidence-state demo --benchmark composed --all # 6 of 6
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | evidence-state-mcp
```

Any of them failing on a fresh install is a release defect, and each runs in
CI on every push and in the release pipeline against the published artifact.

## What publication does not establish

A package on PyPI is a distribution channel, not evidence. It does not establish
production readiness, external validation, authenticated evidence, source truth,
or fitness for any consequential decision. The limitations shipped with each
release say so, and they are shipped with each release for that reason.
