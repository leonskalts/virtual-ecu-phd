"""Reusable detection reporting for virtual ECU CSV traces.

The module keeps the offline same-trace evaluators and can also report matching
runtime detector results recorded by the C simulator.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence


SUPPORTED_ALGORITHMS = (
    "builtin_ecu",
    "threshold",
    "ewma",
    "cusum",
    "thermal_observer",
    "kalman_filter",
    "adaptive_kalman_filter",
    "hybrid_adaptive_kalman",
)
OFFLINE_RESIDUAL_ALGORITHMS = (
    "threshold",
    "ewma",
    "cusum",
)

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

# The thermal observer predicts one 100 ms coolant step from the nominal
# controller target and a compact healthy thermal model. Sustained positive
# observed-minus-expected heating is accumulated after this allowance.
THERMAL_OBSERVER_TARGET_COOLANT_C = 92.0
THERMAL_OBSERVER_DT_S = 0.1
THERMAL_OBSERVER_MISMATCH_ALLOWANCE_C = 0.015
THERMAL_OBSERVER_DECISION_LIMIT_C = 1.50

# Lightweight scalar Kalman-style observer constants. The prediction mirrors
# the C runtime detector and uses safe defaults when older CSVs lack newer
# campaign metadata columns.
KALMAN_FILTER_PROCESS_NOISE_Q = 0.020
KALMAN_FILTER_MEASUREMENT_NOISE_R = 4.000
KALMAN_FILTER_INITIAL_COVARIANCE = 1.000
KALMAN_FILTER_INNOVATION_THRESHOLD = 3.000
KALMAN_FILTER_ACCUMULATION_ALLOWANCE = 0.060
KALMAN_FILTER_ACCUMULATION_LEAK = 0.985
KALMAN_FILTER_ACCUMULATION_LIMIT = 3.000
ADAPTIVE_KALMAN_THRESHOLD_SCALE_MIN = 0.700
ADAPTIVE_KALMAN_THRESHOLD_SCALE_MAX = 1.200
ADAPTIVE_KALMAN_THRESHOLD_SCALE_LOW_STRESS = 1.150
ADAPTIVE_KALMAN_THRESHOLD_SCALE_RANGE = 0.450
ADAPTIVE_KALMAN_CONTEXT_MULTIPLIER_MAX = 1.180
ADAPTIVE_KALMAN_ACTUATOR_SCORE_WEIGHT = 1.050
ADAPTIVE_KALMAN_TREND_SCORE_WEIGHT = 0.220
ADAPTIVE_KALMAN_TREND_GATE_SCORE = 0.250
ADAPTIVE_KALMAN_STRONG_SCORE = 1.180
ADAPTIVE_KALMAN_CONFIRM_SCORE = 1.000
ADAPTIVE_KALMAN_WEAK_SCORE = 0.920
ADAPTIVE_KALMAN_WEAK_CONFIRM_SAMPLES = 3
HYBRID_KALMAN_FAST_STRONG_SCORE = 1.200
HYBRID_KALMAN_FAST_MEDIUM_SCORE = 1.000
HYBRID_KALMAN_SUPPORT_SCORE = 0.300
HYBRID_KALMAN_TREND_SUPPORT_SCORE = 0.400
HYBRID_KALMAN_HIGH_CONTEXT_SCORE = 0.700
HYBRID_KALMAN_CONTEXT_MULTIPLIER_MIN = 0.850
HYBRID_KALMAN_CONTEXT_MULTIPLIER_MAX = 1.150
HYBRID_KALMAN_ACTUATOR_FAST_WEIGHT = 1.050
HYBRID_KALMAN_SENSOR_FAST_WEIGHT = 0.850
HYBRID_KALMAN_SENSOR_FAST_SUPPORT_SCORE = 0.880
HYBRID_KALMAN_SENSOR_FAST_COMBINED_SUPPORT_SCORE = 0.900
HYBRID_KALMAN_FAST_SCORE_MAX = 1.500
HYBRID_KALMAN_SENSOR_SCORE_MAX = 1.250
HYBRID_KALMAN_THERMAL_FUSION_LIMIT_C = 0.300
HYBRID_KALMAN_THERMAL_FUSION_SCORE_MAX = 1.120
HYBRID_KALMAN_THERMAL_SENSOR_SUPPORT_SCORE = 0.020
HYBRID_KALMAN_THERMAL_ACTUATOR_SUPPORT_SCORE = 0.250
HYBRID_KALMAN_THERMAL_KALMAN_SUPPORT_SCORE = 0.200
HYBRID_KALMAN_THERMAL_SENSOR_SUPPORT_WEIGHT = 0.350
HYBRID_KALMAN_THERMAL_KALMAN_SUPPORT_WEIGHT = 0.200
HYBRID_KALMAN_THERMAL_MEDIUM_SCORE = 0.950
HYBRID_KALMAN_CONFIRM_SCORE = 0.950
HYBRID_KALMAN_WEAK_SCORE = 0.900
HYBRID_KALMAN_MEDIUM_CONFIRM_SAMPLES = 2
HYBRID_KALMAN_WEAK_CONFIRM_SAMPLES = 3


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


def clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


def thermal_observer_expected_delta(row: Dict[str, str]) -> float:
    coolant_temp_c = parse_float(row, "coolant_temp_meas_c")
    engine_load = parse_float(row, "engine_load")
    vehicle_speed_kph = parse_float(row, "vehicle_speed_kph")
    ambient_temp_c = parse_float(row, "ambient_temp_c")
    temp_error_c = coolant_temp_c - THERMAL_OBSERVER_TARGET_COOLANT_C
    nominal_pump = clamp_unit(
        0.30 + (0.025 * temp_error_c) + (0.35 * engine_load)
    )
    nominal_fan = clamp_unit(
        0.25
        + (0.065 * temp_error_c)
        - (0.10 * (vehicle_speed_kph / 200.0))
    )
    heat_generation = 2.2 + (9.5 * engine_load)
    if (
        row.get("phase_label", "") == "hot_idle"
        or parse_int(row, "phase_id", -1) == 3
    ):
        heat_generation += 2.0
    heat_generation += parse_float(row, "campaign_heat_generation_bias")
    ram_air_scale = parse_float(row, "campaign_ram_air_scale", 1.0)
    expected_rate_c_per_s = (
        heat_generation
        - (7.5 * nominal_pump)
        - (6.0 * nominal_fan)
        - ((vehicle_speed_kph / 40.0) * ram_air_scale)
        - (0.08 * (coolant_temp_c - ambient_temp_c))
    )
    return expected_rate_c_per_s * THERMAL_OBSERVER_DT_S


def kalman_filter_expected_delta(
    row: Dict[str, str],
    coolant_temp_c: float,
) -> float:
    engine_load = parse_float(row, "engine_load")
    vehicle_speed_kph = parse_float(row, "vehicle_speed_kph")
    ambient_temp_c = parse_float(row, "ambient_temp_c")
    temp_error_c = coolant_temp_c - THERMAL_OBSERVER_TARGET_COOLANT_C
    nominal_pump = clamp_unit(
        0.30 + (0.025 * temp_error_c) + (0.35 * engine_load)
    )
    nominal_fan = clamp_unit(
        0.25
        + (0.065 * temp_error_c)
        - (0.10 * (vehicle_speed_kph / 200.0))
    )
    # Older traces may not have command columns; default to the nominal healthy
    # demand so the observer remains usable as a same-trace offline fallback.
    pump_command = parse_float(row, "pump_command", nominal_pump)
    fan_command = parse_float(row, "fan_command", nominal_fan)
    pump_cooling = max(nominal_pump, pump_command)
    fan_cooling = max(nominal_fan, fan_command)
    heat_generation = 2.2 + (9.5 * engine_load)
    if (
        row.get("phase_label", "") == "hot_idle"
        or parse_int(row, "phase_id", -1) == 3
    ):
        heat_generation += 2.0
    heat_generation += parse_float(row, "campaign_heat_generation_bias")
    ram_air_scale = parse_float(row, "campaign_ram_air_scale", 1.0)
    expected_rate_c_per_s = (
        heat_generation
        - (7.5 * clamp_unit(pump_cooling))
        - (6.0 * clamp_unit(fan_cooling))
        - ((vehicle_speed_kph / 40.0) * ram_air_scale)
        - (0.08 * (coolant_temp_c - ambient_temp_c))
    )
    return expected_rate_c_per_s * THERMAL_OBSERVER_DT_S


def adaptive_kalman_context_severity(
    row: Dict[str, str],
    previous_coolant_temp_c: float,
) -> float:
    coolant_temp_c = parse_float(row, "coolant_temp_meas_c")
    coolant_delta_c = coolant_temp_c - previous_coolant_temp_c
    load_score = clamp_unit((parse_float(row, "engine_load") - 0.35) / 0.65)
    low_speed_score = clamp_unit(
        (45.0 - parse_float(row, "vehicle_speed_kph")) / 45.0
    )
    low_extra_airflow_score = 1.0 - clamp_unit(
        parse_float(row, "external_airflow_factor", 0.0)
    )
    ambient_score = clamp_unit((parse_float(row, "ambient_temp_c") - 25.0) / 15.0)
    uphill_score = clamp_unit(parse_float(row, "road_slope_percent", 0.0) / 8.0)
    coolant_level_score = clamp_unit(
        (coolant_temp_c - THERMAL_OBSERVER_TARGET_COOLANT_C) / 18.0
    )
    rising_score = clamp_unit((coolant_delta_c - 0.025) / 0.125)
    return clamp_unit(
        (0.24 * load_score)
        + (0.16 * low_speed_score)
        + (0.10 * low_extra_airflow_score)
        + (0.16 * ambient_score)
        + (0.10 * uphill_score)
        + (0.14 * coolant_level_score)
        + (0.10 * rising_score)
    )


def adaptive_kalman_threshold_scale(
    row: Dict[str, str],
    previous_coolant_temp_c: float,
) -> float:
    severity = adaptive_kalman_context_severity(row, previous_coolant_temp_c)
    return max(
        ADAPTIVE_KALMAN_THRESHOLD_SCALE_MIN,
        min(
            ADAPTIVE_KALMAN_THRESHOLD_SCALE_MAX,
            ADAPTIVE_KALMAN_THRESHOLD_SCALE_LOW_STRESS
            - (ADAPTIVE_KALMAN_THRESHOLD_SCALE_RANGE * severity),
        ),
    )


def adaptive_kalman_trend_score(
    row: Dict[str, str],
    previous_coolant_temp_c: float,
) -> float:
    coolant_delta_c = (
        parse_float(row, "coolant_temp_meas_c") - previous_coolant_temp_c
    )
    return clamp_unit((coolant_delta_c - 0.025) / 0.150)


def adaptive_kalman_actuator_score(row: Dict[str, str]) -> float:
    fan_score = abs(parse_float(row, "fan_tracking_error")) / THRESHOLD_LIMITS[
        "fan_tracking_error"
    ]
    pump_score = abs(parse_float(row, "pump_tracking_error")) / THRESHOLD_LIMITS[
        "pump_tracking_error"
    ]
    return max(fan_score, pump_score)


def hybrid_kalman_sensor_score(row: Dict[str, str]) -> float:
    return abs(parse_float(row, "coolant_sensor_residual_c")) / THRESHOLD_LIMITS[
        "coolant_sensor_residual_c"
    ]


def hybrid_kalman_context_multiplier(context_severity: float) -> float:
    return max(
        HYBRID_KALMAN_CONTEXT_MULTIPLIER_MIN,
        min(
            HYBRID_KALMAN_CONTEXT_MULTIPLIER_MAX,
            HYBRID_KALMAN_CONTEXT_MULTIPLIER_MIN
            + (
                (
                    HYBRID_KALMAN_CONTEXT_MULTIPLIER_MAX
                    - HYBRID_KALMAN_CONTEXT_MULTIPLIER_MIN
                )
                * context_severity
            ),
        ),
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

    if algorithm_name == "thermal_observer":
        accumulated_mismatch_c = 0.0
        previous_coolant_temp_c = parse_float(rows[0], "coolant_temp_meas_c")
        expected_delta_c = thermal_observer_expected_delta(rows[0])
        alarms.append(False)
        for row in rows[1:]:
            current_coolant_temp_c = parse_float(row, "coolant_temp_meas_c")
            observed_delta_c = (
                current_coolant_temp_c - previous_coolant_temp_c
            )
            accumulated_mismatch_c = max(
                0.0,
                accumulated_mismatch_c
                + observed_delta_c
                - expected_delta_c
                - THERMAL_OBSERVER_MISMATCH_ALLOWANCE_C,
            )
            alarms.append(
                accumulated_mismatch_c
                / THERMAL_OBSERVER_DECISION_LIMIT_C
                >= 1.0
            )
            previous_coolant_temp_c = current_coolant_temp_c
            expected_delta_c = thermal_observer_expected_delta(row)
        return alarms

    if algorithm_name in {
        "kalman_filter",
        "adaptive_kalman_filter",
        "hybrid_adaptive_kalman",
    }:
        estimate_c = parse_float(rows[0], "coolant_temp_meas_c")
        covariance = KALMAN_FILTER_INITIAL_COVARIANCE
        expected_delta_c = kalman_filter_expected_delta(rows[0], estimate_c)
        accumulated_innovation = 0.0
        previous_coolant_temp_c = estimate_c
        thermal_previous_coolant_temp_c = estimate_c
        thermal_expected_delta_c = thermal_observer_expected_delta(rows[0])
        thermal_accumulated_mismatch_c = 0.0
        confirmation_count = 0
        alarms.append(False)
        for row in rows[1:]:
            predicted_c = estimate_c + expected_delta_c
            predicted_covariance = covariance + KALMAN_FILTER_PROCESS_NOISE_Q
            innovation = parse_float(row, "coolant_temp_meas_c") - predicted_c
            innovation_variance = (
                predicted_covariance + KALMAN_FILTER_MEASUREMENT_NOISE_R
            )
            normalized_innovation = abs(innovation) / math.sqrt(
                innovation_variance
            )
            kalman_gain = predicted_covariance / innovation_variance
            threshold_scale = (
                adaptive_kalman_threshold_scale(row, previous_coolant_temp_c)
                if algorithm_name in {
                    "adaptive_kalman_filter",
                    "hybrid_adaptive_kalman",
                }
                else 1.0
            )
            innovation_threshold = (
                KALMAN_FILTER_INNOVATION_THRESHOLD * threshold_scale
            )
            accumulation_limit = KALMAN_FILTER_ACCUMULATION_LIMIT * threshold_scale
            estimate_c = predicted_c + (kalman_gain * innovation)
            covariance = (1.0 - kalman_gain) * predicted_covariance
            accumulated_innovation = max(
                0.0,
                (KALMAN_FILTER_ACCUMULATION_LEAK * accumulated_innovation)
                + normalized_innovation
                - KALMAN_FILTER_ACCUMULATION_ALLOWANCE,
            )
            expected_delta_c = kalman_filter_expected_delta(row, estimate_c)
            instantaneous_score = normalized_innovation / innovation_threshold
            accumulated_score = accumulated_innovation / accumulation_limit
            raw_score = max(instantaneous_score, accumulated_score)
            raw_alarm = (
                normalized_innovation >= innovation_threshold
                or accumulated_innovation >= accumulation_limit
            )
            if algorithm_name in {
                "adaptive_kalman_filter",
                "hybrid_adaptive_kalman",
            }:
                context_severity = adaptive_kalman_context_severity(
                    row, previous_coolant_temp_c
                )
                context_multiplier = 1.0 + (
                    (ADAPTIVE_KALMAN_CONTEXT_MULTIPLIER_MAX - 1.0)
                    * context_severity
                )
                actuator_score = adaptive_kalman_actuator_score(row)
                actuator_component = max(
                    0.0,
                    min(
                        1.25,
                        ADAPTIVE_KALMAN_ACTUATOR_SCORE_WEIGHT * actuator_score,
                    ),
                )
                trend_gate = (
                    raw_score >= ADAPTIVE_KALMAN_TREND_GATE_SCORE
                    or actuator_score >= ADAPTIVE_KALMAN_TREND_GATE_SCORE
                )
                trend_component = (
                    ADAPTIVE_KALMAN_TREND_SCORE_WEIGHT
                    * adaptive_kalman_trend_score(row, previous_coolant_temp_c)
                    if trend_gate
                    else 0.0
                )
                combined_score = max(raw_score, actuator_component)
                combined_score = max(
                    0.0,
                    min(2.0, (combined_score + trend_component) * context_multiplier),
                )
                hybrid_fast_alarm = False
                hybrid_sensor_fast_alarm = False
                hybrid_medium_evidence = False
                if algorithm_name == "hybrid_adaptive_kalman":
                    sensor_score = hybrid_kalman_sensor_score(row)
                    fast_actuator_score = max(
                        0.0,
                        min(
                            HYBRID_KALMAN_FAST_SCORE_MAX,
                            HYBRID_KALMAN_ACTUATOR_FAST_WEIGHT * actuator_score,
                        ),
                    )
                    fast_sensor_score = max(
                        0.0,
                        min(
                            HYBRID_KALMAN_SENSOR_SCORE_MAX,
                            HYBRID_KALMAN_SENSOR_FAST_WEIGHT * sensor_score,
                        ),
                    )
                    fast_score = max(fast_actuator_score, fast_sensor_score)
                    hybrid_fast_score = max(
                        0.0,
                        min(
                            HYBRID_KALMAN_FAST_SCORE_MAX,
                            fast_score
                            * hybrid_kalman_context_multiplier(context_severity),
                        ),
                    )
                    kalman_support = (
                        instantaneous_score >= HYBRID_KALMAN_SUPPORT_SCORE
                        or accumulated_score >= HYBRID_KALMAN_SUPPORT_SCORE
                        or raw_score >= HYBRID_KALMAN_SUPPORT_SCORE
                    )
                    trend_support = (
                        trend_gate
                        and adaptive_kalman_trend_score(
                            row, previous_coolant_temp_c
                        )
                        >= HYBRID_KALMAN_TREND_SUPPORT_SCORE
                    )
                    context_support = (
                        context_severity >= HYBRID_KALMAN_HIGH_CONTEXT_SCORE
                    )
                    fast_support = (
                        kalman_support or trend_support or context_support
                    )
                    hybrid_fast_alarm = (
                        hybrid_fast_score >= HYBRID_KALMAN_FAST_STRONG_SCORE
                        and fast_support
                    )
                    hybrid_sensor_fast_alarm = (
                        fast_sensor_score
                        >= HYBRID_KALMAN_SENSOR_FAST_SUPPORT_SCORE
                        and combined_score
                        >= HYBRID_KALMAN_SENSOR_FAST_COMBINED_SUPPORT_SCORE
                        and (kalman_support or trend_support)
                    )
                    hybrid_medium_evidence = (
                        hybrid_fast_score >= HYBRID_KALMAN_FAST_MEDIUM_SCORE
                        and (kalman_support or trend_support)
                    )
                    observed_thermal_delta_c = (
                        parse_float(row, "coolant_temp_meas_c")
                        - thermal_previous_coolant_temp_c
                    )
                    thermal_accumulated_mismatch_c = max(
                        0.0,
                        thermal_accumulated_mismatch_c
                        + observed_thermal_delta_c
                        - thermal_expected_delta_c
                        - THERMAL_OBSERVER_MISMATCH_ALLOWANCE_C,
                    )
                    thermal_fusion_score = max(
                        0.0,
                        min(
                            HYBRID_KALMAN_THERMAL_FUSION_SCORE_MAX,
                            (
                                thermal_accumulated_mismatch_c
                                / HYBRID_KALMAN_THERMAL_FUSION_LIMIT_C
                            )
                            + (
                                HYBRID_KALMAN_THERMAL_SENSOR_SUPPORT_WEIGHT
                                * sensor_score
                            )
                            + (
                                HYBRID_KALMAN_THERMAL_KALMAN_SUPPORT_WEIGHT
                                * raw_score
                            ),
                        ),
                    )
                    hybrid_thermal_evidence = (
                        (
                            sensor_score
                            >= HYBRID_KALMAN_THERMAL_SENSOR_SUPPORT_SCORE
                            or actuator_score
                            >= HYBRID_KALMAN_THERMAL_ACTUATOR_SUPPORT_SCORE
                        )
                        and raw_score >= HYBRID_KALMAN_THERMAL_KALMAN_SUPPORT_SCORE
                        and thermal_fusion_score
                        >= HYBRID_KALMAN_THERMAL_MEDIUM_SCORE
                    )
                    if hybrid_thermal_evidence:
                        combined_score = max(combined_score, thermal_fusion_score)
                        hybrid_medium_evidence = True
                    if (
                        hybrid_fast_alarm
                        or hybrid_sensor_fast_alarm
                        or hybrid_medium_evidence
                    ):
                        combined_score = max(combined_score, hybrid_fast_score)
                    thermal_previous_coolant_temp_c = parse_float(
                        row, "coolant_temp_meas_c"
                    )
                    thermal_expected_delta_c = thermal_observer_expected_delta(row)
                if (
                    hybrid_fast_alarm
                    or hybrid_sensor_fast_alarm
                    or combined_score >= ADAPTIVE_KALMAN_STRONG_SCORE
                    or actuator_score >= 1.0
                    or raw_alarm
                ):
                    required_samples = 1
                elif (
                    hybrid_medium_evidence
                    or (
                        algorithm_name == "hybrid_adaptive_kalman"
                        and combined_score >= HYBRID_KALMAN_CONFIRM_SCORE
                    )
                ):
                    required_samples = HYBRID_KALMAN_MEDIUM_CONFIRM_SAMPLES
                elif combined_score >= ADAPTIVE_KALMAN_CONFIRM_SCORE:
                    required_samples = 2
                elif algorithm_name == "hybrid_adaptive_kalman":
                    required_samples = HYBRID_KALMAN_WEAK_CONFIRM_SAMPLES
                else:
                    required_samples = ADAPTIVE_KALMAN_WEAK_CONFIRM_SAMPLES
                weak_score = (
                    HYBRID_KALMAN_WEAK_SCORE
                    if algorithm_name == "hybrid_adaptive_kalman"
                    else ADAPTIVE_KALMAN_WEAK_SCORE
                )
                if combined_score >= weak_score:
                    confirmation_count += 1
                else:
                    confirmation_count = 0
                alarms.append(
                    raw_alarm
                    or hybrid_fast_alarm
                    or hybrid_sensor_fast_alarm
                    or confirmation_count >= required_samples
                )
            else:
                alarms.append(raw_alarm)
            previous_coolant_temp_c = parse_float(row, "coolant_temp_meas_c")
        return alarms

    raise ValueError(f"Unknown offline detector: {algorithm_name}")


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


def runtime_detection_available(
    rows: Sequence[Dict[str, str]], algorithm_name: str
) -> bool:
    required_columns = {
        "runtime_detection_algorithm",
        "runtime_detection_alarm",
        "runtime_detection_detected",
        "runtime_detection_first_detection_ms",
        "runtime_detection_latency_ms",
    }
    return required_columns.issubset(rows[0]) and all(
        row.get("runtime_detection_algorithm", "") == algorithm_name for row in rows
    )


def evaluate_runtime_detection(
    csv_path: Path | str, algorithm_name: str
) -> Dict[str, object]:
    """Report detector results recorded by the C simulator at runtime."""
    if algorithm_name not in SUPPORTED_ALGORITHMS:
        raise ValueError(
            f"Unsupported detection algorithm '{algorithm_name}'. "
            f"Expected one of: {', '.join(SUPPORTED_ALGORITHMS)}"
        )

    path = Path(csv_path)
    rows = read_csv_rows(path)
    if not runtime_detection_available(rows, algorithm_name):
        raise ValueError(
            f"Runtime results for '{algorithm_name}' are not present in {path}"
        )

    first_row = rows[0]
    final_row = rows[-1]
    events = fault_events(first_row)
    fault_start_ms = min((event.start_ms for event in events), default=None)
    fault_type = "+".join(event.fault_type for event in events) if events else "none"
    first_ecu_dtc_label, first_ecu_dtc_s, ecu_dtc_latency_s = first_post_fault_dtc(
        rows, fault_start_ms
    )
    first_detection_ms = parse_int(
        final_row, "runtime_detection_first_detection_ms", -1
    )
    detection_latency_ms = parse_int(
        final_row, "runtime_detection_latency_ms", -1
    )
    detected = parse_int(final_row, "runtime_detection_detected") != 0
    alarms = [
        parse_int(row, "runtime_detection_alarm") != 0
        for row in rows
    ]
    false_positive_count = parse_int(
        final_row,
        "runtime_detection_false_positive_count",
        count_alarm_episodes(rows, alarms, end_before_ms=fault_start_ms),
    )
    action_requested = (
        parse_int(final_row, "runtime_detection_action_requested") != 0
    )
    action_time_ms = parse_int(
        final_row, "runtime_detection_action_time_ms", -1
    )
    first_action_row = next(
        (
            row
            for row in rows
            if parse_int(row, "runtime_detection_action_requested") != 0
        ),
        None,
    )
    campaign_id = first_row.get("campaign_id", path.stem)
    scenario_id = first_row.get("scenario_id", "") or campaign_id or path.stem

    return {
        "algorithm": algorithm_name,
        "detection_source": "runtime",
        "scenario_id": scenario_id,
        "campaign_id": campaign_id,
        "fault_type": fault_type,
        "fault_start_s": fault_start_ms / 1000.0 if fault_start_ms is not None else None,
        "detected": detected,
        "first_detection_s": first_detection_ms / 1000.0 if first_detection_ms >= 0 else None,
        "detection_latency_s": (
            detection_latency_ms / 1000.0 if detection_latency_ms >= 0 else None
        ),
        "false_positive_count": false_positive_count,
        "missed_detection": bool(events) and not detected,
        "first_ecu_dtc_label": first_ecu_dtc_label,
        "first_ecu_dtc_s": first_ecu_dtc_s,
        "ecu_dtc_latency_s": ecu_dtc_latency_s,
        "final_safe_state": final_row.get("safe_state_label", "unknown"),
        "max_coolant_temp_c": max(
            parse_float(row, "coolant_temp_true_c") for row in rows
        ),
        "runtime_detection_label": final_row.get(
            "runtime_detection_label", "none"
        ),
        "runtime_detection_score": parse_float(
            final_row, "runtime_detection_score"
        ),
        "runtime_detection_action": final_row.get(
            "runtime_detection_action", "observe_only"
        ),
        "runtime_detection_action_requested": action_requested,
        "runtime_detection_requested_safe_state": (
            first_action_row.get("runtime_detection_requested_safe_state", "none")
            if first_action_row is not None
            else "none"
        ),
        "runtime_detection_action_time_s": (
            action_time_ms / 1000.0 if action_time_ms >= 0 else None
        ),
        "runtime_detection_action_reason": final_row.get(
            "runtime_detection_action_reason", "none"
        ),
    }


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
        "detection_source": "offline",
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
    """Prefer matching runtime results, then fall back to offline evaluation."""
    rows = read_csv_rows(csv_path)
    if runtime_detection_available(rows, algorithm_name):
        return evaluate_runtime_detection(csv_path, algorithm_name)
    return evaluate_detection(csv_path, algorithm_name)
