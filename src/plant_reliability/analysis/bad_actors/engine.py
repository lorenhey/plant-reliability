import pandas as pd
from typing import List, Dict, Any
from pydantic import BaseModel
from plant_reliability.core.domain.models import Event
from plant_reliability.core.timeline.reconstruction import AssetTimeline


class BadActorScore(BaseModel):
    asset_id: str
    composite_score: float
    failure_frequency: int
    downtime_hours: float
    maintenance_cost: float
    chronicity_index: float


class BadActorConfig(BaseModel):
    weight_frequency: float = 0.3
    weight_downtime: float = 0.4
    weight_cost: float = 0.2
    weight_chronicity: float = 0.1


def identify_bad_actors(
    events: List[Event], timelines: Dict[str, AssetTimeline], config: BadActorConfig
) -> List[BadActorScore]:
    asset_stats = {}

    for asset_id, timeline in timelines.items():
        asset_events = [e for e in events if e.asset_id == asset_id]

        # Calculate raw dimensions
        # Failure frequency
        failures = [
            e
            for e in asset_events
            if e.state == "FAILED" or e.maintenance_type == "CORRECTIVE"
        ]
        freq = len(failures)

        # Downtime
        dt = timeline.get_downtime_hours()

        # Cost
        cost = sum(e.cost for e in asset_events)

        # Chronicity (simple ratio of failures / unique failure modes, indicating recurring same failures)
        modes = set(f.failure_mode for f in failures if f.failure_mode)
        chronicity = freq / len(modes) if len(modes) > 0 else 1.0 if freq > 0 else 0.0

        asset_stats[asset_id] = {
            "freq": freq,
            "dt": dt,
            "cost": cost,
            "chronicity": chronicity,
        }

    if not asset_stats:
        return []

    # Normalize dimensions (0 to 1) to combine them
    max_freq = max((s["freq"] for s in asset_stats.values()), default=1.0) or 1.0
    max_dt = max((s["dt"] for s in asset_stats.values()), default=1.0) or 1.0
    max_cost = max((s["cost"] for s in asset_stats.values()), default=1.0) or 1.0
    max_chronicity = (
        max((s["chronicity"] for s in asset_stats.values()), default=1.0) or 1.0
    )

    scores = []
    for asset_id, stats in asset_stats.items():
        # Composite score
        n_freq = stats["freq"] / max_freq
        n_dt = stats["dt"] / max_dt
        n_cost = stats["cost"] / max_cost
        n_chronicity = stats["chronicity"] / max_chronicity

        score = (
            n_freq * config.weight_frequency
            + n_dt * config.weight_downtime
            + n_cost * config.weight_cost
            + n_chronicity * config.weight_chronicity
        )

        scores.append(
            BadActorScore(
                asset_id=asset_id,
                composite_score=score,
                failure_frequency=stats["freq"],
                downtime_hours=stats["dt"],
                maintenance_cost=stats["cost"],
                chronicity_index=stats["chronicity"],
            )
        )

    # Sort by descending composite score
    return sorted(scores, key=lambda x: x.composite_score, reverse=True)
