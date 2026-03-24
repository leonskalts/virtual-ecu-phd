#!/usr/bin/env python3
"""Generate paper-ready tables and figures from virtual ECU campaign logs."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from typing import Dict, List

os.environ.setdefault("MPLCONFIGDIR", "/tmp/virtual_ecu_mpl")

import matplotlib.pyplot as plt


CAMPAIGNS = [
    {
        "campaign_id": "baseline",
        "label": "Baseline",
        "color": "#1f77b4",
        "raw_candidates": ["baseline.csv"],
        "summary_candidates": ["baseline_summary.csv"],
    },
    {
        "campaign_id": "fan_stuck_only",
        "label": "Fan Stuck Only",
        "color": "#d62728",
        "raw_candidates": ["permanent.csv", "fan_stuck_only.csv"],
        "summary_candidates": ["permanent_summary.csv", "fan_stuck_only_summary.csv"],
    },
    {
        "campaign_id": "fan_stuck_hot_stress",
        "label": "Fan Stuck Hot Stress",
        "color": "#ff7f0e",
        "raw_candidates": ["permanent_stress.csv", "fan_stuck_hot_stress.csv"],
        "summary_candidates": ["permanent_stress_summary.csv", "fan_stuck_hot_stress_summary.csv"],
    },
    {
        "campaign_id": "sensor_bias_only",
        "label": "Sensor Bias Only",
        "color": "#2ca02c",
        "raw_candidates": ["transient.csv", "sensor_bias_only.csv"],
        "summary_candidates": ["transient_summary.csv", "sensor_bias_only_summary.csv"],
    },
    {
        "campaign_id": "paper_default",
        "label": "Paper Default",
        "color": "#9467bd",
        "raw_candidates": ["paper_default.csv", "thermal_run.csv"],
        "summary_candidates": ["paper_default_summary.csv", "thermal_run_summary.csv"],
    },
]

TABLE_1_COLUMNS = [
    "campaign_id",
    "campaign_label",
    "campaign_category",
    "campaign_event_count",
    "campaign_ambient_offset_c",
    "campaign_engine_load_scale",
    "campaign_heat_generation_bias",
    "campaign_ram_air_scale",
    "campaign_event_1_mode_label",
    "campaign_event_1_behavior_label",
    "campaign_event_1_start_ms",
    "campaign_event_1_duration_ms",
    "campaign_event_1_parameter",
    "campaign_event_2_mode_label",
    "campaign_event_2_behavior_label",
    "campaign_event_2_start_ms",
    "campaign_event_2_duration_ms",
    "campaign_event_2_parameter",
    "campaign_event_3_mode_label",
    "campaign_event_3_behavior_label",
    "campaign_event_3_start_ms",
    "campaign_event_3_duration_ms",
    "campaign_event_3_parameter",
    "campaign_event_4_mode_label",
    "campaign_event_4_behavior_label",
    "campaign_event_4_start_ms",
    "campaign_event_4_duration_ms",
    "campaign_event_4_parameter",
]

TABLE_2_COLUMNS = [
    "campaign_id",
    "campaign_label",
    "campaign_category",
    "fault_present_in_campaign",
    "first_fault_start_ms",
    "detection_latency_ms",
    "detection_dtc_id",
    "detection_dtc_label",
    "safe_state_latency_ms",
    "first_safe_state_id",
    "first_safe_state_label",
    "max_coolant_temp_c",
    "safe_mode_duration_ms",
    "pump_tracking_error_mean_abs",
    "pump_tracking_error_max_abs",
    "fan_tracking_error_mean_abs",
    "fan_tracking_error_max_abs",
    "final_coolant_temp_c",
    "final_safe_state_id",
    "final_safe_state_label",
    "final_primary_dtc_id",
    "final_primary_dtc_label",
]

SAFE_STATE_TICKS = [0, 1, 2, 3]
SAFE_STATE_LABELS = ["Normal", "Precautionary", "Limp Home", "Shutdown"]
MAIN_FIGURE_CAMPAIGN_IDS = {"baseline", "fan_stuck_only", "fan_stuck_hot_stress"}

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "legend.fontsize": 10,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate main paper tables and figures from virtual ECU CSV logs."
    )
    parser.add_argument(
        "--logs-dir",
        default="logs",
        help="Directory containing campaign CSV and summary CSV files.",
    )
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Directory where generated tables and figures will be written.",
    )
    return parser.parse_args()


def first_existing_path(base_dir: Path, candidates: List[str]) -> Path | None:
    for candidate in candidates:
        path = base_dir / candidate
        if path.exists():
            return path
    return None


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def float_value(row: Dict[str, str], key: str) -> float:
    return float(row[key])


def int_value(row: Dict[str, str], key: str) -> int:
    return int(float(row[key]))


def sample_period_ms(rows: List[Dict[str, str]]) -> int:
    if len(rows) >= 2:
        delta = int_value(rows[1], "time_ms") - int_value(rows[0], "time_ms")
        if delta > 0:
            return delta
    return 100


def derive_summary_from_raw(rows: List[Dict[str, str]]) -> Dict[str, str]:
    first_row = rows[0]
    last_row = rows[-1]
    sample_ms = sample_period_ms(rows)
    fault_start_times = []
    pump_errors = []
    fan_errors = []
    max_coolant_temp_c = None
    safe_mode_duration_ms = 0
    detection_row = None
    safe_state_row = None

    for event_index in range(1, 5):
        mode_label = first_row.get(f"campaign_event_{event_index}_mode_label", "none")
        if mode_label != "none":
            fault_start_times.append(int_value(first_row, f"campaign_event_{event_index}_start_ms"))

    first_fault_start_ms = min(fault_start_times) if fault_start_times else 0
    fault_present = 1 if fault_start_times else 0

    for row in rows:
        time_ms = int_value(row, "time_ms")
        coolant_temp_c = float_value(row, "coolant_temp_true_c")
        pump_error = abs(float_value(row, "pump_tracking_error"))
        fan_error = abs(float_value(row, "fan_tracking_error"))
        safe_state_id = int_value(row, "safe_state_id")
        primary_dtc_id = int_value(row, "primary_dtc_id")

        if max_coolant_temp_c is None or coolant_temp_c > max_coolant_temp_c:
            max_coolant_temp_c = coolant_temp_c

        pump_errors.append(pump_error)
        fan_errors.append(fan_error)

        if safe_state_id != 0:
            safe_mode_duration_ms += sample_ms

        if (
            fault_present
            and time_ms >= first_fault_start_ms
            and detection_row is None
            and primary_dtc_id != 0
        ):
            detection_row = row

        if (
            fault_present
            and time_ms >= first_fault_start_ms
            and safe_state_row is None
            and safe_state_id != 0
        ):
            safe_state_row = row

    pump_mean_abs = sum(pump_errors) / len(pump_errors)
    fan_mean_abs = sum(fan_errors) / len(fan_errors)

    detection_latency_ms = -1
    detection_dtc_id = 0
    detection_dtc_label = "none"
    if detection_row is not None:
        detection_latency_ms = int_value(detection_row, "time_ms") - first_fault_start_ms
        detection_dtc_id = int_value(detection_row, "primary_dtc_id")
        detection_dtc_label = detection_row["primary_dtc_label"]

    safe_state_latency_ms = -1
    first_safe_state_id = 0
    first_safe_state_label = "normal"
    if safe_state_row is not None:
        safe_state_latency_ms = int_value(safe_state_row, "time_ms") - first_fault_start_ms
        first_safe_state_id = int_value(safe_state_row, "safe_state_id")
        first_safe_state_label = safe_state_row["safe_state_label"]

    return {
        "campaign_id": first_row["campaign_id"],
        "campaign_label": first_row["campaign_label"],
        "campaign_category": first_row["campaign_category"],
        "fault_present_in_campaign": str(fault_present),
        "first_fault_start_ms": str(first_fault_start_ms),
        "detection_latency_ms": str(detection_latency_ms),
        "detection_dtc_id": str(detection_dtc_id),
        "detection_dtc_label": detection_dtc_label,
        "safe_state_latency_ms": str(safe_state_latency_ms),
        "first_safe_state_id": str(first_safe_state_id),
        "first_safe_state_label": first_safe_state_label,
        "max_coolant_temp_c": f"{max_coolant_temp_c:.2f}",
        "safe_mode_duration_ms": str(safe_mode_duration_ms),
        "pump_tracking_error_mean_abs": f"{pump_mean_abs:.6f}",
        "pump_tracking_error_max_abs": f"{max(pump_errors):.6f}",
        "fan_tracking_error_mean_abs": f"{fan_mean_abs:.6f}",
        "fan_tracking_error_max_abs": f"{max(fan_errors):.6f}",
        "final_coolant_temp_c": f"{float_value(last_row, 'coolant_temp_true_c'):.2f}",
        "final_safe_state_id": str(int_value(last_row, "safe_state_id")),
        "final_safe_state_label": last_row["safe_state_label"],
        "final_primary_dtc_id": str(int_value(last_row, "primary_dtc_id")),
        "final_primary_dtc_label": last_row["primary_dtc_label"],
    }


def resolve_campaign(logs_dir: Path, spec: Dict[str, str]) -> Dict[str, object]:
    raw_path = first_existing_path(logs_dir, spec["raw_candidates"])
    summary_path = first_existing_path(logs_dir, spec["summary_candidates"])

    if raw_path is None:
        raise FileNotFoundError(
            f"Missing raw CSV for campaign '{spec['campaign_id']}' in {logs_dir}"
        )

    raw_rows = read_csv_rows(raw_path)
    if not raw_rows:
        raise ValueError(f"No time-series rows found in {raw_path}")

    first_row = raw_rows[0]
    if first_row["campaign_id"] != spec["campaign_id"]:
        raise ValueError(
            f"Raw CSV {raw_path} contains campaign_id '{first_row['campaign_id']}', "
            f"expected '{spec['campaign_id']}'"
        )

    summary_row = derive_summary_from_raw(raw_rows)

    return {
        "campaign_id": spec["campaign_id"],
        "label": spec["label"],
        "color": spec["color"],
        "raw_path": raw_path,
        "summary_path": summary_path,
        "rows": raw_rows,
        "first_row": first_row,
        "summary_row": summary_row,
    }


def write_table(path: Path, columns: List[str], rows: List[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_table_1(results_dir: Path, campaigns: List[Dict[str, object]]) -> None:
    table_rows = []

    for campaign in campaigns:
        first_row = campaign["first_row"]
        table_rows.append({column: first_row.get(column, "") for column in TABLE_1_COLUMNS})

    write_table(results_dir / "table_1_campaign_definition.csv", TABLE_1_COLUMNS, table_rows)


def write_table_2(results_dir: Path, campaigns: List[Dict[str, object]]) -> None:
    table_rows = []

    for campaign in campaigns:
        summary_row = campaign["summary_row"]
        table_rows.append({column: summary_row.get(column, "") for column in TABLE_2_COLUMNS})

    write_table(results_dir / "table_2_cross_campaign_results.csv", TABLE_2_COLUMNS, table_rows)


def raw_series(rows: List[Dict[str, str]], x_key: str, y_key: str) -> tuple[List[float], List[float]]:
    x_values = [float_value(row, x_key) for row in rows]
    y_values = [float_value(row, y_key) for row in rows]
    return x_values, y_values


def plot_figure_1(results_dir: Path, campaigns: List[Dict[str, object]]) -> None:
    main_campaigns = [
        campaign for campaign in campaigns if campaign["campaign_id"] in MAIN_FIGURE_CAMPAIGN_IDS
    ]
    fig, ax = plt.subplots(figsize=(9.0, 5.2), constrained_layout=True)

    for campaign in main_campaigns:
        time_s, coolant_temp = raw_series(campaign["rows"], "time_s", "coolant_temp_true_c")
        ax.plot(time_s, coolant_temp, linewidth=2.2, color=campaign["color"], label=campaign["label"])

    ax.axhline(108.0, color="#8c564b", linestyle="--", linewidth=1.2)
    ax.axhline(115.0, color="#7f7f7f", linestyle=":", linewidth=1.2)
    ax.text(119.0, 108.6, "Warning", color="#8c564b", ha="right", va="bottom")
    ax.text(119.0, 115.6, "Critical", color="#7f7f7f", ha="right", va="bottom")
    ax.set_xlim(0.0, 120.0)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Coolant Temperature [C]")
    ax.set_title("Figure 1. Coolant Temperature Trajectories")
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.8)
    ax.legend(loc="upper left", ncol=3, frameon=False)
    fig.savefig(results_dir / "figure_1_coolant_temperature_vs_time.png", dpi=200)
    plt.close(fig)


def plot_figure_2(results_dir: Path, campaigns: List[Dict[str, object]]) -> None:
    main_campaigns = [
        campaign for campaign in campaigns if campaign["campaign_id"] in MAIN_FIGURE_CAMPAIGN_IDS
    ]
    fig, axes = plt.subplots(
        len(main_campaigns), 1, sharex=True, figsize=(9.0, 6.8), constrained_layout=True
    )

    for axis, campaign in zip(axes, main_campaigns):
        time_s, safe_state = raw_series(campaign["rows"], "time_s", "safe_state_id")
        axis.step(time_s, safe_state, where="post", color=campaign["color"], linewidth=2.2)
        axis.set_yticks(SAFE_STATE_TICKS)
        axis.set_yticklabels(SAFE_STATE_LABELS)
        axis.set_ylim(-0.2, 3.2)
        axis.set_ylabel(campaign["label"], rotation=0, labelpad=44, va="center")
        axis.grid(True, linestyle=":", linewidth=0.6, alpha=0.8)

    axes[0].set_title("Figure 2. Safe-State Timelines")
    axes[0].text(1.0, 1.10, "Baseline and permanent-fault campaigns", transform=axes[0].transAxes)
    axes[-1].set_xlim(0.0, 120.0)
    axes[-1].set_xlabel("Time [s]")
    fig.savefig(results_dir / "figure_2_safe_state_timeline.png", dpi=200)
    plt.close(fig)


def plot_figure_3(results_dir: Path, campaigns: List[Dict[str, object]]) -> None:
    permanent_campaigns = [
        campaign
        for campaign in campaigns
        if campaign["campaign_id"] in {"fan_stuck_only", "fan_stuck_hot_stress"}
    ]

    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(9.0, 6.4), constrained_layout=True)

    for axis, campaign in zip(axes, permanent_campaigns):
        rows = campaign["rows"]
        time_s, fan_command = raw_series(rows, "time_s", "fan_command")
        _, fan_actual = raw_series(rows, "time_s", "fan_actual")
        first_row = campaign["first_row"]
        fault_start_s = int_value(first_row, "campaign_event_1_start_ms") / 1000.0
        fault_end_s = (
            int_value(first_row, "campaign_event_1_start_ms") +
            int_value(first_row, "campaign_event_1_duration_ms")
        ) / 1000.0

        axis.plot(time_s, fan_command, color=campaign["color"], linewidth=2.2, label="Fan command")
        axis.plot(time_s, fan_actual, color="#111111", linestyle="--", linewidth=1.8, label="Fan actual")
        axis.axvspan(fault_start_s, fault_end_s, color=campaign["color"], alpha=0.12)
        axis.text(0.01, 0.90, campaign["label"], transform=axis.transAxes, ha="left", va="top")
        axis.set_ylabel("Fan [-]")
        axis.set_ylim(-0.05, 1.05)
        axis.grid(True, linestyle=":", linewidth=0.6, alpha=0.8)

    axes[0].set_title("Figure 3. Fan Command and Realized Fan Response")
    axes[0].legend(loc="upper center", bbox_to_anchor=(0.5, 1.18), ncol=2, frameon=False)
    axes[-1].set_xlim(0.0, 120.0)
    axes[-1].set_xlabel("Time [s]")
    fig.savefig(results_dir / "figure_3_fan_command_vs_actual.png", dpi=200)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    logs_dir = Path(args.logs_dir)
    results_dir = Path(args.results_dir)

    results_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

    campaign_data = [resolve_campaign(logs_dir, spec) for spec in CAMPAIGNS]

    write_table_1(results_dir, campaign_data)
    write_table_2(results_dir, campaign_data)
    plot_figure_1(results_dir, campaign_data)
    plot_figure_2(results_dir, campaign_data)
    plot_figure_3(results_dir, campaign_data)

    print(f"Wrote analysis outputs to {results_dir}")
    print(f"  - {results_dir / 'table_1_campaign_definition.csv'}")
    print(f"  - {results_dir / 'table_2_cross_campaign_results.csv'}")
    print(f"  - {results_dir / 'figure_1_coolant_temperature_vs_time.png'}")
    print(f"  - {results_dir / 'figure_2_safe_state_timeline.png'}")
    print(f"  - {results_dir / 'figure_3_fan_command_vs_actual.png'}")


if __name__ == "__main__":
    main()
