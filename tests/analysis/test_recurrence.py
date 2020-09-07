import pytest
from datetime import datetime
from plant_reliability.core.domain.models import Event, AssetState, MaintenanceType
from plant_reliability.analysis.recurrence.engine import detect_chronic_failures


def test_short_interval_recurrence():
    events = [
        Event(
            event_id="1",
            asset_id="A1",
            start_time=datetime(2024, 1, 1, 10, 0),
            end_time=datetime(2024, 1, 1, 12, 0),
            state=AssetState.FAILED,
        ),
        Event(
            event_id="2",
            asset_id="A1",
            start_time=datetime(2024, 1, 2, 10, 0),  # Failed again 22 hours later
            end_time=datetime(2024, 1, 2, 12, 0),
            state=AssetState.FAILED,
        ),
        Event(
            event_id="3",
            asset_id="A2",
            start_time=datetime(2024, 1, 1, 10, 0),
            end_time=datetime(2024, 1, 1, 12, 0),
            state=AssetState.FAILED,
        ),
        Event(
            event_id="4",
            asset_id="A2",
            start_time=datetime(
                2024, 1, 10, 10, 0
            ),  # Failed again 9 days later (> 72h)
            end_time=datetime(2024, 1, 10, 12, 0),
            state=AssetState.FAILED,
        ),
    ]

    patterns = detect_chronic_failures(events, short_interval_hours=72.0)

    assert len(patterns) == 1
    assert patterns[0].asset_id == "A1"
    assert patterns[0].pattern_type == "Short-interval Repeat"
    assert "22.0 hours" in patterns[0].description
