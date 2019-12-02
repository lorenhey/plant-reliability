# plant-reliability

"plant-reliability" turns messy maintenance records into auditable reliability engineering.

It is an open-source reliability engineering toolkit designed for real-world maintenance data, transforming imperfect CSV and Excel files into reproducible, traceable, auditable reliability analysis.

## Core Principle

«A reliability metric is useless if the engineer cannot explain exactly how it was calculated.»

Every important result is auditable. For any calculated metric, you can inspect its definitions, assumptions, exclusions, and the intermediate variables.

## Quick Start

1. Install via `uv` or `pip`:
   ```bash
   uv pip install plant-reliability
   ```
2. Run the demo to see how it works instantly:
   ```bash
   plant-reliability demo
   ```
3. Analyze your own dataset:
   ```bash
   plant-reliability analyze maintenance.csv
   ```
4. Generate an HTML engineering report:
   ```bash
   plant-reliability report maintenance.csv --output report.html
   ```
5. Run the local interactive web interface:
   ```bash
   plant-reliability serve
   ```
6. Ask the engine to explain a metric calculation step-by-step:
   ```bash
   plant-reliability explain MTBF P-101 maintenance.csv
   ```

## Target Users
- Reliability engineers
- Maintenance planners
- Process and Mechanical engineers
- Asset managers

## Offline-First
Industrial data stays industrial. The core software works entirely locally. No telemetry. No proprietary API dependency.

## Features
- **Data Quality Engine:** Flags missing classifications, negative durations, and inconsistencies before you trust the metrics.
- **Timeline Reconstruction:** Automatically builds semantic asset timelines (Running, Failed, Planned Stop) based on raw records.
- **Metrics Engine:** MTBF, MTTR, MDT, Availability.
- **Bad Actor Analysis:** Configurable composite scoring to find assets truly hurting your plant (Frequency, Downtime, Cost, Chronicity).
- **Weibull Analysis:** 2-parameter Weibull parameter estimation and interpretation (early-life, random, wear-out).

## Input Formats
By default, the CSV/Excel importer expects:
- `equipment`
- `failure_start` (Format: YYYY-MM-DD HH:MM:SS)
- `failure_end` (Format: YYYY-MM-DD HH:MM:SS)
- `maintenance_type` (CORRECTIVE, PREVENTIVE, INSPECTION)
- `failure_mode` (String)
- `cost` (Numeric)
- `work_order` (String)

Custom mapping profiles are supported programmatically.

## Development
This project requires Python 3.12+ and uses `uv` for dependency management.
```bash
uv sync
uv run pytest
```
