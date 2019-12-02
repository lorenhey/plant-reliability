import streamlit as st
import pandas as pd
from pathlib import Path
from plant_reliability.importers.mapping import ImportMapping
from plant_reliability.importers.csv_importer import CsvImporter
from plant_reliability.core.validation.data_quality import DataQualityEngine
from plant_reliability.core.timeline.reconstruction import reconstruct_timeline
from plant_reliability.analysis.bad_actors.engine import (
    identify_bad_actors,
    BadActorConfig,
)
from plant_reliability.core.metrics.definitions import (
    calculate_mtbf,
    calculate_mttr,
    calculate_availability,
)


def run_ui():
    st.set_page_config(page_title="Plant Reliability", layout="wide")
    st.title("Plant Reliability Analysis")

    st.sidebar.header("Data Upload")
    uploaded_file = st.sidebar.file_uploader("Upload Maintenance Data", type=["csv"])

    if uploaded_file is not None:
        # Save temp
        temp_path = Path("temp_upload.csv")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        mapping = ImportMapping.default()
        importer = CsvImporter(mapping)
        events, raw_count = importer.read_file(str(temp_path))

        st.header("Data Quality")
        engine = DataQualityEngine()
        dq = engine.evaluate_events(events, raw_count)

        col1, col2, col3 = st.columns(3)
        col1.metric("Rows Imported", dq.rows_imported)
        col2.metric("Valid Records", dq.valid_records)
        col3.metric("Timestamp Completeness", f"{dq.timestamp_completeness:.1f}%")

        if dq.issues:
            for issue in dq.issues:
                st.warning(f"**{issue.severity.value}**: {issue.description}")

        st.header("Bad Actors Analysis")
        start_time = min(e.start_time for e in events if e.start_time)
        end_time = max(e.end_time or e.start_time for e in events if e.start_time)

        assets = list(set(e.asset_id for e in events if e.asset_id))
        timelines = {
            a: reconstruct_timeline(a, events, start_time, end_time) for a in assets
        }
        bad_actors = identify_bad_actors(events, timelines, BadActorConfig())

        if bad_actors:
            df_actors = pd.DataFrame(
                [
                    {
                        "Asset": a.asset_id,
                        "Composite Score": round(a.composite_score, 3),
                        "Failures": a.failure_frequency,
                        "Downtime (h)": round(a.downtime_hours, 1),
                        "Cost ($)": round(a.maintenance_cost, 2),
                    }
                    for a in bad_actors
                ]
            )

            st.dataframe(df_actors.head(10), use_container_width=True)

            # Show detailed metrics for the top bad actor
            top_actor = bad_actors[0].asset_id
            st.header(f"Detailed Analysis: {top_actor}")

            tl = timelines[top_actor]
            mtbf = calculate_mtbf(tl, events)
            mttr = calculate_mttr(events, top_actor)
            avail = calculate_availability(tl)

            c1, c2, c3 = st.columns(3)
            c1.metric("MTBF", f"{mtbf.value:.1f} h")
            c2.metric("MTTR", f"{mttr.value:.1f} h")
            c3.metric("Availability", f"{avail.value:.2f} %")

            st.subheader("MTBF Calculation Explain")
            st.code(mtbf.equation)
            st.write(mtbf.components)

    else:
        st.info("Upload a CSV file with maintenance records to begin analysis.")


if __name__ == "__main__":
    run_ui()
