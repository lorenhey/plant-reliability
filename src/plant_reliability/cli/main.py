from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from plant_reliability.analysis.bad_actors.engine import (
    BadActorConfig,
    identify_bad_actors,
)
from plant_reliability.core.metrics.definitions import (
    calculate_availability,
    calculate_mtbf,
    calculate_mttr,
)
from plant_reliability.core.timeline.reconstruction import reconstruct_timeline
from plant_reliability.core.validation.data_quality import DataQualityEngine
from plant_reliability.importers.csv_importer import CsvImporter
from plant_reliability.importers.excel_importer import ExcelImporter
from plant_reliability.importers.mapping import ImportMapping

app = typer.Typer(
    help="plant-reliability: Turn messy maintenance records into auditable reliability engineering."
)
console = Console()


def load_data(filepath: Path, mapping: ImportMapping):
    if filepath.suffix.lower() == ".csv":
        importer = CsvImporter(mapping)
    elif filepath.suffix.lower() in [".xlsx", ".xls"]:
        importer = ExcelImporter(mapping)
    else:
        raise ValueError(f"Unsupported file format: {filepath.suffix}")

    return importer.read_file(str(filepath))


@app.command()
def validate(filepath: Path):
    """Valida un conjunto de datos y emite un Reporte de Calidad de Datos."""
    mapping = ImportMapping.default()
    events, raw_count = load_data(filepath, mapping)

    engine = DataQualityEngine()
    report = engine.evaluate_events(events, raw_count)

    console.print("\n[bold]REPORTE DE CALIDAD DE DATOS[/bold]")
    console.print(f"Filas importadas: {report.rows_imported}")
    console.print(f"Registros válidos: {report.valid_records}")
    console.print(f"Completitud de fechas: {report.timestamp_completeness:.1f} %")
    console.print(f"Completitud de equipos: {report.asset_id_completeness:.1f} %")
    console.print(
        f"Completitud de modos de falla: {report.failure_mode_completeness:.1f} %"
    )

    if report.issues:
        console.print("\n[bold]Problemas Detectados:[/bold]")
        for issue in report.issues:
            color = "red" if issue.severity.value in ["ERROR", "BLOCKING"] else "yellow"
            console.print(
                f"[{color}]{issue.severity.value}[/{color}]: {issue.description}"
            )
            if issue.remediation:
                console.print(f"  - {issue.remediation}")
    else:
        console.print(
            "\n[green]No se detectaron problemas de calidad de datos.[/green]"
        )


@app.command()
def explain(metric: str, asset: str, filepath: Path):
    """Explica exactamente cómo se calcula una métrica para un equipo."""
    metric = metric.upper()
    mapping = ImportMapping.default()
    events, _ = load_data(filepath, mapping)

    if not events:
        console.print("[red]No se encontraron eventos válidos en el archivo.[/red]")
        return

    start_time = min(e.start_time for e in events if e.start_time)
    end_time = max(e.end_time or e.start_time for e in events if e.start_time)

    timeline = reconstruct_timeline(asset, events, start_time, end_time)

    if metric == "MTBF":
        res = calculate_mtbf(timeline, events)
    elif metric == "MTTR":
        res = calculate_mttr(events, asset)
    elif metric == "AVAILABILITY":
        res = calculate_availability(timeline)
    else:
        console.print(f"[red]Métrica desconocida: {metric}[/red]")
        return

    console.print(f"\n[bold]{res.name} - {asset}[/bold]\n")
    if res.error:
        console.print(f"[bold red]ERROR:[/bold red] {res.error}")
        return

    console.print(f"[bold]Definición:[/bold]\n{res.definition}\n")
    console.print(f"[bold]Ecuación:[/bold]\n{res.equation}\n")

    console.print("[bold]Componentes:[/bold]")
    for k, v in res.components.items():
        console.print(f"  {k}: {v:.2f}" if isinstance(v, float) else f"  {k}: {v}")

    if res.warning:
        console.print(f"\n[bold yellow]ADVERTENCIA:[/bold yellow] {res.warning}")

    console.print(
        f"\n[bold green]Resultado: {res.value:.2f} {res.units}[/bold green]\n"
    )


@app.command()
def analyze(filepath: Path):
    """Ejecuta un análisis de confiabilidad completo (Bad Actors)."""
    console.print(f"Analizando {filepath}...")
    mapping = ImportMapping.default()
    events, _ = load_data(filepath, mapping)

    if not events:
        console.print("[red]No hay eventos válidos para analizar.[/red]")
        return

    start_time = min(e.start_time for e in events if e.start_time)
    end_time = max(e.end_time or e.start_time for e in events if e.start_time)

    # Get unique assets
    assets = list({e.asset_id for e in events if e.asset_id})
    timelines = {
        a: reconstruct_timeline(a, events, start_time, end_time) for a in assets
    }

    bad_actors = identify_bad_actors(events, timelines, BadActorConfig())

    table = Table(title="Top 10 Bad Actors")
    table.add_column("Equipo")
    table.add_column("Score", justify="right")
    table.add_column("Fallas", justify="right")
    table.add_column("Horas Parado", justify="right")

    for actor in bad_actors[:10]:
        table.add_row(
            actor.asset_id,
            f"{actor.composite_score:.2f}",
            str(actor.failure_frequency),
            f"{actor.downtime_hours:.1f}",
        )

    console.print(table)


@app.command()
def report(filepath: Path, output: Path = Path("reliability_report.html")):
    """Genera un reporte de confiabilidad completo en formato HTML."""
    from plant_reliability.reporting.html_generator import generate_html_report

    console.print(f"Leyendo archivo: {filepath}...")
    mapping = ImportMapping.default()
    events, raw_count = load_data(filepath, mapping)

    if not events:
        console.print("[red]No hay eventos válidos para analizar.[/red]")
        return

    engine = DataQualityEngine()
    dq_report = engine.evaluate_events(events, raw_count)

    start_time = min(e.start_time for e in events if e.start_time)
    end_time = max(e.end_time or e.start_time for e in events if e.start_time)

    assets = list({e.asset_id for e in events if e.asset_id})
    timelines = {
        a: reconstruct_timeline(a, events, start_time, end_time) for a in assets
    }
    bad_actors = identify_bad_actors(events, timelines, BadActorConfig())

    generate_html_report(dq_report, bad_actors, timelines, events, str(output))
    console.print(
        f"[bold green]Reporte generado exitosamente en: {output}[/bold green]"
    )


@app.command()
def demo():
    """Genera y analiza un dataset sintético de demostración."""
    from plant_reliability.examples.demo_generator import generate_demo_dataset

    console.print(
        "[bold green]Generando dataset sintético de demostración...[/bold green]"
    )
    filepath = generate_demo_dataset()
    console.print(f"Dataset creado en {filepath}\n")

    validate(filepath)
    console.print("\n")
    analyze(filepath)


@app.command()
def serve():
    """Inicia la interfaz web local (Streamlit)."""
    import subprocess
    import sys
    from pathlib import Path

    app_path = Path(__file__).parent.parent / "ui" / "app.py"
    console.print("[bold green]Iniciando interfaz web local...[/bold green]")
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])


if __name__ == "__main__":
    app()
