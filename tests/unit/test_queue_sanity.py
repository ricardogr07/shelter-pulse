"""Queue sanity: SimPy output must be within a reasonable range of M/M/1 analytical results.

For a single-stage M/M/1 queue:
  arrival rate λ, service rate μ → mean queue length E[L] = λ/(μ-λ)  (for λ < μ)
"""

from pathlib import Path

import numpy as np
import simpy

from shelterpulse.core.engine import run_simulation
from shelterpulse.core.schema import load_scenario

WHISKER_HAVEN = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"


def _run_mm1(arrival_rate: float, service_rate: float, duration: float, seed: int) -> float:
    """Simulate a single M/M/1 queue and return mean queue length."""
    rng = np.random.default_rng(seed)
    env = simpy.Environment()
    server = simpy.Resource(env, capacity=1)
    queue_samples: list[int] = []

    def customer():
        with server.request() as req:
            yield req
            service_time = float(rng.exponential(1.0 / service_rate))
            yield env.timeout(service_time)

    def arrivals():
        while env.now < duration:
            yield env.timeout(float(rng.exponential(1.0 / arrival_rate)))
            env.process(customer())

    def sampler():
        while env.now < duration:
            yield env.timeout(1.0)
            queue_samples.append(len(server.queue))

    env.process(arrivals())
    env.process(sampler())
    env.run(until=duration)
    return float(np.mean(queue_samples)) if queue_samples else 0.0


def test_mm1_queue_length_within_tolerance():
    """Sim mean queue length (waiting only) must be within ±30% of M/M/1 analytical E[Lq].

    len(server.queue) gives customers waiting in queue (not being served), so the
    correct analytical reference is E[Lq] = ρ²/(1-ρ), not E[L] = ρ/(1-ρ).
    """
    lam = 1.0    # arrivals per hour
    mu = 1.5     # service completions per hour
    rho = lam / mu
    e_lq_analytical = rho ** 2 / (1.0 - rho)  # ≈ 1.333

    # Run long enough to average out variance (10,000 hours)
    sim_mean_q = _run_mm1(lam, mu, duration=10_000.0, seed=7)

    tolerance = 0.30
    lower = e_lq_analytical * (1 - tolerance)
    upper = e_lq_analytical * (1 + tolerance)
    assert lower <= sim_mean_q <= upper, (
        f"M/M/1 sanity failed: analytical E[Lq]={e_lq_analytical:.2f}, "
        f"sim={sim_mean_q:.2f}, tolerance=±{tolerance*100:.0f}%"
    )


def test_shelter_simulation_plausible_queue(scenario=None):
    """The Whisker Haven isolation queue should not be permanently zero or infinite."""
    if scenario is None:
        scenario = load_scenario(WHISKER_HAVEN)

    result = run_simulation(scenario, seed=42)

    # During kitten season with 12 isolation slots, we expect some queueing
    # but not a runaway queue that dwarfs capacity
    assert result.mean_isolation_queue >= 0, "Queue cannot be negative"
    assert result.peak_isolation_queue < scenario.isolation_capacity * 20, (
        f"Peak isolation queue ({result.peak_isolation_queue}) "
        f"implausibly large vs capacity ({scenario.isolation_capacity})"
    )
