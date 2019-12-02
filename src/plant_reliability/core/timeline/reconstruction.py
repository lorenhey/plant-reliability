from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from plant_reliability.core.domain.models import Event, AssetState


class TimelineInterval(BaseModel):
    start_time: datetime
    end_time: datetime
    state: AssetState
    associated_event_id: Optional[str] = None

    @property
    def duration_hours(self) -> float:
        return (self.end_time - self.start_time).total_seconds() / 3600.0


class AssetTimeline:
    def __init__(self, asset_id: str, intervals: List[TimelineInterval]):
        self.asset_id = asset_id
        self.intervals = sorted(intervals, key=lambda x: x.start_time)

    def get_uptime_hours(self) -> float:
        return sum(
            i.duration_hours for i in self.intervals if i.state == AssetState.RUNNING
        )

    def get_downtime_hours(self) -> float:
        return sum(
            i.duration_hours
            for i in self.intervals
            if i.state
            in (AssetState.FAILED, AssetState.UNDER_REPAIR, AssetState.PLANNED_STOP)
        )


def reconstruct_timeline(
    asset_id: str, events: List[Event], period_start: datetime, period_end: datetime
) -> AssetTimeline:
    """
    Reconstructs the timeline of an asset based on its events.
    Assumes the asset is RUNNING unless an event indicates otherwise.
    """
    sorted_events = sorted(
        [
            e
            for e in events
            if e.asset_id == asset_id
            and e.start_time >= period_start
            and (e.end_time is None or e.end_time <= period_end)
        ],
        key=lambda x: x.start_time,
    )

    intervals = []
    current_time = period_start

    for event in sorted_events:
        if event.start_time > current_time:
            # The asset was running before this event
            intervals.append(
                TimelineInterval(
                    start_time=current_time,
                    end_time=event.start_time,
                    state=AssetState.RUNNING,
                )
            )

        end_t = (
            event.end_time if event.end_time else event.start_time
        )  # Instantaneous event if no end time

        # Add the event interval itself
        if end_t > event.start_time:
            intervals.append(
                TimelineInterval(
                    start_time=event.start_time,
                    end_time=end_t,
                    state=event.state,
                    associated_event_id=event.event_id,
                )
            )

        current_time = max(current_time, end_t)

    if current_time < period_end:
        intervals.append(
            TimelineInterval(
                start_time=current_time, end_time=period_end, state=AssetState.RUNNING
            )
        )

    return AssetTimeline(asset_id=asset_id, intervals=intervals)
