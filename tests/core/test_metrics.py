from datetime import datetime, timedelta

from plant_reliability.core.domain.models import AssetState, Event, MaintenanceType
from plant_reliability.core.metrics.definitions import (
    MetricResult,
    calculate_availability,
    calculate_mtbf,
    calculate_mttr,
    calculate_oee,
)
from plant_reliability.core.timeline.reconstruction import reconstruct_timeline


def test_metrics_hand_verifiable():
    # Operating time = 100 h
    # Failures = 4
    # Expected MTBF = 25 h

    start_period = datetime(2023, 1, 1, 0, 0, 0)
    end_period = start_period + timedelta(hours=104)  # Total 104 hours

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

    # Test OEE
    oee = calculate_oee(availability, performance=0.9, quality=0.95)
    assert round(oee.value, 4) == round(availability.value * 0.9 * 0.95, 4)


def test_missing_data_integrity():
    # Section 41: Engineering Integrity
    # If operating hours are unavailable -> MTBF cannot be calculated
    # If no failures -> MTBF infinite

    start_period = datetime(2023, 1, 1, 0, 0, 0)
    end_period = start_period + timedelta(hours=10)

    # No events
    timeline = reconstruct_timeline("A2", [], start_period, end_period)

    mtbf = calculate_mtbf(timeline, [])
    # Uptime is 10h, failures 0
    assert mtbf.value is None
    assert "infinito" in mtbf.warning

    # What if uptime is 0?
    timeline_zero = reconstruct_timeline(
        "A3",
        [
            Event(
                event_id="e",
                asset_id="A3",
                start_time=start_period,
                end_time=end_period,
                state=AssetState.FAILED,
            )
        ],
        start_period,
        end_period,
    )

    mtbf_zero = calculate_mtbf(timeline_zero, [])
    assert mtbf_zero.value is None
    assert "tiempo de operación porque éste es cero" in mtbf_zero.error

    # MTTR missing end time
    events_broken = [
        Event(
            event_id="e1",
            asset_id="A3",
            start_time=start_period,
            state=AssetState.FAILED,
        )
    ]
    mttr_broken = calculate_mttr(events_broken, "A3")
    assert mttr_broken.value is None
    assert "pero solo 0 contienen una fecha" in mttr_broken.error


def test_oee_incomplete():
    # Section 11: Do not fabricate Performance or Quality
    avail = MetricResult(
        name="Availability",
        value=90.0,
        units="%",
        equation="",
        components={},
        definition="",
    )

    oee_inc = calculate_oee(avail, performance=None, quality=None)
    assert oee_inc.value == 90.0
    assert "Solo el componente de Disponibilidad" in oee_inc.warning
