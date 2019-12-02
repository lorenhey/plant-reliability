from datetime import datetime, timedelta
import pytest
from plant_reliability.core.domain.models import Event, AssetState, MaintenanceType
from plant_reliability.core.timeline.reconstruction import reconstruct_timeline
from plant_reliability.core.metrics.definitions import (
    calculate_mtbf,
    calculate_mttr,
    calculate_availability,
)


def test_metrics_hand_verifiable():
    # Operating time = 100 h
    # Failures = 4
    # Expected MTBF = 25 h

    start_period = datetime(2023, 1, 1, 0, 0, 0)
    end_period = start_period + timedelta(hours=104)  # Total 104 hours

    # Let's create 4 failures, each lasting 1 hour, so uptime is 100h.
    # Uptime 1: 0 to 25 -> 25h
    # Fail 1: 25 to 26 -> 1h down
    # Uptime 2: 26 to 51 -> 25h
    # Fail 2: 51 to 52 -> 1h down
    # Uptime 3: 52 to 77 -> 25h
    # Fail 3: 77 to 78 -> 1h down
    # Uptime 4: 78 to 103 -> 25h
    # Fail 4: 103 to 104 -> 1h down

    events = [
        Event(
            event_id="e1",
            asset_id="A1",
            start_time=start_period + timedelta(hours=25),
            end_time=start_period + timedelta(hours=26),
            state=AssetState.FAILED,
            maintenance_type=MaintenanceType.CORRECTIVE,
        ),
        Event(
            event_id="e2",
            asset_id="A1",
            start_time=start_period + timedelta(hours=51),
            end_time=start_period + timedelta(hours=52),
            state=AssetState.FAILED,
            maintenance_type=MaintenanceType.CORRECTIVE,
        ),
        Event(
            event_id="e3",
            asset_id="A1",
            start_time=start_period + timedelta(hours=77),
            end_time=start_period + timedelta(hours=78),
            state=AssetState.FAILED,
            maintenance_type=MaintenanceType.CORRECTIVE,
        ),
        Event(
            event_id="e4",
            asset_id="A1",
            start_time=start_period + timedelta(hours=103),
            end_time=start_period + timedelta(hours=104),
            state=AssetState.FAILED,
            maintenance_type=MaintenanceType.CORRECTIVE,
        ),
    ]

    timeline = reconstruct_timeline("A1", events, start_period, end_period)

    assert timeline.get_uptime_hours() == 100.0
    assert timeline.get_downtime_hours() == 4.0

    mtbf = calculate_mtbf(timeline, events)
    assert mtbf.value == 25.0

    mttr = calculate_mttr(events, "A1")
    assert mttr.value == 1.0

    availability = calculate_availability(timeline)
    assert round(availability.value, 4) == round((100.0 / 104.0) * 100.0, 4)
