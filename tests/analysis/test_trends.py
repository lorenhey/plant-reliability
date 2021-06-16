from datetime import datetime

from plant_reliability.analysis.trends.engine import analyze_trends
from plant_reliability.core.domain.models import AssetState, Event, MaintenanceType


def test_trend_analysis():
    # 2 months of data
    start = datetime(2024, 1, 1)
    end = datetime(2024, 2, 28)

    events = [
        # Jan event
        Event(
            event_id="1",
            asset_id="A1",
            start_time=datetime(2024, 1, 15),
            end_time=datetime(2024, 1, 16),
            state=AssetState.FAILED,
            maintenance_type=MaintenanceType.CORRECTIVE,
            cost=1000.0,
        ),
        # Feb event
        Event(
            event_id="2",
            asset_id="A1",
            start_time=datetime(2024, 2, 10),
            end_time=datetime(2024, 2, 12),
            state=AssetState.FAILED,
            maintenance_type=MaintenanceType.CORRECTIVE,
            cost=2000.0,
        ),
    ]

    trends = analyze_trends("A1", events, start, end, period="M")

    assert len(trends) == 2

    jan_trend = trends[0]
    assert jan_trend.period == "2024-01"
    assert jan_trend.failure_count == 1
    assert jan_trend.cost == 1000.0
    assert jan_trend.downtime_hours == 24.0

    feb_trend = trends[1]
    assert feb_trend.period == "2024-02"
    assert feb_trend.failure_count == 1
    assert feb_trend.cost == 2000.0
    assert feb_trend.downtime_hours == 48.0
