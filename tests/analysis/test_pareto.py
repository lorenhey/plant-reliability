import pytest
from datetime import datetime
from plant_reliability.core.domain.models import Event
from plant_reliability.analysis.pareto.engine import analyze_pareto


def test_pareto_analysis():
    events = [
        Event(
            event_id="1",
            asset_id="A1",
            start_time=datetime.now(),
            cost=100.0,
            failure_mode="LEAK",
        ),
        Event(
            event_id="2",
            asset_id="A1",
            start_time=datetime.now(),
            cost=200.0,
            failure_mode="LEAK",
        ),
        Event(
            event_id="3",
            asset_id="A2",
            start_time=datetime.now(),
            cost=50.0,
            failure_mode="VIBRATION",
        ),
        Event(
            event_id="4",
            asset_id="A3",
            start_time=datetime.now(),
            cost=50.0,
            failure_mode="VIBRATION",
        ),
    ]

    # Pareto by asset, cost
    res = analyze_pareto(events, dimension="asset_id", metric="cost")
    assert res.dimension == "asset_id"
    assert len(res.items) == 3

    # A1 should be first with 300 cost
    assert res.items[0].category == "A1"
    assert res.items[0].value == 300.0
    assert res.items[0].cumulative_percentage == 75.0  # 300 / 400
