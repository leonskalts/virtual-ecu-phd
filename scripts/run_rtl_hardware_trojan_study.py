#!/usr/bin/env python3
"""Run the trace-driven RTL coolant-sensor Hardware Trojan study."""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT / "results" / "rtl_hardware_trojan_study_v1"
)
DEFAULT_EXECUTABLE = PROJECT_ROOT / "virtual_ecu"
RTL_DIR = PROJECT_ROOT / "rtl" / "security"
RTL_WRAPPER = (
    PROJECT_ROOT / "sim" / "security" / "coolant_sensor_interface_tb.v"
)

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

COMPARISON_COLUMNS = (
    "experiment_kind",
    "variant",
    "rtl_trojan_enabled",
    "rtl_trojan_type",
    "rtl_trojan_target",
    "detector",
    "runtime_detection_detected",
    "detected_after_payload",
    "runtime_detection_first_detection_ms",
    "detection_latency_from_payload_ms",
    "runtime_reported_false_positive_count",
    "runtime_detection_label",
    "rtl_trojan_triggered",
    "rtl_trojan_payload_active",
    "rtl_trojan_trigger_time_ms",
    "rtl_clean_sensor_value_c",
    "rtl_trojan_sensor_value_c",
    "first_ecu_dtc_label_after_payload",
    "first_ecu_dtc_time_ms",
    "max_coolant_temp_c",
    "final_safe_state",
    "raw_csv",
    "summary_csv",
)

VERILATOR_HARNESS = r"""
#include <cstdint>
#include <fstream>
#include <iostream>

#include "Vcoolant_sensor_interface_tb.h"
#include "verilated.h"

static int signed_value(std::uint16_t value)
{
    return static_cast<std::int16_t>(value);
}

static void clock_cycle(Vcoolant_sensor_interface_tb &top)
{
    top.clk = 0;
    top.eval();
    top.clk = 1;
    top.eval();
    top.clk = 0;
    top.eval();
}

int main(int argc, char **argv)
{
    Verilated::commandArgs(argc, argv);
    if (argc != 3) {
        std::cerr << "usage: rtl_trojan_trace_sim INPUT OUTPUT\n";
        return 2;
    }

    std::ifstream input(argv[1]);
    std::ofstream output(argv[2]);
    if (!input || !output) {
        std::cerr << "unable to open RTL trace input or output\n";
        return 2;
    }

    Vcoolant_sensor_interface_tb top;
    top.reset_n = 0;
    top.sensor_in = 0;
    clock_cycle(top);
    clock_cycle(top);
    top.reset_n = 1;

    output
        << "time_ms,sensor_in_deci_c,clean_sensor_out_deci_c,"
        << "trojan_sensor_out_deci_c,trojan_triggered,payload_active,"
        << "trigger_counter,rtl_clean_sensor_value_deci_c,"
        << "rtl_trojan_sensor_value_deci_c\n";

    unsigned int time_ms = 0;
    int sensor_value = 0;
    while (input >> time_ms >> sensor_value) {
        top.sensor_in = static_cast<std::uint16_t>(sensor_value);
        clock_cycle(top);
        output
            << time_ms << ","
            << sensor_value << ","
            << signed_value(top.clean_sensor_out) << ","
            << signed_value(top.trojan_sensor_out) << ","
            << static_cast<int>(top.trojan_triggered) << ","
            << static_cast<int>(top.payload_active) << ","
            << top.trigger_counter << ","
            << signed_value(top.trojan_clean_sensor_value) << ","
            << signed_value(top.trojan_debug_sensor_value) << "\n";
    }

    top.final();
    return 0;
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build and simulate the clean and Trojan-infected coolant sensor "
            "RTL, then replay each output through the existing Virtual ECU "
            "runtime detectors."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for security-study traces and reports.",
    )
    parser.add_argument(
        "--executable",
        type=Path,
        default=DEFAULT_EXECUTABLE,
        help="Path to the virtual_ecu executable.",
    )
    parser.add_argument(
        "--simulation-duration-ms",
        type=int,
        default=120000,
        help="Duration of the source and trace-replay runs.",
    )
    return parser.parse_args()


def run_checked(command: Sequence[str], cwd: Path) -> None:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"Command failed ({' '.join(command)}):\n{detail}"
        )


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"CSV has no data rows: {path}")
    return rows


def write_rows(
    path: Path,
    columns: Sequence[str],
    rows: Iterable[Dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())


def summary_path(raw_path: Path) -> Path:
    return raw_path.with_name(f"{raw_path.stem}_summary.csv")


def build_virtual_ecu(executable: Path) -> None:
    if executable.resolve() == DEFAULT_EXECUTABLE.resolve():
        run_checked(("make",), PROJECT_ROOT)
    if not executable.is_file():
        raise FileNotFoundError(
            f"Virtual ECU executable not found: {executable}"
        )


def generate_source_trace(
    executable: Path,
    output_dir: Path,
    duration_ms: int,
) -> List[Dict[str, str]]:
    raw_path = output_dir / "source_baseline.csv"
    run_checked(
        (
            str(executable),
            str(raw_path),
            "baseline",
            "--detector",
            "hybrid_adaptive_kalman",
            "--detector-action",
            "observe_only",
            "--simulation-duration-ms",
            str(duration_ms),
        ),
        PROJECT_ROOT,
    )
    return read_rows(raw_path)


def build_and_run_rtl(
    source_rows: Sequence[Dict[str, str]],
    output_trace: Path,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="virtual_ecu_rtl_trojan_"
    ) as temp_name:
        temp_dir = Path(temp_name)
        input_path = temp_dir / "rtl_input_trace.txt"
        harness_path = temp_dir / "rtl_trace_harness.cpp"
        obj_dir = temp_dir / "obj_dir"

        with input_path.open("w", encoding="utf-8") as handle:
            for row in source_rows:
                time_ms = int(float(row["time_ms"]))
                sensor_deci_c = round(
                    float(row["coolant_temp_true_c"]) * 10.0
                )
                handle.write(f"{time_ms} {sensor_deci_c}\n")
        harness_path.write_text(VERILATOR_HARNESS, encoding="utf-8")

        run_checked(
            (
                "verilator",
                "--cc",
                "--exe",
                "--build",
                "--Wall",
                "--top-module",
                "coolant_sensor_interface_tb",
                "--Mdir",
                str(obj_dir),
                "-o",
                "rtl_trojan_trace_sim",
                str(RTL_DIR / "coolant_sensor_interface_clean.v"),
                str(RTL_DIR / "coolant_sensor_interface_trojan.v"),
                str(RTL_WRAPPER),
                str(harness_path),
            ),
            PROJECT_ROOT,
        )
        run_checked(
            (
                str(obj_dir / "rtl_trojan_trace_sim"),
                str(input_path),
                str(output_trace),
            ),
            temp_dir,
        )


def write_replay_traces(
    rtl_rows: Sequence[Dict[str, str]],
    output_dir: Path,
) -> tuple[Path, Path, int, Dict[str, str]]:
    clean_path = output_dir / "virtual_ecu_clean_sensor_trace.csv"
    trojan_path = output_dir / "virtual_ecu_trojan_sensor_trace.csv"
    trigger_row = next(
        (row for row in rtl_rows if int(row["payload_active"]) != 0),
        None,
    )
    if trigger_row is None:
        raise RuntimeError(
            "The RTL input sequence did not activate the Trojan payload."
        )

    clean_rows = []
    trojan_rows = []
    for row in rtl_rows:
        time_ms = int(row["time_ms"])
        clean_c = int(row["clean_sensor_out_deci_c"]) / 10.0
        trojan_c = int(row["trojan_sensor_out_deci_c"]) / 10.0
        clean_rows.append(
            {"time_ms": time_ms, "coolant_temp_c": f"{clean_c:.1f}"}
        )
        trojan_rows.append(
            {"time_ms": time_ms, "coolant_temp_c": f"{trojan_c:.1f}"}
        )

    write_rows(clean_path, ("time_ms", "coolant_temp_c"), clean_rows)
    write_rows(trojan_path, ("time_ms", "coolant_temp_c"), trojan_rows)
    return clean_path, trojan_path, int(trigger_row["time_ms"]), trigger_row


def first_dtc_after(
    raw_rows: Sequence[Dict[str, str]],
    start_ms: int,
) -> tuple[str, int]:
    for row in raw_rows:
        time_ms = int(float(row["time_ms"]))
        if time_ms < start_ms:
            continue
        if int(float(row["primary_dtc_id"])) != 0:
            return row["primary_dtc_label"], time_ms
    return "none", -1


def run_detector_variant(
    executable: Path,
    raw_dir: Path,
    detector: str,
    variant: str,
    sensor_trace: Path,
    duration_ms: int,
    trigger_time_ms: int,
    trigger_row: Dict[str, str],
) -> Dict[str, object]:
    raw_path = raw_dir / f"{variant}__{detector}.csv"
    run_checked(
        (
            str(executable),
            str(raw_path),
            "baseline",
            "--detector",
            detector,
            "--detector-action",
            "observe_only",
            "--simulation-duration-ms",
            str(duration_ms),
            "--coolant-sensor-trace",
            str(sensor_trace),
        ),
        PROJECT_ROOT,
    )

    raw_rows = read_rows(raw_path)
    summary_rows = read_rows(summary_path(raw_path))
    summary = summary_rows[0]
    final_row = raw_rows[-1]
    first_detection_ms = int(
        float(summary["runtime_detection_first_detection_ms"])
    )
    detected = int(float(summary["runtime_detection_detected"]))
    attack_variant = variant == "trojan"
    detected_after_payload = int(
        attack_variant
        and detected != 0
        and first_detection_ms >= trigger_time_ms
    )
    dtc_label, dtc_time_ms = first_dtc_after(
        raw_rows,
        trigger_time_ms if attack_variant else 0,
    )

    return {
        "experiment_kind": "rtl_hardware_trojan",
        "variant": variant,
        "rtl_trojan_enabled": int(attack_variant),
        "rtl_trojan_type": (
            "coolant_temperature_masking" if attack_variant else "none"
        ),
        "rtl_trojan_target": "coolant_sensor_interface",
        "detector": detector,
        "runtime_detection_detected": detected,
        "detected_after_payload": detected_after_payload,
        "runtime_detection_first_detection_ms": first_detection_ms,
        "detection_latency_from_payload_ms": (
            first_detection_ms - trigger_time_ms
            if detected_after_payload
            else -1
        ),
        "runtime_reported_false_positive_count": int(
            float(final_row["runtime_detection_false_positive_count"])
        ),
        "runtime_detection_label": summary["runtime_detection_label"],
        "rtl_trojan_triggered": int(attack_variant),
        "rtl_trojan_payload_active": int(attack_variant),
        "rtl_trojan_trigger_time_ms": (
            trigger_time_ms if attack_variant else -1
        ),
        "rtl_clean_sensor_value_c": (
            int(trigger_row["clean_sensor_out_deci_c"]) / 10.0
        ),
        "rtl_trojan_sensor_value_c": (
            int(trigger_row["trojan_sensor_out_deci_c"]) / 10.0
            if attack_variant
            else int(trigger_row["clean_sensor_out_deci_c"]) / 10.0
        ),
        "first_ecu_dtc_label_after_payload": dtc_label,
        "first_ecu_dtc_time_ms": dtc_time_ms,
        "max_coolant_temp_c": summary["max_coolant_temp_c"],
        "final_safe_state": summary["final_safe_state_label"],
        "raw_csv": relative_path(raw_path),
        "summary_csv": relative_path(summary_path(raw_path)),
    }


def write_taxonomy(path: Path) -> None:
    write_rows(
        path,
        (
            "experiment_kind",
            "trojan_type",
            "insertion_level",
            "target",
            "trigger",
            "payload",
            "activation",
            "evaluation_scope",
        ),
        (
            {
                "experiment_kind": "rtl_hardware_trojan",
                "trojan_type": "coolant_temperature_masking",
                "insertion_level": "RTL sensor interface",
                "target": "ECU-facing coolant sensor sample",
                "trigger": "sensor >= 95.0 C for 8 consecutive cycles",
                "payload": "subtract 8.0 C from the reported sample",
                "activation": "sticky until reset",
                "evaluation_scope": (
                    "Verilator RTL simulation plus Virtual ECU trace replay"
                ),
            },
        ),
    )


def write_reports(
    output_dir: Path,
    results: Sequence[Dict[str, object]],
    trigger_time_ms: int,
) -> None:
    clean = [row for row in results if row["variant"] == "clean"]
    trojan = [row for row in results if row["variant"] == "trojan"]
    clean_alarms = sum(int(row["runtime_detection_detected"]) for row in clean)
    attack_detections = sum(int(row["detected_after_payload"]) for row in trojan)
    detected_names = [
        str(row["detector"])
        for row in trojan
        if int(row["detected_after_payload"]) != 0
    ]
    hybrid = next(
        row
        for row in trojan
        if row["detector"] == "hybrid_adaptive_kalman"
    )

    readme = f"""# RTL Hardware Trojan Study v1

This directory is generated by `scripts/run_rtl_hardware_trojan_study.py`.
It is intentionally ignored by git.

The study first runs a nominal Virtual ECU thermal trace, quantizes its coolant
sensor input to signed 16-bit deci-degrees Celsius, and simulates both actual
Verilog sensor-interface modules with Verilator. The clean and infected RTL
outputs are then replayed as the ECU-facing coolant sample in dedicated
baseline campaigns. Existing detectors run unchanged in `observe_only` mode.

- RTL payload activation: {trigger_time_ms} ms
- Clean detector alarms: {clean_alarms}/{len(clean)}
- Trojan detections after activation: {attack_detections}/{len(trojan)}
- Detectors observing the activation consequence: {", ".join(detected_names) if detected_names else "none"}
- Hybrid Adaptive Kalman detected after activation: {hybrid["detected_after_payload"]}
- Hybrid Adaptive Kalman latency from payload: {hybrid["detection_latency_from_payload_ms"]} ms

The raw clean and Trojan Virtual ECU CSV files can be loaded directly in the
existing GUI Compare view. This is trace-driven co-simulation: the RTL consumes
a prerecorded nominal coolant input, while each ECU replay retains its own
thermal plant for runtime monitoring. It is not a fabricated-chip result.

## Outputs

- `rtl_trojan_sensor_trace.csv`: direct clean-versus-infected RTL evidence.
- `virtual_ecu_clean_sensor_trace.csv`: clean RTL replay input.
- `virtual_ecu_trojan_sensor_trace.csv`: infected RTL replay input.
- `detector_comparison.csv`: unchanged detector outcomes for both variants.
- `attack_taxonomy_table.csv`: trigger, payload, target, and scope.
- `raw/`: GUI-compatible Virtual ECU traces and summaries.
- `trojan_claim_summary.md`: bounded claim and limitations.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    claim = f"""# RTL Hardware Trojan Claim Summary

## Supported claim

This experiment contains a real Verilog RTL Hardware Trojan model in the
coolant sensor interface. Its explicit trigger requires a reading of at least
95.0 C for eight consecutive interface cycles. Once triggered, its sticky
payload subtracts 8.0 C from the ECU-facing sample until reset.

Verilator activated the payload at {trigger_time_ms} ms. The unchanged Virtual
ECU detectors reported {attack_detections}/{len(trojan)} post-activation
detections; the clean replay produced {clean_alarms}/{len(clean)} detector
alarms. Hybrid Adaptive Kalman post-activation detection was
{hybrid["detected_after_payload"]}, with latency
{hybrid["detection_latency_from_payload_ms"]} ms.

## Boundaries

- This is an RTL-level trigger-payload model, not a relabeled C fault.
- It is a deterministic trace-driven Verilator/Virtual ECU experiment.
- It is not silicon-proven, fabricated-chip evidence, or a claim that all
  Hardware Trojans are detected.
- Detection results apply only to this configured input sequence, payload, and
  existing detector calibrations.
- The replayed RTL input is prerecorded, so this first version is not a fully
  bidirectional cycle-by-cycle plant/RTL co-simulation.
"""
    (output_dir / "trojan_claim_summary.md").write_text(
        claim,
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    if shutil.which("verilator") is None:
        print(
            "Verilator is required for the RTL Hardware Trojan study. "
            "Install with sudo apt install verilator."
        )
        return 2
    if args.simulation_duration_ms < 1000:
        raise ValueError("Simulation duration must be at least 1000 ms.")

    output_dir = args.output_dir.resolve()
    raw_dir = output_dir / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    build_virtual_ecu(args.executable)
    print("[1/4] Generating nominal coolant input trace")
    source_rows = generate_source_trace(
        args.executable.resolve(),
        output_dir,
        args.simulation_duration_ms,
    )

    rtl_trace = output_dir / "rtl_trojan_sensor_trace.csv"
    print("[2/4] Building and simulating clean and Trojan RTL with Verilator")
    build_and_run_rtl(source_rows, rtl_trace)
    rtl_rows = read_rows(rtl_trace)
    clean_trace, trojan_trace, trigger_time_ms, trigger_row = (
        write_replay_traces(rtl_rows, output_dir)
    )

    print("[3/4] Replaying RTL outputs through unchanged Virtual ECU detectors")
    results = []
    total = len(DETECTORS) * 2
    run_index = 0
    for variant, sensor_trace in (
        ("clean", clean_trace),
        ("trojan", trojan_trace),
    ):
        for detector in DETECTORS:
            run_index += 1
            print(f"  [{run_index:02d}/{total}] {variant} / {detector}")
            results.append(
                run_detector_variant(
                    args.executable.resolve(),
                    raw_dir,
                    detector,
                    variant,
                    sensor_trace,
                    args.simulation_duration_ms,
                    trigger_time_ms,
                    trigger_row,
                )
            )

    print("[4/4] Writing isolated security-study tables and reports")
    write_rows(
        output_dir / "detector_comparison.csv",
        COMPARISON_COLUMNS,
        results,
    )
    write_taxonomy(output_dir / "attack_taxonomy_table.csv")
    write_reports(output_dir, results, trigger_time_ms)
    print(f"RTL Hardware Trojan study complete: {output_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"RTL Hardware Trojan study failed: {error}", file=sys.stderr)
        raise SystemExit(1)
