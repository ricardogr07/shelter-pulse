"""Baseline allocation strategies for benchmarking the JAX-BO optimizer."""

from __future__ import annotations

from shelterpulse.optimize.workflow import CandidateAllocation


def equal_allocation() -> CandidateAllocation:
    """Equal budget split across all four intervention types."""
    return CandidateAllocation(
        foster_support=0.25,
        clinic_hours=0.25,
        temporary_isolation=0.25,
        adoption_events=0.25,
    )


def all_in_foster() -> CandidateAllocation:
    """All budget into foster support — single-intervention baseline."""
    return CandidateAllocation(
        foster_support=1.0,
        clinic_hours=0.0,
        temporary_isolation=0.0,
        adoption_events=0.0,
    )


def domain_heuristic() -> CandidateAllocation:
    """Domain-knowledge heuristic: prioritise the known bottleneck (isolation + clinic)."""
    return CandidateAllocation(
        foster_support=0.10,
        clinic_hours=0.40,
        temporary_isolation=0.40,
        adoption_events=0.10,
    )


def zero_allocation() -> CandidateAllocation:
    """No intervention budget spent — pure baseline for cost comparison."""
    return CandidateAllocation(
        foster_support=0.0,
        clinic_hours=0.0,
        temporary_isolation=0.0,
        adoption_events=0.0,
    )


ALL_BASELINES: dict[str, CandidateAllocation] = {
    "equal": equal_allocation(),
    "all_in_foster": all_in_foster(),
    "domain_heuristic": domain_heuristic(),
    "zero": zero_allocation(),
}
