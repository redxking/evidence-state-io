"""Evidence-State I/O public API."""

from .canonical import (
    CANONICALIZATION_PROFILE,
    DIGEST_ALGORITHM,
    canonical_digest,
    canonical_json_bytes,
    verify_canonical_digest,
)
from .coverage import (
    CoverageAssessment,
    CoverageComponent,
    CoverageIssue,
    CoveragePolicy,
    evaluate_coverage,
)
from .emptybench import (
    EmptyBenchCase,
    EmptyBenchOutcome,
    EmptyBenchReport,
    demo_cases,
    parse_cases,
    run_emptybench,
    run_seed_emptybench,
    seed_cases,
)
from .gate import (
    GateDecision,
    GateReason,
    NegativeClaimPolicy,
    NegativeClaimRequest,
    evaluate_negative_claim,
)
from .models import (
    ClaimMode,
    CoverageEvidence,
    EvidenceEnvelope,
    EvidenceState,
    ModelValidationError,
    PopulationBasis,
    QueryScope,
    SourceDescriptor,
)

__all__ = [
    "CANONICALIZATION_PROFILE",
    "DIGEST_ALGORITHM",
    "ClaimMode",
    "CoverageAssessment",
    "CoverageComponent",
    "CoverageEvidence",
    "CoverageIssue",
    "CoveragePolicy",
    "EmptyBenchCase",
    "EmptyBenchOutcome",
    "EmptyBenchReport",
    "EvidenceEnvelope",
    "EvidenceState",
    "GateDecision",
    "GateReason",
    "ModelValidationError",
    "NegativeClaimPolicy",
    "NegativeClaimRequest",
    "PopulationBasis",
    "QueryScope",
    "SourceDescriptor",
    "canonical_digest",
    "canonical_json_bytes",
    "demo_cases",
    "evaluate_coverage",
    "evaluate_negative_claim",
    "parse_cases",
    "run_emptybench",
    "run_seed_emptybench",
    "seed_cases",
    "verify_canonical_digest",
]

__version__ = "0.1.0"
