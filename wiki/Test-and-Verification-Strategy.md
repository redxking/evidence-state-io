# Test and verification strategy

The gate includes unit, schema, contract-mutation, integration, golden-vector,
determinism, replay, invariant, negative, adversarial, packaging, browser-parity,
and clean-start checks. Every golden scenario is repeated at least 100 times for
byte-identical deterministic output. The frozen deterministic core enforces at
least 90% branch coverage; operational continuation tooling has separate
functional tests because it intentionally observes Git and wall time.

Python 3.11, 3.12, and 3.13 are supported. CI, installed-wheel verification,
and clean-clone reproduction are distinct gates. Green tests do not prove
external validation or operational effectiveness.
