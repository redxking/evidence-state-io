# Integration guide

Place the gateway after a read-only observation adapter and before the AI or
human workflow that would phrase a negative conclusion. The adapter must
provide honest source identity, authorization context, accessible population,
query binding, pagination or partition completion, index time, exclusions,
errors, and observations. The application—not the result producer—must supply
the registry snapshot, trust selection, named policy, and evaluation time.

Treat `REJECT_NEGATIVE` as “insufficient evidence,” not as a positive finding.
Preserve the qualified statement and certificate with downstream records. Do
not use a permit as authority to close an incident or execute an action.
