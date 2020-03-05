import numpy as np
import math
from typing import List, Dict, Any
from pydantic import BaseModel
from plant_reliability.analysis.weibull.engine import WeibullResult


class PolicyComparisonResult(BaseModel):
    policy_name: str
    expected_cost_per_unit_time: float
    optimal_pm_interval: float = 0.0
    details: Dict[str, Any]


def evaluate_maintenance_policies(
    weibull_res: WeibullResult,
    cost_pm: float,
    cost_cm: float,
    max_time: float = 10000.0,
) -> List[PolicyComparisonResult]:
    """
    Evaluates Run-to-Failure vs Preventive Maintenance based on Weibull parameters.
    """
    if weibull_res is None or weibull_res.beta_shape <= 1.0:
        # If Beta <= 1, PM is mathematically useless or harmful in standard models
        return [
            PolicyComparisonResult(
                policy_name="Run to Failure",
                expected_cost_per_unit_time=cost_cm
                / (weibull_res.eta_scale * math.gamma(1 + 1 / weibull_res.beta_shape))
                if weibull_res
                else 0.0,
                details={
                    "Reason": "Beta <= 1. Preventive replacement is not recommended."
                },
            )
        ]

    beta = weibull_res.beta_shape
    eta = weibull_res.eta_scale

    # MTTF for Weibull = eta * Gamma(1 + 1/beta)
    mttf = eta * math.gamma(1 + 1 / beta)
    cost_rtf_rate = cost_cm / mttf

    # For a block replacement or age replacement policy, the expected cost per unit time C(tp)
    # C(tp) = [Cost_PM * R(tp) + Cost_CM * F(tp)] / Integral[R(t) dt from 0 to tp]
    # Let's find the optimal Tp by evaluating a grid of possible intervals
    t_grid = np.linspace(eta * 0.1, min(eta * 3.0, max_time), 1000)

    best_tp = t_grid[0]
    best_cost_rate = float("inf")

    # We will use simple numerical integration for the denominator
    # Denominator: Expected cycle time = Integral of R(t) from 0 to tp
    for tp in t_grid:
        # F(tp)
        f_tp = 1 - np.exp(-((tp / eta) ** beta))
        r_tp = 1 - f_tp

        # Expected cost in the cycle
        cycle_cost = cost_pm * r_tp + cost_cm * f_tp

        # Numerically integrate R(t) from 0 to tp
        t_vals = np.linspace(0, tp, 100)
        r_vals = np.exp(-((t_vals / eta) ** beta))
        cycle_time = np.trapezoid(r_vals, t_vals)

        if cycle_time > 0:
            rate = cycle_cost / cycle_time
            if rate < best_cost_rate:
                best_cost_rate = rate
                best_tp = tp

    return [
        PolicyComparisonResult(
            policy_name="Run to Failure",
            expected_cost_per_unit_time=cost_rtf_rate,
            details={"MTTF": mttf},
        ),
        PolicyComparisonResult(
            policy_name="Optimal Age Replacement",
            expected_cost_per_unit_time=best_cost_rate,
            optimal_pm_interval=best_tp,
            details={
                "Cost savings (%)": ((cost_rtf_rate - best_cost_rate) / cost_rtf_rate)
                * 100.0
                if cost_rtf_rate > 0
                else 0
            },
        ),
    ]
