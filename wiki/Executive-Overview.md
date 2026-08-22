# Executive overview

Evidence-State I/O prevents a specific decision error: treating a valid empty
tool result as proof that the sought condition is absent. The risk appears in
threat hunting, monitoring, inventory, compliance review, and investigation
whenever access, coverage, freshness, finality, or source health is incomplete.

The product inserts a deterministic evidence-sufficiency contract between a
read-only observation tool and its consumer. It either permits a qualified,
scope-preserving negative or rejects the negative and preserves uncertainty.
It does not authorize actions, certify source truth, or prove universal absence.

The executive decision gate is evidence-based: first reproduce the bounded
candidate and paired benchmark, then conduct discovery and an authorized shadow
evaluation. Investment beyond the prototype depends on the published go/no-go
thresholds, not on a polished demonstration.

See [Product scope and non-goals](Product-Scope-and-Non-Goals),
[Roadmap](Roadmap), and [Known limitations](Known-Limitations-and-Open-Questions).
