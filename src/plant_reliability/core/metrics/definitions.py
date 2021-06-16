from typing import Any

from pydantic import BaseModel

from plant_reliability.core.domain.models import AssetState, Event, MaintenanceType
from plant_reliability.core.timeline.reconstruction import AssetTimeline


class MetricResult(BaseModel):
    name: str
    value: float | None
    units: str
    equation: str
    components: dict[str, Any]
    definition: str
    error: str | None = None
    warning: str | None = None


def calculate_availability(timeline: AssetTimeline) -> MetricResult:
    uptime = timeline.get_uptime_hours()
    downtime = timeline.get_downtime_hours()
    total = uptime + downtime

    error = None
    val = None
    if total == 0:
        error = "La disponibilidad (Availability) no puede ser calculada porque la suma de tiempo de operación y tiempo de parada es cero."
    else:
        val = uptime / total * 100.0

    return MetricResult(
        name="Disponibilidad (Availability)",
        value=val,
        units="%",
        equation="Tiempo de Operación / (Tiempo de Operación + Tiempo de Parada)",
        components={
            "Tiempo de Operación (h)": uptime,
            "Tiempo de Parada (h)": downtime,
        },
        definition="Probabilidad de que un activo se encuentre operando satisfactoriamente en cualquier momento bajo las condiciones declaradas.",
        error=error,
    )


def calculate_mtbf(timeline: AssetTimeline, events: list[Event]) -> MetricResult:
    uptime = timeline.get_uptime_hours()

    # Failures are events with state FAILED or maintenance_type CORRECTIVE
    failures = [
        e
        for e in events
        if e.asset_id == timeline.asset_id
        and (
            e.state == AssetState.FAILED
            or e.maintenance_type == MaintenanceType.CORRECTIVE
        )
    ]
    num_failures = len(failures)

    error = None
    warning = None
    val = None

    if uptime == 0.0:
        error = "El MTBF no puede ser calculado a partir del tiempo de operación porque éste es cero."
    elif num_failures == 0:
        warning = "No se detectaron fallas en el período analizado. El MTBF es teóricamente infinito."
    else:
        val = uptime / num_failures

    return MetricResult(
        name="MTBF",
        value=val,
        units="horas",
        equation="Tiempo de Operación / Cantidad de Fallas",
        components={"Tiempo de Operación (h)": uptime, "Fallas": num_failures},
        definition="Tiempo Medio Entre Fallas (Mean Time Between Failures). Tiempo promedio de operación entre fallas reparables.",
        error=error,
        warning=warning,
    )


def calculate_mttr(events: list[Event], asset_id: str) -> MetricResult:
    # MTTR is based on repair times (duration of corrective events)
    repairs = [
        e
        for e in events
        if e.asset_id == asset_id
        and (
            e.state == AssetState.FAILED
            or e.maintenance_type == MaintenanceType.CORRECTIVE
        )
    ]

    num_repairs = len(repairs)

    # We must check if these repair events actually have duration
    valid_repairs = [
        e for e in repairs if e.end_time is not None and e.start_time is not None
    ]
    num_valid = len(valid_repairs)

    total_repair_time = sum(e.duration_hours for e in valid_repairs)

    error = None
    val = None

    if num_repairs > 0 and num_valid < num_repairs:
        error = f"No se puede calcular el MTTR con precisión. Se encontraron {num_repairs} eventos de falla, pero solo {num_valid} contienen una fecha válida de fin de reparación."
    elif num_valid == 0:
        error = "No hay duraciones de reparación disponibles. Campos requeridos: inicio_falla, fin_reparacion."
    else:
        val = total_repair_time / num_valid

    return MetricResult(
        name="MTTR",
        value=val,
        units="horas",
        equation="Tiempo Total de Reparación / Cantidad de Reparaciones Válidas",
        components={
            "Tiempo Total de Reparación (h)": total_repair_time,
            "Cantidad de Reparaciones Válidas": num_valid,
            "Eventos Excluidos (Sin fecha fin)": num_repairs - num_valid,
        },
        definition="Tiempo Medio Para Reparar (Mean Time To Repair). El tiempo promedio requerido para reparar un activo fallado.",
        error=error,
    )


def calculate_oee(
    availability: MetricResult,
    performance: float | None = None,
    quality: float | None = None,
) -> MetricResult:
    """
    OEE = Availability * Performance * Quality
    """
    val = None
    warning = None
    error = None

    a_val = availability.value / 100.0 if availability.value is not None else None

    components = {"Disponibilidad (%)": availability.value}

    if performance is None or quality is None:
        warning = "No se ingresaron los componentes de Rendimiento (Performance) o Calidad (Quality). Solo el componente de Disponibilidad es calculable."
        if a_val is not None:
            val = a_val * 100.0
    else:
        components["Rendimiento (%)"] = performance * 100.0
        components["Calidad (%)"] = quality * 100.0
        if a_val is not None:
            val = (a_val * performance * quality) * 100.0

    if availability.error:
        error = "El OEE no puede ser calculado porque la Disponibilidad es inválida."

    return MetricResult(
        name="OEE (Efectividad General del Equipo)",
        value=val,
        units="%",
        equation="Disponibilidad * Rendimiento * Calidad",
        components=components,
        definition="OEE (Overall Equipment Effectiveness). Es una medida integral de la productividad de manufactura.",
        error=error,
        warning=warning,
    )
