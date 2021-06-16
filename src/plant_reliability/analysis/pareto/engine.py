
import pandas as pd
from pydantic import BaseModel

from plant_reliability.core.domain.models import Event


class ParetoItem(BaseModel):
    category: str
    value: float
    cumulative_percentage: float


class ParetoResult(BaseModel):
    dimension: str
    metric: str
    items: list[ParetoItem]


def analyze_pareto(events: list[Event], dimension: str, metric: str) -> ParetoResult:
    """
    Perform a Pareto analysis on events.

    dimension: "asset_id", "failure_mode", "maintenance_type", "work_order"
    metric: "downtime_hours", "cost", "event_count"
    """
    df = pd.DataFrame([e.model_dump() for e in events])

    # Extract calculated properties for metrics if needed
    if metric == "downtime_hours":
        df["downtime_hours"] = [e.duration_hours for e in events]
    elif metric == "event_count":
        df["event_count"] = 1

    if df.empty or dimension not in df.columns or metric not in df.columns:
        return ParetoResult(dimension=dimension, metric=metric, items=[])

    # Group by dimension and sum metric
    # Drop na for the specific dimension
    df_clean = df.dropna(subset=[dimension])

    if df_clean.empty:
        return ParetoResult(dimension=dimension, metric=metric, items=[])

    grouped = df_clean.groupby(dimension)[metric].sum().reset_index()
    grouped = grouped.sort_values(by=metric, ascending=False)

    total = grouped[metric].sum()
    if total == 0:
        return ParetoResult(dimension=dimension, metric=metric, items=[])

    grouped["cumulative_percentage"] = (grouped[metric].cumsum() / total) * 100.0

    items = []
    for _, row in grouped.iterrows():
        items.append(
            ParetoItem(
                category=str(row[dimension]),
                value=float(row[metric]),
                cumulative_percentage=float(row["cumulative_percentage"]),
            )
        )

    return ParetoResult(dimension=dimension, metric=metric, items=items)
