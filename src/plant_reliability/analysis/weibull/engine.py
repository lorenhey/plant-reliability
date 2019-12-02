import numpy as np
from scipy.stats import weibull_min
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class WeibullResult(BaseModel):
    beta_shape: float
    eta_scale: float
    sample_size: int
    interpretation: str
    warnings: List[str]


def interpret_beta(beta: float) -> str:
    if beta < 0.95:
        return "Beta < 1: Decreasing hazard rate. Compatible with early-life or infant-mortality behaviour."
    elif 0.95 <= beta <= 1.05:
        return "Beta ≈ 1: Approximately constant hazard rate. Compatible with random failures."
    else:
        return "Beta > 1: Increasing hazard rate. Compatible with wear-out or fatigue behaviour."


def analyze_weibull(ttf_values: List[float]) -> Optional[WeibullResult]:
    warnings = []

    # Filter out zeros or negative times to failure
    valid_ttf = [t for t in ttf_values if t > 0]

    if len(valid_ttf) < 5:
        warnings.append(
            f"Insufficient sample size ({len(valid_ttf)}). Weibull analysis requires at least 5 failures for reasonable confidence, and ideally >10."
        )

    if len(valid_ttf) < 3:
        return None  # Cannot fit with < 3 reliably

    # Fit the 2-parameter Weibull distribution using scipy
    # scipy's weibull_min fits shape (c = beta), loc, and scale (eta)
    # We force loc=0 for a standard 2-parameter Weibull
    shape, loc, scale = weibull_min.fit(valid_ttf, floc=0)

    beta = float(shape)
    eta = float(scale)

    return WeibullResult(
        beta_shape=beta,
        eta_scale=eta,
        sample_size=len(valid_ttf),
        interpretation=interpret_beta(beta),
        warnings=warnings,
    )
