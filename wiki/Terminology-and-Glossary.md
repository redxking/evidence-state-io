# Terminology and glossary

- **Empty observation:** a tool execution that returned zero matches.
- **Scoped negative:** a qualified conclusion limited to declared evidence scope.
- **Evidence sufficiency:** whether required evidence conditions support that conclusion.
- **Finality horizon:** the earliest point after which the governed late-arrival and reopen windows have closed.
- **Coverage profile:** application-controlled assumptions for source population, retention, detection, freshness, and finality.
- **Trust selection:** the exact registry snapshot and profile reference selected outside the producer request.
- **Replay certificate:** an unsigned deterministic record binding request, evidence, policy, profile, trust context, and decision.
- **Fail closed:** reject the negative claim when required evidence is missing, malformed, contradictory, stale, ambiguous, unsupported, or unverifiable.

Terms such as “trusted,” “verified,” and “certificate” are bounded to the local
contract; they do not imply cryptographic identity, independent custody, or
external certification.
