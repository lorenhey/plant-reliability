from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AssetState(str, Enum):
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    UNDER_REPAIR = "UNDER_REPAIR"
    PLANNED_STOP = "PLANNED_STOP"
    UNKNOWN = "UNKNOWN"
    OFFLINE = "OFFLINE"


class MaintenanceType(str, Enum):
    CORRECTIVE = "CORRECTIVE"
    PREVENTIVE = "PREVENTIVE"
    INSPECTION = "INSPECTION"
    UNKNOWN = "UNKNOWN"


class Event(BaseModel):
    event_id: str
    asset_id: str
    start_time: datetime
    end_time: datetime | None = None
    state: AssetState = AssetState.UNKNOWN
    maintenance_type: MaintenanceType | None = None
    failure_mode: str | None = None
    cost: float = 0.0
    work_order: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def duration_hours(self) -> float:
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds() / 3600.0
        return 0.0


class Asset(BaseModel):
    asset_id: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
