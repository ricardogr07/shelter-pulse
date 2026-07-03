"""SimPy discrete-event simulation engine for the cat-shelter flow.

Cat flow:
  intake → assessment → (isolation if needed) → medical clearance
         → housing → (foster if available) → adoption-ready → adopted / transferred
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Generator

import numpy as np
import simpy

from shelterpulse.core.schema import (
    CatAgeClass,
    CatIntakeProfile,
    HealthStatus,
    Scenario,
    SeasonalEvent,
)

if TYPE_CHECKING:
    from shelterpulse.core.interventions import InterventionParams


# ── Result dataclasses ────────────────────────────────────────────────────────

@dataclasses.dataclass(frozen=True)
class SimulationResult:
    """Aggregate outcomes from one simulation replication."""

    total_intake: int
    adopted: int
    transferred: int
    still_in_shelter: int

    # Queue / capacity metrics
    peak_isolation_queue: int
    mean_isolation_queue: float
    peak_housing_occupancy: int
    mean_housing_occupancy: float

    # Financial
    total_cost: float
    overflow_cat_days: float   # integral of housing queue length over days

    # Workforce utilization (role → fraction of available hours used, 0–1)
    vet_tech_utilization: float
    animal_care_utilization: float
    foster_coordinator_utilization: float

    # Derived
    mean_length_of_stay: float   # days, cats that exited


# ── Internal mutable state (not exposed outside engine) ───────────────────────

@dataclasses.dataclass
class _Counters:
    total_intake: int = 0
    adopted: int = 0
    transferred: int = 0
    still_in_shelter: int = 0
    overflow_cat_days: float = 0.0
    total_cost: float = 0.0

    # For mean length-of-stay calculation
    exit_stay_days: list[float] = dataclasses.field(default_factory=list)

    # Occupancy / queue snapshots (sampled every hour)
    isolation_queue_samples: list[int] = dataclasses.field(default_factory=list)
    housing_occupancy_samples: list[int] = dataclasses.field(default_factory=list)
    peak_isolation_queue: int = 0
    peak_housing_occupancy: int = 0

    # Workforce busy-hours accumulators
    vet_tech_busy_hours: float = 0.0
    animal_care_busy_hours: float = 0.0
    foster_coordinator_busy_hours: float = 0.0


@dataclasses.dataclass(frozen=True)
class _Arrival:
    """One pre-generated intake event shared by every allocation for a seed."""

    cat_id: int
    time_hours: float
    profile: CatIntakeProfile


@dataclasses.dataclass
class _CatRandomStreams:
    """Independent per-cat streams keep CRN draws synchronized by source."""

    assessment: np.random.Generator
    isolation: np.random.Generator
    clearance: np.random.Generator
    adoption: np.random.Generator
    transfer: np.random.Generator
    foster_coordination: np.random.Generator


# ── Service time helpers ───────────────────────────────────────────────────────

def _assessment_hours(profile: CatIntakeProfile, rng: np.random.Generator) -> float:
    """Intake assessment duration in hours. Neonatals take longer."""
    base = 0.5 if profile.age_class == CatAgeClass.neonatal else 0.25
    return float(rng.exponential(base))


def _medical_clearance_hours(profile: CatIntakeProfile, rng: np.random.Generator) -> float:
    """Hours to complete medical clearance. Medical-hold cats need more time."""
    if profile.health_status in (HealthStatus.medical_hold, HealthStatus.critical):
        return float(rng.gamma(3.0, 8.0))   # mean ~24h, heavy tail
    if profile.health_status == HealthStatus.isolation_required:
        return float(rng.gamma(2.0, 12.0))  # mean ~24h in isolation
    return float(rng.exponential(4.0))      # healthy: quick check


def _isolation_days(profile: CatIntakeProfile, rng: np.random.Generator) -> float:
    """Days a cat must spend in isolation before joining general population."""
    if profile.health_status != HealthStatus.isolation_required:
        return 0.0
    return float(rng.gamma(2.0, 7.0))  # mean ~14 days


def _adoption_wait_days(profile: CatIntakeProfile, rng: np.random.Generator, multiplier: float = 1.0) -> float:
    """Days from adoption-ready to adoption/transfer event."""
    if profile.age_class == CatAgeClass.neonatal:
        raw = float(rng.gamma(3.0, 10.0))
    elif profile.age_class == CatAgeClass.adult:
        raw = float(rng.exponential(12.0))
    else:
        raw = float(rng.gamma(2.0, 5.0))
    return raw * multiplier


def _current_intake_rate(scenario: Scenario, day: float) -> float:
    """Return effective intake rate at given simulation day, including seasonal multiplier."""
    rate = scenario.intake_rate_per_day
    for event in scenario.seasonal_events:
        if event.start_day <= day < event.start_day + event.duration_days:
            rate *= event.intake_multiplier
    return rate


def _generate_arrivals(scenario: Scenario, seed: int) -> list[_Arrival]:
    """Generate an exact piecewise NHPP intake schedule for one replication.

    The schedule is generated before any cat lifecycle process starts. Reusing
    the same seed therefore gives every allocation identical arrival times and
    intake profiles, independent of intervention-driven event ordering.
    """
    arrival_seed, profile_seed = np.random.SeedSequence(seed).spawn(2)
    arrival_rng = np.random.default_rng(arrival_seed)
    profile_rng = np.random.default_rng(profile_seed)
    profiles = list(scenario.intake_profiles)
    weights = np.array([profile.weight for profile in profiles])
    change_days = {
        0.0,
        *(
            float(day)
            for event in scenario.seasonal_events
            for day in (event.start_day, event.start_day + event.duration_days)
            if day < scenario.duration_days
        ),
    }
    max_rate = max(
        _current_intake_rate(scenario, day + 1e-9)
        for day in change_days
    )
    horizon_hours = scenario.duration_days * 24.0

    arrivals: list[_Arrival] = []
    time_hours = 0.0
    while time_hours < horizon_hours:
        time_hours += float(arrival_rng.exponential(24.0 / max_rate))
        if time_hours >= horizon_hours:
            break
        current_rate = _current_intake_rate(scenario, time_hours / 24.0)
        if arrival_rng.random() > current_rate / max_rate:
            continue
        profile = profiles[int(profile_rng.choice(len(profiles), p=weights))]
        arrivals.append(
            _Arrival(
                cat_id=len(arrivals),
                time_hours=time_hours,
                profile=profile,
            )
        )
    return arrivals


def _make_cat_random_streams(seed: int, cat_id: int) -> _CatRandomStreams:
    """Create stable random streams for each stochastic lifecycle source."""
    child_seeds = np.random.SeedSequence([seed, cat_id]).spawn(6)
    generators = [np.random.default_rng(child_seed) for child_seed in child_seeds]
    return _CatRandomStreams(*generators)


def _wait_with_daily_care(
    env: simpy.Environment,
    animal_care: simpy.Resource,
    wait_days: float,
    care_hours_per_day: float,
) -> Generator:
    """Advance an in-shelter stay with one bounded animal-care task per day."""
    remaining_days = max(0.0, wait_days)
    while remaining_days > 1e-9:
        day_fraction = min(1.0, remaining_days)
        care_hours = care_hours_per_day * day_fraction
        with animal_care.request() as care_request:
            yield care_request
            yield env.timeout(care_hours)
        remaining_interval = max(0.0, day_fraction * 24.0 - care_hours)
        if remaining_interval:
            yield env.timeout(remaining_interval)
        remaining_days -= day_fraction


# ── Cat lifecycle process ──────────────────────────────────────────────────────

def _cat_process(
    env: simpy.Environment,
    cat_id: int,
    profile: CatIntakeProfile,
    resources: dict[str, Any],
    scenario: Scenario,
    counters: _Counters,
    random_streams: _CatRandomStreams,
    adoption_wait_multiplier: float = 1.0,
    vet_service_time_multiplier: float = 1.0,
    foster_coordination_time_multiplier: float = 1.0,
) -> Generator:
    """SimPy process representing one cat's journey through the shelter."""

    arrival_day = env.now / 24.0
    counters.total_intake += 1
    counters.total_cost += scenario.cost_model.variable_per_cat_day  # first day

    # 1. Intake assessment (needs vet-tech or animal-care time)
    assessment_h = (
        _assessment_hours(profile, random_streams.assessment)
        * vet_service_time_multiplier
    )
    with resources["vet_tech"].request() as vet_request:
        yield vet_request
        counters.vet_tech_busy_hours += assessment_h
        yield env.timeout(assessment_h)

    # 2. Isolation (if required) — competes for isolation slots
    isolation_d = _isolation_days(profile, random_streams.isolation)
    if isolation_d > 0:
        with resources["isolation"].request() as req:
            yield req
            yield env.timeout(isolation_d * 24.0)

    # 3. Medical clearance (vet-tech time)
    clearance_h = (
        _medical_clearance_hours(profile, random_streams.clearance)
        * vet_service_time_multiplier
    )
    if clearance_h > 0:
        with resources["vet_tech"].request() as vet_request:
            yield vet_request
            counters.vet_tech_busy_hours += clearance_h
            counters.total_cost += scenario.cost_model.medical_event_cost
            yield env.timeout(clearance_h)

    wait_d = _adoption_wait_days(
        profile,
        random_streams.adoption,
        adoption_wait_multiplier,
    )
    foster_eligible = (
        profile.age_class == CatAgeClass.neonatal
        or profile.health_status in (HealthStatus.medical_hold, HealthStatus.critical)
        or resources["housing"].count >= resources["housing"].capacity
    )
    foster_available = resources["foster"].count < resources["foster"].capacity

    # 4a. Eligible cats use foster capacity when an immediate slot is available.
    if foster_eligible and foster_available:
        with resources["foster"].request() as foster_req:
            yield foster_req
            coord_h = (
                float(random_streams.foster_coordination.exponential(0.5))
                * foster_coordination_time_multiplier
            )
            with resources["foster_coordinator"].request() as coordinator_request:
                yield coordinator_request
                counters.foster_coordinator_busy_hours += coord_h
                yield env.timeout(coord_h)
            counters.total_cost += (
                scenario.foster_network.supply_cost_per_cat_day * wait_d
            )
            yield env.timeout(wait_d * 24.0)
    else:
        # 4b. Other cats request general housing; this queue defines overflow.
        with resources["housing"].request() as housing_req:
            yield housing_req
            counters.total_cost += scenario.cost_model.variable_per_cat_day * wait_d
            care_h_per_day = (
                0.5 if profile.age_class == CatAgeClass.neonatal else 0.25
            )
            counters.animal_care_busy_hours += wait_d * care_h_per_day
            yield from _wait_with_daily_care(
                env,
                resources["animal_care"],
                wait_d,
                care_h_per_day,
            )

    # 7. Exit: adopted or transferred
    exit_day = env.now / 24.0
    stay_days = exit_day - arrival_day

    # Adults have higher transfer rate; juveniles/kittens almost always adopted
    transfer_prob = 0.15 if profile.age_class == CatAgeClass.adult else 0.03
    if random_streams.transfer.random() < transfer_prob:
        counters.transferred += 1
    else:
        counters.adopted += 1

    counters.exit_stay_days.append(stay_days)


# ── Intake generator ───────────────────────────────────────────────────────────

def _intake_generator(
    env: simpy.Environment,
    scenario: Scenario,
    resources: dict[str, Any],
    counters: _Counters,
    arrivals: list[_Arrival],
    seed: int,
    adoption_wait_multiplier: float = 1.0,
    vet_service_time_multiplier: float = 1.0,
    foster_coordination_time_multiplier: float = 1.0,
) -> Generator:
    """Replay a pre-generated intake schedule into the SimPy environment."""
    previous_time = 0.0
    for arrival in arrivals:
        yield env.timeout(arrival.time_hours - previous_time)
        previous_time = arrival.time_hours
        env.process(
            _cat_process(
                env,
                arrival.cat_id,
                arrival.profile,
                resources,
                scenario,
                counters,
                _make_cat_random_streams(seed, arrival.cat_id),
                adoption_wait_multiplier,
                vet_service_time_multiplier,
                foster_coordination_time_multiplier,
            )
        )


# ── Metrics sampler ────────────────────────────────────────────────────────────

def _metrics_sampler(
    env: simpy.Environment,
    resources: dict[str, Any],
    counters: _Counters,
    scenario: Scenario,
) -> Generator:
    """Sample queue depths and occupancy every hour for the duration."""
    end_time = scenario.duration_days * 24.0
    while env.now < end_time:
        yield env.timeout(1.0)  # sample every hour

        iso_q = len(resources["isolation"].queue)
        counters.isolation_queue_samples.append(iso_q)
        counters.peak_isolation_queue = max(counters.peak_isolation_queue, iso_q)

        housing_occ = resources["housing"].count
        counters.housing_occupancy_samples.append(housing_occ)
        counters.peak_housing_occupancy = max(counters.peak_housing_occupancy, housing_occ)

        # Integrate the number of cats waiting for housing over the one-hour
        # sample interval. One queued cat for 24 samples equals one cat-day.
        counters.overflow_cat_days += len(resources["housing"].queue) / 24.0

        # Daily fixed cost (charged once per 24 samples)
        if int(env.now) % 24 == 0:
            counters.total_cost += scenario.cost_model.fixed_per_day


# ── Public entry point ─────────────────────────────────────────────────────────

def _role_hours_per_day(scenario: Scenario, role: str) -> float:
    return sum(
        workforce.fte * workforce.hours_per_day
        for workforce in scenario.workforce
        if workforce.role.value == role
    )


def _build_resources(
    env: simpy.Environment,
    scenario: Scenario,
    intervention: "InterventionParams | None",
) -> dict[str, Any]:
    """Build physical resources and concurrent workforce service pools."""
    extra_isolation = intervention.extra_isolation_slots if intervention else 0
    extra_foster = intervention.extra_foster_slots if intervention else 0
    role_fte = {
        role: sum(
            workforce.fte
            for workforce in scenario.workforce
            if workforce.role.value == role
        )
        for role in ("vet_tech", "animal_care", "foster_coordinator")
    }

    return {
        "vet_tech": simpy.Resource(
            env,
            capacity=max(1, round(role_fte["vet_tech"])),
        ),
        "animal_care": simpy.Resource(
            env,
            capacity=max(1, round(role_fte["animal_care"])),
        ),
        "foster_coordinator": simpy.Resource(
            env,
            capacity=max(1, round(role_fte["foster_coordinator"])),
        ),
        "housing": simpy.Resource(env, capacity=scenario.housing_capacity),
        "isolation": simpy.Resource(
            env,
            capacity=scenario.isolation_capacity + extra_isolation,
        ),
        "foster": simpy.Resource(
            env,
            capacity=scenario.foster_network.capacity + extra_foster,
        ),
    }

def run_simulation(scenario: Scenario, seed: int, intervention: "InterventionParams | None" = None) -> SimulationResult:
    """Run one replication of the shelter simulation and return aggregated results.

    Args:
        scenario: Validated scenario configuration.
        seed: Random seed for this replication (use different seeds per replication).
        intervention: Optional resource deltas from budget allocation.

    Returns:
        SimulationResult with flow counts, utilization, and financial metrics.
    """
    env = simpy.Environment()
    counters = _Counters()
    resources = _build_resources(env, scenario, intervention)
    adoption_wait_multiplier = (
        intervention.adoption_wait_multiplier if intervention else 1.0
    )
    arrivals = _generate_arrivals(scenario, seed)

    env.process(
        _intake_generator(
            env,
            scenario,
            resources,
            counters,
            arrivals,
            seed,
            adoption_wait_multiplier,
            intervention.vet_service_time_multiplier if intervention else 1.0,
            intervention.foster_coordination_time_multiplier if intervention else 1.0,
        )
    )
    env.process(_metrics_sampler(env, resources, counters, scenario))
    env.run(until=scenario.duration_days * 24.0)

    # Cats still in shelter at end of simulation
    counters.still_in_shelter = (
        counters.total_intake - counters.adopted - counters.transferred
    )

    # Workforce utilization: busy hours / total available hours
    total_days = scenario.duration_days
    vet_available = _role_hours_per_day(scenario, "vet_tech") * total_days
    care_available = _role_hours_per_day(scenario, "animal_care") * total_days
    coord_available = _role_hours_per_day(scenario, "foster_coordinator") * total_days

    return SimulationResult(
        total_intake=counters.total_intake,
        adopted=counters.adopted,
        transferred=counters.transferred,
        still_in_shelter=counters.still_in_shelter,
        peak_isolation_queue=counters.peak_isolation_queue,
        mean_isolation_queue=(
            float(np.mean(counters.isolation_queue_samples))
            if counters.isolation_queue_samples else 0.0
        ),
        peak_housing_occupancy=counters.peak_housing_occupancy,
        mean_housing_occupancy=(
            float(np.mean(counters.housing_occupancy_samples))
            if counters.housing_occupancy_samples else 0.0
        ),
        total_cost=counters.total_cost,
        overflow_cat_days=counters.overflow_cat_days,
        vet_tech_utilization=min(1.0, counters.vet_tech_busy_hours / max(vet_available, 1.0)),
        animal_care_utilization=min(1.0, counters.animal_care_busy_hours / max(care_available, 1.0)),
        foster_coordinator_utilization=min(
            1.0, counters.foster_coordinator_busy_hours / max(coord_available, 1.0)
        ),
        mean_length_of_stay=(
            float(np.mean(counters.exit_stay_days)) if counters.exit_stay_days else 0.0
        ),
    )
