# Demo walkthrough

Open the [public demonstration](https://redxking.github.io/evidence-state-io/#demo).
Select **covered** and run it: the empty observation is accompanied by complete,
current, accessible, final evidence and produces `PERMIT_SCOPED_NEGATIVE`.
Then select **incomplete**: the visible result remains empty, but incomplete
pagination produces `REJECT_NEGATIVE` and preserves uncertainty.

Try stale, ambiguous, conflicting, tampered, and invalid cases; edit or upload
synthetic JSON; inspect canonical input, reason codes, hashes, and trace; then
download the synthetic receipt. The browser implementation is a JavaScript
demonstration reference tested in CI against Python-generated golden fixtures.
It produces no live effect and fails closed when assets or inputs are invalid.
