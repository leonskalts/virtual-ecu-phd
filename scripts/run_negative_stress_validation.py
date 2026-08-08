#!/usr/bin/env python3
"""Measure runtime-detector false alarms over deterministic clean stress profiles."""

from __future__ import annotations

import argparse
import csv
import math
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "negative_stress_validation"
DEFAULT_EXECUTABLE = PROJECT_ROOT / "virtual_ecu"
OBSERVE_ONLY = "observe_only"
EXPERIMENT_FAMILY = "negative_stress_validation"

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

PROFILE_COLUMNS = (
    "start_ms",
    "end_ms",
    "vehicle_speed_kph",
    "engine_load",
    "ambient_temp_c",
    "external_airflow_factor",
    "road_slope_percent",
)

NORMALIZED_COLUMNS = (
    "experiment_family",
    "scenario_id",
    "scenario_name",
    "scenario_group",
    "variant",
    "detector",
    "is_clean",
    "false_alarm",
    "first_alarm_ms",
    "false_positive_count",
    "detection_label",
    "max_coolant_temp_c",
    "final_safe_state",
    "duration_ms",
    "profile_id",
    "profile_name",
    "raw_csv",
    "summary_csv",
    "notes",
)

DETECTOR_SUMMARY_COLUMNS = (
    "detector",
    "clean_runs",
    "false_alarm_runs",
    "false_alarm_rate_percent",
    "total_false_positive_episodes",
    "earliest_false_alarm_ms",
    "labels_seen",
    "scenario_groups_with_false_alarms",
)

SCENARIO_SUMMARY_COLUMNS = (
    "scenario_id",
    "scenario_name",
    "scenario_group",
    "detectors_tested",
    "detectors_with_false_alarm",
    "detector_names_with_false_alarm",
    "max_coolant_temp_c",
    "final_safe_state",
    "notes",
)

PROFILE_TABLE_COLUMNS = (
    "scenario_id",
    "scenario_name",
    "scenario_group",
    "variant",
    "duration_ms",
    "profile_id",
    "profile_name",
    "profile_source",
    "segment_index",
    *PROFILE_COLUMNS,
    "notes",
)


@dataclass(frozen=True)
class ProfileSegment:
    start_ms: int
    end_ms: int
    vehicle_speed_kph: float
    engine_load: float
    ambient_temp_c: float
    external_airflow_factor: float
    road_slope_percent: float

    def as_row(self) -> Dict[str, object]:
        return {
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "vehicle_speed_kph": self.vehicle_speed_kph,
            "engine_load": self.engine_load,
            "ambient_temp_c": self.ambient_temp_c,
            "external_airflow_factor": self.external_airflow_factor,
            "road_slope_percent": self.road_slope_percent,
        }


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    scenario_name: str
    scenario_group: str
    variant: str
    duration_ms: int
    profile_id: str
    profile_name: str
    segments: tuple[ProfileSegment, ...] | None
    notes: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run all eight unchanged runtime detectors over 60 deterministic "
            "no-fault stress variants and summarize false alarms."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated profiles, traces, tables, and reports.",
    )
    parser.add_argument(
        "--executable",
        type=Path,
        default=DEFAULT_EXECUTABLE,
        help="Path to the compiled virtual_ecu executable.",
    )
    return parser.parse_args()


def equal_segments(
    duration_ms: int,
    states: Sequence[tuple[float, float, float, float, float]],
) -> tuple[ProfileSegment, ...]:
    """Convert supported piecewise-constant driving states into full coverage."""
    if not states or len(states) > 16:
        raise ValueError("A driving profile must contain between 1 and 16 states.")
    segments: List[ProfileSegment] = []
    for index, state in enumerate(states):
        start_ms = (duration_ms * index) // len(states)
        end_ms = (duration_ms * (index + 1)) // len(states)
        segments.append(ProfileSegment(start_ms, end_ms, *state))
    return tuple(segments)


def constant_profile(
    duration_ms: int,
    speed_kph: float,
    load: float,
    ambient_c: float,
    airflow: float,
    slope_percent: float = 0.0,
) -> tuple[ProfileSegment, ...]:
    return equal_segments(
        duration_ms,
        ((speed_kph, load, ambient_c, airflow, slope_percent),),
    )


def build_scenarios() -> tuple[ScenarioSpec, ...]:
    scenarios: List[ScenarioSpec] = []

    def add(
        scenario_id: str,
        scenario_name: str,
        scenario_group: str,
        variant: str,
        duration_ms: int,
        segments: tuple[ProfileSegment, ...] | None,
        notes: str,
    ) -> None:
        default_profile = segments is None
        scenarios.append(
            ScenarioSpec(
                scenario_id=scenario_id,
                scenario_name=scenario_name,
                scenario_group=scenario_group,
                variant=variant,
                duration_ms=duration_ms,
                profile_id=(
                    "default_thermal_plant"
                    if default_profile
                    else f"profile_{scenario_id}"
                ),
                profile_name=(
                    "Built-in deterministic thermal drive cycle"
                    if default_profile
                    else f"Clean profile: {scenario_name}"
                ),
                segments=segments,
                notes=notes,
            )
        )

    for duration_s in (120, 300, 600):
        duration_ms = duration_s * 1000
        add(
            f"duration_default_{duration_s}s",
            f"Built-in clean cycle, {duration_s} s",
            "duration_variation",
            f"default_{duration_s}s",
            duration_ms,
            None,
            "No custom profile; the existing deterministic no-fault thermal "
            "cycle is extended to the requested duration.",
        )
        add(
            f"duration_steady_{duration_s}s",
            f"Steady nominal cruise, {duration_s} s",
            "duration_variation",
            f"steady_{duration_s}s",
            duration_ms,
            constant_profile(duration_ms, 55.0, 0.50, 28.0, 0.25),
            "Steady supported driving/environment inputs with no injected fault.",
        )

    ambient_values = (-10.0, 0.0, 10.0, 20.0, 25.0, 30.0, 34.0, 37.0, 40.0, 42.0)
    for index, ambient_c in enumerate(ambient_values, start=1):
        token = str(int(ambient_c)).replace("-", "minus")
        add(
            f"ambient_{index:02d}_{token}c",
            f"Steady cruise at {ambient_c:g} C ambient",
            "ambient_variation",
            f"ambient_{ambient_c:g}c",
            120000,
            constant_profile(120000, 55.0, 0.50, ambient_c, 0.25),
            "Ambient variation stays within the simulator's supported -40 to 80 C profile range.",
        )

    load_values = (0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.72, 0.80, 0.86, 0.92)
    for index, load in enumerate(load_values, start=1):
        add(
            f"load_{index:02d}_{int(round(load * 100)):02d}pct",
            f"Steady cruise at {load:.0%} engine load",
            "engine_load_variation",
            f"load_{int(round(load * 100))}pct",
            120000,
            constant_profile(120000, 55.0, load, 30.0, 0.25),
            "Constant valid engine-load input; no degraded component or fault event is configured.",
        )

    for index, speed_kph in enumerate((0.0, 10.0, 30.0, 55.0, 90.0), start=1):
        add(
            f"speed_{index:02d}_{int(speed_kph):03d}kph",
            f"Steady operation at {speed_kph:g} km/h",
            "speed_airflow_variation",
            f"speed_{speed_kph:g}kph",
            120000,
            constant_profile(120000, speed_kph, 0.55, 32.0, 0.20),
            "Supported steady speed exercises normal phase and ram-air transitions without a fault.",
        )
    for index, airflow in enumerate((0.0, 0.15, 0.30, 0.50, 0.75), start=1):
        add(
            f"airflow_{index:02d}_{int(round(airflow * 100)):02d}pct",
            f"Urban cruise with {airflow:.0%} external airflow",
            "speed_airflow_variation",
            f"airflow_{int(round(airflow * 100))}pct",
            120000,
            constant_profile(120000, 35.0, 0.55, 32.0, airflow),
            "External airflow uses the existing clean profile input and does not alter actuator behavior.",
        )

    load_sequences = (
        ("step_up_mild", "Mild load step-up", (0.30, 0.30, 0.55, 0.55)),
        ("step_up_strong", "Strong load step-up", (0.25, 0.25, 0.78, 0.78)),
        ("step_down_mild", "Mild load step-down", (0.65, 0.65, 0.40, 0.40)),
        ("step_down_strong", "Strong load step-down", (0.82, 0.82, 0.30, 0.30)),
        ("repeated_pulses", "Repeated load pulses", (0.35, 0.75, 0.35, 0.75, 0.35, 0.75, 0.35, 0.55)),
        ("short_pulses", "Short bounded load pulses", (0.45, 0.70, 0.45, 0.70, 0.45, 0.70, 0.45, 0.70, 0.45, 0.55)),
        ("hill_load", "Hill-climb-like load cycle", (0.45, 0.55, 0.65, 0.75, 0.82, 0.70, 0.55, 0.40)),
    )
    for index, (token, name, loads) in enumerate(load_sequences, start=1):
        states = tuple((55.0, load, 31.0, 0.25, 0.0) for load in loads)
        add(
            f"dynamic_load_{index:02d}_{token}",
            name,
            "dynamic_load_profiles",
            token,
            120000,
            equal_segments(120000, states),
            "Piecewise-constant clean load schedule using only the supported driving-profile mechanism.",
        )
    sine_states = tuple(
        (55.0, 0.52 + 0.25 * math.sin((2.0 * math.pi * index) / 12.0), 31.0, 0.25, 0.0)
        for index in range(12)
    )
    add(
        "dynamic_load_08_smooth_wave",
        "Smooth-wave load approximation",
        "dynamic_load_profiles",
        "smooth_wave",
        120000,
        equal_segments(120000, sine_states),
        "A deterministic 12-segment approximation is used because profiles "
        "support piecewise-constant, not continuous sinusoidal, inputs.",
    )

    speed_sequences = (
        ("stop_go_mild", "Mild stop-and-go cycle", (0, 25, 10, 35, 0, 30, 15, 40)),
        ("stop_go_dense", "Dense stop-and-go cycle", (0, 15, 0, 25, 0, 20, 0, 30, 10, 0)),
        ("idle_to_highway", "Idle-to-highway transition", (0, 0, 20, 45, 75, 95)),
        ("highway_to_idle", "Highway-to-idle transition", (100, 90, 70, 40, 15, 0)),
        ("urban_cycle", "Varying urban speed cycle", (20, 35, 50, 30, 10, 25, 45, 20)),
        ("highway_cycle", "Varying highway speed cycle", (70, 85, 105, 90, 75, 110, 95, 80)),
        ("cooldown", "Highway cooldown transition", (25, 40, 60, 80, 100, 110)),
        ("airflow_transient", "Speed and airflow transient cycle", (15, 35, 70, 95, 55, 25, 0, 40)),
    )
    for index, (token, name, speeds) in enumerate(speed_sequences, start=1):
        states = []
        for state_index, speed in enumerate(speeds):
            load = 0.62 if speed < 20 else (0.55 if speed < 70 else 0.48)
            airflow = 0.10 + (0.08 * (state_index % 4)) if token == "airflow_transient" else 0.20
            states.append((float(speed), load, 32.0, airflow, 0.0))
        add(
            f"dynamic_speed_{index:02d}_{token}",
            name,
            "dynamic_speed_profiles",
            token,
            120000,
            equal_segments(120000, tuple(states)),
            "Deterministic clean speed/airflow transitions with normal controller and actuator operation.",
        )

    combined_specs = (
        (
            "hot_high_load",
            "Hot ambient with sustained high load",
            120000,
            constant_profile(120000, 50.0, 0.80, 40.0, 0.25, 2.0),
            "Combined hot ambient, load, and mild grade stress within supported clean-profile limits.",
        ),
        (
            "hot_low_speed",
            "Hot ambient with low-speed cooling",
            120000,
            constant_profile(120000, 15.0, 0.68, 40.0, 0.15, 1.0),
            "Hot low-speed clean operation; no fan or pump fault is configured.",
        ),
        (
            "hot_stop_go",
            "Hot stop-and-go cycle",
            120000,
            equal_segments(
                120000,
                tuple(
                    (float(speed), 0.62, 38.0, 0.15, 1.0)
                    for speed in (0, 25, 5, 35, 0, 30, 10, 40)
                ),
            ),
            "Hot urban transitions exercise normal fan-command changes without a stuck actuator.",
        ),
        (
            "warm_load_pulses",
            "Warm ambient with repeated load pulses",
            120000,
            equal_segments(
                120000,
                tuple(
                    (45.0, load, 36.0, 0.20, 0.0)
                    for load in (0.40, 0.75, 0.40, 0.80, 0.40, 0.75, 0.45, 0.60)
                ),
            ),
            "Warm clean profile combines bounded thermal and load transients.",
        ),
        (
            "long_moderate_load",
            "Long moderate-load warm cruise",
            300000,
            constant_profile(300000, 55.0, 0.65, 34.0, 0.25, 1.0),
            "Long-duration clean profile with moderate sustained load.",
        ),
        (
            "long_varying_speed",
            "Long varying-speed warm cycle",
            300000,
            equal_segments(
                300000,
                tuple(
                    (float(speed), 0.58, 34.0, 0.20, 0.0)
                    for speed in (15, 35, 70, 95, 55, 25, 0, 40, 80, 50, 20, 65)
                ),
            ),
            "Long clean cycle with deterministic speed transitions.",
        ),
        (
            "warm_hill_climb",
            "Warm hill-climb-like cycle",
            120000,
            equal_segments(
                120000,
                tuple(
                    (45.0, load, 36.0, 0.20, slope)
                    for load, slope in (
                        (0.50, 1),
                        (0.58, 3),
                        (0.65, 5),
                        (0.72, 7),
                        (0.78, 8),
                        (0.68, 5),
                        (0.55, 2),
                        (0.42, 0),
                    )
                ),
            ),
            "Road grade is the simulator's supported clean load context; no component degradation is injected.",
        ),
        (
            "near_boundary_thermal",
            "Near-boundary valid thermal stress",
            120000,
            equal_segments(
                120000,
                (
                    (25.0, 0.68, 38.0, 0.12, 1.0),
                    (20.0, 0.74, 39.0, 0.10, 2.0),
                    (30.0, 0.70, 38.0, 0.15, 1.0),
                    (45.0, 0.60, 36.0, 0.20, 0.0),
                ),
            ),
            "Designed to approach normal thermal boundaries while retaining "
            "healthy sensing, control, pump, and fan paths.",
        ),
    )
    for index, (token, name, duration_ms, segments, notes) in enumerate(combined_specs, start=1):
        add(
            f"combined_{index:02d}_{token}",
            name,
            "combined_boundary_stress",
            token,
            duration_ms,
            segments,
            notes,
        )

    if len(scenarios) != 60:
        raise RuntimeError(f"Expected 60 negative-stress variants, found {len(scenarios)}.")
    if len({scenario.scenario_id for scenario in scenarios}) != len(scenarios):
        raise RuntimeError("Negative-stress scenario IDs must be unique.")
    return tuple(scenarios)


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


def read_one_row(path: Path) -> Dict[str, str]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise RuntimeError(f"Expected one summary row in {path}, found {len(rows)}.")
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


def write_profiles(
    output_dir: Path,
    scenarios: Sequence[ScenarioSpec],
) -> tuple[Dict[str, Path], List[Dict[str, object]]]:
    profile_dir = output_dir / "profiles"
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_paths: Dict[str, Path] = {}
    table_rows: List[Dict[str, object]] = []
    for scenario in scenarios:
        common = {
            "scenario_id": scenario.scenario_id,
            "scenario_name": scenario.scenario_name,
            "scenario_group": scenario.scenario_group,
            "variant": scenario.variant,
            "duration_ms": scenario.duration_ms,
            "profile_id": scenario.profile_id,
            "profile_name": scenario.profile_name,
            "notes": scenario.notes,
        }
        if scenario.segments is None:
            table_rows.append(
                {
                    **common,
                    "profile_source": "built_in_default_thermal_plant",
                    "segment_index": "",
                    **{column: "" for column in PROFILE_COLUMNS},
                }
            )
            continue
        path = profile_dir / f"{scenario.profile_id}.csv"
        write_rows(path, PROFILE_COLUMNS, (segment.as_row() for segment in scenario.segments))
        profile_paths[scenario.profile_id] = path
        for index, segment in enumerate(scenario.segments, start=1):
            table_rows.append(
                {
                    **common,
                    "profile_source": relative_path(path),
                    "segment_index": index,
                    **segment.as_row(),
                }
            )
    return profile_paths, table_rows


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


def validate_clean_summary(
    summary: Mapping[str, str],
    scenario: ScenarioSpec,
    detector: str,
) -> None:
    checks = {
        "campaign_id": "baseline",
        "campaign_event_count": "0",
        "fault_present_in_campaign": "0",
        "runtime_detection_algorithm": detector,
        "runtime_detection_action": OBSERVE_ONLY,
        "simulation_duration_ms": str(scenario.duration_ms),
    }
    for column, expected in checks.items():
        actual = str(summary.get(column, "")).strip()
        if actual != expected:
            raise RuntimeError(
                f"Clean-run invariant failed for {scenario.scenario_id}/{detector}: "
                f"{column}={actual!r}, expected {expected!r}."
            )


def scan_clean_raw(
    raw_path: Path,
    scenario: ScenarioSpec,
    detector: str,
) -> tuple[int, int, str]:
    first_alarm_ms = -1
    detection_label = "none"
    false_positive_count = 0
    rows_seen = 0
    with raw_path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows_seen += 1
            if row.get("campaign_id") != "baseline":
                raise RuntimeError(f"Non-baseline row found in clean trace {raw_path}.")
            if parse_int(row.get("campaign_event_count", "-1")) != 0:
                raise RuntimeError(f"Fault event metadata found in clean trace {raw_path}.")
            if parse_int(row.get("fault_mode_id", "-1")) != 0:
                raise RuntimeError(f"Active fault found in clean trace {raw_path}.")
            if any(
                parse_int(row.get(f"campaign_event_{index}_mode_id", "-1")) != 0
                for index in range(1, 5)
            ):
                raise RuntimeError(f"Configured fault metadata found in clean trace {raw_path}.")
            if abs(parse_float(row.get("control_target_deviation_c", "nan"))) > 1.0e-6:
                raise RuntimeError(f"Control-target corruption found in clean trace {raw_path}.")
            if row.get("runtime_detection_algorithm") != detector:
                raise RuntimeError(f"Detector mismatch found in trace {raw_path}.")
            if row.get("runtime_detection_action") != OBSERVE_ONLY:
                raise RuntimeError(f"Non-observe-only action found in trace {raw_path}.")

            false_positive_count = max(
                false_positive_count,
                parse_int(row.get("runtime_detection_false_positive_count", "0"), 0),
            )
            alarm = parse_int(row.get("runtime_detection_alarm", "0"), 0) != 0
            detected = parse_int(row.get("runtime_detection_detected", "0"), 0) != 0
            if (alarm or detected) and first_alarm_ms < 0:
                first_alarm_ms = parse_int(row.get("time_ms", "-1"))
                detection_label = row.get("runtime_detection_label", "none") or "none"

    if rows_seen == 0:
        raise RuntimeError(f"Raw trace has no rows: {raw_path}")
    return first_alarm_ms, false_positive_count, detection_label


def run_scenario_detector(
    executable: Path,
    output_dir: Path,
    scenario: ScenarioSpec,
    detector: str,
    profile_paths: Mapping[str, Path],
) -> Dict[str, object]:
    raw_dir = output_dir / "raw" / scenario.scenario_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{detector}.csv"
    summary_path = summary_path_for(raw_path)
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
    if scenario.segments is not None:
        command.extend(("--driving-profile", str(profile_paths[scenario.profile_id])))
    run_checked(command, f"{scenario.scenario_id}/{detector}")

    summary = read_one_row(summary_path)
    validate_clean_summary(summary, scenario, detector)
    first_alarm_ms, false_positive_count, detection_label = scan_clean_raw(
        raw_path,
        scenario,
        detector,
    )
    false_alarm = int(first_alarm_ms >= 0 or false_positive_count > 0)
    if false_alarm == 0:
        first_alarm_ms = -1
        detection_label = "none"
    elif first_alarm_ms < 0:
        detection_label = summary.get("runtime_detection_label", "unknown") or "unknown"

    return {
        "experiment_family": EXPERIMENT_FAMILY,
        "scenario_id": scenario.scenario_id,
        "scenario_name": scenario.scenario_name,
        "scenario_group": scenario.scenario_group,
        "variant": scenario.variant,
        "detector": detector,
        "is_clean": 1,
        "false_alarm": false_alarm,
        "first_alarm_ms": first_alarm_ms,
        "false_positive_count": false_positive_count,
        "detection_label": detection_label,
        "max_coolant_temp_c": f"{parse_float(summary.get('max_coolant_temp_c', '')):.2f}",
        "final_safe_state": summary.get("final_safe_state_label", "unknown"),
        "duration_ms": parse_int(summary.get("simulation_duration_ms", "")),
        "profile_id": scenario.profile_id,
        "profile_name": scenario.profile_name,
        "raw_csv": relative_path(raw_path),
        "summary_csv": relative_path(summary_path),
        "notes": scenario.notes,
    }


def detector_summary(rows: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    output: List[Dict[str, object]] = []
    for detector in DETECTORS:
        subset = [row for row in rows if row["detector"] == detector]
        alarms = [row for row in subset if parse_int(row["false_alarm"], 0) != 0]
        alarm_times = [parse_int(row["first_alarm_ms"]) for row in alarms if parse_int(row["first_alarm_ms"]) >= 0]
        output.append(
            {
                "detector": detector,
                "clean_runs": len(subset),
                "false_alarm_runs": len(alarms),
                "false_alarm_rate_percent": f"{(100.0 * len(alarms) / len(subset)) if subset else 0.0:.3f}",
                "total_false_positive_episodes": sum(parse_int(row["false_positive_count"], 0) for row in subset),
                "earliest_false_alarm_ms": min(alarm_times) if alarm_times else -1,
                "labels_seen": ";".join(sorted({str(row["detection_label"]) for row in alarms})) or "none",
                "scenario_groups_with_false_alarms": ";".join(
                    sorted({str(row["scenario_group"]) for row in alarms})
                )
                or "none",
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
        alarm_detectors = sorted(
            str(row["detector"])
            for row in subset
            if parse_int(row["false_alarm"], 0) != 0
        )
        safe_states = sorted({str(row["final_safe_state"]) for row in subset})
        output.append(
            {
                "scenario_id": scenario_id,
                "scenario_name": first["scenario_name"],
                "scenario_group": first["scenario_group"],
                "detectors_tested": len({str(row["detector"]) for row in subset}),
                "detectors_with_false_alarm": len(alarm_detectors),
                "detector_names_with_false_alarm": ";".join(alarm_detectors) or "none",
                "max_coolant_temp_c": f"{max(parse_float(row['max_coolant_temp_c']) for row in subset):.2f}",
                "final_safe_state": ";".join(safe_states),
                "notes": first["notes"],
            }
        )
    return output


def write_claim_summary(
    path: Path,
    scenarios: Sequence[ScenarioSpec],
    rows: Sequence[Mapping[str, object]],
    detector_rows: Sequence[Mapping[str, object]],
) -> None:
    alarm_rows = [row for row in rows if parse_int(row["false_alarm"], 0) != 0]
    hybrid = next(row for row in detector_rows if row["detector"] == "hybrid_adaptive_kalman")
    alarm_detectors = [
        f"{row['detector']} ({row['false_alarm_runs']}/{row['clean_runs']} runs)"
        for row in detector_rows
        if parse_int(row["false_alarm_runs"], 0) != 0
    ]
    alarm_groups = sorted({str(row["scenario_group"]) for row in alarm_rows})
    lines = [
        "# Negative Stress False-Alarm Claim Summary",
        "",
        "## Bounded results",
        "",
        f"- Evaluated deterministic no-fault stress variants: {len(scenarios)}.",
        f"- Normalized detector runs: {len(rows)} ({len(scenarios)} variants × {len(DETECTORS)} detectors).",
        f"- Clean runs with at least one detector alarm: {len(alarm_rows)}.",
        "- Reported false-positive episodes across all runs: "
        f"{sum(parse_int(row['false_positive_count'], 0) for row in rows)}.",
        (
            "- In the evaluated deterministic negative stress matrix, "
            f"Hybrid Adaptive Kalman produced {hybrid['false_alarm_runs']} false-alarm runs "
            f"out of {hybrid['clean_runs']} ({hybrid['false_alarm_rate_percent']}%)."
        ),
        "- Detectors with false-alarm runs: " + (", ".join(alarm_detectors) if alarm_detectors else "none."),
        "- Scenario groups with false-alarm runs: " + (", ".join(alarm_groups) if alarm_groups else "none."),
        "",
        "## Scope boundary",
        "",
        "These statements apply only to the evaluated deterministic "
        "baseline-campaign profiles and unchanged detector configurations. "
        "They do not establish that a detector can never produce a false alarm.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_readme(
    path: Path,
    scenarios: Sequence[ScenarioSpec],
    rows: Sequence[Mapping[str, object]],
) -> None:
    groups = sorted({scenario.scenario_group for scenario in scenarios})
    lines = [
        "# Negative Stress Validation",
        "",
        "This directory is generated by "
        "`scripts/run_negative_stress_validation.py`. It measures false alarms "
        "from the eight unchanged runtime detectors under deterministic, "
        "stressful, but no-fault operation.",
        "",
        "## Clean-run controls",
        "",
        "- Every simulator invocation uses the existing `baseline` campaign.",
        "- Every summary is checked for zero configured campaign events and `fault_present_in_campaign = 0`.",
        "- Every raw row is checked for zero active/configured fault modes and zero control-target deviation.",
        "- No sensor, fan, calibration, or RTL replay trace is supplied.",
        "- Detector action is `observe_only`, so detector alarms do not alter the plant.",
        "- Scenario/report labels are added only after each simulator run and are never detector inputs.",
        "",
        "## Matrix",
        "",
        f"- No-fault variants: {len(scenarios)}.",
        f"- Detectors: {len(DETECTORS)}.",
        f"- Normalized detector runs: {len(rows)}.",
        f"- Scenario groups: {', '.join(groups)}.",
        "",
        "## Outputs",
        "",
        "- `negative_stress_false_alarm_matrix.csv`: one normalized row per scenario/detector run.",
        "- `negative_stress_detector_summary.csv`: false-alarm totals and rates by detector.",
        "- `negative_stress_scenario_summary.csv`: detector outcomes by clean scenario.",
        "- `negative_stress_false_alarm_details.csv`: only runs containing an alarm.",
        "- `negative_stress_clean_profile_table.csv`: exact supported profile segments used by each scenario.",
        "- `negative_stress_claim_summary.md`: bounded claim-ready findings.",
        "- `profiles/`: generated clean driving/environment CSV inputs.",
        "- `raw/`: raw simulator traces and existing simulator summary CSVs.",
        "",
        "## Limitations",
        "",
        "- The simulator has no supported normal-operation sensor-noise option, so this runner does not invent one.",
        "- The normal controller target is fixed at 92 C; no scheduled target variation is fabricated.",
        "- Continuous sinusoidal inputs are unsupported. The smooth-wave load "
        "case uses a deterministic 12-segment piecewise-constant approximation.",
        "- The plant and profiles are compact research models, not calibrated production-vehicle environments.",
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

    scenarios = build_scenarios()
    expected_rows = len(scenarios) * len(DETECTORS)
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_paths, profile_rows = write_profiles(output_dir, scenarios)

    print(
        f"[1/3] Running {len(scenarios)} deterministic no-fault variants "
        f"across {len(DETECTORS)} detectors ({expected_rows} runs)"
    )
    rows: List[Dict[str, object]] = []
    for index, scenario in enumerate(scenarios, start=1):
        print(f"  [{index:02d}/{len(scenarios)}] {scenario.scenario_id}")
        for detector in DETECTORS:
            rows.append(
                run_scenario_detector(
                    executable,
                    output_dir,
                    scenario,
                    detector,
                    profile_paths,
                )
            )

    if len(rows) != expected_rows:
        raise RuntimeError(f"Expected {expected_rows} normalized rows, found {len(rows)}.")
    if {str(row["detector"]) for row in rows} != set(DETECTORS):
        raise RuntimeError("Not all eight supported detectors were evaluated.")
    if any(parse_int(row["is_clean"], 0) != 1 for row in rows):
        raise RuntimeError("Negative-stress matrix contains a non-clean normalized row.")

    print("[2/3] Writing false-alarm matrices and summaries")
    detector_rows = detector_summary(rows)
    scenario_rows = scenario_summary(rows)
    alarm_rows = [row for row in rows if parse_int(row["false_alarm"], 0) != 0]
    write_rows(output_dir / "negative_stress_false_alarm_matrix.csv", NORMALIZED_COLUMNS, rows)
    write_rows(output_dir / "negative_stress_detector_summary.csv", DETECTOR_SUMMARY_COLUMNS, detector_rows)
    write_rows(output_dir / "negative_stress_scenario_summary.csv", SCENARIO_SUMMARY_COLUMNS, scenario_rows)
    write_rows(output_dir / "negative_stress_false_alarm_details.csv", NORMALIZED_COLUMNS, alarm_rows)
    write_rows(output_dir / "negative_stress_clean_profile_table.csv", PROFILE_TABLE_COLUMNS, profile_rows)
    write_claim_summary(output_dir / "negative_stress_claim_summary.md", scenarios, rows, detector_rows)
    write_readme(output_dir / "README.md", scenarios, rows)

    hybrid = next(row for row in detector_rows if row["detector"] == "hybrid_adaptive_kalman")
    print("[3/3] Negative stress validation complete")
    print(f"No-fault scenario variants: {len(scenarios)}")
    print(f"Normalized detector runs: {len(rows)}")
    print(f"All-detector false-alarm runs: {len(alarm_rows)}")
    print(
        "Hybrid false-alarm runs: "
        f"{hybrid['false_alarm_runs']}/{hybrid['clean_runs']} "
        f"({hybrid['false_alarm_rate_percent']}%)"
    )
    print(f"Output directory: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
