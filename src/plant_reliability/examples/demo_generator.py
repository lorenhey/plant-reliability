import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path


def generate_demo_dataset(output_dir: str = ".") -> Path:
    """Generates a synthetic but realistic maintenance dataset."""
    np.random.seed(42)

    assets = (
        [f"P-10{i}" for i in range(1, 6)]
        + [f"C-20{i}" for i in range(1, 4)]
        + ["M-301", "M-302"]
    )

    start_date = datetime(2023, 1, 1)

    events = []

    for asset in assets:
        current_date = start_date

        # P-101 is a bad actor
        if asset == "P-101":
            mtbf_days = 15
            mttr_hours = 12
        elif asset == "C-201":  # Wear-out behavior (increasing failure rate)
            mtbf_days = 60
            mttr_hours = 24
        else:
            mtbf_days = np.random.uniform(45, 120)
            mttr_hours = np.random.uniform(2, 8)

        while current_date < datetime(2025, 12, 31):
            if asset == "C-201":
                # Simulated wear-out: time between failures decreases
                time_to_fail = np.random.weibull(2.5) * mtbf_days
            else:
                # Random failures
                time_to_fail = np.random.exponential(mtbf_days)

            fail_date = current_date + timedelta(days=time_to_fail)

            if fail_date > datetime(2025, 12, 31):
                break

            repair_time = np.random.exponential(mttr_hours)
            repair_end = fail_date + timedelta(hours=repair_time)

            modes = [
                "SEAL_LEAK",
                "BEARING_FAIL",
                "VIBRATION",
                "OVERHEATING",
                "SENSOR_FAULT",
            ]

            events.append(
                {
                    "equipment": asset,
                    "failure_start": fail_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "failure_end": repair_end.strftime("%Y-%m-%d %H:%M:%S"),
                    "maintenance_type": "CORRECTIVE",
                    "failure_mode": np.random.choice(modes, p=[0.4, 0.3, 0.1, 0.1, 0.1])
                    if asset == "P-101"
                    else np.random.choice(modes),
                    "cost": round(np.random.uniform(500, 5000), 2),
                    "work_order": f"WO-{np.random.randint(10000, 99999)}",
                }
            )

            current_date = repair_end

    # Add some data quality issues intentionally
    # 1. Missing failure mode
    events[5]["failure_mode"] = None

    # 2. Negative repair duration
    bad_fail = datetime(2024, 5, 1)
    bad_repair = bad_fail - timedelta(hours=2)
    events.append(
        {
            "equipment": "P-103",
            "failure_start": bad_fail.strftime("%Y-%m-%d %H:%M:%S"),
            "failure_end": bad_repair.strftime("%Y-%m-%d %H:%M:%S"),
            "maintenance_type": "CORRECTIVE",
            "failure_mode": "UNKNOWN",
            "cost": 1000,
            "work_order": "WO-99999",
        }
    )

    df = pd.DataFrame(events)
    df = df.sort_values(by="failure_start")

    out_path = Path(output_dir) / "demo_dataset.csv"
    df.to_csv(out_path, index=False)

    return out_path
