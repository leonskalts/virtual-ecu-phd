#!/usr/bin/env python3
"""Generate paper-ready tables and figures from batch aggregate results."""

from __future__ import annotations

import argparse
import csv
import math
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

os.environ.setdefault("MPLCONFIGDIR", "/tmp/virtual_ecu_mpl")

import matplotlib.pyplot as plt


DEFAULT_AGGREGATE = Path("results/batch/paper_quick/aggregate_summary.csv")
DEFAULT_ANALYSIS_DIR = Path("results/batch/paper_quick/analysis")

TABLE_BATCH_1_COLUMNS = [
    "fault_class",
    "number_of_runs",
    "mean_detection_latency_ms",
    "mean_safe_state_latency_ms",
    "mean_max_coolant_temperature_c",
    "mean_safe_mode_duration_ms",
    "most_common_final_safe_state",
    "most_common_final_dtc",
]

TABLE_BATCH_2_COLUMNS = [
    "fault_type",
    "number_of_runs",
    "min_detection_latency_ms",
    "mean_detection_latency_ms",
    "max_detection_latency_ms",
    "min_safe_state_latency_ms",
    "mean_safe_state_latency_ms",
    "max_safe_state_latency_ms",
    "min_max_coolant_temperature_c",
    "mean_max_coolant_temperature_c",
    "max_max_coolant_temperature_c",
    "final_safe_state_normal_count",
    "final_safe_state_precautionary_cooling_count",
    "final_safe_state_limp_home_count",
    "final_safe_state_controlled_shutdown_count",
]

SAFE_STATES = ["normal", "precautionary_cooling", "limp_home", "controlled_shutdown"]
SAFE_STATE_DISPLAY = {
    "normal": "Normal",
    "precautionary_cooling": "Precautionary",
    "limp_home": "Limp Home",
    "controlled_shutdown": "Shutdown",
}
FAULT_TYPE_DISPLAY = {
    "none": "Baseline",
    "sensor_bias": "Sensor Bias",
    "sensor_interface_intermittent": "Sensor Interface Intermittent",
    "pump_degraded": "Pump Degraded",
    "fan_stuck_off": "Fan Stuck Off",
    "calibration_memory_corruption": "Calibration Memory Corruption",
}
FAULT_TYPE_ORDER = [
    "none",
    "sensor_bias",
    "sensor_interface_intermittent",
    "pump_degraded",
    "fan_stuck_off",
    "calibration_memory_corruption",
]

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate paper-draft batch-analysis tables and figures from an aggregate summary CSV."
    )
    parser.add_argument(
        "--aggregate-csv",
        default=str(DEFAULT_AGGREGATE),
        help="Path to the batch aggregate summary CSV.",
    )
    parser.add_argument(
        "--analysis-dir",
        default=str(DEFAULT_ANALYSIS_DIR),
        help="Directory where analysis tables and figures will be written.",
    )
    return parser.parse_args()


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def int_or_none(value: str) -> int | None:
    parsed = int(float(value))
    return None if parsed < 0 else parsed


def float_or_none(value: str) -> float | None:
    if value == "":
        return None
    return float(value)


def mean_or_none(values: Sequence[float | int]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def format_float(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{decimals}f}"


def format_int(value: int | None) -> str:
    if value is None:
        return "n/a"
    return str(value)


def mode_or_none(values: Iterable[str]) -> str:
    filtered = [value for value in values if value]
    if not filtered:
        return "n/a"

    counts = Counter(filtered)
    top_count = max(counts.values())
    top_values = sorted(value for value, count in counts.items() if count == top_count)
    return top_values[0]


def grouped_rows(rows: Sequence[Dict[str, str]], key: str) -> Dict[str, List[Dict[str, str]]]:
    groups: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)
    return groups


def ordered_fault_types(rows: Sequence[Dict[str, str]]) -> List[str]:
    present = {row["fault_type"] for row in rows}
    ordered = [fault_type for fault_type in FAULT_TYPE_ORDER if fault_type in present]
    extras = sorted(present - set(ordered))
    return ordered + extras


def write_csv(path: Path, columns: Sequence[str], rows: Sequence[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        writer.writerows(rows)


def table_batch_1(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    table_rows: List[Dict[str, str]] = []

    for fault_class, class_rows in sorted(grouped_rows(rows, "fault_class").items()):
        detection_latencies = [
            value
            for value in (int_or_none(row["detection_latency_ms"]) for row in class_rows)
            if value is not None
        ]
        safe_state_latencies = [
            value
            for value in (int_or_none(row["safe_state_latency_ms"]) for row in class_rows)
            if value is not None
        ]
        max_coolant_temps = [
            value
            for value in (float_or_none(row["max_coolant_temperature_c"]) for row in class_rows)
            if value is not None
        ]
        safe_mode_durations = [
            value
            for value in (int_or_none(row["safe_mode_duration_ms"]) for row in class_rows)
            if value is not None
        ]

        table_rows.append(
            {
                "fault_class": fault_class,
                "number_of_runs": str(len(class_rows)),
                "mean_detection_latency_ms": format_float(mean_or_none(detection_latencies), 1),
                "mean_safe_state_latency_ms": format_float(mean_or_none(safe_state_latencies), 1),
                "mean_max_coolant_temperature_c": format_float(mean_or_none(max_coolant_temps), 2),
                "mean_safe_mode_duration_ms": format_float(mean_or_none(safe_mode_durations), 1),
                "most_common_final_safe_state": mode_or_none(row["final_safe_state"] for row in class_rows),
                "most_common_final_dtc": mode_or_none(row["final_dtc"] for row in class_rows),
            }
        )

    return table_rows


def table_batch_2(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    table_rows: List[Dict[str, str]] = []

    for fault_type in ordered_fault_types(rows):
        type_rows = [row for row in rows if row["fault_type"] == fault_type]
        detection_latencies = [
            value
            for value in (int_or_none(row["detection_latency_ms"]) for row in type_rows)
            if value is not None
        ]
        safe_state_latencies = [
            value
            for value in (int_or_none(row["safe_state_latency_ms"]) for row in type_rows)
            if value is not None
        ]
        max_coolant_temps = [
            value
            for value in (float_or_none(row["max_coolant_temperature_c"]) for row in type_rows)
            if value is not None
        ]
        safe_state_counts = Counter(row["final_safe_state"] for row in type_rows)

        table_rows.append(
            {
                "fault_type": fault_type,
                "number_of_runs": str(len(type_rows)),
                "min_detection_latency_ms": format_int(min(detection_latencies) if detection_latencies else None),
                "mean_detection_latency_ms": format_float(mean_or_none(detection_latencies), 1),
                "max_detection_latency_ms": format_int(max(detection_latencies) if detection_latencies else None),
                "min_safe_state_latency_ms": format_int(min(safe_state_latencies) if safe_state_latencies else None),
                "mean_safe_state_latency_ms": format_float(mean_or_none(safe_state_latencies), 1),
                "max_safe_state_latency_ms": format_int(max(safe_state_latencies) if safe_state_latencies else None),
                "min_max_coolant_temperature_c": format_float(min(max_coolant_temps) if max_coolant_temps else None, 2),
                "mean_max_coolant_temperature_c": format_float(mean_or_none(max_coolant_temps), 2),
                "max_max_coolant_temperature_c": format_float(max(max_coolant_temps) if max_coolant_temps else None, 2),
                "final_safe_state_normal_count": str(safe_state_counts.get("normal", 0)),
                "final_safe_state_precautionary_cooling_count": str(
                    safe_state_counts.get("precautionary_cooling", 0)
                ),
                "final_safe_state_limp_home_count": str(safe_state_counts.get("limp_home", 0)),
                "final_safe_state_controlled_shutdown_count": str(
                    safe_state_counts.get("controlled_shutdown", 0)
                ),
            }
        )

    return table_rows


def fault_type_labels(rows: Sequence[Dict[str, str]]) -> List[str]:
    return [FAULT_TYPE_DISPLAY.get(fault_type, fault_type) for fault_type in ordered_fault_types(rows)]


def grouped_metric_means(rows: Sequence[Dict[str, str]], column: str) -> List[float]:
    means: List[float] = []
    for fault_type in ordered_fault_types(rows):
        values = []
        for row in rows:
            if row["fault_type"] != fault_type:
                continue
            if column in {"detection_latency_ms", "safe_state_latency_ms", "safe_mode_duration_ms"}:
                parsed = int_or_none(row[column])
            else:
                parsed = float_or_none(row[column])
            if parsed is not None:
                values.append(parsed)

        means.append(float("nan") if not values else float(sum(values) / len(values)))
    return means


def plot_mean_bar(
    rows: Sequence[Dict[str, str]],
    column: str,
    ylabel: str,
    title: str,
    output_path: Path,
    color: str,
) -> None:
    labels = fault_type_labels(rows)
    values = grouped_metric_means(rows, column)
    x_positions = list(range(len(labels)))

    fig, ax = plt.subplots(figsize=(9.2, 4.8), constrained_layout=True)
    bars = ax.bar(x_positions, values, color=color, edgecolor="#2f2f2f", linewidth=0.5)

    for bar, value in zip(bars, values):
        if math.isnan(value):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                0.5,
                "n/a",
                ha="center",
                va="bottom",
                rotation=90,
                color="#6a6a6a",
            )

    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, axis="y", linestyle=":", linewidth=0.6, alpha=0.8)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_safe_state_distribution(rows: Sequence[Dict[str, str]], output_path: Path) -> None:
    fault_types = ordered_fault_types(rows)
    labels = [FAULT_TYPE_DISPLAY.get(fault_type, fault_type) for fault_type in fault_types]
    x_positions = list(range(len(fault_types)))

    counts_by_state = {
        state: [0 for _ in fault_types]
        for state in SAFE_STATES
    }

    for index, fault_type in enumerate(fault_types):
        relevant_rows = [row for row in rows if row["fault_type"] == fault_type]
        counts = Counter(row["final_safe_state"] for row in relevant_rows)
        for state in SAFE_STATES:
            counts_by_state[state][index] = counts.get(state, 0)

    fig, ax = plt.subplots(figsize=(9.6, 5.2), constrained_layout=True)
    bottom = [0 for _ in fault_types]
    colors = {
        "normal": "#7fbf7b",
        "precautionary_cooling": "#f2c14e",
        "limp_home": "#e07a5f",
        "controlled_shutdown": "#7b2d26",
    }

    for state in SAFE_STATES:
        ax.bar(
            x_positions,
            counts_by_state[state],
            bottom=bottom,
            color=colors[state],
            label=SAFE_STATE_DISPLAY[state],
            edgecolor="#2f2f2f",
            linewidth=0.5,
        )
        bottom = [current + added for current, added in zip(bottom, counts_by_state[state])]

    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Run Count")
    ax.set_title("Figure Batch 4. Final Safe-State Distribution by Fault Type")
    ax.grid(True, axis="y", linestyle=":", linewidth=0.6, alpha=0.8)
    ax.legend(loc="upper right", frameon=False)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    aggregate_csv = Path(args.aggregate_csv)
    analysis_dir = Path(args.analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

    rows = read_csv_rows(aggregate_csv)
    if not rows:
        raise ValueError(f"No rows found in {aggregate_csv}")

    batch_1_rows = table_batch_1(rows)
    batch_2_rows = table_batch_2(rows)

    write_csv(analysis_dir / "table_batch_1_fault_class_summary.csv", TABLE_BATCH_1_COLUMNS, batch_1_rows)
    write_csv(analysis_dir / "table_batch_2_fault_type_summary.csv", TABLE_BATCH_2_COLUMNS, batch_2_rows)

    plot_mean_bar(
        rows,
        "detection_latency_ms",
        "Mean Detection Latency [ms]",
        "Figure Batch 1. Detection Latency by Fault Type",
        analysis_dir / "figure_batch_1_detection_latency_by_fault_type.png",
        color="#4c78a8",
    )
    plot_mean_bar(
        rows,
        "max_coolant_temperature_c",
        "Mean Max Coolant Temperature [C]",
        "Figure Batch 2. Max Coolant Temperature by Fault Type",
        analysis_dir / "figure_batch_2_max_coolant_temperature_by_fault_type.png",
        color="#e07a5f",
    )
    plot_mean_bar(
        rows,
        "safe_mode_duration_ms",
        "Mean Safe-Mode Duration [ms]",
        "Figure Batch 3. Safe-Mode Duration by Fault Type",
        analysis_dir / "figure_batch_3_safe_mode_duration_by_fault_type.png",
        color="#76b7b2",
    )
    plot_safe_state_distribution(
        rows,
        analysis_dir / "figure_batch_4_final_safe_state_distribution.png",
    )

    print(f"Wrote batch analysis outputs to {analysis_dir}")
    print(f"  - {analysis_dir / 'table_batch_1_fault_class_summary.csv'}")
    print(f"  - {analysis_dir / 'table_batch_2_fault_type_summary.csv'}")
    print(f"  - {analysis_dir / 'figure_batch_1_detection_latency_by_fault_type.png'}")
    print(f"  - {analysis_dir / 'figure_batch_2_max_coolant_temperature_by_fault_type.png'}")
    print(f"  - {analysis_dir / 'figure_batch_3_safe_mode_duration_by_fault_type.png'}")
    print(f"  - {analysis_dir / 'figure_batch_4_final_safe_state_distribution.png'}")


if __name__ == "__main__":
    main()
