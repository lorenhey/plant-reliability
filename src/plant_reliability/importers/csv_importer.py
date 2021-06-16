import uuid
from datetime import datetime

import pandas as pd

from plant_reliability.core.domain.models import AssetState, Event, MaintenanceType
from plant_reliability.importers.mapping import ImportMapping


class CsvImporter:
    def __init__(self, mapping: ImportMapping):
        self.mapping = mapping

    def parse_time(self, val, fmt) -> datetime | None:
        if pd.isna(val) or val is None:
            return None
        try:
            if fmt:
                return pd.to_datetime(val, format=fmt).to_pydatetime()
            return pd.to_datetime(val).to_pydatetime()
        except Exception:
            return None

    def read_file(self, filepath: str) -> tuple[list[Event], int]:
        df = pd.read_csv(filepath)
        return self._process_dataframe(df)

    def _process_dataframe(self, df: pd.DataFrame) -> tuple[list[Event], int]:
        events = []
        raw_count = len(df)

        for idx, row in df.iterrows():
            asset_id = (
                str(row[self.mapping.asset_id])
                if self.mapping.asset_id in row and pd.notna(row[self.mapping.asset_id])
                else "UNKNOWN_ASSET"
            )

            start_time = self.parse_time(
                row.get(self.mapping.start_time, None),
                self.mapping.timestamp_format,
            )
            if not start_time:
                continue  # Skip rows without start time

            end_time = self.parse_time(
                row.get(self.mapping.end_time) if self.mapping.end_time else None,
                self.mapping.timestamp_format,
            )

            # Map state
            state_val = (
                str(row.get(self.mapping.state)).upper()
                if self.mapping.state
                and self.mapping.state in row
                and pd.notna(row[self.mapping.state])
                else AssetState.FAILED.value
            )
            state = (
                AssetState(state_val)
                if state_val in [s.value for s in AssetState]
                else AssetState.FAILED
            )

            # Map maintenance type
            maint_val = (
                str(row.get(self.mapping.maintenance_type)).upper()
                if self.mapping.maintenance_type
                and self.mapping.maintenance_type in row
                and pd.notna(row[self.mapping.maintenance_type])
                else MaintenanceType.CORRECTIVE.value
            )
            maint_type = (
                MaintenanceType(maint_val)
                if maint_val in [m.value for m in MaintenanceType]
                else MaintenanceType.UNKNOWN
            )

            failure_mode = (
                str(row[self.mapping.failure_mode])
                if self.mapping.failure_mode
                and self.mapping.failure_mode in row
                and pd.notna(row[self.mapping.failure_mode])
                else None
            )
            work_order = (
                str(row[self.mapping.work_order])
                if self.mapping.work_order
                and self.mapping.work_order in row
                and pd.notna(row[self.mapping.work_order])
                else None
            )

            cost = 0.0
            if (
                self.mapping.cost
                and self.mapping.cost in row
                and pd.notna(row[self.mapping.cost])
            ):
                try:
                    cost = float(row[self.mapping.cost])
                except ValueError:
                    cost = 0.0

            event_id = (
                str(row[self.mapping.event_id])
                if self.mapping.event_id
                and self.mapping.event_id in row
                and pd.notna(row[self.mapping.event_id])
                else str(uuid.uuid4())
            )

            metadata = {k: str(v) for k, v in row.items() if pd.notna(v)}

            events.append(
                Event(
                    event_id=event_id,
                    asset_id=asset_id,
                    start_time=start_time,
                    end_time=end_time,
                    state=state,
                    maintenance_type=maint_type,
                    failure_mode=failure_mode,
                    cost=cost,
                    work_order=work_order,
                    metadata=metadata,
                )
            )

        return events, raw_count
