#!/usr/bin/env python3
"""Run systematic batch experiments for the virtual ECU platform."""

from __future__ import annotations

import argparse
import csv
import subprocess
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "results" / "batch"


@dataclass(frozen=True)
class SweepDefinition:
    campaign_id: str
    campaign_type: str
    fault_class: str
    fault_type: str
    fault_behavior: str
    start_times_ms: Sequence[int]
    durations_ms: Sequence[int]
    parameters: Sequence[float]


@dataclass(frozen=True)
class RunSpec:
    run_id: str
    campaign_id: str
    campaign_type: str
    fault_class: str
    fault_type: str
    fault_behavior: str
    fault_start_ms: int
    fault_duration_ms: int
    fault_parameter: float
    builtin_campaign: str | None = None


SWEEP_PROFILES: Dict[str, Sequence[SweepDefinition]] = {
    "quick": (
        SweepDefinition(
            campaign_id="sensing_sensor_bias_sweep",
            campaign_type="custom_single_fault",
            fault_class="sensing-path fault",
            fault_type="sensor_bias",
            fault_behavior="transient",
            start_times_ms=(20000, 40000),
            durations_ms=(10000, 20000),
            parameters=(4.0, 8.0),
        ),
        SweepDefinition(
            campaign_id="sensing_sensor_interface_intermittent_sweep",
            campaign_type="custom_single_fault",
            fault_class="sensing-path fault",
            fault_type="sensor_interface_intermittent",
            fault_behavior="transient",
            start_times_ms=(30000, 50000),
            durations_ms=(10000, 25000),
            parameters=(4.0, 8.0),
        ),
        SweepDefinition(
            campaign_id="actuation_pump_degraded_sweep",
            campaign_type="custom_single_fault",
            fault_class="actuation-path fault",
            fault_type="pump_degraded",
            fault_behavior="transient",
            start_times_ms=(40000, 70000),
            durations_ms=(10000, 25000),
            parameters=(0.75, 0.45),
        ),
        SweepDefinition(
            campaign_id="actuation_fan_stuck_off_sweep",
            campaign_type="custom_single_fault",
            fault_class="actuation-path fault",
            fault_type="fan_stuck_off",
            fault_behavior="permanent",
            start_times_ms=(75000, 90000),
            durations_ms=(0,),
            parameters=(0.0,),
        ),
        SweepDefinition(
            campaign_id="computation_calibration_memory_sweep",
            campaign_type="custom_single_fault",
            fault_class="computation/memory-path fault",
            fault_type="calibration_memory_corruption",
            fault_behavior="transient",
            start_times_ms=(30000, 60000),
            durations_ms=(10000, 30000),
            parameters=(8.0, 16.0),
        ),
    ),
    "conference": (
        SweepDefinition(
            campaign_id="sensing_sensor_bias_sweep",
            campaign_type="custom_single_fault",
            fault_class="sensing-path fault",
            fault_type="sensor_bias",
            fault_behavior="transient",
            start_times_ms=(20000, 30000, 45000),
            durations_ms=(5000, 15000, 30000),
            parameters=(4.0, 6.0, 8.0),
        ),
        SweepDefinition(
            campaign_id="sensing_sensor_interface_intermittent_sweep",
            campaign_type="custom_single_fault",
            fault_class="sensing-path fault",
            fault_type="sensor_interface_intermittent",
            fault_behavior="transient",
            start_times_ms=(25000, 45000, 65000),
            durations_ms=(5000, 20000, 35000),
            parameters=(4.0, 8.0, 12.0),
        ),
        SweepDefinition(
            campaign_id="actuation_pump_degraded_sweep",
            campaign_type="custom_single_fault",
            fault_class="actuation-path fault",
            fault_type="pump_degraded",
            fault_behavior="transient",
            start_times_ms=(40000, 60000, 80000),
            durations_ms=(10000, 25000, 40000),
            parameters=(0.75, 0.60, 0.45),
        ),
        SweepDefinition(
            campaign_id="actuation_fan_stuck_off_sweep",
            campaign_type="custom_single_fault",
            fault_class="actuation-path fault",
            fault_type="fan_stuck_off",
            fault_behavior="permanent",
            start_times_ms=(70000, 85000, 95000),
            durations_ms=(0,),
            parameters=(0.0,),
        ),
        SweepDefinition(
            campaign_id="computation_calibration_memory_sweep",
            campaign_type="custom_single_fault",
            fault_class="computation/memory-path fault",
            fault_type="calibration_memory_corruption",
            fault_behavior="transient",
            start_times_ms=(30000, 50000, 70000),
            durations_ms=(10000, 25000, 40000),
            parameters=(8.0, 12.0, 16.0),
        ),
    ),
}

AGGREGATE_COLUMNS = [
    "run_id",
    "batch_profile",
    "campaign_id",
    "campaign_type",
    "fault_class",
    "fault_type",
    "fault_behavior",
    "fault_parameter",
    "fault_start_time_ms",
    "fault_duration_ms",
    "raw_csv_path",
    "summary_csv_path",
    "simulator_campaign_id",
    "experiment_id",
    "detection_latency_ms",
    "safe_state_latency_ms",
    "max_coolant_temperature_c",
    "safe_mode_duration_ms",
    "final_safe_state",
    "final_dtc",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run systematic batch sweeps for the virtual ECU and write an aggregate summary CSV."
    )
    parser.add_argument(
        "--profile",
        choices=sorted(SWEEP_PROFILES.keys()),
        default="conference",
        help="Named sweep profile controlling the parameter grid.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Directory where batch outputs will be written.",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Subdirectory name under the output root. Defaults to the profile name.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for the number of generated runs, useful for smoke tests.",
    )
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Do not include the nominal baseline reference run in the batch output.",
    )
    return parser.parse_args()


def detect_executable() -> Path:
    for candidate in (PROJECT_ROOT / "virtual_ecu", PROJECT_ROOT / "virtual_ecu.exe"):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Compiled virtual ECU executable not found. Build it first with 'make' or your local GCC toolchain."
    )


def summary_path_for(log_path: Path) -> Path:
    return log_path.with_name(f"{log_path.stem}_summary.csv")


def read_single_csv_row(path: Path) -> Dict[str, str]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        raise ValueError(f"No rows found in summary CSV {path}")

    return rows[0]


def relative_to_project(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def format_parameter_token(parameter: float) -> str:
    return f"{parameter:.3f}".replace("-", "m").replace(".", "p")


def baseline_run_spec() -> RunSpec:
    return RunSpec(
        run_id="run_000_baseline_reference",
        campaign_id="baseline",
        campaign_type="built_in_reference",
        fault_class="baseline",
        fault_type="none",
        fault_behavior="none",
        fault_start_ms=0,
        fault_duration_ms=0,
        fault_parameter=0.0,
        builtin_campaign="baseline",
    )


def generate_run_specs(profile_name: str, include_baseline: bool) -> List[RunSpec]:
    specs: List[RunSpec] = []
    run_index = 1

    if include_baseline:
        specs.append(baseline_run_spec())

    for sweep in SWEEP_PROFILES[profile_name]:
        for start_ms, duration_ms, parameter in product(
            sweep.start_times_ms, sweep.durations_ms, sweep.parameters
        ):
            run_id = (
                f"run_{run_index:03d}_{sweep.fault_type}"
                f"_s{start_ms}_d{duration_ms}_p{format_parameter_token(parameter)}"
            )
            specs.append(
                RunSpec(
                    run_id=run_id,
                    campaign_id=sweep.campaign_id,
                    campaign_type=sweep.campaign_type,
                    fault_class=sweep.fault_class,
                    fault_type=sweep.fault_type,
                    fault_behavior=sweep.fault_behavior,
                    fault_start_ms=start_ms,
                    fault_duration_ms=duration_ms,
                    fault_parameter=parameter,
                )
            )
            run_index += 1

    return specs


def command_for_run(executable: Path, log_path: Path, spec: RunSpec) -> List[str]:
    if spec.builtin_campaign is not None:
        return [str(executable), str(log_path), spec.builtin_campaign]

    return [
        str(executable),
        str(log_path),
        "custom",
        spec.fault_type,
        str(spec.fault_start_ms),
        str(spec.fault_duration_ms),
        spec.fault_behavior,
        f"{spec.fault_parameter:.3f}",
    ]


def aggregate_row(
    profile_name: str,
    spec: RunSpec,
    raw_path: Path,
    summary_path: Path,
    summary_row: Dict[str, str],
) -> Dict[str, str]:
    return {
        "run_id": spec.run_id,
        "batch_profile": profile_name,
        "campaign_id": spec.campaign_id,
        "campaign_type": spec.campaign_type,
        "fault_class": spec.fault_class,
        "fault_type": spec.fault_type,
        "fault_behavior": spec.fault_behavior,
        "fault_parameter": f"{spec.fault_parameter:.3f}",
        "fault_start_time_ms": str(spec.fault_start_ms),
        "fault_duration_ms": str(spec.fault_duration_ms),
        "raw_csv_path": relative_to_project(raw_path),
        "summary_csv_path": relative_to_project(summary_path),
        "simulator_campaign_id": summary_row.get("campaign_id", ""),
        "experiment_id": summary_row.get("experiment_id", ""),
        "detection_latency_ms": summary_row.get("detection_latency_ms", ""),
        "safe_state_latency_ms": summary_row.get("safe_state_latency_ms", ""),
        "max_coolant_temperature_c": summary_row.get("max_coolant_temp_c", ""),
        "safe_mode_duration_ms": summary_row.get("safe_mode_duration_ms", ""),
        "final_safe_state": summary_row.get("final_safe_state_label", ""),
        "final_dtc": summary_row.get("final_primary_dtc_label", ""),
    }


def write_csv(path: Path, columns: Sequence[str], rows: Iterable[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        writer.writerows(rows)


def run_batch(profile_name: str, specs: Sequence[RunSpec], output_dir: Path) -> Path:
    executable = detect_executable()
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    aggregate_rows: List[Dict[str, str]] = []

    for index, spec in enumerate(specs, start=1):
        raw_path = runs_dir / f"{spec.run_id}.csv"
        summary_path = summary_path_for(raw_path)
        command = command_for_run(executable, raw_path, spec)

        print(f"[{index}/{len(specs)}] Running {spec.run_id}")
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"Batch run failed for {spec.run_id}.\n"
                f"Command: {' '.join(command)}\n"
                f"{completed.stderr or completed.stdout}"
            )

        summary_row = read_single_csv_row(summary_path)
        aggregate_rows.append(aggregate_row(profile_name, spec, raw_path, summary_path, summary_row))

    aggregate_path = output_dir / "aggregate_summary.csv"
    write_csv(aggregate_path, AGGREGATE_COLUMNS, aggregate_rows)
    return aggregate_path


def main() -> None:
    args = parse_args()
    batch_id = args.batch_id or args.profile
    output_dir = Path(args.output_root) / batch_id

    specs = generate_run_specs(args.profile, include_baseline=not args.skip_baseline)
    if args.limit is not None:
        specs = specs[: max(args.limit, 0)]

    if not specs:
        raise SystemExit("No batch runs were generated.")

    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate_path = run_batch(args.profile, specs, output_dir)

    print("\nBatch experiment complete.")
    print(f"Output directory: {output_dir}")
    print(f"Aggregate summary: {aggregate_path}")
    print(f"Per-run CSVs: {output_dir / 'runs'}")


if __name__ == "__main__":
    main()
