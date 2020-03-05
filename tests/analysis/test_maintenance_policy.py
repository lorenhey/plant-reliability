import pytest
from plant_reliability.analysis.weibull.engine import WeibullResult
from plant_reliability.analysis.maintenance_policy.engine import (
    evaluate_maintenance_policies,
)


def test_policy_random_failure():
    # Beta = 1.0 (random failure) -> PM should not be better than RTF
    weibull = WeibullResult(
        beta_shape=1.0, eta_scale=1000.0, sample_size=10, interpretation="", warnings=[]
    )

    policies = evaluate_maintenance_policies(weibull, cost_pm=100, cost_cm=500)

    assert len(policies) == 1
    assert policies[0].policy_name == "Run to Failure"
    assert "Beta <= 1" in policies[0].details["Reason"]


def test_policy_wear_out():
    # Beta = 3.0 (wear out) -> PM should be beneficial
    weibull = WeibullResult(
        beta_shape=3.0, eta_scale=1000.0, sample_size=10, interpretation="", warnings=[]
    )

    policies = evaluate_maintenance_policies(weibull, cost_pm=100, cost_cm=1000)

    assert len(policies) == 2
    assert policies[0].policy_name == "Run to Failure"
    assert policies[1].policy_name == "Optimal Age Replacement"

    assert (
        policies[1].expected_cost_per_unit_time
        < policies[0].expected_cost_per_unit_time
    )
    assert policies[1].optimal_pm_interval > 0
