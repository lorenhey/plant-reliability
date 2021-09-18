from pydantic import BaseModel


class ImportMapping(BaseModel):
    event_id: str | None = None
    asset_id: str
    start_time: str
    end_time: str | None = None
    state: str | None = None
    maintenance_type: str | None = None
    failure_mode: str | None = None
    cost: str | None = None
    work_order: str | None = None

    # Custom formats for timestamps
    timestamp_format: str | None = None

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
