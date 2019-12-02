from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


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
    end_time: Optional[datetime] = None
    state: AssetState = AssetState.UNKNOWN
    maintenance_type: Optional[MaintenanceType] = None
    failure_mode: Optional[str] = None
    cost: float = 0.0
    work_order: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def duration_hours(self) -> float:
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds() / 3600.0
        return 0.0


class Asset(BaseModel):
    asset_id: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
