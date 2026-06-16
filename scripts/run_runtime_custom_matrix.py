#!/usr/bin/env python3
"""Run an 18-run runtime detector/action matrix for one custom scenario."""

from __future__ import annotations

import argparse
import html
import math
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, List, Sequence

import run_runtime_intervention_study as study


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "runtime_custom_matrix" / "latest"
DEFAULT_EXECUTABLE = PROJECT_ROOT / "virtual_ecu"
FIGURE_SPECS = (
    ("detection_latency_by_detector.png", "Detection latency by detector"),
    (
        "max_coolant_by_detector_action.png",
        "Maximum coolant temperature by detector and action",
    ),
    ("action_time_by_detector_action.png", "Action time by detector and action"),
    ("missed_detections_by_detector.png", "Missed detections by detector"),
)


@dataclass(frozen=True)
class Event:
    fault_type: str
    start_ms: int
    duration_ms: int
    behavior: str
    parameter: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run all six runtime detectors and three detector actions for one "
            "custom scenario in the virtual ECU research simulator."
        )
    )
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--scenario-name", required=True)
    parser.add_argument(
        "--event",
        nargs=5,
        action="append",
        required=True,
        metavar=("FAULT_TYPE", "START_MS", "DURATION_MS", "BEHAVIOR", "PARAMETER"),
        help="Repeat for each ordered custom fault event.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--executable", type=Path, default=DEFAULT_EXECUTABLE)
    parser.add_argument("--no-figures", action="store_true")
    return parser.parse_args()


def parse_events(values: Sequence[Sequence[str]]) -> List[Event]:
    if not 1 <= len(values) <= 4:
        raise ValueError("A custom matrix requires between one and four events.")
    events = [
        Event(
            fault_type=value[0],
            start_ms=int(value[1]),
            duration_ms=int(value[2]),
            behavior=value[3],
            parameter=float(value[4]),
        )
        for value in values
    ]
    if any(event.behavior not in {"transient", "permanent"} for event in events):
        raise ValueError("Event behavior must be transient or permanent.")
    if any(event.start_ms < 0 or event.duration_ms < 0 for event in events):
        raise ValueError("Event timing values must be non-negative.")
    if any(
        current.start_ms < previous.start_ms
        for previous, current in zip(events, events[1:])
    ):
        raise ValueError("Custom events must be ordered by non-decreasing start time.")
    return events


def simulator_command(
    executable: Path,
    raw_path: Path,
    events: Sequence[Event],
    detector: str,
    action: str,
) -> List[str]:
    command = [str(executable), str(raw_path)]
    if len(events) == 1:
        event = events[0]
        command.extend(
            [
                "custom",
                event.fault_type,
                str(event.start_ms),
                str(event.duration_ms),
                event.behavior,
                f"{event.parameter:g}",
            ]
        )
    else:
        command.extend(["custom_multi", str(len(events))])
        for event in events:
            command.extend(
                [
                    event.fault_type,
                    str(event.start_ms),
                    str(event.duration_ms),
                    event.behavior,
                    f"{event.parameter:g}",
                ]
            )
    command.extend(["--detector", detector, "--detector-action", action])
    return command


def run_simulation(
    executable: Path,
    raw_dir: Path,
    scenario_id: str,
    scenario_name: str,
    events: Sequence[Event],
    detector: str,
    action: str,
) -> Dict[str, object]:
    stem = f"{detector}__{action}"
    raw_path = raw_dir / f"{stem}.csv"
    summary_path = study.summary_path_for(raw_path)
    completed = subprocess.run(
        simulator_command(executable, raw_path, events, detector, action),
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"Simulator failed for {detector}/{action}: {message}")
    if not raw_path.is_file() or not summary_path.is_file():
        raise RuntimeError(f"Simulator did not produce the expected files for {stem}")

    raw_rows = study.read_csv_rows(raw_path)
    summary = study.read_csv_rows(summary_path)[0]
    final_raw = raw_rows[-1]
    fault_start_ms = min(event.start_ms for event in events)
    detection_row = study.first_runtime_row(raw_rows, "runtime_detection_detected")
    action_row = study.first_runtime_row(
        raw_rows, "runtime_detection_action_requested"
    )
    dtc_label, dtc_time_ms, dtc_latency_ms = study.first_ecu_dtc(
        raw_rows, fault_start_ms
    )
    return {
        "scenario_id": scenario_id,
        "scenario_name": scenario_name,
        "fault_type": "+".join(event.fault_type for event in events),
        "fault_start_ms": fault_start_ms,
        "detector": detector,
        "detector_action": action,
        "runtime_detection_detected": study.parse_int(
            summary.get("runtime_detection_detected", "0"), 0
        ),
        "runtime_detection_first_detection_ms": study.parse_int(
            summary.get("runtime_detection_first_detection_ms", "-1")
        ),
        "runtime_detection_latency_ms": study.parse_int(
            summary.get("runtime_detection_latency_ms", "-1")
        ),
        "runtime_detection_action_requested": study.parse_int(
            summary.get("runtime_detection_action_requested", "0"), 0
        ),
        "runtime_detection_requested_safe_state": (
            action_row.get("runtime_detection_requested_safe_state", "none")
            if action_row is not None
            else "none"
        ),
        "runtime_detection_action_time_ms": study.parse_int(
            summary.get("runtime_detection_action_time_ms", "-1")
        ),
        "runtime_detection_false_positive_count": study.parse_int(
            final_raw.get("runtime_detection_false_positive_count", "0"), 0
        ),
        "runtime_detection_label": (
            detection_row.get("runtime_detection_label", "none")
            if detection_row is not None
            else "none"
        ),
        "first_ecu_dtc_label": dtc_label,
        "first_ecu_dtc_time_ms": dtc_time_ms,
        "first_ecu_dtc_latency_ms": dtc_latency_ms,
        "final_safe_state": summary.get("final_safe_state_label", "unknown"),
        "max_coolant_temp_c": study.parse_float(
            summary.get("max_coolant_temp_c", "")
        ),
        "safe_state_latency_ms": study.parse_int(
            summary.get("safe_state_latency_ms", "-1")
        ),
        "detection_latency_ms": study.parse_int(
            summary.get("detection_latency_ms", "-1")
        ),
        "shutdown_requested": max(
            study.parse_int(row.get("shutdown_requested", "0"), 0)
            for row in raw_rows
        ),
        "raw_csv": study.relative_path(raw_path),
        "summary_csv": study.relative_path(summary_path),
    }


def run_matrix(
    executable: Path,
    output_dir: Path,
    scenario_id: str,
    scenario_name: str,
    events: Sequence[Event],
) -> List[Dict[str, object]]:
    if not executable.is_file():
        raise FileNotFoundError(
            f"Simulator executable not found: {executable}. Run 'make' first."
        )
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, object]] = []
    total = len(study.DETECTORS) * len(study.ACTIONS)
    run_index = 0
    for detector in study.DETECTORS:
        for action in study.ACTIONS:
            run_index += 1
            print(f"[{run_index:02d}/{total}] {detector} / {action}")
            results.append(
                run_simulation(
                    executable,
                    raw_dir,
                    scenario_id,
                    scenario_name,
                    events,
                    detector,
                    action,
                )
            )
    return results


def findings(results: Sequence[Dict[str, object]]) -> List[str]:
    detector_rows = study.detector_summary(results)
    finite = [
        row
        for row in detector_rows
        if not math.isnan(float(row["mean_latency_ms"]))
    ]
    action_rows = study.action_summary(results)
    result: List[str] = []
    if finite:
        fastest_value = min(float(row["mean_latency_ms"]) for row in finite)
        fastest = [
            str(row["detector"])
            for row in finite
            if math.isclose(float(row["mean_latency_ms"]), fastest_value, abs_tol=0.5)
        ]
        result.append(
            f"Fastest detected runtime response: {' / '.join(fastest)} "
            f"at {fastest_value:.1f} ms."
        )
    observe = next(row for row in action_rows if row["action"] == "observe_only")
    coolest = min(float(row["mean_max_coolant_temp_c"]) for row in action_rows)
    coolest_actions = [
        str(row["action"])
        for row in action_rows
        if math.isclose(
            float(row["mean_max_coolant_temp_c"]), coolest, abs_tol=0.005
        )
    ]
    result.append(
        f"Lowest descriptive mean maximum coolant: {' / '.join(coolest_actions)} "
        f"at {coolest:.2f} C "
        f"({coolest - float(observe['mean_max_coolant_temp_c']):+.2f} C "
        "versus observe_only)."
    )
    missed = [
        str(row["detector"]) for row in detector_rows if int(row["missed"]) > 0
    ]
    result.append(
        "Missed observe-only detection: "
        + (", ".join(missed) if missed else "none")
        + "."
    )
    observe_states = {
        str(row["detector"]): str(row["final_safe_state"])
        for row in results
        if row["detector_action"] == "observe_only"
    }
    changed = sum(
        1
        for row in results
        if row["detector_action"] != "observe_only"
        and str(row["final_safe_state"])
        != observe_states.get(str(row["detector"]), "")
    )
    result.append(
        f"Active detector actions changed the final safe-state outcome in "
        f"{changed} of {len(results) - len(study.DETECTORS)} intervention runs."
    )
    result.append(
        "Observe-only preserves the virtual ECU simulator's built-in safety behavior."
    )
    return result


def plot_figures(
    output_dir: Path, results: Sequence[Dict[str, object]]
) -> List[Path]:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/virtual_ecu_mpl")
    os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    by_key = {
        (str(row["detector"]), str(row["detector_action"])): row for row in results
    }
    paths: List[Path] = []

    observed = [by_key[(detector, "observe_only")] for detector in study.DETECTORS]
    latencies = [
        (
            float(row["runtime_detection_latency_ms"]) / 1000.0
            if int(row["runtime_detection_detected"])
            else 0.0
        )
        for row in observed
    ]
    fig, ax = plt.subplots(figsize=(8.2, 4.8), constrained_layout=True)
    bars = ax.bar(
        study.DETECTORS,
        latencies,
        color=[study.DETECTOR_COLORS[name] for name in study.DETECTORS],
    )
    latency_scale = max(max(latencies), 0.1)
    ax.set_ylim(0.0, latency_scale * 1.25)
    for bar, row, value in zip(bars, observed, latencies):
        label = f"{value:.2f} s" if int(row["runtime_detection_detected"]) else "missed"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + latency_scale * 0.04,
            label,
            ha="center",
        )
    ax.set_ylabel("Runtime detection latency [s]")
    ax.set_title("Detection Latency by Detector (Observe Only)")
    ax.tick_params(axis="x", labelrotation=15)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    ax.grid(axis="y", linestyle=":", alpha=0.7)
    path = figure_dir / FIGURE_SPECS[0][0]
    fig.savefig(path, dpi=190)
    plt.close(fig)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(9.2, 5.0), constrained_layout=True)
    width = 0.24
    for action, offset in zip(study.ACTIONS, (-width, 0.0, width)):
        values = [
            float(by_key[(detector, action)]["max_coolant_temp_c"])
            for detector in study.DETECTORS
        ]
        ax.bar(
            [index + offset for index in range(len(study.DETECTORS))],
            values,
            width=width,
            color=study.ACTION_COLORS[action],
            label=action,
        )
    ax.set_xticks(
        range(len(study.DETECTORS)), study.DETECTORS, rotation=15, ha="right"
    )
    ax.set_ylabel("Maximum coolant [C]")
    ax.set_title("Maximum Coolant Temperature by Detector and Action")
    ax.grid(axis="y", linestyle=":", alpha=0.7)
    ax.legend(frameon=False)
    path = figure_dir / FIGURE_SPECS[1][0]
    fig.savefig(path, dpi=190)
    plt.close(fig)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(8.8, 5.0), constrained_layout=True)
    width = 0.34
    active_actions = ("precautionary_cooling", "limp_home")
    for action, offset in zip(active_actions, (-width / 2, width / 2)):
        values = [
            max(
                0.0,
                float(by_key[(detector, action)]["runtime_detection_action_time_ms"])
                / 1000.0,
            )
            for detector in study.DETECTORS
        ]
        ax.bar(
            [index + offset for index in range(len(study.DETECTORS))],
            values,
            width=width,
            color=study.ACTION_COLORS[action],
            label=action,
        )
    ax.set_xticks(
        range(len(study.DETECTORS)), study.DETECTORS, rotation=15, ha="right"
    )
    ax.set_ylabel("Absolute action time [s]")
    ax.set_title("Action Time by Detector and Action")
    ax.grid(axis="y", linestyle=":", alpha=0.7)
    ax.legend(frameon=False)
    path = figure_dir / FIGURE_SPECS[2][0]
    fig.savefig(path, dpi=190)
    plt.close(fig)
    paths.append(path)

    misses = [0 if int(row["runtime_detection_detected"]) else 1 for row in observed]
    fig, ax = plt.subplots(figsize=(7.8, 4.6), constrained_layout=True)
    bars = ax.bar(
        study.DETECTORS,
        misses,
        color=[study.DETECTOR_COLORS[name] for name in study.DETECTORS],
    )
    ax.set_ylim(0, 1.35)
    ax.set_yticks((0, 1))
    ax.set_ylabel("Missed scenarios")
    ax.set_title("Missed Detections by Detector (Observe Only)")
    ax.tick_params(axis="x", labelrotation=15)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    ax.grid(axis="y", linestyle=":", alpha=0.7)
    for bar, value in zip(bars, misses):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.06, str(value), ha="center")
    path = figure_dir / FIGURE_SPECS[3][0]
    fig.savefig(path, dpi=190)
    plt.close(fig)
    paths.append(path)
    return paths


def write_markdown(
    path: Path,
    scenario_id: str,
    scenario_name: str,
    events: Sequence[Event],
    results: Sequence[Dict[str, object]],
) -> None:
    lines = [
        "# Runtime Custom Scenario Matrix",
        "",
        "This matrix uses the virtual ECU research simulator. Runtime detectors run "
        "inside the C simulation loop, and detector actions are optional research "
        "interventions. `observe_only` preserves baseline simulator behavior.",
        "",
        f"- Scenario: {scenario_name} (`{scenario_id}`)",
        f"- Fault events: {len(events)}",
        f"- Runtime detectors: {len(study.DETECTORS)}",
        f"- Detector actions: {len(study.ACTIONS)}",
        f"- Simulator runs: {len(results)}",
        "",
        "## Key Findings",
        "",
        *(f"- {item}" for item in findings(results)),
        "",
        "## Limitations",
        "",
        "- Results are deterministic outcomes for one configured custom scenario.",
        "- This is not production ECU validation or real-vehicle validation.",
        "- Thermal differences are descriptive and do not establish statistical significance.",
        "",
        "## Reproduction",
        "",
        "Use the Runtime Study page's **Run Matrix for Latest Custom Scenario** "
        "button to reproduce this exact 5 x 3 comparison from the latest custom configuration.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(
    path: Path,
    scenario_id: str,
    scenario_name: str,
    events: Sequence[Event],
    results: Sequence[Dict[str, object]],
    figures: Sequence[Path],
) -> None:
    detector_rows = study.detector_summary(results)
    finite = [
        row
        for row in detector_rows
        if not math.isnan(float(row["mean_latency_ms"]))
    ]
    fastest_value = (
        min(float(row["mean_latency_ms"]) for row in finite) if finite else math.nan
    )
    fastest_names = [
        str(row["detector"])
        for row in finite
        if math.isclose(
            float(row["mean_latency_ms"]), fastest_value, abs_tol=0.5
        )
    ]
    action_rows = study.action_summary(results)
    coolest_value = min(
        float(row["mean_max_coolant_temp_c"]) for row in action_rows
    )
    coolest_names = [
        str(row["action"])
        for row in action_rows
        if math.isclose(
            float(row["mean_max_coolant_temp_c"]), coolest_value, abs_tol=0.005
        )
    ]
    cards = (
        ("Scenario", scenario_name),
        ("Runs", str(len(results))),
        ("Detectors", str(len(study.DETECTORS))),
        ("Action modes", str(len(study.ACTIONS))),
        (
            "Fastest detector",
            (
                f"{' / '.join(fastest_names)} ({fastest_value:.1f} ms)"
                if fastest_names
                else "n/a"
            ),
        ),
        (
            "Lowest mean max coolant",
            f"{' / '.join(coolest_names)} ({coolest_value:.2f} C)",
        ),
    )
    cards_html = "".join(
        f'<div class="card"><span>{html.escape(label)}</span>'
        f"<strong>{html.escape(value)}</strong></div>"
        for label, value in cards
    )
    findings_html = "".join(
        f"<li>{html.escape(item)}</li>" for item in findings(results)
    )
    figure_names = {figure.name for figure in figures}
    figures_html = "".join(
        "<figure>"
        f'<img src="figures/{html.escape(filename)}" alt="{html.escape(caption)}">'
        f"<figcaption>{html.escape(caption)}</figcaption></figure>"
        for filename, caption in FIGURE_SPECS
        if filename in figure_names
    )
    event_rows = "".join(
        "<tr>"
        f"<td>{index}</td><td>{html.escape(event.fault_type)}</td>"
        f"<td>{event.start_ms}</td><td>{event.duration_ms}</td>"
        f"<td>{html.escape(event.behavior)}</td><td>{event.parameter:g}</td>"
        "</tr>"
        for index, event in enumerate(events, start=1)
    )
    report = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Runtime Custom Scenario Matrix</title>
<style>
body{{margin:0;font-family:Arial,sans-serif;color:#172033;background:#f3f6fa;line-height:1.5}}
main{{max-width:1180px;margin:auto;padding:32px 22px 56px}}h1{{margin:0 0 8px}}
h2{{margin-top:30px}}p,figcaption,.card span{{color:#526173}}
.hero,.card,figure,.table-wrap,.note{{background:#fff;border:1px solid #dbe3ec;border-radius:12px}}
.hero{{padding:24px;border-top:5px solid #2563eb}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px;margin-top:18px}}
.card{{padding:14px}}.card span,.card strong{{display:block}}.card strong{{margin-top:5px;font-size:18px}}
.figures{{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:16px}}
figure{{margin:0;padding:12px}}figure img{{width:100%}}.table-wrap{{overflow:auto}}
table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{padding:8px 9px;border-bottom:1px solid #dbe3ec;text-align:left;white-space:nowrap}}
th{{background:#eef4ff}}.note{{padding:15px;border-left:4px solid #f59e0b}}
code{{background:#e8eef6;padding:2px 5px;border-radius:4px}}
</style></head><body><main>
<section class="hero"><h1>Runtime Custom Scenario Matrix</h1>
<p>This virtual ECU research simulator study evaluates one custom scenario across
six runtime detectors and three detector actions. Runtime detectors run inside
the C simulation loop. Detector actions are optional research interventions;
<code>observe_only</code> preserves baseline behavior.</p>
<div class="cards">{cards_html}</div></section>
<h2>Scenario</h2><p><strong>{html.escape(scenario_name)}</strong>
(<code>{html.escape(scenario_id)}</code>)</p>
<div class="table-wrap"><table><thead><tr><th>#</th><th>Fault</th><th>Start [ms]</th>
<th>Duration [ms]</th><th>Behavior</th><th>Parameter</th></tr></thead>
<tbody>{event_rows}</tbody></table></div>
<h2>Key Findings</h2><ul>{findings_html}</ul>
<h2>Figures</h2><div class="figures">{figures_html or '<p>Figures were not generated.</p>'}</div>
<h2>Main Comparison Table</h2>{study.html_table(results)}
<h2>Limitations</h2><div class="note">These are deterministic outcomes from a
virtual ECU research simulator for one configured scenario. This is not production
ECU validation or real-vehicle validation. Simplified plant dynamics, detector
calibration, and scenario selection limit generalization.</div>
<h2>Reproduction</h2><p>Use <strong>Run Matrix for Latest Custom Scenario</strong>
on the GUI Runtime Study page. The command is assembled from the latest normalized
custom scenario configuration.</p>
</main></body></html>"""
    path.write_text(report, encoding="utf-8")


def main() -> int:
    args = parse_args()
    events = parse_events(args.event)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    results = run_matrix(
        args.executable.resolve(),
        output_dir,
        args.scenario_id,
        args.scenario_name,
        events,
    )
    comparison_path = output_dir / "runtime_custom_matrix_comparison.csv"
    summary_path = output_dir / "runtime_custom_matrix_summary.md"
    report_path = output_dir / "runtime_custom_matrix_report.html"
    study.write_comparison_csv(comparison_path, results)
    figure_paths: List[Path] = []
    if not args.no_figures:
        figure_paths = plot_figures(output_dir, results)
    write_markdown(
        summary_path, args.scenario_id, args.scenario_name, events, results
    )
    write_html(
        report_path,
        args.scenario_id,
        args.scenario_name,
        events,
        results,
        figure_paths,
    )
    for output in (comparison_path, summary_path, report_path, *figure_paths):
        print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
