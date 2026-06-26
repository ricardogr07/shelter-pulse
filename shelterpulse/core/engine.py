"""SimPy discrete-event simulation engine for the cat-shelter flow.

Cat flow:
  intake → assessment → (isolation if needed) → medical clearance
         → housing → (foster if available) → adoption-ready → adopted / transferred
"""

from __future__ import annotations

import dataclasses
from typing import Generator

import numpy as np
import simpy

from shelterpulse.core.schema import (
    CatAgeClass,
    CatIntakeProfile,
    HealthStatus,
    Scenario,
    SeasonalEvent,
)


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
    overflow_cat_days: int   # cat-days spent above housing capacity

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
    overflow_cat_days: int = 0
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


def _adoption_wait_days(profile: CatIntakeProfile, rng: np.random.Generator) -> float:
    """Days from adoption-ready to adoption/transfer event."""
    # Neonatals take longer; adults have higher transfer probability
    if profile.age_class == CatAgeClass.neonatal:
        return float(rng.gamma(3.0, 10.0))
    if profile.age_class == CatAgeClass.adult:
        return float(rng.exponential(12.0))
    return float(rng.gamma(2.0, 5.0))


def _current_intake_rate(scenario: Scenario, day: float) -> float:
    """Return effective intake rate at given simulation day, including seasonal multiplier."""
    rate = scenario.intake_rate_per_day
    for event in scenario.seasonal_events:
        if event.start_day <= day < event.start_day + event.duration_days:
            rate *= event.intake_multiplier
    return rate


# ── Cat lifecycle process ──────────────────────────────────────────────────────

def _cat_process(
    env: simpy.Environment,
    cat_id: int,
    profile: CatIntakeProfile,
    resources: dict[str, simpy.Resource],
    scenario: Scenario,
    counters: _Counters,
    rng: np.random.Generator,
) -> Generator:
    """SimPy process representing one cat's journey through the shelter."""

    arrival_day = env.now / 24.0
    counters.total_intake += 1
    counters.total_cost += scenario.cost_model.variable_per_cat_day  # first day

    # 1. Intake assessment (needs vet-tech or animal-care time)
    assessment_h = _assessment_hours(profile, rng)
    with resources["vet_tech"].request() as req:
        yield req
        counters.vet_tech_busy_hours += assessment_h
        yield env.timeout(assessment_h)

    # 2. Isolation (if required) — competes for isolation slots
    isolation_d = _isolation_days(profile, rng)
    if isolation_d > 0:
        with resources["isolation"].request() as req:
            yield req
            yield env.timeout(isolation_d * 24.0)

    # 3. Medical clearance (vet-tech time)
    clearance_h = _medical_clearance_hours(profile, rng)
    if clearance_h > 0:
        with resources["vet_tech"].request() as req:
            yield req
            counters.vet_tech_busy_hours += clearance_h
            counters.total_cost += scenario.cost_model.medical_event_cost
            yield env.timeout(clearance_h)

    # 4. Enter general housing (may overflow if at capacity)
    with resources["housing"].request() as req:
        yield req
        counters.total_cost += scenario.cost_model.variable_per_cat_day

        # 5. Foster placement attempt (foster coordinator time)
        foster_placed = False
        if resources["foster"].capacity > 0:
            coord_h = float(rng.exponential(0.5))
            with resources["foster_coordinator"].request() as coord_req:
                yield coord_req
                counters.foster_coordinator_busy_hours += coord_h
                yield env.timeout(coord_h)
            foster_placed = True
            counters.total_cost += scenario.foster_network.supply_cost_per_cat_day

        # 6. Wait until adoption-ready (animal care maintains the cat)
        wait_d = _adoption_wait_days(profile, rng)
        care_h_per_day = 0.5 if profile.age_class == CatAgeClass.neonatal else 0.25
        counters.animal_care_busy_hours += wait_d * care_h_per_day
        counters.total_cost += scenario.cost_model.variable_per_cat_day * wait_d
        yield env.timeout(wait_d * 24.0)

    # 7. Exit: adopted or transferred
    exit_day = env.now / 24.0
    stay_days = exit_day - arrival_day

    # Adults have higher transfer rate; juveniles/kittens almost always adopted
    transfer_prob = 0.15 if profile.age_class == CatAgeClass.adult else 0.03
    if rng.random() < transfer_prob:
        counters.transferred += 1
    else:
        counters.adopted += 1

    counters.exit_stay_days.append(stay_days)


# ── Intake generator ───────────────────────────────────────────────────────────

def _intake_generator(
    env: simpy.Environment,
    scenario: Scenario,
    resources: dict[str, simpy.Resource],
    counters: _Counters,
    rng: np.random.Generator,
) -> Generator:
    """Generate cat arrivals using a non-homogeneous Poisson process."""
    weights = np.array([p.weight for p in scenario.intake_profiles])
    profiles = list(scenario.intake_profiles)

    while env.now < scenario.duration_days * 24.0:
        day = env.now / 24.0
        rate = _current_intake_rate(scenario, day)
        inter_arrival_hours = float(rng.exponential(24.0 / rate))
        yield env.timeout(inter_arrival_hours)

        if env.now >= scenario.duration_days * 24.0:
            break

        profile = profiles[rng.choice(len(profiles), p=weights)]
        env.process(
            _cat_process(env, counters.total_intake, profile, resources, scenario, counters, rng)
        )


# ── Metrics sampler ────────────────────────────────────────────────────────────

def _metrics_sampler(
    env: simpy.Environment,
    resources: dict[str, simpy.Resource],
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

        if housing_occ >= scenario.housing_capacity:
            counters.overflow_cat_days += 1  # 1 hour overflow ≈ 1/24 cat-days; approximate as 1 per hour

        # Daily fixed cost (charged once per 24 samples)
        if int(env.now) % 24 == 0:
            counters.total_cost += scenario.cost_model.fixed_per_day


# ── Public entry point ─────────────────────────────────────────────────────────

def run_simulation(scenario: Scenario, seed: int) -> SimulationResult:
    """Run one replication of the shelter simulation and return aggregated results.

    Args:
        scenario: Validated scenario configuration.
        seed: Random seed for this replication (use different seeds per replication).

    Returns:
        SimulationResult with flow counts, utilization, and financial metrics.
    """
    rng = np.random.default_rng(seed)
    env = simpy.Environment()
    counters = _Counters()

    # Build workforce capacity from scenario (hours → workers available simultaneously)
    vet_tech_capacity = max(1, int(
        sum(w.fte for w in scenario.workforce if w.role.value == "vet_tech")
    ))
    animal_care_capacity = max(1, int(
        sum(w.fte for w in scenario.workforce if w.role.value == "animal_care")
    ))
    foster_coord_capacity = max(1, int(
        sum(w.fte for w in scenario.workforce if w.role.value == "foster_coordinator")
    ))

    resources: dict[str, simpy.Resource] = {
        "vet_tech": simpy.Resource(env, capacity=vet_tech_capacity),
        "animal_care": simpy.Resource(env, capacity=animal_care_capacity),
        "foster_coordinator": simpy.Resource(env, capacity=foster_coord_capacity),
        "housing": simpy.Resource(env, capacity=scenario.housing_capacity),
        "isolation": simpy.Resource(env, capacity=scenario.isolation_capacity),
        "foster": simpy.Resource(env, capacity=scenario.foster_network.capacity),
    }

    env.process(_intake_generator(env, scenario, resources, counters, rng))
    env.process(_metrics_sampler(env, resources, counters, scenario))
    env.run(until=scenario.duration_days * 24.0)

    # Cats still in shelter at end of simulation
    counters.still_in_shelter = (
        counters.total_intake - counters.adopted - counters.transferred
    )

    # Workforce utilization: busy hours / total available hours
    total_days = scenario.duration_days
    vet_available = sum(
        w.fte * w.hours_per_day * total_days
        for w in scenario.workforce if w.role.value == "vet_tech"
    )
    care_available = sum(
        w.fte * w.hours_per_day * total_days
        for w in scenario.workforce if w.role.value == "animal_care"
    )
    coord_available = sum(
        w.fte * w.hours_per_day * total_days
        for w in scenario.workforce if w.role.value == "foster_coordinator"
    )

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
