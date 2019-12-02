from pydantic import BaseModel
from typing import Dict, Optional


class ImportMapping(BaseModel):
    event_id: Optional[str] = None
    asset_id: str
    start_time: str
    end_time: Optional[str] = None
    state: Optional[str] = None
    maintenance_type: Optional[str] = None
    failure_mode: Optional[str] = None
    cost: Optional[str] = None
    work_order: Optional[str] = None

    # Custom formats for timestamps
    timestamp_format: Optional[str] = None

    @classmethod
    def default(cls) -> "ImportMapping":
        return cls(
            asset_id="equipment",
            start_time="failure_start",
            end_time="failure_end",
            maintenance_type="maintenance_type",
            failure_mode="failure_mode",
            cost="cost",
            work_order="work_order",
        )
