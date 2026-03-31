#!/usr/bin/env python3
"""Simple Tkinter frontend for the virtual ECU simulator."""

from __future__ import annotations

import csv
import os
import subprocess
import threading
import textwrap
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError as exc:  # pragma: no cover - import failure is environment-specific.
    raise SystemExit(
        "Tkinter is not available in this Python installation. "
        "Install the Tk package for Python and try again."
    ) from exc

os.environ.setdefault("MPLCONFIGDIR", "/tmp/virtual_ecu_mpl")

import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = PROJECT_ROOT / "logs"
EXPORT_ROOT = PROJECT_ROOT / "results" / "gui_comparison_reports"
SNAPSHOT_ROOT = PROJECT_ROOT / "results" / "gui_snapshots"
DEFAULT_BATCH_AGGREGATE_CSV = PROJECT_ROOT / "results" / "batch" / "paper_quick" / "aggregate_summary.csv"

CAMPAIGNS: Sequence[Tuple[str, str]] = (
    ("baseline", "Baseline"),
    ("sensor_bias_only", "Sensor Bias Only"),
    ("sensor_interface_intermittent", "Sensor Interface Intermittent"),
    ("stale_sensor_data_only", "Stale Sensor Data Only"),
    ("stale_sensor_data_hot_stress", "Stale Sensor Data Hot Stress"),
    ("pump_degraded_only", "Pump Degraded Only"),
    ("fan_stuck_only", "Fan Stuck Only"),
    ("fan_stuck_hot_stress", "Fan Stuck Hot Stress"),
    ("calibration_memory_corruption", "Calibration Memory Corruption"),
    ("paper_default", "Paper Default"),
)

MODE_TO_CLASS = {
    "sensor_bias": "sensing-path fault",
    "sensor_interface_intermittent": "sensing-path fault",
    "stale_sensor_data": "timing/communication-path fault",
    "pump_degraded": "actuation-path fault",
    "fan_stuck_off": "actuation-path fault",
    "calibration_memory_corruption": "computation/memory-path fault",
}

FAULT_TYPE_DISPLAY = {
    "none": "Baseline",
    "sensor_bias": "Sensor Bias",
    "sensor_interface_intermittent": "Sensor Interface Intermittent",
    "stale_sensor_data": "Stale Sensor Data",
    "pump_degraded": "Pump Degraded",
    "fan_stuck_off": "Fan Stuck Off",
    "calibration_memory_corruption": "Calibration Memory Corruption",
}

FAULT_TYPE_ORDER = (
    "none",
    "sensor_bias",
    "sensor_interface_intermittent",
    "stale_sensor_data",
    "pump_degraded",
    "fan_stuck_off",
    "calibration_memory_corruption",
)

SAFE_STATE_LABELS = {
    0: "normal",
    1: "precautionary_cooling",
    2: "limp_home",
    3: "controlled_shutdown",
}
SAFE_STATE_SEVERITY = {
    "normal": 0,
    "precautionary_cooling": 1,
    "limp_home": 2,
    "controlled_shutdown": 3,
}
DTC_SEVERITY = {
    0: 0,
    1001: 1,
    2001: 3,
    2002: 4,
    3001: 2,
    3002: 2,
    3003: 3,
}

LEFT_COLOR = "#c4473a"
RIGHT_COLOR = "#1f5aa6"
LEFT_DASH = None
RIGHT_DASH = (6, 4)

CAMPAIGN_STORIES = {
    "baseline": {
        "campaign_name": "Baseline",
        "description": "Nominal reference run used as the comparison case for all injected-fault campaigns.",
        "fault_class": "baseline / no injected fault",
        "hardware_source": "No injected hardware-origin fault. Sensor, actuation, and memory paths are nominal.",
        "ecu_manifestation": "Nominal coolant sensing, nominal controller target, and nominal pump/fan realization.",
        "diagnostic_effect": "No expected DTC confirmation. Diagnostics remain quiet unless a model or threshold issue is introduced.",
        "system_effect": "Normal thermal regulation with no safety escalation. Serves as the nominal comparison case.",
    },
    "sensor_bias_only": {
        "campaign_name": "Sensor Bias Only",
        "description": "Single sensing-path bias case for showing measurement corruption without major thermal escalation.",
        "fault_class": "sensing-path fault",
        "hardware_source": "ADC offset, reference drift, or analog front-end bias in the coolant sensing chain.",
        "ecu_manifestation": "Biased coolant measurement at the ECU input even though the plant temperature is unchanged.",
        "diagnostic_effect": "Coolant sensor rationality DTC is expected to appear quickly from the measurement residual.",
        "system_effect": "Control demand may be distorted, but the main system-level effect is diagnostic visibility rather than safe-state escalation.",
    },
    "sensor_interface_intermittent": {
        "campaign_name": "Sensor Interface Intermittent",
        "description": "Bursty sensing-path disturbance case for showing intermittent ECU-visible sensor corruption.",
        "fault_class": "sensing-path fault",
        "hardware_source": "Intermittent sensor-interface corruption such as sampling glitches, connector intermittency, or burst noise.",
        "ecu_manifestation": "Bursty coolant reading disturbances appear at the ECU interface while the true thermal state remains smooth.",
        "diagnostic_effect": "Transient or intermittent coolant sensor rationality behavior is expected, with DTC activity tied to burst timing.",
        "system_effect": "Temporary control disturbance may occur, but safe-state entry is usually limited unless the disturbance couples into thermal stress.",
    },
    "stale_sensor_data_only": {
        "campaign_name": "Stale Sensor Data Only",
        "description": "Moderate timing/communication-path case where the ECU reuses an older coolant sample and cooling demand arrives late.",
        "fault_class": "timing/communication-path fault",
        "hardware_source": "Clock-domain crossing delay, stale register handoff, DMA refresh lag, or sampled-data transport timing fault in the sensor-to-ECU path.",
        "ecu_manifestation": "The coolant measurement visible to the controller updates too slowly, so the ECU acts on aged thermal information.",
        "diagnostic_effect": "Sensor rationality evidence appears after the stale-data lag becomes large enough during the rising-temperature phase.",
        "system_effect": "Cooling demand arrives late, increasing peak coolant temperature and making delayed control action visible even without an extreme stress case.",
    },
    "stale_sensor_data_hot_stress": {
        "campaign_name": "Stale Sensor Data Hot Stress",
        "description": "Stressed timing/communication-path campaign that combines stale ECU coolant data with hotter and lower-airflow operating conditions.",
        "fault_class": "timing/communication-path fault under thermal stress",
        "hardware_source": "Persistent sampled-data refresh delay caused by stale register transfer, timing margin loss, or a delayed sensor-to-ECU communication update path.",
        "ecu_manifestation": "The controller repeatedly operates on aged coolant measurements during the urban-traffic and hot-idle phases.",
        "diagnostic_effect": "Coolant sensor rationality evidence is expected to persist longer, with overtemperature and safe-state transitions appearing sooner than in the milder timing case.",
        "system_effect": "This is the strongest timing/communication demonstration case: stale data delays cooling action enough to create a visible thermal and safety consequence.",
    },
    "pump_degraded_only": {
        "campaign_name": "Pump Degraded Only",
        "description": "Actuation-path degradation case for reduced pump authority and tracking mismatch.",
        "fault_class": "actuation-path fault",
        "hardware_source": "Weak driver behavior, supply droop, aging, or partial loss of pump actuation authority.",
        "ecu_manifestation": "Pump actual response is reduced relative to the ECU command.",
        "diagnostic_effect": "Pump tracking fault and possibly cooling-performance degradation behavior are expected as the mismatch persists.",
        "system_effect": "Reduced heat rejection can raise coolant temperature and may eventually push the safety monitor toward precautionary action.",
    },
    "fan_stuck_only": {
        "campaign_name": "Fan Stuck Only",
        "description": "Permanent fan actuation-loss case for direct tracking-fault and safe-state behavior.",
        "fault_class": "actuation-path fault",
        "hardware_source": "PWM output, gate-driver, or power-stage fault that leaves the fan effectively stuck off.",
        "ecu_manifestation": "The ECU commands fan actuation, but the realized fan response stays near zero.",
        "diagnostic_effect": "Fan tracking DTC is expected quickly because commanded and realized fan signals diverge.",
        "system_effect": "Protective cooling and limp-home escalation are expected as the ECU responds to persistent actuation loss.",
    },
    "fan_stuck_hot_stress": {
        "campaign_name": "Fan Stuck Hot Stress",
        "description": "Thermally stressed permanent-fault case that best exposes cross-layer propagation into safety response.",
        "fault_class": "actuation-path fault under thermal stress",
        "hardware_source": "Permanent fan power-stage or gate-driver stuck-off fault combined with hotter ambient and lower ram-air cooling.",
        "ecu_manifestation": "Fan command remains high while fan actual remains unavailable during a thermally aggressive operating condition.",
        "diagnostic_effect": "Fan tracking DTC is expected, followed by stronger thermal-warning and performance-related evidence if temperature rises.",
        "system_effect": "This is the strongest cross-layer safe-state case: thermal stress rises faster and precautionary or limp-home behavior appears earlier.",
    },
    "calibration_memory_corruption": {
        "campaign_name": "Calibration Memory Corruption",
        "description": "Computation/memory-path case where corrupted control calibration shifts thermal behavior over time.",
        "fault_class": "computation/memory-path fault",
        "hardware_source": "Corrupted calibration register, NVM bit upset, or memory-path fault affecting the coolant control target.",
        "ecu_manifestation": "The ECU uses a shifted cooling target, delaying requested cooling despite correct sensed temperatures.",
        "diagnostic_effect": "Cooling-performance and thermal-related diagnostics are expected later in the run as the consequences propagate outward.",
        "system_effect": "Higher peak coolant temperature and earlier safety intervention are expected because the controller itself is miscalibrated.",
    },
    "paper_default": {
        "campaign_name": "Paper Default",
        "description": "Mixed multi-stage campaign for demonstrating sensing, actuation, and safety propagation in one run.",
        "fault_class": "mixed hardware-origin faults",
        "hardware_source": "Sequential sensing-path, actuation-path, and power-stage faults representing a cross-layer multi-stage failure story.",
        "ecu_manifestation": "The ECU first sees biased sensing, then degraded pump authority, then fan actuation loss.",
        "diagnostic_effect": "Diagnostics evolve over time from sensor rationality behavior to actuator-tracking and thermal-response evidence.",
        "system_effect": "This campaign demonstrates staged propagation from hardware-origin faults into system degradation and safety escalation.",
    },
}


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summary_path_for(log_path: Path) -> Path:
    if log_path.suffix.lower() == ".csv":
        return log_path.with_name(f"{log_path.stem}_summary.csv")
    return log_path.with_name(f"{log_path.name}_summary.csv")


def detect_executable() -> Path | None:
    for candidate in (PROJECT_ROOT / "virtual_ecu", PROJECT_ROOT / "virtual_ecu.exe"):
        if candidate.exists():
            return candidate
    return None


def campaign_log_path(campaign_id: str, slot: str = "single") -> Path:
    return LOGS_DIR / f"gui_{slot}_{campaign_id}.csv"


def float_series(rows: Sequence[Dict[str, str]], key: str) -> List[float]:
    return [float(row[key]) for row in rows]


def int_series(rows: Sequence[Dict[str, str]], key: str) -> List[int]:
    return [int(float(row[key])) for row in rows]


def event_modes(first_row: Dict[str, str]) -> List[str]:
    modes = []

    for index in range(1, 5):
        mode_label = first_row.get(f"campaign_event_{index}_mode_label", "none")
        if mode_label and mode_label != "none":
            modes.append(mode_label)

    return modes


def event_behaviors(first_row: Dict[str, str]) -> List[str]:
    behaviors = []

    for index in range(1, 5):
        behavior_label = first_row.get(f"campaign_event_{index}_behavior_label", "none")
        if behavior_label and behavior_label != "none":
            behaviors.append(behavior_label)

    return behaviors


def infer_fault_class(first_row: Dict[str, str]) -> str:
    modes = event_modes(first_row)
    classes = {MODE_TO_CLASS.get(mode, "other fault") for mode in modes}

    if not modes:
        return "baseline"
    if len(classes) == 1:
        return next(iter(classes))
    return "mixed hardware-origin faults"


def campaign_story(campaign_id: str) -> Dict[str, str]:
    return CAMPAIGN_STORIES.get(
        campaign_id,
        {
            "campaign_name": campaign_id,
            "description": "No campaign-specific description is available.",
            "fault_class": "unknown",
            "hardware_source": "No campaign-specific cross-layer description is available.",
            "ecu_manifestation": "No campaign-specific ECU manifestation description is available.",
            "diagnostic_effect": "No campaign-specific diagnostic description is available.",
            "system_effect": "No campaign-specific system-level description is available.",
        },
    )


def format_latency(value: str) -> str:
    try:
        latency_ms = int(float(value))
    except (TypeError, ValueError):
        return "n/a"

    if latency_ms < 0:
        return "n/a"

    return f"{latency_ms} ms"


def format_temperature(value: str) -> str:
    try:
        return f"{float(value):.2f} C"
    except (TypeError, ValueError):
        return "n/a"


def summarize_fault_class(campaign_id: str, first_row: Dict[str, str] | None = None) -> str:
    if campaign_id in CAMPAIGN_STORIES:
        return CAMPAIGN_STORIES[campaign_id]["fault_class"]
    if first_row is not None:
        return infer_fault_class(first_row)
    return "unknown"


def metric_card_colors(metric_name: str, value: str) -> Tuple[str, str]:
    neutral = ("#eef3f7", "#1f2e3b")
    alert = ("#fce8e6", "#8a2f27")
    caution = ("#fff4dd", "#8a6120")
    info = ("#e8f0fb", "#1c4d8c")
    calm = ("#e8f4ec", "#245f3d")

    if value in {"n/a", "-", "none", "normal"}:
        return neutral

    if metric_name == "Final DTC":
        return alert if value != "none" else calm
    if metric_name == "Final Safe State":
        if value == "controlled_shutdown":
            return alert
        if value in {"limp_home", "precautionary_cooling"}:
            return caution
        return calm
    if metric_name == "Maximum Coolant Temperature":
        try:
            temp_c = float(value.split()[0])
        except (IndexError, ValueError):
            return neutral
        if temp_c >= 115.0:
            return alert
        if temp_c >= 108.0:
            return caution
        return calm
    if metric_name in {"Detection Latency", "Safe-State Latency"}:
        return info

    return neutral


def comparison_export_dir(left_campaign_id: str, right_campaign_id: str) -> Path:
    return EXPORT_ROOT / f"{left_campaign_id}_vs_{right_campaign_id}"


def snapshot_export_dir(left_campaign_id: str, right_campaign_id: str) -> Path:
    return SNAPSHOT_ROOT / f"{left_campaign_id}_vs_{right_campaign_id}"


def write_report_csv(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["field", "left", "right"])
        writer.writeheader()
        writer.writerows(rows)


def write_snapshot_csv(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["section", "field", "left", "right", "value"])
        writer.writeheader()
        writer.writerows(rows)


def int_or_none(value: str) -> int | None:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return None if parsed < 0 else parsed


def float_or_none(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean_or_none(values: Sequence[float | int]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def mode_or_none(values: Iterable[str]) -> str:
    filtered = [value for value in values if isinstance(value, str) and value]
    if not filtered:
        return "n/a"

    counts: Dict[str, int] = {}
    for value in filtered:
        counts[value] = counts.get(value, 0) + 1

    top_count = max(counts.values())
    winners = sorted(value for value, count in counts.items() if count == top_count)
    return winners[0]


def safe_state_score(label: str) -> int:
    return SAFE_STATE_SEVERITY.get(label, 0)


def dtc_score(summary_row: Dict[str, str]) -> int:
    dtc_id = int_or_none(summary_row.get("final_primary_dtc_id", ""))
    if dtc_id is not None:
        return DTC_SEVERITY.get(dtc_id, 1 if dtc_id > 0 else 0)
    return 0 if summary_row.get("final_primary_dtc_label", "none") == "none" else 1


def summary_max_temp(summary_row: Dict[str, str]) -> float | None:
    return float_or_none(summary_row.get("max_coolant_temp_c", ""))


def summary_detection_latency(summary_row: Dict[str, str]) -> int | None:
    return int_or_none(summary_row.get("detection_latency_ms", ""))


def summary_safe_state_latency(summary_row: Dict[str, str]) -> int | None:
    return int_or_none(summary_row.get("safe_state_latency_ms", ""))


def summary_safe_mode_duration(summary_row: Dict[str, str]) -> int | None:
    return int_or_none(summary_row.get("safe_mode_duration_ms", ""))


def format_latency_value(value: int | None) -> str:
    return "n/a" if value is None else f"{value} ms"


def format_temp_value(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f} C"


def humanize_label(value: str) -> str:
    return value.replace("_", " ")


def compare_detection_statement(
    left_name: str,
    left_summary: Dict[str, str],
    right_name: str,
    right_summary: Dict[str, str],
) -> Tuple[str, str]:
    left_latency = summary_detection_latency(left_summary)
    right_latency = summary_detection_latency(right_summary)

    if left_latency is None and right_latency is None:
        return ("Detection", "Neither campaign confirms a fault during the run.")
    if left_latency is None:
        return ("Detection", f"{right_name} detects faster because it is the only case with confirmed fault detection ({right_latency} ms).")
    if right_latency is None:
        return ("Detection", f"{left_name} detects faster because it is the only case with confirmed fault detection ({left_latency} ms).")
    if left_latency < right_latency:
        return ("Detection", f"{left_name} detects faster ({left_latency} ms vs {right_latency} ms).")
    if right_latency < left_latency:
        return ("Detection", f"{right_name} detects faster ({right_latency} ms vs {left_latency} ms).")
    return ("Detection", f"Both campaigns detect at the same latency ({left_latency} ms).")


def comparison_findings(
    left_name: str,
    left_summary: Dict[str, str],
    right_name: str,
    right_summary: Dict[str, str],
) -> Tuple[List[str], List[str]]:
    lines: List[str] = []
    interpretation: List[str] = []

    left_temp = summary_max_temp(left_summary)
    right_temp = summary_max_temp(right_summary)
    if left_temp is not None and right_temp is not None:
        if left_temp > right_temp:
            thermal_line = f"Thermal severity: {left_name} is more severe ({left_temp:.2f} C vs {right_temp:.2f} C peak coolant)."
            thermal_winner = left_name
        elif right_temp > left_temp:
            thermal_line = f"Thermal severity: {right_name} is more severe ({right_temp:.2f} C vs {left_temp:.2f} C peak coolant)."
            thermal_winner = right_name
        else:
            thermal_line = f"Thermal severity: both campaigns reach the same peak coolant temperature ({left_temp:.2f} C)."
            thermal_winner = "both campaigns"
    else:
        thermal_line = "Thermal severity: peak coolant temperature is not available for one or both campaigns."
        thermal_winner = "neither campaign"
    lines.append(thermal_line)

    _label, detection_line = compare_detection_statement(left_name, left_summary, right_name, right_summary)
    lines.append(f"Fault detection: {detection_line.split(': ', 1)[-1] if ': ' in detection_line else detection_line}")

    left_state = left_summary.get("final_safe_state_label", "normal")
    right_state = right_summary.get("final_safe_state_label", "normal")
    left_state_score = safe_state_score(left_state)
    right_state_score = safe_state_score(right_state)
    left_safe_duration = summary_safe_mode_duration(left_summary) or 0
    right_safe_duration = summary_safe_mode_duration(right_summary) or 0

    if (left_state_score, left_safe_duration) > (right_state_score, right_safe_duration):
        safe_winner = left_name
        safe_line = (
            f"Safe-state impact: {left_name} is stronger "
            f"({humanize_label(left_state)} final state, {format_latency_value(summary_safe_state_latency(left_summary))} entry, {left_safe_duration} ms safe-mode duration)."
        )
    elif (right_state_score, right_safe_duration) > (left_state_score, left_safe_duration):
        safe_winner = right_name
        safe_line = (
            f"Safe-state impact: {right_name} is stronger "
            f"({humanize_label(right_state)} final state, {format_latency_value(summary_safe_state_latency(right_summary))} entry, {right_safe_duration} ms safe-mode duration)."
        )
    else:
        safe_winner = "both campaigns"
        safe_line = f"Safe-state impact: both campaigns finish with comparable safe-state severity ({humanize_label(left_state)} vs {humanize_label(right_state)})."
    lines.append(safe_line)

    left_dtc = left_summary.get("final_primary_dtc_label", "none")
    right_dtc = right_summary.get("final_primary_dtc_label", "none")
    left_dtc_score = dtc_score(left_summary)
    right_dtc_score = dtc_score(right_summary)
    if (left_dtc_score, left_state_score) > (right_dtc_score, right_state_score):
        critical_winner = left_name
        critical_line = f"Critical end state: {left_name} is more critical at the end of the run ({humanize_label(left_dtc)} / {humanize_label(left_state)})."
    elif (right_dtc_score, right_state_score) > (left_dtc_score, left_state_score):
        critical_winner = right_name
        critical_line = f"Critical end state: {right_name} is more critical at the end of the run ({humanize_label(right_dtc)} / {humanize_label(right_state)})."
    else:
        critical_winner = "both campaigns"
        critical_line = f"Critical end state: both campaigns finish with similar end-of-run criticality ({humanize_label(left_dtc)} / {humanize_label(left_state)} vs {humanize_label(right_dtc)} / {humanize_label(right_state)})."
    lines.append(critical_line)

    interpretation.append(f"{thermal_winner.capitalize() if thermal_winner != 'both campaigns' else 'The two cases'} drives the stronger thermal outcome in this comparison.")
    interpretation.append(detection_line)
    interpretation.append(f"{safe_winner.capitalize() if safe_winner != 'both campaigns' else 'Both campaigns'} shows the stronger protection response at ECU safe-state level.")
    interpretation.append(f"{critical_winner.capitalize() if critical_winner != 'both campaigns' else 'The end states'} gives the more critical end-of-run diagnostic/safety outcome.")

    return lines, interpretation


def batch_findings(rows: Sequence[Dict[str, str]]) -> Tuple[List[str], List[str]]:
    fault_types = [fault_type for fault_type in FAULT_TYPE_ORDER if fault_type != "none" and any(row["fault_type"] == fault_type for row in rows)]
    type_rows = {fault_type: [row for row in rows if row["fault_type"] == fault_type] for fault_type in fault_types}

    detection_means = {
        fault_type: mean_or_none(
            [value for value in (int_or_none(row.get("detection_latency_ms", "")) for row in type_rows[fault_type]) if value is not None]
        )
        for fault_type in fault_types
    }
    temp_means = {
        fault_type: mean_or_none(
            [value for value in (float_or_none(row.get("max_coolant_temperature_c", "")) for row in type_rows[fault_type]) if value is not None]
        )
        for fault_type in fault_types
    }
    safe_duration_means = {
        fault_type: mean_or_none(
            [value for value in (int_or_none(row.get("safe_mode_duration_ms", "")) for row in type_rows[fault_type]) if value is not None]
        )
        for fault_type in fault_types
    }
    safe_state_scores = {
        fault_type: mean_or_none([safe_state_score(row.get("final_safe_state", "normal")) for row in type_rows[fault_type]])
        for fault_type in fault_types
    }

    valid_detection = {fault_type: value for fault_type, value in detection_means.items() if value is not None}
    fastest_detection = min(valid_detection, key=valid_detection.get) if valid_detection else None
    hottest_fault = max(temp_means, key=lambda fault_type: temp_means[fault_type] or float("-inf")) if temp_means else None
    strongest_safe = max(
        fault_types,
        key=lambda fault_type: (
            safe_state_scores.get(fault_type) or 0.0,
            safe_duration_means.get(fault_type) or 0.0,
            -(detection_means.get(fault_type) or 1_000_000.0),
        ),
    ) if fault_types else None

    lines: List[str] = []
    interpretation: List[str] = []

    if fastest_detection is not None:
        lines.append(
            f"Fastest mean detection: {FAULT_TYPE_DISPLAY.get(fastest_detection, fastest_detection)} ({detection_means[fastest_detection]:.1f} ms)."
        )
    else:
        lines.append("Fastest mean detection: no fault type shows confirmed detection in the loaded batch.")

    if hottest_fault is not None and temp_means[hottest_fault] is not None:
        lines.append(
            f"Highest mean max coolant temperature: {FAULT_TYPE_DISPLAY.get(hottest_fault, hottest_fault)} ({temp_means[hottest_fault]:.2f} C)."
        )
    else:
        lines.append("Highest mean max coolant temperature: not available from the loaded batch.")

    if strongest_safe is not None:
        lines.append(
            f"Strongest safe-state effect: {FAULT_TYPE_DISPLAY.get(strongest_safe, strongest_safe)} "
            f"(mean final-state severity {safe_state_scores[strongest_safe]:.2f}, mean safe-mode duration {(safe_duration_means[strongest_safe] or 0.0):.1f} ms)."
        )
    else:
        lines.append("Strongest safe-state effect: not available from the loaded batch.")

    timing_mean_temp = temp_means.get("stale_sensor_data")
    timing_safe_score = safe_state_scores.get("stale_sensor_data")
    timing_is_meaningful = (
        "stale_sensor_data" in type_rows
        and (
            (timing_mean_temp is not None and timing_mean_temp >= 108.0)
            or (timing_safe_score is not None and timing_safe_score > 0.0)
            or ((safe_duration_means.get("stale_sensor_data") or 0.0) > 0.0)
        )
    )
    if "stale_sensor_data" in type_rows:
        meaning = "does" if timing_is_meaningful else "does not yet"
        lines.append(
            f"Timing/communication case: Stale Sensor Data {meaning} appear as a meaningful study case "
            f"({format_temp_value(timing_mean_temp)} mean peak coolant, {(safe_duration_means.get('stale_sensor_data') or 0.0):.1f} ms mean safe-mode duration)."
        )
    else:
        lines.append("Timing/communication case: no stale-sensor-data runs are present in the loaded batch.")

    if hottest_fault is not None:
        interpretation.append(
            f"{FAULT_TYPE_DISPLAY.get(hottest_fault, hottest_fault)} currently drives the strongest thermal excursion in the aggregate study."
        )
    if fastest_detection is not None:
        interpretation.append(
            f"{FAULT_TYPE_DISPLAY.get(fastest_detection, fastest_detection)} is the most observable fault family at mean detection-latency level."
        )
    if strongest_safe is not None:
        interpretation.append(
            f"{FAULT_TYPE_DISPLAY.get(strongest_safe, strongest_safe)} shows the strongest protection-state consequence across the loaded batch."
        )
    interpretation.append(
        "The timing/communication path is now treated as a meaningful study case when stale-sensor-data runs produce clear thermal or protection impact."
        if timing_is_meaningful
        else "The timing/communication path is present, but its batch-level consequence remains milder than the strongest actuation or mixed-fault cases."
    )

    return lines, interpretation


def render_snapshot_markdown(snapshot: Dict[str, object]) -> str:
    left_campaign_id = str(snapshot["left_campaign_id"])
    right_campaign_id = str(snapshot["right_campaign_id"])
    left_campaign_name = str(snapshot["left_campaign_name"])
    right_campaign_name = str(snapshot["right_campaign_name"])
    left_fault_class = str(snapshot["left_fault_class"])
    right_fault_class = str(snapshot["right_fault_class"])
    metrics = snapshot["metrics"]  # type: ignore[assignment]
    findings = snapshot["findings"]  # type: ignore[assignment]
    interpretation = snapshot["interpretation"]  # type: ignore[assignment]

    lines = [
        "# Virtual ECU Results Snapshot",
        "",
        "## Comparison",
        "",
        f"- Left campaign: `{left_campaign_id}` ({left_campaign_name})",
        f"- Right campaign: `{right_campaign_id}` ({right_campaign_name})",
        f"- Left fault class: {left_fault_class}",
        f"- Right fault class: {right_fault_class}",
        "",
        "## Key Metrics",
        "",
        "| Metric | Left | Right |",
        "| --- | --- | --- |",
    ]

    for metric_name, values in metrics:
        lines.append(f"| {metric_name} | {values['left']} | {values['right']} |")

    lines.extend(["", "## Key Findings", ""])
    lines.extend(f"- {line}" for line in findings)
    lines.extend(["", "## Interpretation", ""])
    lines.extend(f"- {line}" for line in interpretation)
    lines.append("")
    return "\n".join(lines)


def snapshot_csv_rows(snapshot: Dict[str, object]) -> List[Dict[str, str]]:
    rows = [
        {
            "section": "comparison",
            "field": "left_campaign",
            "left": str(snapshot["left_campaign_id"]),
            "right": "",
            "value": str(snapshot["left_campaign_name"]),
        },
        {
            "section": "comparison",
            "field": "right_campaign",
            "left": "",
            "right": str(snapshot["right_campaign_id"]),
            "value": str(snapshot["right_campaign_name"]),
        },
        {
            "section": "comparison",
            "field": "fault_class",
            "left": str(snapshot["left_fault_class"]),
            "right": str(snapshot["right_fault_class"]),
            "value": "",
        },
    ]

    for metric_name, values in snapshot["metrics"]:  # type: ignore[index]
        rows.append(
            {
                "section": "metrics",
                "field": metric_name.lower().replace(" ", "_"),
                "left": values["left"],
                "right": values["right"],
                "value": "",
            }
        )

    for index, line in enumerate(snapshot["findings"], start=1):  # type: ignore[index]
        rows.append(
            {
                "section": "findings",
                "field": f"finding_{index}",
                "left": "",
                "right": "",
                "value": str(line),
            }
        )

    for index, line in enumerate(snapshot["interpretation"], start=1):  # type: ignore[index]
        rows.append(
            {
                "section": "interpretation",
                "field": f"line_{index}",
                "left": "",
                "right": "",
                "value": str(line),
            }
        )

    return rows


def save_snapshot_overview_image(path: Path, snapshot: Dict[str, object]) -> None:
    metrics = snapshot["metrics"]  # type: ignore[assignment]
    findings = snapshot["findings"]  # type: ignore[assignment]
    interpretation = snapshot["interpretation"]  # type: ignore[assignment]

    summary_lines = [
        f"Left: {snapshot['left_campaign_name']} ({snapshot['left_campaign_id']})",
        f"Right: {snapshot['right_campaign_name']} ({snapshot['right_campaign_id']})",
        f"Left fault class: {snapshot['left_fault_class']}",
        f"Right fault class: {snapshot['right_fault_class']}",
        "",
        "Key Metrics",
    ]
    for metric_name, values in metrics:
        summary_lines.append(f"{metric_name}: L={values['left']} | R={values['right']}")

    finding_lines = ["Key Findings"]
    finding_lines.extend(f"- {line}" for line in findings)

    interpretation_lines = ["Interpretation"]
    for line in interpretation:
        interpretation_lines.extend(textwrap.wrap(line, width=52) or [line])

    fig = plt.figure(figsize=(12, 8), constrained_layout=True)
    fig.patch.set_facecolor("#f4f6f8")
    grid = fig.add_gridspec(2, 2, height_ratios=[3, 2], width_ratios=[3, 2])

    title_ax = fig.add_subplot(grid[0, 0])
    findings_ax = fig.add_subplot(grid[0, 1])
    interpretation_ax = fig.add_subplot(grid[1, :])

    for axis in (title_ax, findings_ax, interpretation_ax):
        axis.axis("off")

    title_ax.text(
        0.0,
        1.0,
        "Virtual ECU Results Snapshot",
        fontsize=18,
        fontweight="bold",
        color="#1d3448",
        va="top",
    )
    title_ax.text(
        0.0,
        0.92,
        "\n".join(summary_lines),
        fontsize=11,
        color="#22313f",
        va="top",
        linespacing=1.5,
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#ffffff", "edgecolor": "#d8e0e7"},
    )
    findings_ax.text(
        0.0,
        1.0,
        "\n".join(finding_lines),
        fontsize=11,
        color="#22313f",
        va="top",
        linespacing=1.5,
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#ffffff", "edgecolor": "#d8e0e7"},
    )
    interpretation_ax.text(
        0.0,
        1.0,
        "\n".join(interpretation_lines),
        fontsize=11,
        color="#425160",
        va="top",
        linespacing=1.6,
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#ffffff", "edgecolor": "#d8e0e7"},
    )

    fig.savefig(path, dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)


def write_snapshot_bundle(export_dir: Path, snapshot: Dict[str, object]) -> List[Path]:
    export_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

    markdown_path = export_dir / "snapshot_summary.md"
    csv_path = export_dir / "snapshot_summary.csv"
    image_path = export_dir / "snapshot_overview.png"

    markdown_path.write_text(render_snapshot_markdown(snapshot), encoding="utf-8")
    write_snapshot_csv(csv_path, snapshot_csv_rows(snapshot))
    save_snapshot_overview_image(image_path, snapshot)

    return [markdown_path, csv_path, image_path]


def save_coolant_comparison_plot(
    left_label: str,
    left_rows: Sequence[Dict[str, str]],
    right_label: str,
    right_rows: Sequence[Dict[str, str]],
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 4.8), constrained_layout=True)
    ax.plot(float_series(left_rows, "time_s"), float_series(left_rows, "coolant_temp_true_c"), color=LEFT_COLOR, linewidth=2.2, label=left_label)
    ax.plot(float_series(right_rows, "time_s"), float_series(right_rows, "coolant_temp_true_c"), color=RIGHT_COLOR, linewidth=2.2, linestyle="--", label=right_label)
    ax.axhline(108.0, color="#8c6b2d", linestyle="--", linewidth=1.1)
    ax.axhline(115.0, color="#7b4d57", linestyle=":", linewidth=1.1)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Coolant Temperature [C]")
    ax.set_title("Coolant Temperature Comparison")
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.8)
    ax.legend(loc="upper left", frameon=False)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def save_safe_state_comparison_plot(
    left_label: str,
    left_rows: Sequence[Dict[str, str]],
    right_label: str,
    right_rows: Sequence[Dict[str, str]],
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 4.8), constrained_layout=True)
    ax.step(float_series(left_rows, "time_s"), int_series(left_rows, "safe_state_id"), where="post", color=LEFT_COLOR, linewidth=2.2, label=left_label)
    ax.step(float_series(right_rows, "time_s"), int_series(right_rows, "safe_state_id"), where="post", color=RIGHT_COLOR, linewidth=2.2, linestyle="--", label=right_label)
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(["Normal", "Precautionary", "Limp Home", "Shutdown"])
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Safe State")
    ax.set_title("Safe-State Comparison")
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.8)
    ax.legend(loc="upper left", frameon=False)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def save_fan_comparison_plot(
    left_label: str,
    left_rows: Sequence[Dict[str, str]],
    right_label: str,
    right_rows: Sequence[Dict[str, str]],
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 4.8), constrained_layout=True)
    ax.plot(float_series(left_rows, "time_s"), float_series(left_rows, "fan_command"), color=LEFT_COLOR, linewidth=2.2, label=f"{left_label} command")
    ax.plot(float_series(left_rows, "time_s"), float_series(left_rows, "fan_actual"), color="#7d1f17", linewidth=1.8, linestyle=":", label=f"{left_label} actual")
    ax.plot(float_series(right_rows, "time_s"), float_series(right_rows, "fan_command"), color=RIGHT_COLOR, linewidth=2.2, linestyle="--", label=f"{right_label} command")
    ax.plot(float_series(right_rows, "time_s"), float_series(right_rows, "fan_actual"), color="#5e7fb0", linewidth=1.8, linestyle="-.", label=f"{right_label} actual")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Fan [-]")
    ax.set_ylim(0.0, 1.05)
    ax.set_title("Fan Command / Actual Comparison")
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.8)
    ax.legend(loc="upper left", ncol=2, frameon=False)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


class PlotCanvas(ttk.Frame):
    """Small reusable plotting widget backed by a Tkinter Canvas."""

    def __init__(self, master: tk.Misc, title: str, *, canvas_height: int = 220) -> None:
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.title_var = tk.StringVar(value=title)
        self.base_canvas_height = canvas_height
        self.presentation_mode = False

        self.title_label = ttk.Label(self, textvariable=self.title_var, style="Section.TLabel")
        self.title_label.grid(
            row=0, column=0, sticky="w", padx=6, pady=(0, 4)
        )

        self.canvas = tk.Canvas(
            self,
            background="#ffffff",
            height=canvas_height,
            highlightthickness=1,
            highlightbackground="#c7d0d9",
        )
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _event: self.redraw())
        self._drawer = self._draw_message
        self._payload: object = "No data loaded yet."

    def set_title(self, title: str) -> None:
        self.title_var.set(title)

    def set_presentation_mode(self, enabled: bool) -> None:
        self.presentation_mode = enabled
        extra_height = 80 if enabled and self.base_canvas_height >= 600 else 40 if enabled else 0
        self.canvas.configure(height=self.base_canvas_height + extra_height)
        self.redraw()

    def show_message(self, text: str) -> None:
        self._drawer = self._draw_message
        self._payload = text
        self.redraw()

    def plot_lines(
        self,
        series: Sequence[Tuple[str, str, Sequence[float], Sequence[float], Tuple[int, ...] | None]],
        *,
        y_label: str,
        y_min: float | None = None,
        y_max: float | None = None,
        threshold_lines: Sequence[Tuple[float, str, str]] = (),
    ) -> None:
        self._drawer = self._draw_line_plot
        self._payload = {
            "series": [
                (label, color, list(x_values), list(y_values), dash)
                for label, color, x_values, y_values, dash in series
            ],
            "y_label": y_label,
            "y_min": y_min,
            "y_max": y_max,
            "threshold_lines": list(threshold_lines),
        }
        self.redraw()

    def plot_step_series(
        self,
        x_values: Sequence[float],
        y_values: Sequence[int],
        *,
        y_label: str,
        tick_labels: Dict[int, str],
    ) -> None:
        self._drawer = self._draw_step_plot
        self._payload = {
            "x_values": list(x_values),
            "y_values": list(y_values),
            "y_label": y_label,
            "tick_labels": dict(tick_labels),
        }
        self.redraw()

    def plot_step_comparison(
        self,
        series: Sequence[Tuple[str, str, Sequence[float], Sequence[int], Tuple[int, ...] | None]],
        *,
        y_label: str,
        tick_labels: Dict[int, str],
    ) -> None:
        self._drawer = self._draw_step_comparison_plot
        self._payload = {
            "series": [
                (label, color, list(x_values), list(y_values), dash)
                for label, color, x_values, y_values, dash in series
            ],
            "y_label": y_label,
            "tick_labels": dict(tick_labels),
        }
        self.redraw()

    def plot_bars(
        self,
        categories: Sequence[str],
        values: Sequence[float | None],
        *,
        y_label: str,
        bar_color: str = "#4c78a8",
    ) -> None:
        self._drawer = self._draw_bar_plot
        self._payload = {
            "categories": list(categories),
            "values": list(values),
            "y_label": y_label,
            "bar_color": bar_color,
        }
        self.redraw()

    def plot_stacked_bars(
        self,
        categories: Sequence[str],
        stacks: Sequence[Tuple[str, str, Sequence[float]]],
        *,
        y_label: str,
        max_value: float = 100.0,
        x_label: str = "Fault Type",
    ) -> None:
        self._drawer = self._draw_stacked_bar_plot
        self._payload = {
            "categories": list(categories),
            "stacks": [
                (label, color, list(values))
                for label, color, values in stacks
            ],
            "y_label": y_label,
            "max_value": max_value,
            "x_label": x_label,
        }
        self.redraw()

    def redraw(self) -> None:
        self.canvas.delete("all")
        self._drawer(self._payload)

    def _canvas_size(self) -> Tuple[int, int]:
        width = max(self.canvas.winfo_width(), 280)
        height = max(self.canvas.winfo_height(), 200)
        return width, height

    def _font(self, role: str) -> Tuple[str, int] | Tuple[str, int, str]:
        presentation = self.presentation_mode
        if role == "message":
            return ("TkDefaultFont", 12 if presentation else 10, "bold" if presentation else "normal")
        if role == "axis_label":
            return ("TkDefaultFont", 11 if presentation else 10, "bold" if presentation else "normal")
        if role == "tick":
            return ("TkDefaultFont", 10 if presentation else 9)
        if role == "legend":
            return ("TkDefaultFont", 10 if presentation else 9)
        if role == "threshold":
            return ("TkDefaultFont", 10 if presentation else 9, "bold" if presentation else "normal")
        if role == "bar_value":
            return ("TkDefaultFont", 10 if presentation else 9, "bold")
        return ("TkDefaultFont", 10)

    def _line_width(self, emphasis: bool = False) -> int:
        if self.presentation_mode:
            return 3 if emphasis else 2
        return 2 if emphasis else 1

    def _plot_bounds(
        self,
        *,
        left_margin: int = 76,
        top_margin: int = 18,
        right_margin: int = 24,
        bottom_margin: int = 54,
    ) -> Tuple[int, int, int, int]:
        width, height = self._canvas_size()
        left = left_margin
        top = top_margin
        right = max(width - right_margin, left + 40)
        bottom = max(height - bottom_margin, top + 40)
        return left, top, right, bottom

    def _draw_axes(
        self,
        y_label: str,
        x_label: str = "Time [s]",
        *,
        left_margin: int = 76,
        top_margin: int = 18,
        right_margin: int = 24,
        bottom_margin: int = 54,
    ) -> Tuple[int, int, int, int]:
        left, top, right, bottom = self._plot_bounds(
            left_margin=left_margin,
            top_margin=top_margin,
            right_margin=right_margin,
            bottom_margin=bottom_margin,
        )
        self.canvas.create_line(left, bottom, right, bottom, fill="#4a5560", width=self._line_width())
        self.canvas.create_line(left, bottom, left, top, fill="#4a5560", width=self._line_width())
        self.canvas.create_text(
            (left + right) / 2,
            bottom + (30 if self.presentation_mode else 26),
            text=x_label,
            fill="#33404d",
            font=self._font("axis_label"),
        )
        self.canvas.create_text(
            28 if self.presentation_mode else 24,
            (top + bottom) / 2,
            text=y_label,
            fill="#33404d",
            angle=90,
            font=self._font("axis_label"),
        )
        return left, top, right, bottom

    def _legend_rows(
        self,
        entries: Sequence[Tuple[str, str, Tuple[int, ...] | None]],
        available_width: float,
    ) -> List[List[Tuple[str, str, Tuple[int, ...] | None]]]:
        rows: List[List[Tuple[str, str, Tuple[int, ...] | None]]] = []
        current_row: List[Tuple[str, str, Tuple[int, ...] | None]] = []
        current_width = 0.0

        for label, color, dash in entries:
            entry_width = 48 + len(label) * (7.6 if self.presentation_mode else 6.8)
            if current_row and current_width + entry_width > available_width:
                rows.append(current_row)
                current_row = []
                current_width = 0.0
            current_row.append((label, color, dash))
            current_width += entry_width

        if current_row:
            rows.append(current_row)

        return rows

    def _draw_legend(
        self,
        entries: Sequence[Tuple[str, str, Tuple[int, ...] | None]],
        *,
        left: int,
        top: int,
        right: int,
    ) -> int:
        if not entries:
            return 0

        rows = self._legend_rows(entries, max(right - left - 8, 120))
        y_pos = top
        for row in rows:
            x_pos = left
            for label, color, dash in row:
                self.canvas.create_line(
                    x_pos,
                    y_pos + 6,
                    x_pos + 18,
                    y_pos + 6,
                    fill=color,
                    width=self._line_width(emphasis=True),
                    dash=dash or (),
                )
                self.canvas.create_text(
                    x_pos + 24,
                    y_pos + 6,
                    text=label,
                    anchor="w",
                    fill="#33404d",
                    font=self._font("legend"),
                )
                x_pos += 48 + len(label) * (7.6 if self.presentation_mode else 6.8)
            y_pos += 22 if self.presentation_mode else 18

        row_height = 22 if self.presentation_mode else 18
        return max(row_height * len(rows) + 8, 0)

    def _bottom_margin_for_categories(self, categories: Sequence[str]) -> int:
        if not categories:
            return 64 if self.presentation_mode else 56
        longest = max(len(category) for category in categories)
        if longest > 22:
            return 104 if self.presentation_mode else 92
        if longest > 14:
            return 88 if self.presentation_mode else 76
        return 70 if self.presentation_mode else 60

    def _draw_message(self, payload: object) -> None:
        width, height = self._canvas_size()
        self.canvas.create_text(
            width / 2,
            height / 2,
            text=str(payload),
            fill="#506070",
            font=self._font("message"),
            width=max(width - 40, 120),
            justify="center",
        )

    def _draw_line_plot(self, payload: object) -> None:
        data = payload  # type: ignore[assignment]
        series = data["series"]
        y_label = data["y_label"]
        y_min = data["y_min"]
        y_max = data["y_max"]
        threshold_lines = data["threshold_lines"]

        if not series:
            self._draw_message("No plot data available.")
            return

        all_x = [x_value for _, _, x_values, _, _ in series for x_value in x_values]
        all_y = [y_value for _, _, _, y_values, _ in series for y_value in y_values]
        if not all_x or not all_y:
            self._draw_message("No plot data available.")
            return

        legend_entries = [(label, color, dash) for label, color, _, _, dash in series]
        legend_height = self._draw_legend(legend_entries, left=86, top=10, right=self._canvas_size()[0] - 16)
        left, top, right, bottom = self._draw_axes(
            y_label,
            top_margin=18 + legend_height,
            bottom_margin=60,
        )
        all_y.extend(value for value, _, _ in threshold_lines)

        min_x = min(all_x)
        max_x = max(all_x)
        min_y = min(all_y) if y_min is None else y_min
        max_y = max(all_y) if y_max is None else y_max

        if max_x <= min_x:
            max_x = min_x + 1.0
        if max_y <= min_y:
            max_y = min_y + 1.0

        y_padding = 0.08 * (max_y - min_y)
        min_y -= y_padding
        max_y += y_padding

        def map_x(value: float) -> float:
            return left + (value - min_x) * (right - left) / (max_x - min_x)

        def map_y(value: float) -> float:
            return bottom - (value - min_y) * (bottom - top) / (max_y - min_y)

        for tick in range(5):
            y_value = min_y + tick * (max_y - min_y) / 4.0
            y_pos = map_y(y_value)
            self.canvas.create_line(left - 4, y_pos, right, y_pos, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(left - 8, y_pos, text=f"{y_value:.1f}", anchor="e", fill="#506070", font=self._font("tick"))

        for tick in range(5):
            x_value = min_x + tick * (max_x - min_x) / 4.0
            x_pos = map_x(x_value)
            self.canvas.create_line(x_pos, top, x_pos, bottom + 4, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(x_pos, bottom + 14, text=f"{x_value:.0f}", anchor="n", fill="#506070", font=self._font("tick"))

        for value, color, label in threshold_lines:
            y_pos = map_y(value)
            self.canvas.create_line(left, y_pos, right, y_pos, fill=color, dash=(6, 4), width=self._line_width())
            label_y = max(y_pos - 8, top + 8)
            self.canvas.create_text(right - 6, label_y, text=label, anchor="e", fill=color, font=self._font("threshold"))

        for label, color, x_values, y_values, dash in series:
            points = []
            for x_value, y_value in zip(x_values, y_values):
                points.extend((map_x(x_value), map_y(y_value)))

            if len(points) >= 4:
                self.canvas.create_line(*points, fill=color, width=self._line_width(emphasis=True), smooth=False, dash=dash or ())

    def _draw_step_plot(self, payload: object) -> None:
        data = payload  # type: ignore[assignment]
        x_values = data["x_values"]
        y_values = data["y_values"]
        y_label = data["y_label"]
        tick_labels = data["tick_labels"]

        if not x_values or not y_values:
            self._draw_message("No plot data available.")
            return

        left, top, right, bottom = self._draw_axes(y_label, bottom_margin=60)
        min_x = min(x_values)
        max_x = max(x_values)

        if max_x <= min_x:
            max_x = min_x + 1.0

        def map_x(value: float) -> float:
            return left + (value - min_x) * (right - left) / (max_x - min_x)

        def map_y(state_id: int) -> float:
            return bottom - state_id * (bottom - top) / 3.0

        for state_id in range(4):
            y_pos = map_y(state_id)
            self.canvas.create_line(left - 4, y_pos, right, y_pos, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(
                left - 8,
                y_pos,
                text=tick_labels.get(state_id, str(state_id)),
                anchor="e",
                fill="#506070",
                font=self._font("tick"),
            )

        for tick in range(5):
            x_value = min_x + tick * (max_x - min_x) / 4.0
            x_pos = map_x(x_value)
            self.canvas.create_line(x_pos, top, x_pos, bottom + 4, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(x_pos, bottom + 14, text=f"{x_value:.0f}", anchor="n", fill="#506070", font=self._font("tick"))

        points = []
        for index, (x_value, y_value) in enumerate(zip(x_values, y_values)):
            x_pos = map_x(x_value)
            y_pos = map_y(y_value)
            points.extend((x_pos, y_pos))

            if index + 1 < len(x_values):
                next_x = map_x(x_values[index + 1])
                points.extend((next_x, y_pos))

        if len(points) >= 4:
            self.canvas.create_line(*points, fill="#1f5aa6", width=self._line_width(emphasis=True), smooth=False)

    def _draw_step_comparison_plot(self, payload: object) -> None:
        data = payload  # type: ignore[assignment]
        series = data["series"]
        y_label = data["y_label"]
        tick_labels = data["tick_labels"]

        if not series:
            self._draw_message("No plot data available.")
            return

        all_x = [x for _, _, x_values, _, _ in series for x in x_values]
        if not all_x:
            self._draw_message("No plot data available.")
            return

        legend_entries = [(label, color, dash) for label, color, _, _, dash in series]
        legend_height = self._draw_legend(legend_entries, left=86, top=10, right=self._canvas_size()[0] - 16)
        left, top, right, bottom = self._draw_axes(
            y_label,
            top_margin=18 + legend_height,
            bottom_margin=60,
        )
        min_x = min(all_x)
        max_x = max(all_x)

        if max_x <= min_x:
            max_x = min_x + 1.0

        def map_x(value: float) -> float:
            return left + (value - min_x) * (right - left) / (max_x - min_x)

        def map_y(state_id: int) -> float:
            return bottom - state_id * (bottom - top) / 3.0

        for state_id in range(4):
            y_pos = map_y(state_id)
            self.canvas.create_line(left - 4, y_pos, right, y_pos, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(
                left - 8,
                y_pos,
                text=tick_labels.get(state_id, str(state_id)),
                anchor="e",
                fill="#506070",
                font=self._font("tick"),
            )

        for tick in range(5):
            x_value = min_x + tick * (max_x - min_x) / 4.0
            x_pos = map_x(x_value)
            self.canvas.create_line(x_pos, top, x_pos, bottom + 4, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(x_pos, bottom + 14, text=f"{x_value:.0f}", anchor="n", fill="#506070", font=self._font("tick"))

        for label, color, x_values, y_values, dash in series:
            points = []
            for index, (x_value, y_value) in enumerate(zip(x_values, y_values)):
                x_pos = map_x(x_value)
                y_pos = map_y(y_value)
                points.extend((x_pos, y_pos))

                if index + 1 < len(x_values):
                    next_x = map_x(x_values[index + 1])
                    points.extend((next_x, y_pos))

            if len(points) >= 4:
                self.canvas.create_line(*points, fill=color, width=self._line_width(emphasis=True), dash=dash or ())

    def _draw_bar_plot(self, payload: object) -> None:
        data = payload  # type: ignore[assignment]
        categories = data["categories"]
        values = data["values"]
        y_label = data["y_label"]
        bar_color = data["bar_color"]

        if not categories or not values:
            self._draw_message("No plot data available.")
            return

        valid_values = [value for value in values if value is not None]
        if not valid_values:
            self._draw_message("No valid values available for this batch plot.")
            return

        bottom_margin = self._bottom_margin_for_categories(categories)
        left, top, right, bottom = self._draw_axes(
            y_label,
            x_label="Fault Type",
            bottom_margin=bottom_margin,
        )
        max_value = max(valid_values)
        if max_value <= 0.0:
            max_value = 1.0
        max_value *= 1.12

        def map_y(value: float) -> float:
            return bottom - value * (bottom - top) / max_value

        bar_count = len(categories)
        slot_width = (right - left) / max(bar_count, 1)
        bar_width = slot_width * 0.58

        for tick in range(5):
            y_value = tick * max_value / 4.0
            y_pos = map_y(y_value)
            self.canvas.create_line(left - 4, y_pos, right, y_pos, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(left - 8, y_pos, text=f"{y_value:.0f}", anchor="e", fill="#506070", font=self._font("tick"))

        for index, (category, value) in enumerate(zip(categories, values)):
            center_x = left + (index + 0.5) * slot_width
            x0 = center_x - bar_width / 2.0
            x1 = center_x + bar_width / 2.0
            if value is None:
                self.canvas.create_text(center_x, bottom - 8, text="n/a", fill="#6a6a6a", font=self._font("bar_value"))
            else:
                y_top = map_y(value)
                self.canvas.create_rectangle(x0, y_top, x1, bottom, fill=bar_color, outline="#2f2f2f")
                self.canvas.create_text(center_x, y_top - 8, text=f"{value:.0f}", fill="#33404d", font=self._font("bar_value"))

            self.canvas.create_text(
                center_x,
                bottom + 14,
                text=category,
                anchor="n",
                fill="#506070",
                font=self._font("tick"),
                width=slot_width * 0.9,
            )

    def _draw_stacked_bar_plot(self, payload: object) -> None:
        data = payload  # type: ignore[assignment]
        categories = data["categories"]
        stacks = data["stacks"]
        y_label = data["y_label"]
        max_value = data["max_value"]
        x_label = data["x_label"]

        if not categories or not stacks:
            self._draw_message("No plot data available.")
            return

        legend_entries = [(label, color, None) for label, color, _ in stacks]
        legend_height = self._draw_legend(legend_entries, left=86, top=10, right=self._canvas_size()[0] - 16)
        bottom_margin = self._bottom_margin_for_categories(categories)
        left, top, right, bottom = self._draw_axes(
            y_label,
            x_label=x_label,
            top_margin=18 + legend_height,
            bottom_margin=bottom_margin,
        )

        if max_value <= 0.0:
            max_value = 1.0

        def map_y(value: float) -> float:
            return bottom - value * (bottom - top) / max_value

        slot_width = (right - left) / max(len(categories), 1)
        bar_width = slot_width * 0.58
        cumulative = [0.0 for _ in categories]

        for tick in range(5):
            tick_value = tick * max_value / 4.0
            y_pos = map_y(tick_value)
            label = f"{tick_value:.0f}" if max_value <= 100.0 else f"{tick_value:.1f}"
            self.canvas.create_line(left - 4, y_pos, right, y_pos, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(left - 8, y_pos, text=label, anchor="e", fill="#506070", font=self._font("tick"))

        for _label, color, values in stacks:
            for index, value in enumerate(values):
                safe_value = max(float(value), 0.0)
                center_x = left + (index + 0.5) * slot_width
                x0 = center_x - bar_width / 2.0
                x1 = center_x + bar_width / 2.0
                y0 = map_y(cumulative[index] + safe_value)
                y1 = map_y(cumulative[index])
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="#2f2f2f")
                cumulative[index] += safe_value

        for index, category in enumerate(categories):
            center_x = left + (index + 0.5) * slot_width
            total_value = cumulative[index]
            self.canvas.create_text(
                center_x,
                map_y(total_value) - 10,
                text=f"{total_value:.0f}",
                fill="#33404d",
                font=self._font("bar_value"),
            )
            self.canvas.create_text(
                center_x,
                bottom + 14,
                text=category,
                anchor="n",
                fill="#506070",
                font=self._font("tick"),
                width=slot_width * 0.9,
            )


class VirtualECUGui(tk.Tk):
    METRIC_NAMES = (
        "Final DTC",
        "Final Safe State",
        "Maximum Coolant Temperature",
        "Detection Latency",
        "Safe-State Latency",
    )
    EMPHASIZED_METRICS = {
        "Final DTC",
        "Final Safe State",
        "Maximum Coolant Temperature",
        "Detection Latency",
        "Safe-State Latency",
    }
    SNAPSHOT_METRIC_NAMES = (
        "Final DTC",
        "Final Safe State",
        "Maximum Coolant Temperature",
        "Detection Latency",
        "Safe-State Latency",
    )
    COMPARISON_PLOT_OPTIONS = (
        "Coolant Temperature Comparison",
        "Safe-State Comparison",
        "Fan Command / Actual Comparison",
    )
    RECOMMENDED_DEMO_COMPARISONS = (
        ("Baseline vs Fan Hot Stress", "baseline", "fan_stuck_hot_stress"),
        ("Baseline vs Calibration", "baseline", "calibration_memory_corruption"),
        ("Baseline vs Stale Sensor", "baseline", "stale_sensor_data_only"),
        ("Stale Mild vs Hot Stress", "stale_sensor_data_only", "stale_sensor_data_hot_stress"),
        ("Timing Stress vs Fan Hot Stress", "stale_sensor_data_hot_stress", "fan_stuck_hot_stress"),
    )
    BATCH_PLOT_OPTIONS = (
        "Mean Detection Latency",
        "Mean Safe-State Latency",
        "Mean Maximum Coolant Temperature",
        "Mean Safe-Mode Duration",
        "Final Safe-State Distribution",
    )
    BATCH_SAFE_STATE_COLORS = {
        "normal": "#7fbf7b",
        "precautionary_cooling": "#f2c14e",
        "limp_home": "#e07a5f",
        "controlled_shutdown": "#7b2d26",
    }

    def __init__(self) -> None:
        super().__init__()
        self.title("Virtual ECU Research GUI")
        self.geometry("1360x1020")
        self.minsize(1180, 920)

        self.executable = detect_executable()
        self.left_campaign = tk.StringVar(value="baseline")
        self.right_campaign = tk.StringVar(value="fan_stuck_hot_stress")
        self.presentation_mode = tk.BooleanVar(value=False)
        self.comparison_plot_choice = tk.StringVar(value=self.COMPARISON_PLOT_OPTIONS[0])
        self.batch_plot_choice = tk.StringVar(value=self.BATCH_PLOT_OPTIONS[0])
        self.status_text = tk.StringVar(value="Select two campaigns and run a comparison.")
        self.batch_status_text = tk.StringVar(value="Load a batch aggregate summary CSV to inspect sweep-level trends.")
        self.comparison_findings_var = tk.StringVar(value="Run a comparison to generate automatic findings.")
        self.comparison_interpretation_var = tk.StringVar(value="-")
        self.batch_findings_var = tk.StringVar(value="Load a batch aggregate summary CSV to generate automatic findings.")
        self.batch_interpretation_var = tk.StringVar(value="-")
        self.left_description_var = tk.StringVar(value="-")
        self.right_description_var = tk.StringVar(value="-")
        self.batch_csv_path = tk.StringVar(value=str(DEFAULT_BATCH_AGGREGATE_CSV))
        self.batch_run_count_var = tk.StringVar(value="-")
        self.batch_fault_classes_var = tk.StringVar(value="-")
        self.batch_fault_types_var = tk.StringVar(value="-")

        self.summary_vars = {
            "left": {name: tk.StringVar(value="-") for name in ("Campaign Name", "Fault Class", *self.METRIC_NAMES)},
            "right": {name: tk.StringVar(value="-") for name in ("Campaign Name", "Fault Class", *self.METRIC_NAMES)},
        }
        self.context_vars = {
            "left": {
                "Fault Class": tk.StringVar(value="-"),
                "Hardware Source": tk.StringVar(value="-"),
                "ECU Manifestation": tk.StringVar(value="-"),
            },
            "right": {
                "Fault Class": tk.StringVar(value="-"),
                "Hardware Source": tk.StringVar(value="-"),
                "ECU Manifestation": tk.StringVar(value="-"),
            },
        }
        self.metric_cells: Dict[str, Dict[str, Dict[str, tk.Widget]]] = {"left": {}, "right": {}}
        self.current_comparison: Dict[str, object] | None = None
        self.current_plot_results: Dict[str, object] | None = None
        self.batch_rows: List[Dict[str, str]] = []
        self.batch_table: ttk.Treeview | None = None
        self.batch_plot: PlotCanvas | None = None
        self.comparison_plot: PlotCanvas | None = None

        self._configure_style()
        self._build_layout()
        self._apply_presentation_mode()
        self._refresh_campaign_context()
        self._reset_summary_values()
        self._clear_batch_results()

        if self.executable is None:
            self.status_text.set(
                "Compiled virtual ECU executable not found. Build it first with 'make' or your local GCC toolchain."
            )
            self.run_compare_button.state(["disabled"])
            self.run_left_button.state(["disabled"])
            self.snapshot_button.state(["disabled"])
            self.export_button.state(["disabled"])

        if DEFAULT_BATCH_AGGREGATE_CSV.exists():
            self.load_batch_results()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.configure("Root.TFrame", background="#f4f6f8")
        style.configure("Panel.TFrame", background="#eef3f7")
        style.configure("Header.TLabel", font=("TkDefaultFont", 17, "bold"), background="#f4f6f8")
        style.configure("Subheader.TLabel", font=("TkDefaultFont", 10), foreground="#465564", background="#f4f6f8")
        style.configure("Section.TLabel", font=("TkDefaultFont", 12, "bold"))
        style.configure("FieldName.TLabel", font=("TkDefaultFont", 10, "bold"), foreground="#22313f")
        style.configure("FieldValue.TLabel", font=("TkDefaultFont", 10), foreground="#374553")
        style.configure("Hint.TLabel", font=("TkDefaultFont", 9), foreground="#4d5c69")
        style.configure("ColumnHeader.TLabel", font=("TkDefaultFont", 10, "bold"), foreground="#1d3448")
        style.configure("MetricLabel.TLabel", font=("TkDefaultFont", 10, "bold"), foreground="#1f3040")
        style.configure("Batch.Treeview", rowheight=26, font=("TkDefaultFont", 9))
        style.configure("Batch.Treeview.Heading", font=("TkDefaultFont", 9, "bold"))

    def _build_layout(self) -> None:
        self.configure(background="#f4f6f8")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, padding=(16, 14, 16, 10), style="Root.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=0)

        ttk.Label(header, text="Virtual ECU Research Explorer", style="Header.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Use campaign comparison for live fault-propagation demos and batch results for quick sweep-level inspection. The scripted analysis remains the paper-grade workflow.",
            style="Subheader.TLabel",
            wraplength=920,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(2, 8))

        header_controls = ttk.Frame(header, style="Root.TFrame")
        header_controls.grid(row=0, column=1, rowspan=2, sticky="ne")
        ttk.Checkbutton(
            header_controls,
            text="Presentation Mode",
            variable=self.presentation_mode,
            command=self._on_presentation_mode_toggled,
        ).grid(row=0, column=0, sticky="e")
        ttk.Label(
            header_controls,
            textvariable=self.status_text,
            foreground="#3d4b59",
            wraplength=360,
            justify="right",
        ).grid(row=1, column=0, sticky="e", pady=(8, 0))

        notebook = ttk.Notebook(self)
        notebook.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        summary_tab = ttk.Frame(notebook, padding=(4, 8, 4, 6), style="Root.TFrame")
        summary_tab.columnconfigure(0, weight=1)
        summary_tab.rowconfigure(1, weight=1)
        notebook.add(summary_tab, text="Comparison Summary")

        figures_tab = ttk.Frame(notebook, padding=(4, 8, 4, 6), style="Root.TFrame")
        figures_tab.columnconfigure(0, weight=1)
        figures_tab.rowconfigure(0, weight=1)
        notebook.add(figures_tab, text="Comparison Figures")

        batch_tab = ttk.Frame(notebook, padding=(4, 8, 4, 6), style="Root.TFrame")
        batch_tab.columnconfigure(0, weight=1)
        batch_tab.rowconfigure(3, weight=1)
        notebook.add(batch_tab, text="Batch Results")

        self._build_comparison_summary_tab(summary_tab)
        self._build_comparison_figures_tab(figures_tab)
        self._build_batch_tab(batch_tab)

    def _build_comparison_summary_tab(self, parent: ttk.Frame) -> None:
        selectors_area = ttk.Frame(parent, padding=(12, 0, 12, 12), style="Root.TFrame")
        selectors_area.grid(row=0, column=0, sticky="ew")
        selectors_area.columnconfigure(0, weight=1)
        selectors_area.columnconfigure(1, weight=1)
        selectors_area.columnconfigure(2, weight=0)

        self._build_selector_card(
            selectors_area,
            0,
            "Left Campaign",
            self.left_campaign,
            self.left_description_var,
            self._on_campaign_changed,
        )
        self._build_selector_card(
            selectors_area,
            1,
            "Right Campaign",
            self.right_campaign,
            self.right_description_var,
            self._on_campaign_changed,
        )

        actions = ttk.Frame(selectors_area, style="Root.TFrame")
        actions.grid(row=0, column=2, rowspan=2, sticky="ne", padx=(12, 0))

        self.run_compare_button = ttk.Button(actions, text="Run Comparison", command=self.run_comparison)
        self.run_compare_button.grid(row=0, column=0, sticky="e")
        self.run_left_button = ttk.Button(actions, text="Run Left Only", command=self.run_left_only)
        self.run_left_button.grid(row=1, column=0, sticky="e", pady=(8, 0))
        self.snapshot_button = ttk.Button(actions, text="Export Results Snapshot", command=self.export_results_snapshot)
        self.snapshot_button.grid(row=2, column=0, sticky="e", pady=(8, 0))
        self.snapshot_button.state(["disabled"])
        self.export_button = ttk.Button(actions, text="Export Comparison Report", command=self.export_current_comparison)
        self.export_button.grid(row=3, column=0, sticky="e", pady=(8, 0))
        self.export_button.state(["disabled"])

        self._build_recommended_demo_shortcuts(selectors_area)

        info_area = ttk.Frame(parent, padding=(12, 0, 12, 12), style="Root.TFrame")
        info_area.grid(row=1, column=0, sticky="ew")
        info_area.columnconfigure(0, weight=3)
        info_area.columnconfigure(1, weight=2)

        summary_frame = ttk.LabelFrame(info_area, text="Comparison Summary", padding=14)
        summary_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        summary_frame.columnconfigure(0, minsize=190)
        summary_frame.columnconfigure(1, weight=1)
        summary_frame.columnconfigure(2, weight=1)

        ttk.Label(summary_frame, text="", style="ColumnHeader.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(summary_frame, text="Left Run", style="ColumnHeader.TLabel").grid(row=0, column=1, sticky="w", pady=(0, 8))
        ttk.Label(summary_frame, text="Right Run", style="ColumnHeader.TLabel").grid(row=0, column=2, sticky="w", pady=(0, 8))

        summary_rows = ["Campaign Name", "Fault Class", *self.METRIC_NAMES]
        for row_index, metric_name in enumerate(summary_rows, start=1):
            ttk.Label(summary_frame, text=metric_name, style="MetricLabel.TLabel").grid(
                row=row_index, column=0, sticky="nw", padx=(0, 12), pady=4
            )
            self._add_metric_cell(summary_frame, row_index, 1, "left", metric_name)
            self._add_metric_cell(summary_frame, row_index, 2, "right", metric_name)

        ttk.Label(
            summary_frame,
            text="Comparison mode is the main research/demo view. Single-run mode remains available for a focused left-campaign inspection.",
            style="Hint.TLabel",
            wraplength=620,
            justify="left",
        ).grid(row=len(summary_rows) + 1, column=0, columnspan=3, sticky="w", pady=(10, 0))

        context_frame = ttk.LabelFrame(info_area, text="Campaign Context", padding=14)
        context_frame.grid(row=0, column=1, sticky="nsew")
        context_frame.columnconfigure(0, weight=1)
        context_frame.columnconfigure(1, weight=1)

        self._build_context_column(context_frame, 0, "Left Context", "left", LEFT_COLOR)
        self._build_context_column(context_frame, 1, "Right Context", "right", RIGHT_COLOR)

        findings_frame = ttk.LabelFrame(parent, text="Findings / Interpretation", padding=14)
        findings_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        findings_frame.columnconfigure(0, weight=1)
        self._build_findings_cards(
            findings_frame,
            self.comparison_findings_var,
            self.comparison_interpretation_var,
            wraplength=540,
        )

    def _build_comparison_figures_tab(self, parent: ttk.Frame) -> None:
        plots = ttk.Frame(parent, padding=(12, 8, 12, 12), style="Root.TFrame")
        plots.grid(row=0, column=0, sticky="nsew")
        plots.columnconfigure(0, weight=1)
        plots.rowconfigure(1, weight=1, minsize=700)

        plot_header = ttk.Frame(plots, style="Root.TFrame")
        plot_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        plot_header.columnconfigure(0, weight=0)
        plot_header.columnconfigure(1, weight=0)
        plot_header.columnconfigure(2, weight=1)

        ttk.Label(plot_header, text="Comparison Plot", style="FieldName.TLabel").grid(row=0, column=0, sticky="w")
        selector = ttk.Combobox(
            plot_header,
            textvariable=self.comparison_plot_choice,
            values=list(self.COMPARISON_PLOT_OPTIONS),
            state="readonly",
            width=34,
        )
        selector.grid(row=0, column=1, sticky="w", padx=(10, 0))
        selector.bind("<<ComboboxSelected>>", self._on_plot_selection_changed)
        ttk.Label(
            plot_header,
            text="Use this dedicated figures page for cleaner, presentation-friendly plots during live demos, thesis walkthroughs, and screenshots.",
            style="Hint.TLabel",
            wraplength=720,
            justify="left",
        ).grid(row=0, column=2, sticky="w", padx=(14, 0))

        self.comparison_plot = PlotCanvas(
            plots,
            self.comparison_plot_choice.get(),
            canvas_height=700,
        )
        self.comparison_plot.grid(row=1, column=0, sticky="nsew")
        self.comparison_plot.show_message("Run a comparison from the Comparison Summary page to display the selected plot here.")

    def _build_batch_tab(self, parent: ttk.Frame) -> None:
        controls = ttk.LabelFrame(parent, text="Batch Aggregate Summary", padding=14)
        controls.grid(row=0, column=0, sticky="ew", padx=12, pady=(0, 12))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Aggregate CSV", style="FieldName.TLabel").grid(row=0, column=0, sticky="w")
        path_entry = ttk.Entry(controls, textvariable=self.batch_csv_path)
        path_entry.grid(row=0, column=1, sticky="ew", padx=(10, 10))
        ttk.Button(controls, text="Browse", command=self.browse_batch_results).grid(row=0, column=2, sticky="e")
        ttk.Button(controls, text="Load Batch Results", command=self.load_batch_results).grid(
            row=0, column=3, sticky="e", padx=(8, 0)
        )

        ttk.Label(
            controls,
            text="This tab is a lightweight viewing layer for aggregate sweep results. Use the analysis scripts for publication tables and figures.",
            style="Hint.TLabel",
            wraplength=940,
            justify="left",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 4))
        ttk.Label(controls, textvariable=self.batch_status_text, style="Hint.TLabel", wraplength=940, justify="left").grid(
            row=2, column=0, columnspan=4, sticky="w"
        )

        overview = ttk.Frame(parent, padding=(12, 0, 12, 12), style="Root.TFrame")
        overview.grid(row=1, column=0, sticky="ew")
        overview.columnconfigure(0, weight=1)
        overview.columnconfigure(1, weight=1)
        overview.columnconfigure(2, weight=1)

        self._build_batch_stat_card(overview, 0, "Number of Runs", self.batch_run_count_var)
        self._build_batch_stat_card(overview, 1, "Fault Classes Present", self.batch_fault_classes_var)
        self._build_batch_stat_card(overview, 2, "Fault Types Present", self.batch_fault_types_var)

        findings_frame = ttk.LabelFrame(parent, text="Batch Findings / Interpretation", padding=14)
        findings_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        findings_frame.columnconfigure(0, weight=1)
        self._build_findings_cards(
            findings_frame,
            self.batch_findings_var,
            self.batch_interpretation_var,
            wraplength=540,
        )

        content = ttk.Frame(parent, padding=(12, 0, 12, 12), style="Root.TFrame")
        content.grid(row=3, column=0, sticky="nsew")
        content.columnconfigure(0, weight=5)
        content.columnconfigure(1, weight=4)
        content.rowconfigure(0, weight=1)

        table_frame = ttk.LabelFrame(content, text="Per-Fault-Type Averages", padding=10)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = (
            "fault_type",
            "runs",
            "mean_detection_latency",
            "mean_safe_state_latency",
            "mean_max_temp",
            "mean_safe_mode_duration",
            "dominant_safe_state",
        )
        self.batch_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=10,
            style="Batch.Treeview",
        )
        headings = {
            "fault_type": "Fault Type",
            "runs": "Runs",
            "mean_detection_latency": "Mean Detection [ms]",
            "mean_safe_state_latency": "Mean Safe State [ms]",
            "mean_max_temp": "Mean Max Temp [C]",
            "mean_safe_mode_duration": "Mean Safe-Mode [ms]",
            "dominant_safe_state": "Dominant Final State",
        }
        widths = {
            "fault_type": 190,
            "runs": 60,
            "mean_detection_latency": 120,
            "mean_safe_state_latency": 125,
            "mean_max_temp": 120,
            "mean_safe_mode_duration": 125,
            "dominant_safe_state": 150,
        }
        anchors = {
            "fault_type": tk.W,
            "runs": tk.CENTER,
            "mean_detection_latency": tk.CENTER,
            "mean_safe_state_latency": tk.CENTER,
            "mean_max_temp": tk.CENTER,
            "mean_safe_mode_duration": tk.CENTER,
            "dominant_safe_state": tk.CENTER,
        }
        for column_id in columns:
            self.batch_table.heading(column_id, text=headings[column_id])
            self.batch_table.column(column_id, width=widths[column_id], anchor=anchors[column_id], stretch=column_id == "fault_type")

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.batch_table.yview)
        self.batch_table.configure(yscrollcommand=scroll.set)
        self.batch_table.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        plot_frame = ttk.LabelFrame(content, text="Batch Comparison View", padding=10)
        plot_frame.grid(row=0, column=1, sticky="nsew")
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(2, weight=1, minsize=320)

        plot_header = ttk.Frame(plot_frame, style="Root.TFrame")
        plot_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        plot_header.columnconfigure(2, weight=1)

        ttk.Label(plot_header, text="Batch Plot", style="FieldName.TLabel").grid(row=0, column=0, sticky="w")
        selector = ttk.Combobox(
            plot_header,
            textvariable=self.batch_plot_choice,
            values=list(self.BATCH_PLOT_OPTIONS),
            state="readonly",
            width=31,
        )
        selector.grid(row=0, column=1, sticky="w", padx=(10, 0))
        selector.bind("<<ComboboxSelected>>", self._on_batch_plot_selection_changed)

        ttk.Label(
            plot_frame,
            text="Use the selector to switch between observability, thermal severity, and safe-state outcome views from the currently loaded aggregate summary.",
            style="Hint.TLabel",
            wraplength=360,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 8))
        self.batch_plot = PlotCanvas(plot_frame, self.batch_plot_choice.get(), canvas_height=300)
        self.batch_plot.grid(row=2, column=0, sticky="nsew")
        self.batch_plot.show_message("Load a batch aggregate summary CSV to view the sweep-level comparison.")

    def _build_selector_card(
        self,
        parent: ttk.Frame,
        column: int,
        title: str,
        variable: tk.StringVar,
        description_var: tk.StringVar,
        callback,
    ) -> None:
        card = ttk.Frame(parent, padding=(0, 0, 16 if column == 0 else 0, 0), style="Root.TFrame")
        card.grid(row=0, column=column, sticky="ew")
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text=title, style="FieldName.TLabel").grid(row=0, column=0, sticky="w")
        box = ttk.Combobox(
            card,
            textvariable=variable,
            values=[campaign_id for campaign_id, _label in CAMPAIGNS],
            state="readonly",
            width=32,
        )
        box.grid(row=0, column=1, sticky="w", padx=(10, 0))
        box.bind("<<ComboboxSelected>>", callback)

        ttk.Label(
            card,
            textvariable=description_var,
            style="Hint.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=1, column=1, sticky="w", pady=(6, 0))

    def _build_batch_stat_card(self, parent: ttk.Frame, column: int, title: str, variable: tk.StringVar) -> None:
        card = tk.Frame(parent, bg="#ffffff", bd=1, relief="solid", highlightthickness=0)
        card.grid(row=0, column=column, sticky="nsew", padx=(0, 10 if column < 2 else 0))
        tk.Label(
            card,
            text=title,
            bg="#ffffff",
            fg="#22313f",
            font=("TkDefaultFont", 10, "bold"),
            anchor="w",
            padx=12,
            pady=0,
        ).pack(fill="x", pady=(10, 2))
        tk.Label(
            card,
            textvariable=variable,
            bg="#ffffff",
            fg="#1f2e3b",
            font=("TkDefaultFont", 10, "bold"),
            justify="left",
            wraplength=300,
            anchor="w",
            padx=12,
            pady=10,
        ).pack(fill="x")

    def _build_findings_cards(
        self,
        parent: ttk.Frame,
        findings_var: tk.StringVar,
        interpretation_var: tk.StringVar,
        *,
        wraplength: int,
    ) -> None:
        cards = ttk.Frame(parent, style="Root.TFrame")
        cards.grid(row=0, column=0, sticky="ew")
        cards.columnconfigure(0, weight=3)
        cards.columnconfigure(1, weight=2)

        self._build_text_card(
            cards,
            0,
            "Key Findings",
            findings_var,
            wraplength=wraplength,
            body_font=("TkDefaultFont", 10, "bold"),
            body_fg="#22313f",
        )
        self._build_text_card(
            cards,
            1,
            "Interpretation",
            interpretation_var,
            wraplength=wraplength,
            body_font=("TkDefaultFont", 10),
            body_fg="#425160",
        )

    def _build_text_card(
        self,
        parent: ttk.Frame,
        column: int,
        title: str,
        variable: tk.StringVar,
        *,
        wraplength: int,
        body_font: Tuple[str, int] | Tuple[str, int, str],
        body_fg: str,
    ) -> None:
        card = tk.Frame(parent, bg="#ffffff", bd=1, relief="solid", highlightthickness=0)
        card.grid(row=0, column=column, sticky="nsew", padx=(0, 10 if column == 0 else 0))

        tk.Label(
            card,
            text=title,
            bg="#ffffff",
            fg="#1d3448",
            font=("TkDefaultFont", 10, "bold"),
            anchor="w",
            padx=14,
            pady=0,
        ).pack(fill="x", pady=(12, 4))
        tk.Label(
            card,
            textvariable=variable,
            bg="#ffffff",
            fg=body_fg,
            font=body_font,
            justify="left",
            wraplength=wraplength,
            anchor="w",
            padx=14,
            pady=12,
        ).pack(fill="x")

    def _build_recommended_demo_shortcuts(self, parent: ttk.Frame) -> None:
        shortcuts = ttk.LabelFrame(parent, text="Recommended Demo Comparisons", padding=12)
        shortcuts.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        shortcuts.columnconfigure(0, weight=1)
        shortcuts.columnconfigure(1, weight=1)
        shortcuts.columnconfigure(2, weight=1)

        ttk.Label(
            shortcuts,
            text="Use these one-click pairings for live walkthroughs of nominal, timing-fault, computation/memory, and severe actuation-fault behavior.",
            style="Hint.TLabel",
            wraplength=980,
            justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        for index, (label, left_campaign, right_campaign) in enumerate(self.RECOMMENDED_DEMO_COMPARISONS):
            ttk.Button(
                shortcuts,
                text=label,
                command=lambda left=left_campaign, right=right_campaign: self._apply_demo_comparison(left, right),
            ).grid(row=1 + index // 3, column=index % 3, sticky="ew", padx=(0, 8 if index % 3 < 2 else 0), pady=4)

    def _build_context_column(
        self,
        parent: ttk.Frame,
        column: int,
        title: str,
        slot: str,
        accent: str,
    ) -> None:
        block = tk.Frame(parent, bg="#ffffff", bd=1, relief="solid", highlightthickness=0)
        block.grid(row=0, column=column, sticky="nsew", padx=(0, 8 if column == 0 else 0))

        accent_bar = tk.Frame(block, bg=accent, width=12)
        accent_bar.pack(side="left", fill="y")

        body = tk.Frame(block, bg="#ffffff")
        body.pack(side="left", fill="both", expand=True)

        tk.Label(
            body,
            text=title,
            bg="#ffffff",
            fg="#1d3448",
            font=("TkDefaultFont", 10, "bold"),
            anchor="w",
            padx=14,
            pady=0,
        ).grid(row=0, column=0, sticky="w", pady=(14, 8))
        self._add_context_row(body, 1, "Fault Class", self.context_vars[slot]["Fault Class"])
        self._add_context_row(body, 2, "Hardware Source", self.context_vars[slot]["Hardware Source"])
        self._add_context_row(body, 3, "ECU Manifestation", self.context_vars[slot]["ECU Manifestation"])

    def _add_context_row(self, parent: tk.Frame, row: int, label: str, variable: tk.StringVar) -> None:
        tk.Label(
            parent,
            text=label,
            bg="#ffffff",
            fg="#4d5c69",
            font=("TkDefaultFont", 9, "bold"),
            anchor="w",
            padx=14,
            pady=0,
        ).grid(row=row, column=0, sticky="nw", pady=(0, 2))
        tk.Label(
            parent,
            textvariable=variable,
            bg="#ffffff",
            fg="#374553",
            font=("TkDefaultFont", 10),
            wraplength=325,
            justify="left",
            anchor="w",
            padx=14,
            pady=0,
        ).grid(row=row + 1, column=0, sticky="nw", pady=(0, 12))

    def _add_metric_cell(self, parent: ttk.Frame, row: int, column: int, slot: str, metric_name: str) -> None:
        frame = tk.Frame(parent, bg="#eef3f7", bd=1, relief="solid", highlightthickness=0)
        frame.grid(row=row, column=column, sticky="ew", padx=(0, 8 if column == 1 else 0), pady=4)

        value = tk.Label(
            frame,
            textvariable=self.summary_vars[slot][metric_name],
            bg="#eef3f7",
            fg="#1f2e3b",
            font=("TkDefaultFont", 10, "bold"),
            anchor="w",
            justify="left",
            wraplength=235,
            padx=10,
            pady=8,
        )
        value.pack(fill="x")

        self.metric_cells[slot][metric_name] = {"frame": frame, "value": value}

    def _on_campaign_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._refresh_campaign_context()
        self._reset_summary_values()

    def _apply_demo_comparison(self, left_campaign: str, right_campaign: str) -> None:
        self.left_campaign.set(left_campaign)
        self.right_campaign.set(right_campaign)
        self._refresh_campaign_context()
        self._reset_summary_values()
        self.status_text.set(f"Demo shortlist loaded: {left_campaign} vs {right_campaign}. Run comparison to inspect it.")

    def _on_presentation_mode_toggled(self) -> None:
        self._apply_presentation_mode()

    def _metric_font(self, metric_name: str) -> Tuple[str, int, str]:
        if metric_name in {"Campaign Name", "Fault Class"}:
            return ("TkDefaultFont", 10, "bold")
        if metric_name in self.EMPHASIZED_METRICS:
            return ("TkDefaultFont", 11, "bold")
        return ("TkDefaultFont", 10, "bold")

    def _metric_wraplength(self, metric_name: str) -> int:
        if metric_name in self.EMPHASIZED_METRICS:
            return 250
        return 235

    def _metric_padding(self, metric_name: str) -> Tuple[int, int]:
        if metric_name in self.EMPHASIZED_METRICS:
            return (12, 11)
        return (10, 8)

    def _metric_cell_colors(self, metric_name: str, value: str) -> Tuple[str, str]:
        if metric_name in {"Campaign Name", "Fault Class"}:
            return ("#eef3f7", "#1f2e3b")
        return metric_card_colors(metric_name, value)

    def _apply_presentation_mode(self) -> None:
        if self.comparison_plot is not None:
            self.comparison_plot.set_presentation_mode(self.presentation_mode.get())
        self._refresh_selected_plot()

    def _on_plot_selection_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._refresh_selected_plot()

    def _on_batch_plot_selection_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._refresh_batch_plot()

    def browse_batch_results(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select Batch Aggregate Summary CSV",
            initialdir=str(DEFAULT_BATCH_AGGREGATE_CSV.parent if DEFAULT_BATCH_AGGREGATE_CSV.parent.exists() else PROJECT_ROOT),
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if selected:
            self.batch_csv_path.set(selected)

    def load_batch_results(self) -> None:
        csv_path = Path(self.batch_csv_path.get()).expanduser()
        try:
            rows = read_csv_rows(csv_path)
        except FileNotFoundError:
            self._clear_batch_results()
            self.batch_status_text.set(f"Batch aggregate CSV not found: {csv_path}")
            return
        except (OSError, csv.Error) as exc:
            self._clear_batch_results()
            self.batch_status_text.set(f"Failed to load batch aggregate CSV: {exc}")
            return

        if not rows:
            self._clear_batch_results()
            self.batch_status_text.set(f"Batch aggregate CSV is empty: {csv_path}")
            return

        self._apply_batch_results(csv_path, rows)

    def _clear_batch_results(self) -> None:
        self.batch_rows = []
        self.batch_run_count_var.set("-")
        self.batch_fault_classes_var.set("-")
        self.batch_fault_types_var.set("-")
        self.batch_findings_var.set("Load a batch aggregate summary CSV to generate automatic findings.")
        self.batch_interpretation_var.set("-")

        if self.batch_table is not None:
            for item_id in self.batch_table.get_children():
                self.batch_table.delete(item_id)

        if self.batch_plot is not None:
            self.batch_plot.set_title(self.batch_plot_choice.get())
            self.batch_plot.show_message("Load a batch aggregate summary CSV to view the sweep-level comparison.")

    def _apply_batch_results(self, csv_path: Path, rows: Sequence[Dict[str, str]]) -> None:
        self.batch_rows = list(rows)

        fault_classes = sorted({row["fault_class"] for row in rows if row.get("fault_class")})
        fault_types = self._ordered_fault_types(rows)
        self.batch_run_count_var.set(str(len(rows)))
        self.batch_fault_classes_var.set(", ".join(fault_classes) if fault_classes else "n/a")
        self.batch_fault_types_var.set(
            ", ".join(FAULT_TYPE_DISPLAY.get(fault_type, fault_type) for fault_type in fault_types) if fault_types else "n/a"
        )

        self._populate_batch_table(rows, fault_types)
        self.batch_status_text.set(f"Loaded {len(rows)} batch runs from {csv_path}")
        self._update_batch_findings(rows)
        self._refresh_batch_plot()

    def _ordered_fault_types(self, rows: Sequence[Dict[str, str]]) -> List[str]:
        present = {row["fault_type"] for row in rows if row.get("fault_type")}
        ordered = [fault_type for fault_type in FAULT_TYPE_ORDER if fault_type in present]
        extras = sorted(present - set(ordered))
        return ordered + extras

    def _populate_batch_table(self, rows: Sequence[Dict[str, str]], fault_types: Sequence[str]) -> None:
        if self.batch_table is None:
            return

        for item_id in self.batch_table.get_children():
            self.batch_table.delete(item_id)

        for fault_type in fault_types:
            type_rows = [row for row in rows if row["fault_type"] == fault_type]
            detection_values = [
                value
                for value in (int_or_none(row.get("detection_latency_ms", "")) for row in type_rows)
                if value is not None
            ]
            safe_state_latency_values = [
                value
                for value in (int_or_none(row.get("safe_state_latency_ms", "")) for row in type_rows)
                if value is not None
            ]
            max_temp_values = [
                value
                for value in (float_or_none(row.get("max_coolant_temperature_c", "")) for row in type_rows)
                if value is not None
            ]
            safe_mode_values = [
                value
                for value in (int_or_none(row.get("safe_mode_duration_ms", "")) for row in type_rows)
                if value is not None
            ]
            dominant_state = mode_or_none(row.get("final_safe_state", "") for row in type_rows)

            self.batch_table.insert(
                "",
                "end",
                values=(
                    FAULT_TYPE_DISPLAY.get(fault_type, fault_type),
                    str(len(type_rows)),
                    self._format_batch_number(mean_or_none(detection_values), decimals=1),
                    self._format_batch_number(mean_or_none(safe_state_latency_values), decimals=1),
                    self._format_batch_number(mean_or_none(max_temp_values), decimals=2),
                    self._format_batch_number(mean_or_none(safe_mode_values), decimals=1),
                    SAFE_STATE_LABELS.get(dominant_state, dominant_state),
                ),
            )

    def _refresh_batch_plot(self) -> None:
        if self.batch_plot is None:
            return

        self.batch_plot.set_title(self.batch_plot_choice.get())

        if not self.batch_rows:
            self.batch_plot.show_message("Load a batch aggregate summary CSV to view the sweep-level comparison.")
            return

        fault_types = self._ordered_fault_types(self.batch_rows)
        self._update_batch_plot(self.batch_rows, fault_types)

    def _batch_metric_values(
        self,
        rows: Sequence[Dict[str, str]],
        fault_type: str,
        column: str,
    ) -> List[float]:
        values: List[float] = []

        for row in rows:
            if row["fault_type"] != fault_type:
                continue

            if column == "max_coolant_temperature_c":
                parsed = float_or_none(row.get(column, ""))
            else:
                parsed = int_or_none(row.get(column, ""))

            if parsed is not None:
                values.append(float(parsed))

        return values

    def _update_batch_plot(self, rows: Sequence[Dict[str, str]], fault_types: Sequence[str]) -> None:
        if self.batch_plot is None:
            return

        selected_plot = self.batch_plot_choice.get()
        categories: List[str] = []
        values: List[float | None] = []

        plot_definitions = {
            "Mean Detection Latency": (
                "detection_latency_ms",
                "Mean Detection [ms]",
                "#5077b8",
                False,
            ),
            "Mean Safe-State Latency": (
                "safe_state_latency_ms",
                "Mean Safe-State [ms]",
                "#7a6fd0",
                True,
            ),
            "Mean Maximum Coolant Temperature": (
                "max_coolant_temperature_c",
                "Mean Max Temp [C]",
                "#cf6c54",
                False,
            ),
            "Mean Safe-Mode Duration": (
                "safe_mode_duration_ms",
                "Mean Safe-Mode [ms]",
                "#4c9f92",
                True,
            ),
        }

        if selected_plot == "Final Safe-State Distribution":
            self._update_batch_safe_state_distribution(rows, fault_types)
            return

        if selected_plot not in plot_definitions:
            self.batch_plot.show_message("Unknown batch plot selection.")
            return

        column, y_label, bar_color, skip_baseline_without_values = plot_definitions[selected_plot]

        for fault_type in fault_types:
            metric_values = self._batch_metric_values(rows, fault_type, column)
            mean_value = mean_or_none(metric_values)
            if fault_type == "none" and mean_value is None and skip_baseline_without_values:
                continue
            categories.append(FAULT_TYPE_DISPLAY.get(fault_type, fault_type))
            values.append(mean_value)

        if not categories:
            self.batch_plot.show_message(f"No valid values were found for {selected_plot.lower()} in this aggregate summary.")
            return

        self.batch_plot.plot_bars(
            categories,
            values,
            y_label=y_label,
            bar_color=bar_color,
        )

    def _update_batch_safe_state_distribution(
        self,
        rows: Sequence[Dict[str, str]],
        fault_types: Sequence[str],
    ) -> None:
        if self.batch_plot is None:
            return

        categories: List[str] = []
        stacks = {
            "normal": [],
            "precautionary_cooling": [],
            "limp_home": [],
            "controlled_shutdown": [],
        }

        for fault_type in fault_types:
            type_rows = [row for row in rows if row["fault_type"] == fault_type]
            if not type_rows:
                continue

            categories.append(FAULT_TYPE_DISPLAY.get(fault_type, fault_type))
            total_runs = float(len(type_rows))
            for state in stacks:
                count = sum(1 for row in type_rows if row.get("final_safe_state") == state)
                stacks[state].append((100.0 * count) / total_runs)

        if not categories:
            self.batch_plot.show_message("No final safe-state data was found in this aggregate summary.")
            return

        self.batch_plot.plot_stacked_bars(
            categories,
            [
                (SAFE_STATE_LABELS[state], self.BATCH_SAFE_STATE_COLORS[state], stacks[state])
                for state in ("normal", "precautionary_cooling", "limp_home", "controlled_shutdown")
            ],
            y_label="Outcome Share [%]",
            max_value=100.0,
        )

    def _format_batch_number(self, value: float | None, decimals: int = 1) -> str:
        if value is None:
            return "n/a"
        return f"{value:.{decimals}f}"

    def _refresh_campaign_context(self) -> None:
        for slot, campaign_var, description_var in (
            ("left", self.left_campaign, self.left_description_var),
            ("right", self.right_campaign, self.right_description_var),
        ):
            story = campaign_story(campaign_var.get())
            description_var.set(story["description"])
            self.summary_vars[slot]["Campaign Name"].set(story["campaign_name"])
            self.summary_vars[slot]["Fault Class"].set(story["fault_class"])
            self.context_vars[slot]["Fault Class"].set(story["fault_class"])
            self.context_vars[slot]["Hardware Source"].set(story["hardware_source"])
            self.context_vars[slot]["ECU Manifestation"].set(story["ecu_manifestation"])

    def _reset_summary_values(self) -> None:
        self.current_comparison = None
        self.current_plot_results = None
        self.snapshot_button.state(["disabled"])
        self.export_button.state(["disabled"])
        self.comparison_findings_var.set("Run a comparison to generate automatic findings.")
        self.comparison_interpretation_var.set("-")
        for slot in ("left", "right"):
            for metric_name in self.METRIC_NAMES:
                self.summary_vars[slot][metric_name].set("-")
        self._refresh_metric_cells()
        if self.comparison_plot is not None:
            self.comparison_plot.set_title(self.comparison_plot_choice.get())
            self.comparison_plot.show_message("Run a comparison from the Comparison Summary page to display the selected plot here.")

    def run_left_only(self) -> None:
        self._run_campaigns(include_right=False)

    def run_comparison(self) -> None:
        self._run_campaigns(include_right=True)

    def _run_campaigns(self, include_right: bool) -> None:
        if self.executable is None:
            messagebox.showerror(
                "Executable Not Found",
                "The compiled virtual ECU executable was not found. Build it first with 'make'.",
            )
            return

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        left_campaign = self.left_campaign.get()
        right_campaign = self.right_campaign.get()
        self.status_text.set(
            f"Running comparison: {left_campaign} vs {right_campaign}..."
            if include_right else f"Running left campaign: {left_campaign}..."
        )
        self.run_compare_button.state(["disabled"])
        self.run_left_button.state(["disabled"])
        self.snapshot_button.state(["disabled"])
        self.export_button.state(["disabled"])

        worker = threading.Thread(
            target=self._run_campaigns_worker,
            args=(include_right,),
            daemon=True,
        )
        worker.start()

    def _run_single_campaign(self, campaign_id: str, slot: str) -> Dict[str, object]:
        log_path = campaign_log_path(campaign_id, slot)
        summary_path = summary_path_for(log_path)
        command = [str(self.executable), str(log_path), campaign_id]

        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout or "Unknown simulator failure.")

        raw_rows = read_csv_rows(log_path)
        summary_rows = read_csv_rows(summary_path)
        if not raw_rows or not summary_rows:
            raise RuntimeError("The simulator completed but did not generate readable CSV data.")

        return {
            "campaign_id": campaign_id,
            "raw_rows": raw_rows,
            "summary_row": summary_rows[0],
        }

    def _run_campaigns_worker(self, include_right: bool) -> None:
        try:
            left_result = self._run_single_campaign(self.left_campaign.get(), "left")
            right_result = self._run_single_campaign(self.right_campaign.get(), "right") if include_right else None
        except OSError as exc:
            message = f"Failed to run simulator: {exc}"
            self.after(0, lambda msg=message: self._show_error(msg))
            return
        except (RuntimeError, csv.Error) as exc:
            message = str(exc)
            self.after(0, lambda msg=message: self._show_error(msg))
            return

        self.after(0, lambda: self._apply_results(left_result, right_result))

    def _show_error(self, message: str) -> None:
        self.status_text.set("Run failed.")
        self.run_compare_button.state(["!disabled"])
        self.run_left_button.state(["!disabled"])
        self.snapshot_button.state(["disabled"])
        self.export_button.state(["disabled"])
        messagebox.showerror("Virtual ECU Run Failed", message)

    def _apply_results(
        self,
        left_result: Dict[str, object],
        right_result: Dict[str, object] | None,
    ) -> None:
        self.run_compare_button.state(["!disabled"])
        self.run_left_button.state(["!disabled"])

        left_campaign = str(left_result["campaign_id"])
        self._apply_summary_slot("left", left_campaign, left_result["raw_rows"], left_result["summary_row"])

        if right_result is not None:
            right_campaign = str(right_result["campaign_id"])
            self._apply_summary_slot("right", right_campaign, right_result["raw_rows"], right_result["summary_row"])
            self.status_text.set(f"Loaded comparison: {left_campaign} vs {right_campaign}.")
            self.current_comparison = {
                "left": left_result,
                "right": right_result,
            }
            self.snapshot_button.state(["!disabled"])
            self.export_button.state(["!disabled"])
        else:
            self._clear_slot("right")
            self.status_text.set(f"Loaded left campaign: {left_campaign}.")
            self.current_comparison = None
            self.snapshot_button.state(["disabled"])
            self.export_button.state(["disabled"])

        self.current_plot_results = {
            "left": left_result,
            "right": right_result,
        }
        self._refresh_metric_cells()
        self._update_comparison_findings(left_result, right_result)
        self._refresh_selected_plot()

    def _update_comparison_findings(
        self,
        left_result: Dict[str, object],
        right_result: Dict[str, object] | None,
    ) -> None:
        if right_result is None:
            self.comparison_findings_var.set("Findings become available after a left-versus-right comparison run.")
            self.comparison_interpretation_var.set("-")
            return

        left_name = self.summary_vars["left"]["Campaign Name"].get()
        right_name = self.summary_vars["right"]["Campaign Name"].get()
        left_summary = left_result["summary_row"]  # type: ignore[assignment]
        right_summary = right_result["summary_row"]  # type: ignore[assignment]

        finding_lines, interpretation_lines = comparison_findings(left_name, left_summary, right_name, right_summary)
        self.comparison_findings_var.set("\n".join(f"- {line}" for line in finding_lines))
        self.comparison_interpretation_var.set("\n".join(interpretation_lines))

    def _update_batch_findings(self, rows: Sequence[Dict[str, str]]) -> None:
        finding_lines, interpretation_lines = batch_findings(rows)
        self.batch_findings_var.set("\n".join(f"- {line}" for line in finding_lines))
        self.batch_interpretation_var.set("\n".join(interpretation_lines))

    def _apply_summary_slot(
        self,
        slot: str,
        campaign_id: str,
        raw_rows: object,
        summary_row: object,
    ) -> None:
        rows = raw_rows  # type: ignore[assignment]
        summary = summary_row  # type: ignore[assignment]
        first_row = rows[0]

        self.summary_vars[slot]["Campaign Name"].set(summary.get("campaign_label", campaign_id))
        self.summary_vars[slot]["Fault Class"].set(summarize_fault_class(campaign_id, first_row))
        self.summary_vars[slot]["Final DTC"].set(summary.get("final_primary_dtc_label", "none"))
        self.summary_vars[slot]["Final Safe State"].set(summary.get("final_safe_state_label", "normal"))
        self.summary_vars[slot]["Maximum Coolant Temperature"].set(
            format_temperature(summary.get("max_coolant_temp_c", ""))
        )
        self.summary_vars[slot]["Detection Latency"].set(
            format_latency(summary.get("detection_latency_ms", ""))
        )
        self.summary_vars[slot]["Safe-State Latency"].set(
            format_latency(summary.get("safe_state_latency_ms", ""))
        )

    def _clear_slot(self, slot: str) -> None:
        story = campaign_story(self.right_campaign.get() if slot == "right" else self.left_campaign.get())
        self.summary_vars[slot]["Campaign Name"].set(story["campaign_name"])
        self.summary_vars[slot]["Fault Class"].set(story["fault_class"])
        for metric_name in self.METRIC_NAMES:
            self.summary_vars[slot][metric_name].set("-")

    def _refresh_metric_cells(self) -> None:
        for slot in ("left", "right"):
            for metric_name, cell in self.metric_cells[slot].items():
                background, foreground = self._metric_cell_colors(metric_name, self.summary_vars[slot][metric_name].get())
                cell = self.metric_cells[slot][metric_name]
                frame = cell["frame"]
                value = cell["value"]
                x_padding, y_padding = self._metric_padding(metric_name)
                frame.configure(bg=background)
                value.configure(
                    bg=background,
                    fg=foreground,
                    font=self._metric_font(metric_name),
                    wraplength=self._metric_wraplength(metric_name),
                    padx=x_padding,
                    pady=y_padding,
                )

    def _refresh_selected_plot(self) -> None:
        if self.comparison_plot is None:
            return

        selected_plot = self.comparison_plot_choice.get()
        self.comparison_plot.set_title(selected_plot)

        if self.current_plot_results is None:
            self.comparison_plot.show_message("Run a comparison from the Comparison Summary page to display the selected plot here.")
            return

        left_result = self.current_plot_results["left"]  # type: ignore[index]
        right_result = self.current_plot_results["right"]  # type: ignore[index]
        self._update_plots(left_result, right_result, selected_plot)

    def _update_plots(
        self,
        left_result: Dict[str, object],
        right_result: Dict[str, object] | None,
        selected_plot: str,
    ) -> None:
        if self.comparison_plot is None:
            return

        left_rows = left_result["raw_rows"]  # type: ignore[assignment]
        left_label = self.summary_vars["left"]["Campaign Name"].get()
        right_rows = right_result["raw_rows"] if right_result is not None else None  # type: ignore[assignment]

        if selected_plot == "Coolant Temperature Comparison":
            coolant_series = [
                (
                    left_label,
                    LEFT_COLOR,
                    float_series(left_rows, "time_s"),
                    float_series(left_rows, "coolant_temp_true_c"),
                    LEFT_DASH,
                )
            ]

            if right_rows is not None:
                coolant_series.append(
                    (
                        self.summary_vars["right"]["Campaign Name"].get(),
                        RIGHT_COLOR,
                        float_series(right_rows, "time_s"),
                        float_series(right_rows, "coolant_temp_true_c"),
                        RIGHT_DASH,
                    )
                )

            self.comparison_plot.plot_lines(
                coolant_series,
                y_label="Temp [C]",
                threshold_lines=((108.0, "#8c6b2d", "Warning"), (115.0, "#7b4d57", "Critical")),
            )
            return

        if selected_plot == "Safe-State Comparison":
            safe_series = [
                (
                    left_label,
                    LEFT_COLOR,
                    float_series(left_rows, "time_s"),
                    int_series(left_rows, "safe_state_id"),
                    LEFT_DASH,
                )
            ]

            if right_rows is not None:
                safe_series.append(
                    (
                        self.summary_vars["right"]["Campaign Name"].get(),
                        RIGHT_COLOR,
                        float_series(right_rows, "time_s"),
                        int_series(right_rows, "safe_state_id"),
                        RIGHT_DASH,
                    )
                )

            self.comparison_plot.plot_step_comparison(
                safe_series,
                y_label="State",
                tick_labels=SAFE_STATE_LABELS,
            )
            return

        fan_series = [
            (
                f"{left_label} command",
                LEFT_COLOR,
                float_series(left_rows, "time_s"),
                float_series(left_rows, "fan_command"),
                LEFT_DASH,
            ),
            (
                f"{left_label} actual",
                "#7d1f17",
                float_series(left_rows, "time_s"),
                float_series(left_rows, "fan_actual"),
                (2, 3),
            ),
        ]
        left_permanent = "permanent" in event_behaviors(left_rows[0])
        right_permanent = False

        if right_rows is not None:
            right_label = self.summary_vars["right"]["Campaign Name"].get()
            right_permanent = "permanent" in event_behaviors(right_rows[0])
            fan_series.extend(
                (
                    (
                        f"{right_label} command",
                        RIGHT_COLOR,
                        float_series(right_rows, "time_s"),
                        float_series(right_rows, "fan_command"),
                        RIGHT_DASH,
                    ),
                    (
                        f"{right_label} actual",
                        "#5e7fb0",
                        float_series(right_rows, "time_s"),
                        float_series(right_rows, "fan_actual"),
                        (8, 3, 2, 3),
                    ),
                )
            )

        if left_permanent or right_permanent:
            self.comparison_plot.plot_lines(
                fan_series,
                y_label="Fan [-]",
                y_min=0.0,
                y_max=1.0,
            )
        else:
            self.comparison_plot.show_message(
                "Fan Command / Actual Comparison is only meaningful for campaigns with a permanent-fault phase. Neither selected run contains one."
            )

    def export_current_comparison(self) -> None:
        if self.current_comparison is None:
            messagebox.showinfo(
                "No Comparison Loaded",
                "Run a left-versus-right comparison first, then export the current report.",
            )
            return

        left_result = self.current_comparison["left"]  # type: ignore[index]
        right_result = self.current_comparison["right"]  # type: ignore[index]
        left_campaign_id = str(left_result["campaign_id"])
        right_campaign_id = str(right_result["campaign_id"])

        export_dir = comparison_export_dir(left_campaign_id, right_campaign_id)
        export_dir.mkdir(parents=True, exist_ok=True)
        os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

        report_rows = [
            {"field": "left_campaign_id", "left": left_campaign_id, "right": ""},
            {"field": "right_campaign_id", "left": right_campaign_id, "right": ""},
            {"field": "left_fault_class", "left": self.summary_vars["left"]["Fault Class"].get(), "right": ""},
            {"field": "right_fault_class", "left": self.summary_vars["right"]["Fault Class"].get(), "right": ""},
        ]

        for metric_name in self.METRIC_NAMES:
            report_rows.append(
                {
                    "field": metric_name.lower().replace(" ", "_"),
                    "left": self.summary_vars["left"][metric_name].get(),
                    "right": self.summary_vars["right"][metric_name].get(),
                }
            )

        write_report_csv(export_dir / "comparison_summary.csv", report_rows)

        with (export_dir / "comparison_summary.txt").open("w", encoding="utf-8") as handle:
            handle.write("Virtual ECU Comparison Report\n")
            handle.write(f"Left campaign: {left_campaign_id}\n")
            handle.write(f"Right campaign: {right_campaign_id}\n")
            handle.write(f"Left fault class: {self.summary_vars['left']['Fault Class'].get()}\n")
            handle.write(f"Right fault class: {self.summary_vars['right']['Fault Class'].get()}\n\n")
            for metric_name in self.METRIC_NAMES:
                handle.write(
                    f"{metric_name}: left={self.summary_vars['left'][metric_name].get()}, "
                    f"right={self.summary_vars['right'][metric_name].get()}\n"
                )

        left_rows = left_result["raw_rows"]  # type: ignore[index]
        right_rows = right_result["raw_rows"]  # type: ignore[index]
        left_label = self.summary_vars["left"]["Campaign Name"].get()
        right_label = self.summary_vars["right"]["Campaign Name"].get()

        save_coolant_comparison_plot(
            left_label,
            left_rows,
            right_label,
            right_rows,
            export_dir / "coolant_temperature_comparison.png",
        )
        save_safe_state_comparison_plot(
            left_label,
            left_rows,
            right_label,
            right_rows,
            export_dir / "safe_state_comparison.png",
        )

        left_permanent = "permanent" in event_behaviors(left_rows[0])
        right_permanent = "permanent" in event_behaviors(right_rows[0])
        if left_permanent or right_permanent:
            save_fan_comparison_plot(
                left_label,
                left_rows,
                right_label,
                right_rows,
                export_dir / "fan_comparison.png",
            )

        self.status_text.set(f"Exported comparison report to {export_dir}")
        messagebox.showinfo(
            "Comparison Exported",
            f"Saved the comparison report and plot images to:\n{export_dir}",
        )

    def export_results_snapshot(self) -> None:
        if self.current_comparison is None:
            messagebox.showinfo(
                "No Comparison Loaded",
                "Run a left-versus-right comparison first, then export the current results snapshot.",
            )
            return

        left_result = self.current_comparison["left"]  # type: ignore[index]
        right_result = self.current_comparison["right"]  # type: ignore[index]
        left_campaign_id = str(left_result["campaign_id"])
        right_campaign_id = str(right_result["campaign_id"])
        export_dir = snapshot_export_dir(left_campaign_id, right_campaign_id)

        metrics = []
        for metric_name in self.SNAPSHOT_METRIC_NAMES:
            metrics.append(
                (
                    metric_name,
                    {
                        "left": self.summary_vars["left"][metric_name].get(),
                        "right": self.summary_vars["right"][metric_name].get(),
                    },
                )
            )

        finding_lines = [
            line[2:] if line.startswith("- ") else line
            for line in self.comparison_findings_var.get().splitlines()
            if line.strip()
        ]
        interpretation_lines = [line for line in self.comparison_interpretation_var.get().splitlines() if line.strip() and line.strip() != "-"]

        snapshot = {
            "left_campaign_id": left_campaign_id,
            "right_campaign_id": right_campaign_id,
            "left_campaign_name": self.summary_vars["left"]["Campaign Name"].get(),
            "right_campaign_name": self.summary_vars["right"]["Campaign Name"].get(),
            "left_fault_class": self.summary_vars["left"]["Fault Class"].get(),
            "right_fault_class": self.summary_vars["right"]["Fault Class"].get(),
            "metrics": metrics,
            "findings": finding_lines,
            "interpretation": interpretation_lines,
        }

        generated_files = write_snapshot_bundle(export_dir, snapshot)
        self.status_text.set(f"Exported results snapshot to {export_dir}")
        messagebox.showinfo(
            "Results Snapshot Exported",
            "Saved the presentation-ready snapshot bundle to:\n"
            f"{export_dir}\n\n"
            + "\n".join(str(path.name) for path in generated_files),
        )


def main() -> None:
    app = VirtualECUGui()
    app.mainloop()


if __name__ == "__main__":
    main()
