#!/usr/bin/env python3
"""Benchmark Virtual ECU host-side simulation speed against simulated time."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import shlex
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
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "simulation_realtime_benchmark"
RTL_RESULTS_DIR = PROJECT_ROOT / "results" / "rtl_hardware_trojan_study_v1"

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

MATRIX_COLUMNS = (
    "benchmark_id",
    "scenario_group",
    "scenario_name",
    "command",
    "detector",
    "repeat_count",
    "simulated_duration_ms",
    "simulated_duration_s",
    "wall_time_min_s",
    "wall_time_mean_s",
    "wall_time_median_s",
    "wall_time_max_s",
    "wall_time_std_s",
    "real_time_factor_min",
    "real_time_factor_mean",
    "real_time_factor_median",
    "real_time_factor_max",
    "faster_than_realtime_mean",
    "realtime_margin_x",
    "steps_observed",
    "effective_simulated_steps_per_wall_second",
    "output_raw_csv",
    "notes",
)

DETECTOR_SUMMARY_COLUMNS = (
    "detector",
    "cases",
    "mean_real_time_factor",
    "median_real_time_factor",
    "min_real_time_factor",
    "max_wall_time_s",
    "all_cases_faster_than_realtime",
    "notes",
)

SCENARIO_SUMMARY_COLUMNS = (
    "scenario_name",
    "detectors_tested",
    "mean_real_time_factor",
    "slowest_detector",
    "slowest_real_time_factor",
    "faster_than_realtime_for_all_detectors",
    "notes",
)


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    group: str
    name: str
    duration_ms: int
    campaign_arguments: tuple[str, ...] = ("baseline",)
    replay_arguments: tuple[str, ...] = ()
    notes: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Measure Virtual ECU simulation and detector wall-clock execution "
            "speed relative to simulated time."
        )
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--executable", type=Path, default=DEFAULT_EXECUTABLE)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument(
        "--warmup-runs",
        type=int,
        default=1,
        help="Untimed warm-up executions per case (default: 1).",
    )
    parser.add_argument(
        "--skip-rtl",
        action="store_true",
        help="Skip replay-only HT1-HT4 cases even when traces are available.",
    )
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
        raise RuntimeError(f"{label} failed ({shlex.join(command)}):\n{detail}")


def build_if_needed(executable: Path) -> None:
    if executable.is_file():
        return
    if executable.resolve() == DEFAULT_EXECUTABLE.resolve():
        print("Virtual ECU executable is missing; building it before timing.")
        run_checked(("make",), "Virtual ECU build")
    if not executable.is_file():
        raise FileNotFoundError(f"Virtual ECU executable not found: {executable}")


def replay_scenarios(warnings: List[str]) -> List[Scenario]:
    trace_specs = (
        (
            "rtl_ht1_coolant_sensor",
            "HT1 — Coolant Sensor Interface replay",
            (("--coolant-sensor-trace", "virtual_ecu_trojan_sensor_trace.csv"),),
        ),
        (
            "rtl_ht2_fan_driver",
            "HT2 — Fan Driver Interface replay",
            (("--fan-actual-trace", "virtual_ecu_trojan_fan_actual_trace.csv"),),
        ),
        (
            "rtl_ht3_calibration_memory",
            "HT3 — Calibration Memory Interface replay",
            (("--calibration-trace", "virtual_ecu_trojan_calibration_trace.csv"),),
        ),
        (
            "rtl_ht4_multi_stage_chain",
            "HT4 — Multi-Stage RTL Chain replay",
            (
                ("--calibration-trace", "virtual_ecu_trojan_calibration_trace.csv"),
                ("--coolant-sensor-trace", "virtual_ecu_trojan_sensor_trace.csv"),
                ("--fan-actual-trace", "virtual_ecu_trojan_fan_actual_trace.csv"),
            ),
        ),
    )
    scenarios: List[Scenario] = []
    for scenario_id, name, inputs in trace_specs:
        missing = [filename for _, filename in inputs if not (RTL_RESULTS_DIR / filename).is_file()]
        if missing:
            warnings.append(
                f"Skipped {name}: missing existing replay trace(s): {', '.join(missing)}."
            )
            continue
        arguments = tuple(
            token
            for option, filename in inputs
            for token in (option, str((RTL_RESULTS_DIR / filename).resolve()))
        )
        scenarios.append(
            Scenario(
                scenario_id,
                "rtl_security_replay",
                name,
                120000,
                replay_arguments=arguments,
                notes=(
                    "Replay-only timing using an existing Trojan trace; Verilator "
                    "generation and build time are excluded."
                ),
            )
        )
    return scenarios


def benchmark_scenarios(include_rtl: bool, warnings: List[str]) -> List[Scenario]:
    scenarios = [
        Scenario(
            "clean_baseline_120s",
            "clean_baseline",
            "Clean baseline — 120 s",
            120000,
            notes="Standard deterministic baseline simulator path.",
        ),
        Scenario(
            "fault_sensor_bias",
            "conventional_fault",
            "Sensor bias — medium transient",
            120000,
            ("custom", "sensor_bias", "45000", "15000", "transient", "6"),
            notes="Supported custom sensor-bias event used by existing validations.",
        ),
        Scenario(
            "fault_fan_stuck_off",
            "conventional_fault",
            "Fan stuck off — permanent",
            120000,
            ("custom", "fan_stuck_off", "75000", "0", "permanent", "0"),
            notes="Supported custom fan-stuck-off event used by existing validations.",
        ),
        Scenario(
            "fault_pump_degraded",
            "conventional_fault",
            "Pump degraded — medium transient",
            120000,
            ("custom", "pump_degraded", "60000", "25000", "transient", "0.45"),
            notes="Supported custom pump-degradation event used by existing validations.",
        ),
        Scenario(
            "fault_calibration_memory_corruption",
            "conventional_fault",
            "Calibration memory corruption — large permanent shift",
            120000,
            (
                "custom",
                "calibration_memory_corruption",
                "52000",
                "0",
                "permanent",
                "16",
            ),
            notes="Supported custom calibration-corruption event used by existing validations.",
        ),
        Scenario(
            "fault_stale_sensor_data",
            "conventional_fault",
            "Stale sensor data — medium transient hold",
            120000,
            ("custom", "stale_sensor_data", "45000", "25000", "transient", "5000"),
            notes="Supported custom stale-sensor event used by existing validations.",
        ),
        Scenario(
            "clean_duration_300s",
            "duration_scaling",
            "Clean duration scaling — 300 s",
            300000,
            notes="Longer clean run for host-side duration scaling evidence.",
        ),
        Scenario(
            "clean_duration_600s",
            "duration_scaling",
            "Clean duration scaling — 600 s",
            600000,
            notes="Longer clean run for host-side duration scaling evidence.",
        ),
    ]
    if include_rtl:
        scenarios.extend(replay_scenarios(warnings))
    else:
        warnings.append("RTL/security replay cases were disabled with --skip-rtl.")
    return scenarios


def simulator_command(
    executable: Path,
    raw_path: Path,
    scenario: Scenario,
    detector: str,
) -> List[str]:
    return [
        str(executable),
        str(raw_path),
        *scenario.campaign_arguments,
        "--detector",
        detector,
        "--detector-action",
        "observe_only",
        "--simulation-duration-ms",
        str(scenario.duration_ms),
        *scenario.replay_arguments,
    ]


def read_simulation_extent(raw_path: Path) -> tuple[int, int]:
    maximum_time_ms: int | None = None
    steps = 0
    with raw_path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            steps += 1
            value = row.get("time_ms", "").strip()
            if value:
                parsed = int(float(value))
                maximum_time_ms = parsed if maximum_time_ms is None else max(maximum_time_ms, parsed)
    if steps == 0:
        raise RuntimeError(f"Simulator raw CSV has no data rows: {raw_path}")
    if maximum_time_ms is None:
        raise RuntimeError(f"Simulator raw CSV has no usable time_ms values: {raw_path}")
    return maximum_time_ms, steps


def measured_run(command: Sequence[str], label: str) -> float:
    start = time.perf_counter()
    completed = subprocess.run(
        list(command),
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - start
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"{label} failed ({shlex.join(command)}):\n{detail}")
    return elapsed


def number(value: float) -> str:
    return f"{value:.6f}"


def benchmark_case(
    executable: Path,
    raw_dir: Path,
    scenario: Scenario,
    detector: str,
    repeats: int,
    warmup_runs: int,
) -> tuple[Dict[str, object], Dict[str, object]]:
    benchmark_id = f"{scenario.scenario_id}__{detector}"
    raw_path = raw_dir / f"{benchmark_id}.csv"
    command = simulator_command(executable, raw_path, scenario, detector)

    for index in range(warmup_runs):
        run_checked(command, f"{benchmark_id} warm-up {index + 1}")

    wall_times: List[float] = []
    extents: List[tuple[int, int]] = []
    for index in range(repeats):
        wall_times.append(measured_run(command, f"{benchmark_id} repeat {index + 1}"))
        extents.append(read_simulation_extent(raw_path))

    if len(set(extents)) != 1:
        raise RuntimeError(f"Inconsistent simulation extents across repeats for {benchmark_id}: {extents}")
    simulated_duration_ms, steps = extents[-1]
    simulated_duration_s = simulated_duration_ms / 1000.0
    wall_min = min(wall_times)
    wall_mean = statistics.mean(wall_times)
    wall_median = statistics.median(wall_times)
    wall_max = max(wall_times)
    wall_std = statistics.stdev(wall_times) if len(wall_times) > 1 else 0.0
    factor_min = simulated_duration_s / wall_max
    factor_mean = simulated_duration_s / wall_mean
    factor_median = simulated_duration_s / wall_median
    factor_max = simulated_duration_s / wall_min
    notes = scenario.notes
    if simulated_duration_ms != scenario.duration_ms:
        notes += (
            f" Configured duration was {scenario.duration_ms} ms; metrics use the "
            f"raw CSV maximum time_ms of {simulated_duration_ms} ms."
        )

    row: Dict[str, object] = {
        "benchmark_id": benchmark_id,
        "scenario_group": scenario.group,
        "scenario_name": scenario.name,
        "command": shlex.join(command),
        "detector": detector,
        "repeat_count": repeats,
        "simulated_duration_ms": simulated_duration_ms,
        "simulated_duration_s": number(simulated_duration_s),
        "wall_time_min_s": number(wall_min),
        "wall_time_mean_s": number(wall_mean),
        "wall_time_median_s": number(wall_median),
        "wall_time_max_s": number(wall_max),
        "wall_time_std_s": number(wall_std),
        "real_time_factor_min": number(factor_min),
        "real_time_factor_mean": number(factor_mean),
        "real_time_factor_median": number(factor_median),
        "real_time_factor_max": number(factor_max),
        "faster_than_realtime_mean": int(factor_mean >= 1.0),
        "realtime_margin_x": number(factor_mean),
        "steps_observed": steps,
        "effective_simulated_steps_per_wall_second": number(steps / wall_mean),
        "output_raw_csv": relative_path(raw_path),
        "notes": notes.strip(),
    }
    command_record = {
        "benchmark_id": benchmark_id,
        "command": command,
        "timed_repeats": repeats,
        "untimed_warmup_runs": warmup_runs,
    }
    return row, command_record


def detector_summary(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    summary = []
    for detector in DETECTORS:
        selected = [row for row in rows if row["detector"] == detector]
        factors = [float(row["real_time_factor_mean"]) for row in selected]
        if not factors:
            continue
        summary.append(
            {
                "detector": detector,
                "cases": len(selected),
                "mean_real_time_factor": number(statistics.mean(factors)),
                "median_real_time_factor": number(statistics.median(factors)),
                "min_real_time_factor": number(min(factors)),
                "max_wall_time_s": number(max(float(row["wall_time_max_s"]) for row in selected)),
                "all_cases_faster_than_realtime": int(all(factor >= 1.0 for factor in factors)),
                "notes": "Mean factors are computed from each case's mean wall-clock runtime.",
            }
        )
    return summary


def scenario_summary(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    summary = []
    names = list(dict.fromkeys(str(row["scenario_name"]) for row in rows))
    for name in names:
        selected = [row for row in rows if row["scenario_name"] == name]
        by_speed = sorted(selected, key=lambda row: float(row["real_time_factor_mean"]))
        factors = [float(row["real_time_factor_mean"]) for row in selected]
        summary.append(
            {
                "scenario_name": name,
                "detectors_tested": len(selected),
                "mean_real_time_factor": number(statistics.mean(factors)),
                "slowest_detector": by_speed[0]["detector"],
                "slowest_real_time_factor": number(float(by_speed[0]["real_time_factor_mean"])),
                "faster_than_realtime_for_all_detectors": int(all(factor >= 1.0 for factor in factors)),
                "notes": selected[0]["notes"],
            }
        )
    return summary


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
        with Path("/proc/cpuinfo").open("r", encoding="utf-8") as handle:
            for line in handle:
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
        "python_implementation": platform.python_implementation(),
        "cpu_model": cpu_model,
        "logical_cpu_count": os.cpu_count(),
        "wsl_detected": "microsoft" in proc_version.lower(),
        "proc_version": proc_version,
        "git_commit": command_output(("git", "rev-parse", "HEAD")),
        "git_status_short": command_output(("git", "status", "--short")),
    }


def write_readme(
    output_dir: Path,
    rows: Sequence[Dict[str, object]],
    host: Dict[str, object],
    repeats: int,
    warmups: int,
) -> None:
    factors = [float(row["real_time_factor_mean"]) for row in rows]
    rtl_count = sum(row["scenario_group"] == "rtl_security_replay" for row in rows)
    text = f"""# Simulation Real-Time Execution Benchmark

This benchmark measures the wall-clock execution time of the Virtual ECU simulator and one selected runtime detector per process on the evaluated host. It covers clean, conventional-fault, duration-scaling, and available replay-only RTL/security cases.

## Metric

`real_time_factor = simulated_duration_seconds / wall_clock_runtime_seconds`

- A factor above 1.0 means the simulation completed faster than wall-clock real time.
- A factor equal to 1.0 is approximately wall-clock real time.
- A factor below 1.0 means the simulation completed slower than wall-clock real time.

Simulated duration and timestep count are read from each produced raw CSV (`max(time_ms)` and data-row count). Each case has {repeats} timed repeats after {warmups} untimed warm-up run(s). Timing uses Python `time.perf_counter()` around only the simulator subprocess. CSV creation is part of simulator execution; report generation, plots, and GUI startup are excluded. The standard deviation is the sample standard deviation when multiple repeats exist.

## Coverage and result

- Aggregate cases: {len(rows)}
- Detectors: {len(set(str(row['detector']) for row in rows))}
- Scenarios: {len(set(str(row['scenario_name']) for row in rows))}
- RTL/security aggregate cases: {rtl_count}
- Slowest case mean factor: {min(factors):.3f}x
- Fastest case mean factor: {max(factors):.3f}x
- All evaluated cases faster than wall-clock real time: {'yes' if all(factor >= 1.0 for factor in factors) else 'no'}

The `builtin_ecu` case represents the simulator's standard built-in diagnostic path. The simulator exposes one runtime detector selection per process; it does not expose a detector-free mode or an existing all-detectors-in-one-process timing mode, so neither was invented for this benchmark.

## RTL/security scope

RTL cases replay existing HT1-HT4 Trojan traces through the unchanged Virtual ECU. Verilator compilation and trace generation are deliberately excluded from the normal simulation real-time factor. This keeps the measurement specific to host-side Virtual ECU replay and detector execution.

## Host context

- Platform: {host['platform']}
- Python: {host['python_version']} ({host['python_implementation']})
- CPU: {host['cpu_model']}
- Logical CPUs: {host['logical_cpu_count']}
- WSL detected: {host['wsl_detected']}
- Git commit: {host['git_commit']}

## Interpretation boundary

Runtime detectors operate against simulated online timesteps, while this benchmark asks whether those timesteps can be executed faster than elapsed wall-clock time on one host. These results are PC/WSL host timing evidence only. They are not embedded ECU hardware timing validation, hard real-time certification, production-readiness evidence, or a worst-case execution-time guarantee.
"""
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def write_claim_summary(output_dir: Path, rows: Sequence[Dict[str, object]]) -> str:
    factors = [float(row["real_time_factor_mean"]) for row in rows]
    all_fast = all(factor >= 1.0 for factor in factors)
    hybrid = [
        float(row["real_time_factor_mean"])
        for row in rows
        if row["detector"] == "hybrid_adaptive_kalman"
    ]
    if all_fast:
        claim = (
            "On the evaluated host platform, all benchmarked Virtual ECU simulation "
            "cases executed faster than wall-clock real time."
        )
    else:
        count = sum(factor >= 1.0 for factor in factors)
        claim = (
            f"On the evaluated host platform, {count} of {len(factors)} benchmarked "
            "Virtual ECU simulation cases executed faster than wall-clock real time."
        )
    text = f"""# Bounded Claim Summary

{claim}

Across the evaluated scenarios, Hybrid Adaptive Kalman achieved a mean real-time factor of {statistics.mean(hybrid):.3f}x. The evaluated-case range across all detector/scenario pairs was {min(factors):.3f}x to {max(factors):.3f}x using mean wall time per case.

This supports only host-side simulation execution feasibility for the evaluated scenarios. It does not constitute embedded ECU hardware validation, a hard real-time guarantee, certification, or production-readiness evidence.
"""
    (output_dir / "simulation_realtime_claim_summary.md").write_text(text, encoding="utf-8")
    return claim


def write_limitations(output_dir: Path) -> None:
    text = """# Simulation Real-Time Benchmark Limitations

- Measurements apply to this host PC/WSL environment only and are sensitive to its hardware and software configuration.
- This is not embedded ECU hardware timing validation, worst-case execution-time analysis, or hard real-time certification.
- Operating-system scheduling, background load, process startup, filesystem caching, and other host noise can affect wall-clock measurements.
- GUI startup and rendering are excluded; this benchmark measures the simulator subprocess and its CSV output path.
- Results apply only to the evaluated scenarios, durations, detector selections, and repeat count.
- RTL/security timings are replay-only when existing traces are available. Verilator build and trace-generation time are excluded and are not mixed into the simulation real-time factor.
- Each process selects one detector. The project has no supported detector-free or all-detectors-in-one-process benchmark mode.
- Mean-case factors are not guarantees of deadline behavior under arbitrary workloads or host contention.
"""
    (output_dir / "simulation_realtime_limitations.md").write_text(text, encoding="utf-8")


def write_figures(
    output_dir: Path,
    matrix_rows: Sequence[Dict[str, object]],
    detector_rows: Sequence[Dict[str, object]],
    scenario_rows: Sequence[Dict[str, object]],
    warnings: List[str],
) -> List[Path]:
    try:
        cache_dir = (
            Path(tempfile.gettempdir())
            / "virtual_ecu_realtime_benchmark_matplotlib"
        )
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
    paths: List[Path] = []

    fig, ax = plt.subplots(figsize=(10.5, 5.2), constrained_layout=True)
    detector_names = [str(row["detector"]) for row in detector_rows]
    detector_factors = [float(row["mean_real_time_factor"]) for row in detector_rows]
    ax.bar(detector_names, detector_factors, color="#2f7ed8")
    ax.axhline(1.0, color="#b23a48", linestyle="--", linewidth=1.2, label="real time")
    ax.set_ylabel("Mean real-time factor [x]")
    ax.set_title("Host Simulation Real-Time Factor by Detector")
    ax.tick_params(axis="x", labelrotation=24)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    ax.grid(axis="y", linestyle=":", alpha=0.55)
    ax.legend(frameon=False)
    path = figure_dir / "real_time_factor_by_detector.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    paths.append(path)

    scenario_names = [str(row["scenario_name"]) for row in scenario_rows]
    short_names = [name.replace(" — ", "\n") for name in scenario_names]
    scenario_factors = [float(row["mean_real_time_factor"]) for row in scenario_rows]
    fig, ax = plt.subplots(figsize=(12.5, 6.0), constrained_layout=True)
    ax.bar(short_names, scenario_factors, color="#28a080")
    ax.axhline(1.0, color="#b23a48", linestyle="--", linewidth=1.2, label="real time")
    ax.set_ylabel("Mean real-time factor [x]")
    ax.set_title("Host Simulation Real-Time Factor by Scenario")
    ax.tick_params(axis="x", labelrotation=28, labelsize=8)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    ax.grid(axis="y", linestyle=":", alpha=0.55)
    ax.legend(frameon=False)
    path = figure_dir / "real_time_factor_by_scenario.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(12.5, 6.0), constrained_layout=True)
    slowest_wall_times = []
    for summary_row in scenario_rows:
        selected = [
            row
            for row in matrix_rows
            if row["scenario_name"] == summary_row["scenario_name"]
            and row["detector"] == summary_row["slowest_detector"]
        ]
        slowest_wall_times.append(float(selected[0]["wall_time_mean_s"]))
    ax.bar(short_names, slowest_wall_times, color="#f0a33a")
    ax.set_ylabel("Slowest detector mean wall time [s]")
    ax.set_title("Host Wall Time by Scenario")
    ax.tick_params(axis="x", labelrotation=28, labelsize=8)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    ax.grid(axis="y", linestyle=":", alpha=0.55)
    path = figure_dir / "wall_time_by_scenario.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    paths.append(path)
    return paths


def main() -> int:
    args = parse_args()
    if args.repeats < 1:
        raise ValueError("--repeats must be at least 1")
    if args.warmup_runs < 0:
        raise ValueError("--warmup-runs must be non-negative")

    executable = args.executable.resolve()
    output_dir = args.output_dir.resolve()
    raw_dir = output_dir / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    build_if_needed(executable)

    warnings: List[str] = []
    scenarios = benchmark_scenarios(not args.skip_rtl, warnings)
    if not scenarios:
        raise RuntimeError("No benchmark scenarios are available")

    total = len(scenarios) * len(DETECTORS)
    print(
        f"Running {total} aggregate cases with {args.repeats} timed repeat(s) "
        f"and {args.warmup_runs} warm-up(s) per case."
    )
    rows: List[Dict[str, object]] = []
    commands: List[Dict[str, object]] = []
    case_index = 0
    for scenario in scenarios:
        print(f"- {scenario.name}")
        for detector in DETECTORS:
            case_index += 1
            print(f"  [{case_index:02d}/{total}] {detector}")
            row, command_record = benchmark_case(
                executable,
                raw_dir,
                scenario,
                detector,
                args.repeats,
                args.warmup_runs,
            )
            rows.append(row)
            commands.append(command_record)

    matrix_path = output_dir / "simulation_realtime_benchmark_matrix.csv"
    detector_path = output_dir / "simulation_realtime_detector_summary.csv"
    scenario_path = output_dir / "simulation_realtime_scenario_summary.csv"
    detector_rows = detector_summary(rows)
    scenario_rows = scenario_summary(rows)
    write_csv(matrix_path, MATRIX_COLUMNS, rows)
    write_csv(detector_path, DETECTOR_SUMMARY_COLUMNS, detector_rows)
    write_csv(scenario_path, SCENARIO_SUMMARY_COLUMNS, scenario_rows)

    host = host_info()
    write_readme(output_dir, rows, host, args.repeats, args.warmup_runs)
    claim = write_claim_summary(output_dir, rows)
    write_limitations(output_dir)

    figure_paths = [] if args.no_figures else write_figures(
        output_dir, rows, detector_rows, scenario_rows, warnings
    )

    factors = [float(row["real_time_factor_mean"]) for row in rows]
    hybrid = [
        float(row["real_time_factor_mean"])
        for row in rows
        if row["detector"] == "hybrid_adaptive_kalman"
    ]
    output_files = [
        output_dir / "README.md",
        matrix_path,
        detector_path,
        scenario_path,
        output_dir / "simulation_realtime_claim_summary.md",
        output_dir / "simulation_realtime_limitations.md",
        *figure_paths,
    ]
    manifest_path = output_dir / "evidence_manifest.json"
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host_info": host,
        "python_version": platform.python_version(),
        "timing_method": "time.perf_counter around simulator subprocess only",
        "benchmark_commands": commands,
        "output_files": [relative_path(path) for path in (*output_files, manifest_path)],
        "row_counts": {
            "benchmark_matrix": len(rows),
            "detector_summary": len(detector_rows),
            "scenario_summary": len(scenario_rows),
        },
        "key_metrics": {
            "fastest_real_time_factor_mean": max(factors),
            "slowest_real_time_factor_mean": min(factors),
            "hybrid_mean_real_time_factor": statistics.mean(hybrid),
            "all_cases_faster_than_realtime_mean": all(factor >= 1.0 for factor in factors),
            "bounded_claim": claim,
        },
        "scope": {
            "host_simulation_only": True,
            "embedded_hardware_validation": False,
            "gui_rendering_included": False,
            "rtl_replay_only": True,
            "verilator_generation_included": False,
        },
        "warnings": warnings,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Simulation real-time benchmark complete: {output_dir}")
    print(f"Slowest/Fastest mean real-time factor: {min(factors):.3f}x / {max(factors):.3f}x")
    print(claim)
    for warning in warnings:
        print(f"Warning: {warning}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
