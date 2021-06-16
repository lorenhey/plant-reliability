from datetime import datetime

from plant_reliability.core.domain.models import Event
from plant_reliability.core.validation.data_quality import DataQualityEngine


def test_negative_durations():
    engine = DataQualityEngine()
    events = [
        Event(
            event_id="1",
            asset_id="A1",
            start_time=datetime(2023, 1, 2),
            end_time=datetime(2023, 1, 1),  # Negative
            state="FAILED",
        )
    ]

    report = engine.evaluate_events(events)
    assert len(report.issues) == 1
    assert "negative" in report.issues[0].description
    assert report.issues[0].severity.value == "ERROR"


def test_missing_failure_mode():
    engine = DataQualityEngine()
    events = [
        Event(
            event_id="1",
            asset_id="A1",
            start_time=datetime(2023, 1, 1),
            maintenance_type="CORRECTIVE",
            failure_mode=None,
        )
    ]

    report = engine.evaluate_events(events)
    assert len(report.issues) == 1
    assert "without failure classification" in report.issues[0].description
    assert report.issues[0].severity.value == "WARNING"
