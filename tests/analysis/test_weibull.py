import numpy as np

from plant_reliability.analysis.weibull.engine import analyze_weibull


def test_weibull_random_failures():
    # Exponential distribution implies beta ~ 1.0
    np.random.seed(42)
    # Generate 500 samples from exponential distribution (Weibull with shape=1)
    ttf = np.random.exponential(100, 500).tolist()

    res = analyze_weibull(ttf)

    assert res is not None
    assert 0.90 < res.beta_shape < 1.10
    assert 90 < res.eta_scale < 110


def test_weibull_wearout_failures():
    # Generate samples from Weibull with shape=3.0 (wear-out)
    np.random.seed(42)
    ttf = np.random.weibull(3.0, 500) * 100
    ttf = ttf.tolist()

    res = analyze_weibull(ttf)

    assert res is not None
    assert 2.8 < res.beta_shape < 3.2


def test_weibull_insufficient_data():
    ttf = [10.0, 20.0]
    res = analyze_weibull(ttf)
    assert res is None  # < 3 samples

    ttf2 = [10.0, 20.0, 30.0, 40.0]
    res2 = analyze_weibull(ttf2)
    assert res2 is not None
    assert len(res2.warnings) > 0
    assert "Insufficient sample size" in res2.warnings[0]
