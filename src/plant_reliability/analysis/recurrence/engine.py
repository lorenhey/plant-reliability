from typing import List, Dict
from pydantic import BaseModel
from plant_reliability.core.domain.models import Event, AssetState


class RecurrencePattern(BaseModel):
    asset_id: str
    pattern_type: str
    description: str
    evidence_events: List[str]
    severity: str


def detect_chronic_failures(
    events: List[Event], short_interval_hours: float = 72.0
) -> List[RecurrencePattern]:
    """
    Detects patterns like:
    - Recurring failure modes.
    - Repeated repairs within short intervals (e.g., failing again within 72h).
    """
    patterns = []

    # Group by asset
    asset_events = {}
    for e in events:
        if e.state == AssetState.FAILED:
            asset_events.setdefault(e.asset_id, []).append(e)

    for asset_id, evs in asset_events.items():
        # Sort by start time
        evs.sort(key=lambda x: x.start_time)

        mode_counts = {}

        for i in range(len(evs)):
            current = evs[i]

            # Count failure modes
            if current.failure_mode:
                mode_counts[current.failure_mode] = (
                    mode_counts.get(current.failure_mode, 0) + 1
                )

            # Check short interval recurrence
            if i > 0:
                prev = evs[i - 1]
                if prev.end_time and current.start_time:
                    delta = (
                        current.start_time - prev.end_time
                    ).total_seconds() / 3600.0
                    if 0 < delta <= short_interval_hours:
                        patterns.append(
                            RecurrencePattern(
                                asset_id=asset_id,
                                pattern_type="Short-interval Repeat",
                                description=f"Asset failed again {delta:.1f} hours after previous repair completed.",
                                evidence_events=[prev.event_id, current.event_id],
                                severity="WARNING",
                            )
                        )

        # Check for chronic modes (e.g., same mode > 3 times)
        for mode, count in mode_counts.items():
            if count >= 3:
                evidence = [e.event_id for e in evs if e.failure_mode == mode]
                patterns.append(
                    RecurrencePattern(
                        asset_id=asset_id,
                        pattern_type="Chronic Failure Mode",
                        description=f"Failure mode '{mode}' occurred {count} times.",
                        evidence_events=evidence,
                        severity="WARNING" if count < 5 else "ERROR",
                    )
                )

    return patterns
