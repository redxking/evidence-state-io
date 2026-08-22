> The versioned corpus and oracle now ship inside the package at
> `src/evidence_state_io/benchmarks/`. They were moved there so an
> installed distribution resolves them from the package itself rather
> than from the caller's working directory. This directory keeps the
> custody notes.

# EmptyBench P0 seed artifacts

The seed benchmark separates inputs from expected decisions:

- `emptybench-p0-corpus.json` contains one canonical covered request and 12
  matched control/fault pairs expressed as deterministic JSON Pointer
  replacements. It contains no machine-scored expected verdict or reason
  fields; `control` and `fault` name experimental roles but do not determine
  the oracle's expected decision.
- `emptybench-p0-oracle.json` contains the declarative decision rules and case
  assignments. It binds the exact corpus schema, version, and digest.

Both artifacts use `esio-canonical-json-0.1` and carry SHA-256 integrity
digests. The oracle digest must also be retained outside the oracle artifact;
the candidate implementation pins the seed value for its built-in demo, and
the custom CLI requires `--expected-oracle-digest`.

The typed Python scoring API enforces the same boundary: callers must provide
the separately retained `expected_oracle_digest`. Before expansion or scoring,
the runner serializes and strictly reparses the corpus, oracle, and evaluation
context, then compares every expanded case with the corpus-bound definition.
Previously parsed or directly constructed mutable objects are therefore not a
trusted bypass around canonical validation.

Current seed custody values:

- Corpus: `sha256:c054b681a6c86cd0009aa07347f25e660ccee9d0c648fa4acf537de412591f93`
- Oracle: `sha256:543bf22c308ed1ee1436f6bd8bb9cc7353680c09d41b849c1af9216a8c730339`

These digests detect mutation only when the expected oracle digest is kept in
separate trusted custody. They are not signatures, do not authenticate the
artifact authors, and do not establish that the declarative oracle is
scientifically correct. The seed is a deterministic regression corpus, not the
frozen held-out research campaign described in the validation plan.
