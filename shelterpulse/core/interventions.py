"""Dollar→resource adapters: translate budget allocations into simulation parameter deltas."""

from __future__ import annotations

import dataclasses

from shelterpulse.core.schema import Scenario


@dataclasses.dataclass(frozen=True)
class InterventionParams:
    """Additive adjustments applied on top of the base scenario for one candidate."""

    extra_isolation_slots: int
    extra_vet_tech_fte: float
    extra_foster_slots: int
    adoption_wait_multiplier: float


def resolve_intervention(
    foster_support: float,
    clinic_hours: float,
    temporary_isolation: float,
    adoption_events: float,
    scenario: Scenario,
) -> InterventionParams:
    """Convert budget shares into concrete resource deltas."""
    budget = scenario.total_intervention_budget
    period = scenario.duration_days / 30.0

    foster_budget = foster_support * budget
    clinic_budget = clinic_hours * budget
    isolation_budget = temporary_isolation * budget
    adoption_budget = adoption_events * budget

    extra_foster_slots = int(foster_budget / (200.0 * period))
    extra_vet_tech_fte = min(2.0, clinic_budget / (2000.0 * period))
    extra_isolation_slots = int(isolation_budget / (500.0 * period))
    adoption_wait_multiplier = max(0.5, 0.85 ** int(adoption_budget / 1000.0))

    return InterventionParams(
        extra_isolation_slots=extra_isolation_slots,
        extra_vet_tech_fte=extra_vet_tech_fte,
        extra_foster_slots=extra_foster_slots,
        adoption_wait_multiplier=adoption_wait_multiplier,
    )
