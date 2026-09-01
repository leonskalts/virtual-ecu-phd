#!/usr/bin/env python3
"""Export computed Virtual ECU security-paper tables, figures, and notes."""

from __future__ import annotations

import csv
import json
import math
import os
import platform
import statistics
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_ROOT / "results"
OUTPUT_DIR = RESULTS_ROOT / "paper_evidence_security_v1"
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"

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
DETECTOR_LABELS = {
    "builtin_ecu": "Built-in ECU diagnostics",
    "threshold": "Threshold",
    "ewma": "EWMA",
    "cusum": "CUSUM",
    "thermal_observer": "Thermal observer",
    "kalman_filter": "Kalman filter",
    "adaptive_kalman_filter": "Adaptive Kalman filter",
    "hybrid_adaptive_kalman": "Hybrid Adaptive Kalman",
}
DETECTOR_COLORS = {
    "builtin_ecu": "#64748b",
    "threshold": "#2563eb",
    "ewma": "#7c3aed",
    "cusum": "#c026d3",
    "thermal_observer": "#ea580c",
    "kalman_filter": "#0891b2",
    "adaptive_kalman_filter": "#0284c7",
    "hybrid_adaptive_kalman": "#0f766e",
}
FAULT_CLASS_ORDER = (
    "Sensing path",
    "Actuator path",
    "Calibration / memory",
    "Timing / stale data",
    "Multi-event chain",
    "RTL Trojan trace replay",
    "Unknown",
)


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def find_csv(
    root: Path,
    preferred_names: Sequence[str],
    required_columns: Sequence[str],
) -> Path | None:
    candidates: List[Path] = []
    for name in preferred_names:
        direct = root / name
        if direct.is_file():
            candidates.append(direct)
    if root.is_dir():
        candidates.extend(path for path in root.rglob("*.csv") if path not in candidates)
    for path in candidates:
        try:
            with path.open("r", newline="", encoding="utf-8") as handle:
                columns = next(csv.reader(handle), [])
        except OSError:
            continue
        if set(required_columns).issubset(columns):
            return path
    return None


def as_int(row: Mapping[str, object], key: str, default: int = 0) -> int:
    text = str(row.get(key, "")).strip()
    return int(float(text)) if text else default


def as_float(row: Mapping[str, object], key: str, default: float = math.nan) -> float:
    text = str(row.get(key, "")).strip()
    return float(text) if text else default


def fmt(value: float, digits: int = 1) -> str:
    if not math.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}"


def markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_table(
    stem: str,
    columns: Sequence[str],
    rows: Sequence[Mapping[str, object]],
) -> tuple[Path, Path]:
    if not rows:
        raise ValueError(f"Refusing to write empty table: {stem}")
    csv_path = TABLE_DIR / f"{stem}.csv"
    md_path = TABLE_DIR / f"{stem}.md"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(markdown_cell(row.get(column, "")) for column in columns) + " |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path, md_path


def classify_event(row: Mapping[str, object], warnings: List[str]) -> str:
    text = " ".join(
        str(row.get(key, "")).lower()
        for key in (
            "scenario_id",
            "scenario_name",
            "scenario_group",
            "fault_type",
            "trojan_target",
            "experiment_family",
        )
    )
    if "ht4" in text or "multi_stage" in text or "multi-event" in text or "multi_fault" in text or "chain" in text:
        return "Multi-event chain"
    if "ht1" in text:
        return "Sensing path"
    if "ht2" in text:
        return "Actuator path"
    if "ht3" in text:
        return "Calibration / memory"
    if "stale" in text or "timing" in text or "communication" in text:
        return "Timing / stale data"
    if "calibration" in text or "control_target" in text or "memory" in text:
        return "Calibration / memory"
    if "fan" in text or "pump" in text or "actuator" in text:
        return "Actuator path"
    if "sensor" in text or "coolant" in text or "bias" in text:
        return "Sensing path"
    identity = str(row.get("scenario_id", row.get("scenario_name", "unknown")))
    warning = f"Could not classify event scenario: {identity}"
    if warning not in warnings:
        warnings.append(warning)
    return "Unknown"


def detector_family_rows() -> List[Dict[str, object]]:
    families = {
        "builtin_ecu": ("ECU diagnostics", "Diagnostic trouble-code state"),
        "threshold": ("Direct residual", "Instantaneous bounded ECU residuals"),
        "ewma": ("Statistical residual", "Exponentially weighted residual history"),
        "cusum": ("Statistical residual", "Cumulative residual evidence"),
        "thermal_observer": ("Model-based observer", "Healthy thermal-response mismatch"),
        "kalman_filter": ("Kalman-style observer", "Normalized innovation and bounded support"),
        "adaptive_kalman_filter": ("Context-adaptive observer", "Adaptive Kalman/context evidence"),
        "hybrid_adaptive_kalman": (
            "Proposed hybrid observer",
            "Kalman-style residual reasoning plus sensor freshness, actuator consistency, thermal response, and calibration/control-target deviation",
        ),
    }
    return [
        {
            "Detector": DETECTOR_LABELS[detector],
            "Runtime ID": detector,
            "Family": families[detector][0],
            "Main evidence": families[detector][1],
            "Online inside ECU loop": "Yes",
            "Notes": (
                "Proposed/custom detector; comparison is bounded to evaluated matrices."
                if detector == "hybrid_adaptive_kalman"
                else "Baseline comparison detector."
            ),
        }
        for detector in DETECTORS
    ]


def scenario_class_rows() -> List[Dict[str, object]]:
    return [
        {"Scenario class": "Sensing-path faults", "Example faults": "sensor_bias; sensor_interface_intermittent", "ECU path affected": "Sensor/interface measurement", "Security relevance": "Corrupted or biased ECU-visible observations", "Used in validation": "Expanded runtime matrix"},
        {"Scenario class": "Actuator-path faults", "Example faults": "fan_stuck_off", "ECU path affected": "Fan command/realized output", "Security relevance": "Command-to-actuation integrity", "Used in validation": "Expanded runtime matrix"},
        {"Scenario class": "Pump/fan degradation", "Example faults": "pump_degraded; fan_stuck_off", "ECU path affected": "Cooling actuation", "Security relevance": "Degraded or suppressed cooling response", "Used in validation": "Expanded runtime matrix"},
        {"Scenario class": "Stale sensor/timing faults", "Example faults": "stale_sensor_data", "ECU path affected": "Sampling/timing freshness", "Security relevance": "Delayed or held sensor information", "Used in validation": "Expanded runtime matrix"},
        {"Scenario class": "Calibration/memory corruption", "Example faults": "calibration_memory_corruption", "ECU path affected": "Control target/calibration", "Security relevance": "Internal control-data integrity", "Used in validation": "Expanded runtime matrix"},
        {"Scenario class": "Multi-event fault chains", "Example faults": "ordered sensor/pump/fan and calibration sequences", "ECU path affected": "Multiple ECU paths", "Security relevance": "Staged cross-path abnormal behavior", "Used in validation": "Expanded runtime matrix"},
        {"Scenario class": "Clean/no-fault stress", "Example faults": "none; ambient/load/speed/airflow/duration profiles", "ECU path affected": "Nominal plant and ECU", "Security relevance": "False-positive robustness", "Used in validation": "Negative-stress matrix"},
        {"Scenario class": "RTL Trojan trace replay", "Example faults": "HT1; HT2; HT3; HT4", "ECU path affected": "Sensor, actuator, calibration, composite paths", "Security relevance": "Representative RTL trigger/payload effects", "Used in validation": "RTL and expanded matrices"},
    ]


def expanded_tables(
    matrix_rows: Sequence[Dict[str, str]], warnings: List[str]
) -> tuple[List[Dict[str, object]], List[Dict[str, object]], List[Dict[str, object]], Dict[str, object]]:
    event_rows = [
        row
        for row in matrix_rows
        if row.get("variant") != "clean" and as_int(row, "event_start_ms", -1) >= 0
    ]
    clean_rows = [row for row in matrix_rows if row.get("variant") == "clean"]
    scenario_keys = sorted({str(row["scenario_id"]) for row in event_rows})
    fastest_counts = {detector: 0 for detector in DETECTORS}
    for scenario_id in scenario_keys:
        selected = [row for row in event_rows if row["scenario_id"] == scenario_id and as_int(row, "detected_after_event") != 0]
        if not selected:
            continue
        best = min(as_int(row, "detection_latency_ms") for row in selected)
        for row in selected:
            if as_int(row, "detection_latency_ms") == best:
                fastest_counts[str(row["detector"])] += 1

    metrics: Dict[str, Dict[str, object]] = {}
    for detector in DETECTORS:
        events = [row for row in event_rows if row["detector"] == detector]
        clean = [row for row in clean_rows if row["detector"] == detector]
        detected = [row for row in events if as_int(row, "detected_after_event") != 0]
        latencies = [as_int(row, "detection_latency_ms") for row in detected]
        clean_alarm_runs = sum(
            as_int(row, "first_detection_ms", -1) >= 0 or as_int(row, "false_positive_count") > 0
            for row in clean
        )
        metrics[detector] = {
            "event_runs": len(events),
            "detections": len(detected),
            "misses": len(events) - len(detected),
            "coverage": 100.0 * len(detected) / len(events) if events else math.nan,
            "clean_runs": len(clean),
            "clean_alarms": clean_alarm_runs,
            "mean_latency": statistics.mean(latencies) if latencies else math.nan,
            "median_latency": statistics.median(latencies) if latencies else math.nan,
            "fastest": fastest_counts[detector],
        }
    ranking = sorted(
        DETECTORS,
        key=lambda detector: (
            -float(metrics[detector]["coverage"]),
            float(metrics[detector]["mean_latency"]),
            int(metrics[detector]["clean_alarms"]),
        ),
    )
    ranks = {detector: index + 1 for index, detector in enumerate(ranking)}
    main_rows = []
    for detector in DETECTORS:
        item = metrics[detector]
        main_rows.append(
            {
                "Detector": DETECTOR_LABELS[detector],
                "Event coverage": f"{item['detections']}/{item['event_runs']} ({float(item['coverage']):.1f}%)",
                "Missed detections": item["misses"],
                "Clean-run alarms / false positives": f"{item['clean_alarms']}/{item['clean_runs']}",
                "Mean latency ms": fmt(float(item["mean_latency"])),
                "Median latency ms": fmt(float(item["median_latency"])),
                "Fastest or tied-fastest count": item["fastest"],
                "Rank or notes": f"Computed rank {ranks[detector]}" + ("; proposed detector" if detector == "hybrid_adaptive_kalman" else ""),
            }
        )

    by_class: List[Dict[str, object]] = []
    heatmap: Dict[str, Dict[str, float]] = defaultdict(dict)
    class_names = []
    for row in event_rows:
        class_name = classify_event(row, warnings)
        if class_name not in class_names:
            class_names.append(class_name)
    if (
        "RTL Trojan trace replay" not in class_names
        and any(row.get("experiment_family") == "rtl_security" for row in event_rows)
    ):
        class_names.append("RTL Trojan trace replay")
    class_names.sort(key=lambda value: FAULT_CLASS_ORDER.index(value) if value in FAULT_CLASS_ORDER else 999)
    for class_name in class_names:
        classified = (
            [row for row in event_rows if row.get("experiment_family") == "rtl_security"]
            if class_name == "RTL Trojan trace replay"
            else [row for row in event_rows if classify_event(row, warnings) == class_name]
        )
        for detector in DETECTORS:
            selected = [row for row in classified if row["detector"] == detector]
            detected = [row for row in selected if as_int(row, "detected_after_event") != 0]
            latencies = [as_int(row, "detection_latency_ms") for row in detected]
            coverage = 100.0 * len(detected) / len(selected) if selected else math.nan
            heatmap[class_name][detector] = coverage
            by_class.append(
                {
                    "Fault class": class_name,
                    "Detector": DETECTOR_LABELS[detector],
                    "Coverage": f"{len(detected)}/{len(selected)} ({fmt(coverage)}%)",
                    "Misses": len(selected) - len(detected),
                    "Mean latency ms": fmt(statistics.mean(latencies) if latencies else math.nan),
                    "Median latency ms": fmt(statistics.median(latencies) if latencies else math.nan),
                    "Notes": "Detected-event latency only.",
                }
            )
    heatmap_rows = [
        {"Fault class": class_name, **{detector: fmt(heatmap[class_name].get(detector, math.nan)) for detector in DETECTORS}}
        for class_name in class_names
    ]
    hybrid = metrics["hybrid_adaptive_kalman"]
    lowest_mean = min(float(item["mean_latency"]) for item in metrics.values() if math.isfinite(float(item["mean_latency"])))
    checks = {
        "event_variants": len(scenario_keys),
        "event_rows": len(event_rows),
        "clean_variants": len({str(row["scenario_id"]) for row in clean_rows}),
        "hybrid_full_coverage": int(hybrid["misses"]) == 0,
        "hybrid_clean_alarm_runs": hybrid["clean_alarms"],
        "hybrid_mean_latency_ms": hybrid["mean_latency"],
        "hybrid_lowest_mean_latency": math.isclose(float(hybrid["mean_latency"]), lowest_mean),
        "hybrid_fastest_or_tied_count": hybrid["fastest"],
    }
    if not checks["hybrid_full_coverage"]:
        warnings.append("Sanity check differs: Hybrid did not have full expanded-matrix event coverage.")
    if int(checks["hybrid_clean_alarm_runs"]) != 0:
        warnings.append("Sanity check differs: Hybrid had clean-run alarms in the expanded matrix.")
    if not checks["hybrid_lowest_mean_latency"]:
        warnings.append("Sanity check differs: Hybrid did not have the lowest mean detected-event latency.")
    return main_rows, by_class, heatmap_rows, {"metrics": metrics, "checks": checks, "event_rows": event_rows}


def negative_stress_rows(source_rows: Sequence[Dict[str, str]], warnings: List[str]) -> tuple[List[Dict[str, object]], Dict[str, object]]:
    rows = []
    for detector in DETECTORS:
        matches = [row for row in source_rows if row.get("detector") == detector]
        if not matches:
            warnings.append(f"Negative-stress summary is missing detector: {detector}")
            continue
        row = matches[0]
        rows.append(
            {
                "Detector": DETECTOR_LABELS[detector],
                "Clean stress variants tested": as_int(row, "clean_runs"),
                "Alarm runs": as_int(row, "false_alarm_runs"),
                "False-positive episodes": as_int(row, "total_false_positive_episodes"),
                "False-positive rate": f"{as_float(row, 'false_alarm_rate_percent'):.3f}%",
                "Notes": "Deterministic no-fault stress profiles; absence here is not a universal guarantee.",
            }
        )
    total_runs = sum(as_int(row, "clean_runs") for row in source_rows)
    variants = max((as_int(row, "clean_runs") for row in source_rows), default=0)
    alarm_runs = sum(as_int(row, "false_alarm_runs") for row in source_rows)
    if variants != 60 or total_runs != 480:
        warnings.append(f"Negative-stress sanity check differs: {variants} variants and {total_runs} runs.")
    return rows, {"variants": variants, "runs": total_runs, "alarm_runs": alarm_runs}


def rtl_summary_rows(
    comparison: Sequence[Dict[str, str]], taxonomy: Sequence[Dict[str, str]], warnings: List[str]
) -> tuple[List[Dict[str, object]], Dict[str, object]]:
    taxonomy_by_id = {row["rtl_target_id"]: row for row in taxonomy}
    expected = (
        "ht1_coolant_sensor",
        "ht2_fan_driver",
        "ht3_calibration_memory",
        "ht4_multi_stage_chain",
    )
    effects = {
        "ht1_coolant_sensor": "Masked ECU-facing coolant measurement",
        "ht2_fan_driver": "Suppressed realized fan output",
        "ht3_calibration_memory": "Shifted cooling control target",
        "ht4_multi_stage_chain": "Staged calibration, sensor, and fan effects",
    }
    rows = []
    hybrid_detected = 0
    for target_id in expected:
        meta = taxonomy_by_id.get(target_id)
        selected = [row for row in comparison if row.get("rtl_target_id") == target_id]
        trojan = [row for row in selected if row.get("variant") == "trojan"]
        clean = [row for row in selected if row.get("variant") == "clean"]
        if meta is None or not trojan or not clean:
            warnings.append(f"RTL summary is missing evidence for {target_id}.")
            continue
        detected = [row for row in trojan if as_int(row, "detected_after_payload") != 0]
        hybrid = next((row for row in trojan if row.get("detector") == "hybrid_adaptive_kalman"), None)
        hybrid_alarm = hybrid is not None and as_int(hybrid, "detected_after_payload") != 0
        hybrid_detected += int(hybrid_alarm)
        notes = (
            "Trace-driven composite of existing HT3, HT1, and HT2 effects; not an independent RTL module."
            if target_id == "ht4_multi_stage_chain"
            else "Representative RTL trigger/payload interface case study."
        )
        rows.append(
            {
                "HT ID": target_id.split("_")[0].upper(),
                "Target": trojan[0]["rtl_target_name"],
                "Trigger description": meta["trigger"],
                "Payload description": meta["payload"],
                "Trace/replay boundary": meta["evaluation_scope"],
                "ECU-visible effect": effects[target_id],
                "Detectors alarmed": f"{len(detected)}/{len(trojan)}" + (" (" + "; ".join(DETECTOR_LABELS[row["detector"]] for row in detected) + ")" if detected else ""),
                "Hybrid alarm latency ms": as_int(hybrid, "detection_latency_from_payload_ms", -1) if hybrid_alarm and hybrid else "not detected",
                "Max coolant clean": fmt(as_float(clean[0], "max_coolant_temp_c"), 2),
                "Max coolant Trojan": fmt(as_float(trojan[0], "max_coolant_temp_c"), 2),
                "Notes": notes + " No silicon/fabrication claim.",
            }
        )
    return rows, {"targets": len(rows), "hybrid_targets_detected": hybrid_detected, "trojan_rows": sum(row.get("variant") == "trojan" for row in comparison)}


def online_rows(
    causality: Sequence[Dict[str, str]], timing: Sequence[Dict[str, str]], warnings: List[str]
) -> tuple[List[Dict[str, object]], Dict[str, object]]:
    causal_by_detector = {row["detector"]: row for row in causality}
    timing_by_detector = {row["detector"]: row for row in timing}
    rows = []
    for detector in DETECTORS:
        causal = causal_by_detector.get(detector)
        timed = timing_by_detector.get(detector)
        if causal is None or timed is None:
            warnings.append(f"Online audit is missing detector: {detector}")
            continue
        rows.append(
            {
                "Detector": DETECTOR_LABELS[detector],
                "Future-sample access detected": "Yes" if as_int(causal, "uses_future_samples") else "No",
                "Causality audit result": "Passed" if as_int(causal, "causality_check_passed") else "Failed",
                "Mean update time ms": timed["mean_update_time_ms"],
                "Max update time ms": timed["max_update_time_ms"],
                "p99 update time ms": timed.get("p99_update_time_ms", "n/a"),
                "Timestep budget ms": timed["timestep_budget_ms"],
                "Budget passed": "Yes" if as_int(timed, "all_cases_fit_budget") else "No",
                "Notes": "Host-side C update audit against the simulated timestep budget; not embedded certification.",
            }
        )
    all_causal = all(as_int(row, "causality_check_passed") != 0 and as_int(row, "uses_future_samples") == 0 for row in causality)
    all_fit = all(as_int(row, "all_cases_fit_budget") != 0 for row in timing)
    hybrid = timing_by_detector.get("hybrid_adaptive_kalman", {})
    return rows, {
        "all_causal": all_causal,
        "all_fit": all_fit,
        "budget_ms": as_float(hybrid, "timestep_budget_ms"),
        "hybrid_mean_ms": as_float(hybrid, "mean_update_time_ms"),
        "hybrid_max_ms": as_float(hybrid, "max_update_time_ms"),
        "hybrid_p99_ms": as_float(hybrid, "p99_update_time_ms"),
    }


def benchmark_rows(source: Sequence[Dict[str, str]]) -> tuple[List[Dict[str, object]], List[Dict[str, object]], Dict[str, object]]:
    grouped: Dict[tuple[str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in source:
        grouped[(row["scenario_group"], row["detector"])].append(row)
    rows = []
    for group in sorted({key[0] for key in grouped}):
        for detector in DETECTORS:
            selected = grouped.get((group, detector), [])
            if not selected:
                continue
            rows.append(
                {
                    "Scenario group": group,
                    "Detector": DETECTOR_LABELS[detector],
                    "Mean real-time factor": fmt(statistics.mean(as_float(row, "real_time_factor_mean") for row in selected), 3),
                    "Min real-time factor": fmt(min(as_float(row, "real_time_factor_min") for row in selected), 3),
                    "Max real-time factor": fmt(max(as_float(row, "real_time_factor_max") for row in selected), 3),
                    "Faster than wall-clock real time": "Yes" if all(as_int(row, "faster_than_realtime_mean") for row in selected) else "No",
                    "Notes": "Host-side simulator-process throughput; not embedded ECU timing certification.",
                }
            )
    by_mean = sorted(source, key=lambda row: as_float(row, "real_time_factor_mean"))
    hybrid_values = [as_float(row, "real_time_factor_mean") for row in source if row["detector"] == "hybrid_adaptive_kalman"]
    overall = {
        "fastest": by_mean[-1],
        "slowest": by_mean[0],
        "hybrid_mean": statistics.mean(hybrid_values),
        "all_faster": all(as_int(row, "faster_than_realtime_mean") for row in source),
        "cases": len(source),
    }
    overall_rows = [
        {"Metric": "Fastest case", "Value": f"{by_mean[-1]['benchmark_id']} — {as_float(by_mean[-1], 'real_time_factor_mean'):.3f}x"},
        {"Metric": "Slowest case", "Value": f"{by_mean[0]['benchmark_id']} — {as_float(by_mean[0], 'real_time_factor_mean'):.3f}x"},
        {"Metric": "Hybrid mean real-time factor", "Value": f"{overall['hybrid_mean']:.3f}x"},
        {"Metric": "All cases faster than wall-clock real time", "Value": "Yes" if overall["all_faster"] else "No"},
        {"Metric": "Aggregate detector/scenario cases", "Value": len(source)},
    ]
    return rows, overall_rows, overall


def configure_matplotlib() -> object:
    cache_dir = Path(tempfile.gettempdir()) / "virtual_ecu_paper_evidence_matplotlib"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "figure.dpi": 120,
            "savefig.dpi": 300,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linestyle": ":",
        }
    )
    return plt


def save_figure(plt: object, fig: object, stem: str) -> List[Path]:
    paths = []
    for suffix in ("png", "pdf"):
        path = FIGURE_DIR / f"{stem}.{suffix}"
        fig.savefig(path, bbox_inches="tight")
        paths.append(path)
    plt.close(fig)
    return paths


def draw_flow_figure(plt: object) -> List[Path]:
    fig, ax = plt.subplots(figsize=(14.0, 3.4))
    ax.axis("off")
    boxes = (
        ("Fault / Trojan\nscenario", "#dbeafe"),
        ("Virtual ECU loop\nsense • control\ndiagnose • actuate", "#e0f2fe"),
        ("Eight online\nruntime detectors", "#ede9fe"),
        ("Alarm / optional\nsafe-state request", "#fef3c7"),
        ("Thermal plant\noutcome", "#dcfce7"),
        ("CSV / results / GUI\nevidence export", "#f1f5f9"),
    )
    xs = [0.02, 0.18, 0.40, 0.56, 0.73, 0.87]
    widths = [0.12, 0.18, 0.12, 0.13, 0.11, 0.12]
    for index, ((label, color), x, width) in enumerate(zip(boxes, xs, widths)):
        ax.add_patch(plt.Rectangle((x, 0.35), width, 0.30, transform=ax.transAxes, facecolor=color, edgecolor="#475569", linewidth=1.2))
        ax.text(x + width / 2, 0.50, label, transform=ax.transAxes, ha="center", va="center", fontsize=8.0, weight="bold" if index in {1, 2} else "normal")
        if index < len(boxes) - 1:
            ax.annotate("", xy=(xs[index + 1] - 0.004, 0.50), xytext=(x + width + 0.004, 0.50), xycoords=ax.transAxes, arrowprops={"arrowstyle": "->", "color": "#334155", "lw": 1.4})
    ax.set_title("Virtual ECU Security-Oriented Evaluation Flow", pad=12, weight="bold")
    return save_figure(plt, fig, "figure_1_virtual_ecu_security_evaluation_flow")


def draw_hybrid_figure(plt: object) -> List[Path]:
    fig, ax = plt.subplots(figsize=(10.5, 5.5))
    ax.axis("off")
    sources = (
        "Kalman-style\nresidual reasoning",
        "Sensor\nfreshness",
        "Actuator\nconsistency",
        "Thermal\nresponse",
        "Calibration / control-\ntarget deviation",
    )
    ys = [0.82, 0.66, 0.50, 0.34, 0.18]
    for label, y in zip(sources, ys):
        ax.add_patch(plt.Rectangle((0.05, y - 0.055), 0.28, 0.11, transform=ax.transAxes, facecolor="#e0f2fe", edgecolor="#0369a1"))
        ax.text(0.19, y, label, transform=ax.transAxes, ha="center", va="center", fontsize=9)
        ax.annotate("", xy=(0.47, 0.50), xytext=(0.34, y), xycoords=ax.transAxes, arrowprops={"arrowstyle": "->", "color": "#475569", "lw": 1.2})
    ax.add_patch(plt.Rectangle((0.47, 0.40), 0.22, 0.20, transform=ax.transAxes, facecolor="#ccfbf1", edgecolor="#0f766e", linewidth=1.8))
    ax.text(0.58, 0.50, "Hybrid Adaptive Kalman\nevidence fusion", transform=ax.transAxes, ha="center", va="center", weight="bold")
    ax.annotate("", xy=(0.78, 0.50), xytext=(0.70, 0.50), xycoords=ax.transAxes, arrowprops={"arrowstyle": "->", "color": "#475569", "lw": 1.5})
    ax.add_patch(plt.Rectangle((0.78, 0.40), 0.18, 0.20, transform=ax.transAxes, facecolor="#fef3c7", edgecolor="#b45309", linewidth=1.4))
    ax.text(0.87, 0.50, "Runtime anomaly alarm\n/ optional safe-state\nrequest", transform=ax.transAxes, ha="center", va="center", fontsize=9)
    ax.set_title("Hybrid Adaptive Kalman Evidence Fusion", pad=12, weight="bold")
    return save_figure(plt, fig, "figure_2_hybrid_adaptive_kalman_evidence_fusion")


def draw_data_figures(
    plt: object,
    expanded: Dict[str, object],
    heatmap_rows: Sequence[Dict[str, object]],
    negative_rows_data: Sequence[Dict[str, object]],
    rtl_comparison: Sequence[Dict[str, str]],
    online_timing: Sequence[Dict[str, str]],
    benchmark_source: Sequence[Dict[str, str]],
) -> List[Path]:
    paths: List[Path] = []
    metrics = expanded["metrics"]
    labels = [DETECTOR_LABELS[detector] for detector in DETECTORS]
    colors = [DETECTOR_COLORS[detector] for detector in DETECTORS]

    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    values = [float(metrics[detector]["coverage"]) for detector in DETECTORS]
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylim(0, 108)
    ax.set_ylabel("Event coverage [%]")
    ax.set_title("Detector Coverage — Expanded Deterministic Validation")
    ax.tick_params(axis="x", rotation=24)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1.2, f"{value:.1f}%", ha="center", fontsize=8)
    paths.extend(save_figure(plt, fig, "figure_3_detector_coverage_comparison"))

    event_rows = expanded["event_rows"]
    latency_sets = [
        [as_int(row, "detection_latency_ms") for row in event_rows if row["detector"] == detector and as_int(row, "detected_after_event") != 0]
        for detector in DETECTORS
    ]
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    box = ax.boxplot(latency_sets, tick_labels=labels, patch_artist=True, showfliers=True)
    for patch, color in zip(box["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
    ax.set_ylabel("Detected-event latency [ms]")
    ax.set_title("Detector Latency — Expanded Deterministic Validation")
    ax.tick_params(axis="x", rotation=24)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    paths.extend(save_figure(plt, fig, "figure_4_detector_latency_comparison"))

    classes = [str(row["Fault class"]) for row in heatmap_rows]
    matrix = [[float(row[detector]) for detector in DETECTORS] for row in heatmap_rows]
    fig, ax = plt.subplots(figsize=(11.2, max(4.5, 0.65 * len(classes) + 2.0)))
    image = ax.imshow(matrix, cmap="YlGnBu", vmin=0, vmax=100, aspect="auto")
    ax.grid(False)
    ax.set_xticks(range(len(DETECTORS)), labels=labels, rotation=28, ha="right")
    ax.set_yticks(range(len(classes)), labels=classes)
    ax.set_title("Per-Fault-Class Detector Coverage [%]")
    for y, values_row in enumerate(matrix):
        for x, value in enumerate(values_row):
            ax.text(x, y, f"{value:.0f}", ha="center", va="center", color="white" if value >= 65 else "#0f172a", fontsize=8)
    fig.colorbar(image, ax=ax, label="Coverage [%]")
    paths.extend(save_figure(plt, fig, "figure_5_per_fault_class_coverage_heatmap"))

    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    rates = [float(str(row["False-positive rate"]).rstrip("%")) for row in negative_rows_data]
    bars = ax.bar(labels, rates, color=colors)
    ax.set_ylim(0, max(1.0, max(rates, default=0.0) * 1.2))
    ax.set_ylabel("False-positive run rate [%]")
    ax.set_title("Negative-Stress False-Positive Summary")
    ax.tick_params(axis="x", rotation=24)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    if max(rates, default=0.0) == 0.0:
        ax.text(0.5, 0.88, "No alarm runs in the evaluated deterministic clean-stress matrix", transform=ax.transAxes, ha="center", va="center", fontsize=9, bbox={"facecolor": "white", "edgecolor": "#94a3b8", "boxstyle": "round,pad=0.4"})
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, max(0.025, rate + 0.02), f"{rate:.3f}%", ha="center", fontsize=7.5)
    paths.extend(save_figure(plt, fig, "figure_6_negative_stress_false_positive_summary"))

    target_ids = ["ht1_coolant_sensor", "ht2_fan_driver", "ht3_calibration_memory", "ht4_multi_stage_chain"]
    outcome = []
    for target in target_ids:
        outcome.append([
            max((as_int(row, "detected_after_payload") for row in rtl_comparison if row.get("rtl_target_id") == target and row.get("variant") == "trojan" and row.get("detector") == detector), default=0)
            for detector in DETECTORS
        ])
    fig, ax = plt.subplots(figsize=(10.5, 4.5))
    image = ax.imshow(outcome, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.grid(False)
    ax.set_xticks(range(len(DETECTORS)), labels=labels, rotation=28, ha="right")
    ax.set_yticks(range(4), labels=("HT1 Sensor", "HT2 Fan", "HT3 Calibration", "HT4 Composite"))
    ax.set_title("Representative RTL Trojan Case-Study Detection Outcome")
    for y, row in enumerate(outcome):
        for x, value in enumerate(row):
            ax.text(x, y, "Alarm" if value else "Miss", ha="center", va="center", fontsize=7.5, color="white" if value else "#0f172a")
    fig.colorbar(image, ax=ax, ticks=(0, 1), label="Detected after payload")
    paths.extend(save_figure(plt, fig, "figure_7_rtl_ht1_ht4_detection_summary"))

    timing_by = {row["detector"]: row for row in online_timing}
    max_times = [as_float(timing_by[detector], "max_update_time_ms") for detector in DETECTORS]
    budget = as_float(timing_by[DETECTORS[0]], "timestep_budget_ms")
    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    ax.bar(labels, max_times, color=colors)
    ax.axhline(budget, color="#dc2626", linestyle="--", linewidth=1.4, label=f"Simulated timestep budget ({budget:g} ms)")
    ax.set_yscale("log")
    ax.set_ylabel("Maximum observed update time [ms, log scale]")
    ax.set_title("Host-Side Detector Timing vs Simulated Timestep Budget")
    ax.tick_params(axis="x", rotation=24)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    ax.legend(frameon=False)
    paths.extend(save_figure(plt, fig, "figure_8_online_detector_timing_vs_budget"))

    factor_values = [
        statistics.mean(as_float(row, "real_time_factor_mean") for row in benchmark_source if row["detector"] == detector)
        for detector in DETECTORS
    ]
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    ax.bar(labels, factor_values, color=colors)
    ax.axhline(1.0, color="#dc2626", linestyle="--", linewidth=1.3, label="Wall-clock real time (1x)")
    ax.set_ylabel("Mean host simulation real-time factor [x]")
    ax.set_title("Host-Side Simulation Throughput by Detector")
    ax.tick_params(axis="x", rotation=24)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    ax.legend(frameon=False)
    paths.extend(save_figure(plt, fig, "figure_9_simulation_throughput_realtime_factor"))
    return paths


def write_narratives(
    sources: Mapping[str, Path],
    warnings: Sequence[str],
    expanded: Dict[str, object],
    negative: Dict[str, object],
    rtl: Dict[str, object],
    online: Dict[str, object],
    benchmark: Dict[str, object],
    ablation_available: bool,
) -> None:
    source_lines = "\n".join(f"- `{path.relative_to(PROJECT_ROOT)}`" for path in sources.values())
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) or "- None."
    readme = f"""# Virtual ECU Security Paper Evidence Package v1

This package contains paper-oriented tables, figures, bounded claims, limitations,
and reproduction commands computed from repository validation results. It centers
on Hybrid Adaptive Kalman, security-oriented fault injection, representative
HT1–HT4 RTL case studies, comparison with seven baseline detectors, online
execution evidence, and clean negative-stress evidence.

## Source result files

{source_lines}

## Package contents

- `tables/`: CSV and Markdown versions of Tables 1–8, heatmap-ready coverage,
  throughput overall summary, and an ablation-status note.
- `figures/`: publication-style PNG and PDF versions of Figures 1–9.
- `claims_summary.md`: claims computed from the source tables.
- `limitations.md`: explicit model, RTL, timing, and generalization boundaries.
- `reproduction_commands.md`: exact study and export commands.

## Completion status

- Eight-detector expanded comparison: complete from available results.
- Per-fault-class breakdown: complete; uncertain mappings would be reported as `Unknown`.
- Negative-stress validation: complete from available results.
- HT1–HT4 summary: complete from available results.
- Online timing/causality and simulation throughput: complete from available results.
- Hybrid component ablation: {'quantitative data available' if ablation_available else 'not included; explicit component-disable variants are not implemented'}.

## Export warnings

{warning_lines}

All quantitative values are derived from CSV evidence. This package does not
include unrelated result families or local GUI session state.
"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")

    checks = expanded["checks"]
    claims = [
        "# Computed Claims Summary",
        "",
        f"- In the evaluated {expanded['source_label']} deterministic matrix, Hybrid Adaptive Kalman detected {int(expanded['metrics']['hybrid_adaptive_kalman']['detections'])}/{int(expanded['metrics']['hybrid_adaptive_kalman']['event_runs'])} event variants ({float(expanded['metrics']['hybrid_adaptive_kalman']['coverage']):.1f}% coverage) with {int(checks['hybrid_clean_alarm_runs'])} clean-run alarms across {int(expanded['metrics']['hybrid_adaptive_kalman']['clean_runs'])} clean variants.",
        f"- In that matrix, Hybrid Adaptive Kalman had a mean detected-event latency of {float(checks['hybrid_mean_latency_ms']):.1f} ms and was fastest or tied-fastest in {int(checks['hybrid_fastest_or_tied_count'])}/{int(checks['event_variants'])} event variants.",
        f"- Under the evaluated negative-stress profiles, the eight detectors produced {int(negative['alarm_runs'])} alarm runs across {int(negative['runs'])} detector/profile runs ({int(negative['variants'])} profiles per detector). This does not establish that false alarms are impossible.",
        f"- In the representative RTL trigger/payload case studies, Hybrid Adaptive Kalman alarmed after payload activation for {int(rtl['hybrid_targets_detected'])}/{int(rtl['targets'])} HT targets. HT4 is a trace-driven composite of existing HT3, HT1, and HT2 effects, not an independent RTL module.",
        f"- The evaluated detector implementations passed the sampled prefix-causality checks with no future-sample access reported: {'yes' if online['all_causal'] else 'no'}. On the evaluated host, all measured detector updates fit the {float(online['budget_ms']):g} ms simulated timestep budget: {'yes' if online['all_fit'] else 'no'}.",
        f"- In the host-side simulation benchmark on the evaluated platform, all {int(benchmark['cases'])} cases completed faster than wall-clock real time: {'yes' if benchmark['all_faster'] else 'no'}. Hybrid Adaptive Kalman's mean real-time factor was {float(benchmark['hybrid_mean']):.3f}x.",
        "",
        "These claims apply only to the evaluated deterministic profiles, parameters, traces, detector thresholds, and host. They do not imply production readiness, embedded certification, silicon validation, exhaustive fault/Trojan detection, or hard real-time guarantees.",
    ]
    (OUTPUT_DIR / "claims_summary.md").write_text("\n".join(claims) + "\n", encoding="utf-8")

    limitations = """# Limitations

- The experiments use deterministic simulator profiles and a simplified automotive-inspired thermal plant.
- The Virtual ECU is an academic prototype, not a production ECU model or real-vehicle validation platform.
- Results depend on the evaluated profiles, event timing, payload parameters, detector thresholds, and trace boundaries.
- No result establishes detection of all possible faults or Hardware Trojans.
- HT1–HT3 are representative RTL interface trigger/payload case studies; they are not silicon/fabrication validation.
- HT4 is a trace-driven composite of existing HT3, HT1, and HT2 effects, not a new independent RTL module or fully closed-loop RTL/plant co-simulation.
- Verilator-generated interface traces are replayed through the unchanged Virtual ECU; this boundary is not physical Trojan insertion evidence.
- Host-side per-update timing and simulation throughput are not embedded hardware validation, worst-case execution-time analysis, certification, or hard real-time guarantees.
- Negative-stress results cover only the generated clean profiles and cannot prove that false alarms are impossible.
- Quantitative Hybrid component ablation is absent because explicit component-disable runtime variants have not been implemented and validated. Post-processing inference would not faithfully preserve online detector state evolution.
"""
    (OUTPUT_DIR / "limitations.md").write_text(limitations, encoding="utf-8")

    reproduction = """# Reproduction Commands

Run from the repository root. Verilator is required for commands that regenerate RTL traces.

```bash
make
make rtl-trojan-study
python3 scripts/run_full_runtime_validation.py
python3 scripts/run_expanded_runtime_validation.py
python3 scripts/run_negative_stress_validation.py
python3 scripts/run_simulation_realtime_benchmark.py
python3 scripts/run_online_detector_timing_audit.py
```

The following command currently records ablation availability/status only. It
does not produce quantitative ablation results because faithful component-disable
detector variants are not implemented:

```bash
python3 scripts/run_hybrid_ablation_study.py
```

Export from available results or run the complete workflow:

```bash
python3 scripts/export_paper_evidence_security_v1.py
python3 scripts/run_paper_security_results_v1.py
```

Reuse existing study results while refreshing the package:

```bash
python3 scripts/run_paper_security_results_v1.py --skip-existing
```
"""
    (OUTPUT_DIR / "reproduction_commands.md").write_text(reproduction, encoding="utf-8")


def consistency_checks(
    table_csvs: Sequence[Path], figure_paths: Sequence[Path], table1: Sequence[Mapping[str, object]], rtl_rows: Sequence[Mapping[str, object]]
) -> List[str]:
    failures = []
    runtime_ids = {str(row["Runtime ID"]) for row in table1}
    if runtime_ids != set(DETECTORS):
        failures.append("Detector-family table does not contain exactly the eight expected runtime IDs.")
    if sum(row["Runtime ID"] == "hybrid_adaptive_kalman" for row in table1) != 1:
        failures.append("Hybrid Adaptive Kalman does not appear exactly once in the detector-family table.")
    if {str(row["HT ID"]) for row in rtl_rows} != {"HT1", "HT2", "HT3", "HT4"}:
        failures.append("RTL table does not contain HT1, HT2, HT3, and HT4.")
    if not any(row["HT ID"] == "HT4" and "composite" in str(row["Notes"]).lower() for row in rtl_rows):
        failures.append("HT4 is not identified as a trace-driven composite.")
    for path in table_csvs:
        if not read_rows(path):
            failures.append(f"Generated table has no data rows: {path.name}")
    for path in figure_paths:
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(f"Generated figure is missing or empty: {path.name}")
    for required in (OUTPUT_DIR / "limitations.md", OUTPUT_DIR / "reproduction_commands.md"):
        if not required.is_file():
            failures.append(f"Required narrative file is missing: {required.name}")
    main_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in OUTPUT_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".csv"}
    ).lower()
    forbidden = ("fake-fault", "spoof")
    for term in forbidden:
        if term in main_text:
            failures.append(f"Excluded topic appeared in the package text: {term}")
    if "host-side" not in (OUTPUT_DIR / "claims_summary.md").read_text(encoding="utf-8").lower():
        failures.append("Claims summary does not identify host-side timing scope.")
    return failures


def main() -> int:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    warnings: List[str] = []
    sources: Dict[str, Path] = {}

    roots = {
        "full": RESULTS_ROOT / "full_runtime_validation",
        "expanded": RESULTS_ROOT / "expanded_runtime_validation",
        "negative": RESULTS_ROOT / "negative_stress_validation",
        "rtl": RESULTS_ROOT / "rtl_hardware_trojan_study_v1",
        "online": RESULTS_ROOT / "online_detector_timing_audit",
        "benchmark": RESULTS_ROOT / "simulation_realtime_benchmark",
    }
    discovery = {
        "full_matrix": ("full", ("combined_detection_latency_matrix.csv",), ("scenario_id", "detector", "variant", "detected_after_event", "detection_latency_ms")),
        "expanded_matrix": ("expanded", ("expanded_combined_detection_latency_matrix.csv",), ("scenario_id", "detector", "variant", "detected_after_event", "detection_latency_ms")),
        "negative_summary": ("negative", ("negative_stress_detector_summary.csv",), ("detector", "clean_runs", "false_alarm_runs", "false_alarm_rate_percent")),
        "rtl_comparison": ("rtl", ("detector_comparison.csv",), ("rtl_target_id", "variant", "detector", "detected_after_payload")),
        "rtl_taxonomy": ("rtl", ("attack_taxonomy_table.csv",), ("rtl_target_id", "trigger", "payload", "evaluation_scope")),
        "online_causality": ("online", ("online_detector_causality_summary.csv",), ("detector", "uses_future_samples", "causality_check_passed")),
        "online_timing": ("online", ("online_detector_timing_summary.csv",), ("detector", "mean_update_time_ms", "max_update_time_ms", "timestep_budget_ms")),
        "benchmark_matrix": ("benchmark", ("simulation_realtime_benchmark_matrix.csv",), ("scenario_group", "detector", "real_time_factor_mean", "faster_than_realtime_mean")),
    }
    for key, (root_key, names, columns) in discovery.items():
        path = find_csv(roots[root_key], names, columns)
        if path is None:
            warnings.append(f"Missing result CSV for {key} under {roots[root_key].relative_to(PROJECT_ROOT)}")
        else:
            sources[key] = path
            print(f"SOURCE {key}: {path.relative_to(PROJECT_ROOT)}")
    missing_required = [
        key
        for key in discovery
        if key not in sources and key not in {"full_matrix", "expanded_matrix"}
    ]
    if "full_matrix" not in sources and "expanded_matrix" not in sources:
        missing_required.append("expanded_matrix_or_full_matrix")
    if missing_required:
        raise RuntimeError("Required source evidence is missing: " + ", ".join(missing_required))

    comparison_key = "expanded_matrix" if "expanded_matrix" in sources else "full_matrix"
    expanded_source = read_rows(sources[comparison_key])
    negative_source = read_rows(sources["negative_summary"])
    rtl_comparison = read_rows(sources["rtl_comparison"])
    rtl_taxonomy = read_rows(sources["rtl_taxonomy"])
    online_causality = read_rows(sources["online_causality"])
    online_timing = read_rows(sources["online_timing"])
    benchmark_source = read_rows(sources["benchmark_matrix"])

    table_csvs: List[Path] = []
    table_mds: List[Path] = []
    def add_table(stem: str, columns: Sequence[str], rows: Sequence[Mapping[str, object]]) -> None:
        csv_path, md_path = write_table(stem, columns, rows)
        table_csvs.append(csv_path)
        table_mds.append(md_path)

    table1 = detector_family_rows()
    add_table("table_1_detector_families_and_evidence", tuple(table1[0]), table1)
    table2 = scenario_class_rows()
    add_table("table_2_fault_injection_scenario_classes", tuple(table2[0]), table2)

    main_rows, class_rows, heatmap_rows, expanded = expanded_tables(expanded_source, warnings)
    expanded["source_label"] = (
        "expanded runtime validation"
        if comparison_key == "expanded_matrix"
        else "full runtime validation fallback"
    )
    add_table("table_3_main_detector_comparison", tuple(main_rows[0]), main_rows)
    add_table("table_4_per_fault_class_detector_breakdown", tuple(class_rows[0]), class_rows)
    add_table("table_4_fault_class_coverage_heatmap", ("Fault class", *DETECTORS), heatmap_rows)

    negative_rows_data, negative = negative_stress_rows(negative_source, warnings)
    add_table("table_5_negative_stress_false_positive_validation", tuple(negative_rows_data[0]), negative_rows_data)

    rtl_rows, rtl = rtl_summary_rows(rtl_comparison, rtl_taxonomy, warnings)
    add_table("table_6_rtl_hardware_trojan_case_study_summary", tuple(rtl_rows[0]), rtl_rows)

    timing_rows, online = online_rows(online_causality, online_timing, warnings)
    add_table("table_7_online_detector_timing_and_causality", tuple(timing_rows[0]), timing_rows)

    throughput_rows, throughput_overall_rows, benchmark = benchmark_rows(benchmark_source)
    add_table("table_8_simulation_realtime_benchmark", tuple(throughput_rows[0]), throughput_rows)
    add_table("table_8_simulation_realtime_overall_summary", tuple(throughput_overall_rows[0]), throughput_overall_rows)

    ablation_status_path = RESULTS_ROOT / "hybrid_ablation_study" / "ablation_status.json"
    ablation_available = False
    if ablation_status_path.is_file():
        sources["ablation_status"] = ablation_status_path
        ablation_status = json.loads(ablation_status_path.read_text(encoding="utf-8"))
        ablation_available = bool(ablation_status.get("quantitative_ablation_available", False))
    ablation_note = """# Table 9 — Hybrid Ablation Status

Quantitative ablation is not included. The current C detector does not expose
validated component-disable variants for sensor freshness, actuator consistency,
calibration/control-target evidence, thermal response, or residual-only Hybrid
operation. Post-processing those channels would not faithfully reproduce the
online detector's state evolution and confirmation rules. No ablation numbers or
figure were inferred.
"""
    (TABLE_DIR / "hybrid_ablation_status.md").write_text(ablation_note, encoding="utf-8")

    plt = configure_matplotlib()
    figure_paths = []
    figure_paths.extend(draw_flow_figure(plt))
    figure_paths.extend(draw_hybrid_figure(plt))
    figure_paths.extend(draw_data_figures(plt, expanded, heatmap_rows, negative_rows_data, rtl_comparison, online_timing, benchmark_source))

    write_narratives(sources, warnings, expanded, negative, rtl, online, benchmark, ablation_available)
    failures = consistency_checks(table_csvs, figure_paths, table1, rtl_rows)
    if failures:
        raise RuntimeError("Consistency checks failed:\n- " + "\n- ".join(failures))

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/export_paper_evidence_security_v1.py",
        "python_version": platform.python_version(),
        "source_files": {key: str(path.relative_to(PROJECT_ROOT)) for key, path in sources.items()},
        "output_counts": {
            "csv_tables": len(table_csvs),
            "markdown_tables": len(table_mds) + 1,
            "png_figures": sum(path.suffix == ".png" for path in figure_paths),
            "pdf_figures": sum(path.suffix == ".pdf" for path in figure_paths),
        },
        "computed_metrics": {
            "expanded": expanded["checks"],
            "negative_stress": negative,
            "rtl": rtl,
            "online_timing": online,
            "simulation_benchmark": {
                "cases": benchmark["cases"],
                "hybrid_mean_real_time_factor": benchmark["hybrid_mean"],
                "all_cases_faster_than_realtime": benchmark["all_faster"],
                "fastest_benchmark_id": benchmark["fastest"]["benchmark_id"],
                "slowest_benchmark_id": benchmark["slowest"]["benchmark_id"],
            },
            "quantitative_ablation_available": ablation_available,
        },
        "warnings": warnings,
        "consistency_checks_passed": True,
    }
    (OUTPUT_DIR / "evidence_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print("\nConsistency report: PASS")
    print(f"  Detectors: {len(DETECTORS)}")
    print(f"  Tables: {len(table_csvs)} CSV + {len(table_mds) + 1} Markdown")
    print(f"  Figures: {len(figure_paths) // 2} PNG + PDF pairs")
    print(f"  HT targets: {rtl['targets']}")
    print(f"  Quantitative ablation: {'available' if ablation_available else 'not included (status documented)'}")
    for warning in warnings:
        print(f"  WARNING: {warning}")
    print(f"Paper evidence package written to: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=os.sys.stderr)
        raise SystemExit(1)
