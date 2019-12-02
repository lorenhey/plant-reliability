from typing import List, Optional, Any
from pydantic import BaseModel
from plant_reliability.core.timeline.reconstruction import AssetTimeline
from plant_reliability.core.domain.models import AssetState, MaintenanceType, Event


class MetricResult(BaseModel):
    name: str
    value: float
    units: str
    equation: str
    components: dict[str, Any]
    definition: str


def calculate_availability(timeline: AssetTimeline) -> MetricResult:
    uptime = timeline.get_uptime_hours()
    downtime = timeline.get_downtime_hours()
    total = uptime + downtime
    val = (uptime / total * 100.0) if total > 0 else 0.0

    return MetricResult(
        name="Availability",
        value=val,
        units="%",
        equation="Uptime / (Uptime + Downtime)",
        components={"Uptime (h)": uptime, "Downtime (h)": downtime},
        definition="The probability that an asset is operating satisfactorily at any point in time under stated conditions.",
    )


def calculate_mtbf(timeline: AssetTimeline, events: List[Event]) -> MetricResult:
    uptime = timeline.get_uptime_hours()

    # Failures are events with state FAILED or maintenance_type CORRECTIVE
    failures = [
        e
        for e in events
        if e.asset_id == timeline.asset_id
        and (
            e.state == AssetState.FAILED
            or e.maintenance_type == MaintenanceType.CORRECTIVE
        )
    ]
    num_failures = len(failures)

    val = (uptime / num_failures) if num_failures > 0 else float("inf")

    return MetricResult(
        name="MTBF",
        value=val,
        units="hours",
        equation="Operating Time / Number of Failures",
        components={"Operating Time (h)": uptime, "Failures": num_failures},
        definition="Mean Time Between Failures. Average operating time between repairable failures.",
    )


def calculate_mttr(events: List[Event], asset_id: str) -> MetricResult:
    # MTTR is based on repair times (duration of corrective events)
    repairs = [
        e
        for e in events
        if e.asset_id == asset_id
        and (
            e.state == AssetState.FAILED
            or e.maintenance_type == MaintenanceType.CORRECTIVE
        )
    ]
    num_repairs = len(repairs)

    total_repair_time = sum(e.duration_hours for e in repairs)

    val = (total_repair_time / num_repairs) if num_repairs > 0 else 0.0

    return MetricResult(
        name="MTTR",
        value=val,
        units="hours",
        equation="Total Repair Time / Number of Repairs",
        components={
            "Total Repair Time (h)": total_repair_time,
            "Number of Repairs": num_repairs,
        },
        definition="Mean Time To Repair. The average time required to repair a failed asset.",
    )
