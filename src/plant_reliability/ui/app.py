import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime
import io

from plant_reliability.importers.mapping import ImportMapping
from plant_reliability.importers.csv_importer import CsvImporter
from plant_reliability.importers.excel_importer import ExcelImporter
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


def create_template_excel():
    df = pd.DataFrame(
        {
            "equipment": ["Bomba-01", "Motor-02"],
            "failure_start": ["2024-01-10 08:00", "2024-02-15 14:30"],
            "failure_end": ["2024-01-10 12:00", "2024-02-16 09:00"],
            "maintenance_type": ["CORRECTIVE", "PREVENTIVE"],
            "failure_mode": ["Rodamiento", "Lubricacion"],
            "cost": [1500, 200],
            "work_order": ["OT-101", "OT-102"],
        }
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Mantenimiento")
    return buffer.getvalue()


def run_ui():
    st.set_page_config(
        page_title="Plant Reliability", layout="wide", initial_sidebar_state="expanded"
    )
    st.title("Plant Reliability Analysis")

    st.sidebar.header("Data Upload")

    st.sidebar.markdown(
        "Para empezar, podés descargar la plantilla o subir tu propio Excel/CSV."
    )
    st.sidebar.download_button(
        label="📥 Descargar Plantilla Excel",
        data=create_template_excel(),
        file_name="plantilla_mantenimiento.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.sidebar.divider()
    uploaded_file = st.sidebar.file_uploader(
        "Subir Archivo de Mantenimiento", type=["csv", "xlsx", "xls"]
    )

    if uploaded_file is not None:
        file_ext = Path(uploaded_file.name).suffix.lower()

        # Read raw columns to map them
        if file_ext == ".csv":
            raw_df = pd.read_csv(uploaded_file, nrows=0)
        else:
            raw_df = pd.read_excel(uploaded_file, nrows=0)

        columns = list(raw_df.columns)

        st.subheader("Mapeo de Columnas (Reconocimiento Automático)")
        st.info(
            "Revisá que las columnas de tu archivo coincidan con lo que necesita el motor. Si alguna no coincide, cambiala en los selectores."
        )

        # Best-effort auto mapping
        def guess_col(possible_names):
            for p in possible_names:
                for c in columns:
                    if p.lower() in c.lower():
                        return c
            return None if columns else ""

        col1, col2, col3 = st.columns(3)
        with col1:
            asset_col = st.selectbox(
                "Equipo / Activo (Obligatorio)",
                columns,
                index=columns.index(guess_col(["equip", "asset", "maquina", "tag"]))
                if guess_col(["equip", "asset", "maquina", "tag"])
                else 0,
            )
            start_col = st.selectbox(
                "Inicio de Falla (Obligatorio)",
                columns,
                index=columns.index(guess_col(["start", "inicio", "falla"]))
                if guess_col(["start", "inicio", "falla"])
                else 0,
            )
        with col2:
            end_col = st.selectbox(
                "Fin de Reparación (Opcional)",
                ["-- Ninguno --"] + columns,
                index=(columns.index(guess_col(["end", "fin", "reparacion"])) + 1)
                if guess_col(["end", "fin", "reparacion"])
                else 0,
            )
            type_col = st.selectbox(
                "Tipo Mantenimiento (Opcional)",
                ["-- Ninguno --"] + columns,
                index=(columns.index(guess_col(["type", "tipo", "mantenimiento"])) + 1)
                if guess_col(["type", "tipo", "mantenimiento"])
                else 0,
            )
        with col3:
            mode_col = st.selectbox(
                "Modo de Falla (Opcional)",
                ["-- Ninguno --"] + columns,
                index=(
                    columns.index(guess_col(["mode", "modo", "causa", "sintoma"])) + 1
                )
                if guess_col(["mode", "modo", "causa", "sintoma"])
                else 0,
            )
            cost_col = st.selectbox(
                "Costo (Opcional)",
                ["-- Ninguno --"] + columns,
                index=(columns.index(guess_col(["cost", "precio"])) + 1)
                if guess_col(["cost", "precio"])
                else 0,
            )

        if st.button("Ejecutar Análisis", type="primary"):
            # Prepare mapping
            mapping = ImportMapping(
                asset_id=asset_col,
                start_time=start_col,
                end_time=end_col if end_col != "-- Ninguno --" else None,
                maintenance_type=type_col if type_col != "-- Ninguno --" else None,
                failure_mode=mode_col if mode_col != "-- Ninguno --" else None,
                cost=cost_col if cost_col != "-- Ninguno --" else None,
            )

            temp_path = Path(f"temp_upload{file_ext}")
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            importer = (
                CsvImporter(mapping) if file_ext == ".csv" else ExcelImporter(mapping)
            )
            events, raw_count = importer.read_file(str(temp_path))

            st.divider()

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
                c1.metric("Filas Importadas", dq.rows_imported)
                c2.metric("Registros Válidos", dq.valid_records)
                c3.metric("Fechas Completas", f"{dq.timestamp_completeness:.1f}%")

                if dq.issues:
                    for issue in dq.issues:
                        st.warning(f"**{issue.severity.value}**: {issue.description}")
                else:
                    st.success(
                        "No se detectaron problemas de calidad de datos. Listo para analizar."
                    )

            with tab2:
                st.header("Bad Actors")
                bad_actors = identify_bad_actors(events, timelines, BadActorConfig())
                if bad_actors:
                    df_actors = pd.DataFrame(
                        [
                            {
                                "Equipo": a.asset_id,
                                "Score de Riesgo": round(a.composite_score, 3),
                                "Fallas": a.failure_frequency,
                                "Horas Parado": round(a.downtime_hours, 1),
                                "Costo ($)": round(a.maintenance_cost, 2),
                            }
                            for a in bad_actors
                        ]
                    )
                    st.dataframe(df_actors, use_container_width=True)

            with tab3:
                st.header("Análisis de Pareto")
                col_p1, col_p2 = st.columns(2)
                dimension = col_p1.selectbox("Dimensión", ["asset_id", "failure_mode"])
                metric = col_p2.selectbox(
                    "Métrica", ["downtime_hours", "event_count", "cost"]
                )

                pareto_res = analyze_pareto(events, dimension, metric)
                if pareto_res.items:
                    df_pareto = pd.DataFrame([i.model_dump() for i in pareto_res.items])

                    fig = go.Figure()
                    fig.add_trace(
                        go.Bar(
                            x=df_pareto["category"],
                            y=df_pareto["value"],
                            name="Valor",
                            yaxis="y1",
                        )
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=df_pareto["category"],
                            y=df_pareto["cumulative_percentage"],
                            name="% Acumulado",
                            mode="lines+markers",
                            yaxis="y2",
                            line=dict(color="red"),
                        )
                    )
                    fig.update_layout(
                        title=f"Pareto: {metric} por {dimension}",
                        yaxis=dict(title="Valor", side="left"),
                        yaxis2=dict(
                            title="% Acumulado",
                            side="right",
                            overlaying="y",
                            range=[0, 105],
                        ),
                        hovermode="x unified",
                    )
                    st.plotly_chart(fig, use_container_width=True)

            with tab4:
                st.header("Tendencias de Equipos")
                selected_asset = st.selectbox("Seleccionar Equipo", assets)

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
                            title=f"{selected_asset} - MTBF Mensual (Horas)",
                            markers=True,
                        )
                        st.plotly_chart(fig_mtbf, use_container_width=True)

                        fig_dt = px.bar(
                            df_trends,
                            x="period",
                            y="downtime_hours",
                            title=f"{selected_asset} - Horas Parado por Mes",
                            color_discrete_sequence=["indianred"],
                        )
                        st.plotly_chart(fig_dt, use_container_width=True)

            with tab5:
                st.header("Weibull & Mantenimiento Preventivo")
                weibull_asset = st.selectbox(
                    "Equipo para Análisis Weibull", assets, key="w_asset"
                )

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
                        c1.metric("Beta (Forma)", f"{weibull_res.beta_shape:.3f}")
                        c2.metric("Eta (Escala)", f"{weibull_res.eta_scale:.1f} h")
                        st.info(weibull_res.interpretation)
                        for w in weibull_res.warnings:
                            st.warning(w)

                        st.subheader("Comparación de Políticas (LCC)")
                        pm_cost = st.number_input(
                            "Costo Intervención Preventiva ($)", value=1000.0
                        )
                        cm_cost = st.number_input(
                            "Costo Intervención Correctiva / Falla ($)", value=5000.0
                        )

                        policies = evaluate_maintenance_policies(
                            weibull_res, pm_cost, cm_cost
                        )
                        df_policies = pd.DataFrame(
                            [
                                {
                                    "Política": p.policy_name,
                                    "Costo Esperado / Hora": round(
                                        p.expected_cost_per_unit_time, 2
                                    ),
                                    "Intervalo Óptimo PM (h)": round(
                                        p.optimal_pm_interval, 1
                                    )
                                    if p.optimal_pm_interval > 0
                                    else "N/A",
                                }
                                for p in policies
                            ]
                        )
                        st.dataframe(df_policies, use_container_width=True)
                else:
                    st.warning(
                        f"No hay suficientes datos de falla para {weibull_asset}. Se requieren al menos 3 intervalos de tiempo de operación hasta la falla."
                    )

    else:
        st.info(
            "Subí un archivo CSV o Excel con registros de mantenimiento para empezar."
        )


if __name__ == "__main__":
    run_ui()
