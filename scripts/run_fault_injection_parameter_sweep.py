#!/usr/bin/env python3
"""Run a deterministic fault-injection and HT-like parameter sensitivity study."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "fault_injection_parameter_sweep"
DEFAULT_EXECUTABLE = PROJECT_ROOT / "virtual_ecu"
SIMULATION_DURATION_MS = 120000
OBSERVE_ONLY = "observe_only"

DETECTORS = (
    "builtin_ecu",
    "threshold",
    "ewma",
    "cusum",
    "thermal_observer",
    "kalman_filter",
    "adaptive_kalman_filter",
    "hybrid_adaptive_kalman",
)
DETECTOR_NAMES = {
    "builtin_ecu": "Built-in ECU diagnostics",
    "threshold": "Threshold",
    "ewma": "EWMA",
    "cusum": "CUSUM",
    "thermal_observer": "Thermal observer",
    "kalman_filter": "Kalman filter",
    "adaptive_kalman_filter": "Adaptive Kalman filter",
    "hybrid_adaptive_kalman": "Hybrid Adaptive Kalman",
}


@dataclass(frozen=True)
class Event:
    fault_type: str
    start_ms: int
    duration_ms: int
    behavior: str
    parameter: float


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    scenario_name: str
    scenario_group: str
    fault_type: str
    security_group: str
    parameter_name: str
    parameter_value: str
    parameter_value_numeric: float | None
    severity_level: str
    timing_label: str
    activation_time_ms: int
    duration_ms: int | None
    events: tuple[Event, ...]
    notes: str = ""


EVENT_COLUMNS = (
    "scenario_id",
    "scenario_name",
    "scenario_group",
    "fault_type",
    "security_group",
    "parameter_name",
    "parameter_value",
    "parameter_value_numeric",
    "severity_level",
    "timing_label",
    "activation_time_ms",
    "duration_ms",
    "detector_id",
    "detector_name",
    "event_detected",
    "first_alarm_time_ms",
    "detection_latency_ms",
    "missed_detection",
    "clean_alarm",
    "max_coolant_temp",
    "final_safety_state",
    "runtime_detection_label",
    "raw_csv",
    "summary_csv",
    "notes",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run actual Virtual ECU simulations across a bounded deterministic "
            "fault and representative HT-like parameter grid."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true", help="Run the compact validation grid.")
    mode.add_argument("--full", action="store_true", help="Run the largest supported grid.")
    parser.add_argument("--limit", type=int, default=None, metavar="N", help="Run the first N deterministic event variants plus the clean reference.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--executable", type=Path, default=DEFAULT_EXECUTABLE)
    parser.add_argument("--skip-existing", action="store_true", help="Reuse a detector run only when both expected raw and summary CSV files exist.")
    parser.add_argument("--seed", type=int, default=0, help="Recorded for reproducibility; the current grid uses no randomization.")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    return args


def slug_number(value: float | int) -> str:
    return f"{value:g}".replace("-", "neg").replace(".", "p")


def add_single(
    scenarios: List[Scenario],
    *,
    prefix: str,
    name: str,
    group: str,
    fault_type: str,
    security_group: str,
    parameter_name: str,
    parameter_value: float,
    applied_parameter: float,
    severity: str,
    timing: str,
    start_ms: int,
    duration_ms: int,
    behavior: str,
    notes: str = "",
) -> None:
    scenarios.append(
        Scenario(
            scenario_id=f"{prefix}_{slug_number(parameter_value)}_{timing}",
            scenario_name=name,
            scenario_group=group,
            fault_type=fault_type,
            security_group=security_group,
            parameter_name=parameter_name,
            parameter_value=f"{parameter_value:g}",
            parameter_value_numeric=float(parameter_value),
            severity_level=severity,
            timing_label=timing,
            activation_time_ms=start_ms,
            duration_ms=None if duration_ms == 0 else duration_ms,
            events=(Event(fault_type, start_ms, duration_ms, behavior, applied_parameter),),
            notes=notes,
        )
    )


def build_scenarios(mode: str) -> List[Scenario]:
    """Build the ordered grid. Multi-event stages do not overlap in the C scheduler."""
    scenarios: List[Scenario] = [
        Scenario(
            "clean_reference",
            "Clean nominal reference",
            "clean_reference",
            "none",
            "none",
            "none",
            "0",
            0.0,
            "none",
            "none",
            -1,
            None,
            (),
            "No injected event; used only to count clean alarms.",
        )
    ]
    timings = {"early": 25000, "mid": 50000, "late": 75000}
    timing_items = list(timings.items()) if mode != "quick" else [("early", 25000), ("late", 75000)]

    bias_values = ((2, "very_low"), (4, "low"), (6, "medium"), (8, "high"), (10, "very_high"), (12, "maximum"))
    if mode == "quick":
        bias_values = (bias_values[0], bias_values[2], bias_values[-1])
    for value, severity in bias_values:
        for timing, start in timing_items:
            add_single(
                scenarios,
                prefix="sensor_bias_c",
                name=f"Coolant sensor bias {value} C ({timing})",
                group="sensor_bias",
                fault_type="sensor_bias",
                security_group="conventional_fault",
                parameter_name="bias_amplitude_c",
                parameter_value=value,
                applied_parameter=value,
                severity=severity,
                timing=timing,
                start_ms=start,
                duration_ms=15000,
                behavior="transient",
            )

    stale_levels = ((1000, 12000, "short"), (5000, 30000, "medium"), (15000, 45000, "long"))
    for hold_ms, active_ms, severity in stale_levels:
        for timing, start in timing_items:
            duration = min(active_ms, SIMULATION_DURATION_MS - start - 5000)
            add_single(
                scenarios,
                prefix="stale_hold_ms",
                name=f"Stale sensor {severity} hold ({timing})",
                group="stale_sensor",
                fault_type="stale_sensor_data",
                security_group="conventional_fault",
                parameter_name="stale_hold_ms",
                parameter_value=hold_ms,
                applied_parameter=hold_ms,
                severity=severity,
                timing=timing,
                start_ms=start,
                duration_ms=duration,
                behavior="transient",
                notes=f"The stale update hold is {hold_ms} ms during a {duration} ms active window.",
            )

    fan_durations = ((10000, "short"), (30000, "long"), (0, "permanent"))
    if mode == "quick":
        fan_durations = (fan_durations[0], fan_durations[-1])
    for duration, severity in fan_durations:
        for timing, start in timing_items:
            value = duration if duration else SIMULATION_DURATION_MS - start
            add_single(
                scenarios,
                prefix=f"fan_off_{severity}",
                name=f"Fan stuck off {severity} ({timing})",
                group="fan_stuck_off",
                fault_type="fan_stuck_off",
                security_group="conventional_fault",
                parameter_name="active_duration_ms",
                parameter_value=value,
                applied_parameter=0,
                severity=severity,
                timing=timing,
                start_ms=start,
                duration_ms=duration,
                behavior="permanent" if duration == 0 else "transient",
                notes="A zero configured duration is permanent through the remainder of the simulation." if duration == 0 else "",
            )

    pump_levels = ((25, 0.75, "mild"), (55, 0.45, "moderate"), (75, 0.25, "severe"))
    pump_timings = timing_items if mode != "quick" else [("mid", timings["mid"])]
    for loss_percent, scale, severity in pump_levels:
        for timing, start in pump_timings:
            add_single(
                scenarios,
                prefix="pump_loss_percent",
                name=f"Pump degradation {severity} ({timing})",
                group="pump_degradation",
                fault_type="pump_degraded",
                security_group="conventional_fault",
                parameter_name="effectiveness_loss_percent",
                parameter_value=loss_percent,
                applied_parameter=scale,
                severity=severity,
                timing=timing,
                start_ms=start,
                duration_ms=30000,
                behavior="transient",
                notes=f"Applied simulator pump effectiveness scale: {scale:g}.",
            )

    calibration_values = ((4, "low"), (8, "medium"), (12, "high"), (16, "maximum"))
    calibration_timings = timing_items if mode != "quick" else [("mid", timings["mid"])]
    for offset, severity in calibration_values:
        for timing, start in calibration_timings:
            add_single(
                scenarios,
                prefix="calibration_offset_c",
                name=f"Calibration target offset +{offset} C ({timing})",
                group="calibration_corruption",
                fault_type="calibration_memory_corruption",
                security_group="conventional_fault",
                parameter_name="control_target_offset_c",
                parameter_value=offset,
                applied_parameter=offset,
                severity=severity,
                timing=timing,
                start_ms=start,
                duration_ms=0,
                behavior="permanent",
            )

    chain_specs = (
        ("bias_then_fan", "Sensor bias then fan stuck off", Event("sensor_bias", 25000, 10000, "transient", 8.0), "fan_stuck_off", 0.0),
        ("pump_then_calibration", "Pump degradation then calibration corruption", Event("pump_degraded", 25000, 15000, "transient", 0.45), "calibration_memory_corruption", 12.0),
        ("stale_then_fan", "Stale sensor then fan stuck off", Event("stale_sensor_data", 25000, 15000, "transient", 5000.0), "fan_stuck_off", 0.0),
        ("calibration_then_fan", "Calibration corruption then fan stuck off", Event("calibration_memory_corruption", 25000, 10000, "transient", 12.0), "fan_stuck_off", 0.0),
    )
    spacings = ((15000, "close"), (30000, "medium"), (50000, "long"))
    if mode == "quick":
        spacings = ((30000, "medium"),)
    for chain_id, name, first, second_type, second_parameter in chain_specs:
        for spacing, severity in spacings:
            second_start = first.start_ms + spacing
            scenarios.append(
                Scenario(
                    f"chain_{chain_id}_{severity}",
                    f"{name} ({severity} spacing)",
                    "multi_event_chain",
                    f"{first.fault_type}+{second_type}",
                    "conventional_fault",
                    "stage_spacing_ms",
                    str(spacing),
                    float(spacing),
                    severity,
                    "staged",
                    first.start_ms,
                    None,
                    (first, Event(second_type, second_start, 0, "permanent", second_parameter)),
                    "Events use supported custom_multi scheduling; the first transient ends before the second stage.",
                )
            )

    # These are actual Virtual ECU fault-manifestation runs aligned with HT1-HT4
    # payload concepts. They are intentionally not described as RTL parameter sweeps.
    security_timings = (
        [("mid", timings["mid"])] if mode == "quick" else timing_items
    )
    ht1_values = ((2, "low"), (4, "medium"), (8, "high"), (12, "maximum"))
    if mode == "quick":
        ht1_values = (ht1_values[0], ht1_values[2], ht1_values[-1])
    for magnitude, severity in ht1_values:
        for timing, start in security_timings:
            add_single(
                scenarios,
                prefix="ht1_like_payload_c",
                name=f"HT1-like coolant sensor payload -{magnitude} C ({timing})",
                group="ht1_like_sensor_payload",
                fault_type="sensor_bias",
                security_group="HT1-like",
                parameter_name="payload_magnitude_c",
                parameter_value=magnitude,
                applied_parameter=-magnitude,
                severity=severity,
                timing=timing,
                start_ms=start,
                duration_ms=20000,
                behavior="transient",
                notes=f"Virtual ECU manifestation-level run with an applied {-magnitude:g} C sensor offset; not parameterized RTL.",
            )

    ht2_durations = ((10000, "short"), (30000, "long"), (0, "permanent"))
    if mode == "quick":
        ht2_durations = (ht2_durations[0], ht2_durations[-1])
    for duration, severity in ht2_durations:
        for timing, start in security_timings:
            value = duration if duration else SIMULATION_DURATION_MS - start
            add_single(
                scenarios,
                prefix=f"ht2_like_fan_suppression_{severity}",
                name=f"HT2-like fan output suppression {severity} ({timing})",
                group="ht2_like_fan_payload",
                fault_type="fan_stuck_off",
                security_group="HT2-like",
                parameter_name="payload_duration_ms",
                parameter_value=value,
                applied_parameter=0,
                severity=severity,
                timing=timing,
                start_ms=start,
                duration_ms=duration,
                behavior="permanent" if duration == 0 else "transient",
                notes="Virtual ECU fan-output manifestation; trigger threshold and persistence remain fixed/unavailable without new RTL parameterization.",
            )

    ht3_values = calibration_values
    if mode == "quick":
        ht3_values = (ht3_values[0], ht3_values[2], ht3_values[-1])
    for offset, severity in ht3_values:
        for timing, start in security_timings:
            add_single(
                scenarios,
                prefix="ht3_like_offset_c",
                name=f"HT3-like control-target payload +{offset} C ({timing})",
                group="ht3_like_calibration_payload",
                fault_type="calibration_memory_corruption",
                security_group="HT3-like",
                parameter_name="payload_offset_c",
                parameter_value=offset,
                applied_parameter=offset,
                severity=severity,
                timing=timing,
                start_ms=start,
                duration_ms=0,
                behavior="permanent",
                notes="Virtual ECU manifestation-level calibration payload; not parameterized RTL.",
            )

    ht4_spacings = ((15000, "close"), (30000, "medium"), (45000, "long"))
    if mode == "quick":
        ht4_spacings = (ht4_spacings[0], ht4_spacings[-1])
    for spacing, severity in ht4_spacings:
        first_start = 15000
        events = (
            Event("calibration_memory_corruption", first_start, 8000, "transient", 12.0),
            Event("sensor_bias", first_start + spacing, 8000, "transient", -8.0),
            Event("fan_stuck_off", first_start + 2 * spacing, 0, "permanent", 0.0),
        )
        scenarios.append(
            Scenario(
                f"ht4_like_stage_spacing_{severity}",
                f"HT4-like multi-stage manifestation ({severity} spacing)",
                "ht4_like_multi_stage",
                "calibration_memory_corruption+sensor_bias+fan_stuck_off",
                "HT4-like",
                "stage_spacing_ms",
                str(spacing),
                float(spacing),
                severity,
                "staged",
                first_start,
                None,
                events,
                "Trace-independent Virtual ECU composite using supported custom_multi events; not an RTL-simulated HT4 parameter variant.",
            )
        )

    if mode == "full":
        # Duration sensitivity for sensor bias is added only to the full grid.
        for duration, severity in ((5000, "short"), (30000, "long")):
            for timing, start in timings.items():
                add_single(
                    scenarios,
                    prefix=f"sensor_bias_duration_{severity}",
                    name=f"Sensor bias 6 C {severity} duration ({timing})",
                    group="sensor_bias_duration",
                    fault_type="sensor_bias",
                    security_group="conventional_fault",
                    parameter_name="active_duration_ms",
                    parameter_value=duration,
                    applied_parameter=6,
                    severity=severity,
                    timing=timing,
                    start_ms=start,
                    duration_ms=duration,
                    behavior="transient",
                )
    return scenarios


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"CSV has no data rows: {path}")
    return rows


def as_int(value: object, default: int = -1) -> int:
    text = str(value).strip()
    return int(float(text)) if text else default


def as_float(value: object, default: float = math.nan) -> float:
    text = str(value).strip()
    return float(text) if text else default


def summary_path(raw_path: Path) -> Path:
    return raw_path.with_name(f"{raw_path.stem}_summary.csv")


def simulator_command(executable: Path, raw_path: Path, scenario: Scenario, detector: str) -> List[str]:
    command = [str(executable), str(raw_path)]
    if not scenario.events:
        command.append("baseline")
    elif len(scenario.events) == 1:
        event = scenario.events[0]
        command.extend(("custom", event.fault_type, str(event.start_ms), str(event.duration_ms), event.behavior, f"{event.parameter:g}"))
    else:
        command.extend(("custom_multi", str(len(scenario.events))))
        for event in scenario.events:
            command.extend((event.fault_type, str(event.start_ms), str(event.duration_ms), event.behavior, f"{event.parameter:g}"))
    command.extend(("--detector", detector, "--detector-action", OBSERVE_ONLY, "--simulation-duration-ms", str(SIMULATION_DURATION_MS)))
    return command


def evaluate_run(executable: Path, raw_dir: Path, scenario: Scenario, detector: str, skip_existing: bool) -> Dict[str, object]:
    scenario_dir = raw_dir / scenario.scenario_id
    scenario_dir.mkdir(parents=True, exist_ok=True)
    raw_path = scenario_dir / f"{detector}.csv"
    summary_csv = summary_path(raw_path)
    if not (skip_existing and raw_path.is_file() and summary_csv.is_file()):
        completed = subprocess.run(
            simulator_command(executable, raw_path, scenario, detector),
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"Simulator failed for {scenario.scenario_id}/{detector}: {detail}")
    if not raw_path.is_file() or not summary_csv.is_file():
        raise RuntimeError(f"Missing expected simulator output for {scenario.scenario_id}/{detector}")

    raw_rows = read_rows(raw_path)
    summary = read_rows(summary_csv)[0]
    first_detection = as_int(summary.get("runtime_detection_first_detection_ms", "-1"))
    clean_alarm = int(not scenario.events and first_detection >= 0)
    event_detected = int(bool(scenario.events) and first_detection >= scenario.activation_time_ms)
    latency = first_detection - scenario.activation_time_ms if event_detected else -1
    detection_row = next(
        (row for row in raw_rows if as_int(row.get("runtime_detection_detected", "0"), 0) != 0),
        None,
    )
    return {
        "scenario_id": scenario.scenario_id,
        "scenario_name": scenario.scenario_name,
        "scenario_group": scenario.scenario_group,
        "fault_type": scenario.fault_type,
        "security_group": scenario.security_group,
        "parameter_name": scenario.parameter_name,
        "parameter_value": scenario.parameter_value,
        "parameter_value_numeric": "" if scenario.parameter_value_numeric is None else f"{scenario.parameter_value_numeric:g}",
        "severity_level": scenario.severity_level,
        "timing_label": scenario.timing_label,
        "activation_time_ms": scenario.activation_time_ms,
        "duration_ms": "" if scenario.duration_ms is None else scenario.duration_ms,
        "detector_id": detector,
        "detector_name": DETECTOR_NAMES[detector],
        "event_detected": "yes" if event_detected else "no",
        "first_alarm_time_ms": first_detection,
        "detection_latency_ms": latency,
        "missed_detection": "yes" if scenario.events and not event_detected else "no",
        "clean_alarm": "yes" if clean_alarm else "no",
        "max_coolant_temp": f"{as_float(summary.get('max_coolant_temp_c', '')):.2f}",
        "final_safety_state": summary.get("final_safe_state_label", "unknown"),
        "runtime_detection_label": detection_row.get("runtime_detection_label", "none") if detection_row else "none",
        "raw_csv": relative(raw_path),
        "summary_csv": relative(summary_csv),
        "notes": scenario.notes,
    }


def write_csv(path: Path, rows: Sequence[Mapping[str, object]], columns: Sequence[str] | None = None) -> None:
    if not rows and columns is None:
        raise RuntimeError(f"Refusing to write empty result file: {path}")
    fieldnames = list(columns or rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def event_rows(rows: Iterable[Mapping[str, object]]) -> List[Mapping[str, object]]:
    return [row for row in rows if str(row["fault_type"]) != "none"]


def detected(row: Mapping[str, object]) -> bool:
    return str(row["event_detected"]).lower() == "yes"


def aggregate(rows: Sequence[Mapping[str, object]], group_columns: Sequence[str]) -> List[Dict[str, object]]:
    grouped: Dict[tuple[str, ...], List[Mapping[str, object]]] = defaultdict(list)
    for row in event_rows(rows):
        grouped[tuple(str(row[column]) for column in group_columns)].append(row)
    output: List[Dict[str, object]] = []
    for key in sorted(grouped):
        selected = grouped[key]
        detections = [row for row in selected if detected(row)]
        latencies = [as_int(row["detection_latency_ms"]) for row in detections]
        item: Dict[str, object] = dict(zip(group_columns, key))
        item.update(
            {
                "event_variants": len(selected),
                "detected_events": len(detections),
                "missed_detections": len(selected) - len(detections),
                "coverage_percent": f"{100.0 * len(detections) / len(selected):.2f}",
                "mean_latency_ms": f"{statistics.mean(latencies):.2f}" if latencies else "",
                "median_latency_ms": f"{statistics.median(latencies):.2f}" if latencies else "",
                "max_latency_ms": max(latencies) if latencies else "",
                "max_coolant_temp": f"{max(as_float(row['max_coolant_temp']) for row in selected):.2f}",
            }
        )
        output.append(item)
    return output


def fastest_counts(rows: Sequence[Mapping[str, object]]) -> Dict[str, int]:
    by_scenario: Dict[str, List[Mapping[str, object]]] = defaultdict(list)
    for row in event_rows(rows):
        by_scenario[str(row["scenario_id"])].append(row)
    counts = {detector: 0 for detector in DETECTORS}
    for selected in by_scenario.values():
        detections = [row for row in selected if detected(row)]
        if not detections:
            continue
        best = min(as_int(row["detection_latency_ms"]) for row in detections)
        for row in detections:
            if as_int(row["detection_latency_ms"]) == best:
                counts[str(row["detector_id"])] += 1
    return counts


def detector_summary(rows: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    fastest = fastest_counts(rows)
    output = []
    for detector in DETECTORS:
        selected = [row for row in event_rows(rows) if row["detector_id"] == detector]
        detections = [row for row in selected if detected(row)]
        latencies = [as_int(row["detection_latency_ms"]) for row in detections]
        clean = [row for row in rows if row["detector_id"] == detector and row["fault_type"] == "none"]
        output.append(
            {
                "detector_id": detector,
                "detector_name": DETECTOR_NAMES[detector],
                "total_event_variants": len(selected),
                "detected_events": len(detections),
                "missed_detections": len(selected) - len(detections),
                "coverage_percent": f"{100.0 * len(detections) / len(selected):.2f}",
                "mean_latency_ms": f"{statistics.mean(latencies):.2f}" if latencies else "",
                "median_latency_ms": f"{statistics.median(latencies):.2f}" if latencies else "",
                "max_latency_ms": max(latencies) if latencies else "",
                "fastest_tied_fastest_count": fastest[detector],
                "clean_variants": len(clean),
                "clean_alarms": sum(str(row["clean_alarm"]) == "yes" for row in clean),
            }
        )
    return output


def hybrid_comparisons(rows: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    grouped: Dict[str, List[Mapping[str, object]]] = defaultdict(list)
    for row in event_rows(rows):
        key = str(row["security_group"] if row["security_group"] != "conventional_fault" else row["scenario_group"])
        grouped[key].append(row)
    output = []
    for group, selected in sorted(grouped.items()):
        metrics: Dict[str, tuple[float, float]] = {}
        for detector in DETECTORS:
            subset = [row for row in selected if row["detector_id"] == detector]
            detections = [row for row in subset if detected(row)]
            latency = statistics.mean(as_int(row["detection_latency_ms"]) for row in detections) if detections else math.inf
            metrics[detector] = (100.0 * len(detections) / len(subset) if subset else math.nan, latency)
        baseline = max(
            DETECTORS[:-1],
            key=lambda item: (metrics[item][0], -metrics[item][1]),
        )
        hybrid_coverage, hybrid_latency = metrics["hybrid_adaptive_kalman"]
        baseline_coverage, baseline_latency = metrics[baseline]
        if hybrid_coverage > baseline_coverage:
            outcome = "higher coverage"
        elif hybrid_coverage < baseline_coverage:
            outcome = "lower coverage"
        elif hybrid_latency < baseline_latency:
            outcome = "coverage tie; lower mean detected-event latency"
        elif hybrid_latency == baseline_latency:
            outcome = "coverage and mean-latency tie"
        else:
            outcome = "coverage tie; higher mean detected-event latency"
        output.append(
            {
                "fault_or_security_group": group,
                "hybrid_coverage_percent": f"{hybrid_coverage:.2f}",
                "best_baseline_detector_id": baseline,
                "best_baseline_detector_name": DETECTOR_NAMES[baseline],
                "best_baseline_coverage_percent": f"{baseline_coverage:.2f}",
                "hybrid_mean_latency_ms": "" if not math.isfinite(hybrid_latency) else f"{hybrid_latency:.2f}",
                "best_baseline_mean_latency_ms": "" if not math.isfinite(baseline_latency) else f"{baseline_latency:.2f}",
                "computed_comparison": outcome,
            }
        )
    return output


def threshold_rows(rows: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    output = []
    groups = sorted({(str(row["scenario_group"]), str(row["parameter_name"])) for row in event_rows(rows) if str(row.get("parameter_value_numeric", ""))})
    for group, parameter in groups:
        base = [row for row in event_rows(rows) if row["scenario_group"] == group and row["parameter_name"] == parameter]
        values = sorted({as_float(row["parameter_value_numeric"]) for row in base})
        if len(values) < 2 or "spacing" in parameter or "duration" in parameter:
            continue
        for detector in DETECTORS:
            any_value = ""
            full_value = ""
            for value in values:
                selected = [row for row in base if row["detector_id"] == detector and as_float(row["parameter_value_numeric"]) == value]
                detection_count = sum(detected(row) for row in selected)
                if detection_count and any_value == "":
                    any_value = f"{value:g}"
                if selected and detection_count == len(selected) and full_value == "":
                    full_value = f"{value:g}"
            output.append(
                {
                    "scenario_group": group,
                    "parameter_name": parameter,
                    "detector_id": detector,
                    "detector_name": DETECTOR_NAMES[detector],
                    "lowest_value_with_any_detection": any_value or "not reached",
                    "lowest_value_with_full_timing_coverage": full_value or "not reached",
                    "interpretation_boundary": "Threshold is within the evaluated grid only.",
                }
            )
    return output


def security_summary(rows: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    security = [row for row in rows if str(row["security_group"]).startswith("HT")]
    return aggregate(security, ("security_group", "detector_id", "detector_name"))


def write_markdown(output_dir: Path, mode: str, scenarios: Sequence[Scenario], rows: Sequence[Mapping[str, object]], summaries: Sequence[Mapping[str, object]], comparisons: Sequence[Mapping[str, object]], thresholds: Sequence[Mapping[str, object]]) -> None:
    event_variant_count = sum(bool(s.events) for s in scenarios)
    security_count = sum(s.security_group.startswith("HT") for s in scenarios)
    hybrid = next(row for row in summaries if row["detector_id"] == "hybrid_adaptive_kalman")
    readme = f"""# Fault-Injection and Trojan-Parameter Sensitivity Study

This directory contains computed outputs from {len(rows)} actual Virtual ECU detector runs across {len(scenarios)} deterministic scenario variants ({event_variant_count} event variants and {len(scenarios) - event_variant_count} clean reference). All eight runtime detectors use `observe_only`, so thermal outcomes reflect the same configured fault manifestation rather than detector-driven intervention.

Mode: `{mode}`  
Simulation duration: {SIMULATION_DURATION_MS} ms per run  
Representative HT-like manifestation variants: {security_count}

The HT-like rows are Virtual ECU manifestation-level parameter variants aligned with HT1–HT4 payload concepts. They are not new parameterized RTL simulations and do not alter the existing HT1–HT4 baselines.

## Files

- `sweep_event_results.csv`: one row per scenario/detector run, with raw evidence paths.
- `sweep_detector_summary.csv`: overall coverage, latency, fastest/tied-fastest, and clean-alarm counts.
- `sweep_by_fault_type.csv`, `sweep_by_severity.csv`, `sweep_by_timing.csv`: computed breakdowns.
- `sweep_by_security_group.csv`: detector outcomes for representative HT-like manifestation variants.
- `sweep_hybrid_vs_baselines.csv`: computed Hybrid-versus-best-baseline comparisons.
- `sweep_detection_thresholds.csv`: lowest evaluated parameter values with any/full timing coverage where meaningful.
- `sweep_claims_summary.md` and `sweep_limitations.md`: bounded interpretation.
- `raw/`: simulator trace and summary CSV evidence for each run.

Reproduce from the repository root:

```bash
python3 scripts/run_fault_injection_parameter_sweep.py
```
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    hybrid_comparisons = [row for row in comparisons if row["fault_or_security_group"]]
    comparison_lines = [
        f"- {row['fault_or_security_group']}: Hybrid {row['hybrid_coverage_percent']}% versus {row['best_baseline_detector_name']} {row['best_baseline_coverage_percent']}%; {row['computed_comparison']}."
        for row in hybrid_comparisons
    ]
    threshold_lines = [
        f"- {row['scenario_group']} / {row['detector_name']}: any detection at {row['lowest_value_with_any_detection']}; full timing coverage at {row['lowest_value_with_full_timing_coverage']}."
        for row in thresholds
        if row["detector_id"] == "hybrid_adaptive_kalman"
    ]
    claims = [
        "# Parameter Sweep Claims Summary",
        "",
        f"- In the evaluated deterministic parameter sweep, Hybrid Adaptive Kalman detected {hybrid['detected_events']}/{hybrid['total_event_variants']} event variants ({hybrid['coverage_percent']}% coverage).",
        f"- Its median detected-event latency was {hybrid['median_latency_ms'] or 'n/a'} ms; latency excludes missed detections.",
        f"- The evaluated clean reference produced {hybrid['clean_alarms']} Hybrid clean alarm run(s).",
        "- Sensitivity results describe only the finite severity, duration, and activation-timing grid recorded in `sweep_config.json`.",
        "",
        "## Hybrid versus best evaluated baseline by group",
        "",
        *(comparison_lines or ["- No comparison rows were available."]),
        "",
        "## Evaluated-grid detection thresholds for Hybrid Adaptive Kalman",
        "",
        *(threshold_lines or ["- No monotonic numeric threshold was meaningful for the selected grid."]),
        "",
        "These computed comparisons do not establish detection of all faults or Hardware Trojans.",
    ]
    (output_dir / "sweep_claims_summary.md").write_text("\n".join(claims) + "\n", encoding="utf-8")

    limitations = """# Parameter Sweep Limitations

- The parameter grid is finite and deterministic; severity and timing ranges are evaluated examples, not exhaustive automotive coverage.
- The simulator uses a simplified academic thermal plant and host-side fixed-step execution, not a real vehicle or production ECU.
- Detector thresholds and the unchanged `hybrid_adaptive_kalman` implementation are evaluated as currently configured.
- The HT-like sensitivity cases are actual Virtual ECU fault-manifestation runs aligned with representative HT1–HT4 payload concepts. They are not parameterized RTL simulations, silicon validation, or an exhaustive Trojan taxonomy.
- Existing RTL HT1–HT4 behavior is unchanged. RTL trigger-threshold and persistence parameter sweeps remain unavailable because clean parameterization would require separate validated RTL variants.
- Multi-event cases use the supported ordered `custom_multi` interface and non-overlapping precursor stages; they do not model arbitrary concurrent faults.
- Detected-event latency excludes misses. A detector alarm before event activation is not credited as an event detection.
- Results do not imply production readiness, embedded certification, hard real-time certification, or complete security coverage.
"""
    (output_dir / "sweep_limitations.md").write_text(limitations, encoding="utf-8")


def main() -> int:
    args = parse_args()
    mode = "quick" if args.quick else "full" if args.full else "default"
    executable = args.executable.resolve()
    if not executable.is_file():
        raise FileNotFoundError(f"Simulator executable not found: {executable}. Run 'make' first.")
    scenarios = build_scenarios(mode)
    if args.limit is not None:
        clean_reference = scenarios[0]
        scenarios = [clean_reference, *scenarios[1 : args.limit + 1]]
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/run_fault_injection_parameter_sweep.py",
        "mode": mode,
        "seed": args.seed,
        "randomization_used": False,
        "simulation_duration_ms": SIMULATION_DURATION_MS,
        "detectors": [{"id": detector, "name": DETECTOR_NAMES[detector]} for detector in DETECTORS],
        "scenario_variant_count": len(scenarios),
        "event_variant_count": sum(bool(s.events) for s in scenarios),
        "detector_run_count": len(scenarios) * len(DETECTORS),
        "security_sensitivity_boundary": "Virtual ECU manifestation-level representative HT-like variants; no new parameterized RTL simulations.",
        "scenarios": [asdict(scenario) for scenario in scenarios],
    }
    (output_dir / "sweep_config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    total = len(scenarios) * len(DETECTORS)
    rows: List[Dict[str, object]] = []
    for scenario_index, scenario in enumerate(scenarios, start=1):
        print(f"[{scenario_index:03d}/{len(scenarios):03d}] {scenario.scenario_id}", flush=True)
        for detector in DETECTORS:
            rows.append(evaluate_run(executable, raw_dir, scenario, detector, args.skip_existing))
    if len(rows) != total:
        raise RuntimeError(f"Expected {total} detector runs, collected {len(rows)}")

    summaries = detector_summary(rows)
    by_fault = aggregate(rows, ("fault_type", "detector_id", "detector_name"))
    by_severity = aggregate(rows, ("scenario_group", "fault_type", "security_group", "parameter_name", "parameter_value", "severity_level", "detector_id", "detector_name"))
    by_timing = aggregate(rows, ("scenario_group", "timing_label", "activation_time_ms", "detector_id", "detector_name"))
    by_security = security_summary(rows)
    comparisons = hybrid_comparisons(rows)
    thresholds = threshold_rows(rows)

    write_csv(output_dir / "sweep_event_results.csv", rows, EVENT_COLUMNS)
    write_csv(output_dir / "sweep_detector_summary.csv", summaries)
    write_csv(output_dir / "sweep_by_fault_type.csv", by_fault)
    write_csv(output_dir / "sweep_by_severity.csv", by_severity)
    write_csv(output_dir / "sweep_by_timing.csv", by_timing)
    write_csv(
        output_dir / "sweep_by_security_group.csv",
        by_security,
        (
            "security_group",
            "detector_id",
            "detector_name",
            "event_variants",
            "detected_events",
            "missed_detections",
            "coverage_percent",
            "mean_latency_ms",
            "median_latency_ms",
            "max_latency_ms",
            "max_coolant_temp",
        ),
    )
    write_csv(output_dir / "sweep_hybrid_vs_baselines.csv", comparisons)
    if thresholds:
        write_csv(output_dir / "sweep_detection_thresholds.csv", thresholds)
    write_markdown(output_dir, mode, scenarios, rows, summaries, comparisons, thresholds)

    hybrid = next(row for row in summaries if row["detector_id"] == "hybrid_adaptive_kalman")
    print("\nParameter sensitivity study complete.")
    print(f"  Scenario variants: {len(scenarios)} ({config['event_variant_count']} event + {len(scenarios) - int(config['event_variant_count'])} clean)")
    print(f"  Detector runs: {len(rows)} across {len(DETECTORS)} detectors")
    print(f"  Hybrid coverage: {hybrid['coverage_percent']}%")
    print(f"  Hybrid median detected-event latency: {hybrid['median_latency_ms'] or 'n/a'} ms")
    print("  Security sensitivity: representative HT-like Virtual ECU manifestations; parameterized RTL unavailable")
    print(f"  Output: {output_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
