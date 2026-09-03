#!/usr/bin/env python3
"""Run the reproducible Virtual ECU security-paper evidence workflow."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_ROOT / "results"
OUTPUT_DIR = RESULTS_ROOT / "paper_evidence_security_v1"
EXPORTER = PROJECT_ROOT / "scripts" / "export_paper_evidence_security_v1.py"


@dataclass(frozen=True)
class WorkflowStep:
    label: str
    command: tuple[str, ...]
    expected: Path
    rtl_generation: bool = False
    ablation: bool = False
    parameter_sweep: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the complete security-paper evidence package."
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip a study when its expected primary result already exists.",
    )
    parser.add_argument(
        "--skip-rtl",
        action="store_true",
        help="Skip the standalone make rtl-trojan-study refresh.",
    )
    parser.add_argument(
        "--skip-ablation",
        action="store_true",
        help="Skip the ablation-availability/status runner.",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Do not build or run studies; export from available result files.",
    )
    parser.add_argument(
        "--skip-parameter-sweep",
        action="store_true",
        help="Skip the deterministic fault/Trojan-parameter sensitivity study.",
    )
    parameter_mode = parser.add_mutually_exclusive_group()
    parameter_mode.add_argument(
        "--parameter-sweep-quick",
        action="store_true",
        help="Use the compact parameter grid (also the workflow default).",
    )
    parameter_mode.add_argument(
        "--parameter-sweep-full",
        action="store_true",
        help="Use the largest supported deterministic parameter grid.",
    )
    return parser.parse_args()


def run(command: Sequence[str], label: str) -> None:
    print(f"RUN  {label}: {' '.join(command)}", flush=True)
    completed = subprocess.run(list(command), cwd=PROJECT_ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {completed.returncode}")


def main() -> int:
    args = parse_args()
    python = sys.executable
    parameter_mode = "full" if args.parameter_sweep_full else "quick"
    parameter_command = (
        python,
        "scripts/run_fault_injection_parameter_sweep.py",
        f"--{parameter_mode}",
    )
    steps = (
        WorkflowStep(
            "RTL Hardware Trojan study",
            ("make", "rtl-trojan-study"),
            RESULTS_ROOT / "rtl_hardware_trojan_study_v1" / "detector_comparison.csv",
            rtl_generation=True,
        ),
        WorkflowStep(
            "full runtime validation",
            (python, "scripts/run_full_runtime_validation.py"),
            RESULTS_ROOT / "full_runtime_validation" / "combined_detection_latency_matrix.csv",
        ),
        WorkflowStep(
            "expanded runtime validation",
            (python, "scripts/run_expanded_runtime_validation.py"),
            RESULTS_ROOT
            / "expanded_runtime_validation"
            / "expanded_combined_detection_latency_matrix.csv",
        ),
        WorkflowStep(
            "negative stress validation",
            (python, "scripts/run_negative_stress_validation.py"),
            RESULTS_ROOT
            / "negative_stress_validation"
            / "negative_stress_false_alarm_matrix.csv",
        ),
        WorkflowStep(
            "simulation real-time benchmark",
            (python, "scripts/run_simulation_realtime_benchmark.py"),
            RESULTS_ROOT
            / "simulation_realtime_benchmark"
            / "simulation_realtime_benchmark_matrix.csv",
        ),
        WorkflowStep(
            "online detector timing audit",
            (python, "scripts/run_online_detector_timing_audit.py"),
            RESULTS_ROOT
            / "online_detector_timing_audit"
            / "online_detector_timing_summary.csv",
        ),
        WorkflowStep(
            "Hybrid ablation status",
            (python, "scripts/run_hybrid_ablation_study.py"),
            RESULTS_ROOT / "hybrid_ablation_study" / "ablation_status.json",
            ablation=True,
        ),
        WorkflowStep(
            f"fault/Trojan parameter sensitivity ({parameter_mode})",
            parameter_command,
            RESULTS_ROOT
            / "fault_injection_parameter_sweep"
            / "sweep_detector_summary.csv",
            parameter_sweep=True,
        ),
    )

    parameter_sweep_ran = False
    if not args.export_only:
        run(("make",), "C simulator build")
        for step in steps:
            if step.rtl_generation and args.skip_rtl:
                print(f"SKIP {step.label}: --skip-rtl")
                continue
            if step.ablation and args.skip_ablation:
                print(f"SKIP {step.label}: --skip-ablation")
                continue
            if step.parameter_sweep and args.skip_parameter_sweep:
                print(f"SKIP {step.label}: --skip-parameter-sweep")
                continue
            if args.skip_existing and step.expected.is_file():
                if step.parameter_sweep and args.parameter_sweep_full:
                    config_path = RESULTS_ROOT / "fault_injection_parameter_sweep" / "sweep_config.json"
                    existing_mode = ""
                    if config_path.is_file():
                        existing_mode = str(json.loads(config_path.read_text(encoding="utf-8")).get("mode", ""))
                    if existing_mode != "full":
                        run(step.command, step.label)
                        parameter_sweep_ran = True
                        continue
                print(f"SKIP {step.label}: existing {step.expected.relative_to(PROJECT_ROOT)}")
                continue
            if args.skip_rtl and step.label in {
                "full runtime validation",
                "expanded runtime validation",
            }:
                print(
                    f"WARNING: {step.label} internally invokes RTL generation; "
                    "--skip-rtl cannot remove that phase from the existing runner."
                )
            run(step.command, step.label)
            if step.parameter_sweep:
                parameter_sweep_ran = True
    else:
        print("EXPORT-ONLY: build and study execution skipped.")

    print("\nExpected input status:")
    for step in steps:
        state = "available" if step.expected.is_file() else "MISSING"
        print(f"  {state:9s} {step.expected.relative_to(PROJECT_ROOT)}")

    export_command = (python, str(EXPORTER.relative_to(PROJECT_ROOT)))
    run(export_command, "paper evidence exporter")
    parameter_output = RESULTS_ROOT / "fault_injection_parameter_sweep"
    parameter_table = OUTPUT_DIR / "tables" / "table_10_fault_parameter_sweep_summary.csv"
    print(
        "Parameter sweep: "
        + ("ran" if parameter_sweep_ran else "not run in this invocation")
        + f"; output {parameter_output.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Paper exporter parameter sweep inclusion: "
        + ("included" if parameter_table.is_file() else "not included (source unavailable)")
    )
    print(f"Paper evidence package: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
