"""Tests for the intervention adapter layer."""

from pathlib import Path

import pytest

from shelterpulse.core.interventions import InterventionParams, resolve_intervention
from shelterpulse.core.schema import load_scenario
from shelterpulse.optimize.workflow import CandidateAllocation


def _resolve(alloc: CandidateAllocation, scenario):
    return resolve_intervention(
        alloc.foster_support, alloc.clinic_hours,
        alloc.temporary_isolation, alloc.adoption_events,
        scenario,
    )

WHISKER_HAVEN = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"


@pytest.fixture(scope="module")
def scenario():
    return load_scenario(WHISKER_HAVEN)


def test_zero_allocation_produces_no_change(scenario):
    from shelterpulse.optimize.baselines import zero_allocation

    params = _resolve(zero_allocation(), scenario)
    assert params.extra_isolation_slots == 0
    assert params.extra_foster_slots == 0
    assert abs(params.extra_vet_tech_fte) < 0.001
    assert abs(params.adoption_wait_multiplier - 1.0) < 0.001


def test_foster_support_increases_capacity(scenario):
    alloc = CandidateAllocation(foster_support=1.0, clinic_hours=0.0, temporary_isolation=0.0, adoption_events=0.0)
    params = _resolve(alloc, scenario)
    assert params.extra_foster_slots > 0


def test_clinic_hours_increases_fte(scenario):
    alloc = CandidateAllocation(foster_support=0.0, clinic_hours=1.0, temporary_isolation=0.0, adoption_events=0.0)
    params = _resolve(alloc, scenario)
    assert params.extra_vet_tech_fte > 0


def test_isolation_increases_slots(scenario):
    alloc = CandidateAllocation(foster_support=0.0, clinic_hours=0.0, temporary_isolation=1.0, adoption_events=0.0)
    params = _resolve(alloc, scenario)
    assert params.extra_isolation_slots > 0


def test_adoption_events_reduces_wait(scenario):
    alloc = CandidateAllocation(foster_support=0.0, clinic_hours=0.0, temporary_isolation=0.0, adoption_events=1.0)
    params = _resolve(alloc, scenario)
    assert params.adoption_wait_multiplier < 1.0


def test_adoption_multiplier_clamped_at_half(scenario):
    alloc = CandidateAllocation(foster_support=0.0, clinic_hours=0.0, temporary_isolation=0.0, adoption_events=1.0)
    params = _resolve(alloc, scenario)
    assert params.adoption_wait_multiplier >= 0.5


def test_vet_tech_fte_capped_at_two(scenario):
    alloc = CandidateAllocation(foster_support=0.0, clinic_hours=1.0, temporary_isolation=0.0, adoption_events=0.0)
    params = _resolve(alloc, scenario)
    assert params.extra_vet_tech_fte <= 2.0


def test_intervention_reduces_overflow(scenario):
    """Domain heuristic vs zero should produce different simulation results."""
    from shelterpulse.optimize.baselines import zero_allocation, domain_heuristic
    from shelterpulse.optimize.interface import evaluate_candidate

    seeds = list(range(42, 46))
    zero = evaluate_candidate(zero_allocation(), scenario, seeds)
    heuristic = evaluate_candidate(domain_heuristic(), scenario, seeds)
    assert zero.mean_overflow_cat_days != heuristic.mean_overflow_cat_days or \
           zero.mean_total_cost != heuristic.mean_total_cost
