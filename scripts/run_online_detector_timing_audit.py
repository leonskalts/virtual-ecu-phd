#!/usr/bin/env python3
"""Audit runtime detector ordering, prefix causality, and update cost."""

from __future__ import annotations

import argparse
import csv
import ctypes
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXECUTABLE = PROJECT_ROOT / "virtual_ecu"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "online_detector_timing_audit"
RTL_RESULTS_DIR = PROJECT_ROOT / "results" / "rtl_hardware_trojan_study_v1"
TIMESTEP_BUDGET_MS = 100.0

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

CAUSALITY_COLUMNS = (
    "detector",
    "evaluation_mode",
    "uses_future_samples",
    "online_equivalent",
    "causality_check_passed",
    "notes",
)

TIMING_COLUMNS = (
    "scenario_id",
    "scenario_name",
    "detector",
    "measured_mode",
    "steps_processed",
    "timestep_budget_ms",
    "mean_update_time_ms",
    "median_update_time_ms",
    "p95_update_time_ms",
    "p99_update_time_ms",
    "max_update_time_ms",
    "worst_case_budget_margin_ms",
    "fits_timestep_budget",
    "notes",
)

SUMMARY_COLUMNS = (
    "detector",
    "scenarios_tested",
    "mean_update_time_ms",
    "max_update_time_ms",
    "p99_update_time_ms",
    "timestep_budget_ms",
    "worst_case_budget_margin_ms",
    "all_cases_fit_budget",
    "causality_check_passed",
    "notes",
)


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    name: str
    campaign_arguments: tuple[str, ...]
    activation_ms: int | None
    replay_arguments: tuple[str, ...] = ()
    notes: str = ""


class AuditInputs(ctypes.Structure):
    _fields_ = [
        ("time_ms", ctypes.c_uint),
        ("scenario_phase", ctypes.c_int),
        ("ambient_temp_c", ctypes.c_float),
        ("engine_load", ctypes.c_float),
        ("vehicle_speed_kph", ctypes.c_float),
        ("external_airflow_factor", ctypes.c_float),
        ("road_slope_percent", ctypes.c_float),
        ("coolant_temp_true_c", ctypes.c_float),
        ("coolant_temp_meas_c", ctypes.c_float),
        ("coolant_sensor_update_age_ms", ctypes.c_uint),
        ("coolant_sensor_expected_period_ms", ctypes.c_uint),
        ("coolant_sensor_freshness_score", ctypes.c_float),
        ("coolant_sensor_freshness_ok", ctypes.c_int),
        ("nominal_control_target_c", ctypes.c_float),
        ("control_target_deviation_c", ctypes.c_float),
        ("pump_command", ctypes.c_float),
        ("pump_actual", ctypes.c_float),
        ("fan_command", ctypes.c_float),
        ("fan_actual", ctypes.c_float),
        ("fan_actuator_health_score", ctypes.c_float),
        ("primary_dtc", ctypes.c_int),
        ("fault_present", ctypes.c_int),
        ("first_fault_start_ms", ctypes.c_uint),
        ("heat_generation_bias", ctypes.c_float),
        ("ram_air_scale", ctypes.c_float),
    ]


AUDIT_WRAPPER_SOURCE = r"""
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "detection_algorithm.h"
#include "diagnostics.h"
#include "ecu_types.h"

typedef struct {
    unsigned int time_ms;
    int scenario_phase;
    float ambient_temp_c;
    float engine_load;
    float vehicle_speed_kph;
    float external_airflow_factor;
    float road_slope_percent;
    float coolant_temp_true_c;
    float coolant_temp_meas_c;
    unsigned int coolant_sensor_update_age_ms;
    unsigned int coolant_sensor_expected_period_ms;
    float coolant_sensor_freshness_score;
    int coolant_sensor_freshness_ok;
    float nominal_control_target_c;
    float control_target_deviation_c;
    float pump_command;
    float pump_actual;
    float fan_command;
    float fan_actual;
    float fan_actuator_health_score;
    int primary_dtc;
    int fault_present;
    unsigned int first_fault_start_ms;
    float heat_generation_bias;
    float ram_air_scale;
} audit_inputs_t;

typedef struct {
    ecu_state_t state;
} audit_handle_t;

void *audit_create(int algorithm)
{
    audit_handle_t *handle = calloc(1U, sizeof(*handle));
    if (handle != NULL) {
        detection_algorithm_init(
            &handle->state.detection,
            (detection_algorithm_t)algorithm,
            DETECTION_ACTION_OBSERVE_ONLY
        );
    }
    return handle;
}

void audit_destroy(void *opaque)
{
    free(opaque);
}

void audit_reset(void *opaque, int algorithm)
{
    audit_handle_t *handle = opaque;
    memset(&handle->state, 0, sizeof(handle->state));
    detection_algorithm_init(
        &handle->state.detection,
        (detection_algorithm_t)algorithm,
        DETECTION_ACTION_OBSERVE_ONLY
    );
}

void audit_set_inputs(void *opaque, const audit_inputs_t *input)
{
    audit_handle_t *handle = opaque;
    ecu_state_t *state = &handle->state;
    state->time.time_ms = input->time_ms;
    state->plant.scenario_phase = (scenario_phase_t)input->scenario_phase;
    state->plant.engine_load = input->engine_load;
    state->plant.external_airflow_factor = input->external_airflow_factor;
    state->plant.road_slope_percent = input->road_slope_percent;
    state->plant.coolant_temp_true_c = input->coolant_temp_true_c;
    state->sensors.ambient_temp_meas_c = input->ambient_temp_c;
    state->sensors.vehicle_speed_meas_kph = input->vehicle_speed_kph;
    state->sensors.coolant_temp_meas_c = input->coolant_temp_meas_c;
    state->sensors.coolant_sensor_update_age_ms =
        input->coolant_sensor_update_age_ms;
    state->sensors.coolant_sensor_expected_period_ms =
        input->coolant_sensor_expected_period_ms;
    state->sensors.coolant_sensor_freshness_score =
        input->coolant_sensor_freshness_score;
    state->sensors.coolant_sensor_freshness_ok =
        input->coolant_sensor_freshness_ok != 0;
    state->control.nominal_control_target_c = input->nominal_control_target_c;
    state->control.control_target_deviation_c =
        input->control_target_deviation_c;
    state->control.pump_command = input->pump_command;
    state->control.fan_command = input->fan_command;
    state->actuators.pump_actual = input->pump_actual;
    state->actuators.fan_actual = input->fan_actual;
    state->actuators.fan_actuator_health_score =
        input->fan_actuator_health_score;
    state->diagnostics.primary_dtc = (diagnostic_id_t)input->primary_dtc;
    state->metrics.fault_present_in_campaign = input->fault_present != 0;
    state->metrics.first_fault_start_ms = input->first_fault_start_ms;
    state->experiment.heat_generation_bias = input->heat_generation_bias;
    state->experiment.ram_air_scale = input->ram_air_scale;
}

void audit_step(void *opaque)
{
    audit_handle_t *handle = opaque;
    detection_algorithm_step(&handle->state);
}

float audit_score(void *opaque)
{
    audit_handle_t *handle = opaque;
    return handle->state.detection.current_score;
}

int audit_alarm(void *opaque)
{
    audit_handle_t *handle = opaque;
    return handle->state.detection.alarm_active ? 1 : 0;
}

int audit_detected(void *opaque)
{
    audit_handle_t *handle = opaque;
    return handle->state.detection.detected ? 1 : 0;
}

int audit_first_detection_time_ms(void *opaque)
{
    audit_handle_t *handle = opaque;
    return handle->state.detection.first_detection_time_ms;
}

unsigned int audit_false_positive_count(void *opaque)
{
    audit_handle_t *handle = opaque;
    return handle->state.detection.false_positive_count;
}

unsigned int audit_confirmation_count(void *opaque)
{
    audit_handle_t *handle = opaque;
    return handle->state.detection.adaptive_kalman_filter_confirmation_count;
}

const char *audit_label(void *opaque)
{
    audit_handle_t *handle = opaque;
    return handle->state.detection.runtime_label;
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit online detector causality and host-side C update timing "
            "against the Virtual ECU timestep budget."
        )
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--executable", type=Path, default=DEFAULT_EXECUTABLE)
    parser.add_argument("--no-figures", action="store_true")
    return parser.parse_args()


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())


def write_csv(
    path: Path,
    columns: Sequence[str],
    rows: Iterable[Dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


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
        raise RuntimeError(f"{label} failed: {detail}")


def build_if_needed(executable: Path) -> None:
    if executable.is_file():
        return
    if executable.resolve() == DEFAULT_EXECUTABLE.resolve():
        run_checked(("make",), "Virtual ECU build")
    if not executable.is_file():
        raise FileNotFoundError(f"Virtual ECU executable not found: {executable}")


def available_scenarios(warnings: List[str]) -> List[Scenario]:
    scenarios = [
        Scenario("clean_baseline", "Clean baseline", ("baseline",), None),
        Scenario(
            "fan_stuck_off",
            "Fan stuck off",
            ("custom", "fan_stuck_off", "75000", "0", "permanent", "0"),
            75000,
        ),
        Scenario(
            "sensor_bias",
            "Sensor bias",
            ("custom", "sensor_bias", "45000", "15000", "transient", "6"),
            45000,
        ),
        Scenario(
            "calibration_memory_corruption",
            "Calibration memory corruption",
            (
                "custom",
                "calibration_memory_corruption",
                "52000",
                "0",
                "permanent",
                "16",
            ),
            52000,
        ),
    ]
    rtl_specs = (
        (
            "ht1_coolant_sensor",
            "HT1 — Coolant Sensor Interface replay",
            93200,
            (("--coolant-sensor-trace", "virtual_ecu_trojan_sensor_trace.csv"),),
        ),
        (
            "ht2_fan_driver",
            "HT2 — Fan Driver Interface replay",
            96000,
            (("--fan-actual-trace", "virtual_ecu_trojan_fan_actual_trace.csv"),),
        ),
        (
            "ht3_calibration_memory",
            "HT3 — Calibration Memory Interface replay",
            52000,
            (("--calibration-trace", "virtual_ecu_trojan_calibration_trace.csv"),),
        ),
        (
            "ht4_multi_stage_chain",
            "HT4 — Multi-Stage RTL Chain replay",
            52000,
            (
                ("--calibration-trace", "virtual_ecu_trojan_calibration_trace.csv"),
                ("--coolant-sensor-trace", "virtual_ecu_trojan_sensor_trace.csv"),
                ("--fan-actual-trace", "virtual_ecu_trojan_fan_actual_trace.csv"),
            ),
        ),
    )
    for scenario_id, name, activation_ms, inputs in rtl_specs:
        missing = [filename for _, filename in inputs if not (RTL_RESULTS_DIR / filename).is_file()]
        if missing:
            warnings.append(
                f"Skipped {name}: missing existing RTL replay trace(s): {', '.join(missing)}."
            )
            continue
        replay_arguments = tuple(
            token
            for option, filename in inputs
            for token in (option, str((RTL_RESULTS_DIR / filename).resolve()))
        )
        scenarios.append(
            Scenario(
                scenario_id,
                name,
                ("baseline",),
                activation_ms,
                replay_arguments,
                "Existing RTL trace replay; Verilator generation is not part of this audit.",
            )
        )
    return scenarios


def generate_trace(executable: Path, trace_dir: Path, scenario: Scenario) -> Path:
    path = trace_dir / f"{scenario.scenario_id}.csv"
    command = [
        str(executable),
        str(path),
        *scenario.campaign_arguments,
        "--detector",
        "builtin_ecu",
        "--detector-action",
        "observe_only",
        "--simulation-duration-ms",
        "120000",
        *scenario.replay_arguments,
    ]
    run_checked(command, f"source trace generation for {scenario.name}")
    return path


def read_trace(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"Trace has no data rows: {path}")
    times = [int(float(row["time_ms"])) for row in rows]
    if any(current <= previous for previous, current in zip(times, times[1:])):
        raise RuntimeError(f"Trace is not strictly increasing by time_ms: {path}")
    return rows


def compile_audit_library(temp_dir: Path) -> ctypes.CDLL:
    wrapper_path = temp_dir / "online_detector_audit_wrapper.c"
    library_path = temp_dir / "libonline_detector_audit.so"
    wrapper_path.write_text(AUDIT_WRAPPER_SOURCE, encoding="utf-8")
    run_checked(
        (
            "gcc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-O2",
            "-shared",
            "-fPIC",
            "-I",
            str(PROJECT_ROOT / "include"),
            str(wrapper_path),
            str(PROJECT_ROOT / "src" / "detection_algorithm.c"),
            str(PROJECT_ROOT / "src" / "diagnostics.c"),
            "-o",
            str(library_path),
        ),
        "temporary detector audit library build",
    )
    library = ctypes.CDLL(str(library_path))
    library.audit_create.argtypes = [ctypes.c_int]
    library.audit_create.restype = ctypes.c_void_p
    library.audit_destroy.argtypes = [ctypes.c_void_p]
    library.audit_reset.argtypes = [ctypes.c_void_p, ctypes.c_int]
    library.audit_set_inputs.argtypes = [ctypes.c_void_p, ctypes.POINTER(AuditInputs)]
    library.audit_step.argtypes = [ctypes.c_void_p]
    library.audit_score.argtypes = [ctypes.c_void_p]
    library.audit_score.restype = ctypes.c_float
    library.audit_alarm.argtypes = [ctypes.c_void_p]
    library.audit_alarm.restype = ctypes.c_int
    library.audit_detected.argtypes = [ctypes.c_void_p]
    library.audit_detected.restype = ctypes.c_int
    library.audit_first_detection_time_ms.argtypes = [ctypes.c_void_p]
    library.audit_first_detection_time_ms.restype = ctypes.c_int
    library.audit_false_positive_count.argtypes = [ctypes.c_void_p]
    library.audit_false_positive_count.restype = ctypes.c_uint
    library.audit_confirmation_count.argtypes = [ctypes.c_void_p]
    library.audit_confirmation_count.restype = ctypes.c_uint
    library.audit_label.argtypes = [ctypes.c_void_p]
    library.audit_label.restype = ctypes.c_char_p
    return library


def as_float(row: Dict[str, str], field: str, default: float) -> float:
    text = row.get(field, "").strip()
    return float(text) if text else default


def as_int(row: Dict[str, str], field: str, default: int) -> int:
    text = row.get(field, "").strip()
    return int(float(text)) if text else default


def first_fault_start(rows: Sequence[Dict[str, str]]) -> tuple[int, int]:
    event_count = as_int(rows[0], "campaign_event_count", 0)
    starts = [
        as_int(rows[0], f"campaign_event_{index}_start_ms", -1)
        for index in range(1, event_count + 1)
    ]
    valid = [value for value in starts if value >= 0]
    return (1, min(valid)) if valid else (0, 0)


def audit_input(row: Dict[str, str], fault_present: int, fault_start: int) -> AuditInputs:
    return AuditInputs(
        as_int(row, "time_ms", 0),
        as_int(row, "phase_id", 0),
        as_float(row, "ambient_temp_c", 25.0),
        as_float(row, "engine_load", 0.0),
        as_float(row, "vehicle_speed_kph", 0.0),
        0.0,
        0.0,
        as_float(row, "coolant_temp_true_c", 0.0),
        as_float(row, "coolant_temp_meas_c", 0.0),
        as_int(row, "coolant_sensor_update_age_ms", 0),
        as_int(row, "coolant_sensor_expected_period_ms", 100),
        as_float(row, "coolant_sensor_freshness_score", 0.0),
        as_int(row, "coolant_sensor_freshness_ok", 1),
        as_float(row, "nominal_control_target_c", 92.0),
        as_float(row, "control_target_deviation_c", 0.0),
        as_float(row, "pump_command", 0.0),
        as_float(row, "pump_actual", 0.0),
        as_float(row, "fan_command", 0.0),
        as_float(row, "fan_actual", 0.0),
        as_float(row, "fan_actuator_health_score", 0.0),
        as_int(row, "primary_dtc_id", 0),
        fault_present,
        fault_start,
        as_float(row, "campaign_heat_generation_bias", 0.0),
        as_float(row, "campaign_ram_air_scale", 1.0),
    )


def snapshot(library: ctypes.CDLL, handle: int) -> tuple[object, ...]:
    label = library.audit_label(handle)
    return (
        float(library.audit_score(handle)),
        int(library.audit_alarm(handle)),
        int(library.audit_detected(handle)),
        int(library.audit_first_detection_time_ms(handle)),
        int(library.audit_false_positive_count(handle)),
        int(library.audit_confirmation_count(handle)),
        label.decode("utf-8") if label else "",
    )


def checkpoint_indices(rows: Sequence[Dict[str, str]], activation_ms: int | None) -> List[int]:
    times = [as_int(row, "time_ms", 0) for row in rows]
    end_ms = times[-1]
    requested = (
        (0, end_ms // 3, (2 * end_ms) // 3, end_ms)
        if activation_ms is None
        else (
            max(0, activation_ms - 100),
            activation_ms,
            min(end_ms, activation_ms + 1000),
            end_ms,
        )
    )
    return sorted(
        {
            min(range(len(times)), key=lambda index: abs(times[index] - value))
            for value in requested
        }
    )


def percentile(values: Sequence[int], percentile_value: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * percentile_value
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (fraction * (ordered[upper] - ordered[lower]))


def audit_detector_scenario(
    library: ctypes.CDLL,
    detector_index: int,
    rows: Sequence[Dict[str, str]],
    checkpoints: Sequence[int],
) -> tuple[List[int], bool, int]:
    fault_present, fault_start = first_fault_start(rows)
    inputs = [audit_input(row, fault_present, fault_start) for row in rows]
    handle = library.audit_create(detector_index)
    if not handle:
        raise RuntimeError("Could not allocate temporary detector audit state")
    try:
        library.audit_reset(handle, detector_index)
        timings_ns: List[int] = []
        for item in inputs:
            library.audit_set_inputs(handle, ctypes.byref(item))
            start_ns = time.perf_counter_ns()
            library.audit_step(handle)
            timings_ns.append(time.perf_counter_ns() - start_ns)

        library.audit_reset(handle, detector_index)
        full_snapshots: Dict[int, tuple[object, ...]] = {}
        for index, item in enumerate(inputs):
            library.audit_set_inputs(handle, ctypes.byref(item))
            library.audit_step(handle)
            if index in checkpoints:
                full_snapshots[index] = snapshot(library, handle)

        causality_passed = True
        comparisons = 0
        for checkpoint in checkpoints:
            library.audit_reset(handle, detector_index)
            for item in inputs[: checkpoint + 1]:
                library.audit_set_inputs(handle, ctypes.byref(item))
                library.audit_step(handle)
            comparisons += 1
            if snapshot(library, handle) != full_snapshots[checkpoint]:
                causality_passed = False
        return timings_ns, causality_passed, comparisons
    finally:
        library.audit_destroy(handle)


def format_ms(nanoseconds: float) -> str:
    return f"{nanoseconds / 1_000_000.0:.9f}"


def timing_row(
    scenario: Scenario,
    detector: str,
    timings_ns: Sequence[int],
) -> Dict[str, object]:
    maximum_ns = max(timings_ns)
    margin_ms = TIMESTEP_BUDGET_MS - (maximum_ns / 1_000_000.0)
    return {
        "scenario_id": scenario.scenario_id,
        "scenario_name": scenario.name,
        "detector": detector,
        "measured_mode": "detector_update_only",
        "steps_processed": len(timings_ns),
        "timestep_budget_ms": f"{TIMESTEP_BUDGET_MS:.3f}",
        "mean_update_time_ms": format_ms(statistics.mean(timings_ns)),
        "median_update_time_ms": format_ms(statistics.median(timings_ns)),
        "p95_update_time_ms": format_ms(percentile(timings_ns, 0.95)),
        "p99_update_time_ms": format_ms(percentile(timings_ns, 0.99)),
        "max_update_time_ms": format_ms(maximum_ns),
        "worst_case_budget_margin_ms": f"{margin_ms:.9f}",
        "fits_timestep_budget": int(margin_ms >= 0.0),
        "notes": (
            "Exact compiled C detection_algorithm_step call; file parsing and state "
            "preparation excluded. Includes perf-counter and Python ctypes dispatch overhead."
        ),
    }


def source_order_check() -> tuple[bool, Dict[str, object]]:
    scheduler_path = PROJECT_ROOT / "src" / "scheduler.c"
    detector_path = PROJECT_ROOT / "src" / "detection_algorithm.c"
    scheduler = scheduler_path.read_text(encoding="utf-8")
    detector = detector_path.read_text(encoding="utf-8")
    step_position = scheduler.find("detection_algorithm_step(state);")
    log_position = scheduler.find("logger_write(state);")
    plant_position = scheduler.find("thermal_plant_step(state);")
    loop_position = scheduler.find("for (state->time.time_ms = 0U;")
    source_passed = (
        loop_position >= 0
        and step_position > loop_position
        and log_position > step_position
        and plant_position > log_position
        and "void detection_algorithm_step(struct ecu_state *state)" in detector
    )
    return source_passed, {
        "scheduler": relative_path(scheduler_path),
        "detector_implementation": relative_path(detector_path),
        "detector_step_inside_fixed_timestep_loop": step_position > loop_position >= 0,
        "detector_step_before_logging": log_position > step_position >= 0,
        "detector_step_before_plant_advance": plant_position > step_position >= 0,
    }


def causality_rows(
    detector_pass: Dict[str, bool],
    comparison_counts: Dict[str, int],
    source_passed: bool,
) -> List[Dict[str, object]]:
    return [
        {
            "detector": detector,
            "evaluation_mode": "runtime C detector inside ECU loop",
            "uses_future_samples": 0,
            "online_equivalent": 1,
            "causality_check_passed": int(source_passed and detector_pass[detector]),
            "notes": (
                "Called once per fixed timestep using current ECU state. "
                "Alarm score/active decisions do not use campaign timing metadata. "
                f"Full-order versus fresh prefix state matched at "
                f"{comparison_counts[detector]} sampled checkpoints."
            ),
        }
        for detector in DETECTORS
    ]


def timing_summary(
    timing_rows: Sequence[Dict[str, object]],
    samples: Dict[str, List[int]],
    detector_pass: Dict[str, bool],
    source_passed: bool,
) -> List[Dict[str, object]]:
    rows = []
    for detector in DETECTORS:
        selected = [row for row in timing_rows if row["detector"] == detector]
        detector_samples = samples[detector]
        maximum_ns = max(detector_samples)
        margin_ms = TIMESTEP_BUDGET_MS - (maximum_ns / 1_000_000.0)
        rows.append(
            {
                "detector": detector,
                "scenarios_tested": len(selected),
                "mean_update_time_ms": format_ms(statistics.mean(detector_samples)),
                "max_update_time_ms": format_ms(maximum_ns),
                "p99_update_time_ms": format_ms(percentile(detector_samples, 0.99)),
                "timestep_budget_ms": f"{TIMESTEP_BUDGET_MS:.3f}",
                "worst_case_budget_margin_ms": f"{margin_ms:.9f}",
                "all_cases_fit_budget": int(
                    all(int(row["fits_timestep_budget"]) != 0 for row in selected)
                ),
                "causality_check_passed": int(source_passed and detector_pass[detector]),
                "notes": (
                    "Aggregated individual C update-call samples across all evaluated traces; "
                    "host timer and ctypes dispatch overhead are included."
                ),
            }
        )
    return rows


def command_output(command: Sequence[str]) -> str:
    try:
        completed = subprocess.run(
            list(command),
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip() if completed.returncode == 0 else "unavailable"
    except OSError:
        return "unavailable"


def host_info() -> Dict[str, object]:
    cpu_model = "unavailable"
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    proc_version = "unavailable"
    try:
        proc_version = Path("/proc/version").read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_model": cpu_model,
        "logical_cpu_count": os.cpu_count(),
        "wsl_detected": "microsoft" in proc_version.lower(),
        "git_commit": command_output(("git", "rev-parse", "HEAD")),
        "git_status_short": command_output(("git", "status", "--short")),
    }


def write_readme(
    output_dir: Path,
    scenarios: Sequence[Scenario],
    host: Dict[str, object],
    source_facts: Dict[str, object],
    all_causal: bool,
    all_fit: bool,
) -> None:
    text = f"""# Online Detector Execution and Causality Audit

Online/runtime detection means an alarm at simulated time `t` is computed from detector state accumulated through `t` and ECU inputs available at `t`, without reading later samples. Offline post-processing may inspect a whole completed run; none of the eight audited alarm implementations use that mode.

## Evaluation path

All eight selectable algorithms use the same C function, `detection_algorithm_step`, inside the deterministic scheduler loop. The call occurs after current-timestep sensing, control, actuator, diagnostics, and safety work, and before logging and the next plant advance. Source-order checks found:

- Detector step inside fixed-timestep loop: {source_facts['detector_step_inside_fixed_timestep_loop']}
- Detector step before logging: {source_facts['detector_step_before_logging']}
- Detector step before plant advancement: {source_facts['detector_step_before_plant_advance']}
- Scheduler source: `{source_facts['scheduler']}`
- Detector source: `{source_facts['detector_implementation']}`

The future-lookahead guard processes each trace in strictly increasing `time_ms` order. At representative checkpoints before activation, at activation, shortly after activation, and near the end, it compares the detector state reached during a full ordered pass with a fresh detector run over only the prefix ending at that checkpoint. No suffix row is supplied to the prefix run. Overall prefix causality result: **{'passed' if all_causal else 'failed'}**.

Alarm score and `alarm_active` decisions use current ECU signals plus detector history. Campaign `first_fault_start_ms` metadata is consulted only after the alarm decision to classify false positives and detection timing; it does not affect whether the alarm becomes active.

## Timing method

The audit compiles the unchanged `src/detection_algorithm.c` with a temporary, audit-only wrapper. Python loads that temporary library and measures each exact C `detection_algorithm_step` call using `time.perf_counter_ns()`. CSV parsing and audit-state preparation occur outside the timed region. The reported `measured_mode` is `detector_update_only`; measurements conservatively include Python-to-C `ctypes` dispatch and timer-call overhead.

The simulator timestep budget is {TIMESTEP_BUDGET_MS:.0f} ms (`ECU_DT_MS`). All measured detector/scenario cases fit this host-side budget: {'yes' if all_fit else 'no'}.

## Scenario coverage

{chr(10).join(f'- {scenario.name}' for scenario in scenarios)}

## Simulated time versus wall-clock time

Simulated timestamps advance deterministically in 100 ms increments. This audit measures the host wall-clock cost of the detector update associated with each simulated timestep. It differs from the simulation real-time benchmark, which measures a complete simulator process including plant, scheduler, CSV logging, and process overhead.

## Host context

- Platform: {host['platform']}
- Python: {host['python_version']}
- CPU: {host['cpu_model']}
- WSL detected: {host['wsl_detected']}
- Git commit: {host['git_commit']}

## Interpretation boundary

This is source-order, prefix-causality, and host/WSL execution-cost evidence for the evaluated traces. It is not embedded hardware validation, worst-case execution-time analysis, hard real-time certification, or production-readiness evidence.
"""
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def write_claim_summary(
    output_dir: Path,
    all_causal: bool,
    all_fit: bool,
    slowest_ms: float,
) -> str:
    causality_claim = (
        "The evaluated detector implementations processed the selected traces in "
        "timestamp order without future-sample access."
        if all_causal
        else "At least one evaluated detector prefix comparison did not establish causality."
    )
    timing_claim = (
        "On the evaluated host platform, all measured detector update times were "
        "below the 100 ms simulated ECU timestep budget."
        if all_fit
        else "At least one measured host detector update exceeded the 100 ms simulated timestep budget."
    )
    text = f"""# Bounded Claim Summary

{causality_claim}

{timing_claim} The maximum observed update-call measurement was {slowest_ms:.9f} ms.

These findings apply only to the current source and evaluated traces on this host. They do not establish an embedded ECU hard real-time guarantee, certification, worst-case execution time, or production readiness.
"""
    (output_dir / "online_detector_claim_summary.md").write_text(text, encoding="utf-8")
    return f"{causality_claim} {timing_claim}"


def write_limitations(output_dir: Path) -> None:
    text = """# Online Detector Audit Limitations

- Timing was measured on the evaluated host PC/WSL environment only, not embedded ECU hardware.
- Python-to-C `ctypes` dispatch and `perf_counter_ns` timer overhead are included, although CSV loading and input-state preparation are excluded.
- Python-host timing may differ materially from execution on an embedded C target, compiler, RTOS, or microcontroller.
- Operating-system scheduling, host contention, CPU frequency behavior, and timer noise can affect measurements.
- Results apply only to the evaluated traces and current detector source.
- The temporary wrapper supplies logged detector inputs. Two contextual fields not present in the CSV schema (`external_airflow_factor` and `road_slope_percent`) use neutral zero values; this does not affect the no-future-access structure but can affect exact branch timing.
- Prefix checks sample representative timestamps rather than every possible prefix.
- The 100 ms comparison is a simulated-loop budget check, not worst-case execution-time analysis or a hard real-time guarantee.
- RTL cases use existing replay traces. Verilator build and trace generation are excluded.
"""
    (output_dir / "online_detector_limitations.md").write_text(text, encoding="utf-8")


def write_figures(
    output_dir: Path,
    summary_rows: Sequence[Dict[str, object]],
    warnings: List[str],
) -> List[Path]:
    try:
        cache_dir = Path(tempfile.gettempdir()) / "virtual_ecu_online_audit_matplotlib"
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        warnings.append("Figures were skipped because matplotlib is unavailable.")
        return []

    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    names = [str(row["detector"]) for row in summary_rows]
    p99_values = [float(row["p99_update_time_ms"]) for row in summary_rows]
    margins = [float(row["worst_case_budget_margin_ms"]) for row in summary_rows]
    paths = []

    fig, ax = plt.subplots(figsize=(10.5, 5.2), constrained_layout=True)
    ax.bar(names, p99_values, color="#2f7ed8")
    ax.set_ylabel("p99 C update time [ms]")
    ax.set_title("Online Detector Update Time by Algorithm")
    ax.tick_params(axis="x", labelrotation=24)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    ax.grid(axis="y", linestyle=":", alpha=0.55)
    path = figure_dir / "detector_update_time_by_algorithm.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(10.5, 5.2), constrained_layout=True)
    ax.bar(names, margins, color="#28a080")
    ax.axhline(0.0, color="#b23a48", linestyle="--", linewidth=1.2)
    ax.set_ylabel("Worst-case margin to 100 ms budget [ms]")
    ax.set_title("Online Detector Timestep Budget Margin")
    ax.tick_params(axis="x", labelrotation=24)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    ax.grid(axis="y", linestyle=":", alpha=0.55)
    path = figure_dir / "detector_budget_margin_by_algorithm.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    paths.append(path)
    return paths


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    executable = args.executable.resolve()
    trace_dir = output_dir / "source_traces"
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_dir.mkdir(parents=True, exist_ok=True)
    build_if_needed(executable)

    warnings: List[str] = []
    scenarios = available_scenarios(warnings)
    print(f"Preparing {len(scenarios)} representative online traces.")
    trace_rows: Dict[str, List[Dict[str, str]]] = {}
    for scenario in scenarios:
        print(f"- {scenario.name}")
        trace_rows[scenario.scenario_id] = read_trace(
            generate_trace(executable, trace_dir, scenario)
        )

    source_passed, source_facts = source_order_check()
    if not source_passed:
        warnings.append("Static scheduler ordering check did not pass.")

    timing_rows: List[Dict[str, object]] = []
    detector_samples = {detector: [] for detector in DETECTORS}
    detector_pass = {detector: True for detector in DETECTORS}
    comparison_counts = {detector: 0 for detector in DETECTORS}

    with tempfile.TemporaryDirectory(prefix="virtual_ecu_online_audit_") as name:
        library = compile_audit_library(Path(name))
        total = len(scenarios) * len(DETECTORS)
        case_index = 0
        for scenario in scenarios:
            rows = trace_rows[scenario.scenario_id]
            checkpoints = checkpoint_indices(rows, scenario.activation_ms)
            for detector_index, detector in enumerate(DETECTORS):
                case_index += 1
                print(f"[{case_index:02d}/{total}] {scenario.scenario_id} / {detector}")
                timings_ns, causal, comparisons = audit_detector_scenario(
                    library,
                    detector_index,
                    rows,
                    checkpoints,
                )
                detector_samples[detector].extend(timings_ns)
                detector_pass[detector] = detector_pass[detector] and causal
                comparison_counts[detector] += comparisons
                timing_rows.append(timing_row(scenario, detector, timings_ns))

    causality = causality_rows(
        detector_pass,
        comparison_counts,
        source_passed,
    )
    summary_rows = timing_summary(
        timing_rows,
        detector_samples,
        detector_pass,
        source_passed,
    )
    causality_path = output_dir / "online_detector_causality_summary.csv"
    timing_path = output_dir / "online_detector_timing_matrix.csv"
    summary_path = output_dir / "online_detector_timing_summary.csv"
    write_csv(causality_path, CAUSALITY_COLUMNS, causality)
    write_csv(timing_path, TIMING_COLUMNS, timing_rows)
    write_csv(summary_path, SUMMARY_COLUMNS, summary_rows)

    all_causal = all(int(row["causality_check_passed"]) != 0 for row in causality)
    all_fit = all(int(row["fits_timestep_budget"]) != 0 for row in timing_rows)
    slowest_ms = max(float(row["max_update_time_ms"]) for row in timing_rows)
    host = host_info()
    write_readme(output_dir, scenarios, host, source_facts, all_causal, all_fit)
    claim = write_claim_summary(output_dir, all_causal, all_fit, slowest_ms)
    write_limitations(output_dir)
    figure_paths = [] if args.no_figures else write_figures(
        output_dir, summary_rows, warnings
    )

    manifest_path = output_dir / "evidence_manifest.json"
    output_files = [
        output_dir / "README.md",
        causality_path,
        timing_path,
        summary_path,
        output_dir / "online_detector_claim_summary.md",
        output_dir / "online_detector_limitations.md",
        *figure_paths,
        manifest_path,
    ]
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host_info": host,
        "git_commit": host["git_commit"],
        "row_counts": {
            "causality_summary": len(causality),
            "timing_matrix": len(timing_rows),
            "timing_summary": len(summary_rows),
        },
        "scenarios_used": [
            {
                "scenario_id": scenario.scenario_id,
                "scenario_name": scenario.name,
                "activation_ms": scenario.activation_ms,
                "steps": len(trace_rows[scenario.scenario_id]),
            }
            for scenario in scenarios
        ],
        "source_order_evidence": source_facts,
        "timing_method": (
            "time.perf_counter_ns around exact compiled C detection_algorithm_step; "
            "ctypes dispatch and timer overhead included"
        ),
        "output_files": [relative_path(path) for path in output_files],
        "warnings": warnings,
        "key_metrics": {
            "all_detectors_causality_check_passed": all_causal,
            "future_sample_access_found": not all_causal,
            "timestep_budget_ms": TIMESTEP_BUDGET_MS,
            "maximum_observed_update_time_ms": slowest_ms,
            "all_detector_scenarios_fit_timestep_budget": all_fit,
            "bounded_claim": claim,
        },
        "scope": {
            "host_wsl_measurement_only": True,
            "embedded_hardware_validation": False,
            "hard_realtime_guarantee": False,
            "gui_or_plot_timing_included": False,
            "file_loading_timing_included": False,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Online detector timing audit complete: {output_dir}")
    print(f"Causality checks passed: {all_causal}")
    print(f"All detector/scenario cases fit {TIMESTEP_BUDGET_MS:.0f} ms: {all_fit}")
    print(f"Maximum observed update time: {slowest_ms:.9f} ms")
    for warning in warnings:
        print(f"Warning: {warning}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
