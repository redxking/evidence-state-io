# Operations and troubleshooting

Use `./scripts/setup.sh` after source changes, `./scripts/test.sh` for the source
suite, `./scripts/check.sh` for static and browser checks, and
`./scripts/acceptance.sh` for the isolated acceptance gate. A stale installed
package is reported explicitly; rerun setup rather than bypassing the check.

The bounded continuation controller is available through:

```bash
python -m evidence_state_io.advance --repo . --status
python -m evidence_state_io.advance --repo . --reconcile --remote
```

It uses a nonblocking repository lock, invalidates watched evidence after
changes, and stops for engineering or external action. It is not a daemon and
does not make gateway decisions.
