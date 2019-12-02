import typer
import pandas as pd
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from plant_reliability.importers.mapping import ImportMapping
from plant_reliability.importers.csv_importer import CsvImporter
from plant_reliability.importers.excel_importer import ExcelImporter
from plant_reliability.core.validation.data_quality import DataQualityEngine
from plant_reliability.core.timeline.reconstruction import reconstruct_timeline
from plant_reliability.core.metrics.definitions import (
    calculate_mtbf,
    calculate_mttr,
    calculate_availability,
)
from plant_reliability.analysis.weibull.engine import analyze_weibull
from plant_reliability.analysis.bad_actors.engine import (
    identify_bad_actors,
    BadActorConfig,
)

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
    """Validate a dataset and print a Data Quality Report."""
    mapping = ImportMapping.default()
    events, raw_count = load_data(filepath, mapping)

    engine = DataQualityEngine()
    report = engine.evaluate_events(events, raw_count)

    console.print(f"\n[bold]DATA QUALITY REPORT[/bold]")
    console.print(f"Rows imported: {report.rows_imported}")
    console.print(f"Valid records: {report.valid_records}")
    console.print(f"Timestamp completeness: {report.timestamp_completeness:.1f} %")
    console.print(f"Asset ID completeness: {report.asset_id_completeness:.1f} %")
    console.print(
        f"Failure-mode completeness: {report.failure_mode_completeness:.1f} %"
    )

    if report.issues:
        console.print("\n[bold]Issues:[/bold]")
        for issue in report.issues:
            color = "red" if issue.severity.value in ["ERROR", "BLOCKING"] else "yellow"
            console.print(
                f"[{color}]{issue.severity.value}[/{color}]: {issue.description}"
            )
            if issue.remediation:
                console.print(f"  - {issue.remediation}")
    else:
        console.print("\n[green]No data quality issues detected.[/green]")


@app.command()
def explain(metric: str, asset: str, filepath: Path):
    """Explain exactly how a metric is calculated for an asset."""
    metric = metric.upper()
    mapping = ImportMapping.default()
    events, _ = load_data(filepath, mapping)

    if not events:
        console.print("[red]No valid events found in dataset.[/red]")
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
        console.print(f"[red]Unknown metric: {metric}[/red]")
        return

    console.print(f"\n[bold]{res.name} - {asset}[/bold]\n")
    console.print(f"[bold]Definition:[/bold]\n{res.definition}\n")
    console.print(f"[bold]Equation:[/bold]\n{res.equation}\n")

    console.print("[bold]Components:[/bold]")
    for k, v in res.components.items():
        console.print(f"  {k}: {v:.2f}" if isinstance(v, float) else f"  {k}: {v}")

    console.print(f"\n[bold green]Result: {res.value:.2f} {res.units}[/bold green]\n")


@app.command()
def analyze(filepath: Path):
    """Run a comprehensive reliability analysis."""
    console.print(f"Analyzing {filepath}...")
    mapping = ImportMapping.default()
    events, _ = load_data(filepath, mapping)

    if not events:
        console.print("[red]No valid events to analyze.[/red]")
        return

    start_time = min(e.start_time for e in events if e.start_time)
    end_time = max(e.end_time or e.start_time for e in events if e.start_time)

    # Get unique assets
    assets = list(set(e.asset_id for e in events if e.asset_id))
    timelines = {
        a: reconstruct_timeline(a, events, start_time, end_time) for a in assets
    }

    bad_actors = identify_bad_actors(events, timelines, BadActorConfig())

    table = Table(title="Top 10 Bad Actors")
    table.add_column("Asset")
    table.add_column("Score", justify="right")
    table.add_column("Failures", justify="right")
    table.add_column("Downtime (h)", justify="right")

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
    """Generate a comprehensive HTML reliability report."""
    from plant_reliability.reporting.html_generator import generate_html_report

    console.print(f"Reading dataset: {filepath}...")
    mapping = ImportMapping.default()
    events, raw_count = load_data(filepath, mapping)

    if not events:
        console.print("[red]No valid events to analyze.[/red]")
        return

    engine = DataQualityEngine()
    dq_report = engine.evaluate_events(events, raw_count)

    start_time = min(e.start_time for e in events if e.start_time)
    end_time = max(e.end_time or e.start_time for e in events if e.start_time)

    assets = list(set(e.asset_id for e in events if e.asset_id))
    timelines = {
        a: reconstruct_timeline(a, events, start_time, end_time) for a in assets
    }
    bad_actors = identify_bad_actors(events, timelines, BadActorConfig())

    generate_html_report(dq_report, bad_actors, timelines, events, str(output))
    console.print(
        f"[bold green]Report successfully generated at: {output}[/bold green]"
    )


@app.command()
def demo():
    """Generate and analyze a synthetic demo dataset."""
    from plant_reliability.examples.demo_generator import generate_demo_dataset

    console.print("[bold green]Generating synthetic demo dataset...[/bold green]")
    filepath = generate_demo_dataset()
    console.print(f"Created demo dataset at {filepath}\n")

    validate(filepath)
    console.print("\n")
    analyze(filepath)


@app.command()
def serve():
    """Launch the local web interface (Streamlit)."""
    import subprocess
    import sys
    from pathlib import Path

    app_path = Path(__file__).parent.parent / "ui" / "app.py"
    console.print("[bold green]Starting local web interface...[/bold green]")
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])


if __name__ == "__main__":
    app()
