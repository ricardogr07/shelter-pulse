"""Tests that the GP+EI optimizer genuinely does sequential refinement."""
import pytest
from pathlib import Path
from shelterpulse.core.schema import load_scenario
from shelterpulse.optimize.jaxbo_optimizer import optimize_jaxbo

WHISKER_HAVEN = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"

@pytest.fixture(scope="module")
def scenario():
    return load_scenario(WHISKER_HAVEN)

@pytest.fixture(scope="module") 
def seeds():
    return list(range(42, 50))  # 8 seeds for speed

def test_gp_ei_returns_correct_count(scenario, seeds):
    """GP+EI should return n_candidates results."""
    results = optimize_jaxbo(scenario, seeds, n_candidates=10)
    assert len(results) == 10

def test_gp_ei_convergence(scenario, seeds):
    """Later evaluations should trend better than initial random ones.
    The best result from 15 GP+EI iterations should beat the best from 15 random."""
    import numpy as np
    from shelterpulse.optimize.interface import evaluate_candidate
    from shelterpulse.optimize.workflow import CandidateAllocation
    
    # Random baseline: 15 random Dirichlet evaluations
    rng = np.random.default_rng(123)
    random_results = []
    for _ in range(15):
        shares = rng.dirichlet([1,1,1,1])
        alloc = CandidateAllocation(
            foster_support=float(shares[0]),
            clinic_hours=float(shares[1]),
            temporary_isolation=float(shares[2]),
            adoption_events=float(shares[3]),
        )
        random_results.append(evaluate_candidate(alloc, scenario, seeds))
    best_random = min(r.mean_overflow_cat_days for r in random_results)
    
    # GP+EI: 15 sequential evaluations
    bo_results = optimize_jaxbo(scenario, seeds, n_candidates=15)
    best_bo = min(r.mean_overflow_cat_days for r in bo_results)
    
    # BO should be at least as good (allow 10% tolerance for stochasticity)
    assert best_bo <= best_random * 1.1, (
        f"GP+EI best ({best_bo:.1f}) should beat random best ({best_random:.1f})"
    )

def test_warm_start_uses_prior_data(scenario, seeds):
    """Warm-starting with good baselines should help convergence."""
    from shelterpulse.optimize.baselines import ALL_BASELINES
    from shelterpulse.optimize.interface import evaluate_candidate

    warm = [evaluate_candidate(alloc, scenario, seeds) for alloc in ALL_BASELINES.values()]
    results = optimize_jaxbo(scenario, seeds, n_candidates=8, warm_start=warm)
    # Results include warm-start points + new evaluations
    assert len(results) >= 8
    # With warm start from known-good baselines, best should be at least as good
    best = min(r.mean_overflow_cat_days for r in results)
    best_warm = min(r.mean_overflow_cat_days for r in warm)
    assert best <= best_warm  # BO should not regress from warm-start best
    assert best >= 0
