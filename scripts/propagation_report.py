#!/usr/bin/env python3
"""Helpers for cross-layer propagation timelines and reports."""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Dict, List, Sequence

os.environ.setdefault("MPLCONFIGDIR", "/tmp/virtual_ecu_mpl")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch


LANE_ORDER = (
    "hardware_origin",
    "ecu_manifestation",
    "diagnostic_effect",
    "system_effect",
)
LANE_LABELS = {
    "hardware_origin": "1. Hardware-Origin Fault",
    "ecu_manifestation": "2. ECU Manifestation",
    "diagnostic_effect": "3. Diagnostic Effect",
    "system_effect": "4. Safe-State / System Effect",
}
LANE_SHORT_LABELS = {
    "hardware_origin": "Hardware",
    "ecu_manifestation": "ECU",
    "diagnostic_effect": "Diagnostics",
    "system_effect": "System",
}
RUN_STYLES = (
    {"color": "#c4473a", "marker": "o", "linestyle": "-", "offset": 0.14},
    {"color": "#1f5aa6", "marker": "D", "linestyle": "--", "offset": -0.14},
)

CAMPAIGN_STORIES = {
    "fan_stuck_hot_stress": {
        "headline": "Strong actuation-path demo: a fan power-stage fault becomes immediate tracking loss, then drives thermal stress and limp-home protection.",
        "hardware_origin": "Permanent fan gate-driver or power-stage stuck-off fault under hot, low-airflow conditions.",
        "ecu_manifestation": "The ECU requests fan actuation, but realized fan response stays unavailable, creating a clear actuator-tracking mismatch.",
        "diagnostic_effect": "Fan-tracking evidence appears almost immediately because commanded and realized fan behavior diverge sharply.",
        "system_effect": "Protection escalates quickly and the run later develops clear thermal stress, making the cross-layer story easy to explain in demos.",
    },
    "stale_sensor_data_hot_stress": {
        "headline": "Strong timing/communication demo: stale sampled data turns a refresh-delay fault into visible thermal and safety escalation.",
        "hardware_origin": "Persistent sensor-to-ECU timing or communication refresh delay that leaves the controller operating on aged coolant data.",
        "ecu_manifestation": "The ECU acts on stale coolant measurements, so cooling demand lags behind the true thermal state during the stressed phase.",
        "diagnostic_effect": "Sensor-rationality and cooling-performance evidence appear once the stale measurement lag grows large enough to distort control behavior.",
        "system_effect": "Delayed cooling action produces warning-level thermal stress and safe-state escalation, making the timing fault research-visible.",
    },
    "calibration_memory_corruption": {
        "headline": "Strong computation/memory demo: corrupted calibration shifts controller behavior before thermal and safety consequences become visible.",
        "hardware_origin": "Corrupted calibration register or nonvolatile memory bit upset affecting the cooling-control target.",
        "ecu_manifestation": "The ECU continues with a delayed cooling request even though measured temperatures are correct, because the internal target is shifted.",
        "diagnostic_effect": "Thermal and cooling-performance evidence appears later than in direct actuation faults because the error begins inside control computation.",
        "system_effect": "Coolant temperature rises higher than nominal and protection eventually escalates, illustrating delayed cross-layer propagation.",
    },
    "paper_default": {
        "headline": "Mixed-fault demo: sensing, actuation, and safety effects appear in a staged chain that is useful for thesis walkthroughs.",
        "hardware_origin": "Sequential sensing-path, pump-actuation, and fan power-stage faults representing a multi-stage cross-layer failure story.",
        "ecu_manifestation": "The ECU first sees biased sensing, then reduced pump authority, then loss of realized fan actuation.",
        "diagnostic_effect": "Diagnostic evidence evolves from sensor-rationality to pump-tracking and fan-tracking behavior as the fault chain progresses.",
        "system_effect": "Protection responds in stages, making the run well suited for explaining progressive propagation across layers.",
    },
}


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def int_value(row: Dict[str, str], key: str) -> int:
    return int(float(row.get(key, "0") or 0))


def float_value(row: Dict[str, str], key: str) -> float:
    return float(row.get(key, "0") or 0.0)


def humanize_label(value: str) -> str:
    return value.replace("_", " ")


def compact_label(value: str) -> str:
    text = humanize_label(value)
    text = text.replace("coolant ", "")
    text = text.replace("sensor ", "")
    text = text.replace("tracking ", "")
    text = text.replace("requested", "request")
    text = text.replace("overtemperature ", "")
    return text


def _phase_label(row: Dict[str, str]) -> str:
    return row.get("phase_label", "unknown")


def _event_record(
    row: Dict[str, str],
    lane: str,
    label: str,
    short_label: str,
    detail: str,
    *,
    signal: str,
    effect_subtype: str,
) -> Dict[str, object]:
    return {
        "lane": lane,
        "lane_label": LANE_LABELS[lane],
        "label": label,
        "short_label": short_label,
        "time_ms": int_value(row, "time_ms"),
        "time_s": float_value(row, "time_s"),
        "phase_label": _phase_label(row),
        "signal": signal,
        "effect_subtype": effect_subtype,
        "detail": detail,
    }


def _fallback_story(first_mode_label: str) -> Dict[str, str]:
    readable_mode = humanize_label(first_mode_label) if first_mode_label else "fault"
    return {
        "headline": f"Cross-layer demo: {readable_mode} is followed from injected hardware-origin fault to ECU and system effect.",
        "hardware_origin": f"Injected hardware-origin {readable_mode} fault.",
        "ecu_manifestation": f"The ECU experiences a visible {readable_mode} manifestation at its interfaces or internal control path.",
        "diagnostic_effect": "Diagnostic evidence appears once the ECU-visible manifestation becomes strong enough to trigger monitoring logic.",
        "system_effect": "Thermal or safety consequences emerge if the ECU manifestation persists long enough to influence control behavior.",
    }


def campaign_story(campaign_id: str, first_mode_label: str) -> Dict[str, str]:
    return CAMPAIGN_STORIES.get(campaign_id, _fallback_story(first_mode_label))


def fault_intervals(rows: Sequence[Dict[str, str]]) -> List[Dict[str, object]]:
    if not rows:
        return []

    intervals: List[Dict[str, object]] = []
    active: Dict[str, object] | None = None
    active_index: int | None = None
    last_time_ms = int_value(rows[-1], "time_ms")
    last_time_s = float_value(rows[-1], "time_s")
    last_phase = _phase_label(rows[-1])

    for row in rows:
        current_index = int_value(row, "active_event_index")
        time_ms = int_value(row, "time_ms")
        time_s = float_value(row, "time_s")

        if current_index != active_index:
            if active is not None:
                active["end_ms"] = time_ms
                active["end_s"] = time_s
                active["end_phase_label"] = _phase_label(row)
                intervals.append(active)
                active = None

            if current_index >= 0:
                mode_label = row.get("fault_mode_label", "none")
                behavior_label = row.get("fault_behavior_label", "none")
                parameter = float_value(row, "active_fault_parameter")
                active = {
                    "lane": "hardware_origin",
                    "lane_label": LANE_LABELS["hardware_origin"],
                    "mode_label": mode_label,
                    "behavior_label": behavior_label,
                    "parameter": parameter,
                    "label": f"{humanize_label(mode_label)} ({behavior_label})",
                    "short_label": compact_label(mode_label),
                    "signal": "fault injection schedule",
                    "effect_subtype": "fault_activation",
                    "detail": f"{behavior_label} fault active, parameter={parameter:.3f}",
                    "start_ms": time_ms,
                    "end_ms": time_ms,
                    "start_s": time_s,
                    "end_s": time_s,
                    "start_phase_label": _phase_label(row),
                    "end_phase_label": _phase_label(row),
                }

            active_index = current_index

    if active is not None:
        active["end_ms"] = last_time_ms
        active["end_s"] = last_time_s
        active["end_phase_label"] = last_phase
        intervals.append(active)

    return intervals


def _first_row_after(
    rows: Sequence[Dict[str, str]],
    start_ms: int,
    predicate,
) -> Dict[str, str] | None:
    for row in rows:
        if int_value(row, "time_ms") < start_ms:
            continue
        if predicate(row):
            return row
    return None


def _manifestation_event_for_interval(
    rows: Sequence[Dict[str, str]],
    interval: Dict[str, object],
) -> Dict[str, object]:
    mode_label = str(interval["mode_label"])
    start_ms = int(interval["start_ms"])
    start_row = _first_row_after(rows, start_ms, lambda row: int_value(row, "time_ms") == start_ms) or rows[0]

    if mode_label == "sensor_bias":
        row = _first_row_after(
            rows,
            start_ms,
            lambda current: abs(float_value(current, "coolant_sensor_residual_c")) >= max(2.0, float(interval["parameter"]) * 0.3),
        ) or start_row
        residual = float_value(row, "coolant_sensor_residual_c")
        return _event_record(
            row,
            "ecu_manifestation",
            "Biased coolant measurement visible at ECU input",
            "biased measurement",
            f"Coolant measurement residual reached {residual:.2f} C.",
            signal="coolant_sensor_residual_c",
            effect_subtype="measurement_bias",
        )

    if mode_label == "sensor_interface_intermittent":
        row = _first_row_after(
            rows,
            start_ms,
            lambda current: abs(float_value(current, "coolant_sensor_residual_c")) >= max(2.0, float(interval["parameter"]) * 0.35),
        ) or start_row
        residual = float_value(row, "coolant_sensor_residual_c")
        return _event_record(
            row,
            "ecu_manifestation",
            "Intermittent coolant-reading disturbance reaches ECU",
            "reading glitch",
            f"Bursty coolant residual reached {residual:.2f} C.",
            signal="coolant_sensor_residual_c",
            effect_subtype="measurement_glitch",
        )

    if mode_label == "stale_sensor_data":
        row = _first_row_after(
            rows,
            start_ms,
            lambda current: abs(float_value(current, "coolant_sensor_residual_c")) >= 2.0,
        ) or start_row
        measured = float_value(row, "coolant_temp_meas_c")
        true_temp = float_value(row, "coolant_temp_true_c")
        return _event_record(
            row,
            "ecu_manifestation",
            "Aged coolant sample drives ECU control decisions",
            "aged coolant data",
            f"Measured coolant was {measured:.2f} C while true coolant was {true_temp:.2f} C.",
            signal="coolant_temp_meas_c vs coolant_temp_true_c",
            effect_subtype="stale_data",
        )

    if mode_label == "pump_degraded":
        row = _first_row_after(
            rows,
            start_ms,
            lambda current: float_value(current, "pump_tracking_error") >= 0.20,
        ) or start_row
        error = float_value(row, "pump_tracking_error")
        return _event_record(
            row,
            "ecu_manifestation",
            "Pump response falls below ECU command",
            "pump mismatch",
            f"Pump tracking error reached {error:.3f}.",
            signal="pump_tracking_error",
            effect_subtype="actuator_tracking_mismatch",
        )

    if mode_label == "fan_stuck_off":
        row = _first_row_after(
            rows,
            start_ms,
            lambda current: float_value(current, "fan_command") >= 0.20 and float_value(current, "fan_tracking_error") >= 0.20,
        ) or start_row
        return _event_record(
            row,
            "ecu_manifestation",
            "Fan command remains high while realized fan stays unavailable",
            "fan mismatch",
            f"Fan command was {float_value(row, 'fan_command'):.3f} while fan actual was {float_value(row, 'fan_actual'):.3f}.",
            signal="fan_command vs fan_actual",
            effect_subtype="actuator_tracking_mismatch",
        )

    if mode_label == "calibration_memory_corruption":
        row = _first_row_after(
            rows,
            start_ms,
            lambda current: (
                float_value(current, "coolant_temp_true_c") >= 95.0
                and (float_value(current, "pump_command") <= 0.60 or float_value(current, "fan_command") <= 0.15)
            ),
        ) or start_row
        return _event_record(
            row,
            "ecu_manifestation",
            "Cooling request remains delayed despite rising temperature",
            "delayed cooling request",
            (
                f"Coolant reached {float_value(row, 'coolant_temp_true_c'):.2f} C while "
                f"pump command was {float_value(row, 'pump_command'):.3f} and fan command was {float_value(row, 'fan_command'):.3f}."
            ),
            signal="pump_command / fan_command",
            effect_subtype="control_target_shift",
        )

    return _event_record(
        start_row,
        "ecu_manifestation",
        "ECU-visible fault manifestation becomes active",
        compact_label(mode_label),
        f"The injected {humanize_label(mode_label)} fault became ECU-visible.",
        signal="campaign fault activation",
        effect_subtype="generic_manifestation",
    )


def ecu_manifestation_events(
    rows: Sequence[Dict[str, str]],
    intervals: Sequence[Dict[str, object]],
) -> List[Dict[str, object]]:
    return [_manifestation_event_for_interval(rows, interval) for interval in intervals]


def diagnostic_events(rows: Sequence[Dict[str, str]]) -> List[Dict[str, object]]:
    events: List[Dict[str, object]] = []
    seen_labels: set[str] = set()

    for row in rows:
        current_label = row.get("primary_dtc_label", "none")
        if current_label == "none" or current_label in seen_labels:
            continue

        seen_labels.add(current_label)
        events.append(
            _event_record(
                row,
                "diagnostic_effect",
                f"Primary DTC: {humanize_label(current_label)}",
                compact_label(current_label),
                f"Primary diagnostic evidence first appears as {humanize_label(current_label)}.",
                signal="primary_dtc_label",
                effect_subtype="primary_dtc",
            )
        )

    return events


def thermal_and_safety_events(rows: Sequence[Dict[str, str]]) -> List[Dict[str, object]]:
    events: List[Dict[str, object]] = []
    seen_safe_states: set[str] = set()
    warning_seen = False
    critical_seen = False
    shutdown_seen = False

    for row in rows:
        if not warning_seen and int_value(row, "overtemp_warning") != 0:
            warning_seen = True
            events.append(
                _event_record(
                    row,
                    "system_effect",
                    "Thermal warning threshold crossed",
                    "thermal warning",
                    "Coolant temperature crossed the warning threshold.",
                    signal="overtemp_warning",
                    effect_subtype="thermal_warning",
                )
            )

        if not critical_seen and int_value(row, "overtemp_critical") != 0:
            critical_seen = True
            events.append(
                _event_record(
                    row,
                    "system_effect",
                    "Thermal critical threshold crossed",
                    "thermal critical",
                    "Coolant temperature crossed the critical threshold.",
                    signal="overtemp_critical",
                    effect_subtype="thermal_critical",
                )
            )

        safe_state = row.get("safe_state_label", "normal")
        if safe_state != "normal" and safe_state not in seen_safe_states:
            seen_safe_states.add(safe_state)
            events.append(
                _event_record(
                    row,
                    "system_effect",
                    f"Safe state: {humanize_label(safe_state)}",
                    compact_label(safe_state),
                    f"Protection escalated into {humanize_label(safe_state)}.",
                    signal="safe_state_label",
                    effect_subtype="safe_state",
                )
            )

        if not shutdown_seen and int_value(row, "shutdown_requested") != 0:
            shutdown_seen = True
            events.append(
                _event_record(
                    row,
                    "system_effect",
                    "Shutdown request asserted",
                    "shutdown request",
                    "Controlled-shutdown intent became active.",
                    signal="shutdown_requested",
                    effect_subtype="shutdown_request",
                )
            )

    if rows:
        peak_row = max(rows, key=lambda row: float_value(row, "coolant_temp_true_c"))
        peak_temp_c = float_value(peak_row, "coolant_temp_true_c")
        events.append(
            _event_record(
                peak_row,
                "system_effect",
                f"Peak coolant temperature: {peak_temp_c:.1f} C",
                f"peak {peak_temp_c:.1f} C",
                f"Maximum true coolant temperature reached {peak_temp_c:.2f} C.",
                signal="coolant_temp_true_c",
                effect_subtype="peak_temperature",
            )
        )

    return events


def _first_event(events: Sequence[Dict[str, object]], lane: str) -> Dict[str, object] | None:
    for event in events:
        if event["lane"] == lane:
            return event
    return None


def _first_effect_event(events: Sequence[Dict[str, object]], subtype: str) -> Dict[str, object] | None:
    for event in events:
        if event.get("effect_subtype") == subtype:
            return event
    return None


def _first_fault_start(intervals: Sequence[Dict[str, object]]) -> float | None:
    if not intervals:
        return None
    return min(float(interval["start_s"]) for interval in intervals)


def _format_time(time_s: float | None) -> str:
    return "n/a" if time_s is None else f"{time_s:.1f} s"


def _format_latency(reference_s: float | None, time_s: float | None) -> str:
    if reference_s is None or time_s is None:
        return "n/a"
    return f"{time_s - reference_s:.1f} s"


def _timeline_items(
    intervals: Sequence[Dict[str, object]],
    events: Sequence[Dict[str, object]],
) -> List[Dict[str, object]]:
    items: List[Dict[str, object]] = []

    for interval in intervals:
        items.append(
            {
                "item_type": "interval",
                "lane": interval["lane"],
                "lane_label": interval["lane_label"],
                "summary": interval["label"],
                "short_label": interval["short_label"],
                "time_ms": interval["start_ms"],
                "time_s": interval["start_s"],
                "start_ms": interval["start_ms"],
                "start_s": interval["start_s"],
                "end_ms": interval["end_ms"],
                "end_s": interval["end_s"],
                "phase_label": interval["start_phase_label"],
                "signal": interval["signal"],
                "effect_subtype": interval["effect_subtype"],
                "detail": interval["detail"],
            }
        )

    for event in events:
        items.append(
            {
                "item_type": "event",
                "lane": event["lane"],
                "lane_label": event["lane_label"],
                "summary": event["label"],
                "short_label": event["short_label"],
                "time_ms": event["time_ms"],
                "time_s": event["time_s"],
                "start_ms": "",
                "start_s": "",
                "end_ms": "",
                "end_s": "",
                "phase_label": event["phase_label"],
                "signal": event["signal"],
                "effect_subtype": event["effect_subtype"],
                "detail": event["detail"],
            }
        )

    items.sort(key=lambda item: (float(item["time_s"]), LANE_ORDER.index(str(item["lane"]))))

    for index, item in enumerate(items, start=1):
        item["sequence_index"] = index

    return items


def propagation_chain(report: Dict[str, object]) -> List[Dict[str, object]]:
    story = report["story"]  # type: ignore[assignment]
    intervals = report["fault_intervals"]  # type: ignore[assignment]
    events = report["events"]  # type: ignore[assignment]

    first_fault = intervals[0] if intervals else None
    first_ecu = _first_event(events, "ecu_manifestation")
    first_diag = _first_event(events, "diagnostic_effect")
    first_system = _first_event(events, "system_effect")

    peak_event = _first_effect_event(events, "peak_temperature")
    warning_event = _first_effect_event(events, "thermal_warning")
    first_safe_state = _first_effect_event(events, "safe_state")
    first_fault_start_s = _first_fault_start(intervals)

    chain = [
        {
            "stage_order": 1,
            "chain_stage": "hardware_origin",
            "stage_label": LANE_LABELS["hardware_origin"],
            "story_text": story["hardware_origin"],
            "evidence_label": first_fault["label"] if first_fault is not None else "No injected fault interval",
            "evidence_time_s": float(first_fault["start_s"]) if first_fault is not None else None,
            "evidence_phase_label": first_fault["start_phase_label"] if first_fault is not None else "n/a",
            "evidence_detail": first_fault["detail"] if first_fault is not None else "No fault interval was recorded.",
        },
        {
            "stage_order": 2,
            "chain_stage": "ecu_manifestation",
            "stage_label": LANE_LABELS["ecu_manifestation"],
            "story_text": story["ecu_manifestation"],
            "evidence_label": first_ecu["label"] if first_ecu is not None else "No explicit ECU manifestation extracted",
            "evidence_time_s": float(first_ecu["time_s"]) if first_ecu is not None else None,
            "evidence_phase_label": first_ecu["phase_label"] if first_ecu is not None else "n/a",
            "evidence_detail": first_ecu["detail"] if first_ecu is not None else "The report did not detect a separate ECU-manifestation milestone.",
        },
        {
            "stage_order": 3,
            "chain_stage": "diagnostic_effect",
            "stage_label": LANE_LABELS["diagnostic_effect"],
            "story_text": story["diagnostic_effect"],
            "evidence_label": first_diag["label"] if first_diag is not None else "No diagnostic evidence",
            "evidence_time_s": float(first_diag["time_s"]) if first_diag is not None else None,
            "evidence_phase_label": first_diag["phase_label"] if first_diag is not None else "n/a",
            "evidence_detail": first_diag["detail"] if first_diag is not None else "No primary DTC became active in this run.",
        },
        {
            "stage_order": 4,
            "chain_stage": "system_effect",
            "stage_label": LANE_LABELS["system_effect"],
            "story_text": story["system_effect"],
            "evidence_label": first_system["label"] if first_system is not None else "No safe-state/system effect",
            "evidence_time_s": float(first_system["time_s"]) if first_system is not None else None,
            "evidence_phase_label": first_system["phase_label"] if first_system is not None else "n/a",
            "evidence_detail": first_system["detail"] if first_system is not None else "No non-nominal system-effect milestone was extracted.",
        },
    ]

    timings = [
        ("First injected fault", first_fault_start_s),
        ("First ECU manifestation", float(first_ecu["time_s"]) if first_ecu is not None else None),
        ("First diagnostic effect", float(first_diag["time_s"]) if first_diag is not None else None),
        ("First thermal warning", float(warning_event["time_s"]) if warning_event is not None else None),
        ("First safe-state escalation", float(first_safe_state["time_s"]) if first_safe_state is not None else None),
        ("Peak coolant temperature", float(peak_event["time_s"]) if peak_event is not None else None),
    ]

    report["key_timings"] = [
        {
            "label": label,
            "time_s": time_s,
            "latency_from_fault_s": None if label == "First injected fault" else (
                None if first_fault_start_s is None or time_s is None else time_s - first_fault_start_s
            ),
        }
        for label, time_s in timings
    ]

    return chain


def build_propagation_report(rows: Sequence[Dict[str, str]]) -> Dict[str, object]:
    if not rows:
        raise ValueError("Propagation reports require at least one CSV row.")

    intervals = fault_intervals(rows)
    ecu_events = ecu_manifestation_events(rows, intervals)
    diag_events = diagnostic_events(rows)
    system_events = thermal_and_safety_events(rows)
    events = ecu_events + diag_events + system_events
    events.sort(key=lambda event: (float(event["time_s"]), LANE_ORDER.index(str(event["lane"]))))

    first_mode_label = str(intervals[0]["mode_label"]) if intervals else "none"
    report = {
        "campaign_id": rows[0].get("campaign_id", ""),
        "campaign_label": rows[0].get("campaign_label", ""),
        "duration_ms": int_value(rows[-1], "time_ms"),
        "duration_s": float_value(rows[-1], "time_s"),
        "story": campaign_story(rows[0].get("campaign_id", ""), first_mode_label),
        "fault_intervals": intervals,
        "events": events,
        "timeline_items": _timeline_items(intervals, events),
    }
    report["chain"] = propagation_chain(report)
    return report


def propagation_summary_lines(report: Dict[str, object]) -> List[str]:
    lines: List[str] = []
    chain = report["chain"]  # type: ignore[assignment]

    for step in chain:
        lines.append(
            f"{step['stage_label']}: {step['story_text']} Evidence: {step['evidence_label']} at {_format_time(step['evidence_time_s'])}."
        )

    return lines


def propagation_csv_rows(side: str, report: Dict[str, object]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    first_fault_start_s = _first_fault_start(report["fault_intervals"])  # type: ignore[index]

    for step in report["chain"]:  # type: ignore[index]
        evidence_time_s = step["evidence_time_s"]
        rows.append(
            {
                "side": side,
                "campaign_id": str(report["campaign_id"]),
                "campaign_label": str(report["campaign_label"]),
                "row_type": "chain_stage",
                "order_index": str(step["stage_order"]),
                "chain_stage": str(step["chain_stage"]),
                "chain_stage_label": str(step["stage_label"]),
                "summary": str(step["story_text"]),
                "evidence_label": str(step["evidence_label"]),
                "evidence_time_s": "" if evidence_time_s is None else f"{float(evidence_time_s):.3f}",
                "latency_from_first_fault_s": "" if first_fault_start_s is None or evidence_time_s is None else f"{float(evidence_time_s) - first_fault_start_s:.3f}",
                "start_s": "",
                "end_s": "",
                "phase_label": str(step["evidence_phase_label"]),
                "signal": "",
                "effect_subtype": "",
                "detail": str(step["evidence_detail"]),
            }
        )

    for item in report["timeline_items"]:  # type: ignore[index]
        time_s = float(item["time_s"])
        rows.append(
            {
                "side": side,
                "campaign_id": str(report["campaign_id"]),
                "campaign_label": str(report["campaign_label"]),
                "row_type": "timeline_item",
                "order_index": str(item["sequence_index"]),
                "chain_stage": str(item["lane"]),
                "chain_stage_label": str(item["lane_label"]),
                "summary": str(item["summary"]),
                "evidence_label": str(item["short_label"]),
                "evidence_time_s": f"{time_s:.3f}",
                "latency_from_first_fault_s": "" if first_fault_start_s is None else f"{time_s - first_fault_start_s:.3f}",
                "start_s": "" if item["start_s"] == "" else f"{float(item['start_s']):.3f}",
                "end_s": "" if item["end_s"] == "" else f"{float(item['end_s']):.3f}",
                "phase_label": str(item["phase_label"]),
                "signal": str(item["signal"]),
                "effect_subtype": str(item["effect_subtype"]),
                "detail": str(item["detail"]),
            }
        )

    return rows


def write_propagation_csv(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    columns = [
        "side",
        "campaign_id",
        "campaign_label",
        "row_type",
        "order_index",
        "chain_stage",
        "chain_stage_label",
        "summary",
        "evidence_label",
        "evidence_time_s",
        "latency_from_first_fault_s",
        "start_s",
        "end_s",
        "phase_label",
        "signal",
        "effect_subtype",
        "detail",
    ]

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_propagation_summary(
    path: Path,
    reports: Sequence[Dict[str, object]],
    labels: Sequence[str],
) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write("Cross-Layer Propagation Report\n")
        handle.write("=============================\n\n")

        for label, report in zip(labels, reports):
            story = report["story"]  # type: ignore[assignment]
            handle.write(f"{label}\n")
            handle.write(f"{'-' * len(label)}\n")
            handle.write(f"Campaign ID: {report['campaign_id']}\n")
            handle.write(f"Duration: {float(report['duration_s']):.1f} s\n\n")
            handle.write(f"Research framing: {story['headline']}\n\n")

            handle.write("Propagation Chain\n")
            handle.write("-----------------\n")
            for step in report["chain"]:  # type: ignore[index]
                handle.write(f"{step['stage_label']}\n")
                handle.write(f"   Story: {step['story_text']}\n")
                handle.write(f"   Evidence: {step['evidence_label']} at {_format_time(step['evidence_time_s'])}")
                if step["evidence_phase_label"] not in {"", "n/a", "unknown"}:
                    handle.write(f" during {humanize_label(str(step['evidence_phase_label']))}")
                handle.write("\n")
                handle.write(f"   Detail: {step['evidence_detail']}\n")
            handle.write("\n")

            handle.write("Key Timings\n")
            handle.write("-----------\n")
            for timing in report["key_timings"]:  # type: ignore[index]
                handle.write(
                    f"- {timing['label']}: {_format_time(timing['time_s'])} "
                    f"(latency from first fault: {_format_latency(_first_fault_start(report['fault_intervals']), timing['time_s'])})\n"
                )
            handle.write("\n")

            handle.write("Chronological Milestones\n")
            handle.write("------------------------\n")
            for item in report["timeline_items"]:  # type: ignore[index]
                phase_text = str(item["phase_label"])
                handle.write(
                    f"- [{item['lane_label']}] {item['summary']} at {float(item['time_s']):.1f} s"
                )
                if phase_text not in {"", "unknown"}:
                    handle.write(f" during {humanize_label(phase_text)}")
                if item["item_type"] == "interval":
                    handle.write(f" (active until {float(item['end_s']):.1f} s)")
                handle.write("\n")
            handle.write("\n")


def save_propagation_plot(
    labels: Sequence[str],
    reports: Sequence[Dict[str, object]],
    output_path: Path,
    *,
    title: str = "Cross-Layer Propagation Timeline",
) -> None:
    if not reports:
        raise ValueError("At least one propagation report is required for plotting.")

    fig, ax = plt.subplots(figsize=(11.6, 6.2), constrained_layout=True)
    lane_positions = {lane: len(LANE_ORDER) - 1 - index for index, lane in enumerate(LANE_ORDER)}
    max_time_s = max(
        [float(report["duration_s"]) for report in reports]
        + [
            float(item["end_s"])
            for report in reports
            for item in report["timeline_items"]  # type: ignore[index]
            if item["item_type"] == "interval"
        ]
        + [
            float(item["time_s"])
            for report in reports
            for item in report["timeline_items"]  # type: ignore[index]
        ]
    )

    box_colors = {
        "hardware_origin": "#f6e6e2",
        "ecu_manifestation": "#eef4fb",
        "diagnostic_effect": "#f6f0dd",
        "system_effect": "#edf6ee",
    }

    for lane, position in lane_positions.items():
        ax.axhspan(position - 0.42, position + 0.42, color=box_colors[lane], alpha=0.95, zorder=0)
        ax.axhline(position, color="#cad6df", linewidth=0.8, linestyle=":")
        ax.text(-1.3, position, LANE_LABELS[lane], va="center", ha="right", color="#2f3f4e", fontsize=10, fontweight="bold")

    arrow = FancyArrowPatch(
        (-0.35, lane_positions["hardware_origin"] - 0.25),
        (-0.35, lane_positions["system_effect"] + 0.25),
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=1.2,
        color="#7b8b99",
    )
    ax.add_patch(arrow)
    ax.text(
        -0.55,
        1.5,
        "Propagation direction",
        rotation=90,
        va="center",
        ha="center",
        fontsize=9,
        color="#607180",
    )

    legend_handles = []
    for index, (label, report) in enumerate(zip(labels, reports)):
        style = RUN_STYLES[min(index, len(RUN_STYLES) - 1)]
        y_offset = style["offset"]
        color = str(style["color"])

        for item_index, item in enumerate(report["timeline_items"]):  # type: ignore[index]
            y_pos = lane_positions[str(item["lane"])] + y_offset

            if item["item_type"] == "interval":
                start_s = float(item["start_s"])
                end_s = float(item["end_s"])
                midpoint = start_s + (end_s - start_s) / 2.0
                ax.hlines(y_pos, start_s, end_s, color=color, linewidth=6.0, alpha=0.88, zorder=3)
                ax.scatter([start_s, end_s], [y_pos, y_pos], color=color, s=22, zorder=4)
                ax.text(
                    midpoint,
                    y_pos + (0.18 if y_offset > 0 else -0.22),
                    str(item.get("evidence_label", item.get("short_label", item.get("summary", "")))),
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=color,
                    bbox={"boxstyle": "round,pad=0.22", "facecolor": "white", "edgecolor": "none", "alpha": 0.9},
                )
                continue

            time_s = float(item["time_s"])
            label_offset = 0.18 if (item_index % 2 == 0) == (y_offset > 0) else -0.24
            ax.scatter(
                [time_s],
                [y_pos],
                color=color,
                s=58,
                marker=str(style["marker"]),
                zorder=5,
                edgecolors="white",
                linewidths=0.5,
            )
            ax.vlines(time_s, y_pos - 0.08, y_pos + label_offset * 0.72, color=color, linewidth=0.8, alpha=0.8, zorder=4)
            ax.text(
                time_s,
                y_pos + label_offset,
                str(item.get("evidence_label", item.get("short_label", item.get("summary", "")))),
                ha="center",
                va="center",
                fontsize=8,
                color=color,
                bbox={"boxstyle": "round,pad=0.22", "facecolor": "white", "edgecolor": "none", "alpha": 0.92},
            )

        legend_handles.append(
            plt.Line2D(
                [0],
                [0],
                color=color,
                linestyle=str(style["linestyle"]),
                marker=str(style["marker"]),
                linewidth=2.2,
                markersize=6,
                label=label,
            )
        )

    ax.set_xlim(0.0, max(max_time_s, 1.0) * 1.04)
    ax.set_ylim(-0.65, len(LANE_ORDER) - 0.35)
    ax.set_yticks([])
    ax.set_xlabel("Time [s]")
    ax.set_title(title, fontweight="bold")
    ax.grid(True, axis="x", linestyle=":", linewidth=0.7, alpha=0.8)
    ax.text(
        0.0,
        -0.16,
        "Read top-to-bottom as the propagation chain: hardware-origin fault -> ECU manifestation -> diagnostic effect -> safe-state/system effect.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#5b6b79",
    )
    ax.legend(handles=legend_handles, loc="upper left", frameon=False)

    fig.savefig(output_path, dpi=220)
    plt.close(fig)
