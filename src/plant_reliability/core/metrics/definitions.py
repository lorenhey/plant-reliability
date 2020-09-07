from typing import List, Optional, Any
from pydantic import BaseModel
from plant_reliability.core.timeline.reconstruction import AssetTimeline
from plant_reliability.core.domain.models import AssetState, MaintenanceType, Event


class MetricResult(BaseModel):
    name: str
    value: Optional[float]
    units: str
    equation: str
    components: dict[str, Any]
    definition: str
    error: Optional[str] = None
    warning: Optional[str] = None


def calculate_availability(timeline: AssetTimeline) -> MetricResult:
    uptime = timeline.get_uptime_hours()
    downtime = timeline.get_downtime_hours()
    total = uptime + downtime

    error = None
    val = None
    if total == 0:
        error = "Downtime-based availability cannot be calculated because the sum of operating time and downtime is zero."
    else:
        val = uptime / total * 100.0

    return MetricResult(
        name="Availability",
        value=val,
        units="%",
        equation="Uptime / (Uptime + Downtime)",
        components={"Uptime (h)": uptime, "Downtime (h)": downtime},
        definition="The probability that an asset is operating satisfactorily at any point in time under stated conditions.",
        error=error,
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

    error = None
    warning = None
    val = None

    if uptime == 0.0:
        error = "MTBF cannot be calculated from operating time because operating time is zero. Calendar-time approximation is disabled by default."
    elif num_failures == 0:
        warning = "No failures detected in the specified period. MTBF is theoretically infinite."
    else:
        val = uptime / num_failures

    return MetricResult(
        name="MTBF",
        value=val,
        units="hours",
        equation="Operating Time / Number of Failures",
        components={"Operating Time (h)": uptime, "Failures": num_failures},
        definition="Mean Time Between Failures. Average operating time between repairable failures.",
        error=error,
        warning=warning,
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

    # We must check if these repair events actually have duration
    valid_repairs = [
        e for e in repairs if e.end_time is not None and e.start_time is not None
    ]
    num_valid = len(valid_repairs)

    total_repair_time = sum(e.duration_hours for e in valid_repairs)

    error = None
    val = None

    if num_repairs > 0 and num_valid < num_repairs:
        error = f"Cannot calculate MTTR accurately for asset {asset_id}. {num_repairs} failure events were found, but only {num_valid} contain a valid return-to-service timestamp."
    elif num_valid == 0:
        error = f"No repair durations available for asset {asset_id}. Required fields: failure_start, return_to_service."
    else:
        val = total_repair_time / num_valid

    return MetricResult(
        name="MTTR",
        value=val,
        units="hours",
        equation="Total Repair Time / Number of Valid Repairs",
        components={
            "Total Repair Time (h)": total_repair_time,
            "Number of Valid Repairs": num_valid,
            "Events Excluded (Missing End Time)": num_repairs - num_valid,
        },
        definition="Mean Time To Repair. The average time required to repair a failed asset.",
        error=error,
    )


def calculate_oee(
    availability: MetricResult,
    performance: Optional[float] = None,
    quality: Optional[float] = None,
) -> MetricResult:
    """
    OEE = Availability * Performance * Quality
    """
    val = None
    warning = None
    error = None

    a_val = availability.value / 100.0 if availability.value is not None else None

    components = {"Availability (%)": availability.value}

    if performance is None or quality is None:
        warning = "Performance or Quality inputs do not exist. Only the Availability component is calculable."
        if a_val is not None:
            val = a_val * 100.0
    else:
        components["Performance (%)"] = performance * 100.0
        components["Quality (%)"] = quality * 100.0
        if a_val is not None:
            val = (a_val * performance * quality) * 100.0

    if availability.error:
        error = "OEE cannot be calculated because Availability is invalid."

    return MetricResult(
        name="OEE",
        value=val,
        units="%",
        equation="Availability * Performance * Quality",
        components=components,
        definition="Overall Equipment Effectiveness. A measure of manufacturing productivity.",
        error=error,
        warning=warning,
    )
