# Problem definition

Zero matches describes an execution result. Absence is a stronger claim about
a bounded population and interval. The inference is unsupported when a source
was unavailable, access excluded records, pagination stopped early, data was
stale, the finality window remained open, filters removed records, or required
evidence contradicted itself.

Evidence-State I/O represents these conditions explicitly and evaluates them
before negative language is emitted. The first vertical is cyber investigation
and threat hunting, but the contract is domain-neutral.

The falsifiable question is: for the same visible empty result, can the system
retain supported scoped negatives while rejecting unsupported negatives caused
by controlled evidence faults? [EmptyBench](Benchmark-Methodology) supplies the
paired evaluation structure.
