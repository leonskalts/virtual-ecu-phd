#!/usr/bin/env python3
"""Run the recommended end-to-end study workflow for the virtual ECU platform."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECOMMENDED_LOGS_DIR = PROJECT_ROOT / "logs" / "recommended_study"
RECOMMENDED_RESULTS_DIR = PROJECT_ROOT / "results" / "paper"
RECOMMENDED_BATCH_DIR = PROJECT_ROOT / "results" / "batch" / "paper_quick"

RECOMMENDED_CAMPAIGNS: Sequence[Tuple[str, str]] = (
    ("baseline", "Baseline"),
    ("fan_stuck_hot_stress", "Fan Stuck Hot Stress"),
    ("calibration_memory_corruption", "Calibration Memory Corruption"),
    ("stale_sensor_data_only", "Stale Sensor Data Only"),
    ("stale_sensor_data_hot_stress", "Stale Sensor Data Hot Stress"),
    ("paper_default", "Paper Default"),
)


def detect_executable() -> Path:
    for candidate in (PROJECT_ROOT / "virtual_ecu", PROJECT_ROOT / "virtual_ecu.exe"):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Compiled virtual ECU executable not found. Build it first with 'make'."
    )


def run_command(command: Sequence[str]) -> None:
    completed = subprocess.run(
        list(command),
        cwd=PROJECT_ROOT,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}")


def run_campaign_logs(executable: Path) -> List[Path]:
    RECOMMENDED_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    generated_logs: List[Path] = []

    for campaign_id, _label in RECOMMENDED_CAMPAIGNS:
        log_path = RECOMMENDED_LOGS_DIR / f"{campaign_id}.csv"
        print(f"Running recommended campaign: {campaign_id}")
        run_command((str(executable), str(log_path), campaign_id))
        generated_logs.append(log_path)

    return generated_logs


def write_manifest(generated_logs: Iterable[Path]) -> None:
    RECOMMENDED_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RECOMMENDED_RESULTS_DIR / "recommended_study_manifest.txt"

    important_outputs = [
        RECOMMENDED_RESULTS_DIR / "table_1_campaign_definition.csv",
        RECOMMENDED_RESULTS_DIR / "table_2_cross_campaign_results.csv",
        RECOMMENDED_RESULTS_DIR / "figure_1_coolant_temperature_vs_time.png",
        RECOMMENDED_RESULTS_DIR / "figure_2_safe_state_timeline.png",
        RECOMMENDED_RESULTS_DIR / "figure_3_fan_command_vs_actual.png",
        RECOMMENDED_BATCH_DIR / "aggregate_summary.csv",
        RECOMMENDED_BATCH_DIR / "analysis" / "table_batch_2_fault_type_summary.csv",
        RECOMMENDED_BATCH_DIR / "analysis_claims" / "table_claim_1_main_comparison.csv",
    ]

    with manifest_path.open("w", encoding="utf-8") as handle:
        handle.write("Virtual ECU Recommended Study Manifest\n")
        handle.write("====================================\n\n")
        handle.write("Recommended single-run campaign set:\n")
        for campaign_id, label in RECOMMENDED_CAMPAIGNS:
            handle.write(f"- {campaign_id}: {label}\n")

        handle.write("\nGenerated single-run logs:\n")
        for log_path in generated_logs:
            handle.write(f"- {log_path.relative_to(PROJECT_ROOT)}\n")

        handle.write("\nKey output files:\n")
        for output_path in important_outputs:
            handle.write(f"- {output_path.relative_to(PROJECT_ROOT)}\n")


def main() -> None:
    executable = detect_executable()

    generated_logs = run_campaign_logs(executable)

    print("Generating recommended single-run analysis bundle")
    run_command(
        (
            sys.executable,
            "scripts/generate_paper_results.py",
            "--logs-dir",
            str(RECOMMENDED_LOGS_DIR),
            "--results-dir",
            str(RECOMMENDED_RESULTS_DIR),
        )
    )

    print("Refreshing compact batch study")
    run_command(
        (
            sys.executable,
            "scripts/run_batch_experiments.py",
            "--profile",
            "quick",
            "--output-root",
            "results/batch",
            "--batch-id",
            "paper_quick",
        )
    )

    print("Generating batch-analysis outputs")
    run_command(
        (
            sys.executable,
            "scripts/generate_batch_paper_results.py",
            "--aggregate-csv",
            str(RECOMMENDED_BATCH_DIR / "aggregate_summary.csv"),
            "--analysis-dir",
            str(RECOMMENDED_BATCH_DIR / "analysis"),
        )
    )

    print("Generating claim-focused outputs")
    run_command(
        (
            sys.executable,
            "scripts/generate_batch_claim_results.py",
            "--aggregate-csv",
            str(RECOMMENDED_BATCH_DIR / "aggregate_summary.csv"),
            "--draft-fault-table",
            str(RECOMMENDED_BATCH_DIR / "analysis" / "table_batch_2_fault_type_summary.csv"),
            "--output-dir",
            str(RECOMMENDED_BATCH_DIR / "analysis_claims"),
        )
    )

    write_manifest(generated_logs)

    print("\nRecommended study workflow complete.")
    print(f"Single-run logs: {RECOMMENDED_LOGS_DIR}")
    print(f"Single-run paper/demo bundle: {RECOMMENDED_RESULTS_DIR}")
    print(f"Compact batch study: {RECOMMENDED_BATCH_DIR}")


if __name__ == "__main__":
    main()
