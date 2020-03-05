import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

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
from plant_reliability.analysis.pareto.engine import analyze_pareto
from plant_reliability.analysis.trends.engine import analyze_trends
from plant_reliability.analysis.weibull.engine import analyze_weibull
from plant_reliability.analysis.maintenance_policy.engine import (
    evaluate_maintenance_policies,
)


def run_ui():
    st.set_page_config(page_title="Plant Reliability", layout="wide")
    st.title("Plant Reliability Analysis")

    st.sidebar.header("Data Upload")
    uploaded_file = st.sidebar.file_uploader("Upload Maintenance Data", type=["csv"])

    if uploaded_file is not None:
        temp_path = Path("temp_upload.csv")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        mapping = ImportMapping.default()
        importer = CsvImporter(mapping)
        events, raw_count = importer.read_file(str(temp_path))

        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            [
                "Data Quality",
                "Bad Actors",
                "Pareto Analysis",
                "Asset Trends",
                "Weibull & Policy",
            ]
        )

        start_time = min(
            (e.start_time for e in events if e.start_time), default=datetime.now()
        )
        end_time = max(
            (e.end_time or e.start_time for e in events if e.start_time),
            default=datetime.now(),
        )
        assets = list(set(e.asset_id for e in events if e.asset_id))
        timelines = {
            a: reconstruct_timeline(a, events, start_time, end_time) for a in assets
        }

        with tab1:
            st.header("Data Quality Engine")
            engine = DataQualityEngine()
            dq = engine.evaluate_events(events, raw_count)

            c1, c2, c3 = st.columns(3)
            c1.metric("Rows Imported", dq.rows_imported)
            c2.metric("Valid Records", dq.valid_records)
            c3.metric("Timestamp Completeness", f"{dq.timestamp_completeness:.1f}%")

            if dq.issues:
                for issue in dq.issues:
                    st.warning(f"**{issue.severity.value}**: {issue.description}")
            else:
                st.success("No data quality issues detected.")

        with tab2:
            st.header("Bad Actors")
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
                st.dataframe(df_actors, use_container_width=True)

        with tab3:
            st.header("Pareto Analysis")
            col_p1, col_p2 = st.columns(2)
            dimension = col_p1.selectbox("Dimension", ["asset_id", "failure_mode"])
            metric = col_p2.selectbox(
                "Metric", ["downtime_hours", "event_count", "cost"]
            )

            pareto_res = analyze_pareto(events, dimension, metric)
            if pareto_res.items:
                df_pareto = pd.DataFrame([i.model_dump() for i in pareto_res.items])

                fig = go.Figure()
                fig.add_trace(
                    go.Bar(
                        x=df_pareto["category"],
                        y=df_pareto["value"],
                        name="Value",
                        yaxis="y1",
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=df_pareto["category"],
                        y=df_pareto["cumulative_percentage"],
                        name="Cumulative %",
                        mode="lines+markers",
                        yaxis="y2",
                        line=dict(color="red"),
                    )
                )
                fig.update_layout(
                    title=f"Pareto: {metric} by {dimension}",
                    yaxis=dict(title="Value", side="left"),
                    yaxis2=dict(
                        title="Cumulative %",
                        side="right",
                        overlaying="y",
                        range=[0, 105],
                    ),
                    hovermode="x unified",
                )
                st.plotly_chart(fig, use_container_width=True)

        with tab4:
            st.header("Asset Trends")
            selected_asset = st.selectbox("Select Asset for Trending", assets)

            if selected_asset:
                trends = analyze_trends(
                    selected_asset, events, start_time, end_time, period="M"
                )
                if trends:
                    df_trends = pd.DataFrame([t.model_dump() for t in trends])

                    fig_mtbf = px.line(
                        df_trends,
                        x="period",
                        y="mtbf_hours",
                        title=f"{selected_asset} - Monthly MTBF",
                        markers=True,
                    )
                    st.plotly_chart(fig_mtbf, use_container_width=True)

                    fig_dt = px.bar(
                        df_trends,
                        x="period",
                        y="downtime_hours",
                        title=f"{selected_asset} - Monthly Downtime",
                        color_discrete_sequence=["indianred"],
                    )
                    st.plotly_chart(fig_dt, use_container_width=True)

        with tab5:
            st.header("Weibull & Maintenance Policy")
            weibull_asset = st.selectbox(
                "Select Asset for Weibull Analysis", assets, key="w_asset"
            )

            # Extract Time To Failure (TTF) approximations: Uptime between corrective events
            tl = timelines[weibull_asset]
            ttf_list = [
                i.duration_hours
                for i in tl.intervals
                if i.state == "RUNNING" and i.duration_hours > 0
            ]

            if len(ttf_list) >= 3:
                weibull_res = analyze_weibull(ttf_list)
                if weibull_res:
                    c1, c2 = st.columns(2)
                    c1.metric("Beta (Shape)", f"{weibull_res.beta_shape:.3f}")
                    c2.metric("Eta (Scale)", f"{weibull_res.eta_scale:.1f} h")
                    st.info(weibull_res.interpretation)
                    for w in weibull_res.warnings:
                        st.warning(w)

                    st.subheader("Maintenance Policy Comparison")
                    pm_cost = st.number_input(
                        "Preventive Intervention Cost ($)", value=1000.0
                    )
                    cm_cost = st.number_input(
                        "Corrective Intervention Cost ($)", value=5000.0
                    )

                    policies = evaluate_maintenance_policies(
                        weibull_res, pm_cost, cm_cost
                    )
                    df_policies = pd.DataFrame([p.model_dump() for p in policies])
                    st.dataframe(df_policies, use_container_width=True)
            else:
                st.warning(
                    f"Not enough failure data to perform Weibull analysis on {weibull_asset}. Requires at least 3 failure intervals."
                )

    else:
        st.info("Upload a CSV file with maintenance records to begin analysis.")


if __name__ == "__main__":
    run_ui()
