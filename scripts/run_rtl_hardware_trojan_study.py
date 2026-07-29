#!/usr/bin/env python3
"""Run trace-driven RTL security analysis for Virtual ECU interfaces."""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT / "results" / "rtl_hardware_trojan_study_v1"
)
DEFAULT_EXECUTABLE = PROJECT_ROOT / "virtual_ecu"
RTL_DIR = PROJECT_ROOT / "rtl" / "security"
SIM_DIR = PROJECT_ROOT / "sim" / "security"

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
    "rtl_target_id",
    "rtl_target_name",
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
    "stage_1_calibration_trigger_time_ms",
    "stage_2_sensor_trigger_time_ms",
    "stage_3_fan_trigger_time_ms",
    "rtl_clean_sensor_value_c",
    "rtl_trojan_sensor_value_c",
    "rtl_clean_fan_actual",
    "rtl_trojan_fan_actual",
    "rtl_clean_calibration_value_c",
    "rtl_trojan_calibration_value_c",
    "first_ecu_dtc_label_after_payload",
    "first_ecu_dtc_time_ms",
    "max_coolant_temp_c",
    "final_safe_state",
    "raw_csv",
    "summary_csv",
)


@dataclass(frozen=True)
class TargetSpec:
    target_id: str
    display_name: str
    trojan_type: str
    target_path: str
    trace_option: str
    rtl_trace_name: str
    clean_replay_name: str
    trojan_replay_name: str
    is_composite: bool = False


TARGETS = {
    "coolant_sensor": TargetSpec(
        target_id="ht1_coolant_sensor",
        display_name="Coolant Sensor Interface",
        trojan_type="coolant_temperature_masking",
        target_path="coolant_sensor_interface",
        trace_option="--coolant-sensor-trace",
        rtl_trace_name="rtl_trojan_sensor_trace.csv",
        clean_replay_name="virtual_ecu_clean_sensor_trace.csv",
        trojan_replay_name="virtual_ecu_trojan_sensor_trace.csv",
    ),
    "fan_driver": TargetSpec(
        target_id="ht2_fan_driver",
        display_name="Fan Driver Interface",
        trojan_type="fan_driver_forced_off",
        target_path="fan_driver_interface",
        trace_option="--fan-actual-trace",
        rtl_trace_name="rtl_fan_driver_trojan_trace.csv",
        clean_replay_name="virtual_ecu_clean_fan_actual_trace.csv",
        trojan_replay_name="virtual_ecu_trojan_fan_actual_trace.csv",
    ),
    "calibration_memory": TargetSpec(
        target_id="ht3_calibration_memory",
        display_name="Calibration Memory Interface",
        trojan_type="cooling_target_calibration_shift",
        target_path="calibration_memory_interface",
        trace_option="--calibration-trace",
        rtl_trace_name="rtl_calibration_memory_trojan_trace.csv",
        clean_replay_name="virtual_ecu_clean_calibration_trace.csv",
        trojan_replay_name="virtual_ecu_trojan_calibration_trace.csv",
    ),
    "multi_stage_chain": TargetSpec(
        target_id="ht4_multi_stage_chain",
        display_name="Multi-Stage RTL Chain",
        trojan_type="coordinated_multi_path_chain",
        target_path="calibration_sensor_actuator_composition",
        trace_option="",
        rtl_trace_name="",
        clean_replay_name="",
        trojan_replay_name="",
        is_composite=True,
    ),
}

CHAIN_STAGE_KEYS = (
    "calibration_memory",
    "coolant_sensor",
    "fan_driver",
)

COOLANT_VERILATOR_HARNESS = r"""
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
        std::cerr << "usage: coolant_rtl_security_sim INPUT OUTPUT\n";
        return 2;
    }

    std::ifstream input(argv[1]);
    std::ofstream output(argv[2]);
    if (!input || !output) {
        std::cerr << "unable to open coolant RTL trace input or output\n";
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

FAN_VERILATOR_HARNESS = r"""
#include <cstdint>
#include <fstream>
#include <iostream>

#include "Vfan_driver_interface_tb.h"
#include "verilated.h"

static void clock_cycle(Vfan_driver_interface_tb &top)
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
        std::cerr << "usage: fan_rtl_security_sim INPUT OUTPUT\n";
        return 2;
    }

    std::ifstream input(argv[1]);
    std::ofstream output(argv[2]);
    if (!input || !output) {
        std::cerr << "unable to open fan RTL trace input or output\n";
        return 2;
    }

    Vfan_driver_interface_tb top;
    top.reset_n = 0;
    top.fan_command = 0;
    clock_cycle(top);
    clock_cycle(top);
    top.reset_n = 1;

    output
        << "time_ms,fan_command_milli,clean_fan_actual_milli,"
        << "trojan_fan_actual_milli,trojan_triggered,payload_active,"
        << "trigger_counter,rtl_clean_fan_command_milli,"
        << "rtl_trojan_fan_actual_milli\n";

    unsigned int time_ms = 0;
    unsigned int fan_command = 0;
    while (input >> time_ms >> fan_command) {
        top.fan_command = fan_command;
        clock_cycle(top);
        output
            << time_ms << ","
            << fan_command << ","
            << top.clean_fan_actual << ","
            << top.trojan_fan_actual << ","
            << static_cast<int>(top.trojan_triggered) << ","
            << static_cast<int>(top.payload_active) << ","
            << top.trigger_counter << ","
            << top.trojan_clean_fan_command << ","
            << top.trojan_debug_fan_actual << "\n";
    }

    top.final();
    return 0;
}
"""

CALIBRATION_VERILATOR_HARNESS = r"""
#include <cstdint>
#include <fstream>
#include <iostream>

#include "Vcalibration_memory_interface_tb.h"
#include "verilated.h"

static int signed_value(std::uint16_t value)
{
    return static_cast<std::int16_t>(value);
}

static void clock_cycle(Vcalibration_memory_interface_tb &top)
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
        std::cerr << "usage: calibration_rtl_security_sim INPUT OUTPUT\n";
        return 2;
    }

    std::ifstream input(argv[1]);
    std::ofstream output(argv[2]);
    if (!input || !output) {
        std::cerr << "unable to open calibration RTL trace input or output\n";
        return 2;
    }

    Vcalibration_memory_interface_tb top;
    top.reset_n = 0;
    top.calibration_in = 0;
    clock_cycle(top);
    clock_cycle(top);
    top.reset_n = 1;

    output
        << "time_ms,calibration_in_deci_c,clean_calibration_out_deci_c,"
        << "trojan_calibration_out_deci_c,trojan_triggered,payload_active,"
        << "trigger_counter,clean_calibration_value_deci_c,"
        << "trojan_calibration_value_deci_c\n";

    unsigned int time_ms = 0;
    int calibration_value = 0;
    while (input >> time_ms >> calibration_value) {
        top.calibration_in = static_cast<std::uint16_t>(calibration_value);
        clock_cycle(top);
        output
            << time_ms << ","
            << calibration_value << ","
            << signed_value(top.clean_calibration_out) << ","
            << signed_value(top.trojan_calibration_out) << ","
            << static_cast<int>(top.trojan_triggered) << ","
            << static_cast<int>(top.payload_active) << ","
            << top.trigger_counter << ","
            << signed_value(top.trojan_clean_calibration_value) << ","
            << signed_value(top.trojan_debug_calibration_value) << "\n";
    }

    top.final();
    return 0;
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build and simulate clean and Trojan-infected RTL interfaces, "
            "then replay their outputs through unchanged Virtual ECU detectors."
        )
    )
    parser.add_argument(
        "--target",
        choices=("all", *TARGETS.keys()),
        default="all",
        help="RTL security target to analyze. The default runs all targets.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for RTL security traces and reports.",
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
        help="Duration of source and trace-replay runs.",
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


def build_verilator_model(
    top_module: str,
    sources: Sequence[Path],
    harness_text: str,
    executable_name: str,
    input_rows: Sequence[tuple[int, int]],
    output_trace: Path,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix=f"virtual_ecu_{top_module}_"
    ) as temp_name:
        temp_dir = Path(temp_name)
        input_path = temp_dir / "rtl_input_trace.txt"
        harness_path = temp_dir / "rtl_security_harness.cpp"
        obj_dir = temp_dir / "obj_dir"

        with input_path.open("w", encoding="utf-8") as handle:
            for time_ms, value in input_rows:
                handle.write(f"{time_ms} {value}\n")
        harness_path.write_text(harness_text, encoding="utf-8")

        run_checked(
            (
                "verilator",
                "--cc",
                "--exe",
                "--build",
                "--Wall",
                "--top-module",
                top_module,
                "--Mdir",
                str(obj_dir),
                "-o",
                executable_name,
                *(str(path) for path in sources),
                str(harness_path),
            ),
            PROJECT_ROOT,
        )
        run_checked(
            (
                str(obj_dir / executable_name),
                str(input_path),
                str(output_trace),
            ),
            temp_dir,
        )


def run_coolant_rtl(
    source_rows: Sequence[Dict[str, str]],
    output_trace: Path,
) -> None:
    input_rows = [
        (
            int(float(row["time_ms"])),
            round(float(row["coolant_temp_true_c"]) * 10.0),
        )
        for row in source_rows
    ]
    build_verilator_model(
        "coolant_sensor_interface_tb",
        (
            RTL_DIR / "coolant_sensor_interface_clean.v",
            RTL_DIR / "coolant_sensor_interface_trojan.v",
            SIM_DIR / "coolant_sensor_interface_tb.v",
        ),
        COOLANT_VERILATOR_HARNESS,
        "coolant_rtl_security_sim",
        input_rows,
        output_trace,
    )


def run_fan_rtl(
    source_rows: Sequence[Dict[str, str]],
    output_trace: Path,
) -> None:
    input_rows = [
        (
            int(float(row["time_ms"])),
            round(float(row["fan_command"]) * 1000.0),
        )
        for row in source_rows
    ]
    build_verilator_model(
        "fan_driver_interface_tb",
        (
            RTL_DIR / "fan_driver_interface_clean.v",
            RTL_DIR / "fan_driver_interface_trojan.v",
            SIM_DIR / "fan_driver_interface_tb.v",
        ),
        FAN_VERILATOR_HARNESS,
        "fan_rtl_security_sim",
        input_rows,
        output_trace,
    )


def run_calibration_rtl(
    source_rows: Sequence[Dict[str, str]],
    output_trace: Path,
) -> None:
    input_rows = [
        (
            int(float(row["time_ms"])),
            920,
        )
        for row in source_rows
    ]
    build_verilator_model(
        "calibration_memory_interface_tb",
        (
            RTL_DIR / "calibration_memory_interface_clean.v",
            RTL_DIR / "calibration_memory_interface_trojan.v",
            SIM_DIR / "calibration_memory_interface_tb.v",
        ),
        CALIBRATION_VERILATOR_HARNESS,
        "calibration_rtl_security_sim",
        input_rows,
        output_trace,
    )


def payload_trigger_row(
    rtl_rows: Sequence[Dict[str, str]],
    target: TargetSpec,
) -> Dict[str, str]:
    row = next(
        (item for item in rtl_rows if int(item["payload_active"]) != 0),
        None,
    )
    if row is None:
        raise RuntimeError(
            f"The input sequence did not activate {target.display_name}."
        )
    return row


def write_coolant_replay_traces(
    rtl_rows: Sequence[Dict[str, str]],
    output_dir: Path,
    target: TargetSpec,
) -> tuple[Path, Path, Dict[str, str]]:
    clean_path = output_dir / target.clean_replay_name
    trojan_path = output_dir / target.trojan_replay_name
    trigger_row = payload_trigger_row(rtl_rows, target)
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
    return clean_path, trojan_path, trigger_row


def write_fan_replay_traces(
    rtl_rows: Sequence[Dict[str, str]],
    output_dir: Path,
    target: TargetSpec,
) -> tuple[Path, Path, Dict[str, str]]:
    clean_path = output_dir / target.clean_replay_name
    trojan_path = output_dir / target.trojan_replay_name
    trigger_row = payload_trigger_row(rtl_rows, target)
    clean_rows = []
    trojan_rows = []

    for row in rtl_rows:
        time_ms = int(row["time_ms"])
        clean_actual = int(row["clean_fan_actual_milli"]) / 1000.0
        trojan_actual = int(row["trojan_fan_actual_milli"]) / 1000.0
        clean_rows.append(
            {"time_ms": time_ms, "fan_actual": f"{clean_actual:.3f}"}
        )
        trojan_rows.append(
            {"time_ms": time_ms, "fan_actual": f"{trojan_actual:.3f}"}
        )

    write_rows(clean_path, ("time_ms", "fan_actual"), clean_rows)
    write_rows(trojan_path, ("time_ms", "fan_actual"), trojan_rows)
    return clean_path, trojan_path, trigger_row


def write_calibration_replay_traces(
    rtl_rows: Sequence[Dict[str, str]],
    output_dir: Path,
    target: TargetSpec,
) -> tuple[Path, Path, Dict[str, str]]:
    clean_path = output_dir / target.clean_replay_name
    trojan_path = output_dir / target.trojan_replay_name
    trigger_row = payload_trigger_row(rtl_rows, target)
    clean_rows = []
    trojan_rows = []

    for row in rtl_rows:
        time_ms = int(row["time_ms"])
        clean_c = int(row["clean_calibration_out_deci_c"]) / 10.0
        trojan_c = int(row["trojan_calibration_out_deci_c"]) / 10.0
        clean_rows.append(
            {"time_ms": time_ms, "control_target_c": f"{clean_c:.1f}"}
        )
        trojan_rows.append(
            {"time_ms": time_ms, "control_target_c": f"{trojan_c:.1f}"}
        )

    write_rows(clean_path, ("time_ms", "control_target_c"), clean_rows)
    write_rows(trojan_path, ("time_ms", "control_target_c"), trojan_rows)
    return clean_path, trojan_path, trigger_row


def prepare_individual_target(
    source_rows: Sequence[Dict[str, str]],
    output_dir: Path,
    target: TargetSpec,
) -> tuple[Path, Path, Dict[str, str]]:
    if target.is_composite:
        raise ValueError("Composite targets do not have an independent RTL model.")

    rtl_trace = output_dir / target.rtl_trace_name
    if target.target_id == "ht1_coolant_sensor":
        run_coolant_rtl(source_rows, rtl_trace)
        return write_coolant_replay_traces(
            read_rows(rtl_trace),
            output_dir,
            target,
        )
    if target.target_id == "ht2_fan_driver":
        run_fan_rtl(source_rows, rtl_trace)
        return write_fan_replay_traces(
            read_rows(rtl_trace),
            output_dir,
            target,
        )

    run_calibration_rtl(source_rows, rtl_trace)
    return write_calibration_replay_traces(
        read_rows(rtl_trace),
        output_dir,
        target,
    )


def write_multi_stage_trace_index(
    output_dir: Path,
    prepared: Dict[str, tuple[Path, Path, Dict[str, str]]],
) -> None:
    stage_labels = (
        "stage_1_calibration",
        "stage_2_sensor",
        "stage_3_actuator",
    )
    rows = []

    for stage_label, target_key in zip(stage_labels, CHAIN_STAGE_KEYS):
        target = TARGETS[target_key]
        clean_trace, trojan_trace, trigger_row = prepared[target_key]
        rows.append(
            {
                "stage": stage_label,
                "rtl_target_id": target.target_id,
                "rtl_target_name": target.display_name,
                "rtl_trigger_time_ms": trigger_row["time_ms"],
                "direct_rtl_trace": relative_path(
                    output_dir / target.rtl_trace_name
                ),
                "clean_replay_trace": relative_path(clean_trace),
                "trojan_replay_trace": relative_path(trojan_trace),
            }
        )

    write_rows(
        output_dir / "multi_stage_chain_trace_index.csv",
        (
            "stage",
            "rtl_target_id",
            "rtl_target_name",
            "rtl_trigger_time_ms",
            "direct_rtl_trace",
            "clean_replay_trace",
            "trojan_replay_trace",
        ),
        rows,
    )


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


def interface_values(
    target: TargetSpec,
    trigger_row: Dict[str, str],
) -> tuple[float, float]:
    if target.target_id == "ht1_coolant_sensor":
        return (
            int(trigger_row["clean_sensor_out_deci_c"]) / 10.0,
            int(trigger_row["trojan_sensor_out_deci_c"]) / 10.0,
        )
    if target.target_id == "ht2_fan_driver":
        return (
            int(trigger_row["clean_fan_actual_milli"]) / 1000.0,
            int(trigger_row["trojan_fan_actual_milli"]) / 1000.0,
        )
    if target.target_id == "ht3_calibration_memory":
        return (
            int(trigger_row["clean_calibration_out_deci_c"]) / 10.0,
            int(trigger_row["trojan_calibration_out_deci_c"]) / 10.0,
        )
    return 0.0, 0.0


def run_detector_variant(
    executable: Path,
    raw_dir: Path,
    detector: str,
    variant: str,
    target: TargetSpec,
    replay_inputs: Sequence[tuple[str, Path]],
    duration_ms: int,
    trigger_row: Dict[str, str],
    stage_trigger_times: tuple[int, int, int],
) -> Dict[str, object]:
    raw_path = (
        raw_dir / f"{target.target_id}__{variant}__{detector}.csv"
    )
    trace_arguments = tuple(
        argument
        for option, path in replay_inputs
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
            "observe_only",
            "--simulation-duration-ms",
            str(duration_ms),
            *trace_arguments,
        ),
        PROJECT_ROOT,
    )

    raw_rows = read_rows(raw_path)
    summary = read_rows(summary_path(raw_path))[0]
    final_row = raw_rows[-1]
    trigger_time_ms = int(trigger_row["time_ms"])
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
    clean_value, trojan_value = interface_values(target, trigger_row)

    return {
        "experiment_kind": (
            "rtl_multi_stage_chain"
            if target.is_composite
            else "rtl_hardware_trojan"
        ),
        "rtl_target_id": target.target_id,
        "rtl_target_name": target.display_name,
        "variant": variant,
        "rtl_trojan_enabled": int(attack_variant),
        "rtl_trojan_type": target.trojan_type if attack_variant else "none",
        "rtl_trojan_target": target.target_path,
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
        "stage_1_calibration_trigger_time_ms": (
            stage_trigger_times[0]
            if attack_variant and target.is_composite
            else ""
        ),
        "stage_2_sensor_trigger_time_ms": (
            stage_trigger_times[1]
            if attack_variant and target.is_composite
            else ""
        ),
        "stage_3_fan_trigger_time_ms": (
            stage_trigger_times[2]
            if attack_variant and target.is_composite
            else ""
        ),
        "rtl_clean_sensor_value_c": (
            clean_value if target.target_id == "ht1_coolant_sensor" else ""
        ),
        "rtl_trojan_sensor_value_c": (
            trojan_value
            if attack_variant and target.target_id == "ht1_coolant_sensor"
            else clean_value
            if target.target_id == "ht1_coolant_sensor"
            else ""
        ),
        "rtl_clean_fan_actual": (
            clean_value if target.target_id == "ht2_fan_driver" else ""
        ),
        "rtl_trojan_fan_actual": (
            trojan_value
            if attack_variant and target.target_id == "ht2_fan_driver"
            else clean_value
            if target.target_id == "ht2_fan_driver"
            else ""
        ),
        "rtl_clean_calibration_value_c": (
            clean_value if target.target_id == "ht3_calibration_memory" else ""
        ),
        "rtl_trojan_calibration_value_c": (
            trojan_value
            if attack_variant and target.target_id == "ht3_calibration_memory"
            else clean_value
            if target.target_id == "ht3_calibration_memory"
            else ""
        ),
        "first_ecu_dtc_label_after_payload": dtc_label,
        "first_ecu_dtc_time_ms": dtc_time_ms,
        "max_coolant_temp_c": summary["max_coolant_temp_c"],
        "final_safe_state": summary["final_safe_state_label"],
        "raw_csv": relative_path(raw_path),
        "summary_csv": relative_path(summary_path(raw_path)),
    }


def write_taxonomy(path: Path, targets: Sequence[TargetSpec]) -> None:
    rows = []
    for target in targets:
        if target.target_id == "ht1_coolant_sensor":
            rows.append(
                {
                    "experiment_kind": "rtl_hardware_trojan",
                    "rtl_target_id": target.target_id,
                    "trojan_type": target.trojan_type,
                    "insertion_level": "RTL sensor interface",
                    "target": "ECU-facing coolant sensor sample",
                    "trigger": "sensor >= 95.0 C for 8 consecutive cycles",
                    "payload": "subtract 8.0 C from the reported sample",
                    "activation": "sticky until reset",
                    "evaluation_scope": (
                        "Verilator RTL simulation plus Virtual ECU trace replay"
                    ),
                }
            )
        elif target.target_id == "ht2_fan_driver":
            rows.append(
                {
                    "experiment_kind": "rtl_hardware_trojan",
                    "rtl_target_id": target.target_id,
                    "trojan_type": target.trojan_type,
                    "insertion_level": "RTL actuator interface",
                    "target": "Fan driver realized-output interface",
                    "trigger": (
                        "fan command >= 0.500 for 8 consecutive cycles"
                    ),
                    "payload": "force realized fan output to 0.000",
                    "activation": "sticky until reset",
                    "evaluation_scope": (
                        "Verilator RTL simulation plus Virtual ECU trace replay"
                    ),
                }
            )
        elif target.target_id == "ht3_calibration_memory":
            rows.append(
                {
                    "experiment_kind": "rtl_hardware_trojan",
                    "rtl_target_id": target.target_id,
                    "trojan_type": target.trojan_type,
                    "insertion_level": "RTL calibration-memory interface",
                    "target": "Coolant-control target calibration value",
                    "trigger": "internal counter reaches 521 interface cycles",
                    "payload": "add 16.0 C to the cooling control target",
                    "activation": "sticky until reset",
                    "evaluation_scope": (
                        "Verilator RTL simulation plus Virtual ECU trace replay"
                    ),
                }
            )
        else:
            rows.append(
                {
                    "experiment_kind": "rtl_multi_stage_chain",
                    "rtl_target_id": target.target_id,
                    "trojan_type": target.trojan_type,
                    "insertion_level": "Composite existing RTL interfaces",
                    "target": (
                        "Calibration, coolant-sensor, and fan-driver paths"
                    ),
                    "trigger": (
                        "HT3 counter, then HT1 temperature persistence, "
                        "then HT2 fan-command persistence"
                    ),
                    "payload": (
                        "raise control target, mask coolant sample, and "
                        "suppress realized fan output"
                    ),
                    "activation": "each existing stage sticky until reset",
                    "evaluation_scope": (
                        "Trace-driven composition of three Verilator RTL "
                        "outputs plus Virtual ECU replay"
                    ),
                }
            )

    write_rows(
        path,
        (
            "experiment_kind",
            "rtl_target_id",
            "trojan_type",
            "insertion_level",
            "target",
            "trigger",
            "payload",
            "activation",
            "evaluation_scope",
        ),
        rows,
    )


def target_metrics(
    results: Sequence[Dict[str, object]],
    target: TargetSpec,
) -> Dict[str, object]:
    selected = [
        row for row in results if row["rtl_target_id"] == target.target_id
    ]
    clean = [row for row in selected if row["variant"] == "clean"]
    trojan = [row for row in selected if row["variant"] == "trojan"]
    hybrid = next(
        row
        for row in trojan
        if row["detector"] == "hybrid_adaptive_kalman"
    )
    trigger_time_ms = int(trojan[0]["rtl_trojan_trigger_time_ms"])
    return {
        "clean_alarms": sum(
            int(row["runtime_detection_detected"]) for row in clean
        ),
        "attack_detections": sum(
            int(row["detected_after_payload"]) for row in trojan
        ),
        "detected_names": [
            str(row["detector"])
            for row in trojan
            if int(row["detected_after_payload"]) != 0
        ],
        "hybrid": hybrid,
        "trigger_time_ms": trigger_time_ms,
        "clean_count": len(clean),
        "trojan_count": len(trojan),
        "clean_max_coolant_c": float(clean[0]["max_coolant_temp_c"]),
        "trojan_max_coolant_c": float(trojan[0]["max_coolant_temp_c"]),
    }


def write_multi_stage_summary(
    output_dir: Path,
    results: Sequence[Dict[str, object]],
) -> None:
    target = TARGETS["multi_stage_chain"]
    metrics = target_metrics(results, target)
    hybrid = metrics["hybrid"]

    write_rows(
        output_dir / "multi_stage_chain_summary.csv",
        (
            "experiment_kind",
            "rtl_target_id",
            "stage_1_calibration_trigger_time_ms",
            "stage_2_sensor_trigger_time_ms",
            "stage_3_fan_trigger_time_ms",
            "detector_count",
            "clean_detector_alarms",
            "trojan_detections_after_stage_1",
            "detected_detectors",
            "hybrid_detection_latency_from_stage_1_ms",
            "clean_max_coolant_temp_c",
            "trojan_max_coolant_temp_c",
        ),
        (
            {
                "experiment_kind": "rtl_multi_stage_chain",
                "rtl_target_id": target.target_id,
                "stage_1_calibration_trigger_time_ms": (
                    hybrid["stage_1_calibration_trigger_time_ms"]
                ),
                "stage_2_sensor_trigger_time_ms": (
                    hybrid["stage_2_sensor_trigger_time_ms"]
                ),
                "stage_3_fan_trigger_time_ms": (
                    hybrid["stage_3_fan_trigger_time_ms"]
                ),
                "detector_count": metrics["trojan_count"],
                "clean_detector_alarms": metrics["clean_alarms"],
                "trojan_detections_after_stage_1": metrics[
                    "attack_detections"
                ],
                "detected_detectors": ";".join(metrics["detected_names"]),
                "hybrid_detection_latency_from_stage_1_ms": hybrid[
                    "detection_latency_from_payload_ms"
                ],
                "clean_max_coolant_temp_c": (
                    f"{metrics['clean_max_coolant_c']:.2f}"
                ),
                "trojan_max_coolant_temp_c": (
                    f"{metrics['trojan_max_coolant_c']:.2f}"
                ),
            },
        ),
    )


def write_reports(
    output_dir: Path,
    results: Sequence[Dict[str, object]],
    targets: Sequence[TargetSpec],
) -> None:
    sections = []
    claim_sections = []
    output_lines = []

    for target in targets:
        metrics = target_metrics(results, target)
        hybrid = metrics["hybrid"]
        detected_names = metrics["detected_names"]
        stage_lines = []
        if target.is_composite:
            stage_lines = [
                (
                    "- Stage 1 HT3 actual RTL activation: "
                    f"{hybrid['stage_1_calibration_trigger_time_ms']} ms"
                ),
                (
                    "- Stage 2 HT1 actual RTL activation: "
                    f"{hybrid['stage_2_sensor_trigger_time_ms']} ms"
                ),
                (
                    "- Stage 3 HT2 actual RTL activation: "
                    f"{hybrid['stage_3_fan_trigger_time_ms']} ms"
                ),
            ]
        sections.extend(
            [
                f"## {target.target_id.upper()}: {target.display_name}",
                "",
                f"- RTL payload activation: {metrics['trigger_time_ms']} ms",
                *stage_lines,
                (
                    f"- Clean detector alarms: {metrics['clean_alarms']}/"
                    f"{metrics['clean_count']}"
                ),
                (
                    f"- Trojan detections after activation: "
                    f"{metrics['attack_detections']}/{metrics['trojan_count']}"
                ),
                (
                    "- Detectors observing the activation consequence: "
                    + (", ".join(detected_names) if detected_names else "none")
                ),
                (
                    "- Hybrid Adaptive Kalman latency from payload: "
                    f"{hybrid['detection_latency_from_payload_ms']} ms"
                ),
                (
                    "- Maximum coolant, clean versus Trojan replay: "
                    f"{metrics['clean_max_coolant_c']:.2f} C versus "
                    f"{metrics['trojan_max_coolant_c']:.2f} C"
                ),
                "",
            ]
        )

        if target.target_id == "ht1_coolant_sensor":
            behavior = (
                "requires a coolant reading of at least 95.0 C for eight "
                "consecutive cycles, then subtracts 8.0 C from the "
                "ECU-facing sample"
            )
            output_lines.extend(
                [
                    "- `rtl_trojan_sensor_trace.csv`: HT1 direct RTL trace.",
                    "- `virtual_ecu_clean_sensor_trace.csv` and "
                    "`virtual_ecu_trojan_sensor_trace.csv`: HT1 replay inputs.",
                ]
            )
        elif target.target_id == "ht2_fan_driver":
            behavior = (
                "requires a fan command of at least 0.500 for eight "
                "consecutive cycles, then forces the realized fan output "
                "to zero"
            )
            output_lines.extend(
                [
                    "- `rtl_fan_driver_trojan_trace.csv`: HT2 direct RTL trace.",
                    "- `virtual_ecu_clean_fan_actual_trace.csv` and "
                    "`virtual_ecu_trojan_fan_actual_trace.csv`: HT2 replay "
                    "inputs.",
                ]
            )
        elif target.target_id == "ht3_calibration_memory":
            behavior = (
                "counts 521 calibration-interface cycles, then adds 16.0 C "
                "to the ECU cooling control target"
            )
            output_lines.extend(
                [
                    "- `rtl_calibration_memory_trojan_trace.csv`: HT3 direct "
                    "RTL trace.",
                    "- `virtual_ecu_clean_calibration_trace.csv` and "
                    "`virtual_ecu_trojan_calibration_trace.csv`: HT3 replay "
                    "inputs.",
                ]
            )
        else:
            behavior = (
                "composes the existing HT3 calibration shift, HT1 coolant "
                "masking, and HT2 fan suppression outputs into one staged "
                "replay without adding another RTL implant"
            )
            output_lines.extend(
                [
                    "- `multi_stage_chain_trace_index.csv`: actual RTL trace "
                    "and trigger source for each stage.",
                    "- `multi_stage_chain_summary.csv`: bounded composite "
                    "detector outcomes.",
                ]
            )

        claim_lead = (
            f"The composite scenario {behavior}."
            if target.is_composite
            else f"The explicit RTL trigger-payload implementation {behavior}."
        )
        claim_stage_lines = []
        if target.is_composite:
            claim_stage_lines = [
                (
                    "The actual RTL stage activations were "
                    f"{hybrid['stage_1_calibration_trigger_time_ms']} ms, "
                    f"{hybrid['stage_2_sensor_trigger_time_ms']} ms, and "
                    f"{hybrid['stage_3_fan_trigger_time_ms']} ms."
                )
            ]
        claim_sections.extend(
            [
                f"## {target.target_id.upper()}: {target.display_name}",
                "",
                claim_lead,
                *claim_stage_lines,
                (
                    f"Verilator activated the payload at "
                    f"{metrics['trigger_time_ms']} ms. The unchanged Virtual "
                    f"ECU detectors reported {metrics['attack_detections']}/"
                    f"{metrics['trojan_count']} post-activation detections; "
                    f"the clean replay produced {metrics['clean_alarms']}/"
                    f"{metrics['clean_count']} detector alarms."
                ),
                (
                    "Hybrid Adaptive Kalman latency from the payload was "
                    f"{hybrid['detection_latency_from_payload_ms']} ms."
                ),
                "",
            ]
        )

    readme_lines = [
        "# RTL Security Analysis",
        "",
        "This directory is generated by "
        "`scripts/run_rtl_hardware_trojan_study.py` and is ignored by git.",
        "",
        "The analysis simulates actual clean and Trojan-infected Verilog "
        "sensor, actuator, and calibration interface modules with Verilator, "
        "then replays individual or composed outputs through the "
        "unchanged Virtual ECU detectors in `observe_only` "
        "mode.",
        "",
        *sections,
        "## Outputs",
        "",
        *output_lines,
        "- `detector_comparison.csv`: unchanged detector outcomes.",
        "- `attack_taxonomy_table.csv`: targets, triggers, and payloads.",
        "- `raw/`: GUI-compatible Virtual ECU traces and summaries.",
        "- `trojan_claim_summary.md`: bounded claims and limitations.",
        "",
        "The raw clean and Trojan Virtual ECU CSV files can be loaded in the "
        "existing Compare view. This remains deterministic trace-driven "
        "RTL/ECU replay, not fabricated-chip evidence.",
        "",
    ]
    (output_dir / "README.md").write_text(
        "\n".join(readme_lines),
        encoding="utf-8",
    )

    claim_lines = [
        "# RTL Hardware Trojan Claim Summary",
        "",
        "## Supported claims",
        "",
        "These experiments contain real Verilog RTL Hardware Trojan models "
        "with explicit trigger and payload logic. They are not renamed C-level "
        "fault campaigns.",
        "",
        *claim_sections,
        "## Boundaries",
        "",
        "- These are deterministic trace-driven Verilator/Virtual ECU "
        "experiments.",
        "- Trigger and payload debug outputs are used only for reporting and "
        "latency calculation, never as detector inputs.",
        "- Results apply only to the configured traces, payloads, and detector "
        "calibrations.",
        "- The replay is not fully bidirectional cycle-by-cycle RTL/plant "
        "co-simulation.",
        "- This is not silicon-proven, fabricated-chip evidence, or a claim "
        "that all Hardware Trojans are detected.",
        "",
    ]
    (output_dir / "trojan_claim_summary.md").write_text(
        "\n".join(claim_lines),
        encoding="utf-8",
    )


def selected_targets(choice: str) -> List[TargetSpec]:
    if choice == "all":
        return list(TARGETS.values())
    return [TARGETS[choice]]


def main() -> int:
    args = parse_args()
    if shutil.which("verilator") is None:
        print(
            "Verilator is required for the RTL security analysis. "
            "Install with sudo apt install verilator."
        )
        return 2
    if args.simulation_duration_ms < 1000:
        raise ValueError("Simulation duration must be at least 1000 ms.")

    targets = selected_targets(args.target)
    output_dir = args.output_dir.resolve()
    raw_dir = output_dir / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    build_virtual_ecu(args.executable)
    print(
        "[1/4] Generating nominal coolant, fan-command, and calibration "
        "input trace"
    )
    source_rows = generate_source_trace(
        args.executable.resolve(),
        output_dir,
        args.simulation_duration_ms,
    )

    target_runs = []
    prepared: Dict[str, tuple[Path, Path, Dict[str, str]]] = {}
    print("[2/4] Building and simulating selected RTL targets with Verilator")
    for target in targets:
        print(f"  - {target.display_name}")
        if target.is_composite:
            for target_key in CHAIN_STAGE_KEYS:
                if target_key not in prepared:
                    component = TARGETS[target_key]
                    print(f"    * preparing {component.display_name}")
                    prepared[target_key] = prepare_individual_target(
                        source_rows,
                        output_dir,
                        component,
                    )

            clean_inputs = tuple(
                (
                    TARGETS[target_key].trace_option,
                    prepared[target_key][0],
                )
                for target_key in CHAIN_STAGE_KEYS
            )
            trojan_inputs = tuple(
                (
                    TARGETS[target_key].trace_option,
                    prepared[target_key][1],
                )
                for target_key in CHAIN_STAGE_KEYS
            )
            trigger_rows = tuple(
                prepared[target_key][2]
                for target_key in CHAIN_STAGE_KEYS
            )
            stage_trigger_times = tuple(
                int(trigger_row["time_ms"])
                for trigger_row in trigger_rows
            )
            write_multi_stage_trace_index(output_dir, prepared)
            target_runs.append(
                (
                    target,
                    clean_inputs,
                    trojan_inputs,
                    trigger_rows[0],
                    stage_trigger_times,
                )
            )
        else:
            target_key = next(
                key
                for key, value in TARGETS.items()
                if value.target_id == target.target_id
            )
            if target_key not in prepared:
                prepared[target_key] = prepare_individual_target(
                    source_rows,
                    output_dir,
                    target,
                )
            clean_trace, trojan_trace, trigger_row = prepared[target_key]
            target_runs.append(
                (
                    target,
                    ((target.trace_option, clean_trace),),
                    ((target.trace_option, trojan_trace),),
                    trigger_row,
                    (-1, -1, -1),
                )
            )

    print("[3/4] Replaying RTL outputs through unchanged Virtual ECU detectors")
    results = []
    total = len(target_runs) * len(DETECTORS) * 2
    run_index = 0
    for (
        target,
        clean_inputs,
        trojan_inputs,
        trigger_row,
        stage_trigger_times,
    ) in target_runs:
        for variant, replay_inputs in (
            ("clean", clean_inputs),
            ("trojan", trojan_inputs),
        ):
            for detector in DETECTORS:
                run_index += 1
                print(
                    f"  [{run_index:02d}/{total}] "
                    f"{target.target_id} / {variant} / {detector}"
                )
                results.append(
                    run_detector_variant(
                        args.executable.resolve(),
                        raw_dir,
                        detector,
                        variant,
                        target,
                        replay_inputs,
                        args.simulation_duration_ms,
                        trigger_row,
                        stage_trigger_times,
                    )
                )

    print("[4/4] Writing isolated RTL security tables and reports")
    write_rows(
        output_dir / "detector_comparison.csv",
        COMPARISON_COLUMNS,
        results,
    )
    write_taxonomy(output_dir / "attack_taxonomy_table.csv", targets)
    if any(target.is_composite for target in targets):
        write_multi_stage_summary(output_dir, results)
    write_reports(output_dir, results, targets)
    print(f"RTL security analysis complete: {output_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"RTL security analysis failed: {error}", file=sys.stderr)
        raise SystemExit(1)
