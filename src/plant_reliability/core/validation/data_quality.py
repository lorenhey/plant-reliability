from enum import Enum

from pydantic import BaseModel

from plant_reliability.core.domain.models import Event


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    BLOCKING = "BLOCKING"


class QualityIssue(BaseModel):
    severity: Severity
    description: str
    affected_rows: int = 0
    remediation: str = ""


class DataQualityReport(BaseModel):
    rows_imported: int
    valid_records: int
    timestamp_completeness: float
    asset_id_completeness: float
    failure_mode_completeness: float
    issues: list[QualityIssue]


class DataQualityEngine:
    def __init__(self, raw_df=None):
        self.raw_df = raw_df

    def evaluate_events(
        self, events: list[Event], raw_rows_count: int = 0
    ) -> DataQualityReport:
        rows_imported = raw_rows_count if raw_rows_count > 0 else len(events)

        if not events:
            return DataQualityReport(
                rows_imported=rows_imported,
                valid_records=0,
                timestamp_completeness=0.0,
                asset_id_completeness=0.0,
                failure_mode_completeness=0.0,
                issues=[
                    QualityIssue(
                        severity=Severity.BLOCKING,
                        description="No events provided.",
                        affected_rows=0,
                    )
                ],
            )

        valid_records = len(events)
        timestamp_count = sum(1 for e in events if e.start_time is not None)
        asset_id_count = sum(1 for e in events if e.asset_id)
        failure_mode_count = sum(1 for e in events if e.failure_mode)

        issues = []

        # Check negative durations
        negative_durations = sum(
            1 for e in events if e.end_time and e.end_time < e.start_time
        )
        if negative_durations > 0:
            issues.append(
                QualityIssue(
                    severity=Severity.ERROR,
                    description=f"{negative_durations} negative repair/downtime durations detected",
                    affected_rows=negative_durations,
                    remediation="Check start_time and end_time order in input data.",
                )
            )

        # Check missing failure modes for corrective maintenance
        missing_modes = sum(
            1
            for e in events
            if e.maintenance_type == "CORRECTIVE" and not e.failure_mode
        )
        if missing_modes > 0:
            issues.append(
                QualityIssue(
                    severity=Severity.WARNING,
                    description=f"{missing_modes} corrective events without failure classification",
                    affected_rows=missing_modes,
                    remediation="Ensure failure_mode column is mapped and populated for failure events.",
                )
            )

        return DataQualityReport(
            rows_imported=rows_imported,
            valid_records=valid_records,
            timestamp_completeness=(timestamp_count / valid_records) * 100.0,
            asset_id_completeness=(asset_id_count / valid_records) * 100.0,
            failure_mode_completeness=(failure_mode_count / valid_records) * 100.0,
            issues=issues,
        )
