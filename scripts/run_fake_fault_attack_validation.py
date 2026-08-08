#!/usr/bin/env python3
"""Measure detector responses to deterministic fake-fault replay attacks."""

from __future__ import annotations

import argparse
import csv
import math
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "fake_fault_attack_validation"
DEFAULT_EXECUTABLE = PROJECT_ROOT / "virtual_ecu"
EXPERIMENT_FAMILY = "fake_fault_attack_validation"
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

CHANNEL_CONFIG = {
    "coolant_sensor": {
        "source_column": "coolant_temp_meas_c",
        "header": "coolant_temp_c",
        "option": "--coolant-sensor-trace",
        "minimum": -40.0,
        "maximum": 150.0,
    },
    "fan_actual": {
        "source_column": "fan_actual",
        "header": "fan_actual",
        "option": "--fan-actual-trace",
        "minimum": 0.0,
        "maximum": 1.0,
    },
    "calibration_target": {
        "source_column": "active_control_target_c",
        "header": "control_target_c",
        "option": "--calibration-trace",
        "minimum": 60.0,
        "maximum": 130.0,
    },
}

MATRIX_COLUMNS = (
    "experiment_family",
    "scenario_id",
    "scenario_name",
    "scenario_group",
    "variant",
    "detector",
    "physical_fault_present",
    "rtl_trojan_present",
    "fake_fault_attack_present",
    "spoofed_signal_group",
    "spoofed_signal_name",
    "spoof_start_ms",
    "spoof_end_ms",
    "spoof_magnitude",
    "attack_observed_alarm",
    "detector_was_fooled_by_fake_fault",
    "first_alarm_ms",
    "detection_label",
    "false_fault_latency_ms",
    "max_clean_truth_coolant_temp_c",
    "max_observed_coolant_temp_c",
    "final_clean_truth_safe_state",
    "final_observed_safe_state",
    "raw_csv",
    "summary_csv",
    "truth_raw_csv",
    "truth_summary_csv",
    "notes",
)

DETECTOR_SUMMARY_COLUMNS = (
    "detector",
    "attack_runs",
    "fooled_runs",
    "fooled_rate_percent",
    "resisted_runs",
    "earliest_false_fault_alarm_ms",
    "mean_false_fault_latency_ms",
    "median_false_fault_latency_ms",
    "labels_seen",
    "spoof_groups_that_fooled_detector",
    "spoof_groups_resisted",
)

SCENARIO_SUMMARY_COLUMNS = (
    "scenario_id",
    "scenario_name",
    "scenario_group",
    "spoofed_signal_group",
    "detectors_tested",
    "detectors_fooled",
    "detector_names_fooled",
    "hybrid_fooled",
    "hybrid_first_alarm_ms",
    "max_clean_truth_coolant_temp_c",
    "max_observed_coolant_temp_c",
    "notes",
)

PROFILE_TABLE_COLUMNS = (
    "scenario_id",
    "scenario_name",
    "scenario_group",
    "variant",
    "spoofed_signal_group",
    "spoofed_signal_name",
    "channel",
    "replay_option",
    "operation",
    "start_ms",
    "end_ms",
    "magnitude",
    "secondary_value",
    "period_ms",
    "active_ms",
    "trace_csv",
    "notes",
)


@dataclass(frozen=True)
class ChannelSpoof:
    channel: str
    operation: str
    start_ms: int
    end_ms: int
    magnitude: float
    secondary_value: float = 0.0
    period_ms: int = 0
    active_ms: int = 0
    magnitude_label: str = ""


@dataclass(frozen=True)
class AttackSpec:
    scenario_id: str
    scenario_name: str
    scenario_group: str
    variant: str
    spoofed_signal_group: str
    spoofed_signal_name: str
    spoofs: tuple[ChannelSpoof, ...]
    notes: str

    @property
    def spoof_start_ms(self) -> int:
        return min(spoof.start_ms for spoof in self.spoofs)

    @property
    def spoof_end_ms(self) -> int:
        return max(spoof.end_ms for spoof in self.spoofs)

    @property
    def spoof_magnitude(self) -> str:
        return "; ".join(
            spoof.magnitude_label
            or f"{spoof.channel}:{spoof.magnitude:g}"
            for spoof in self.spoofs
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run eight unchanged runtime detectors over 40 deterministic "
            "fake-fault observation attacks derived from clean physical truth."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for truth runs, attack traces, results, and reports.",
    )
    parser.add_argument(
        "--executable",
        type=Path,
        default=DEFAULT_EXECUTABLE,
        help="Path to the compiled virtual_ecu executable.",
    )
    return parser.parse_args()


def spoof(
    channel: str,
    operation: str,
    start_ms: int,
    end_ms: int,
    magnitude: float,
    label: str,
    *,
    secondary_value: float = 0.0,
    period_ms: int = 0,
    active_ms: int = 0,
) -> ChannelSpoof:
    return ChannelSpoof(
        channel=channel,
        operation=operation,
        start_ms=start_ms,
        end_ms=end_ms,
        magnitude=magnitude,
        secondary_value=secondary_value,
        period_ms=period_ms,
        active_ms=active_ms,
        magnitude_label=label,
    )


def build_attacks() -> tuple[AttackSpec, ...]:
    attacks: List[AttackSpec] = []

    def add(
        scenario_id: str,
        scenario_name: str,
        scenario_group: str,
        variant: str,
        spoofed_signal_group: str,
        spoofed_signal_name: str,
        spoofs: Sequence[ChannelSpoof],
        notes: str,
    ) -> None:
        attacks.append(
            AttackSpec(
                scenario_id,
                scenario_name,
                scenario_group,
                variant,
                spoofed_signal_group,
                spoofed_signal_name,
                tuple(spoofs),
                notes,
            )
        )

    sensor_attacks = (
        ("high_spike", "Fake high coolant spike", spoof("coolant_sensor", "offset", 40000, 45000, 18.0, "+18 C")),
        ("low_drop", "Fake low coolant drop", spoof("coolant_sensor", "offset", 40000, 50000, -18.0, "-18 C")),
        (
            "oscillation",
            "Fake oscillating coolant measurement",
            spoof(
                "coolant_sensor",
                "oscillating_offset",
                40000,
                70000,
                10.0,
                "+/-10 C at 1 s period",
                period_ms=1000,
            ),
        ),
        (
            "slow_upward_drift",
            "Fake slow upward coolant drift",
            spoof(
                "coolant_sensor",
                "ramp_offset",
                30000,
                90000,
                12.0,
                "0 to +12 C drift",
            ),
        ),
        (
            "single_sample_spike",
            "Fake single-sample coolant spike",
            spoof(
                "coolant_sensor",
                "offset",
                50000,
                50100,
                22.0,
                "+22 C for 100 ms",
            ),
        ),
        (
            "sustained_positive_offset",
            "Fake sustained coolant offset",
            spoof("coolant_sensor", "offset", 30000, 100000, 6.0, "+6 C"),
        ),
        (
            "intermittent_glitch",
            "Fake intermittent coolant glitches",
            spoof(
                "coolant_sensor",
                "pulse_train_offset",
                35000,
                95000,
                12.0,
                "+12 C, 300 ms every 3 s",
                period_ms=3000,
                active_ms=300,
            ),
        ),
        (
            "warning_like_value",
            "Fake warning-like coolant value",
            spoof(
                "coolant_sensor",
                "constant",
                60000,
                80000,
                108.0,
                "108 C indicated",
            ),
        ),
        (
            "sustained_negative_offset",
            "Fake sustained negative coolant offset",
            spoof("coolant_sensor", "offset", 30000, 90000, -7.0, "-7 C"),
        ),
        (
            "slow_downward_drift",
            "Fake slow downward coolant drift",
            spoof(
                "coolant_sensor",
                "ramp_offset",
                30000,
                90000,
                -14.0,
                "0 to -14 C drift",
            ),
        ),
        (
            "early_positive_offset",
            "Fake early coolant offset",
            spoof("coolant_sensor", "offset", 10000, 25000, 10.0, "+10 C"),
        ),
        (
            "late_positive_offset",
            "Fake late coolant offset",
            spoof("coolant_sensor", "offset", 90000, 115000, 9.0, "+9 C"),
        ),
    )
    for index, (variant, name, channel_spoof) in enumerate(sensor_attacks, start=1):
        add(
            f"coolant_spoof_{index:02d}_{variant}",
            name,
            "fake_coolant_sensor_indications",
            variant,
            "sensor_observation",
            "coolant_temp_c",
            (channel_spoof,),
            "Clean baseline plant with an opt-in ECU-facing coolant replay trace.",
        )

    stale_attacks = (
        (
            "short_freeze",
            "Fake short frozen coolant indication",
            spoof("coolant_sensor", "freeze", 35000, 40000, 0.0, "held 5 s"),
        ),
        (
            "long_freeze",
            "Fake long frozen coolant indication",
            spoof("coolant_sensor", "freeze", 35000, 80000, 0.0, "held 45 s"),
        ),
        (
            "repeated_freeze",
            "Fake repeated frozen coolant windows",
            spoof(
                "coolant_sensor",
                "repeated_freeze",
                30000,
                90000,
                0.0,
                "4 s held every 10 s",
                period_ms=10000,
                active_ms=4000,
            ),
        ),
        (
            "delayed_samples",
            "Fake delayed coolant samples",
            spoof(
                "coolant_sensor",
                "delayed",
                30000,
                90000,
                2000.0,
                "2 s replay delay",
            ),
        ),
        (
            "intermittent_freeze",
            "Fake intermittent frozen samples",
            spoof(
                "coolant_sensor",
                "repeated_freeze",
                30000,
                90000,
                0.0,
                "2 s held every 8 s",
                period_ms=8000,
                active_ms=2000,
            ),
        ),
        (
            "staircase_hold",
            "Fake staircase-held coolant indication",
            spoof(
                "coolant_sensor",
                "staircase",
                30000,
                100000,
                5000.0,
                "5 s sample holds",
            ),
        ),
    )
    for index, (variant, name, channel_spoof) in enumerate(stale_attacks, start=1):
        add(
            f"stale_spoof_{index:02d}_{variant}",
            name,
            "fake_stale_sensor_indications",
            variant,
            "stale_like_sensor_observation",
            "coolant_temp_c",
            (channel_spoof,),
            "Replay freezes or delays values, but the existing trace interface "
            "marks each replay sample fresh; freshness flags are not spoofed.",
        )

    fan_attacks = (
        (
            "stuck_zero",
            "Fake fan actual stuck at zero",
            spoof("fan_actual", "constant", 60000, 90000, 0.0, "fan_actual=0"),
        ),
        (
            "severe_under_response",
            "Fake severe fan under-response",
            spoof(
                "fan_actual",
                "scale",
                55000,
                95000,
                0.25,
                "25% of clean fan_actual",
            ),
        ),
        (
            "mild_under_response",
            "Fake mild fan under-response",
            spoof(
                "fan_actual",
                "scale",
                55000,
                95000,
                0.60,
                "60% of clean fan_actual",
            ),
        ),
        (
            "stuck_high",
            "Fake fan actual stuck high",
            spoof("fan_actual", "constant", 50000, 80000, 1.0, "fan_actual=1"),
        ),
        (
            "intermittent_dropout",
            "Fake intermittent fan dropout",
            spoof(
                "fan_actual",
                "dropout",
                50000,
                95000,
                0.0,
                "500 ms dropout every 3 s",
                period_ms=3000,
                active_ms=500,
            ),
        ),
        (
            "short_mismatch_pulse",
            "Fake short fan mismatch pulse",
            spoof(
                "fan_actual",
                "constant",
                70000,
                72000,
                0.0,
                "fan_actual=0 for 2 s",
            ),
        ),
        (
            "sustained_negative_bias",
            "Fake sustained fan feedback bias",
            spoof(
                "fan_actual",
                "offset",
                55000,
                95000,
                -0.35,
                "fan_actual - 0.35",
            ),
        ),
        (
            "inverted_response",
            "Fake inverted fan response",
            spoof(
                "fan_actual",
                "inverted",
                55000,
                85000,
                0.0,
                "fan_actual=1-clean",
            ),
        ),
        (
            "delayed_response",
            "Fake delayed fan response",
            spoof(
                "fan_actual",
                "delayed",
                50000,
                95000,
                3000.0,
                "3 s replay delay",
            ),
        ),
        (
            "alternating_zero_high",
            "Fake alternating fan extremes",
            spoof(
                "fan_actual",
                "alternating_constant",
                55000,
                85000,
                0.0,
                "0/1 alternating every 1 s",
                secondary_value=1.0,
                period_ms=2000,
            ),
        ),
    )
    for index, (variant, name, channel_spoof) in enumerate(fan_attacks, start=1):
        add(
            f"fan_spoof_{index:02d}_{variant}",
            name,
            "fake_actuator_feedback_indications",
            variant,
            "actuator_interface",
            "fan_actual",
            (channel_spoof,),
            "Uses the existing fan_actual replay path, which also changes "
            "realized cooling and is not a feedback-only channel.",
        )

    calibration_attacks = (
        (
            "target_jump_high",
            "Fake calibration target jump",
            spoof(
                "calibration_target",
                "offset",
                45000,
                75000,
                16.0,
                "+16 C target",
            ),
        ),
        (
            "target_upward_drift",
            "Fake calibration target drift",
            spoof(
                "calibration_target",
                "ramp_offset",
                30000,
                90000,
                18.0,
                "0 to +18 C target drift",
            ),
        ),
        (
            "short_deviation_pulse",
            "Fake short calibration deviation",
            spoof(
                "calibration_target",
                "offset",
                50000,
                55000,
                12.0,
                "+12 C for 5 s",
            ),
        ),
        (
            "sustained_deviation",
            "Fake sustained calibration deviation",
            spoof(
                "calibration_target",
                "offset",
                30000,
                100000,
                8.0,
                "+8 C target",
            ),
        ),
        (
            "return_to_normal",
            "Fake calibration deviation then return",
            spoof(
                "calibration_target",
                "offset",
                40000,
                70000,
                14.0,
                "+14 C then normal",
            ),
        ),
        (
            "target_jump_low",
            "Fake low calibration target",
            spoof(
                "calibration_target",
                "offset",
                40000,
                80000,
                -12.0,
                "-12 C target",
            ),
        ),
        (
            "target_oscillation",
            "Fake oscillating calibration target",
            spoof(
                "calibration_target",
                "oscillating_offset",
                40000,
                90000,
                8.0,
                "+/-8 C at 2 s period",
                period_ms=2000,
            ),
        ),
        (
            "large_target_value",
            "Fake large calibration target",
            spoof(
                "calibration_target",
                "constant",
                60000,
                75000,
                120.0,
                "120 C target",
            ),
        ),
    )
    for index, (variant, name, channel_spoof) in enumerate(calibration_attacks, start=1):
        add(
            f"calibration_spoof_{index:02d}_{variant}",
            name,
            "fake_calibration_control_indications",
            variant,
            "calibration_interface",
            "active_control_target_c",
            (channel_spoof,),
            "Uses the existing calibration replay path; the spoof changes the "
            "controller target and can alter the closed-loop plant.",
        )

    coordinated_attacks = (
        (
            "sensor_spike_fan_zero",
            "Coordinated fake coolant spike and fan mismatch",
            (
                spoof("coolant_sensor", "offset", 50000, 80000, 12.0, "coolant +12 C"),
                spoof("fan_actual", "constant", 50000, 80000, 0.0, "fan_actual=0"),
            ),
        ),
        (
            "sensor_drift_calibration_jump",
            "Coordinated fake coolant drift and calibration deviation",
            (
                spoof("coolant_sensor", "ramp_offset", 30000, 90000, 10.0, "coolant 0 to +10 C"),
                spoof("calibration_target", "offset", 50000, 90000, 12.0, "target +12 C"),
            ),
        ),
        (
            "sensor_freeze_fan_under_response",
            "Coordinated fake stale-like value and fan under-response",
            (
                spoof("coolant_sensor", "freeze", 40000, 85000, 0.0, "coolant held 45 s"),
                spoof("fan_actual", "scale", 55000, 85000, 0.25, "fan_actual at 25%"),
            ),
        ),
        (
            "sensor_calibration_oscillation",
            "Coordinated fake coolant and calibration oscillation",
            (
                spoof("coolant_sensor", "oscillating_offset", 45000, 85000, 8.0, "coolant +/-8 C", period_ms=1000),
                spoof("calibration_target", "oscillating_offset", 45000, 85000, 8.0, "target +/-8 C", period_ms=2000),
            ),
        ),
    )
    for index, (variant, name, channel_spoofs) in enumerate(coordinated_attacks, start=1):
        add(
            f"coordinated_spoof_{index:02d}_{variant}",
            name,
            "coordinated_fake_fault_attacks",
            variant,
            "coordinated_interfaces",
            "+".join(spoof_item.channel for spoof_item in channel_spoofs),
            channel_spoofs,
            "Multiple existing opt-in replay channels are corrupted together; "
            "no physical fault event or RTL Trojan is configured.",
        )

    if len(attacks) != 40:
        raise RuntimeError(f"Expected 40 fake-fault attacks, found {len(attacks)}.")
    if len({attack.scenario_id for attack in attacks}) != len(attacks):
        raise RuntimeError("Fake-fault scenario IDs must be unique.")
    for attack in attacks:
        channels = [item.channel for item in attack.spoofs]
        if len(channels) != len(set(channels)):
            raise RuntimeError(f"Duplicate spoof channel in {attack.scenario_id}.")
        if any(channel not in CHANNEL_CONFIG for channel in channels):
            raise RuntimeError(f"Unsupported spoof channel in {attack.scenario_id}.")
    return tuple(attacks)


def parse_int(value: object, default: int = -1) -> int:
    text = str(value).strip()
    return default if text == "" else int(float(text))


def parse_float(value: object, default: float = math.nan) -> float:
    text = str(value).strip()
    return default if text == "" else float(text)


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())


def summary_path_for(raw_path: Path) -> Path:
    return raw_path.with_name(f"{raw_path.stem}_summary.csv")


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"CSV has no rows: {path}")
    return rows


def read_one_row(path: Path) -> Dict[str, str]:
    rows = read_rows(path)
    if len(rows) != 1:
        raise RuntimeError(f"Expected one row in {path}, found {len(rows)}.")
    return rows[0]


def write_rows(
    path: Path,
    columns: Sequence[str],
    rows: Iterable[Mapping[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="ignore",
            lineterminator="\n",
        )
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
        raise RuntimeError(f"{label} failed:\n{detail}")


def validate_clean_metadata(
    summary: Mapping[str, str],
    detector: str,
    label: str,
) -> None:
    expected = {
        "campaign_id": "baseline",
        "campaign_event_count": "0",
        "fault_present_in_campaign": "0",
        "runtime_detection_algorithm": detector,
        "runtime_detection_action": OBSERVE_ONLY,
        "simulation_duration_ms": str(SIMULATION_DURATION_MS),
    }
    for column, expected_value in expected.items():
        actual = str(summary.get(column, "")).strip()
        if actual != expected_value:
            raise RuntimeError(
                f"Clean physical-truth invariant failed for {label}: "
                f"{column}={actual!r}, expected {expected_value!r}."
            )


def run_truth_matrix(
    executable: Path,
    output_dir: Path,
) -> tuple[Dict[str, tuple[Path, Path, Dict[str, str]]], List[Dict[str, str]]]:
    truth_dir = output_dir / "truth"
    truth_dir.mkdir(parents=True, exist_ok=True)
    truth: Dict[str, tuple[Path, Path, Dict[str, str]]] = {}
    canonical_rows: List[Dict[str, str]] = []
    for detector in DETECTORS:
        raw_path = truth_dir / f"clean_baseline__{detector}.csv"
        summary_path = summary_path_for(raw_path)
        run_checked(
            (
                str(executable),
                str(raw_path),
                "baseline",
                "--detector",
                detector,
                "--detector-action",
                OBSERVE_ONLY,
                "--simulation-duration-ms",
                str(SIMULATION_DURATION_MS),
            ),
            f"clean truth/{detector}",
        )
        summary = read_one_row(summary_path)
        validate_clean_metadata(summary, detector, f"truth/{detector}")
        rows = read_rows(raw_path)
        if any(parse_int(row.get("fault_mode_id", "-1")) != 0 for row in rows):
            raise RuntimeError(f"Active fault found in truth trace {raw_path}.")
        truth[detector] = (raw_path, summary_path, summary)
        if detector == "builtin_ecu":
            canonical_rows = rows
    return truth, canonical_rows


def source_value_at(
    rows_by_time: Mapping[int, Mapping[str, str]],
    channel: str,
    time_ms: int,
) -> float:
    config = CHANNEL_CONFIG[channel]
    bounded_time = max(0, min(SIMULATION_DURATION_MS, time_ms))
    return parse_float(rows_by_time[bounded_time][str(config["source_column"])])


def spoofed_value(
    spoof_spec: ChannelSpoof,
    time_ms: int,
    base_value: float,
    rows_by_time: Mapping[int, Mapping[str, str]],
) -> float:
    if time_ms < spoof_spec.start_ms or time_ms >= spoof_spec.end_ms:
        return base_value
    elapsed = time_ms - spoof_spec.start_ms
    operation = spoof_spec.operation
    value = base_value
    if operation == "offset":
        value = base_value + spoof_spec.magnitude
    elif operation == "constant":
        value = spoof_spec.magnitude
    elif operation == "scale":
        value = base_value * spoof_spec.magnitude
    elif operation == "inverted":
        value = 1.0 - base_value
    elif operation == "ramp_offset":
        span = max(1, spoof_spec.end_ms - spoof_spec.start_ms)
        value = base_value + spoof_spec.magnitude * (elapsed / span)
    elif operation == "oscillating_offset":
        half_period = max(100, spoof_spec.period_ms // 2)
        sign = 1.0 if (elapsed // half_period) % 2 == 0 else -1.0
        value = base_value + sign * spoof_spec.magnitude
    elif operation == "pulse_train_offset":
        phase = elapsed % spoof_spec.period_ms
        value = base_value + spoof_spec.magnitude if phase < spoof_spec.active_ms else base_value
    elif operation == "freeze":
        value = source_value_at(rows_by_time, spoof_spec.channel, spoof_spec.start_ms)
    elif operation == "delayed":
        value = source_value_at(
            rows_by_time,
            spoof_spec.channel,
            time_ms - int(spoof_spec.magnitude),
        )
    elif operation == "repeated_freeze":
        phase = elapsed % spoof_spec.period_ms
        if phase < spoof_spec.active_ms:
            cycle_start = time_ms - phase
            value = source_value_at(rows_by_time, spoof_spec.channel, cycle_start)
    elif operation == "staircase":
        hold_ms = int(spoof_spec.magnitude)
        held_time = spoof_spec.start_ms + (elapsed // hold_ms) * hold_ms
        value = source_value_at(rows_by_time, spoof_spec.channel, held_time)
    elif operation == "dropout":
        value = 0.0 if elapsed % spoof_spec.period_ms < spoof_spec.active_ms else base_value
    elif operation == "alternating_constant":
        half_period = max(100, spoof_spec.period_ms // 2)
        value = spoof_spec.magnitude if (elapsed // half_period) % 2 == 0 else spoof_spec.secondary_value
    else:
        raise RuntimeError(f"Unknown spoof operation: {operation}")

    config = CHANNEL_CONFIG[spoof_spec.channel]
    return min(float(config["maximum"]), max(float(config["minimum"]), value))


def write_attack_traces(
    output_dir: Path,
    attacks: Sequence[AttackSpec],
    source_rows: Sequence[Mapping[str, str]],
) -> tuple[Dict[str, tuple[tuple[str, Path], ...]], List[Dict[str, object]]]:
    rows_by_time = {
        parse_int(row["time_ms"]): row
        for row in source_rows
    }
    expected_times = set(range(0, SIMULATION_DURATION_MS + 100, 100))
    if set(rows_by_time) != expected_times:
        raise RuntimeError("Canonical clean trace lacks complete 100 ms replay coverage.")

    replay_inputs: Dict[str, tuple[tuple[str, Path], ...]] = {}
    profile_rows: List[Dict[str, object]] = []
    for attack in attacks:
        attack_dir = output_dir / "attack_profiles" / attack.scenario_id
        attack_dir.mkdir(parents=True, exist_ok=True)
        inputs: List[tuple[str, Path]] = []
        for spoof_spec in attack.spoofs:
            config = CHANNEL_CONFIG[spoof_spec.channel]
            trace_path = attack_dir / f"{spoof_spec.channel}.csv"
            header = str(config["header"])
            trace_rows = []
            for time_ms in sorted(rows_by_time):
                base_value = source_value_at(rows_by_time, spoof_spec.channel, time_ms)
                value = spoofed_value(
                    spoof_spec,
                    time_ms,
                    base_value,
                    rows_by_time,
                )
                trace_rows.append({"time_ms": time_ms, header: f"{value:.6f}"})
            write_rows(trace_path, ("time_ms", header), trace_rows)
            option = str(config["option"])
            inputs.append((option, trace_path))
            profile_rows.append(
                {
                    "scenario_id": attack.scenario_id,
                    "scenario_name": attack.scenario_name,
                    "scenario_group": attack.scenario_group,
                    "variant": attack.variant,
                    "spoofed_signal_group": attack.spoofed_signal_group,
                    "spoofed_signal_name": attack.spoofed_signal_name,
                    "channel": spoof_spec.channel,
                    "replay_option": option,
                    "operation": spoof_spec.operation,
                    "start_ms": spoof_spec.start_ms,
                    "end_ms": spoof_spec.end_ms,
                    "magnitude": spoof_spec.magnitude_label,
                    "secondary_value": spoof_spec.secondary_value,
                    "period_ms": spoof_spec.period_ms,
                    "active_ms": spoof_spec.active_ms,
                    "trace_csv": relative_path(trace_path),
                    "notes": attack.notes,
                }
            )
        replay_inputs[attack.scenario_id] = tuple(inputs)
    return replay_inputs, profile_rows


def scan_attack_raw(
    raw_path: Path,
    detector: str,
) -> tuple[int, str, float]:
    first_alarm_ms = -1
    detection_label = "none"
    max_observed_coolant_c = -math.inf
    rows_seen = 0
    with raw_path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows_seen += 1
            if row.get("campaign_id") != "baseline":
                raise RuntimeError(f"Non-baseline campaign found in {raw_path}.")
            if parse_int(row.get("campaign_event_count", "-1")) != 0:
                raise RuntimeError(f"Physical fault metadata found in {raw_path}.")
            if parse_int(row.get("fault_mode_id", "-1")) != 0:
                raise RuntimeError(f"Active physical fault found in {raw_path}.")
            if any(
                parse_int(row.get(f"campaign_event_{index}_mode_id", "-1")) != 0
                for index in range(1, 5)
            ):
                raise RuntimeError(f"Configured physical fault found in {raw_path}.")
            if row.get("runtime_detection_algorithm") != detector:
                raise RuntimeError(f"Detector mismatch in {raw_path}.")
            if row.get("runtime_detection_action") != OBSERVE_ONLY:
                raise RuntimeError(f"Non-observe-only action in {raw_path}.")
            max_observed_coolant_c = max(
                max_observed_coolant_c,
                parse_float(row.get("coolant_temp_meas_c", "")),
            )
            alarm = parse_int(row.get("runtime_detection_alarm", "0"), 0) != 0
            detected = parse_int(row.get("runtime_detection_detected", "0"), 0) != 0
            if (alarm or detected) and first_alarm_ms < 0:
                first_alarm_ms = parse_int(row.get("time_ms", "-1"))
                detection_label = row.get("runtime_detection_label", "none") or "none"
    if rows_seen == 0:
        raise RuntimeError(f"Attack trace has no rows: {raw_path}")
    return first_alarm_ms, detection_label, max_observed_coolant_c


def run_attack_detector(
    executable: Path,
    output_dir: Path,
    attack: AttackSpec,
    detector: str,
    replay_inputs: Mapping[str, tuple[tuple[str, Path], ...]],
    truth: Mapping[str, tuple[Path, Path, Dict[str, str]]],
) -> Dict[str, object]:
    raw_dir = output_dir / "raw" / attack.scenario_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{detector}.csv"
    summary_path = summary_path_for(raw_path)
    trace_arguments = tuple(
        argument
        for option, path in replay_inputs[attack.scenario_id]
        for argument in (option, str(path))
    )
    run_checked(
        (
            str(executable),
            str(raw_path),
            "baseline",
            "--detector",
            detector,
            "--detector-action",
            OBSERVE_ONLY,
            "--simulation-duration-ms",
            str(SIMULATION_DURATION_MS),
            *trace_arguments,
        ),
        f"{attack.scenario_id}/{detector}",
    )
    summary = read_one_row(summary_path)
    validate_clean_metadata(summary, detector, f"{attack.scenario_id}/{detector}")
    first_alarm_ms, detection_label, max_observed_coolant_c = scan_attack_raw(
        raw_path,
        detector,
    )
    observed_alarm = int(first_alarm_ms >= 0)
    truth_raw_path, truth_summary_path, truth_summary = truth[detector]
    return {
        "experiment_family": EXPERIMENT_FAMILY,
        "scenario_id": attack.scenario_id,
        "scenario_name": attack.scenario_name,
        "scenario_group": attack.scenario_group,
        "variant": attack.variant,
        "detector": detector,
        "physical_fault_present": 0,
        "rtl_trojan_present": 0,
        "fake_fault_attack_present": 1,
        "spoofed_signal_group": attack.spoofed_signal_group,
        "spoofed_signal_name": attack.spoofed_signal_name,
        "spoof_start_ms": attack.spoof_start_ms,
        "spoof_end_ms": attack.spoof_end_ms,
        "spoof_magnitude": attack.spoof_magnitude,
        "attack_observed_alarm": observed_alarm,
        "detector_was_fooled_by_fake_fault": observed_alarm,
        "first_alarm_ms": first_alarm_ms,
        "detection_label": detection_label if observed_alarm else "none",
        "false_fault_latency_ms": (
            first_alarm_ms - attack.spoof_start_ms if observed_alarm else -1
        ),
        "max_clean_truth_coolant_temp_c": f"{parse_float(truth_summary['max_coolant_temp_c']):.2f}",
        "max_observed_coolant_temp_c": f"{max_observed_coolant_c:.2f}",
        "final_clean_truth_safe_state": truth_summary.get("final_safe_state_label", "unknown"),
        "final_observed_safe_state": summary.get("final_safe_state_label", "unknown"),
        "raw_csv": relative_path(raw_path),
        "summary_csv": relative_path(summary_path),
        "truth_raw_csv": relative_path(truth_raw_path),
        "truth_summary_csv": relative_path(truth_summary_path),
        "notes": attack.notes,
    }


def detector_summary(rows: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    output: List[Dict[str, object]] = []
    for detector in DETECTORS:
        subset = [row for row in rows if row["detector"] == detector]
        fooled = [
            row
            for row in subset
            if parse_int(row["detector_was_fooled_by_fake_fault"], 0) != 0
        ]
        resisted = [
            row
            for row in subset
            if parse_int(row["detector_was_fooled_by_fake_fault"], 0) == 0
        ]
        fooled_groups = {str(row["spoofed_signal_group"]) for row in fooled}
        resisted_groups = {
            str(row["spoofed_signal_group"]) for row in resisted
        }
        latencies = [parse_int(row["false_fault_latency_ms"]) for row in fooled]
        alarm_times = [parse_int(row["first_alarm_ms"]) for row in fooled]
        output.append(
            {
                "detector": detector,
                "attack_runs": len(subset),
                "fooled_runs": len(fooled),
                "fooled_rate_percent": f"{100.0 * len(fooled) / len(subset):.3f}",
                "resisted_runs": len(subset) - len(fooled),
                "earliest_false_fault_alarm_ms": min(alarm_times) if alarm_times else -1,
                "mean_false_fault_latency_ms": f"{mean(latencies):.1f}" if latencies else -1,
                "median_false_fault_latency_ms": f"{median(latencies):.1f}" if latencies else -1,
                "labels_seen": ";".join(sorted({str(row["detection_label"]) for row in fooled})) or "none",
                "spoof_groups_that_fooled_detector": ";".join(sorted(fooled_groups)) or "none",
                "spoof_groups_resisted": ";".join(sorted(resisted_groups)) or "none",
            }
        )
    return output


def scenario_summary(rows: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    grouped: Dict[str, List[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["scenario_id"])].append(row)
    output: List[Dict[str, object]] = []
    for scenario_id in sorted(grouped):
        subset = grouped[scenario_id]
        first = subset[0]
        fooled_names = sorted(
            str(row["detector"])
            for row in subset
            if parse_int(row["detector_was_fooled_by_fake_fault"], 0) != 0
        )
        hybrid = next(
            row for row in subset if row["detector"] == "hybrid_adaptive_kalman"
        )
        max_observed_coolant_c = max(
            parse_float(row["max_observed_coolant_temp_c"])
            for row in subset
        )
        output.append(
            {
                "scenario_id": scenario_id,
                "scenario_name": first["scenario_name"],
                "scenario_group": first["scenario_group"],
                "spoofed_signal_group": first["spoofed_signal_group"],
                "detectors_tested": len({str(row["detector"]) for row in subset}),
                "detectors_fooled": len(fooled_names),
                "detector_names_fooled": ";".join(fooled_names) or "none",
                "hybrid_fooled": hybrid["detector_was_fooled_by_fake_fault"],
                "hybrid_first_alarm_ms": hybrid["first_alarm_ms"],
                "max_clean_truth_coolant_temp_c": first["max_clean_truth_coolant_temp_c"],
                "max_observed_coolant_temp_c": f"{max_observed_coolant_c:.2f}",
                "notes": first["notes"],
            }
        )
    return output


def attack_group_stats(rows: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    grouped: Dict[str, List[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["scenario_group"])].append(row)
    output = []
    for group in sorted(grouped):
        subset = grouped[group]
        fooled = sum(
            parse_int(row["detector_was_fooled_by_fake_fault"], 0)
            for row in subset
        )
        hybrid_subset = [
            row for row in subset if row["detector"] == "hybrid_adaptive_kalman"
        ]
        hybrid_fooled = sum(
            parse_int(row["detector_was_fooled_by_fake_fault"], 0)
            for row in hybrid_subset
        )
        output.append(
            {
                "scenario_group": group,
                "attack_variants": len({str(row["scenario_id"]) for row in subset}),
                "detector_runs": len(subset),
                "fooled_runs": fooled,
                "fooled_rate_percent": f"{100.0 * fooled / len(subset):.3f}",
                "hybrid_attack_runs": len(hybrid_subset),
                "hybrid_fooled_runs": hybrid_fooled,
                "hybrid_resisted_runs": len(hybrid_subset) - hybrid_fooled,
            }
        )
    return output


def limitations_lines() -> List[str]:
    return [
        "The current simulator has no trusted opt-in diagnostic/status spoof "
        "input, so fake DTC, monitor-flag, error-flag, and safe-state-request "
        "attacks were not evaluated.",
        "The coolant trace replaces the ECU-facing measurement and remains "
        "marked fresh on every replay sample. Frozen or delayed values therefore "
        "test stale-like measurement evidence, not spoofed freshness metadata.",
        "The fan_actual trace is the realized actuator value used by the thermal "
        "plant, not an isolated feedback-only signal. Fan spoof runs can "
        "therefore change actual cooling after replay begins.",
        "The calibration trace replaces the active controller target. "
        "Calibration spoof runs can therefore change controller commands and "
        "closed-loop plant behavior.",
        "Pump feedback spoofing was not evaluated because no opt-in pump replay input exists.",
        "Results apply only to these deterministic trace shapes, timings, "
        "magnitudes, baseline plant, and unchanged detector configurations.",
    ]


def write_claim_summary(
    path: Path,
    attacks: Sequence[AttackSpec],
    rows: Sequence[Mapping[str, object]],
    detector_rows: Sequence[Mapping[str, object]],
    group_rows: Sequence[Mapping[str, object]],
) -> None:
    fooled_total = sum(
        parse_int(row["detector_was_fooled_by_fake_fault"], 0)
        for row in rows
    )
    hybrid = next(
        row for row in detector_rows if row["detector"] == "hybrid_adaptive_kalman"
    )
    max_rate = max(parse_float(row["fooled_rate_percent"]) for row in group_rows)
    most_likely = [
        str(row["scenario_group"])
        for row in group_rows
        if parse_float(row["fooled_rate_percent"]) == max_rate
    ]
    hybrid_resisted = [
        f"{row['scenario_group']} ({row['hybrid_resisted_runs']}/{row['hybrid_attack_runs']} resisted)"
        for row in group_rows
        if parse_int(row["hybrid_resisted_runs"], 0) != 0
    ]
    lines = [
        "# Fake-Fault Attack Claim Summary",
        "",
        "## Bounded results",
        "",
        f"- Evaluated fake-fault attack variants: {len(attacks)}.",
        f"- Normalized detector runs: {len(rows)}.",
        f"- Detectors evaluated: {len(DETECTORS)}.",
        (
            "- In the evaluated deterministic fake-fault attack matrix, Hybrid "
            f"Adaptive Kalman was fooled in {hybrid['fooled_runs']}/{hybrid['attack_runs']} "
            f"spoofed-observation scenarios ({hybrid['fooled_rate_percent']}%)."
        ),
        (
            f"- Across all detectors, {fooled_total}/{len(rows)} runs "
            f"({100.0 * fooled_total / len(rows):.3f}%) reported an alarm relative "
            "to corrupted evidence while physical-fault metadata remained clean."
        ),
        "- Highest fooled-rate attack group(s): " + ", ".join(most_likely) + f" ({max_rate:.3f}%).",
        "- Attack groups with Hybrid resistance: "
        + (
            "; ".join(hybrid_resisted)
            if hybrid_resisted
            else "none in this matrix."
        ),
        "",
        "An alarm can be internally consistent with corrupted observations "
        "while still being false relative to the clean physical reference. A "
        "fooled classification therefore measures evidence-channel compromise, "
        "not detector quality in isolation.",
        "",
        "## Important limitations",
        "",
        *(f"- {line}" for line in limitations_lines()),
        "",
        "These findings do not establish perfect security, universal attack "
        "resistance, or an ability to always distinguish real from fake faults.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_readme(
    path: Path,
    attacks: Sequence[AttackSpec],
    rows: Sequence[Mapping[str, object]],
) -> None:
    lines = [
        "# Fake-Fault Attack Validation",
        "",
        "This generated study compares clean physical-reference runs with "
        "simulator runs that use existing opt-in replay inputs to corrupt "
        "ECU-facing evidence. It does not tune detectors or inject physical "
        "fault events.",
        "",
        "## Truth and observation layers",
        "",
        "1. `truth/` contains detector-matched clean baseline runs with no replay input.",
        "2. `attack_profiles/` contains deterministic sensor, fan_actual, and "
        "calibration replay traces derived from clean truth.",
        "3. `raw/` contains attack runs using the same baseline campaign and unchanged detectors.",
        "4. Reporting labels and fooled classifications are added only after each run and are never detector inputs.",
        "",
        "Every summary is checked for `campaign_id=baseline`, zero campaign "
        "events, and `fault_present_in_campaign=0`. Every attack raw row is "
        "checked for zero active/configured fault modes.",
        "",
        "## Matrix",
        "",
        f"- Fake-fault variants: {len(attacks)}.",
        f"- Detectors: {len(DETECTORS)}.",
        f"- Normalized attack runs: {len(rows)}.",
        "- Groups: fake coolant indications, stale-like coolant indications, "
        "fan_actual interface attacks, calibration/control attacks, and "
        "coordinated attacks.",
        "",
        "## Outputs",
        "",
        "- `fake_fault_attack_matrix.csv`: normalized physical-truth, observation, and detector outcomes.",
        "- `fake_fault_detector_summary.csv`: fooled and resisted outcomes by detector.",
        "- `fake_fault_scenario_summary.csv`: detector outcomes by attack variant.",
        "- `fake_fault_fooled_details.csv`: only fooled detector/attack rows.",
        "- `fake_fault_attack_profile_table.csv`: exact replay operations and trace paths.",
        "- `fake_fault_attack_group_summary.csv`: aggregate outcomes by attack group.",
        "- `fake_fault_claim_summary.md`: bounded claim-ready results.",
        "- `fake_fault_limitations.md`: replay and scope limitations.",
        "",
        "## Interpretation",
        "",
        "A detector is classified as fooled when it alarms in an attack run "
        "whose physical-fault and RTL-Trojan metadata are both zero. The alarm "
        "may be correct relative to corrupted evidence but false relative to "
        "the clean physical truth reference.",
        "",
        "## Limitations",
        "",
        *(f"- {line}" for line in limitations_lines()),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    executable = args.executable.resolve()
    output_dir = args.output_dir.resolve()
    if not executable.is_file():
        raise FileNotFoundError(
            f"Virtual ECU executable not found: {executable}. Run `make` first."
        )

    attacks = build_attacks()
    expected_rows = len(attacks) * len(DETECTORS)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("[1/4] Building detector-matched clean physical truth runs")
    truth, canonical_rows = run_truth_matrix(executable, output_dir)
    print("[2/4] Generating deterministic fake-fault replay traces")
    replay_inputs, profile_rows = write_attack_traces(
        output_dir,
        attacks,
        canonical_rows,
    )

    print(
        f"[3/4] Running {len(attacks)} fake-fault attacks across "
        f"{len(DETECTORS)} detectors ({expected_rows} runs)"
    )
    rows: List[Dict[str, object]] = []
    for index, attack in enumerate(attacks, start=1):
        print(f"  [{index:02d}/{len(attacks)}] {attack.scenario_id}")
        for detector in DETECTORS:
            rows.append(
                run_attack_detector(
                    executable,
                    output_dir,
                    attack,
                    detector,
                    replay_inputs,
                    truth,
                )
            )

    if len(rows) != expected_rows:
        raise RuntimeError(f"Expected {expected_rows} rows, found {len(rows)}.")
    if {str(row["detector"]) for row in rows} != set(DETECTORS):
        raise RuntimeError("Not all eight supported detectors were evaluated.")
    if any(parse_int(row["physical_fault_present"], 1) != 0 for row in rows):
        raise RuntimeError("A physical fault was marked present in the attack matrix.")
    if any(parse_int(row["rtl_trojan_present"], 1) != 0 for row in rows):
        raise RuntimeError("An RTL Trojan was marked present in the attack matrix.")
    if any(parse_int(row["fake_fault_attack_present"], 0) != 1 for row in rows):
        raise RuntimeError("A normalized row lacks fake-fault attack classification.")

    print("[4/4] Writing fake-fault outcome summaries")
    detector_rows = detector_summary(rows)
    scenario_rows = scenario_summary(rows)
    group_rows = attack_group_stats(rows)
    fooled_rows = [
        row
        for row in rows
        if parse_int(row["detector_was_fooled_by_fake_fault"], 0) != 0
    ]
    write_rows(output_dir / "fake_fault_attack_matrix.csv", MATRIX_COLUMNS, rows)
    write_rows(output_dir / "fake_fault_detector_summary.csv", DETECTOR_SUMMARY_COLUMNS, detector_rows)
    write_rows(output_dir / "fake_fault_scenario_summary.csv", SCENARIO_SUMMARY_COLUMNS, scenario_rows)
    write_rows(output_dir / "fake_fault_fooled_details.csv", MATRIX_COLUMNS, fooled_rows)
    write_rows(output_dir / "fake_fault_attack_profile_table.csv", PROFILE_TABLE_COLUMNS, profile_rows)
    write_rows(
        output_dir / "fake_fault_attack_group_summary.csv",
        (
            "scenario_group",
            "attack_variants",
            "detector_runs",
            "fooled_runs",
            "fooled_rate_percent",
            "hybrid_attack_runs",
            "hybrid_fooled_runs",
            "hybrid_resisted_runs",
        ),
        group_rows,
    )
    write_claim_summary(
        output_dir / "fake_fault_claim_summary.md",
        attacks,
        rows,
        detector_rows,
        group_rows,
    )
    write_readme(output_dir / "README.md", attacks, rows)
    (output_dir / "fake_fault_limitations.md").write_text(
        "# Fake-Fault Validation Limitations\n\n"
        + "\n".join(f"- {line}" for line in limitations_lines())
        + "\n",
        encoding="utf-8",
    )

    fooled_total = len(fooled_rows)
    hybrid = next(
        row for row in detector_rows if row["detector"] == "hybrid_adaptive_kalman"
    )
    print("Fake-fault attack validation complete")
    print(f"Attack variants: {len(attacks)}")
    print(f"Normalized detector runs: {len(rows)}")
    print(
        f"All-detector fooled runs: {fooled_total}/{len(rows)} "
        f"({100.0 * fooled_total / len(rows):.3f}%)"
    )
    print(
        f"Hybrid fooled runs: {hybrid['fooled_runs']}/{hybrid['attack_runs']} "
        f"({hybrid['fooled_rate_percent']}%)"
    )
    print(f"Output directory: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
