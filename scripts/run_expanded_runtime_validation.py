#!/usr/bin/env python3
"""Run the expanded deterministic Virtual ECU detector validation matrix."""

from __future__ import annotations

import argparse
import csv
import math
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Dict, Iterable, List, Mapping, Sequence

import run_full_runtime_validation as full_validation
import run_runtime_custom_matrix as custom_matrix
import run_runtime_intervention_study as intervention


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "expanded_runtime_validation"
DEFAULT_EXECUTABLE = PROJECT_ROOT / "virtual_ecu"
RTL_STUDY_SCRIPT = PROJECT_ROOT / "scripts" / "run_rtl_hardware_trojan_study.py"
OBSERVE_ONLY = "observe_only"
DETECTORS = intervention.DETECTORS
EXPECTED_VARIANTS = 40
EXPECTED_NORMALIZED_ROWS = EXPECTED_VARIANTS * len(DETECTORS)

EXPANDED_COLUMNS = (
    "experiment_family",
    "scenario_id",
    "scenario_name",
    "scenario_group",
    "variant",
    "detector",
    "event_start_ms",
    "first_detection_ms",
    "detection_latency_ms",
    "detected_after_event",
    "false_positive_count",
    "detection_label",
    "max_coolant_temp_c",
    "final_safe_state",
    "raw_csv",
    "summary_csv",
    "fault_type",
    "fault_severity",
    "fault_start_ms",
    "profile_id",
    "profile_name",
    "trojan_target",
    "trojan_profile",
    "notes",
)


@dataclass(frozen=True)
class ProfileSpec:
    profile_id: str
    profile_name: str
    rows: tuple[tuple[object, ...], ...]


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    scenario_name: str
    scenario_group: str
    variant: str
    fault_severity: str
    events: tuple[custom_matrix.Event, ...] = ()
    profile_id: str = "default_thermal_plant"
    profile_name: str = "Default thermal plant"
    duration_ms: int = 120000
    notes: str = ""


PROFILE_COLUMNS = (
    "start_ms",
    "end_ms",
    "vehicle_speed_kph",
    "engine_load",
    "ambient_temp_c",
    "external_airflow_factor",
    "road_slope_percent",
)

PROFILES = (
    ProfileSpec(
        "warm_ambient",
        "Warm ambient clean profile",
        ((0, 120000, 70, 0.45, 38, 0.30, 0),),
    ),
    ProfileSpec(
        "high_load",
        "High-load clean profile",
        ((0, 120000, 50, 0.80, 34, 0.20, 3),),
    ),
    ProfileSpec(
        "custom_cycle",
        "Three-segment custom clean profile",
        (
            (0, 40000, 100, 0.45, 30, 0.40, 0),
            (40000, 80000, 35, 0.60, 34, 0.15, 2),
            (80000, 120000, 75, 0.55, 32, 0.25, 0),
        ),
    ),
)

CLEAN_SCENARIOS = (
    ScenarioSpec(
        "clean_nominal",
        "Nominal no-fault baseline",
        "clean_baseline",
        "clean",
        "none",
        notes="Built-in baseline campaign at the standard 120 s duration.",
    ),
    ScenarioSpec(
        "clean_warm_ambient",
        "Warm ambient no-fault baseline",
        "clean_baseline",
        "clean",
        "none",
        profile_id="warm_ambient",
        profile_name="Warm ambient clean profile",
        notes="No injected fault; constant warm ambient profile.",
    ),
    ScenarioSpec(
        "clean_high_load",
        "High-load no-fault baseline",
        "clean_baseline",
        "clean",
        "none",
        profile_id="high_load",
        profile_name="High-load clean profile",
        notes="No injected fault; sustained supported high-load profile.",
    ),
    ScenarioSpec(
        "clean_long_duration",
        "Long-duration no-fault baseline",
        "clean_baseline",
        "clean",
        "none",
        duration_ms=240000,
        notes="Built-in baseline campaign extended deterministically to 240 s.",
    ),
    ScenarioSpec(
        "clean_custom_cycle",
        "Custom-profile no-fault baseline",
        "clean_baseline",
        "clean",
        "none",
        profile_id="custom_cycle",
        profile_name="Three-segment custom clean profile",
        notes="No injected fault; supported three-segment driving profile.",
    ),
)

FAULT_SCENARIOS = (
    ScenarioSpec(
        "sensor_bias_positive_small",
        "Sensor bias positive small",
        "sensor_bias",
        "fault",
        "small",
        (custom_matrix.Event("sensor_bias", 30000, 15000, "transient", 3.0),),
    ),
    ScenarioSpec(
        "sensor_bias_positive_medium",
        "Sensor bias positive medium",
        "sensor_bias",
        "fault",
        "medium",
        (custom_matrix.Event("sensor_bias", 45000, 15000, "transient", 6.0),),
    ),
    ScenarioSpec(
        "sensor_bias_positive_large_late",
        "Sensor bias positive large late",
        "sensor_bias",
        "fault",
        "large",
        (custom_matrix.Event("sensor_bias", 70000, 15000, "transient", 10.0),),
    ),
    ScenarioSpec(
        "sensor_bias_negative_medium",
        "Sensor bias negative medium",
        "sensor_bias",
        "fault",
        "medium_negative",
        (custom_matrix.Event("sensor_bias", 30000, 15000, "transient", -6.0),),
    ),
    ScenarioSpec(
        "stale_sensor_short",
        "Stale sensor short hold",
        "stale_sensor_data",
        "fault",
        "short",
        (
            custom_matrix.Event(
                "stale_sensor_data", 30000, 10000, "transient", 1000.0
            ),
        ),
    ),
    ScenarioSpec(
        "stale_sensor_medium",
        "Stale sensor medium hold",
        "stale_sensor_data",
        "fault",
        "medium",
        (
            custom_matrix.Event(
                "stale_sensor_data", 45000, 25000, "transient", 5000.0
            ),
        ),
    ),
    ScenarioSpec(
        "stale_sensor_long",
        "Stale sensor long permanent hold",
        "stale_sensor_data",
        "fault",
        "long",
        (
            custom_matrix.Event(
                "stale_sensor_data", 65000, 0, "permanent", 15000.0
            ),
        ),
    ),
    ScenarioSpec(
        "stale_sensor_early_long",
        "Stale sensor early long hold",
        "stale_sensor_data",
        "fault",
        "long_early",
        (
            custom_matrix.Event(
                "stale_sensor_data", 25000, 50000, "transient", 12000.0
            ),
        ),
    ),
    ScenarioSpec(
        "fan_stuck_off_early",
        "Fan stuck off early",
        "fan_stuck_off",
        "fault",
        "early",
        (custom_matrix.Event("fan_stuck_off", 40000, 0, "permanent", 0.0),),
    ),
    ScenarioSpec(
        "fan_stuck_off_nominal",
        "Fan stuck off nominal timing",
        "fan_stuck_off",
        "fault",
        "nominal",
        (custom_matrix.Event("fan_stuck_off", 75000, 0, "permanent", 0.0),),
    ),
    ScenarioSpec(
        "fan_stuck_off_high_load",
        "Fan stuck off under high load",
        "fan_stuck_off",
        "fault",
        "high_load",
        (custom_matrix.Event("fan_stuck_off", 60000, 0, "permanent", 0.0),),
        profile_id="high_load",
        profile_name="High-load clean profile",
        notes="Uses the same supported high-load profile as its clean reference.",
    ),
    ScenarioSpec(
        "pump_degraded_mild",
        "Pump degraded mild",
        "pump_degraded",
        "fault",
        "mild",
        (
            custom_matrix.Event(
                "pump_degraded", 60000, 30000, "transient", 0.75
            ),
        ),
    ),
    ScenarioSpec(
        "pump_degraded_medium",
        "Pump degraded medium",
        "pump_degraded",
        "fault",
        "medium",
        (
            custom_matrix.Event(
                "pump_degraded", 60000, 25000, "transient", 0.45
            ),
        ),
    ),
    ScenarioSpec(
        "pump_degraded_severe",
        "Pump degraded severe",
        "pump_degraded",
        "fault",
        "severe",
        (
            custom_matrix.Event(
                "pump_degraded", 60000, 25000, "transient", 0.20
            ),
        ),
    ),
    ScenarioSpec(
        "pump_degraded_early",
        "Pump degraded medium early",
        "pump_degraded",
        "fault",
        "medium_early",
        (
            custom_matrix.Event(
                "pump_degraded", 30000, 25000, "transient", 0.45
            ),
        ),
    ),
    ScenarioSpec(
        "calibration_shift_small",
        "Calibration target shift small",
        "calibration_memory_corruption",
        "fault",
        "small",
        (
            custom_matrix.Event(
                "calibration_memory_corruption",
                52000,
                0,
                "permanent",
                4.0,
            ),
        ),
    ),
    ScenarioSpec(
        "calibration_shift_medium",
        "Calibration target shift medium",
        "calibration_memory_corruption",
        "fault",
        "medium",
        (
            custom_matrix.Event(
                "calibration_memory_corruption",
                52000,
                0,
                "permanent",
                8.0,
            ),
        ),
    ),
    ScenarioSpec(
        "calibration_shift_large",
        "Calibration target shift large",
        "calibration_memory_corruption",
        "fault",
        "large",
        (
            custom_matrix.Event(
                "calibration_memory_corruption",
                52000,
                0,
                "permanent",
                16.0,
            ),
        ),
    ),
    ScenarioSpec(
        "calibration_shift_large_early",
        "Calibration target shift large early",
        "calibration_memory_corruption",
        "fault",
        "large_early",
        (
            custom_matrix.Event(
                "calibration_memory_corruption",
                25000,
                0,
                "permanent",
                16.0,
            ),
        ),
    ),
    ScenarioSpec(
        "sensor_interface_short",
        "Sensor interface intermittent short",
        "sensor_interface_intermittent",
        "fault",
        "short",
        (
            custom_matrix.Event(
                "sensor_interface_intermittent",
                45000,
                5000,
                "transient",
                4.0,
            ),
        ),
    ),
    ScenarioSpec(
        "sensor_interface_long",
        "Sensor interface intermittent long",
        "sensor_interface_intermittent",
        "fault",
        "long",
        (
            custom_matrix.Event(
                "sensor_interface_intermittent",
                45000,
                30000,
                "transient",
                8.0,
            ),
        ),
    ),
    ScenarioSpec(
        "sensor_interface_repeated",
        "Sensor interface repeated bursts",
        "sensor_interface_intermittent",
        "fault",
        "repeated",
        (
            custom_matrix.Event(
                "sensor_interface_intermittent",
                30000,
                5000,
                "transient",
                6.0,
            ),
            custom_matrix.Event(
                "sensor_interface_intermittent",
                60000,
                5000,
                "transient",
                6.0,
            ),
        ),
        notes="Two ordered intermittent events; latency is measured from the first.",
    ),
    ScenarioSpec(
        "chain_sensor_then_pump",
        "Sensor then pump chain",
        "multi_fault_chain",
        "fault",
        "two_stage",
        (
            custom_matrix.Event("sensor_bias", 30000, 15000, "transient", 6.0),
            custom_matrix.Event(
                "pump_degraded", 60000, 25000, "transient", 0.45
            ),
        ),
        notes="Latency is measured from the first ordered event.",
    ),
    ScenarioSpec(
        "chain_pump_then_fan",
        "Pump then fan chain",
        "multi_fault_chain",
        "fault",
        "two_stage",
        (
            custom_matrix.Event(
                "pump_degraded", 40000, 25000, "transient", 0.45
            ),
            custom_matrix.Event("fan_stuck_off", 75000, 0, "permanent", 0.0),
        ),
        notes="Latency is measured from the first ordered event.",
    ),
    ScenarioSpec(
        "chain_sensor_pump_fan",
        "Sensor then pump then fan chain",
        "multi_fault_chain",
        "fault",
        "three_stage",
        (
            custom_matrix.Event("sensor_bias", 30000, 15000, "transient", 6.0),
            custom_matrix.Event(
                "pump_degraded", 60000, 25000, "transient", 0.45
            ),
            custom_matrix.Event("fan_stuck_off", 90000, 0, "permanent", 0.0),
        ),
        notes="Latency is measured from the first ordered event.",
    ),
    ScenarioSpec(
        "chain_calibration_then_sensor",
        "Calibration then sensor chain",
        "multi_fault_chain",
        "fault",
        "two_stage",
        (
            custom_matrix.Event(
                "calibration_memory_corruption",
                25000,
                20000,
                "transient",
                8.0,
            ),
            custom_matrix.Event("sensor_bias", 60000, 15000, "transient", 6.0),
        ),
        notes="Latency is measured from the first ordered event.",
    ),
    ScenarioSpec(
        "chain_calibration_then_fan",
        "Calibration then fan chain",
        "multi_fault_chain",
        "fault",
        "two_stage",
        (
            custom_matrix.Event(
                "calibration_memory_corruption",
                25000,
                20000,
                "transient",
                8.0,
            ),
            custom_matrix.Event("fan_stuck_off", 60000, 0, "permanent", 0.0),
        ),
        notes="Latency is measured from the first ordered event.",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run exactly 320 normalized detector rows across expanded clean, "
            "fault-injection, and RTL Hardware Trojan variants."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output root for expanded validation traces and summaries.",
    )
    parser.add_argument(
        "--executable",
        type=Path,
        default=DEFAULT_EXECUTABLE,
        help="Path to the compiled virtual_ecu executable.",
    )
    return parser.parse_args()


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"CSV has no data rows: {path}")
    return rows


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())


def write_rows(
    path: Path,
    columns: Sequence[str],
    rows: Iterable[Mapping[str, object]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_profiles(output_dir: Path) -> Dict[str, Path]:
    profile_dir = output_dir / "profiles"
    profile_dir.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, Path] = {}
    for profile in PROFILES:
        path = profile_dir / f"{profile.profile_id}.csv"
        write_rows(path, PROFILE_COLUMNS, (dict(zip(PROFILE_COLUMNS, row)) for row in profile.rows))
        paths[profile.profile_id] = path
    return paths


def profile_path_for(
    scenario: ScenarioSpec,
    profile_paths: Mapping[str, Path],
) -> Path | None:
    if scenario.profile_id == "default_thermal_plant":
        return None
    return profile_paths[scenario.profile_id]


def run_checked(command: Sequence[str], label: str) -> None:
    completed = subprocess.run(
        list(command),
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"{label} failed:\n{detail}")


def normalize_rtl_rows(comparison_path: Path) -> List[Dict[str, object]]:
    group_by_target = {
        "ht1_coolant_sensor": "rtl_coolant_sensor",
        "ht2_fan_driver": "rtl_fan_driver",
        "ht3_calibration_memory": "rtl_calibration_memory",
        "ht4_multi_stage_chain": "rtl_multi_stage_chain",
    }
    normalized: List[Dict[str, object]] = []
    for row in read_rows(comparison_path):
        attack_variant = row["variant"] == "trojan"
        normalized.append(
            {
                "experiment_family": "rtl_security",
                "scenario_id": row["rtl_target_id"],
                "scenario_name": row["rtl_target_name"],
                "scenario_group": group_by_target[row["rtl_target_id"]],
                "variant": row["variant"],
                "detector": row["detector"],
                "event_start_ms": (
                    full_validation.parse_int(row["rtl_trojan_trigger_time_ms"])
                    if attack_variant
                    else -1
                ),
                "first_detection_ms": full_validation.parse_int(
                    row["runtime_detection_first_detection_ms"]
                ),
                "detection_latency_ms": (
                    full_validation.parse_int(
                        row["detection_latency_from_payload_ms"]
                    )
                    if attack_variant
                    else -1
                ),
                "detected_after_event": (
                    full_validation.parse_int(row["detected_after_payload"], 0)
                    if attack_variant
                    else 0
                ),
                "false_positive_count": full_validation.parse_int(
                    row["runtime_reported_false_positive_count"], 0
                ),
                "detection_label": row["runtime_detection_label"],
                "max_coolant_temp_c": full_validation.parse_float(
                    row["max_coolant_temp_c"]
                ),
                "final_safe_state": row["final_safe_state"],
                "raw_csv": row["raw_csv"],
                "summary_csv": row["summary_csv"],
                "fault_type": (
                    row["rtl_trojan_type"] if attack_variant else "none"
                ),
                "fault_severity": "configured" if attack_variant else "none",
                "fault_start_ms": (
                    full_validation.parse_int(row["rtl_trojan_trigger_time_ms"])
                    if attack_variant
                    else -1
                ),
                "profile_id": "rtl_nominal_trace",
                "profile_name": "RTL nominal source trace",
                "trojan_target": row["rtl_trojan_target"],
                "trojan_profile": "nominal_trace",
                "notes": (
                    "Trace-driven configured RTL Trojan payload."
                    if attack_variant
                    else "Clean RTL interface replay reference."
                ),
            }
        )
    return normalized


def clean_row(
    executable: Path,
    raw_dir: Path,
    scenario: ScenarioSpec,
    detector: str,
    profile_path: Path | None,
) -> Dict[str, object]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{detector}__{OBSERVE_ONLY}.csv"
    summary_path = intervention.summary_path_for(raw_path)
    command = [
        str(executable),
        str(raw_path),
        "baseline",
        "--detector",
        detector,
        "--detector-action",
        OBSERVE_ONLY,
        "--simulation-duration-ms",
        str(scenario.duration_ms),
    ]
    if profile_path is not None:
        command.extend(("--driving-profile", str(profile_path)))
    run_checked(command, f"{scenario.scenario_id}/{detector}")
    raw_rows = read_rows(raw_path)
    summary = read_rows(summary_path)[0]
    final_row = raw_rows[-1]
    detection_row = intervention.first_runtime_row(
        raw_rows, "runtime_detection_detected"
    )
    return {
        "experiment_family": "clean_baseline",
        "scenario_id": scenario.scenario_id,
        "scenario_name": scenario.scenario_name,
        "scenario_group": scenario.scenario_group,
        "variant": "clean",
        "detector": detector,
        "event_start_ms": -1,
        "first_detection_ms": full_validation.parse_int(
            summary.get("runtime_detection_first_detection_ms", "-1")
        ),
        "detection_latency_ms": -1,
        "detected_after_event": 0,
        "false_positive_count": full_validation.parse_int(
            final_row.get("runtime_detection_false_positive_count", "0"), 0
        ),
        "detection_label": (
            detection_row.get("runtime_detection_label", "none")
            if detection_row is not None
            else "none"
        ),
        "max_coolant_temp_c": full_validation.parse_float(
            summary.get("max_coolant_temp_c", "")
        ),
        "final_safe_state": summary.get("final_safe_state_label", "unknown"),
        "raw_csv": relative_path(raw_path),
        "summary_csv": relative_path(summary_path),
        "fault_type": "none",
        "fault_severity": "none",
        "fault_start_ms": -1,
        "profile_id": scenario.profile_id,
        "profile_name": scenario.profile_name,
        "trojan_target": "",
        "trojan_profile": "",
        "notes": scenario.notes,
    }


def fault_row(
    executable: Path,
    raw_dir: Path,
    scenario: ScenarioSpec,
    detector: str,
    profile_path: Path | None,
) -> Dict[str, object]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    source = custom_matrix.run_simulation(
        executable,
        raw_dir,
        scenario.scenario_id,
        scenario.scenario_name,
        scenario.events,
        detector,
        OBSERVE_ONLY,
        driving_profile=profile_path,
        simulation_duration_ms=scenario.duration_ms,
    )
    event_start_ms = min(event.start_ms for event in scenario.events)
    first_detection_ms = full_validation.parse_int(
        source["runtime_detection_first_detection_ms"]
    )
    runtime_detected = (
        full_validation.parse_int(source["runtime_detection_detected"], 0) != 0
    )
    detected_after_event = int(
        runtime_detected and first_detection_ms >= event_start_ms
    )
    return {
        "experiment_family": "fault_injection",
        "scenario_id": scenario.scenario_id,
        "scenario_name": scenario.scenario_name,
        "scenario_group": scenario.scenario_group,
        "variant": "fault",
        "detector": detector,
        "event_start_ms": event_start_ms,
        "first_detection_ms": first_detection_ms,
        "detection_latency_ms": (
            first_detection_ms - event_start_ms
            if detected_after_event
            else -1
        ),
        "detected_after_event": detected_after_event,
        "false_positive_count": full_validation.parse_int(
            source["runtime_detection_false_positive_count"], 0
        ),
        "detection_label": source["runtime_detection_label"],
        "max_coolant_temp_c": full_validation.parse_float(
            source["max_coolant_temp_c"]
        ),
        "final_safe_state": source["final_safe_state"],
        "raw_csv": source["raw_csv"],
        "summary_csv": source["summary_csv"],
        "fault_type": "+".join(event.fault_type for event in scenario.events),
        "fault_severity": scenario.fault_severity,
        "fault_start_ms": event_start_ms,
        "profile_id": scenario.profile_id,
        "profile_name": scenario.profile_name,
        "trojan_target": "",
        "trojan_profile": "",
        "notes": scenario.notes,
    }


def run_non_rtl_matrix(
    executable: Path,
    output_dir: Path,
    profile_paths: Mapping[str, Path],
) -> List[Dict[str, object]]:
    scenarios = (*CLEAN_SCENARIOS, *FAULT_SCENARIOS)
    total = len(scenarios) * len(DETECTORS)
    results: List[Dict[str, object]] = []
    run_index = 0
    for scenario in scenarios:
        raw_dir = output_dir / scenario.scenario_id / "raw"
        profile_path = profile_path_for(scenario, profile_paths)
        for detector in DETECTORS:
            run_index += 1
            print(
                f"  [{run_index:03d}/{total}] "
                f"{scenario.scenario_id} / {detector}"
            )
            if scenario.variant == "clean":
                results.append(
                    clean_row(
                        executable,
                        raw_dir,
                        scenario,
                        detector,
                        profile_path,
                    )
                )
            else:
                results.append(
                    fault_row(
                        executable,
                        raw_dir,
                        scenario,
                        detector,
                        profile_path,
                    )
                )
    return results


def event_rows(
    rows: Sequence[Mapping[str, object]],
) -> List[Mapping[str, object]]:
    return [
        row for row in rows if row["variant"] in {"fault", "trojan"}
    ]


def detected_latencies(
    rows: Iterable[Mapping[str, object]],
) -> List[float]:
    return [
        float(row["detection_latency_ms"])
        for row in rows
        if full_validation.parse_int(row["detected_after_event"], 0) != 0
        and full_validation.parse_int(row["detection_latency_ms"]) >= 0
    ]


def metric(value: float | None) -> str:
    if value is None or math.isnan(value):
        return ""
    return f"{value:.1f}"


def coverage_summary(
    rows: Sequence[Mapping[str, object]],
) -> List[Dict[str, object]]:
    active = event_rows(rows)
    scopes: List[tuple[str, str]] = [("overall", "all_events")]
    scopes.extend(
        ("experiment_family", family)
        for family in sorted({str(row["experiment_family"]) for row in active})
    )
    scopes.extend(
        ("scenario_group", group)
        for group in sorted({str(row["scenario_group"]) for row in active})
    )
    summary: List[Dict[str, object]] = []
    for scope, value in scopes:
        for detector in DETECTORS:
            subset = [
                row
                for row in active
                if row["detector"] == detector
                and (
                    scope == "overall"
                    or str(row[scope]) == value
                )
            ]
            detected = sum(
                full_validation.parse_int(row["detected_after_event"], 0)
                for row in subset
            )
            latencies = detected_latencies(subset)
            total = len(subset)
            summary.append(
                {
                    "summary_scope": scope,
                    "scope_value": value,
                    "detector": detector,
                    "event_runs": total,
                    "detections": detected,
                    "misses": total - detected,
                    "coverage_percent": (
                        f"{100.0 * detected / total:.1f}" if total else ""
                    ),
                    "mean_detection_latency_ms": metric(
                        mean(latencies) if latencies else None
                    ),
                    "median_detection_latency_ms": metric(
                        median(latencies) if latencies else None
                    ),
                }
            )
    return summary


def clean_false_alarm_summary(
    rows: Sequence[Mapping[str, object]],
) -> List[Dict[str, object]]:
    clean = [row for row in rows if row["variant"] == "clean"]
    summary: List[Dict[str, object]] = []
    for detector in DETECTORS:
        groups = (
            ("overall", "all_clean", [row for row in clean if row["detector"] == detector]),
            *(
                (
                    "scenario",
                    scenario_id,
                    [
                        row
                        for row in clean
                        if row["detector"] == detector
                        and row["scenario_id"] == scenario_id
                    ],
                )
                for scenario_id in sorted(
                    {str(row["scenario_id"]) for row in clean}
                )
            ),
        )
        for scope, scenario_id, subset in groups:
            alarms = [
                row
                for row in subset
                if full_validation.parse_int(row["first_detection_ms"]) >= 0
                or full_validation.parse_int(row["false_positive_count"], 0) > 0
            ]
            times = [
                full_validation.parse_int(row["first_detection_ms"])
                for row in alarms
                if full_validation.parse_int(row["first_detection_ms"]) >= 0
            ]
            summary.append(
                {
                    "summary_scope": scope,
                    "scenario_id": scenario_id,
                    "detector": detector,
                    "clean_runs": len(subset),
                    "clean_runs_with_alarm": len(alarms),
                    "false_positive_episodes": sum(
                        full_validation.parse_int(
                            row["false_positive_count"], 0
                        )
                        for row in subset
                    ),
                    "earliest_clean_detection_ms": (
                        min(times) if times else -1
                    ),
                }
            )
    return summary


def missed_detection_summary(
    rows: Sequence[Mapping[str, object]],
) -> List[Mapping[str, object]]:
    return [
        row
        for row in event_rows(rows)
        if full_validation.parse_int(row["detected_after_event"], 0) == 0
    ]


def scenario_groups(
    rows: Sequence[Mapping[str, object]],
) -> Dict[tuple[str, str, str, str], List[Mapping[str, object]]]:
    groups: Dict[
        tuple[str, str, str, str], List[Mapping[str, object]]
    ] = defaultdict(list)
    for row in event_rows(rows):
        key = (
            str(row["experiment_family"]),
            str(row["scenario_id"]),
            str(row["scenario_name"]),
            str(row["scenario_group"]),
        )
        groups[key].append(row)
    return groups


def best_detector_summary(
    rows: Sequence[Mapping[str, object]],
) -> List[Dict[str, object]]:
    summary: List[Dict[str, object]] = []
    for key, subset in sorted(scenario_groups(rows).items()):
        family, scenario_id, scenario_name, group = key
        detected = [
            row
            for row in subset
            if full_validation.parse_int(row["detected_after_event"], 0) != 0
        ]
        best_latency = (
            min(
                full_validation.parse_int(row["detection_latency_ms"])
                for row in detected
            )
            if detected
            else -1
        )
        fastest = sorted(
            str(row["detector"])
            for row in detected
            if full_validation.parse_int(row["detection_latency_ms"])
            == best_latency
        )
        summary.append(
            {
                "experiment_family": family,
                "scenario_id": scenario_id,
                "scenario_name": scenario_name,
                "scenario_group": group,
                "fastest_detector": ";".join(fastest),
                "fastest_detection_latency_ms": best_latency,
                "detectors_detected": len(detected),
                "detectors_missed": len(subset) - len(detected),
                "missed_by_all": int(not detected),
            }
        )
    return summary


def hybrid_rank_summary(
    rows: Sequence[Mapping[str, object]],
) -> List[Dict[str, object]]:
    summary: List[Dict[str, object]] = []
    for key, subset in sorted(scenario_groups(rows).items()):
        family, scenario_id, scenario_name, group = key
        detected = [
            row
            for row in subset
            if full_validation.parse_int(row["detected_after_event"], 0) != 0
        ]
        best_latency = (
            min(
                full_validation.parse_int(row["detection_latency_ms"])
                for row in detected
            )
            if detected
            else -1
        )
        hybrid = next(
            row
            for row in subset
            if row["detector"] == "hybrid_adaptive_kalman"
        )
        hybrid_detected = (
            full_validation.parse_int(hybrid["detected_after_event"], 0) != 0
        )
        hybrid_latency = (
            full_validation.parse_int(hybrid["detection_latency_ms"])
            if hybrid_detected
            else -1
        )
        faster = sorted(
            str(row["detector"])
            for row in detected
            if hybrid_detected
            and full_validation.parse_int(row["detection_latency_ms"])
            < hybrid_latency
        )
        summary.append(
            {
                "scenario_id": scenario_id,
                "scenario_name": scenario_name,
                "scenario_group": group,
                "experiment_family": family,
                "hybrid_detected": int(hybrid_detected),
                "hybrid_latency_ms": hybrid_latency,
                "best_latency_ms": best_latency,
                "latency_gap_to_best_ms": (
                    hybrid_latency - best_latency
                    if hybrid_detected and best_latency >= 0
                    else -1
                ),
                "hybrid_rank": 1 + len(faster) if hybrid_detected else "",
                "tied_for_fastest": int(
                    hybrid_detected and hybrid_latency == best_latency
                ),
                "detectors_faster_than_hybrid": ";".join(faster),
                "detectors_missed_count": len(subset) - len(detected),
            }
        )
    return summary


def coverage_lookup(
    rows: Sequence[Mapping[str, object]],
) -> Dict[str, Mapping[str, object]]:
    return {
        str(row["detector"]): row
        for row in rows
        if row["summary_scope"] == "overall"
    }


def write_readme(
    path: Path,
    rows: Sequence[Mapping[str, object]],
) -> None:
    variants = {
        (str(row["scenario_id"]), str(row["variant"])) for row in rows
    }
    lines = [
        "# Expanded Runtime Validation",
        "",
        "This directory contains deterministic engineering validation artifacts, "
        "not paper-ready evidence or production ECU assurance.",
        "",
        "## Matrix",
        "",
        f"- Normalized detector rows: {len(rows)}",
        f"- Scenario/variant combinations: {len(variants)}",
        f"- Detectors: {len(DETECTORS)}",
        f"- Clean rows: {sum(row['variant'] == 'clean' for row in rows)}",
        f"- Fault rows: {sum(row['variant'] == 'fault' for row in rows)}",
        f"- Trojan rows: {sum(row['variant'] == 'trojan' for row in rows)}",
        "",
        "All fault runs use `observe_only`. Event and Trojan metadata is read "
        "after each run only for classification and latency calculation.",
        "",
        "## Main outputs",
        "",
        "- `expanded_combined_detection_latency_matrix.csv`",
        "- `expanded_detector_coverage_summary.csv`",
        "- `expanded_clean_false_alarm_summary.csv`",
        "- `expanded_missed_detection_summary.csv`",
        "- `expanded_best_detector_by_scenario.csv`",
        "- `expanded_hybrid_rank_by_scenario.csv`",
        "- `expanded_scenarios_where_hybrid_not_fastest.csv`",
        "- `expanded_validation_claim_summary.md`",
        "",
        "## Reproduction",
        "",
        "```sh",
        "make",
        "python3 scripts/run_expanded_runtime_validation.py",
        "```",
        "",
        "## Limitations",
        "",
        "- RTL coverage uses the four existing nominal trace-driven targets. "
        "Alternative RTL load profiles are not available without changing the "
        "current trace-generation architecture.",
        "- Multi-event latency is measured from the first ordered event; this "
        "matrix does not claim per-stage detection or isolation.",
        "- Fault parameters and profiles are deterministic supported simulator "
        "inputs, not statistical samples or vehicle calibrations.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_claim_summary(
    path: Path,
    rows: Sequence[Mapping[str, object]],
    coverage_rows: Sequence[Mapping[str, object]],
    clean_rows: Sequence[Mapping[str, object]],
    rank_rows: Sequence[Mapping[str, object]],
) -> None:
    lookup = coverage_lookup(coverage_rows)
    overall_clean = [
        row for row in clean_rows if row["summary_scope"] == "overall"
    ]
    clean_alarm_runs = sum(
        full_validation.parse_int(row["clean_runs_with_alarm"], 0)
        for row in overall_clean
    )
    clean_episodes = sum(
        full_validation.parse_int(row["false_positive_episodes"], 0)
        for row in overall_clean
    )
    misses = missed_detection_summary(rows)
    slower = [
        row
        for row in rank_rows
        if full_validation.parse_int(row["hybrid_detected"], 0) != 0
        and str(row["detectors_faster_than_hybrid"]) != ""
    ]
    lines = [
        "# Expanded Runtime Validation Claim Summary",
        "",
        "This is a deterministic engineering summary, not paper-ready evidence.",
        "",
        "## Matrix result",
        "",
        f"- Normalized detector runs: {len(rows)}.",
        f"- Clean detector runs: "
        f"{sum(row['variant'] == 'clean' for row in rows)}.",
        f"- Clean runs with alarms: {clean_alarm_runs}.",
        f"- Clean false-positive episodes: {clean_episodes}.",
        f"- Missed detector/scenario pairs: {len(misses)}.",
        "",
        "## Overall detector coverage and detected-case latency",
        "",
        "| Detector | Coverage | Misses | Mean latency [ms] | Median latency [ms] |",
        "|---|---:|---:|---:|---:|",
    ]
    for detector in DETECTORS:
        row = lookup[detector]
        lines.append(
            f"| {detector} | {row['detections']}/{row['event_runs']} "
            f"({row['coverage_percent']}%) | {row['misses']} | "
            f"{row['mean_detection_latency_ms'] or 'n/a'} | "
            f"{row['median_detection_latency_ms'] or 'n/a'} |"
        )

    lines.extend(
        [
            "",
            "Misses remain separate from latency statistics; a missed detection "
            "is never ranked as faster.",
            "",
            "## Hybrid Adaptive Kalman",
            "",
        ]
    )
    hybrid = lookup["hybrid_adaptive_kalman"]
    lines.append(
        f"- Coverage: {hybrid['detections']}/{hybrid['event_runs']} "
        f"({hybrid['coverage_percent']}%)."
    )
    lines.append(
        f"- Detected-case mean/median latency: "
        f"{hybrid['mean_detection_latency_ms'] or 'n/a'} / "
        f"{hybrid['median_detection_latency_ms'] or 'n/a'} ms."
    )
    lines.append(
        f"- Scenarios where another detector is faster: {len(slower)}."
    )
    for row in slower:
        lines.append(
            f"- {row['scenario_id']}: Hybrid {row['hybrid_latency_ms']} ms, "
            f"best {row['best_latency_ms']} ms, gap "
            f"{row['latency_gap_to_best_ms']} ms; faster: "
            f"{row['detectors_faster_than_hybrid']}."
        )

    lines.extend(
        [
            "",
            "## Comparison detectors",
            "",
        ]
    )
    for detector in (
        "threshold",
        "kalman_filter",
        "adaptive_kalman_filter",
        "hybrid_adaptive_kalman",
    ):
        row = lookup[detector]
        lines.append(
            f"- {detector}: {row['detections']}/{row['event_runs']} coverage, "
            f"{row['misses']} misses, mean/median "
            f"{row['mean_detection_latency_ms'] or 'n/a'} / "
            f"{row['median_detection_latency_ms'] or 'n/a'} ms."
        )

    miss_groups: Dict[str, set[str]] = defaultdict(set)
    for row in misses:
        miss_groups[str(row["detector"])].add(str(row["scenario_group"]))
    lines.extend(["", "## Missed scenario groups", ""])
    for detector in DETECTORS:
        groups = sorted(miss_groups.get(detector, set()))
        lines.append(
            f"- {detector}: {', '.join(groups) if groups else 'none'}."
        )

    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- RTL variation is limited to the four existing nominal "
            "trace-driven targets.",
            "- Multi-event latency is measured from the first event.",
            "- Coverage and latency apply only to these deterministic profiles "
            "and parameters.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    if len(CLEAN_SCENARIOS) != 5 or len(FAULT_SCENARIOS) != 27:
        raise RuntimeError("Expanded scenario catalog must contain 5 clean and 27 fault variants.")

    output_dir = args.output_dir.resolve()
    executable = args.executable.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_paths = write_profiles(output_dir)

    print("[1/4] Running four clean and four Trojan RTL target variants")
    rtl_dir = output_dir / "rtl_security"
    run_checked(
        (
            sys.executable,
            str(RTL_STUDY_SCRIPT),
            "--target",
            "all",
            "--output-dir",
            str(rtl_dir),
            "--executable",
            str(executable),
            "--simulation-duration-ms",
            "120000",
        ),
        "expanded RTL study",
    )
    rtl_rows = normalize_rtl_rows(rtl_dir / "detector_comparison.csv")

    print("[2/4] Running five clean and twenty-seven fault variants")
    non_rtl_rows = run_non_rtl_matrix(
        executable,
        output_dir / "runtime",
        profile_paths,
    )
    rows = rtl_rows + non_rtl_rows
    variants = {
        (str(row["scenario_id"]), str(row["variant"])) for row in rows
    }
    if len(rows) != EXPECTED_NORMALIZED_ROWS or len(variants) != EXPECTED_VARIANTS:
        raise RuntimeError(
            f"Expected {EXPECTED_NORMALIZED_ROWS} rows across "
            f"{EXPECTED_VARIANTS} variants; got {len(rows)} rows across "
            f"{len(variants)} variants."
        )

    print("[3/4] Writing expanded engineering summaries")
    coverage_rows = coverage_summary(rows)
    clean_rows = clean_false_alarm_summary(rows)
    missed_rows = missed_detection_summary(rows)
    best_rows = best_detector_summary(rows)
    rank_rows = hybrid_rank_summary(rows)
    slower_rows = [
        row
        for row in rank_rows
        if full_validation.parse_int(row["hybrid_detected"], 0) != 0
        and str(row["detectors_faster_than_hybrid"]) != ""
    ]

    write_rows(
        output_dir / "expanded_combined_detection_latency_matrix.csv",
        EXPANDED_COLUMNS,
        rows,
    )
    write_rows(
        output_dir / "expanded_detector_coverage_summary.csv",
        (
            "summary_scope",
            "scope_value",
            "detector",
            "event_runs",
            "detections",
            "misses",
            "coverage_percent",
            "mean_detection_latency_ms",
            "median_detection_latency_ms",
        ),
        coverage_rows,
    )
    write_rows(
        output_dir / "expanded_clean_false_alarm_summary.csv",
        (
            "summary_scope",
            "scenario_id",
            "detector",
            "clean_runs",
            "clean_runs_with_alarm",
            "false_positive_episodes",
            "earliest_clean_detection_ms",
        ),
        clean_rows,
    )
    write_rows(
        output_dir / "expanded_missed_detection_summary.csv",
        EXPANDED_COLUMNS,
        missed_rows,
    )
    write_rows(
        output_dir / "expanded_best_detector_by_scenario.csv",
        (
            "experiment_family",
            "scenario_id",
            "scenario_name",
            "scenario_group",
            "fastest_detector",
            "fastest_detection_latency_ms",
            "detectors_detected",
            "detectors_missed",
            "missed_by_all",
        ),
        best_rows,
    )
    rank_columns = (
        "scenario_id",
        "scenario_name",
        "scenario_group",
        "experiment_family",
        "hybrid_detected",
        "hybrid_latency_ms",
        "best_latency_ms",
        "latency_gap_to_best_ms",
        "hybrid_rank",
        "tied_for_fastest",
        "detectors_faster_than_hybrid",
        "detectors_missed_count",
    )
    write_rows(
        output_dir / "expanded_hybrid_rank_by_scenario.csv",
        rank_columns,
        rank_rows,
    )
    write_rows(
        output_dir / "expanded_scenarios_where_hybrid_not_fastest.csv",
        rank_columns,
        slower_rows,
    )
    write_readme(output_dir / "README.md", rows)
    write_claim_summary(
        output_dir / "expanded_validation_claim_summary.md",
        rows,
        coverage_rows,
        clean_rows,
        rank_rows,
    )

    print("[4/4] Expanded runtime validation complete")
    print(f"Output directory: {output_dir}")
    print(f"Normalized detector rows: {len(rows)}")
    print(
        "Clean detector rows: "
        f"{sum(row['variant'] == 'clean' for row in rows)}"
    )
    print(f"Missed detector/scenario pairs: {len(missed_rows)}")
    print(f"Scenarios where Hybrid is not fastest: {len(slower_rows)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"Expanded runtime validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
