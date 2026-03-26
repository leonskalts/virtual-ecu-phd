#!/usr/bin/env python3
"""Generate claim-focused paper outputs from batch experiment results."""

from __future__ import annotations

import argparse
import csv
import os
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

os.environ.setdefault("MPLCONFIGDIR", "/tmp/virtual_ecu_mpl")

import matplotlib.pyplot as plt


DEFAULT_AGGREGATE_CSV = Path("results/batch/paper_quick/aggregate_summary.csv")
DEFAULT_DRAFT_TABLE = Path("results/batch/paper_quick/analysis/table_batch_2_fault_type_summary.csv")
DEFAULT_OUTPUT_DIR = Path("results/batch/paper_quick/analysis_claims")

FAULT_TYPE_ORDER = [
    "sensor_bias",
    "sensor_interface_intermittent",
    "stale_sensor_data",
    "pump_degraded",
    "fan_stuck_off",
    "calibration_memory_corruption",
]

FAULT_TYPE_LABELS = {
    "sensor_bias": "Sensor Bias",
    "sensor_interface_intermittent": "Sensor Interface\nIntermittent",
    "stale_sensor_data": "Stale Sensor\nData",
    "pump_degraded": "Pump Degraded",
    "fan_stuck_off": "Fan Stuck Off",
    "calibration_memory_corruption": "Calibration Memory\nCorruption",
}

FAULT_TYPE_COLORS = {
    "sensor_bias": "#4c9f70",
    "sensor_interface_intermittent": "#87b37a",
    "stale_sensor_data": "#7a6fd0",
    "pump_degraded": "#e6a141",
    "fan_stuck_off": "#c94f4f",
    "calibration_memory_corruption": "#4c78a8",
}

SAFE_STATE_ORDER = ["normal", "precautionary_cooling", "limp_home", "controlled_shutdown"]
SAFE_STATE_LABELS = {
    "normal": "Normal",
    "precautionary_cooling": "Precautionary Cooling",
    "limp_home": "Limp Home",
    "controlled_shutdown": "Controlled Shutdown",
}
SAFE_STATE_COLORS = {
    "normal": "#7fbf7b",
    "precautionary_cooling": "#f2c14e",
    "limp_home": "#e07a5f",
    "controlled_shutdown": "#7b2d26",
}

TABLE_COLUMNS = [
    "fault_type",
    "mean_detection_latency_ms",
    "mean_safe_state_latency_ms",
    "mean_max_coolant_temperature_c",
    "mean_safe_mode_duration_ms",
    "most_common_final_safe_state",
    "most_common_final_dtc",
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
        description="Generate claim-focused publication outputs from a batch aggregate summary CSV."
    )
    parser.add_argument(
        "--aggregate-csv",
        default=str(DEFAULT_AGGREGATE_CSV),
        help="Path to the batch aggregate summary CSV.",
    )
    parser.add_argument(
        "--draft-fault-table",
        default=str(DEFAULT_DRAFT_TABLE),
        help="Path to the first-pass fault-type summary table used for consistency checks.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where claim-focused tables and figures will be written.",
    )
    return parser.parse_args()


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, columns: Sequence[str], rows: Sequence[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        writer.writerows(rows)


def int_or_none(value: str) -> int | None:
    parsed = int(float(value))
    return None if parsed < 0 else parsed


def float_or_none(value: str) -> float | None:
    return None if value == "" else float(value)


def mean_or_none(values: Sequence[float | int]) -> float | None:
    return None if not values else sum(values) / len(values)


def format_float(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{decimals}f}"


def mode_or_none(values: Iterable[str]) -> str:
    filtered = [value for value in values if value]
    if not filtered:
        return "n/a"

    counts = Counter(filtered)
    top = max(counts.values())
    winners = sorted(value for value, count in counts.items() if count == top)
    return winners[0]


def present_fault_types(aggregate_rows: Sequence[Dict[str, str]]) -> List[str]:
    aggregate_types = {row["fault_type"] for row in aggregate_rows}
    ordered = [fault_type for fault_type in FAULT_TYPE_ORDER if fault_type in aggregate_types]
    if not ordered:
        raise ValueError("No claim-focused fault types were found in the aggregate CSV.")
    return ordered


def rows_for_fault_type(rows: Sequence[Dict[str, str]], fault_type: str) -> List[Dict[str, str]]:
    return [row for row in rows if row["fault_type"] == fault_type]


def build_main_comparison_table(rows: Sequence[Dict[str, str]], fault_types: Sequence[str]) -> List[Dict[str, str]]:
    table_rows: List[Dict[str, str]] = []

    for fault_type in fault_types:
        subset = rows_for_fault_type(rows, fault_type)
        detection = [value for value in (int_or_none(row["detection_latency_ms"]) for row in subset) if value is not None]
        safe_state = [value for value in (int_or_none(row["safe_state_latency_ms"]) for row in subset) if value is not None]
        max_temp = [value for value in (float_or_none(row["max_coolant_temperature_c"]) for row in subset) if value is not None]
        safe_duration = [value for value in (int_or_none(row["safe_mode_duration_ms"]) for row in subset) if value is not None]

        table_rows.append(
            {
                "fault_type": fault_type,
                "mean_detection_latency_ms": format_float(mean_or_none(detection), 1),
                "mean_safe_state_latency_ms": format_float(mean_or_none(safe_state), 1),
                "mean_max_coolant_temperature_c": format_float(mean_or_none(max_temp), 2),
                "mean_safe_mode_duration_ms": format_float(mean_or_none(safe_duration), 1),
                "most_common_final_safe_state": mode_or_none(row["final_safe_state"] for row in subset),
                "most_common_final_dtc": mode_or_none(row["final_dtc"] for row in subset),
            }
        )

    return table_rows


def plot_detection_figure(rows: Sequence[Dict[str, str]], fault_types: Sequence[str], output_path: Path) -> None:
    labels = [FAULT_TYPE_LABELS[fault_type] for fault_type in fault_types]
    y_positions = list(range(len(fault_types)))
    detection_means: List[float] = []
    safe_state_means: List[float | None] = []

    for fault_type in fault_types:
        subset = rows_for_fault_type(rows, fault_type)
        detection_values = [
            value for value in (int_or_none(row["detection_latency_ms"]) for row in subset) if value is not None
        ]
        safe_state_values = [
            value for value in (int_or_none(row["safe_state_latency_ms"]) for row in subset) if value is not None
        ]
        detection_means.append(float(mean_or_none(detection_values) or 0.0))
        safe_state_means.append(mean_or_none(safe_state_values))

    fig, ax = plt.subplots(figsize=(8.8, 4.8), constrained_layout=True)

    bar_colors = [FAULT_TYPE_COLORS[fault_type] for fault_type in fault_types]
    bars = ax.barh(y_positions, detection_means, color=bar_colors, edgecolor="#2f2f2f", linewidth=0.6)

    for y_pos, safe_mean in zip(y_positions, safe_state_means):
        if safe_mean is not None:
            ax.plot(safe_mean, y_pos, marker="D", markersize=6, color="#111111")
        else:
            ax.text(250, y_pos, "no safe-state entry", va="center", ha="left", color="#666666", fontsize=8)

    for bar, value in zip(bars, detection_means):
        ax.text(value + 250, bar.get_y() + bar.get_height() / 2.0, f"{value:.0f}", va="center", ha="left")

    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Mean Latency [ms]")
    ax.set_title("Claim Figure 1. Detection and Safe-State Latency by Fault Type")
    ax.grid(True, axis="x", linestyle=":", linewidth=0.6, alpha=0.8)
    ax.legend(
        handles=[
            plt.Line2D([0], [0], color="#666666", linewidth=8, label="Mean detection latency"),
            plt.Line2D([0], [0], marker="D", color="#111111", linestyle="None", label="Mean safe-state latency"),
        ],
        loc="lower right",
        frameon=False,
    )
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_thermal_severity_figure(rows: Sequence[Dict[str, str]], fault_types: Sequence[str], output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 5.0), constrained_layout=True)

    for fault_type in fault_types:
        subset = rows_for_fault_type(rows, fault_type)
        max_temp_values = [
            value for value in (float_or_none(row["max_coolant_temperature_c"]) for row in subset) if value is not None
        ]
        safe_duration_values = [
            value for value in (int_or_none(row["safe_mode_duration_ms"]) for row in subset) if value is not None
        ]
        x_value = mean_or_none(max_temp_values) or 0.0
        y_value = mean_or_none(safe_duration_values) or 0.0

        ax.scatter(
            x_value,
            y_value,
            s=90,
            color=FAULT_TYPE_COLORS[fault_type],
            edgecolor="#222222",
            linewidth=0.7,
        )
        ax.annotate(
            FAULT_TYPE_LABELS[fault_type].replace("\n", " "),
            (x_value, y_value),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=9,
        )

    ax.set_xlabel("Mean Max Coolant Temperature [C]")
    ax.set_ylabel("Mean Safe-Mode Duration [ms]")
    ax.set_title("Claim Figure 2. Thermal Severity by Fault Type")
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.8)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_safe_state_distribution(rows: Sequence[Dict[str, str]], fault_types: Sequence[str], output_path: Path) -> None:
    labels = [FAULT_TYPE_LABELS[fault_type] for fault_type in fault_types]
    x_positions = list(range(len(fault_types)))
    percentages_by_state = {state: [] for state in SAFE_STATE_ORDER}

    for fault_type in fault_types:
        subset = rows_for_fault_type(rows, fault_type)
        counts = Counter(row["final_safe_state"] for row in subset)
        total = len(subset)
        for state in SAFE_STATE_ORDER:
            percentages_by_state[state].append(100.0 * counts.get(state, 0) / total if total > 0 else 0.0)

    fig, ax = plt.subplots(figsize=(8.8, 4.8), constrained_layout=True)
    bottom = [0.0 for _ in fault_types]

    for state in SAFE_STATE_ORDER:
        values = percentages_by_state[state]
        ax.bar(
            x_positions,
            values,
            bottom=bottom,
            color=SAFE_STATE_COLORS[state],
            edgecolor="#2f2f2f",
            linewidth=0.5,
            label=SAFE_STATE_LABELS[state],
        )
        bottom = [current + added for current, added in zip(bottom, values)]

    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels)
    ax.set_ylim(0.0, 100.0)
    ax.set_ylabel("Outcome Share [%]")
    ax.set_title("Claim Figure 3. Final Safe-State Outcome by Fault Type")
    ax.grid(True, axis="y", linestyle=":", linewidth=0.6, alpha=0.8)
    ax.legend(loc="upper right", frameon=False)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    aggregate_csv = Path(args.aggregate_csv)
    draft_fault_table = Path(args.draft_fault_table)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

    aggregate_rows = read_csv_rows(aggregate_csv)
    draft_rows = read_csv_rows(draft_fault_table)
    if not draft_rows:
        raise ValueError(f"No rows found in {draft_fault_table}")
    fault_types = present_fault_types(aggregate_rows)

    table_rows = build_main_comparison_table(aggregate_rows, fault_types)
    write_csv(output_dir / "table_claim_1_main_comparison.csv", TABLE_COLUMNS, table_rows)

    plot_detection_figure(
        aggregate_rows,
        fault_types,
        output_dir / "figure_claim_1_detection_vs_fault_type.png",
    )
    plot_thermal_severity_figure(
        aggregate_rows,
        fault_types,
        output_dir / "figure_claim_2_thermal_severity_vs_fault_type.png",
    )
    plot_safe_state_distribution(
        aggregate_rows,
        fault_types,
        output_dir / "figure_claim_3_safe_state_outcome_vs_fault_type.png",
    )

    print(f"Wrote claim-focused outputs to {output_dir}")
    print(f"  - {output_dir / 'table_claim_1_main_comparison.csv'}")
    print(f"  - {output_dir / 'figure_claim_1_detection_vs_fault_type.png'}")
    print(f"  - {output_dir / 'figure_claim_2_thermal_severity_vs_fault_type.png'}")
    print(f"  - {output_dir / 'figure_claim_3_safe_state_outcome_vs_fault_type.png'}")


if __name__ == "__main__":
    main()
