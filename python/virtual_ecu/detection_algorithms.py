"""Reusable offline detection algorithms for virtual ECU CSV traces.

The functions in this module are post-processing helpers. They read simulator
CSV logs, extract campaign-event timing, and evaluate either the ECU's own DTC
timing or one of the residual-based offline detectors.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence


SUPPORTED_ALGORITHMS = ("builtin_ecu", "threshold", "ewma", "cusum")
OFFLINE_RESIDUAL_ALGORITHMS = ("threshold", "ewma", "cusum")

RESIDUAL_SIGNALS = (
    "fan_tracking_error",
    "pump_tracking_error",
    "coolant_sensor_residual_c",
)

# Configurable detector parameters. Residual magnitudes are used so both
# positive and negative deviations contribute to the detector score.
THRESHOLD_LIMITS = {
    "fan_tracking_error": 0.25,
    "pump_tracking_error": 0.20,
    "coolant_sensor_residual_c": 2.00,
}

EWMA_ALPHA = 0.20
EWMA_LIMITS = {
    "fan_tracking_error": 0.25,
    "pump_tracking_error": 0.20,
    "coolant_sensor_residual_c": 2.00,
}

# CUSUM accumulates max(0, previous + |residual| - allowance). The decision
# limits control how much sustained evidence is required for each signal.
CUSUM_ALLOWANCES = {
    "fan_tracking_error": 0.05,
    "pump_tracking_error": 0.05,
    "coolant_sensor_residual_c": 0.25,
}
CUSUM_DECISION_LIMITS = {
    "fan_tracking_error": 0.80,
    "pump_tracking_error": 0.80,
    "coolant_sensor_residual_c": 8.00,
}


@dataclass(frozen=True)
class FaultEvent:
    fault_type: str
    start_ms: int


def read_csv_rows(csv_path: Path | str) -> List[Dict[str, str]]:
    path = Path(csv_path)
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No data rows found in {path}")
    return rows


def parse_float(row: Dict[str, str], key: str, default: float = 0.0) -> float:
    text = row.get(key, "")
    return default if text == "" else float(text)


def parse_int(row: Dict[str, str], key: str, default: int = 0) -> int:
    return int(parse_float(row, key, float(default)))


def fault_events(first_row: Dict[str, str]) -> List[FaultEvent]:
    events = []
    event_count = parse_int(first_row, "campaign_event_count")
    for index in range(1, event_count + 1):
        fault_type = first_row.get(f"campaign_event_{index}_mode_label", "none")
        if fault_type in {"", "none"}:
            continue
        events.append(
            FaultEvent(
                fault_type=fault_type,
                start_ms=parse_int(first_row, f"campaign_event_{index}_start_ms"),
            )
        )
    return events


def available_residuals(rows: Sequence[Dict[str, str]]) -> List[str]:
    columns = rows[0].keys()
    return [signal for signal in RESIDUAL_SIGNALS if signal in columns]


def normalized_threshold_score(row: Dict[str, str], signals: Sequence[str]) -> float:
    return max(
        (
            abs(parse_float(row, signal)) / THRESHOLD_LIMITS[signal]
            for signal in signals
        ),
        default=0.0,
    )


def detector_alarms(rows: Sequence[Dict[str, str]], algorithm_name: str) -> List[bool]:
    signals = available_residuals(rows)
    alarms: List[bool] = []

    if algorithm_name == "threshold":
        for row in rows:
            alarms.append(normalized_threshold_score(row, signals) >= 1.0)
        return alarms

    if algorithm_name == "ewma":
        state = {signal: 0.0 for signal in signals}
        for row in rows:
            scores = []
            for signal in signals:
                residual = abs(parse_float(row, signal))
                state[signal] = (
                    EWMA_ALPHA * residual + (1.0 - EWMA_ALPHA) * state[signal]
                )
                scores.append(state[signal] / EWMA_LIMITS[signal])
            alarms.append(max(scores, default=0.0) >= 1.0)
        return alarms

    if algorithm_name == "cusum":
        state = {signal: 0.0 for signal in signals}
        for row in rows:
            scores = []
            for signal in signals:
                residual = abs(parse_float(row, signal))
                state[signal] = max(
                    0.0,
                    state[signal] + residual - CUSUM_ALLOWANCES[signal],
                )
                scores.append(state[signal] / CUSUM_DECISION_LIMITS[signal])
            alarms.append(max(scores, default=0.0) >= 1.0)
        return alarms

    raise ValueError(f"Unknown residual detector: {algorithm_name}")


def count_alarm_episodes(
    rows: Sequence[Dict[str, str]],
    alarms: Sequence[bool],
    end_before_ms: int | None,
) -> int:
    count = 0
    previous_alarm = False
    for row, alarm in zip(rows, alarms):
        if end_before_ms is not None and parse_int(row, "time_ms") >= end_before_ms:
            break
        if alarm and not previous_alarm:
            count += 1
        previous_alarm = alarm
    return count


def first_alarm_time_ms(
    rows: Sequence[Dict[str, str]],
    alarms: Sequence[bool],
    fault_start_ms: int | None,
) -> int | None:
    if fault_start_ms is None:
        return None
    for row, alarm in zip(rows, alarms):
        time_ms = parse_int(row, "time_ms")
        if time_ms >= fault_start_ms and alarm:
            return time_ms
    return None


def dtc_alarms(rows: Sequence[Dict[str, str]]) -> List[bool]:
    return [
        row.get("primary_dtc_label", "none") not in {"", "none"}
        or parse_int(row, "primary_dtc_id") != 0
        for row in rows
    ]


def first_post_fault_dtc(
    rows: Sequence[Dict[str, str]], fault_start_ms: int | None
) -> tuple[str, float | None, float | None]:
    if fault_start_ms is None:
        return "none", None, None
    for row in rows:
        time_ms = parse_int(row, "time_ms")
        if time_ms < fault_start_ms:
            continue
        label = row.get("primary_dtc_label", "none")
        if label not in {"", "none"} or parse_int(row, "primary_dtc_id") != 0:
            return label, time_ms / 1000.0, (time_ms - fault_start_ms) / 1000.0
    return "none", None, None


def evaluate_detection(csv_path: Path | str, algorithm_name: str) -> Dict[str, object]:
    """Evaluate one detection algorithm against a simulator raw CSV trace."""
    if algorithm_name not in SUPPORTED_ALGORITHMS:
        raise ValueError(
            f"Unsupported detection algorithm '{algorithm_name}'. "
            f"Expected one of: {', '.join(SUPPORTED_ALGORITHMS)}"
        )

    path = Path(csv_path)
    rows = read_csv_rows(path)
    first_row = rows[0]
    events = fault_events(first_row)
    fault_start_ms = min((event.start_ms for event in events), default=None)
    fault_type = "+".join(event.fault_type for event in events) if events else "none"
    first_ecu_dtc_label, first_ecu_dtc_s, ecu_dtc_latency_s = first_post_fault_dtc(
        rows, fault_start_ms
    )

    if algorithm_name == "builtin_ecu":
        alarms = dtc_alarms(rows)
        detection_time_ms = (
            int(first_ecu_dtc_s * 1000.0) if first_ecu_dtc_s is not None else None
        )
    else:
        alarms = detector_alarms(rows, algorithm_name)
        detection_time_ms = first_alarm_time_ms(rows, alarms, fault_start_ms)

    false_positive_count = count_alarm_episodes(
        rows,
        alarms,
        end_before_ms=fault_start_ms,
    )
    detected = detection_time_ms is not None

    campaign_id = first_row.get("campaign_id", path.stem)
    scenario_id = first_row.get("scenario_id", "") or campaign_id or path.stem

    return {
        "algorithm": algorithm_name,
        "scenario_id": scenario_id,
        "campaign_id": campaign_id,
        "fault_type": fault_type,
        "fault_start_s": fault_start_ms / 1000.0 if fault_start_ms is not None else None,
        "detected": detected,
        "first_detection_s": (
            detection_time_ms / 1000.0 if detection_time_ms is not None else None
        ),
        "detection_latency_s": (
            (detection_time_ms - fault_start_ms) / 1000.0
            if detection_time_ms is not None and fault_start_ms is not None
            else None
        ),
        "false_positive_count": false_positive_count,
        "missed_detection": bool(events) and not detected,
        "first_ecu_dtc_label": first_ecu_dtc_label,
        "first_ecu_dtc_s": first_ecu_dtc_s,
        "ecu_dtc_latency_s": ecu_dtc_latency_s,
        "final_safe_state": rows[-1].get("safe_state_label", "unknown"),
        "max_coolant_temp_c": max(
            parse_float(row, "coolant_temp_true_c") for row in rows
        ),
    }


def run_detection_algorithm(csv_path: Path | str, algorithm_name: str) -> Dict[str, object]:
    """Alias kept for callers that prefer an imperative function name."""
    return evaluate_detection(csv_path, algorithm_name)
