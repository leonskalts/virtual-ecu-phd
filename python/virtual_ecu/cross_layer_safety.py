"""Cross-layer experiment reporting. Never imported by runtime detectors.

Old CSVs remain valid: missing instrumentation produces None, displayed as N/A.
The C monitor uses unrounded runtime values; do not reconstruct its comparisons
from the rounded legacy CSV columns.
"""
from __future__ import annotations

import csv
import subprocess
from pathlib import Path
from typing import Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "cross_layer_safety_v1"
STAGES = (
    "fault_injection_ms", "propagation_internal_ms", "propagation_control_ms",
    "propagation_actuator_command_ms", "propagation_actuator_realization_ms",
    "propagation_plant_ms", "propagation_detector_ms", "propagation_safety_response_ms",
    "propagation_safe_state_ms",
)
METRICS = (
    "injection_to_internal_latency_ms", "injection_to_control_latency_ms",
    "injection_to_actuator_latency_ms", "injection_to_plant_latency_ms",
    "cross_layer_detection_latency_ms", "detection_to_safety_response_latency_ms",
    "propagation_depth", "detected_before_plant_manifestation", "safe_state_reached",
    "unsafe_state_entered", "unsafe_exposure_time_ms", "containment_success", "silent_corruption",
)
LEGACY_METADATA = {
    "sensor_bias": ("sensing_control", "value_corruption", "coolant_sensor"),
    "sensor_interface_intermittent": ("sensing_control", "value_corruption", "coolant_sensor"),
    "stale_sensor_data": ("communication", "stale_data", "coolant_sensor"),
    "calibration_memory_corruption": ("memory", "value_corruption", "control_target_register"),
    "pump_degraded": ("actuator", "degraded_actuator", "pump"),
    "fan_stuck_off": ("actuator", "legacy", "fan"),
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No data rows in {path}")
    if any(None in row or None in row.values() for row in rows):
        raise ValueError(f"Malformed CSV row in {path}")
    return rows


def optional_int(row: Mapping[str, str], key: str) -> int | None:
    value = row.get(key)
    if value in (None, "", "N/A", "-1"):
        return None
    return int(value)


def summarize_rows(rows: Sequence[Mapping[str, str]]) -> dict[str, object]:
    if not rows:
        raise ValueError("No experiment rows")
    first, last = rows[0], rows[-1]
    available = last.get("cross_layer_monitor_enabled") == "1"
    enabled = first.get("cross_layer_fault_enabled") == "1"
    legacy = first.get("campaign_event_1_mode_label", "none")
    layer, model, target = LEGACY_METADATA.get(legacy, (None, None, None))
    result: dict[str, object] = {
        "telemetry_available": available,
        "cross_layer_fault_enabled": optional_int(first, "cross_layer_fault_enabled"),
        "fault_id": first.get("cross_layer_fault_id") if enabled else (legacy if legacy != "none" else None),
        "fault_layer": first.get("cross_layer_fault_layer") if enabled else layer,
        "fault_model": first.get("cross_layer_fault_model") if enabled else model,
        "fault_target": first.get("cross_layer_fault_target") if enabled else target,
        "fault_behavior": first.get("cross_layer_fault_behavior") if enabled else (
            first.get("campaign_event_1_behavior_label") if legacy != "none" else None),
        "seed": optional_int(first, "experiment_seed"),
    }
    for key in (*STAGES, *METRICS):
        result[key] = optional_int(last, key) if available else None
    for label, key in (
        ("injected", "fault_injection_ms"), ("internal_corruption", "propagation_internal_ms"),
        ("control_effect", "propagation_control_ms"), ("actuator_effect", "propagation_actuator_command_ms"),
        ("actuator_realization_effect", "propagation_actuator_realization_ms"),
        ("plant_manifestation", "propagation_plant_ms"), ("detected", "propagation_detector_ms"),
    ):
        result[label] = int(result[key] is not None) if available else None
    return result


def load_summary(path: Path) -> dict[str, object]:
    return summarize_rows(read_rows(path))


def fault_options(model: str, start_ms: int = 45000, duration_ms: int = 100,
                  bit_index: int = 5, seed: int = 42, fault_id: int = 1) -> list[str]:
    if model not in ("bit_flip", "deadline_miss"):
        raise ValueError("Supported fault models: bit_flip, deadline_miss")
    options = ["--cross-layer-fault", model, "--fault-layer",
               "memory" if model == "bit_flip" else "timing", "--fault-target",
               "control_target_register" if model == "bit_flip" else "control_task",
               "--fault-behavior", "transient", "--fault-start-ms", str(start_ms),
               "--fault-duration-ms", str(duration_ms), "--seed", str(seed),
               "--fault-id", str(fault_id)]
    if model == "bit_flip":
        options += ["--bit-index", str(bit_index)]
    return options


def run_experiment(path: Path, campaign_args: Sequence[str], options: Sequence[str],
                   executable: Path | None = None) -> list[str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [str(executable or PROJECT_ROOT / "virtual_ecu"), str(path),
               *campaign_args, *options]
    completed = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError(f"Experiment failed: {completed.stderr.strip() or completed.stdout.strip()}")
    return command


def write_rows(path: Path, rows: Sequence[Mapping[str, object]], columns: Sequence[str] | None = None) -> None:
    if not rows:
        raise ValueError("Cannot write an empty experiment table")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns or rows[0]), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
