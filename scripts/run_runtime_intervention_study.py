#!/usr/bin/env python3
"""Run the reproducible virtual ECU runtime detector intervention study."""

from __future__ import annotations

import argparse
import csv
import html
import math
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "runtime_intervention_study_v1"
DEFAULT_EXECUTABLE = PROJECT_ROOT / "virtual_ecu"

DETECTORS = (
    "builtin_ecu",
    "threshold",
    "ewma",
    "cusum",
    "thermal_observer",
    "kalman_filter",
    "adaptive_kalman_filter",
)
ACTIONS = ("observe_only", "precautionary_cooling", "limp_home")

DETECTOR_COLORS = {
    "builtin_ecu": "#6b7280",
    "threshold": "#3b82f6",
    "ewma": "#f59e0b",
    "cusum": "#10b981",
    "thermal_observer": "#a855f7",
    "kalman_filter": "#dc2626",
    "adaptive_kalman_filter": "#0284c7",
}
ACTION_COLORS = {
    "observe_only": "#64748b",
    "precautionary_cooling": "#0ea5e9",
    "limp_home": "#8b5cf6",
}
SAFE_STATE_COLORS = {
    "normal": "#94a3b8",
    "precautionary_cooling": "#38bdf8",
    "limp_home": "#f59e0b",
    "controlled_shutdown": "#dc2626",
}


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    scenario_name: str
    fault_type: str
    start_ms: int
    duration_ms: int
    behavior: str
    parameter: float


SCENARIOS = (
    Scenario(
        "fan_stuck_off",
        "Fan stuck off",
        "fan_stuck_off",
        75000,
        0,
        "permanent",
        0.0,
    ),
    Scenario(
        "pump_degraded",
        "Pump degraded",
        "pump_degraded",
        60000,
        25000,
        "transient",
        0.45,
    ),
    Scenario(
        "sensor_bias",
        "Coolant sensor bias",
        "sensor_bias",
        30000,
        15000,
        "transient",
        6.0,
    ),
    Scenario(
        "stale_sensor_data",
        "Stale sensor data",
        "stale_sensor_data",
        65000,
        0,
        "permanent",
        15000.0,
    ),
    Scenario(
        "calibration_memory_corruption",
        "Calibration memory corruption",
        "calibration_memory_corruption",
        52000,
        0,
        "permanent",
        16.0,
    ),
)

OUTPUT_COLUMNS = (
    "scenario_id",
    "scenario_name",
    "fault_type",
    "fault_start_ms",
    "detector",
    "detector_action",
    "runtime_detection_detected",
    "runtime_detection_first_detection_ms",
    "runtime_detection_latency_ms",
    "runtime_detection_action_requested",
    "runtime_detection_requested_safe_state",
    "runtime_detection_action_time_ms",
    "runtime_detection_false_positive_count",
    "runtime_detection_label",
    "first_ecu_dtc_label",
    "first_ecu_dtc_time_ms",
    "first_ecu_dtc_latency_ms",
    "final_safe_state",
    "max_coolant_temp_c",
    "safe_state_latency_ms",
    "detection_latency_ms",
    "shutdown_requested",
    "raw_csv",
    "summary_csv",
)

FIGURE_SPECS = (
    (
        "detection_latency_by_detector_scenario.png",
        "Detection latency by detector and scenario",
    ),
    (
        "max_coolant_by_detector_action_scenario.png",
        "Maximum coolant temperature by detector, action, and scenario",
    ),
    (
        "final_safe_state_distribution_by_action.png",
        "Final safe-state distribution by detector action",
    ),
    (
        "action_time_by_detector_action.png",
        "Mean action time by detector and action",
    ),
    (
        "missed_detections_by_detector.png",
        "Missed detections by detector",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run runtime detector/action combinations in the virtual ECU "
            "research simulator and generate comparison artifacts."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for raw traces, tables, figures, and reports.",
    )
    parser.add_argument(
        "--executable",
        type=Path,
        default=DEFAULT_EXECUTABLE,
        help="Path to the compiled virtual_ecu executable.",
    )
    parser.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip Matplotlib figures while still writing CSV and reports.",
    )
    return parser.parse_args()


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"CSV has no data rows: {path}")
    return rows


def parse_int(value: object, default: int = -1) -> int:
    text = str(value).strip()
    if text == "":
        return default
    return int(float(text))


def parse_float(value: object, default: float = math.nan) -> float:
    text = str(value).strip()
    if text == "":
        return default
    return float(text)


def first_ecu_dtc(
    raw_rows: Sequence[Dict[str, str]], fault_start_ms: int
) -> tuple[str, int, int]:
    for row in raw_rows:
        time_ms = parse_int(row.get("time_ms", ""))
        if time_ms < fault_start_ms:
            continue
        label = row.get("primary_dtc_label", "none")
        dtc_id = parse_int(row.get("primary_dtc_id", "0"), 0)
        if label not in {"", "none"} or dtc_id != 0:
            return label or str(dtc_id), time_ms, time_ms - fault_start_ms
    return "none", -1, -1


def first_runtime_row(
    raw_rows: Sequence[Dict[str, str]], column: str
) -> Dict[str, str] | None:
    return next((row for row in raw_rows if parse_int(row.get(column, "0"), 0) != 0), None)


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def summary_path_for(raw_path: Path) -> Path:
    return raw_path.with_name(f"{raw_path.stem}_summary.csv")


def run_simulation(
    executable: Path,
    raw_dir: Path,
    scenario: Scenario,
    detector: str,
    action: str,
) -> Dict[str, object]:
    stem = f"{scenario.scenario_id}__{detector}__{action}"
    raw_path = raw_dir / f"{stem}.csv"
    summary_path = summary_path_for(raw_path)
    command = [
        str(executable),
        str(raw_path),
        "custom",
        scenario.fault_type,
        str(scenario.start_ms),
        str(scenario.duration_ms),
        scenario.behavior,
        f"{scenario.parameter:g}",
        "--detector",
        detector,
        "--detector-action",
        action,
    ]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"Simulator failed for {scenario.scenario_id}/{detector}/{action}: {message}"
        )
    if not raw_path.is_file() or not summary_path.is_file():
        raise RuntimeError(f"Simulator did not produce the expected files for {stem}")

    raw_rows = read_csv_rows(raw_path)
    summary = read_csv_rows(summary_path)[0]
    final_raw = raw_rows[-1]
    detection_row = first_runtime_row(raw_rows, "runtime_detection_detected")
    action_row = first_runtime_row(raw_rows, "runtime_detection_action_requested")
    dtc_label, dtc_time_ms, dtc_latency_ms = first_ecu_dtc(
        raw_rows, scenario.start_ms
    )

    return {
        "scenario_id": scenario.scenario_id,
        "scenario_name": scenario.scenario_name,
        "fault_type": scenario.fault_type,
        "fault_start_ms": scenario.start_ms,
        "detector": detector,
        "detector_action": action,
        "runtime_detection_detected": parse_int(
            summary.get("runtime_detection_detected", "0"), 0
        ),
        "runtime_detection_first_detection_ms": parse_int(
            summary.get("runtime_detection_first_detection_ms", "-1")
        ),
        "runtime_detection_latency_ms": parse_int(
            summary.get("runtime_detection_latency_ms", "-1")
        ),
        "runtime_detection_action_requested": parse_int(
            summary.get("runtime_detection_action_requested", "0"), 0
        ),
        "runtime_detection_requested_safe_state": (
            action_row.get("runtime_detection_requested_safe_state", "none")
            if action_row is not None
            else "none"
        ),
        "runtime_detection_action_time_ms": parse_int(
            summary.get("runtime_detection_action_time_ms", "-1")
        ),
        "runtime_detection_false_positive_count": parse_int(
            final_raw.get("runtime_detection_false_positive_count", "0"), 0
        ),
        "runtime_detection_label": (
            detection_row.get("runtime_detection_label", "none")
            if detection_row is not None
            else "none"
        ),
        "first_ecu_dtc_label": dtc_label,
        "first_ecu_dtc_time_ms": dtc_time_ms,
        "first_ecu_dtc_latency_ms": dtc_latency_ms,
        "final_safe_state": summary.get("final_safe_state_label", "unknown"),
        "max_coolant_temp_c": parse_float(summary.get("max_coolant_temp_c", "")),
        "safe_state_latency_ms": parse_int(
            summary.get("safe_state_latency_ms", "-1")
        ),
        "detection_latency_ms": parse_int(
            summary.get("detection_latency_ms", "-1")
        ),
        "shutdown_requested": max(
            parse_int(row.get("shutdown_requested", "0"), 0) for row in raw_rows
        ),
        "raw_csv": relative_path(raw_path),
        "summary_csv": relative_path(summary_path),
    }


def run_study(executable: Path, output_dir: Path) -> List[Dict[str, object]]:
    if not executable.is_file():
        raise FileNotFoundError(
            f"Simulator executable not found: {executable}. Run 'make' first."
        )

    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    total = len(SCENARIOS) * len(DETECTORS) * len(ACTIONS)
    results: List[Dict[str, object]] = []
    run_index = 0

    for scenario in SCENARIOS:
        for detector in DETECTORS:
            for action in ACTIONS:
                run_index += 1
                print(
                    f"[{run_index:02d}/{total}] "
                    f"{scenario.scenario_id} / {detector} / {action}"
                )
                results.append(
                    run_simulation(
                        executable,
                        raw_dir,
                        scenario,
                        detector,
                        action,
                    )
                )
    return results


def write_comparison_csv(
    path: Path, results: Sequence[Dict[str, object]]
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=OUTPUT_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(results)


def observe_rows(results: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    return [
        row for row in results if row["detector_action"] == "observe_only"
    ]


def detected_latencies(
    rows: Iterable[Dict[str, object]],
) -> List[float]:
    return [
        float(row["runtime_detection_latency_ms"])
        for row in rows
        if int(row["runtime_detection_detected"]) != 0
        and int(row["runtime_detection_latency_ms"]) >= 0
    ]


def detector_summary(
    results: Sequence[Dict[str, object]],
) -> List[Dict[str, object]]:
    rows = observe_rows(results)
    summary = []
    for detector in DETECTORS:
        subset = [row for row in rows if row["detector"] == detector]
        latencies = detected_latencies(subset)
        detected = sum(int(row["runtime_detection_detected"]) for row in subset)
        summary.append(
            {
                "detector": detector,
                "detected": detected,
                "total": len(subset),
                "missed": len(subset) - detected,
                "mean_latency_ms": mean(latencies) if latencies else math.nan,
                "false_positives": sum(
                    int(row["runtime_detection_false_positive_count"])
                    for row in subset
                ),
            }
        )
    return summary


def action_summary(
    results: Sequence[Dict[str, object]],
) -> List[Dict[str, object]]:
    summary = []
    for action in ACTIONS:
        subset = [row for row in results if row["detector_action"] == action]
        temperatures = [float(row["max_coolant_temp_c"]) for row in subset]
        safe_latencies = [
            float(row["safe_state_latency_ms"])
            for row in subset
            if int(row["safe_state_latency_ms"]) >= 0
        ]
        summary.append(
            {
                "action": action,
                "runs": len(subset),
                "mean_max_coolant_temp_c": mean(temperatures),
                "mean_safe_state_latency_ms": (
                    mean(safe_latencies) if safe_latencies else math.nan
                ),
                "actions_requested": sum(
                    int(row["runtime_detection_action_requested"])
                    for row in subset
                ),
                "shutdown_runs": sum(
                    int(row["shutdown_requested"]) for row in subset
                ),
            }
        )
    return summary


def key_findings(results: Sequence[Dict[str, object]]) -> List[str]:
    detectors = detector_summary(results)
    actions = action_summary(results)
    finite_detectors = [
        row for row in detectors if not math.isnan(float(row["mean_latency_ms"]))
    ]
    fastest = min(finite_detectors, key=lambda row: float(row["mean_latency_ms"]))
    observe = next(row for row in actions if row["action"] == "observe_only")
    coolest_temperature = min(
        float(row["mean_max_coolant_temp_c"]) for row in actions
    )
    coolest_actions = [
        str(row["action"])
        for row in actions
        if math.isclose(
            float(row["mean_max_coolant_temp_c"]),
            coolest_temperature,
            abs_tol=0.005,
        )
    ]
    coolest_label = " and ".join(coolest_actions)
    misses = ", ".join(
        f"{row['detector']}: {row['missed']}" for row in detectors
    )
    coolant_delta = (
        coolest_temperature
        - float(observe["mean_max_coolant_temp_c"])
    )
    shutdown_total = sum(int(row["shutdown_requested"]) for row in results)

    return [
        (
            f"{fastest['detector']} had the lowest mean runtime detection latency "
            f"among detected observe-only scenarios "
            f"({float(fastest['mean_latency_ms']):.1f} ms; "
            f"{fastest['detected']}/{fastest['total']} scenarios detected)."
        ),
        (
            f"{coolest_label} produced the lowest descriptive mean maximum "
            f"coolant temperature ({coolest_temperature:.2f} C), "
            f"a {coolant_delta:+.2f} C difference from observe_only."
        ),
        f"Missed detections across the five observe-only scenario traces were {misses}.",
        (
            f"Controlled shutdown was requested in {shutdown_total} of "
            f"{len(results)} runs."
        ),
        (
            "Observe-only runs retain the simulator's built-in diagnostic and "
            "safe-state behavior; intervention comparisons add only the selected "
            "detector request."
        ),
    ]


def plot_figures(
    output_dir: Path, results: Sequence[Dict[str, object]]
) -> List[Path]:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/virtual_ecu_mpl")
    os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    scenario_labels = [scenario.scenario_name for scenario in SCENARIOS]
    scenario_ids = [scenario.scenario_id for scenario in SCENARIOS]

    observed = observe_rows(results)
    by_key = {
        (
            str(row["scenario_id"]),
            str(row["detector"]),
            str(row["detector_action"]),
        ): row
        for row in results
    }

    fig, ax = plt.subplots(figsize=(11.5, 5.5), constrained_layout=True)
    width = 0.16
    offsets = [
        (index - ((len(DETECTORS) - 1) / 2.0)) * width
        for index in range(len(DETECTORS))
    ]
    for detector, offset in zip(DETECTORS, offsets):
        positions = []
        values = []
        for index, scenario_id in enumerate(scenario_ids):
            row = by_key[(scenario_id, detector, "observe_only")]
            if int(row["runtime_detection_detected"]) != 0:
                positions.append(index + offset)
                values.append(float(row["runtime_detection_latency_ms"]) / 1000.0)
        ax.bar(
            positions,
            values,
            width=width,
            color=DETECTOR_COLORS[detector],
            label=detector,
        )
    ax.set_xticks(range(len(scenario_labels)), scenario_labels, rotation=18, ha="right")
    ax.set_ylabel("Runtime detection latency [s]")
    ax.set_title("Detection Latency by Detector and Scenario (Observe Only)")
    ax.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.7)
    ax.legend(frameon=False, ncol=5)
    path = figures_dir / FIGURE_SPECS[0][0]
    fig.savefig(path, dpi=190)
    plt.close(fig)
    paths.append(path)

    fig, axes = plt.subplots(3, 2, figsize=(12.0, 12.0), constrained_layout=True)
    width = 0.24
    action_offsets = [-width, 0.0, width]
    for axis, scenario in zip(axes.flat, SCENARIOS):
        for action, offset in zip(ACTIONS, action_offsets):
            values = [
                float(by_key[(scenario.scenario_id, detector, action)]["max_coolant_temp_c"])
                for detector in DETECTORS
            ]
            axis.bar(
                [index + offset for index in range(len(DETECTORS))],
                values,
                width=width,
                color=ACTION_COLORS[action],
                label=action,
            )
        axis.set_title(scenario.scenario_name)
        axis.set_xticks(range(len(DETECTORS)), DETECTORS, rotation=18, ha="right")
        axis.set_ylabel("Maximum coolant [C]")
        axis.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.7)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    axes.flat[-1].axis("off")
    axes.flat[-1].legend(
        handles,
        labels,
        loc="center",
        frameon=False,
        title="Detector action",
    )
    fig.suptitle("Maximum Coolant Temperature by Detector Action and Scenario")
    path = figures_dir / FIGURE_SPECS[1][0]
    fig.savefig(path, dpi=190)
    plt.close(fig)
    paths.append(path)

    states = (
        "normal",
        "precautionary_cooling",
        "limp_home",
        "controlled_shutdown",
    )
    fig, ax = plt.subplots(figsize=(8.8, 5.2), constrained_layout=True)
    bottoms = [0] * len(ACTIONS)
    for state in states:
        counts = [
            sum(
                1
                for row in results
                if row["detector_action"] == action
                and row["final_safe_state"] == state
            )
            for action in ACTIONS
        ]
        ax.bar(
            ACTIONS,
            counts,
            bottom=bottoms,
            color=SAFE_STATE_COLORS[state],
            label=state,
        )
        bottoms = [bottom + count for bottom, count in zip(bottoms, counts)]
    ax.set_ylabel("Runs")
    ax.set_title("Final Safe-State Distribution by Detector Action")
    ax.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.7)
    ax.legend(frameon=False)
    path = figures_dir / FIGURE_SPECS[2][0]
    fig.savefig(path, dpi=190)
    plt.close(fig)
    paths.append(path)

    active_actions = ("precautionary_cooling", "limp_home")
    fig, ax = plt.subplots(figsize=(8.8, 5.2), constrained_layout=True)
    width = 0.34
    for action, offset in zip(active_actions, (-width / 2.0, width / 2.0)):
        values = []
        for detector in DETECTORS:
            times = [
                float(row["runtime_detection_action_time_ms"]) / 1000.0
                for row in results
                if row["detector"] == detector
                and row["detector_action"] == action
                and int(row["runtime_detection_action_requested"]) != 0
            ]
            values.append(mean(times) if times else 0.0)
        ax.bar(
            [index + offset for index in range(len(DETECTORS))],
            values,
            width=width,
            color=ACTION_COLORS[action],
            label=action,
        )
    ax.set_xticks(range(len(DETECTORS)), DETECTORS, rotation=15, ha="right")
    ax.set_ylabel("Mean absolute action time [s]")
    ax.set_title("Action Time by Detector and Action")
    ax.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.7)
    ax.legend(frameon=False)
    path = figures_dir / FIGURE_SPECS[3][0]
    fig.savefig(path, dpi=190)
    plt.close(fig)
    paths.append(path)

    misses = [
        sum(
            1
            for row in observed
            if row["detector"] == detector
            and int(row["runtime_detection_detected"]) == 0
        )
        for detector in DETECTORS
    ]
    fig, ax = plt.subplots(figsize=(7.8, 4.8), constrained_layout=True)
    bars = ax.bar(
        DETECTORS,
        misses,
        color=[DETECTOR_COLORS[detector] for detector in DETECTORS],
        width=0.62,
    )
    ax.set_ylim(0, len(SCENARIOS) + 0.7)
    ax.set_ylabel("Missed scenarios")
    ax.set_title("Missed Detections by Detector (Observe Only)")
    ax.tick_params(axis="x", labelrotation=15)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    ax.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.7)
    for bar, value in zip(bars, misses):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            value + 0.12,
            str(value),
            ha="center",
            va="bottom",
        )
    path = figures_dir / FIGURE_SPECS[4][0]
    fig.savefig(path, dpi=190)
    plt.close(fig)
    paths.append(path)
    return paths


def format_number(value: object, decimals: int = 1) -> str:
    number = float(value)
    if math.isnan(number):
        return "n/a"
    return f"{number:.{decimals}f}"


def write_markdown_summary(
    path: Path, results: Sequence[Dict[str, object]]
) -> None:
    detectors = detector_summary(results)
    actions = action_summary(results)
    findings = key_findings(results)
    lines = [
        "# Runtime Detector Intervention Study v1",
        "",
        "This study uses the virtual ECU research simulator. Runtime detectors run "
        "inside the C simulation loop, while detector actions are optional research "
        "interventions. Observe-only preserves the built-in ECU behavior.",
        "",
        f"- Scenarios: {len(SCENARIOS)}",
        f"- Detectors: {len(DETECTORS)}",
        f"- Detector actions: {len(ACTIONS)}",
        f"- Total simulator runs: {len(results)}",
        "",
        "## Detector Summary",
        "",
        "| Detector | Detected scenarios | Missed | Mean latency [ms] | False positives |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in detectors:
        lines.append(
            f"| {row['detector']} | {row['detected']}/{row['total']} | "
            f"{row['missed']} | {format_number(row['mean_latency_ms'])} | "
            f"{row['false_positives']} |"
        )
    lines.extend(
        [
            "",
            "## Action Summary",
            "",
            "| Action | Runs | Actions requested | Mean max coolant [C] | Mean safe-state latency [ms] | Shutdown runs |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in actions:
        lines.append(
            f"| {row['action']} | {row['runs']} | {row['actions_requested']} | "
            f"{format_number(row['mean_max_coolant_temp_c'], 2)} | "
            f"{format_number(row['mean_safe_state_latency_ms'])} | "
            f"{row['shutdown_runs']} |"
        )
    lines.extend(["", "## Key Findings", ""])
    lines.extend(f"- {finding}" for finding in findings)
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            "- `raw/`: one raw CSV and one summary CSV per simulator run.",
            "- `runtime_intervention_comparison.csv`: one aggregate row per run.",
            "- `figures/`: five Matplotlib comparison figures.",
            "- `runtime_intervention_report.html`: compact browser report.",
            "",
            "## Limitations",
            "",
            "- Results are deterministic simulation outcomes for the configured scenarios and detector calibrations.",
            "- The study is not production ECU validation and does not represent real-vehicle validation.",
            "- Mean thermal outcomes are descriptive; they do not establish statistical significance.",
            "- The direct residual set has limited observability for calibration-memory corruption.",
            "",
            "## Reproduction",
            "",
            "```bash",
            "make",
            "python3 scripts/run_runtime_intervention_study.py",
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def html_table(results: Sequence[Dict[str, object]]) -> str:
    columns = (
        ("scenario_name", "Scenario"),
        ("detector", "Detector"),
        ("detector_action", "Action"),
        ("runtime_detection_detected", "Detected"),
        ("runtime_detection_latency_ms", "Runtime latency [ms]"),
        ("runtime_detection_requested_safe_state", "Action request"),
        ("runtime_detection_action_time_ms", "Action time [ms]"),
        ("first_ecu_dtc_label", "First ECU DTC"),
        ("first_ecu_dtc_latency_ms", "ECU latency [ms]"),
        ("final_safe_state", "Final state"),
        ("max_coolant_temp_c", "Max coolant [C]"),
        ("shutdown_requested", "Shutdown"),
    )
    header = "".join(f"<th>{html.escape(label)}</th>" for _key, label in columns)
    body_rows = []
    for row in results:
        cells = []
        for key, _label in columns:
            value = row[key]
            if key == "max_coolant_temp_c":
                text = f"{float(value):.2f}"
            elif key in {
                "runtime_detection_latency_ms",
                "runtime_detection_action_time_ms",
                "first_ecu_dtc_latency_ms",
            } and int(value) < 0:
                text = "n/a"
            else:
                text = str(value)
            cells.append(f"<td>{html.escape(text)}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<div class="table-wrap"><table><thead><tr>'
        + header
        + "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table></div>"
    )


def write_html_report(
    path: Path,
    results: Sequence[Dict[str, object]],
    figures: Sequence[Path],
) -> None:
    detectors = detector_summary(results)
    actions = action_summary(results)
    finite_detectors = [
        row for row in detectors if not math.isnan(float(row["mean_latency_ms"]))
    ]
    fastest = min(finite_detectors, key=lambda row: float(row["mean_latency_ms"]))
    coolest_temperature = min(
        float(row["mean_max_coolant_temp_c"]) for row in actions
    )
    coolest_actions = [
        str(row["action"])
        for row in actions
        if math.isclose(
            float(row["mean_max_coolant_temp_c"]),
            coolest_temperature,
            abs_tol=0.005,
        )
    ]
    coolest_label = " / ".join(coolest_actions)
    findings = key_findings(results)
    figure_names = {figure.name for figure in figures}
    figure_html = []
    for filename, caption in FIGURE_SPECS:
        if filename in figure_names:
            figure_html.append(
                "<figure>"
                f'<img src="figures/{html.escape(filename)}" alt="{html.escape(caption)}">'
                f"<figcaption>{html.escape(caption)}</figcaption>"
                "</figure>"
            )
    findings_html = "".join(
        f"<li>{html.escape(finding)}</li>" for finding in findings
    )
    report = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Runtime Detector Intervention Study v1</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172033;
      --muted: #526173;
      --line: #dbe3ec;
      --panel: #ffffff;
      --accent: #2563eb;
      --bg: #f3f6fa;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.5;
    }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 36px 24px 64px; }}
    h1 {{ margin: 0 0 8px; font-size: 32px; }}
    h2 {{ margin-top: 34px; font-size: 22px; }}
    p {{ color: var(--muted); }}
    .hero, .card, figure, .table-wrap {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
    }}
    .hero {{ padding: 26px; border-top: 5px solid var(--accent); }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-top: 18px;
    }}
    .card {{ padding: 17px; }}
    .card .label {{ color: var(--muted); font-size: 13px; }}
    .card .value {{ margin-top: 4px; font-size: 22px; font-weight: 700; }}
    .figures {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 18px; }}
    figure {{ margin: 0; padding: 14px; }}
    figure img {{ display: block; width: 100%; height: auto; }}
    figcaption {{ margin-top: 9px; color: var(--muted); font-size: 14px; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; }}
    th {{ position: sticky; top: 0; background: #eef4ff; }}
    tbody tr:nth-child(even) {{ background: #f8fafc; }}
    code {{ background: #e8eef6; padding: 2px 5px; border-radius: 4px; }}
    .note {{ padding: 16px 18px; background: #fff8e6; border-left: 4px solid #f59e0b; }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <h1>Runtime Detector Intervention Study v1</h1>
    <p>
      This reproducible study uses a virtual ECU research simulator to examine
      whether earlier runtime detection and optional detector-driven safety
      requests change simulated safety and thermal outcomes. Runtime detectors
      execute inside the C simulation loop. Detector actions are optional research interventions;
      <code>observe_only</code> preserves baseline built-in ECU behavior.
    </p>
    <div class="cards">
      <div class="card"><div class="label">Scenarios</div><div class="value">{len(SCENARIOS)}</div></div>
      <div class="card"><div class="label">Detectors</div><div class="value">{len(DETECTORS)}</div></div>
      <div class="card"><div class="label">Action modes</div><div class="value">{len(ACTIONS)}</div></div>
      <div class="card"><div class="label">Fastest average detector</div><div class="value">{html.escape(str(fastest['detector']))}</div><div class="label">{float(fastest['mean_latency_ms']):.1f} ms</div></div>
      <div class="card"><div class="label">Lowest mean max coolant</div><div class="value">{html.escape(coolest_label)}</div><div class="label">{coolest_temperature:.2f} C</div></div>
    </div>
  </section>

  <h2>Study Design</h2>
  <p>
    Five custom single-fault scenarios are crossed with {len(DETECTORS)} runtime detectors
    and three action modes, producing {len(results)} deterministic simulator
    runs. A detector identifies an anomaly; an action optionally requests
    precautionary cooling or limp-home through the existing maximum-severity
    safety arbitration.
  </p>

  <h2>Key Findings</h2>
  <ul>{findings_html}</ul>

  <h2>Figures</h2>
  <div class="figures">{''.join(figure_html) or '<p>Figures were not generated.</p>'}</div>

  <h2>Main Comparison Table</h2>
  {html_table(results)}

  <h2>Limitations</h2>
  <div class="note">
    These are deterministic outcomes from a virtual ECU research simulator.
    The study is not production ECU validation. It is not real-vehicle validation.
    Detector calibrations, simplified plant dynamics, selected faults, and direct
    residual observability limit generalization. Thermal averages are descriptive
    and do not establish statistical significance.
  </div>

  <h2>Reproduction</h2>
  <p>From the repository root:</p>
  <pre><code>make
python3 scripts/run_runtime_intervention_study.py</code></pre>
</main>
</body>
</html>
"""
    path.write_text(report, encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    executable = args.executable.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(parents=True, exist_ok=True)

    results = run_study(executable, output_dir)
    comparison_path = output_dir / "runtime_intervention_comparison.csv"
    summary_path = output_dir / "runtime_intervention_summary.md"
    report_path = output_dir / "runtime_intervention_report.html"
    write_comparison_csv(comparison_path, results)

    figures: List[Path] = []
    if not args.no_figures:
        figures = plot_figures(output_dir, results)
    write_markdown_summary(summary_path, results)
    write_html_report(report_path, results, figures)

    print(f"Wrote {comparison_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")
    for figure in figures:
        print(f"Wrote {figure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
