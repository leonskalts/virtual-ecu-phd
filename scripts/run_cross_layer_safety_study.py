#!/usr/bin/env python3
"""Engineering validation of two cross-layer faults and legacy comparisons."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "python"))
from virtual_ecu.cross_layer_safety import (  # noqa: E402
    DEFAULT_OUTPUT_DIR, METRICS, STAGES, fault_options, load_summary,
    run_experiment, write_rows,
)


def run_study(output_dir: Path = DEFAULT_OUTPUT_DIR, seed: int = 42) -> list[dict[str, object]]:
    subprocess.run(["make"], cwd=PROJECT_ROOT, check=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    common = ["--detector", "hybrid_adaptive_kalman", "--detector-action", "limp_home"]
    cases = (
        ("baseline", ["baseline"], ["--cross-layer-monitor", "on", "--seed", str(seed)]),
        ("memory_bit_flip", ["baseline"], fault_options("bit_flip", seed=seed)),
        ("control_deadline_miss", ["baseline"], fault_options("deadline_miss", seed=seed, fault_id=2)),
        ("sensor_bias", ["custom", "sensor_bias", "45000", "10000", "transient", "6"],
         ["--cross-layer-monitor", "on", "--seed", str(seed)]),
        ("pump_degraded", ["custom", "pump_degraded", "45000", "10000", "transient", "0.45"],
         ["--cross-layer-monitor", "on", "--seed", str(seed)]),
    )
    summaries = []
    commands = []
    for name, campaign, options in cases:
        path = raw_dir / f"{name}.csv"
        commands.append(run_experiment(path, campaign, [*options, *common]))
        summaries.append({"run_id": name, "raw_csv": str(path), **load_summary(path)})
        print(f"Completed {name}")
    write_rows(output_dir / "cross_layer_run_summary.csv", summaries)
    write_rows(output_dir / "propagation_summary.csv", summaries, ("run_id", "fault_id", *STAGES))
    write_rows(output_dir / "safety_metrics_summary.csv", summaries, ("run_id", "fault_id", *METRICS))
    (output_dir / "commands.json").write_text(json.dumps(commands, indent=2) + "\n", encoding="utf-8")
    columns = (
        "run_id", "fault_id", "fault_layer", "fault_model", "fault_target", "fault_behavior",
        "fault_injection_ms", "internal_corruption", "control_effect", "actuator_effect",
        "actuator_realization_effect", "plant_manifestation", "detected",
        "cross_layer_detection_latency_ms", "safe_state_reached", "propagation_depth",
    )
    lines = [
        "# Cross-layer safety v1 engineering validation", "",
        "All five runs use the default 120 s operating profile, Hybrid Adaptive Kalman, "
        "and the limp-home detector action. Seed: " + str(seed) + ".", "",
        "Each monitored run has its own fault-free reference with the same operating "
        "configuration, detector, and safety policy. Reference state is reporting-only.", "",
        "1 = observed; 0 = not observed within this run; N/A = unavailable or not reached. "
        "Baseline safety metrics that require an injection are N/A. "
        "Times and latencies are in milliseconds.", "",
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in summaries:
        lines.append("| " + " | ".join("N/A" if row[k] is None else str(row[k]) for k in columns) + " |")
    lines += ["", "## Interpretation and limits", "",
        "Plant manifestation means |coolant temperature − reference| ≥ 0.01 °C using "
        "unrounded C state. Command/realization differences use > 1e-6 normalized units. "
        "A missed deadline can be visible internally without crossing the plant criterion.", "",
        "Detected means an alarm in the injected run while its reference has no alarm. "
        "Safe state means an applied protective mode more severe than the reference, "
        "not proof of hazard containment. Unsafe exposure uses the simulator's 115 °C "
        "critical-temperature threshold. Containment success remains N/A.", "",
        "Propagation depth is the furthest reached stage (internal=1, control=2, "
        "command=3, realization=4, plant=5). Legacy actuator faults can enter the "
        "chain at realization and feed back into control later; stages need not all occur.", "",
        "Existing detectors and thresholds are unchanged. Pre-existing detector "
        "sensor residuals use simulator plant truth; legacy alarm bookkeeping and DTC "
        "classification also use campaign metadata. No new cross-layer metadata or "
        "reference comparison enters detector decisions. Full production-signal "
        "isolation is not claimed.", "",
        "This package validates implementation behavior only; it makes no publication, "
        "certification, or real-vehicle safety claim.", "",
        "Definitions: docs/cross_layer_safety_architecture.md. Reproduction: commands.json.", "",
    ]
    (output_dir / "cross_layer_safety_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not 0 <= args.seed <= 2**32 - 1:
        parser.error("seed must be an unsigned 32-bit integer")
    run_study(args.output_dir.resolve(), args.seed)
    print(f"Cross-layer safety outputs: {args.output_dir}")


if __name__ == "__main__":
    main()
