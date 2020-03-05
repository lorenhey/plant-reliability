import pandas as pd
from typing import List, Dict
from datetime import datetime
from pydantic import BaseModel
from plant_reliability.core.domain.models import Event, AssetState, MaintenanceType
from plant_reliability.core.timeline.reconstruction import reconstruct_timeline
from plant_reliability.core.metrics.definitions import calculate_mtbf


class TrendPoint(BaseModel):
    period: str  # YYYY-MM
    mtbf_hours: float
    mttr_hours: float
    downtime_hours: float
    failure_count: int
    cost: float


def analyze_trends(
    asset_id: str,
    events: List[Event],
    start_date: datetime,
    end_date: datetime,
    period: str = "M",
) -> List[TrendPoint]:
    """
    Calculates monthly (or specified frequency) trends for a given asset.
    """
    asset_events = [
        e
        for e in events
        if e.asset_id == asset_id
        and e.start_time >= start_date
        and e.start_time <= end_date
    ]

    if not asset_events:
        return []

    # Generate a date range for the periods
    periods = pd.period_range(start=start_date, end=end_date, freq=period)

    trend_points = []

    for p in periods:
        p_start = p.start_time.to_pydatetime()
        p_end = p.end_time.to_pydatetime()

        # Events falling into this period
        p_events = [e for e in asset_events if p_start <= e.start_time <= p_end]

        # Timeline for this specific period
        p_timeline = reconstruct_timeline(asset_id, p_events, p_start, p_end)

        mtbf_res = calculate_mtbf(p_timeline, p_events)

        failures = [
            e
            for e in p_events
            if e.state == AssetState.FAILED
            or e.maintenance_type == MaintenanceType.CORRECTIVE
        ]
        failure_count = len(failures)

        downtime = p_timeline.get_downtime_hours()

        # MTTR = downtime / failures (approximation for the period)
        total_repair_time = sum(e.duration_hours for e in failures)
        mttr = (total_repair_time / failure_count) if failure_count > 0 else 0.0

        cost = sum(e.cost for e in p_events)

        trend_points.append(
            TrendPoint(
                period=str(p),
                mtbf_hours=mtbf_res.value if mtbf_res.value != float("inf") else 0.0,
                mttr_hours=mttr,
                downtime_hours=downtime,
                failure_count=failure_count,
                cost=cost,
            )
        )

    return trend_points
