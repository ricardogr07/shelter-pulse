"""Dollar→resource adapters: translate budget allocations into simulation parameter deltas."""

from __future__ import annotations

import dataclasses

from shelterpulse.core.schema import InterventionType, Scenario


@dataclasses.dataclass(frozen=True)
class InterventionParams:
    """Additive adjustments applied on top of the base scenario for one candidate."""

    extra_isolation_slots: int
    vet_service_time_multiplier: float
    extra_foster_slots: int
    foster_coordination_time_multiplier: float
    adoption_wait_multiplier: float


def _effect_params(scenario: Scenario, intervention_type: InterventionType) -> dict[str, float]:
    """Return the configured effect parameters for one intervention."""
    for intervention in scenario.interventions:
        if intervention.type == intervention_type:
            return intervention.effect_params
    return {}


def resolve_intervention(
    foster_support: float,
    clinic_hours: float,
    temporary_isolation: float,
    adoption_events: float,
    scenario: Scenario,
) -> InterventionParams:
    """Convert budget shares into concrete resource deltas.

    Effect sizes come from the validated scenario rather than hidden constants.
    Hour-based effects reduce service time in proportion to the additional
    daily hours relative to the configured baseline workforce capacity.
    """
    budget = scenario.total_intervention_budget

    foster_budget = foster_support * budget
    clinic_budget = clinic_hours * budget
    isolation_budget = temporary_isolation * budget
    adoption_budget = adoption_events * budget

    foster_effects = _effect_params(scenario, InterventionType.foster_support)
    clinic_effects = _effect_params(scenario, InterventionType.extra_clinic_hours)
    isolation_effects = _effect_params(scenario, InterventionType.temporary_isolation)
    adoption_effects = _effect_params(scenario, InterventionType.adoption_events)

    extra_foster_slots = int(
        foster_budget * foster_effects.get("capacity_increase_per_dollar", 0.0)
    )
    extra_foster_coordinator_hours_per_day = (
        foster_budget * foster_effects.get("coordinator_hours_per_dollar", 0.0)
        / scenario.duration_days
    )
    extra_vet_tech_hours_per_day = (
        clinic_budget * clinic_effects.get("vet_hours_per_dollar", 0.0)
        / scenario.duration_days
    )
    extra_isolation_slots = int(
        isolation_budget * isolation_effects.get("slots_per_dollar", 0.0)
    )

    baseline_vet_hours_per_day = sum(
        workforce.fte * workforce.hours_per_day
        for workforce in scenario.workforce
        if workforce.role.value == "vet_tech"
    )
    baseline_coordinator_hours_per_day = sum(
        workforce.fte * workforce.hours_per_day
        for workforce in scenario.workforce
        if workforce.role.value == "foster_coordinator"
    )
    vet_service_time_multiplier = (
        baseline_vet_hours_per_day
        / (baseline_vet_hours_per_day + extra_vet_tech_hours_per_day)
        if baseline_vet_hours_per_day > 0
        else 1.0
    )
    foster_coordination_time_multiplier = (
        baseline_coordinator_hours_per_day
        / (
            baseline_coordinator_hours_per_day
            + extra_foster_coordinator_hours_per_day
        )
        if baseline_coordinator_hours_per_day > 0
        else 1.0
    )

    adoption_rate_increase = (
        adoption_budget
        * adoption_effects.get("adoption_rate_multiplier_per_dollar", 0.0)
    )
    adoption_wait_multiplier = max(0.5, 1.0 / (1.0 + adoption_rate_increase))

    return InterventionParams(
        extra_isolation_slots=extra_isolation_slots,
        vet_service_time_multiplier=vet_service_time_multiplier,
        extra_foster_slots=extra_foster_slots,
        foster_coordination_time_multiplier=foster_coordination_time_multiplier,
        adoption_wait_multiplier=adoption_wait_multiplier,
    )
