"""Pydantic v2 models for scenario validation and loading."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CatAgeClass(str, Enum):
    neonatal = "neonatal"       # bottle-feeders, <4 weeks
    weaned_kitten = "weaned_kitten"  # 4–12 weeks
    juvenile = "juvenile"       # 3–6 months
    adult = "adult"             # 6+ months


class HealthStatus(str, Enum):
    healthy = "healthy"
    medical_hold = "medical_hold"
    isolation_required = "isolation_required"
    critical = "critical"


class WorkforceRole(str, Enum):
    vet_tech = "vet_tech"
    animal_care = "animal_care"
    foster_coordinator = "foster_coordinator"
    adoption_counselor = "adoption_counselor"


class InterventionType(str, Enum):
    foster_support = "foster_support"
    extra_clinic_hours = "extra_clinic_hours"
    temporary_isolation = "temporary_isolation"
    adoption_events = "adoption_events"


class CatIntakeProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    age_class: CatAgeClass
    health_status: HealthStatus
    weight: float = Field(gt=0, description="Arrival fraction (0–1) of this profile")

    @field_validator("weight")
    @classmethod
    def weight_in_range(cls, v: float) -> float:
        if not 0 < v <= 1:
            raise ValueError("weight must be in (0, 1]")
        return v


class WorkforcePool(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    role: WorkforceRole
    fte: float = Field(gt=0, description="Full-time equivalents")
    hours_per_day: float = Field(gt=0, le=24)
    skills: list[str] = Field(default_factory=list)


class FosterNetwork(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    capacity: int = Field(gt=0, description="Maximum simultaneous foster placements")
    coordinator_hours_per_week: float = Field(gt=0)
    supply_cost_per_cat_day: float = Field(ge=0)


class SeasonalEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    start_day: int = Field(ge=0)
    duration_days: int = Field(gt=0)
    intake_multiplier: float = Field(gt=0)


class InterventionDef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: InterventionType
    budget_share: float = Field(ge=0, le=1, description="Fraction of total budget allocated")
    effect_params: dict[str, float] = Field(default_factory=dict)


class CostModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    fixed_per_day: float = Field(ge=0, description="Daily fixed operating cost (USD)")
    variable_per_cat_day: float = Field(ge=0, description="Variable cost per cat per day (USD)")
    medical_event_cost: float = Field(ge=0, description="Average cost per medical event (USD)")
    adoption_event_cost: float = Field(ge=0, description="Cost per adoption event (USD)")


class Scenario(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str = "0.1"
    description: str = ""

    duration_days: int = Field(gt=0, description="Simulation horizon in days")
    seed: int = Field(description="Base random seed for reproducibility")
    n_replications: int = Field(default=64, gt=0, description="Monte Carlo replications")

    intake_rate_per_day: float = Field(gt=0, description="Mean cat arrivals per day (baseline)")
    intake_profiles: list[CatIntakeProfile] = Field(min_length=1)

    housing_capacity: int = Field(gt=0, description="Total housing slots (cages + rooms)")
    isolation_capacity: int = Field(gt=0, description="Dedicated isolation slots")

    workforce: list[WorkforcePool] = Field(min_length=1)
    foster_network: FosterNetwork

    cost_model: CostModel
    seasonal_events: list[SeasonalEvent] = Field(default_factory=list)
    interventions: list[InterventionDef] = Field(default_factory=list)

    total_intervention_budget: float = Field(ge=0, description="Total monthly intervention budget (USD)")

    @field_validator("intake_profiles")
    @classmethod
    def profiles_sum_to_one(cls, profiles: list[CatIntakeProfile]) -> list[CatIntakeProfile]:
        total = sum(p.weight for p in profiles)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"intake_profiles weights must sum to 1.0, got {total:.3f}")
        return profiles

    @field_validator("interventions")
    @classmethod
    def intervention_shares_bounded(cls, interventions: list[InterventionDef]) -> list[InterventionDef]:
        total = sum(i.budget_share for i in interventions)
        if total > 1.0 + 1e-6:
            raise ValueError(f"intervention budget_shares sum to {total:.3f}, must be ≤ 1.0")
        return interventions


def load_scenario(path: Path) -> Scenario:
    """Load and validate a scenario YAML file."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Scenario.model_validate(raw)
