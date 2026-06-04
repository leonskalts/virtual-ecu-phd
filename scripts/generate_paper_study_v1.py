#!/usr/bin/env python3
"""Generate a reproducible Paper Study v1 evidence package.

The package is intentionally independent of the GUI and does not modify the C
simulator or its CSV schema. It runs a curated set of supported campaigns,
extracts cross-layer propagation metrics from the raw simulator traces, and
writes cautious paper/professor-facing summaries.
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import shutil
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "paper_study_v1"

AGGREGATE_COLUMNS = [
    "scenario_id",
    "campaign_id",
    "campaign_label",
    "fault_class",
    "fault_type",
    "fault_behavior",
    "fault_origin",
    "ecu_visible_disturbance",
    "primary_dtc_label",
    "first_dtc_label",
    "final_safe_state_label",
    "detection_latency_s",
    "safe_state_entry_latency_s",
    "safe_state_duration_s",
    "max_coolant_temp_c",
    "final_coolant_temp_c",
    "max_sensor_residual_c",
    "max_fan_tracking_error",
    "max_pump_tracking_error",
    "faults_seen",
    "dtcs_seen",
    "safe_states_seen",
    "event_count",
    "first_fault_start_s",
    "raw_csv_path",
    "summary_csv_path",
]

TAXONOMY_COLUMNS = [
    "fault_class",
    "fault_type",
    "fault_origin",
    "ecu_visible_disturbance",
    "diagnostic_evidence_available",
    "safe_state_response_observed",
    "thermal_outcome_observed",
    "representative_scenarios",
]

REPORT_AGGREGATE_COLUMNS = [
    "scenario_id",
    "fault_type",
    "first_dtc_label",
    "final_safe_state_label",
    "detection_latency_s",
    "safe_state_duration_s",
    "max_coolant_temp_c",
]

REPORT_TAXONOMY_COLUMNS = [
    "fault_class",
    "fault_type",
    "fault_origin",
    "ecu_visible_disturbance",
    "diagnostic_evidence_available",
    "safe_state_response_observed",
    "thermal_outcome_observed",
]

REPORT_COMPARISON_COLUMNS = [
    "scenario_id",
    "fault_type",
    "max_coolant_temp_c",
    "final_coolant_temp_c",
    "first_dtc_label",
    "primary_dtc_label",
    "final_safe_state_label",
    "detection_latency_s",
    "safe_state_duration_s",
]

FAULT_CONTEXT = {
    "none": {
        "fault_class": "baseline",
        "fault_origin": "no injected hardware-origin fault",
        "ecu_visible_disturbance": "nominal sensor and actuator signals",
    },
    "sensor_bias": {
        "fault_class": "sensing-path fault",
        "fault_origin": "ADC/reference/front-end offset",
        "ecu_visible_disturbance": "biased coolant temperature measurement",
    },
    "sensor_interface_intermittent": {
        "fault_class": "sensing-path fault",
        "fault_origin": "intermittent sensor-interface corruption",
        "ecu_visible_disturbance": "bursty coolant reading glitches",
    },
    "stale_sensor_data": {
        "fault_class": "timing/communication-path fault",
        "fault_origin": "delayed sampled-data coolant transfer",
        "ecu_visible_disturbance": "older coolant sample reused by control and diagnostics",
    },
    "pump_degraded": {
        "fault_class": "actuation-path fault",
        "fault_origin": "weak driver, aging pump, or supply droop",
        "ecu_visible_disturbance": "reduced pump authority relative to command",
    },
    "fan_stuck_off": {
        "fault_class": "actuation-path fault",
        "fault_origin": "gate-driver, PWM-output, or power-stage stuck-off fault",
        "ecu_visible_disturbance": "commanded fan does not produce expected airflow",
    },
    "calibration_memory_corruption": {
        "fault_class": "computation/memory-path fault",
        "fault_origin": "corrupted coolant-control calibration memory",
        "ecu_visible_disturbance": "altered control threshold or target behavior",
    },
}


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    label: str
    command_args: Sequence[str]
    note: str


SCENARIOS: Sequence[ScenarioSpec] = (
    ScenarioSpec(
        "baseline",
        "Baseline",
        ("baseline",),
        "Nominal reference with no injected fault.",
    ),
    ScenarioSpec(
        "fan_stuck_hot_stress",
        "Fan Stuck Hot Stress",
        ("fan_stuck_hot_stress",),
        "Thermally stressed stuck-off fan actuation path case.",
    ),
    ScenarioSpec(
        "pump_degraded_only",
        "Pump Degraded Only",
        ("pump_degraded_only",),
        "Single degraded-pump actuation path case.",
    ),
    ScenarioSpec(
        "stale_sensor_data_hot_stress",
        "Stale Sensor Hot Stress",
        ("stale_sensor_data_hot_stress",),
        "Thermally stressed stale sampled-data timing/communication case.",
    ),
    ScenarioSpec(
        "sensor_bias_only",
        "Sensor Bias Only",
        ("sensor_bias_only",),
        "Single coolant sensor bias sensing path case.",
    ),
    ScenarioSpec(
        "calibration_memory_corruption",
        "Calibration Memory Corruption",
        ("calibration_memory_corruption",),
        "Single corrupted calibration memory/computation case.",
    ),
    ScenarioSpec(
        "paper_default_multi_fault",
        "Paper Default Multi-Fault",
        ("paper_default",),
        "Built-in multi-event scenario combining sensing and actuation faults.",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate results/paper_study_v1 with raw traces, aggregate CSVs, summaries, and optional figures."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Study output directory. Defaults to results/paper_study_v1.",
    )
    parser.add_argument(
        "--executable",
        default=None,
        help="Path to the compiled virtual ECU executable. Defaults to ./virtual_ecu or ./virtual_ecu.exe.",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Reuse existing raw CSV files in the output directory instead of running the simulator.",
    )
    return parser.parse_args()


def detect_executable(explicit_path: str | None) -> Path:
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    candidates.extend([PROJECT_ROOT / "virtual_ecu", PROJECT_ROOT / "virtual_ecu.exe"])

    for candidate in candidates:
        resolved = candidate if candidate.is_absolute() else PROJECT_ROOT / candidate
        if resolved.exists():
            return resolved

    raise FileNotFoundError("Compiled virtual ECU executable not found. Build it first with 'make'.")


def relative_to_project(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, columns: Sequence[str], rows: Sequence[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_scenarios(executable: Path, output_dir: Path) -> None:
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for scenario in SCENARIOS:
        raw_path = raw_dir / f"{scenario.scenario_id}.csv"
        command = [str(executable), str(raw_path), *scenario.command_args]
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"Scenario '{scenario.scenario_id}' failed.\n"
                f"Command: {' '.join(command)}\n"
                f"{completed.stderr or completed.stdout}"
            )


def format_float(value: float | None, decimals: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{decimals}f}"


def parse_float(row: Dict[str, str], key: str, default: float = 0.0) -> float:
    text = row.get(key, "")
    return default if text == "" else float(text)


def parse_int(row: Dict[str, str], key: str, default: int = 0) -> int:
    text = row.get(key, "")
    return default if text == "" else int(float(text))


def sample_period_ms(rows: Sequence[Dict[str, str]]) -> int:
    if len(rows) >= 2:
        delta = parse_int(rows[1], "time_ms") - parse_int(rows[0], "time_ms")
        if delta > 0:
            return delta
    return 100


def ordered_unique(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def event_faults(first_row: Dict[str, str]) -> List[Dict[str, str]]:
    events = []
    for index in range(1, 5):
        mode = first_row.get(f"campaign_event_{index}_mode_label", "none")
        if mode == "none":
            continue
        events.append(
            {
                "mode": mode,
                "behavior": first_row.get(f"campaign_event_{index}_behavior_label", "none"),
                "start_ms": first_row.get(f"campaign_event_{index}_start_ms", "0"),
                "duration_ms": first_row.get(f"campaign_event_{index}_duration_ms", "0"),
                "parameter": first_row.get(f"campaign_event_{index}_parameter", "0"),
            }
        )
    return events


def first_fault_start_ms(events: Sequence[Dict[str, str]]) -> int | None:
    if not events:
        return None
    return min(int(float(event["start_ms"])) for event in events)


def fault_context_for(fault_types: Sequence[str]) -> Dict[str, str]:
    if not fault_types:
        return FAULT_CONTEXT["none"]
    if len(fault_types) == 1:
        return FAULT_CONTEXT.get(fault_types[0], {})

    classes = ordered_unique(
        FAULT_CONTEXT.get(fault_type, {}).get("fault_class", "unknown fault")
        for fault_type in fault_types
    )
    origins = [
        FAULT_CONTEXT.get(fault_type, {}).get("fault_origin", fault_type)
        for fault_type in fault_types
    ]
    disturbances = [
        FAULT_CONTEXT.get(fault_type, {}).get("ecu_visible_disturbance", fault_type)
        for fault_type in fault_types
    ]
    return {
        "fault_class": "mixed hardware-origin faults"
        if len(classes) > 1
        else classes[0],
        "fault_origin": "; ".join(origins),
        "ecu_visible_disturbance": "; ".join(disturbances),
    }


def first_row_after_fault(
    rows: Sequence[Dict[str, str]],
    start_ms: int | None,
    predicate_key: str,
    normal_value: str,
) -> Dict[str, str] | None:
    if start_ms is None:
        return None
    for row in rows:
        if parse_int(row, "time_ms") < start_ms:
            continue
        if row.get(predicate_key, normal_value) != normal_value:
            return row
    return None


def derive_aggregate_row(scenario: ScenarioSpec, raw_path: Path, summary_path: Path) -> Dict[str, str]:
    rows = read_csv_rows(raw_path)
    if not rows:
        raise ValueError(f"No rows found in {raw_path}")

    first_row = rows[0]
    last_row = rows[-1]
    sample_ms = sample_period_ms(rows)
    events = event_faults(first_row)
    configured_faults = [event["mode"] for event in events]
    active_faults = ordered_unique(row.get("fault_mode_label", "none") for row in rows if row.get("fault_mode_label") != "none")
    faults_seen = ordered_unique([*active_faults, *configured_faults])
    start_ms = first_fault_start_ms(events)
    dtc_row = first_row_after_fault(rows, start_ms, "primary_dtc_label", "none")
    safe_row = first_row_after_fault(rows, start_ms, "safe_state_label", "normal")
    dtcs_seen = ordered_unique(row.get("primary_dtc_label", "none") for row in rows if row.get("primary_dtc_label") != "none")
    safe_states_seen = ordered_unique(row.get("safe_state_label", "normal") for row in rows)
    safe_duration_s = sum(1 for row in rows if row.get("safe_state_label") != "normal") * sample_ms / 1000.0

    context = fault_context_for(faults_seen)

    detection_latency_s = None
    if dtc_row is not None and start_ms is not None:
        detection_latency_s = (parse_int(dtc_row, "time_ms") - start_ms) / 1000.0

    safe_state_entry_latency_s = None
    if safe_row is not None and start_ms is not None:
        safe_state_entry_latency_s = (parse_int(safe_row, "time_ms") - start_ms) / 1000.0

    return {
        "scenario_id": scenario.scenario_id,
        "campaign_id": first_row.get("campaign_id", ""),
        "campaign_label": first_row.get("campaign_label", scenario.label),
        "fault_class": context.get("fault_class", "unknown fault"),
        "fault_type": "+".join(faults_seen) if faults_seen else "none",
        "fault_behavior": "+".join(ordered_unique(event["behavior"] for event in events)) if events else "none",
        "fault_origin": context.get("fault_origin", ""),
        "ecu_visible_disturbance": context.get("ecu_visible_disturbance", ""),
        "primary_dtc_label": last_row.get("primary_dtc_label", "none"),
        "first_dtc_label": dtc_row.get("primary_dtc_label", "none") if dtc_row else "none",
        "final_safe_state_label": last_row.get("safe_state_label", "normal"),
        "detection_latency_s": format_float(detection_latency_s, 3),
        "safe_state_entry_latency_s": format_float(safe_state_entry_latency_s, 3),
        "safe_state_duration_s": format_float(safe_duration_s, 3),
        "max_coolant_temp_c": format_float(max(parse_float(row, "coolant_temp_true_c") for row in rows), 2),
        "final_coolant_temp_c": format_float(parse_float(last_row, "coolant_temp_true_c"), 2),
        "max_sensor_residual_c": format_float(max(abs(parse_float(row, "coolant_sensor_residual_c")) for row in rows), 2),
        "max_fan_tracking_error": format_float(max(abs(parse_float(row, "fan_tracking_error")) for row in rows), 6),
        "max_pump_tracking_error": format_float(max(abs(parse_float(row, "pump_tracking_error")) for row in rows), 6),
        "faults_seen": "|".join(faults_seen) if faults_seen else "none",
        "dtcs_seen": "|".join(dtcs_seen) if dtcs_seen else "none",
        "safe_states_seen": "|".join(safe_states_seen) if safe_states_seen else "normal",
        "event_count": str(len(events)),
        "first_fault_start_s": format_float(start_ms / 1000.0 if start_ms is not None else None, 3),
        "raw_csv_path": relative_to_project(raw_path),
        "summary_csv_path": relative_to_project(summary_path),
    }


def build_aggregate(output_dir: Path) -> List[Dict[str, str]]:
    rows = []
    for scenario in SCENARIOS:
        raw_path = output_dir / "raw" / f"{scenario.scenario_id}.csv"
        summary_path = output_dir / "raw" / f"{scenario.scenario_id}_summary.csv"
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing raw CSV for scenario '{scenario.scenario_id}': {raw_path}")
        if not summary_path.exists():
            raise FileNotFoundError(f"Missing summary CSV for scenario '{scenario.scenario_id}': {summary_path}")
        rows.append(derive_aggregate_row(scenario, raw_path, summary_path))
    return rows


def build_taxonomy_rows(aggregate_rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in aggregate_rows:
        for fault_type in row["faults_seen"].split("|"):
            grouped[fault_type].append(row)

    table_rows = []
    ordered_types = ["none", "sensor_bias", "stale_sensor_data", "pump_degraded", "fan_stuck_off", "calibration_memory_corruption"]
    ordered_types.extend(sorted(set(grouped) - set(ordered_types)))

    for fault_type in ordered_types:
        if fault_type not in grouped:
            continue
        context = FAULT_CONTEXT.get(fault_type, {})
        scenario_rows = grouped[fault_type]
        exact_rows = [
            row for row in scenario_rows
            if row["fault_type"] == fault_type or (fault_type == "none" and row["fault_type"] == "none")
        ]
        evidence_rows = exact_rows if exact_rows else scenario_rows
        dtcs = ordered_unique(
            dtc
            for row in evidence_rows
            for dtc in row["dtcs_seen"].split("|")
            if dtc != "none"
        )
        safe_states = ordered_unique(
            state
            for row in evidence_rows
            for state in row["safe_states_seen"].split("|")
            if state != "normal"
        )
        max_temps = [float(row["max_coolant_temp_c"]) for row in evidence_rows if row["max_coolant_temp_c"] != "n/a"]
        table_rows.append(
            {
                "fault_class": context.get("fault_class", "mixed hardware-origin faults" if fault_type != "none" else "baseline"),
                "fault_type": fault_type,
                "fault_origin": context.get("fault_origin", fault_type),
                "ecu_visible_disturbance": context.get("ecu_visible_disturbance", fault_type),
                "diagnostic_evidence_available": "|".join(dtcs) if dtcs else "none observed in selected representative run(s)",
                "safe_state_response_observed": "|".join(safe_states) if safe_states else "normal only in selected representative run(s)",
                "thermal_outcome_observed": f"max coolant {max(max_temps):.2f} C" if max_temps else "n/a",
                "representative_scenarios": "|".join(row["scenario_id"] for row in scenario_rows),
            }
        )

    return table_rows


def markdown_table(rows: Sequence[Dict[str, str]], columns: Sequence[str]) -> str:
    lines = []
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join("---" for _ in columns) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row.get(column, "") for column in columns) + " |")
    return "\n".join(lines)


def display_label(column: str) -> str:
    labels = {
        "scenario_id": "Scenario",
        "fault_class": "Fault class",
        "fault_type": "Fault type",
        "fault_origin": "Fault origin",
        "ecu_visible_disturbance": "ECU-visible disturbance",
        "diagnostic_evidence_available": "Diagnostic evidence",
        "safe_state_response_observed": "Safe-state response",
        "thermal_outcome_observed": "Thermal outcome",
        "max_coolant_temp_c": "Max coolant [C]",
        "final_coolant_temp_c": "Final coolant [C]",
        "first_dtc_label": "First DTC",
        "primary_dtc_label": "Final primary DTC",
        "final_safe_state_label": "Final safe state",
        "detection_latency_s": "Detection [s]",
        "safe_state_entry_latency_s": "Safe-state entry [s]",
        "safe_state_duration_s": "Safe-state duration [s]",
        "max_sensor_residual_c": "Max sensor residual [C]",
        "max_fan_tracking_error": "Max fan error",
        "max_pump_tracking_error": "Max pump error",
    }
    return labels.get(column, column.replace("_", " ").title())


def html_value(value: str) -> str:
    if value == "":
        return "&nbsp;"
    return html.escape(value).replace("|", "<br>")


def html_table(
    rows: Sequence[Dict[str, str]],
    columns: Sequence[str],
    class_name: str = "",
    label_overrides: Dict[str, str] | None = None,
) -> str:
    class_attr = f' class="{html.escape(class_name)}"' if class_name else ""
    lines = [f"<table{class_attr}>", "<thead><tr>"]
    for column in columns:
        label = label_overrides.get(column, display_label(column)) if label_overrides else display_label(column)
        lines.append(f"<th>{html.escape(label)}</th>")
    lines.append("</tr></thead>")
    lines.append("<tbody>")
    for row in rows:
        lines.append("<tr>")
        for column in columns:
            lines.append(f"<td>{html_value(row.get(column, ''))}</td>")
        lines.append("</tr>")
    lines.append("</tbody></table>")
    return "\n".join(lines)


def read_markdown_bullets(path: Path, heading: str, limit: int) -> List[str]:
    if not path.exists():
        return []

    bullets: List[str] = []
    in_section = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_section = stripped == f"## {heading}"
            continue
        if in_section and stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
            if len(bullets) >= limit:
                break
    return bullets


def read_representative_interpretation(path: Path) -> str:
    if not path.exists():
        return ""

    lines = path.read_text(encoding="utf-8").splitlines()
    paragraphs: List[str] = []
    in_section = False
    current: List[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            in_section = stripped == "## Interpretation"
            continue
        if not in_section:
            continue
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(stripped)

    if current:
        paragraphs.append(" ".join(current))

    return paragraphs[0] if paragraphs else ""


def figure_lines_html(items: Sequence[str]) -> str:
    return "\n".join(item for item in items if item)


def figure_tag(output_dir: Path, filename: str, alt_text: str) -> str:
    path = output_dir / "figures" / filename
    if not path.exists():
        return f'<div class="missing">Missing figure: {html.escape(filename)}</div>'
    return (
        f'<figure><img src="figures/{html.escape(filename)}" alt="{html.escape(alt_text)}">'
        f"<figcaption>{html.escape(alt_text)}</figcaption></figure>"
    )


def key_representative_outcome(rows: Sequence[Dict[str, str]]) -> str:
    by_id = {row["scenario_id"]: row for row in rows}
    baseline = by_id.get("baseline")
    fan = by_id.get("fan_stuck_hot_stress")
    if baseline is None or fan is None:
        return "Baseline vs Fan Hot Stress unavailable"

    temp_delta = float(fan["max_coolant_temp_c"]) - float(baseline["max_coolant_temp_c"])
    return (
        f"{fan['fault_type']} -> {fan['first_dtc_label']} -> "
        f"{fan['final_safe_state_label']} -> +{temp_delta:.2f} C peak coolant"
    )


def optional_figure_tag(output_dir: Path, filename: str, alt_text: str) -> str:
    path = output_dir / "figures" / filename
    if not path.exists():
        return ""
    return figure_tag(output_dir, filename, alt_text)


def write_html_report(output_dir: Path) -> Path:
    aggregate_path = output_dir / "aggregate_summary.csv"
    taxonomy_path = output_dir / "fault_taxonomy_table.csv"
    claim_path = output_dir / "claim_summary.md"
    comparison_path = output_dir / "representative_comparison_summary.md"
    report_path = output_dir / "study_report.html"

    aggregate_rows = read_csv_rows(aggregate_path)
    taxonomy_rows = read_csv_rows(taxonomy_path)
    by_id = {row["scenario_id"]: row for row in aggregate_rows}
    comparison_rows = [
        row for scenario_id in ("baseline", "fan_stuck_hot_stress")
        if (row := by_id.get(scenario_id)) is not None
    ]

    non_baseline_count = sum(1 for row in aggregate_rows if row["scenario_id"] != "baseline")
    baseline_present = any(row["fault_class"] == "baseline" for row in aggregate_rows)
    fault_classes = sorted({row["fault_class"] for row in aggregate_rows if row["fault_class"] != "baseline"})
    fault_path_count = sum(1 for fault_class in fault_classes if fault_class != "mixed hardware-origin faults")
    mixed_present = "mixed hardware-origin faults" in fault_classes
    class_count = fault_path_count + int(mixed_present) + int(baseline_present)
    fault_class_parts = []
    if baseline_present:
        fault_class_parts.append("baseline")
    if fault_path_count > 0:
        fault_class_parts.append(f"{fault_path_count} fault paths")
    if mixed_present:
        fault_class_parts.append("mixed")
    fault_class_text = " + ".join(fault_class_parts) if fault_class_parts else "none"
    claim_bullets = read_markdown_bullets(claim_path, "Supported Claim Candidates", 6)
    representative_text = read_representative_interpretation(comparison_path)
    outcome = key_representative_outcome(aggregate_rows)

    if not claim_bullets:
        claim_bullets = [
            "The package provides reproducible CSV-backed virtual ECU traces.",
            "The traces connect fault metadata to diagnostics, safe states, residuals, and thermal outcomes.",
            "The fan hot-stress case supports a compact actuation-path propagation narrative.",
        ]

    claim_html = "\n".join(f"<li>{html.escape(item)}</li>" for item in claim_bullets)
    report_figure_html = figure_lines_html(
        [
            figure_tag(output_dir, "max_coolant_by_scenario.png", "Thermal Severity: Maximum Coolant Temperature by Scenario"),
            figure_tag(output_dir, "safe_state_duration_by_scenario.png", "Safety Response: Safe-State Duration by Scenario"),
            optional_figure_tag(output_dir, "detection_latency_by_scenario.png", "Detection Latency by Scenario"),
        ]
    )

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Virtual ECU Paper Study v1</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f7fa;
      --panel: #ffffff;
      --ink: #1c2530;
      --muted: #5b6674;
      --line: #d9e0e8;
      --accent: #2d5d7b;
      --accent-soft: #e8f1f5;
      --warn: #7c4a03;
      --warn-bg: #fff7e6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      font-size: 14px;
      line-height: 1.45;
    }}
    .page {{
      max-width: 1160px;
      margin: 0 auto;
      padding: 28px 24px 44px;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 18px;
      margin-bottom: 20px;
    }}
    h1 {{
      margin: 0;
      font-size: 30px;
      letter-spacing: 0;
    }}
    .subtitle {{
      margin: 6px 0 0;
      color: var(--accent);
      font-size: 16px;
      font-weight: 650;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      margin: 16px 0;
      box-shadow: 0 1px 2px rgba(22, 34, 51, 0.04);
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    p {{ margin: 0 0 10px; }}
    .goal {{
      background: transparent;
      border: 0;
      box-shadow: none;
      padding: 0;
      color: var(--muted);
      font-size: 15px;
    }}
    .pipeline {{
      color: var(--ink);
      font-weight: 650;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
      margin: 16px 0;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-height: 92px;
    }}
    .card .label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .card .value {{
      margin-top: 8px;
      font-size: 22px;
      font-weight: 700;
    }}
    .card .detail {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
    }}
    .wide-card {{ grid-column: span 2; }}
    .table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
    }}
    .aggregate-table-wrap {{
      overflow-x: visible;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      font-size: 12px;
    }}
    th, td {{
      padding: 8px 9px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      text-align: left;
    }}
    th {{
      background: #eef3f7;
      color: #263445;
      font-weight: 700;
      white-space: nowrap;
    }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    tbody tr:nth-child(even) td {{ background: #fafbfd; }}
    .aggregate-results {{
      table-layout: fixed;
      font-size: 11.5px;
    }}
    .aggregate-results th,
    .aggregate-results td {{
      padding: 6px 7px;
      overflow-wrap: anywhere;
      word-break: normal;
    }}
    .aggregate-results th {{
      white-space: normal;
    }}
    .aggregate-results th:nth-child(1),
    .aggregate-results td:nth-child(1) {{ width: 19%; }}
    .aggregate-results th:nth-child(2),
    .aggregate-results td:nth-child(2) {{ width: 18%; }}
    .aggregate-results th:nth-child(3),
    .aggregate-results td:nth-child(3) {{ width: 13%; }}
    .aggregate-results th:nth-child(4),
    .aggregate-results td:nth-child(4) {{ width: 15%; }}
    .aggregate-results th:nth-child(5),
    .aggregate-results td:nth-child(5) {{ width: 12%; }}
    .aggregate-results th:nth-child(6),
    .aggregate-results td:nth-child(6) {{ width: 12%; }}
    .aggregate-results th:nth-child(7),
    .aggregate-results td:nth-child(7) {{ width: 11%; }}
    .figure-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      align-items: start;
    }}
    figure {{
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 10px;
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
      max-height: 520px;
      object-fit: contain;
    }}
    figcaption {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
    }}
    .single-figure {{
      max-width: 860px;
    }}
    .claims {{
      margin: 0;
      padding-left: 20px;
    }}
    .claims li {{ margin: 7px 0; }}
    .limits {{
      border-left: 4px solid #d69b2d;
      background: var(--warn-bg);
      color: var(--warn);
    }}
    pre {{
      margin: 0;
      padding: 12px;
      border-radius: 6px;
      background: #17202a;
      color: #eef3f7;
      overflow-x: auto;
      font-size: 13px;
    }}
    .note {{
      color: var(--muted);
      font-size: 13px;
    }}
    .missing {{
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 18px;
      color: var(--muted);
      background: #fff;
    }}
    @media (max-width: 900px) {{
      .cards {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .wide-card {{ grid-column: span 2; }}
      .figure-grid {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 620px) {{
      .page {{ padding: 20px 14px 32px; }}
      .cards {{ grid-template-columns: 1fr; }}
      .wide-card {{ grid-column: span 1; }}
      h1 {{ font-size: 24px; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header>
      <h1>Virtual ECU Paper Study v1</h1>
      <p class="subtitle">Cross-Layer Fault Propagation Evidence Package</p>
    </header>

    <section class="goal">
      <p>This compact report summarizes a reproducible virtual ECU study package for research discussion. The evidence path is <span class="pipeline">fault origin &rarr; ECU-visible disturbance &rarr; diagnostic evidence / DTC &rarr; safe-state response &rarr; thermal outcome</span>. The intent is to support paper framing and research discussion without relying on the GUI.</p>
    </section>

    <div class="cards">
      <div class="card">
        <div class="label">Scenarios</div>
        <div class="value">{len(aggregate_rows)}</div>
        <div class="detail">representative runs</div>
      </div>
      <div class="card">
        <div class="label">Non-baseline</div>
        <div class="value">{non_baseline_count}</div>
        <div class="detail">fault scenarios</div>
      </div>
      <div class="card">
        <div class="label">Fault classes</div>
        <div class="value">{class_count}</div>
        <div class="detail">{html.escape(fault_class_text)}</div>
      </div>
      <div class="card">
        <div class="label">Representative case</div>
        <div class="value">Baseline vs Fan</div>
        <div class="detail">hot-stress actuation path</div>
      </div>
      <div class="card wide-card">
        <div class="label">Key outcome</div>
        <div class="value" style="font-size: 16px;">{html.escape(outcome)}</div>
        <div class="detail">deterministic representative run</div>
      </div>
    </div>

    <section>
      <h2>Fault Taxonomy</h2>
      <div class="table-wrap">
        {html_table(taxonomy_rows, REPORT_TAXONOMY_COLUMNS)}
      </div>
    </section>

    <section>
      <h2>Representative Comparison: Baseline vs Fan Hot Stress</h2>
      <div class="table-wrap">
        {html_table(comparison_rows, REPORT_COMPARISON_COLUMNS)}
      </div>
      <p class="note">{html.escape(representative_text)}</p>
      <div class="single-figure">
        {figure_tag(output_dir, "baseline_vs_fan_hot_stress.png", "Baseline vs Fan Hot Stress")}
      </div>
    </section>

    <section>
      <h2>Aggregate Results</h2>
      <div class="table-wrap aggregate-table-wrap">
        {html_table(
          aggregate_rows,
          REPORT_AGGREGATE_COLUMNS,
          "aggregate-results",
          {"safe_state_duration_s": "Safe-state [s]"},
        )}
      </div>
    </section>

    <section>
      <h2>Aggregate Figures</h2>
      <div class="figure-grid">
        {report_figure_html}
      </div>
    </section>

    <section>
      <h2>Cautious Claim Candidates</h2>
      <ul class="claims">
        {claim_html}
      </ul>
    </section>

    <section class="limits">
      <h2>Limitations / Non-Claims</h2>
      <p>This package is not circuit-level validation, not production ECU certification, not real-vehicle calibration validation, and not statistical reliability estimation. It is a compact reproducible evidence package for a research prototype.</p>
    </section>

    <section>
      <h2>Reproduction Command</h2>
      <pre><code>make
python3 scripts/generate_paper_study_v1.py</code></pre>
    </section>
  </main>
</body>
</html>
"""
    report_path.write_text(html_text, encoding="utf-8")
    return report_path


def write_representative_comparison(output_dir: Path, aggregate_rows: Sequence[Dict[str, str]]) -> None:
    by_id = {row["scenario_id"]: row for row in aggregate_rows}
    path = output_dir / "representative_comparison_summary.md"

    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Representative Comparison: Baseline vs Fan Hot Stress\n\n")
        baseline = by_id.get("baseline")
        fan = by_id.get("fan_stuck_hot_stress")
        if baseline is None or fan is None:
            handle.write("Baseline or fan_stuck_hot_stress is missing from this study run.\n")
            return

        columns = [
            "scenario_id",
            "fault_type",
            "max_coolant_temp_c",
            "final_coolant_temp_c",
            "first_dtc_label",
            "primary_dtc_label",
            "final_safe_state_label",
            "detection_latency_s",
            "safe_state_entry_latency_s",
            "safe_state_duration_s",
            "max_fan_tracking_error",
        ]
        handle.write(markdown_table([baseline, fan], columns))
        handle.write("\n\n")

        temp_delta = float(fan["max_coolant_temp_c"]) - float(baseline["max_coolant_temp_c"])
        handle.write("## Interpretation\n\n")
        handle.write(
            f"In this deterministic representative run, `fan_stuck_hot_stress` reaches a peak coolant "
            f"temperature {temp_delta:.2f} C above the baseline and records `{fan['dtcs_seen']}` as DTC evidence. "
            f"The final safe state is `{fan['final_safe_state_label']}`, compared with "
            f"`{baseline['final_safe_state_label']}` for the baseline.\n\n"
        )
        handle.write(
            "This comparison supports a propagation story from fan actuation disturbance to diagnostic "
            "evidence, safe-state response, and thermal outcome. It does not establish population-level "
            "reliability or real-vehicle calibration validity.\n"
        )


def write_claim_summary(output_dir: Path, aggregate_rows: Sequence[Dict[str, str]]) -> None:
    non_baseline = [row for row in aggregate_rows if row["scenario_id"] != "baseline"]
    detected = [row for row in non_baseline if row["dtcs_seen"] != "none"]
    safe_state_rows = [row for row in non_baseline if row["final_safe_state_label"] != "normal" or row["safe_state_duration_s"] != "0.000"]
    multi_rows = [row for row in aggregate_rows if int(row["event_count"]) > 1]
    by_id = {row["scenario_id"]: row for row in aggregate_rows}
    baseline = by_id.get("baseline")
    fan = by_id.get("fan_stuck_hot_stress")

    path = output_dir / "claim_summary.md"
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Paper Study v1 Claim Summary\n\n")
        handle.write("The statements below are cautious claim candidates supported by this generated package.\n\n")
        handle.write("## Supported Claim Candidates\n\n")
        handle.write(
            f"- The tool produces reproducible, CSV-backed traces for {len(aggregate_rows)} representative "
            "virtual ECU scenarios without requiring GUI interaction.\n"
        )
        handle.write(
            "- The raw CSV schema links configured fault events to ECU-visible labels, diagnostics, "
            "safe-state labels, actuator/sensor residuals, and thermal state in the same trace.\n"
        )
        handle.write(
            f"- In this representative set, {len(detected)} of {len(non_baseline)} non-baseline scenarios "
            "show at least one non-none diagnostic/DTC evidence label during the run.\n"
        )
        handle.write(
            f"- In this representative set, {len(safe_state_rows)} of {len(non_baseline)} non-baseline "
            "scenarios enter or finish in a non-normal safe-state response.\n"
        )
        if fan is not None and baseline is not None:
            temp_delta = float(fan["max_coolant_temp_c"]) - float(baseline["max_coolant_temp_c"])
            handle.write(
                f"- The fan hot-stress representative run demonstrates a clear actuation-path propagation "
                f"case: `{fan['faults_seen']}` leads to `{fan['dtcs_seen']}`, "
                f"`{fan['final_safe_state_label']}`, and a peak coolant temperature {temp_delta:.2f} C "
                "above baseline.\n"
            )
        if multi_rows:
            handle.write(
                "- The included multi-event scenario demonstrates that the framework can represent staged "
                "fault narratives across more than one hardware-origin path.\n"
            )

        handle.write("\n## What This Package Does Not Claim\n\n")
        handle.write("- It does not validate circuit-level transistor or device physics.\n")
        handle.write("- It does not claim production ECU safety compliance or standards certification.\n")
        handle.write("- It does not estimate field failure rates, coverage probabilities, or statistical confidence.\n")
        handle.write("- It does not claim real-vehicle calibration validity; the thermal plant is a research prototype abstraction.\n")
        handle.write("- It does not replace larger parameter sweeps; it is a compact evidence package for discussion and paper framing.\n")


def write_readme(output_dir: Path, aggregate_rows: Sequence[Dict[str, str]], figures_written: Sequence[Path]) -> None:
    path = output_dir / "README.md"
    scenario_lines = "\n".join(
        f"- `{scenario.scenario_id}`: {scenario.note}" for scenario in SCENARIOS
    )
    figure_lines = "\n".join(f"- `{relative_to_project(path)}`" for path in figures_written) or "- No figures generated; matplotlib was not available."

    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Paper Study v1\n\n")
        handle.write(
            "This folder is a compact, reproducible evidence package for the virtual ECU research prototype. "
            "It demonstrates cross-layer fault propagation beyond the GUI: fault origin -> ECU-visible "
            "disturbance -> diagnostic evidence / DTC -> safe-state response -> thermal outcome.\n\n"
        )
        handle.write("## Reproduce\n\n")
        handle.write("From the repository root:\n\n")
        handle.write("```bash\nmake\npython3 scripts/generate_paper_study_v1.py\n```\n\n")
        handle.write("To rebuild summaries from existing raw CSV files only:\n\n")
        handle.write("```bash\npython3 scripts/generate_paper_study_v1.py --skip-run\n```\n\n")
        handle.write("## Included Scenarios\n\n")
        handle.write(f"{scenario_lines}\n\n")
        handle.write("## Key Outputs\n\n")
        handle.write("- `study_report.html`: compact browser report for research meetings.\n")
        handle.write("- `aggregate_summary.csv`: one row per representative scenario with extracted propagation metrics.\n")
        handle.write("- `fault_taxonomy_table.csv`: hardware-origin fault mapping to ECU-visible and system-level evidence.\n")
        handle.write("- `representative_comparison_summary.md`: baseline vs fan hot-stress narrative.\n")
        handle.write("- `claim_summary.md`: cautious claim candidates and explicit non-claims.\n")
        handle.write("- `raw/`: simulator CSV traces and simulator summary CSV files.\n")
        handle.write("- `figures/`: optional simple PNG figures when matplotlib is installed.\n\n")
        handle.write("## Extracted Metrics\n\n")
        handle.write(", ".join(AGGREGATE_COLUMNS))
        handle.write("\n\n")
        handle.write("Latency metrics are measured relative to the first configured fault start time. ")
        handle.write("Values are `n/a` when the scenario has no injected fault or the event was not observed.\n\n")
        handle.write("## Figures\n\n")
        handle.write(f"{figure_lines}\n\n")
        handle.write("## What This Study Does Not Claim\n\n")
        handle.write("- It does not validate physical semiconductor failure mechanisms.\n")
        handle.write("- It does not certify an automotive safety case.\n")
        handle.write("- It does not provide statistical reliability estimates.\n")
        handle.write("- It does not assert real-vehicle calibration accuracy.\n")
        handle.write("- It does not change simulator behavior, CSV schemas, GUI state, or preset formats.\n")


def scenario_display_label(scenario_id: str) -> str:
    labels = {
        "baseline": "Baseline",
        "fan_stuck_hot_stress": "Fan hot stress",
        "pump_degraded_only": "Pump degraded",
        "stale_sensor_data_hot_stress": "Stale sensor hot",
        "sensor_bias_only": "Sensor bias",
        "calibration_memory_corruption": "Calibration memory",
        "paper_default_multi_fault": "Multi-fault",
    }
    return labels.get(scenario_id, scenario_id.replace("_", " "))


def numeric_report_value(row: Dict[str, str], column: str) -> float | None:
    value = row.get(column, "")
    if value in {"", "n/a"}:
        return None
    return float(value)


def plot_scenario_bar(
    plt: object,
    rows: Sequence[Dict[str, str]],
    column: str,
    title: str,
    xlabel: str,
    output_path: Path,
    color: str,
) -> bool:
    values = []
    labels = []
    for row in rows:
        value = numeric_report_value(row, column)
        if value is None:
            continue
        labels.append(scenario_display_label(row["scenario_id"]))
        values.append(value)

    if not values:
        return False

    fig_height = max(4.2, 0.45 * len(values) + 1.4)
    fig, ax = plt.subplots(figsize=(9.2, fig_height), constrained_layout=True)
    positions = list(range(len(values)))
    bars = ax.barh(positions, values, color=color, edgecolor="#2f3c4a", linewidth=0.6)
    ax.set_yticks(positions)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(True, axis="x", linestyle=":", linewidth=0.6, alpha=0.8)
    ax.margins(x=0.12)

    max_value = max(values)
    offset = max(max_value * 0.012, 0.25)
    for bar, value in zip(bars, values):
        ax.text(
            value + offset,
            bar.get_y() + bar.get_height() / 2.0,
            f"{value:.2f}".rstrip("0").rstrip("."),
            va="center",
            ha="left",
            fontsize=9,
            color="#263445",
        )

    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return True


def plot_figures(output_dir: Path, aggregate_rows: Sequence[Dict[str, str]]) -> List[Path]:
    try:
        os.environ.setdefault("MPLCONFIGDIR", "/tmp/virtual_ecu_mpl")
        import matplotlib.pyplot as plt
    except ImportError:
        return []

    os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    bar_figures = [
        (
            "max_coolant_temp_c",
            "Maximum Coolant Temperature by Scenario",
            "Maximum Coolant Temperature [C]",
            figures_dir / "max_coolant_by_scenario.png",
            "#d67a56",
        ),
        (
            "safe_state_duration_s",
            "Safe-State Duration by Scenario",
            "Safe-State Duration [s]",
            figures_dir / "safe_state_duration_by_scenario.png",
            "#4f8f8a",
        ),
        (
            "detection_latency_s",
            "Detection Latency by Scenario",
            "Detection Latency [s]",
            figures_dir / "detection_latency_by_scenario.png",
            "#4c78a8",
        ),
    ]
    for column, title, xlabel, path, color in bar_figures:
        if plot_scenario_bar(plt, aggregate_rows, column, title, xlabel, path, color):
            written.append(path)

    series = []
    for row in aggregate_rows:
        raw_path = PROJECT_ROOT / row["raw_csv_path"]
        rows = read_csv_rows(raw_path)
        series.append((row, rows))

    fig, ax = plt.subplots(figsize=(9.2, 5.0), constrained_layout=True)
    for row, rows in series:
        ax.plot(
            [parse_float(item, "time_s") for item in rows],
            [parse_float(item, "coolant_temp_true_c") for item in rows],
            linewidth=1.8,
            label=row["scenario_id"],
        )
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Coolant Temperature [C]")
    ax.set_title("Paper Study v1 Coolant Temperature")
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.8)
    ax.legend(loc="upper left", fontsize=8, ncol=2, frameon=False)
    path = figures_dir / "coolant_temperature_by_scenario.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    written.append(path)

    fig, ax = plt.subplots(figsize=(9.2, 4.8), constrained_layout=True)
    for row, rows in series:
        ax.step(
            [parse_float(item, "time_s") for item in rows],
            [parse_int(item, "safe_state_id") for item in rows],
            where="post",
            linewidth=1.8,
            label=row["scenario_id"],
        )
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Safe State ID")
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(["Normal", "Precautionary", "Limp Home", "Shutdown"])
    ax.set_title("Paper Study v1 Safe-State Timeline")
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.8)
    ax.legend(loc="upper left", fontsize=8, ncol=2, frameon=False)
    path = figures_dir / "safe_state_timeline_by_scenario.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    written.append(path)

    by_id = {row["scenario_id"]: rows for row, rows in series}
    if "baseline" in by_id and "fan_stuck_hot_stress" in by_id:
        fig, axes = plt.subplots(2, 1, figsize=(9.2, 6.2), sharex=True, constrained_layout=True)
        for scenario_id, rows in (("baseline", by_id["baseline"]), ("fan_stuck_hot_stress", by_id["fan_stuck_hot_stress"])):
            axes[0].plot(
                [parse_float(item, "time_s") for item in rows],
                [parse_float(item, "coolant_temp_true_c") for item in rows],
                linewidth=2.0,
                label=scenario_id,
            )
        fan_rows = by_id["fan_stuck_hot_stress"]
        axes[1].plot(
            [parse_float(item, "time_s") for item in fan_rows],
            [parse_float(item, "fan_command") for item in fan_rows],
            linewidth=2.0,
            label="fan command",
        )
        axes[1].plot(
            [parse_float(item, "time_s") for item in fan_rows],
            [parse_float(item, "fan_actual") for item in fan_rows],
            linewidth=1.8,
            linestyle="--",
            label="fan actual",
        )
        axes[0].set_ylabel("Coolant [C]")
        axes[1].set_ylabel("Fan [-]")
        axes[1].set_xlabel("Time [s]")
        axes[0].set_title("Baseline vs Fan Hot Stress")
        for axis in axes:
            axis.grid(True, linestyle=":", linewidth=0.6, alpha=0.8)
            axis.legend(loc="upper left", frameon=False)
        path = figures_dir / "baseline_vs_fan_hot_stress.png"
        fig.savefig(path, dpi=200)
        plt.close(fig)
        written.append(path)

    return written


def copy_existing_batch_reference(output_dir: Path) -> None:
    """Copy existing batch aggregate as a non-authoritative reference if present."""
    source = PROJECT_ROOT / "results" / "batch" / "paper_quick" / "aggregate_summary.csv"
    if not source.exists():
        return
    target_dir = output_dir / "raw"
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target_dir / "existing_batch_paper_quick_aggregate_summary.csv")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "raw").mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(parents=True, exist_ok=True)

    if not args.skip_run:
        executable = detect_executable(args.executable)
        run_scenarios(executable, output_dir)

    aggregate_rows = build_aggregate(output_dir)
    taxonomy_rows = build_taxonomy_rows(aggregate_rows)

    write_csv(output_dir / "aggregate_summary.csv", AGGREGATE_COLUMNS, aggregate_rows)
    write_csv(output_dir / "fault_taxonomy_table.csv", TAXONOMY_COLUMNS, taxonomy_rows)
    write_representative_comparison(output_dir, aggregate_rows)
    write_claim_summary(output_dir, aggregate_rows)
    copy_existing_batch_reference(output_dir)
    figures_written = plot_figures(output_dir, aggregate_rows)
    write_readme(output_dir, aggregate_rows, figures_written)
    report_path = write_html_report(output_dir)

    print(f"Wrote Paper Study v1 package to {relative_to_project(output_dir)}")
    print(f"  - {relative_to_project(report_path)}")
    print(f"  - {relative_to_project(output_dir / 'README.md')}")
    print(f"  - {relative_to_project(output_dir / 'aggregate_summary.csv')}")
    print(f"  - {relative_to_project(output_dir / 'fault_taxonomy_table.csv')}")
    print(f"  - {relative_to_project(output_dir / 'representative_comparison_summary.md')}")
    print(f"  - {relative_to_project(output_dir / 'claim_summary.md')}")
    print(f"  - {relative_to_project(output_dir / 'raw')}")
    print(f"  - {relative_to_project(output_dir / 'figures')}")


if __name__ == "__main__":
    main()
