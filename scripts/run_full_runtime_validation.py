#!/usr/bin/env python3
"""Run unified RTL-security and fault-injection detector validation."""

from __future__ import annotations

import argparse
import csv
import math
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Dict, Iterable, List, Mapping, Sequence

import run_runtime_custom_matrix as custom_matrix
import run_runtime_intervention_study as intervention


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "full_runtime_validation"
DEFAULT_EXECUTABLE = PROJECT_ROOT / "virtual_ecu"
RTL_STUDY_SCRIPT = PROJECT_ROOT / "scripts" / "run_rtl_hardware_trojan_study.py"

DETECTORS = intervention.DETECTORS
OBSERVE_ONLY = "observe_only"

COMBINED_COLUMNS = (
    "experiment_family",
    "scenario_id",
    "scenario_name",
    "variant",
    "detector",
    "event_start_ms",
    "first_detection_ms",
    "detection_latency_ms",
    "detected_after_event",
    "false_positive_count",
    "detection_label",
    "max_coolant_temp_c",
    "final_safe_state",
    "raw_csv",
    "summary_csv",
)

CUSTOM_SCENARIOS = (
    (
        "sensor_interface_intermittent",
        "Sensor interface intermittent",
        (
            custom_matrix.Event(
                "sensor_interface_intermittent",
                45000,
                20000,
                "transient",
                8.0,
            ),
        ),
    ),
    (
        "ordered_multi_fault_chain",
        "Ordered sensor, pump, and fan fault chain",
        (
            custom_matrix.Event(
                "sensor_bias",
                30000,
                15000,
                "transient",
                6.0,
            ),
            custom_matrix.Event(
                "pump_degraded",
                60000,
                25000,
                "transient",
                0.45,
            ),
            custom_matrix.Event(
                "fan_stuck_off",
                90000,
                0,
                "permanent",
                0.0,
            ),
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run all Virtual ECU runtime detectors over RTL Hardware Trojan, "
            "clean-reference, and supported fault-injection scenarios."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Root directory for validation traces and engineering summaries.",
    )
    parser.add_argument(
        "--executable",
        type=Path,
        default=DEFAULT_EXECUTABLE,
        help="Path to the compiled virtual_ecu executable.",
    )
    parser.add_argument(
        "--simulation-duration-ms",
        type=int,
        default=120000,
        help="Duration used for RTL, clean-baseline, and custom fault runs.",
    )
    return parser.parse_args()


def parse_int(value: object, default: int = -1) -> int:
    text = str(value).strip()
    if text == "":
        return default
    return int(float(text))


def parse_float(value: object, default: float = math.nan) -> float:
    text = str(value).strip()
    if text == "":
        return default
    return float(text)


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"CSV has no data rows: {path}")
    return rows


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())


def write_rows(
    path: Path,
    columns: Sequence[str],
    rows: Iterable[Mapping[str, object]],
) -> None:
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


def normalize_rtl_rows(comparison_path: Path) -> List[Dict[str, object]]:
    normalized: List[Dict[str, object]] = []
    for row in read_rows(comparison_path):
        attack_variant = row["variant"] == "trojan"
        normalized.append(
            {
                "experiment_family": "rtl_security",
                "scenario_id": row["rtl_target_id"],
                "scenario_name": row["rtl_target_name"],
                "variant": row["variant"],
                "detector": row["detector"],
                "event_start_ms": (
                    parse_int(row["rtl_trojan_trigger_time_ms"])
                    if attack_variant
                    else -1
                ),
                "first_detection_ms": parse_int(
                    row["runtime_detection_first_detection_ms"]
                ),
                "detection_latency_ms": (
                    parse_int(row["detection_latency_from_payload_ms"])
                    if attack_variant
                    else -1
                ),
                "detected_after_event": (
                    parse_int(row["detected_after_payload"], 0)
                    if attack_variant
                    else 0
                ),
                "false_positive_count": parse_int(
                    row["runtime_reported_false_positive_count"], 0
                ),
                "detection_label": row["runtime_detection_label"],
                "max_coolant_temp_c": parse_float(row["max_coolant_temp_c"]),
                "final_safe_state": row["final_safe_state"],
                "raw_csv": row["raw_csv"],
                "summary_csv": row["summary_csv"],
            }
        )
    return normalized


def normalize_fault_row(
    row: Mapping[str, object],
    scenario_id: str,
    scenario_name: str,
) -> Dict[str, object]:
    event_start_ms = parse_int(row["fault_start_ms"])
    first_detection_ms = parse_int(
        row["runtime_detection_first_detection_ms"]
    )
    runtime_detected = parse_int(row["runtime_detection_detected"], 0) != 0
    detected_after_event = int(
        runtime_detected
        and first_detection_ms >= event_start_ms
    )
    return {
        "experiment_family": "fault_injection",
        "scenario_id": scenario_id,
        "scenario_name": scenario_name,
        "variant": "fault",
        "detector": row["detector"],
        "event_start_ms": event_start_ms,
        "first_detection_ms": first_detection_ms,
        "detection_latency_ms": (
            first_detection_ms - event_start_ms
            if detected_after_event
            else -1
        ),
        "detected_after_event": detected_after_event,
        "false_positive_count": parse_int(
            row["runtime_detection_false_positive_count"], 0
        ),
        "detection_label": row["runtime_detection_label"],
        "max_coolant_temp_c": parse_float(row["max_coolant_temp_c"]),
        "final_safe_state": row["final_safe_state"],
        "raw_csv": row["raw_csv"],
        "summary_csv": row["summary_csv"],
    }


def run_clean_baseline(
    executable: Path,
    output_dir: Path,
    detector: str,
    simulation_duration_ms: int,
) -> Dict[str, object]:
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"baseline__{detector}.csv"
    summary_path = intervention.summary_path_for(raw_path)
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
            str(simulation_duration_ms),
        ),
        f"clean baseline for {detector}",
    )
    raw_rows = read_rows(raw_path)
    summary = read_rows(summary_path)[0]
    final_row = raw_rows[-1]
    detection_row = intervention.first_runtime_row(
        raw_rows, "runtime_detection_detected"
    )
    first_detection_ms = parse_int(
        summary.get("runtime_detection_first_detection_ms", "-1")
    )
    return {
        "experiment_family": "fault_injection",
        "scenario_id": "baseline",
        "scenario_name": "Nominal no-fault baseline",
        "variant": "clean",
        "detector": detector,
        "event_start_ms": -1,
        "first_detection_ms": first_detection_ms,
        "detection_latency_ms": -1,
        "detected_after_event": 0,
        "false_positive_count": parse_int(
            final_row.get("runtime_detection_false_positive_count", "0"), 0
        ),
        "detection_label": (
            detection_row.get("runtime_detection_label", "none")
            if detection_row is not None
            else "none"
        ),
        "max_coolant_temp_c": parse_float(
            summary.get("max_coolant_temp_c", "")
        ),
        "final_safe_state": summary.get(
            "final_safe_state_label", "unknown"
        ),
        "raw_csv": relative_path(raw_path),
        "summary_csv": relative_path(summary_path),
    }


def run_fault_matrix(
    executable: Path,
    output_dir: Path,
    simulation_duration_ms: int,
) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    total = len(DETECTORS) * (
        1 + len(intervention.SCENARIOS) + len(CUSTOM_SCENARIOS)
    )
    run_index = 0

    baseline_dir = output_dir / "baseline"
    for detector in DETECTORS:
        run_index += 1
        print(f"  [{run_index:02d}/{total}] baseline / {detector}")
        results.append(
            run_clean_baseline(
                executable,
                baseline_dir,
                detector,
                simulation_duration_ms,
            )
        )

    intervention_raw_dir = output_dir / "intervention" / "raw"
    intervention_raw_dir.mkdir(parents=True, exist_ok=True)
    for scenario in intervention.SCENARIOS:
        for detector in DETECTORS:
            run_index += 1
            print(
                f"  [{run_index:02d}/{total}] "
                f"{scenario.scenario_id} / {detector}"
            )
            source = intervention.run_simulation(
                executable,
                intervention_raw_dir,
                scenario,
                detector,
                OBSERVE_ONLY,
            )
            results.append(
                normalize_fault_row(
                    source,
                    scenario.scenario_id,
                    scenario.scenario_name,
                )
            )

    for scenario_id, scenario_name, events in CUSTOM_SCENARIOS:
        raw_dir = output_dir / scenario_id / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        for detector in DETECTORS:
            run_index += 1
            print(f"  [{run_index:02d}/{total}] {scenario_id} / {detector}")
            source = custom_matrix.run_simulation(
                executable,
                raw_dir,
                scenario_id,
                scenario_name,
                events,
                detector,
                OBSERVE_ONLY,
                simulation_duration_ms=simulation_duration_ms,
            )
            results.append(
                normalize_fault_row(source, scenario_id, scenario_name)
            )
    return results


def event_rows(rows: Sequence[Mapping[str, object]]) -> List[Mapping[str, object]]:
    return [
        row
        for row in rows
        if row["variant"] in {"trojan", "fault"}
    ]


def detected_latencies(
    rows: Iterable[Mapping[str, object]],
) -> List[float]:
    return [
        float(row["detection_latency_ms"])
        for row in rows
        if parse_int(row["detected_after_event"], 0) != 0
        and parse_int(row["detection_latency_ms"]) >= 0
    ]


def format_metric(value: float | None) -> str:
    if value is None or math.isnan(value):
        return ""
    return f"{value:.1f}"


def coverage_summary(
    rows: Sequence[Mapping[str, object]],
) -> List[Dict[str, object]]:
    active_rows = event_rows(rows)
    summary: List[Dict[str, object]] = []
    for detector in DETECTORS:
        detector_rows = [
            row for row in active_rows if row["detector"] == detector
        ]
        family_groups = (
            (
                "rtl_security",
                [
                    row
                    for row in detector_rows
                    if row["experiment_family"] == "rtl_security"
                ],
            ),
            (
                "fault_injection",
                [
                    row
                    for row in detector_rows
                    if row["experiment_family"] == "fault_injection"
                ],
            ),
            ("combined", detector_rows),
        )
        for family, subset in family_groups:
            detected = sum(
                parse_int(row["detected_after_event"], 0)
                for row in subset
            )
            latencies = detected_latencies(subset)
            total = len(subset)
            summary.append(
                {
                    "experiment_family": family,
                    "detector": detector,
                    "event_runs": total,
                    "detections": detected,
                    "misses": total - detected,
                    "coverage_percent": (
                        f"{100.0 * detected / total:.1f}" if total else ""
                    ),
                    "mean_detection_latency_ms": format_metric(
                        mean(latencies) if latencies else None
                    ),
                    "median_detection_latency_ms": format_metric(
                        median(latencies) if latencies else None
                    ),
                }
            )
    return summary


def clean_false_alarm_summary(
    rows: Sequence[Mapping[str, object]],
) -> List[Dict[str, object]]:
    clean_rows = [row for row in rows if row["variant"] == "clean"]
    summary: List[Dict[str, object]] = []
    for detector in DETECTORS:
        for family in ("rtl_security", "fault_injection", "combined"):
            subset = [
                row
                for row in clean_rows
                if row["detector"] == detector
                and (
                    family == "combined"
                    or row["experiment_family"] == family
                )
            ]
            alarm_rows = [
                row
                for row in subset
                if parse_int(row["first_detection_ms"]) >= 0
                or parse_int(row["false_positive_count"], 0) > 0
            ]
            first_times = [
                parse_int(row["first_detection_ms"])
                for row in alarm_rows
                if parse_int(row["first_detection_ms"]) >= 0
            ]
            summary.append(
                {
                    "experiment_family": family,
                    "detector": detector,
                    "clean_runs": len(subset),
                    "clean_runs_with_alarm": len(alarm_rows),
                    "false_positive_episodes": sum(
                        parse_int(row["false_positive_count"], 0)
                        for row in subset
                    ),
                    "earliest_clean_detection_ms": (
                        min(first_times) if first_times else -1
                    ),
                }
            )
    return summary


def missed_detection_summary(
    rows: Sequence[Mapping[str, object]],
) -> List[Mapping[str, object]]:
    return [
        row
        for row in event_rows(rows)
        if parse_int(row["detected_after_event"], 0) == 0
    ]


def best_detector_summary(
    rows: Sequence[Mapping[str, object]],
) -> List[Dict[str, object]]:
    groups: Dict[tuple[str, str, str], List[Mapping[str, object]]] = defaultdict(list)
    for row in event_rows(rows):
        key = (
            str(row["experiment_family"]),
            str(row["scenario_id"]),
            str(row["scenario_name"]),
        )
        groups[key].append(row)

    summary: List[Dict[str, object]] = []
    for (family, scenario_id, scenario_name), subset in sorted(groups.items()):
        detected = [
            row
            for row in subset
            if parse_int(row["detected_after_event"], 0) != 0
            and parse_int(row["detection_latency_ms"]) >= 0
        ]
        fastest_latency = (
            min(parse_int(row["detection_latency_ms"]) for row in detected)
            if detected
            else -1
        )
        fastest = sorted(
            str(row["detector"])
            for row in detected
            if parse_int(row["detection_latency_ms"]) == fastest_latency
        )
        summary.append(
            {
                "experiment_family": family,
                "scenario_id": scenario_id,
                "scenario_name": scenario_name,
                "fastest_detector": ";".join(fastest),
                "fastest_detection_latency_ms": fastest_latency,
                "detectors_detected": len(detected),
                "detectors_missed": len(subset) - len(detected),
                "missed_by_all": int(not detected),
            }
        )
    return summary


def coverage_lookup(
    rows: Sequence[Mapping[str, object]],
) -> Dict[tuple[str, str], Mapping[str, object]]:
    return {
        (str(row["experiment_family"]), str(row["detector"])): row
        for row in rows
    }


def clean_alarm_text(rows: Sequence[Mapping[str, object]]) -> str:
    alarmed = [
        str(row["detector"])
        for row in rows
        if row["experiment_family"] == "combined"
        and parse_int(row["clean_runs_with_alarm"], 0) > 0
    ]
    return ", ".join(alarmed) if alarmed else "none"


def write_claim_summary(
    path: Path,
    rows: Sequence[Mapping[str, object]],
    coverage_rows: Sequence[Mapping[str, object]],
    clean_rows: Sequence[Mapping[str, object]],
    best_rows: Sequence[Mapping[str, object]],
) -> None:
    lookup = coverage_lookup(coverage_rows)
    misses = missed_detection_summary(rows)
    lines = [
        "# Full Runtime Validation Claim Summary",
        "",
        "This is a deterministic engineering validation summary, not a "
        "paper-ready result or a production-safety claim.",
        "",
        "## Coverage and latency",
        "",
        "| Detector | Trojan coverage | Trojan mean / median [ms] | "
        "Fault coverage | Fault mean / median [ms] |",
        "|---|---:|---:|---:|---:|",
    ]
    for detector in DETECTORS:
        rtl = lookup[("rtl_security", detector)]
        fault = lookup[("fault_injection", detector)]
        lines.append(
            f"| {detector} | {rtl['detections']}/{rtl['event_runs']} "
            f"({rtl['coverage_percent']}%) | "
            f"{rtl['mean_detection_latency_ms'] or 'n/a'} / "
            f"{rtl['median_detection_latency_ms'] or 'n/a'} | "
            f"{fault['detections']}/{fault['event_runs']} "
            f"({fault['coverage_percent']}%) | "
            f"{fault['mean_detection_latency_ms'] or 'n/a'} / "
            f"{fault['median_detection_latency_ms'] or 'n/a'} |"
        )

    lines.extend(
        [
            "",
            "## Fastest detector by scenario",
            "",
        ]
    )
    for row in best_rows:
        fastest = str(row["fastest_detector"]) or "none"
        latency = parse_int(row["fastest_detection_latency_ms"])
        latency_text = f"{latency} ms" if latency >= 0 else "missed by all"
        lines.append(
            f"- {row['scenario_id']}: {fastest} ({latency_text})."
        )

    lines.extend(
        [
            "",
            "## Clean false alarms and misses",
            "",
            f"- Detectors with any clean-run alarm: {clean_alarm_text(clean_rows)}.",
            f"- Missed detector/scenario pairs: {len(misses)}.",
        ]
    )
    if misses:
        by_detector: Dict[str, List[str]] = defaultdict(list)
        for row in misses:
            by_detector[str(row["detector"])].append(
                f"{row['experiment_family']}:{row['scenario_id']}"
            )
        for detector in DETECTORS:
            if detector in by_detector:
                lines.append(
                    f"- {detector} misses: "
                    + ", ".join(by_detector[detector])
                    + "."
                )

    lines.extend(
        [
            "",
            "## Hybrid Adaptive Kalman comparison",
            "",
        ]
    )
    for family in ("rtl_security", "fault_injection", "combined"):
        parts = []
        for detector in (
            "kalman_filter",
            "adaptive_kalman_filter",
            "hybrid_adaptive_kalman",
        ):
            row = lookup[(family, detector)]
            parts.append(
                f"{detector} {row['detections']}/{row['event_runs']} "
                f"coverage, mean {row['mean_detection_latency_ms'] or 'n/a'} ms, "
                f"median {row['median_detection_latency_ms'] or 'n/a'} ms"
            )
        lines.append(f"- {family}: " + "; ".join(parts) + ".")

    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- Fault and Trojan event metadata is read only after each run for "
            "classification and latency calculation.",
            "- RTL results are trace-driven replay rather than fully bidirectional "
            "cycle-by-cycle RTL/plant co-simulation.",
            "- The ordered multi-fault result is measured from its first event; "
            "this runner does not claim per-stage isolation.",
            "- Outcomes cover these configured deterministic traces and do not "
            "establish statistical significance or production ECU assurance.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_readme(
    path: Path,
    rows: Sequence[Mapping[str, object]],
) -> None:
    rtl_scenarios = sorted(
        {
            str(row["scenario_id"])
            for row in rows
            if row["experiment_family"] == "rtl_security"
            and row["variant"] == "trojan"
        }
    )
    fault_scenarios = sorted(
        {
            str(row["scenario_id"])
            for row in rows
            if row["experiment_family"] == "fault_injection"
            and row["variant"] == "fault"
        }
    )
    lines = [
        "# Full Runtime Validation",
        "",
        "This directory contains engineering validation artifacts for the "
        "unchanged Virtual ECU runtime detectors. It combines trace-driven RTL "
        "security cases with supported simulator fault-injection cases.",
        "",
        "## Scope",
        "",
        f"- RTL Trojan scenarios ({len(rtl_scenarios)}): "
        + ", ".join(rtl_scenarios),
        f"- Fault scenarios ({len(fault_scenarios)}): "
        + ", ".join(fault_scenarios),
        f"- Runtime detectors ({len(DETECTORS)}): " + ", ".join(DETECTORS),
        "- Runtime detector action: observe_only for fault scenarios.",
        "",
        "## Main outputs",
        "",
        "- `combined_detection_latency_matrix.csv`: normalized long-form results.",
        "- `trojan_detection_latency_matrix.csv`: RTL Trojan rows.",
        "- `fault_detection_latency_matrix.csv`: injected-fault rows.",
        "- `detector_coverage_summary.csv`: coverage plus mean/median latency.",
        "- `clean_false_alarm_summary.csv`: clean-reference alarm counts.",
        "- `missed_detection_summary.csv`: detector/scenario misses.",
        "- `best_detector_by_scenario.csv`: fastest detected result per scenario.",
        "- `validation_claim_summary.md`: bounded engineering interpretation.",
        "",
        "## Reproduction",
        "",
        "From the repository root:",
        "",
        "```sh",
        "make",
        "python3 scripts/run_full_runtime_validation.py",
        "```",
        "",
        "The runner invokes the existing RTL study and reuses the existing "
        "runtime-intervention and custom-matrix simulation helpers. Event "
        "timestamps and security metadata are consumed only after simulation "
        "for reporting and latency calculation.",
        "",
        "Generated content in this directory is ignored by Git.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.simulation_duration_ms < 1000:
        raise ValueError("Simulation duration must be at least 1000 ms.")

    output_dir = args.output_dir.resolve()
    executable = args.executable.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rtl_dir = output_dir / "rtl_security"
    print("[1/4] Running all clean and Trojan RTL targets")
    run_checked(
        (
            sys.executable,
            str(RTL_STUDY_SCRIPT),
            "--target",
            "all",
            "--output-dir",
            str(rtl_dir),
            "--executable",
            str(executable),
            "--simulation-duration-ms",
            str(args.simulation_duration_ms),
        ),
        "RTL Hardware Trojan study",
    )
    rtl_rows = normalize_rtl_rows(rtl_dir / "detector_comparison.csv")

    print("[2/4] Running clean baseline and supported fault scenarios")
    fault_rows = run_fault_matrix(
        executable,
        output_dir / "fault_injection",
        args.simulation_duration_ms,
    )
    combined_rows = rtl_rows + fault_rows

    print("[3/4] Building normalized engineering summaries")
    coverage_rows = coverage_summary(combined_rows)
    clean_rows = clean_false_alarm_summary(combined_rows)
    missed_rows = missed_detection_summary(combined_rows)
    best_rows = best_detector_summary(combined_rows)

    write_rows(
        output_dir / "combined_detection_latency_matrix.csv",
        COMBINED_COLUMNS,
        combined_rows,
    )
    write_rows(
        output_dir / "trojan_detection_latency_matrix.csv",
        COMBINED_COLUMNS,
        [
            row
            for row in combined_rows
            if row["experiment_family"] == "rtl_security"
            and row["variant"] == "trojan"
        ],
    )
    write_rows(
        output_dir / "fault_detection_latency_matrix.csv",
        COMBINED_COLUMNS,
        [
            row
            for row in combined_rows
            if row["experiment_family"] == "fault_injection"
            and row["variant"] == "fault"
        ],
    )
    write_rows(
        output_dir / "detector_coverage_summary.csv",
        (
            "experiment_family",
            "detector",
            "event_runs",
            "detections",
            "misses",
            "coverage_percent",
            "mean_detection_latency_ms",
            "median_detection_latency_ms",
        ),
        coverage_rows,
    )
    write_rows(
        output_dir / "clean_false_alarm_summary.csv",
        (
            "experiment_family",
            "detector",
            "clean_runs",
            "clean_runs_with_alarm",
            "false_positive_episodes",
            "earliest_clean_detection_ms",
        ),
        clean_rows,
    )
    write_rows(
        output_dir / "missed_detection_summary.csv",
        COMBINED_COLUMNS,
        missed_rows,
    )
    write_rows(
        output_dir / "best_detector_by_scenario.csv",
        (
            "experiment_family",
            "scenario_id",
            "scenario_name",
            "fastest_detector",
            "fastest_detection_latency_ms",
            "detectors_detected",
            "detectors_missed",
            "missed_by_all",
        ),
        best_rows,
    )
    write_claim_summary(
        output_dir / "validation_claim_summary.md",
        combined_rows,
        coverage_rows,
        clean_rows,
        best_rows,
    )
    write_readme(output_dir / "README.md", combined_rows)

    print("[4/4] Full runtime validation complete")
    print(f"Output directory: {output_dir}")
    print(f"Normalized runs: {len(combined_rows)}")
    print(f"Missed detector/scenario pairs: {len(missed_rows)}")
    print(f"Clean-run alarms: {clean_alarm_text(clean_rows)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"Full runtime validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
