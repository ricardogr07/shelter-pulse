"""Baseline allocation strategies for benchmarking the JAX-BO optimizer."""

from __future__ import annotations

from shelterpulse.optimize.workflow import CandidateAllocation

# Named functions kept for backwards-compat with test imports
def equal_allocation() -> CandidateAllocation:
    return CandidateAllocation(0.25, 0.25, 0.25, 0.25)

def all_in_foster() -> CandidateAllocation:
    return CandidateAllocation(1.0, 0.0, 0.0, 0.0)

def all_in_events() -> CandidateAllocation:
    return CandidateAllocation(0.0, 0.0, 0.0, 1.0)

def domain_heuristic() -> CandidateAllocation:
    # ponytail: clinic hours made overflow *worse* in testing — not included
    return CandidateAllocation(0.40, 0.0, 0.20, 0.40)

def zero_allocation() -> CandidateAllocation:
    return CandidateAllocation(0.0, 0.0, 0.0, 0.0)


ALL_BASELINES: dict[str, CandidateAllocation] = {
    "equal": equal_allocation(),
    "all_in_foster": all_in_foster(),
    "all_in_events": all_in_events(),
    "domain_heuristic": domain_heuristic(),
    "zero": zero_allocation(),
}
