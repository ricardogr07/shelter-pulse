"""Regression tests for scientific semantics described by the whitepaper."""

from pathlib import Path

import pytest
import simpy

from shelterpulse.core.engine import (
    _Counters,
    _build_resources,
    _generate_arrivals,
    _metrics_sampler,
    run_simulation,
)
from shelterpulse.core.interventions import resolve_intervention
from shelterpulse.core.schema import load_scenario
from shelterpulse.optimize.interface import evaluate_candidate
from shelterpulse.optimize.workflow import CandidateAllocation


WHISKER_HAVEN = Path(__file__).parents[2] / "scenarios" / "whisker_haven.yaml"


@pytest.fixture(scope="module")
def scenario():
    return load_scenario(WHISKER_HAVEN)


def test_arrival_schedule_is_reproducible_and_source_aligned(scenario):
    first = _generate_arrivals(scenario, seed=42)
    second = _generate_arrivals(scenario, seed=42)

    assert first == second
    assert first
    assert all(first[i].time_hours < first[i + 1].time_hours for i in range(len(first) - 1))


def test_overflow_integrates_housing_queue_length_as_cat_days(scenario):
    one_day = scenario.model_copy(update={"duration_days": 1})
    env = simpy.Environment()
    housing = simpy.Resource(env, capacity=1)
    isolation = simpy.Resource(env, capacity=1)
    resources = {"housing": housing, "isolation": isolation}
    counters = _Counters()

    housing.request()  # one cat occupies housing
    housing.request()  # two cats wait for the full day
    housing.request()
    env.process(_metrics_sampler(env, resources, counters, one_day))
    env.run(until=24.1)

    assert counters.overflow_cat_days == pytest.approx(2.0)


def test_workforce_resources_use_concurrent_service_capacity(scenario):
    intervention = resolve_intervention(0.0, 1.0, 0.0, 0.0, scenario)
    env = simpy.Environment()
    resources = _build_resources(env, scenario, intervention)

    assert resources["vet_tech"].capacity == 2
    assert isinstance(resources["vet_tech"], simpy.Resource)
    assert intervention.vet_service_time_multiplier < 1.0


def test_allocations_share_the_same_exogenous_intake_schedule(scenario):
    zero = resolve_intervention(0.0, 0.0, 0.0, 0.0, scenario)
    events = resolve_intervention(0.0, 0.0, 0.0, 1.0, scenario)

    zero_result = run_simulation(scenario, seed=42, intervention=zero)
    events_result = run_simulation(scenario, seed=42, intervention=events)

    assert zero_result.total_intake == events_result.total_intake


def test_foster_capacity_changes_congested_scenario_outcome(scenario):
    constrained = scenario.model_copy(update={
        "duration_days": 30,
        "housing_capacity": 4,
        "foster_network": scenario.foster_network.model_copy(update={"capacity": 1}),
        "seasonal_events": [],
    })
    seeds = [42, 43, 44]
    zero = evaluate_candidate(CandidateAllocation(0.0, 0.0, 0.0, 0.0), constrained, seeds)
    foster = evaluate_candidate(CandidateAllocation(1.0, 0.0, 0.0, 0.0), constrained, seeds)

    assert foster.mean_overflow_cat_days < zero.mean_overflow_cat_days


def test_operating_cost_is_not_misused_as_intervention_budget(scenario):
    result = evaluate_candidate(
        CandidateAllocation(0.25, 0.25, 0.25, 0.25),
        scenario,
        [42, 43],
    )

    assert result.is_feasible
    assert result.mean_total_cost > scenario.total_intervention_budget
