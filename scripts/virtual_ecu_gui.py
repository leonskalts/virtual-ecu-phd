#!/usr/bin/env python3
"""Simple Tkinter frontend for the virtual ECU simulator."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import threading
import textwrap
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

try:
    import tkinter as tk
    import tkinter.font as tkfont
    from tkinter import filedialog, messagebox, ttk
except ImportError as exc:  # pragma: no cover - import failure is environment-specific.
    raise SystemExit(
        "Tkinter is not available in this Python installation. "
        "Install the Tk package for Python and try again."
    ) from exc

try:
    import customtkinter as ctk
except ImportError:  # Keep the GUI runnable in minimal WSL/Python installs.
    ctk = None  # type: ignore[assignment]

os.environ.setdefault("MPLCONFIGDIR", "/tmp/virtual_ecu_mpl")

import matplotlib.pyplot as plt
from propagation_report import (
    LANE_LABELS,
    build_propagation_report,
    propagation_csv_rows,
    save_propagation_plot,
    write_propagation_csv,
    write_propagation_summary,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = PROJECT_ROOT / "logs"
CUSTOM_LOGS_DIR = LOGS_DIR / "gui_custom"
CUSTOM_PRESETS_DIR = PROJECT_ROOT / "presets" / "gui_custom"
SHOWCASE_PRESETS_PATH = PROJECT_ROOT / "presets" / "showcase_demo_presets.json"
RECENT_RESULTS_PATH = PROJECT_ROOT / "presets" / "recent_results.json"
FAVORITE_COMPARISONS_PATH = PROJECT_ROOT / "presets" / "favorite_comparisons.json"
GUI_SESSION_STATE_PATH = PROJECT_ROOT / "presets" / "gui_session_state.json"
FAULT_PATH_ASSET_DIR = PROJECT_ROOT / "assets" / "fault_path"
EXPORT_ROOT = PROJECT_ROOT / "results" / "gui_comparison_reports"
SNAPSHOT_ROOT = PROJECT_ROOT / "results" / "gui_snapshots"
PRESENTATION_BUNDLE_ROOT = PROJECT_ROOT / "results" / "gui_presentation_bundles"
DEFAULT_BATCH_AGGREGATE_CSV = PROJECT_ROOT / "results" / "batch" / "paper_quick" / "aggregate_summary.csv"
MAX_CUSTOM_SCENARIO_EVENTS = 4
MAX_RECENT_RESULTS = 6
MAX_FAVORITES = 8
CTK_AVAILABLE = ctk is not None
UI_FONT = "DejaVu Sans"
APP_BG = "#edf2f7"
CARD_BG = "#ffffff"
SOFT_CARD_BG = "#f8fafc"
SIDEBAR_BG = "#14213d"
SIDEBAR_ACTIVE = "#2f80ed"
SIDEBAR_HOVER = "#1f3f70"
SIDEBAR_TEXT = "#f8fafc"
TEXT_DARK = "#172033"
TEXT_MUTED = "#526173"
ACCENT_GREEN = "#2d9c6f"
ACCENT_AMBER = "#d89020"
REQUIRED_RESULT_RAW_COLUMNS = {
    "experiment_id",
    "campaign_id",
    "campaign_label",
    "time_ms",
    "time_s",
    "phase_label",
    "active_event_index",
    "active_fault_parameter",
    "fault_mode_label",
    "fault_behavior_label",
    "safe_state_id",
    "safe_state_label",
    "primary_dtc_id",
    "primary_dtc_label",
    "coolant_temp_true_c",
    "coolant_temp_meas_c",
    "pump_command",
    "pump_actual",
    "fan_command",
    "fan_actual",
}
REQUIRED_RESULT_SUMMARY_COLUMNS = {
    "experiment_id",
    "campaign_id",
    "campaign_label",
    "detection_latency_ms",
    "safe_state_latency_ms",
    "max_coolant_temp_c",
    "final_safe_state_label",
    "final_primary_dtc_label",
}

CAMPAIGNS: Sequence[Tuple[str, str]] = (
    ("baseline", "Baseline"),
    ("sensor_bias_only", "Sensor Bias Only"),
    ("sensor_interface_intermittent", "Sensor Interface Intermittent"),
    ("stale_sensor_data_only", "Stale Sensor Data Only"),
    ("stale_sensor_data_hot_stress", "Stale Sensor Data Hot Stress"),
    ("pump_degraded_only", "Pump Degraded Only"),
    ("fan_stuck_only", "Fan Stuck Only"),
    ("fan_stuck_hot_stress", "Fan Stuck Hot Stress"),
    ("calibration_memory_corruption", "Calibration Memory Corruption"),
    ("paper_default", "Paper Default"),
)
CUSTOM_FAULT_TYPES: Sequence[Tuple[str, str]] = (
    ("sensor_bias", "Sensor Bias"),
    ("sensor_interface_intermittent", "Sensor Interface Intermittent"),
    ("stale_sensor_data", "Stale Sensor Data"),
    ("pump_degraded", "Pump Degraded"),
    ("fan_stuck_off", "Fan Stuck Off"),
    ("calibration_memory_corruption", "Calibration Memory Corruption"),
)
CUSTOM_FAULT_BEHAVIORS: Sequence[Tuple[str, str]] = (
    ("transient", "Transient"),
    ("permanent", "Permanent"),
)
CUSTOM_DEFAULT_PARAMETERS = {
    "sensor_bias": "6.0",
    "sensor_interface_intermittent": "8.0",
    "stale_sensor_data": "2500",
    "pump_degraded": "0.45",
    "fan_stuck_off": "0.0",
    "calibration_memory_corruption": "16.0",
}
BUILTIN_CUSTOM_PRESETS = {
    "sensor_bias_demo": {
        "preset_kind": "single",
        "preset_name": "sensor_bias_demo",
        "fault_type": "sensor_bias",
        "fault_behavior": "transient",
        "start_ms": 20000,
        "duration_ms": 10000,
        "parameter": 8.0,
    },
    "stale_sensor_data_demo": {
        "preset_kind": "single",
        "preset_name": "stale_sensor_data_demo",
        "fault_type": "stale_sensor_data",
        "fault_behavior": "transient",
        "start_ms": 20000,
        "duration_ms": 10000,
        "parameter": 2500.0,
    },
    "fan_stuck_off_demo": {
        "preset_kind": "single",
        "preset_name": "fan_stuck_off_demo",
        "fault_type": "fan_stuck_off",
        "fault_behavior": "permanent",
        "start_ms": 60000,
        "duration_ms": 0,
        "parameter": 0.0,
    },
}
BUILTIN_MULTI_CUSTOM_PRESETS = {
    "sensor_bias_then_fan_loss_demo": {
        "preset_kind": "multi",
        "preset_name": "sensor_bias_then_fan_loss_demo",
        "events": [
            {
                "fault_type": "sensor_bias",
                "fault_behavior": "transient",
                "start_ms": 20000,
                "duration_ms": 10000,
                "parameter": 8.0,
            },
            {
                "fault_type": "fan_stuck_off",
                "fault_behavior": "permanent",
                "start_ms": 65000,
                "duration_ms": 0,
                "parameter": 0.0,
            },
        ],
    },
    "stale_then_pump_demo": {
        "preset_kind": "multi",
        "preset_name": "stale_then_pump_demo",
        "events": [
            {
                "fault_type": "stale_sensor_data",
                "fault_behavior": "transient",
                "start_ms": 25000,
                "duration_ms": 15000,
                "parameter": 3000.0,
            },
            {
                "fault_type": "pump_degraded",
                "fault_behavior": "transient",
                "start_ms": 60000,
                "duration_ms": 25000,
                "parameter": 0.45,
            },
        ],
    },
}
CUSTOM_MODE_AFFECTED_BLOCKS = {
    "sensor_bias": ("sensor_adc",),
    "sensor_interface_intermittent": ("sensor_adc",),
    "stale_sensor_data": ("timing_link",),
    "pump_degraded": ("actuator_power",),
    "fan_stuck_off": ("actuator_power",),
    "calibration_memory_corruption": ("ecu_control_memory",),
}
CUSTOM_FAULT_NOTES = {
    "sensor_bias": "Custom sensing-path bias enters through the ADC/front-end chain.",
    "sensor_interface_intermittent": "Custom intermittent corruption appears at the sensor-interface boundary before ECU control logic.",
    "stale_sensor_data": "Custom stale sampled-data timing leaves the ECU acting on aged coolant information.",
    "pump_degraded": "Custom pump-path degradation reduces realized actuation authority after the ECU command.",
    "fan_stuck_off": "Custom fan driver or power-stage loss prevents commanded fan actuation.",
    "calibration_memory_corruption": "Custom calibration corruption changes ECU control behavior internally before plant-level consequences emerge.",
}
CUSTOM_FAULT_STORY_BASE = {
    "sensor_bias": {
        "campaign_name": "Custom Sensor Bias",
        "description": "Custom sensing-path bias case configured from the GUI.",
        "fault_class": "sensing-path fault",
        "hardware_source": "ADC offset, reference drift, or analog front-end bias in the coolant sensing chain.",
        "ecu_manifestation": "Biased coolant measurement reaches the ECU even though the plant state itself is unchanged.",
        "diagnostic_effect": "Coolant sensor rationality evidence is expected to appear quickly from the measurement residual.",
        "system_effect": "The main effect is distorted sensing and diagnostic visibility rather than an immediate strong thermal escalation.",
    },
    "sensor_interface_intermittent": {
        "campaign_name": "Custom Sensor Interface Intermittent",
        "description": "Custom bursty sensing-path disturbance configured from the GUI.",
        "fault_class": "sensing-path fault",
        "hardware_source": "Intermittent sensor-interface corruption such as connector intermittency, burst noise, or sampling glitches.",
        "ecu_manifestation": "Bursty coolant-reading disturbances appear at the ECU interface while the true thermal state remains smoother.",
        "diagnostic_effect": "Sensor rationality behavior is expected to track the timing and persistence of the bursts.",
        "system_effect": "Control disturbance is usually temporary unless the disturbance persists long enough to couple into thermal stress.",
    },
    "stale_sensor_data": {
        "campaign_name": "Custom Stale Sensor Data",
        "description": "Custom timing/communication-path case configured from the GUI.",
        "fault_class": "timing/communication-path fault",
        "hardware_source": "Sample-refresh delay, stale register handoff, or delayed sensor-to-ECU communication update path.",
        "ecu_manifestation": "The controller receives older coolant information than the true plant state and reacts late.",
        "diagnostic_effect": "Sensor rationality or cooling-performance evidence can appear once the stale-data lag becomes large enough.",
        "system_effect": "Cooling demand arrives late, making the timing fault visible through higher peak temperature or earlier protection.",
    },
    "pump_degraded": {
        "campaign_name": "Custom Pump Degraded",
        "description": "Custom actuation-path degradation case configured from the GUI.",
        "fault_class": "actuation-path fault",
        "hardware_source": "Weak driver behavior, supply droop, aging, or partial pump authority loss.",
        "ecu_manifestation": "Pump actual response is reduced relative to the ECU command.",
        "diagnostic_effect": "Pump-tracking and cooling-performance evidence are expected when the mismatch persists.",
        "system_effect": "Reduced coolant flow can raise thermal stress and trigger stronger safety action if the severity is high enough.",
    },
    "fan_stuck_off": {
        "campaign_name": "Custom Fan Stuck Off",
        "description": "Custom permanent or sustained fan actuation-loss case configured from the GUI.",
        "fault_class": "actuation-path fault",
        "hardware_source": "PWM output, gate-driver, or power-stage loss that leaves the fan effectively unavailable.",
        "ecu_manifestation": "The ECU commands fan actuation, but realized fan response stays unavailable.",
        "diagnostic_effect": "Fan tracking evidence is expected quickly because commanded and realized actuation diverge sharply.",
        "system_effect": "Thermal stress and safe-state escalation become more likely as airflow support is lost.",
    },
    "calibration_memory_corruption": {
        "campaign_name": "Custom Calibration Memory Corruption",
        "description": "Custom computation/memory-path case configured from the GUI.",
        "fault_class": "computation/memory-path fault",
        "hardware_source": "Corrupted calibration register, state-memory upset, or nonvolatile memory disturbance affecting the cooling target.",
        "ecu_manifestation": "The ECU applies a shifted cooling target even when sensed temperature remains correct.",
        "diagnostic_effect": "Thermal and cooling-performance evidence appears after the corrupted internal control behavior propagates outward.",
        "system_effect": "The controller itself becomes miscalibrated, which can raise peak temperature and trigger earlier protective action.",
    },
}

MODE_TO_CLASS = {
    "sensor_bias": "sensing-path fault",
    "sensor_interface_intermittent": "sensing-path fault",
    "stale_sensor_data": "timing/communication-path fault",
    "pump_degraded": "actuation-path fault",
    "fan_stuck_off": "actuation-path fault",
    "calibration_memory_corruption": "computation/memory-path fault",
}

FAULT_TYPE_DISPLAY = {
    "none": "Baseline",
    "sensor_bias": "Sensor Bias",
    "sensor_interface_intermittent": "Sensor Interface Intermittent",
    "stale_sensor_data": "Stale Sensor Data",
    "pump_degraded": "Pump Degraded",
    "fan_stuck_off": "Fan Stuck Off",
    "calibration_memory_corruption": "Calibration Memory Corruption",
}
SCENARIO_TIMELINE_COLORS = {
    "sensor_bias": "#c4473a",
    "sensor_interface_intermittent": "#d17b29",
    "stale_sensor_data": "#4d78c2",
    "pump_degraded": "#2f8f7e",
    "fan_stuck_off": "#8d4fb8",
    "calibration_memory_corruption": "#8a5b2f",
}

FAULT_TYPE_ORDER = (
    "none",
    "sensor_bias",
    "sensor_interface_intermittent",
    "stale_sensor_data",
    "pump_degraded",
    "fan_stuck_off",
    "calibration_memory_corruption",
)

SAFE_STATE_LABELS = {
    0: "normal",
    1: "precautionary_cooling",
    2: "limp_home",
    3: "controlled_shutdown",
}
SAFE_STATE_DISPLAY_ORDER = (
    "normal",
    "precautionary_cooling",
    "limp_home",
    "controlled_shutdown",
)
SAFE_STATE_SEVERITY = {
    "normal": 0,
    "precautionary_cooling": 1,
    "limp_home": 2,
    "controlled_shutdown": 3,
}
DTC_SEVERITY = {
    0: 0,
    1001: 1,
    2001: 3,
    2002: 4,
    3001: 2,
    3002: 2,
    3003: 3,
}

LEFT_COLOR = "#c4473a"
RIGHT_COLOR = "#1f5aa6"
LEFT_DASH = None
RIGHT_DASH = (6, 4)
EVIDENCE_STAGE_DISPLAY = {
    "Hardware-Origin Fault": "1. Hardware-Origin Fault",
    "ECU-Visible Manifestation": "2. ECU Manifestation",
    "First Diagnostic Evidence": "3. Diagnostic Evidence",
    "First Safe-State Transition": "4. Safe-State Transition",
    "Peak Thermal Severity": "5. Peak Thermal Severity",
}
EVIDENCE_STAGE_TAGS = {
    "Hardware-Origin Fault": "evidence_hardware",
    "ECU-Visible Manifestation": "evidence_ecu",
    "First Diagnostic Evidence": "evidence_diagnostic",
    "First Safe-State Transition": "evidence_safe_state",
    "Peak Thermal Severity": "evidence_thermal",
}
FAULT_PATH_BLOCKS: Sequence[Tuple[str, str]] = (
    ("sensor_adc", "Sensor / ADC\nFront-End"),
    ("timing_link", "Timing /\nCommunication Link"),
    ("ecu_control_memory", "ECU Control +\nCalibration Memory"),
    ("actuator_power", "Actuator Driver /\nPower Stage"),
    ("thermal_plant", "Thermal Plant /\nCoolant System"),
)
FAULT_PATH_BLOCK_CLASS = {
    "sensor_adc": "Sensing Path",
    "timing_link": "Timing / Link",
    "ecu_control_memory": "Control / Memory",
    "actuator_power": "Actuation Path",
    "thermal_plant": "Plant Outcome",
}
FAULT_PATH_BLOCK_DISPLAY = {block_id: label.replace("\n", " ") for block_id, label in FAULT_PATH_BLOCKS}
CAMPAIGN_AFFECTED_BLOCKS = {
    "baseline": (),
    "sensor_bias_only": ("sensor_adc",),
    "sensor_interface_intermittent": ("sensor_adc",),
    "stale_sensor_data_only": ("timing_link",),
    "stale_sensor_data_hot_stress": ("timing_link",),
    "pump_degraded_only": ("actuator_power",),
    "fan_stuck_only": ("actuator_power",),
    "fan_stuck_hot_stress": ("actuator_power",),
    "calibration_memory_corruption": ("ecu_control_memory",),
    "paper_default": ("sensor_adc", "actuator_power", "thermal_plant"),
}
FAULT_PATH_NOTES = {
    "baseline": "Nominal sensing, timing, control, actuation, and thermal path.",
    "sensor_bias_only": "Sensing-path corruption enters through the ADC/front-end measurement chain.",
    "sensor_interface_intermittent": "Intermittent sensor-interface corruption appears before ECU control logic.",
    "stale_sensor_data_only": "A timing/communication delay leaves the ECU acting on aged coolant data.",
    "stale_sensor_data_hot_stress": "A stale-data timing path is stressed by hotter, lower-airflow operation.",
    "pump_degraded_only": "Actuator authority is reduced between ECU command and realized coolant flow.",
    "fan_stuck_only": "Fan driver or power-stage behavior prevents commanded fan actuation.",
    "fan_stuck_hot_stress": "Fan power-stage loss propagates into a strong thermal/safety response.",
    "calibration_memory_corruption": "A corrupted calibration target shifts ECU control behavior internally.",
    "paper_default": "Mixed sensing and actuation faults propagate across the chain and end with a clear plant-level thermal consequence.",
}

CAMPAIGN_STORIES = {
    "baseline": {
        "campaign_name": "Baseline",
        "description": "Nominal reference run used as the comparison case for all injected-fault campaigns.",
        "fault_class": "baseline / no injected fault",
        "hardware_source": "No injected hardware-origin fault. Sensor, actuation, and memory paths are nominal.",
        "ecu_manifestation": "Nominal coolant sensing, nominal controller target, and nominal pump/fan realization.",
        "diagnostic_effect": "No expected DTC confirmation. Diagnostics remain quiet unless a model or threshold issue is introduced.",
        "system_effect": "Normal thermal regulation with no safety escalation. Serves as the nominal comparison case.",
    },
    "sensor_bias_only": {
        "campaign_name": "Sensor Bias Only",
        "description": "Single sensing-path bias case for showing measurement corruption without major thermal escalation.",
        "fault_class": "sensing-path fault",
        "hardware_source": "ADC offset, reference drift, or analog front-end bias in the coolant sensing chain.",
        "ecu_manifestation": "Biased coolant measurement at the ECU input even though the plant temperature is unchanged.",
        "diagnostic_effect": "Coolant sensor rationality DTC is expected to appear quickly from the measurement residual.",
        "system_effect": "Control demand may be distorted, but the main system-level effect is diagnostic visibility rather than safe-state escalation.",
    },
    "sensor_interface_intermittent": {
        "campaign_name": "Sensor Interface Intermittent",
        "description": "Bursty sensing-path disturbance case for showing intermittent ECU-visible sensor corruption.",
        "fault_class": "sensing-path fault",
        "hardware_source": "Intermittent sensor-interface corruption such as sampling glitches, connector intermittency, or burst noise.",
        "ecu_manifestation": "Bursty coolant reading disturbances appear at the ECU interface while the true thermal state remains smooth.",
        "diagnostic_effect": "Transient or intermittent coolant sensor rationality behavior is expected, with DTC activity tied to burst timing.",
        "system_effect": "Temporary control disturbance may occur, but safe-state entry is usually limited unless the disturbance couples into thermal stress.",
    },
    "stale_sensor_data_only": {
        "campaign_name": "Stale Sensor Data Only",
        "description": "Moderate timing/communication-path case where the ECU reuses an older coolant sample and cooling demand arrives late.",
        "fault_class": "timing/communication-path fault",
        "hardware_source": "Clock-domain crossing delay, stale register handoff, DMA refresh lag, or sampled-data transport timing fault in the sensor-to-ECU path.",
        "ecu_manifestation": "The coolant measurement visible to the controller updates too slowly, so the ECU acts on aged thermal information.",
        "diagnostic_effect": "Sensor rationality evidence appears after the stale-data lag becomes large enough during the rising-temperature phase.",
        "system_effect": "Cooling demand arrives late, increasing peak coolant temperature and making delayed control action visible even without an extreme stress case.",
    },
    "stale_sensor_data_hot_stress": {
        "campaign_name": "Stale Sensor Data Hot Stress",
        "description": "Stressed timing/communication-path campaign that combines stale ECU coolant data with hotter and lower-airflow operating conditions.",
        "fault_class": "timing/communication-path fault under thermal stress",
        "hardware_source": "Persistent sampled-data refresh delay caused by stale register transfer, timing margin loss, or a delayed sensor-to-ECU communication update path.",
        "ecu_manifestation": "The controller repeatedly operates on aged coolant measurements during the urban-traffic and hot-idle phases.",
        "diagnostic_effect": "Coolant sensor rationality evidence is expected to persist longer, with overtemperature and safe-state transitions appearing sooner than in the milder timing case.",
        "system_effect": "This is the strongest timing/communication demonstration case: stale data delays cooling action enough to create a visible thermal and safety consequence.",
    },
    "pump_degraded_only": {
        "campaign_name": "Pump Degraded Only",
        "description": "Actuation-path degradation case for reduced pump authority and tracking mismatch.",
        "fault_class": "actuation-path fault",
        "hardware_source": "Weak driver behavior, supply droop, aging, or partial loss of pump actuation authority.",
        "ecu_manifestation": "Pump actual response is reduced relative to the ECU command.",
        "diagnostic_effect": "Pump tracking fault and possibly cooling-performance degradation behavior are expected as the mismatch persists.",
        "system_effect": "Reduced heat rejection can raise coolant temperature and may eventually push the safety monitor toward precautionary action.",
    },
    "fan_stuck_only": {
        "campaign_name": "Fan Stuck Only",
        "description": "Permanent fan actuation-loss case for direct tracking-fault and safe-state behavior.",
        "fault_class": "actuation-path fault",
        "hardware_source": "PWM output, gate-driver, or power-stage fault that leaves the fan effectively stuck off.",
        "ecu_manifestation": "The ECU commands fan actuation, but the realized fan response stays near zero.",
        "diagnostic_effect": "Fan tracking DTC is expected quickly because commanded and realized fan signals diverge.",
        "system_effect": "Protective cooling and limp-home escalation are expected as the ECU responds to persistent actuation loss.",
    },
    "fan_stuck_hot_stress": {
        "campaign_name": "Fan Stuck Hot Stress",
        "description": "Thermally stressed permanent-fault case that best exposes cross-layer propagation into safety response.",
        "fault_class": "actuation-path fault under thermal stress",
        "hardware_source": "Permanent fan power-stage or gate-driver stuck-off fault combined with hotter ambient and lower ram-air cooling.",
        "ecu_manifestation": "Fan command remains high while fan actual remains unavailable during a thermally aggressive operating condition.",
        "diagnostic_effect": "Fan tracking DTC is expected, followed by stronger thermal-warning and performance-related evidence if temperature rises.",
        "system_effect": "This is the strongest cross-layer safe-state case: thermal stress rises faster and precautionary or limp-home behavior appears earlier.",
    },
    "calibration_memory_corruption": {
        "campaign_name": "Calibration Memory Corruption",
        "description": "Computation/memory-path case where corrupted control calibration shifts thermal behavior over time.",
        "fault_class": "computation/memory-path fault",
        "hardware_source": "Corrupted calibration register, NVM bit upset, or memory-path fault affecting the coolant control target.",
        "ecu_manifestation": "The ECU uses a shifted cooling target, delaying requested cooling despite correct sensed temperatures.",
        "diagnostic_effect": "Cooling-performance and thermal-related diagnostics are expected later in the run as the consequences propagate outward.",
        "system_effect": "Higher peak coolant temperature and earlier safety intervention are expected because the controller itself is miscalibrated.",
    },
    "paper_default": {
        "campaign_name": "Paper Default",
        "description": "Mixed multi-stage campaign for demonstrating sensing, actuation, and safety propagation in one run.",
        "fault_class": "mixed hardware-origin faults",
        "hardware_source": "Sequential sensing-path, actuation-path, and power-stage faults representing a cross-layer multi-stage failure story.",
        "ecu_manifestation": "The ECU first sees biased sensing, then degraded pump authority, then fan actuation loss.",
        "diagnostic_effect": "Diagnostics evolve over time from sensor rationality behavior to actuator-tracking and thermal-response evidence.",
        "system_effect": "This campaign demonstrates staged propagation from hardware-origin faults into system degradation and safety escalation.",
    },
}


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sanitize_preset_name(name: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in name.strip().lower())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_")


def preset_file_path(name: str) -> Path:
    return CUSTOM_PRESETS_DIR / f"{sanitize_preset_name(name)}.json"


def custom_preset_payload(name: str, config: Dict[str, object]) -> Dict[str, object]:
    if str(config.get("kind", "single")) == "multi":
        events = config.get("events", [])
        return {
            "preset_kind": "multi",
            "preset_name": name,
            "events": [
                {
                    "fault_type": str(event["fault_type"]),
                    "fault_behavior": str(event["fault_behavior"]),
                    "start_ms": int(event["start_ms"]),
                    "duration_ms": int(event["duration_ms"]),
                    "parameter": float(event["parameter"]),
                }
                for event in events  # type: ignore[union-attr]
            ],
        }

    return {
        "preset_kind": "single",
        "preset_name": name,
        "fault_type": str(config["fault_type"]),
        "fault_behavior": str(config["fault_behavior"]),
        "start_ms": int(config["start_ms"]),
        "duration_ms": int(config["duration_ms"]),
        "parameter": float(config["parameter"]),
    }


def write_custom_preset(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def read_custom_preset(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    preset_kind = str(payload.get("preset_kind", "single"))
    if preset_kind == "multi":
        events = []
        for event in payload["events"]:
            events.append(
                {
                    "fault_type": str(event["fault_type"]),
                    "fault_behavior": str(event["fault_behavior"]),
                    "start_ms": int(event["start_ms"]),
                    "duration_ms": int(event["duration_ms"]),
                    "parameter": float(event["parameter"]),
                }
            )
        return {
            "preset_kind": "multi",
            "preset_name": str(payload["preset_name"]),
            "events": events,
        }

    return {
        "preset_kind": "single",
        "preset_name": str(payload["preset_name"]),
        "fault_type": str(payload["fault_type"]),
        "fault_behavior": str(payload["fault_behavior"]),
        "start_ms": int(payload["start_ms"]),
        "duration_ms": int(payload["duration_ms"]),
        "parameter": float(payload["parameter"]),
    }


def list_custom_preset_files() -> List[Path]:
    if not CUSTOM_PRESETS_DIR.exists():
        return []
    return sorted(CUSTOM_PRESETS_DIR.glob("*.json"))


def custom_mode_label(mode: str) -> str:
    return FAULT_TYPE_DISPLAY.get(mode, mode.replace("_", " ").title())


def custom_behavior_label(behavior: str) -> str:
    return behavior.replace("_", " ").title()


def custom_parameter_token(parameter: float) -> str:
    token = f"{parameter:g}"
    parts: List[str] = []
    for char in token:
        if char.isalnum():
            parts.append(char)
        elif char == "-":
            parts.append("neg")
        elif char == ".":
            parts.append("p")
        else:
            parts.append("_")
    return "".join(parts) or "0"


def default_custom_event(
    fault_type: str = "sensor_bias",
    fault_behavior: str = "transient",
    start_ms: int = 20000,
    duration_ms: int = 10000,
    parameter: float | None = None,
) -> Dict[str, object]:
    actual_parameter = parameter
    if actual_parameter is None:
        actual_parameter = float(CUSTOM_DEFAULT_PARAMETERS.get(fault_type, "0.0"))

    return {
        "fault_type": fault_type,
        "fault_behavior": fault_behavior,
        "start_ms": int(start_ms),
        "duration_ms": int(duration_ms),
        "parameter": float(actual_parameter),
    }


def custom_events(config: Dict[str, object]) -> List[Dict[str, object]]:
    if str(config.get("kind", "single")) == "multi":
        return [dict(event) for event in config.get("events", [])]  # type: ignore[arg-type]
    return [
        default_custom_event(
            fault_type=str(config["fault_type"]),
            fault_behavior=str(config["fault_behavior"]),
            start_ms=int(config["start_ms"]),
            duration_ms=int(config["duration_ms"]),
            parameter=float(config["parameter"]),
        )
    ]


def custom_campaign_id(config: Dict[str, object]) -> str:
    if str(config.get("kind", "single")) == "multi":
        parts = []
        for index, event in enumerate(custom_events(config), start=1):
            parts.append(
                f"e{index}_{event['fault_type']}_{event['fault_behavior']}"
                f"_start{event['start_ms']}_dur{event['duration_ms']}"
                f"_param{custom_parameter_token(float(event['parameter']))}"
            )
        return "custom_multi_" + "__".join(parts)

    return (
        f"custom_{config['fault_type']}_{config['fault_behavior']}"
        f"_start{config['start_ms']}_dur{config['duration_ms']}"
        f"_param{custom_parameter_token(float(config['parameter']))}"
    )


def custom_log_path(config: Dict[str, object]) -> Path:
    return CUSTOM_LOGS_DIR / f"{custom_campaign_id(config)}.csv"


def custom_campaign_label(config: Dict[str, object]) -> str:
    if str(config.get("kind", "single")) == "multi":
        events = custom_events(config)
        labels = [custom_mode_label(str(event["fault_type"])) for event in events]
        sequence = " -> ".join(labels[:3])
        if len(labels) > 3:
            sequence += " -> ..."
        return f"Custom Multi-Fault Scenario ({len(events)} events: {sequence})"

    fault_label = custom_mode_label(str(config["fault_type"]))
    behavior = str(config["fault_behavior"])
    start_ms = int(config["start_ms"])
    duration_ms = int(config["duration_ms"])
    parameter = float(config["parameter"])
    timing = (
        f"{start_ms} ms onward"
        if behavior == "permanent" and duration_ms == 0
        else f"{start_ms}-{start_ms + duration_ms} ms"
    )
    return f"Custom {fault_label} ({behavior}, {timing}, p={parameter:g})"


def primary_fault_mode(first_row: Dict[str, str]) -> str:
    modes = event_modes(first_row)
    if modes:
        return modes[0]
    mode_label = first_row.get("fault_mode_label", "none")
    return mode_label if mode_label and mode_label != "none" else "none"


def primary_fault_behavior(first_row: Dict[str, str]) -> str:
    behaviors = event_behaviors(first_row)
    if behaviors:
        return behaviors[0]
    behavior_label = first_row.get("fault_behavior_label", "none")
    return behavior_label if behavior_label and behavior_label != "none" else "none"


def story_for_run(
    campaign_id: str,
    first_row: Dict[str, str] | None = None,
    campaign_label: str | None = None,
) -> Dict[str, str]:
    if campaign_id in CAMPAIGN_STORIES:
        return campaign_story(campaign_id)

    if first_row is None:
        return campaign_story(campaign_id)

    modes = event_modes(first_row)
    if len(modes) > 1:
        hardware_segments: List[str] = []
        affected_blocks = affected_blocks_for_run(campaign_id, first_row)
        for block_id in affected_blocks:
            hardware_segments.append(FAULT_PATH_BLOCK_DISPLAY.get(block_id, block_id.replace("_", " ")))

        sequence = " -> ".join(custom_mode_label(mode) for mode in modes)
        timing_parts = []
        for index, mode in enumerate(modes, start=1):
            timing_parts.append(
                f"{custom_mode_label(mode)} at {first_row.get(f'campaign_event_{index}_start_ms', '0')} ms"
            )

        return {
            "campaign_name": campaign_label or f"Custom Multi-Fault Scenario ({len(modes)} events)",
            "description": (
                "Ordered custom multi-fault scenario configured from the GUI. "
                f"Sequence: {sequence}. Event timing: {'; '.join(timing_parts)}."
            ),
            "fault_class": infer_fault_class(first_row),
            "hardware_source": (
                "Multiple hardware-origin faults are staged across: "
                + ", ".join(hardware_segments if hardware_segments else ["the ECU signal and actuation path"])
                + "."
            ),
            "ecu_manifestation": (
                "The ECU sees a staged propagation story as successive fault events become active in order, "
                "so sensing, control, timing, or actuation effects can evolve across the same run."
            ),
            "diagnostic_effect": (
                "Diagnostic evidence may change over time as later events add new symptoms on top of the earlier path disturbance."
            ),
            "system_effect": (
                "This scenario is designed for thesis/demo use when you want one run to show how multiple electronics-origin faults "
                "stack into thermal and safety consequences."
            ),
        }

    mode = primary_fault_mode(first_row)
    base_story = CUSTOM_FAULT_STORY_BASE.get(mode)
    if base_story is None:
        return campaign_story(campaign_id)

    story = dict(base_story)
    behavior = primary_fault_behavior(first_row)
    start_ms = first_row.get("campaign_event_1_start_ms", first_row.get("active_fault_start_ms", "0"))
    duration_ms = first_row.get("campaign_event_1_duration_ms", first_row.get("active_fault_duration_ms", "0"))
    parameter = first_row.get("campaign_event_1_parameter", first_row.get("active_fault_parameter", "0"))
    if campaign_label:
        story["campaign_name"] = campaign_label
    story["description"] = (
        f"{story['description']} "
        f"Configured as {behavior} with start={start_ms} ms, duration={duration_ms} ms, parameter={parameter}."
    )
    return story


def affected_blocks_for_run(campaign_id: str, first_row: Dict[str, str] | None = None) -> Tuple[str, ...]:
    if campaign_id in CAMPAIGN_AFFECTED_BLOCKS:
        return tuple(CAMPAIGN_AFFECTED_BLOCKS[campaign_id])
    if first_row is None:
        return ()

    affected = []
    for mode in event_modes(first_row):
        for block_id in CUSTOM_MODE_AFFECTED_BLOCKS.get(mode, ()):
            if block_id not in affected:
                affected.append(block_id)

    return tuple(affected)


def fault_path_note_for_run(campaign_id: str, first_row: Dict[str, str] | None = None) -> str:
    if campaign_id in FAULT_PATH_NOTES:
        return FAULT_PATH_NOTES[campaign_id]
    if first_row is None:
        return "Selected campaign mapped onto the qualitative ECU path."

    modes = event_modes(first_row)
    if len(modes) > 1:
        return (
            "Custom multi-fault scenario mapped onto every affected subsystem touched by the ordered event list. "
            "Use the propagation timeline and figures tabs to explain how the narrative evolves from one block to the next."
        )

    mode = primary_fault_mode(first_row)
    behavior = primary_fault_behavior(first_row)
    note = CUSTOM_FAULT_NOTES.get(mode, "Selected campaign mapped onto the qualitative ECU path.")
    if behavior == "permanent":
        return f"{note} The custom run is configured as a persistent fault from its start time."
    return note


def summary_path_for(log_path: Path) -> Path:
    if log_path.suffix.lower() == ".csv":
        return log_path.with_name(f"{log_path.stem}_summary.csv")
    return log_path.with_name(f"{log_path.name}_summary.csv")


def raw_path_for_summary(summary_path: Path) -> Path:
    if summary_path.suffix.lower() == ".csv" and summary_path.stem.endswith("_summary"):
        return summary_path.with_name(f"{summary_path.stem[:-8]}.csv")
    return summary_path


def validate_result_pair(
    raw_rows: Sequence[Dict[str, str]],
    summary_rows: Sequence[Dict[str, str]],
    *,
    raw_path: Path,
    summary_path: Path,
) -> None:
    if not raw_rows:
        raise RuntimeError(f"Raw CSV has no data rows: {raw_path}")
    if not summary_rows:
        raise RuntimeError(f"Summary CSV has no data rows: {summary_path}")

    raw_columns = set(raw_rows[0])
    missing_raw = sorted(REQUIRED_RESULT_RAW_COLUMNS - raw_columns)
    if missing_raw:
        raise RuntimeError(
            "Raw CSV is missing required column(s): "
            + ", ".join(missing_raw)
            + f"\n\nSelected file: {raw_path}"
        )

    summary_columns = set(summary_rows[0])
    missing_summary = sorted(REQUIRED_RESULT_SUMMARY_COLUMNS - summary_columns)
    if missing_summary:
        raise RuntimeError(
            "Summary CSV is missing required column(s): "
            + ", ".join(missing_summary)
            + f"\n\nSummary file: {summary_path}"
        )


def load_existing_result_pair(selected_path: Path) -> Dict[str, object]:
    raw_path = raw_path_for_summary(selected_path.expanduser())
    summary_path = summary_path_for(raw_path)

    if not raw_path.exists():
        raise RuntimeError(f"Raw CSV log not found: {raw_path}")
    if not summary_path.exists():
        raise RuntimeError(
            "Matching summary CSV was not found.\n\n"
            f"Expected: {summary_path}\n\n"
            "Select a raw <name>.csv file that has a matching <name>_summary.csv file beside it."
        )

    raw_rows = read_csv_rows(raw_path)
    summary_rows = read_csv_rows(summary_path)
    validate_result_pair(raw_rows, summary_rows, raw_path=raw_path, summary_path=summary_path)

    summary = dict(summary_rows[0])
    campaign_id = str(summary.get("campaign_id") or raw_rows[0].get("campaign_id") or raw_path.stem)
    if not campaign_id or campaign_id == "unknown":
        campaign_id = f"existing_{sanitize_preset_name(raw_path.stem)}"
    if "campaign_label" not in summary or not summary["campaign_label"]:
        summary["campaign_label"] = raw_path.stem.replace("_", " ").title()

    return {
        "campaign_id": campaign_id,
        "raw_rows": raw_rows,
        "summary_row": summary,
        "log_path": raw_path,
        "summary_path": summary_path,
        "loaded_from_disk": True,
    }


def _project_path(path_text: str) -> Path:
    path = Path(path_text).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def read_showcase_presets(path: Path = SHOWCASE_PRESETS_PATH) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    records = payload.get("showcase_presets", [])
    presets: List[Dict[str, str]] = []
    for record in records:
        presets.append(
            {
                "id": str(record["id"]),
                "title": str(record["title"]),
                "description": str(record["description"]),
                "left_result": str(record["left_result"]),
                "right_result": str(record["right_result"]),
            }
        )
    return presets


def load_showcase_preset_results(preset: Dict[str, str]) -> Tuple[Dict[str, object], Dict[str, object]]:
    left_result = load_existing_result_pair(_project_path(preset["left_result"]))
    right_result = load_existing_result_pair(_project_path(preset["right_result"]))
    return left_result, right_result


def _stored_result_path(path: Path) -> str:
    resolved = path.expanduser()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(resolved)


def _recent_result_item(
    title: str,
    *,
    kind: str,
    description: str,
    left_path: Path,
    right_path: Path | None,
) -> Dict[str, str]:
    return {
        "title": title,
        "kind": kind,
        "description": description,
        "left_result": _stored_result_path(left_path),
        "right_result": "" if right_path is None else _stored_result_path(right_path),
    }


def read_recent_results(path: Path = RECENT_RESULTS_PATH) -> List[Dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    items: List[Dict[str, str]] = []
    for record in payload.get("recent_results", []):
        left_result = str(record.get("left_result", ""))
        if not left_result:
            continue
        items.append(
            {
                "title": str(record.get("title", "Recent result")),
                "kind": str(record.get("kind", "result")),
                "description": str(record.get("description", "")),
                "left_result": left_result,
                "right_result": str(record.get("right_result", "")),
            }
        )
    return items[:MAX_RECENT_RESULTS]


def write_recent_results(items: Sequence[Dict[str, str]], path: Path = RECENT_RESULTS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "recent_results": [
            {
                "title": str(item["title"]),
                "kind": str(item["kind"]),
                "description": str(item.get("description", "")),
                "left_result": str(item["left_result"]),
                "right_result": str(item.get("right_result", "")),
            }
            for item in items[:MAX_RECENT_RESULTS]
        ]
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def load_recent_result_item(item: Dict[str, str]) -> Tuple[Dict[str, object], Dict[str, object] | None]:
    left_result = load_existing_result_pair(_project_path(item["left_result"]))
    right_path = item.get("right_result", "")
    right_result = load_existing_result_pair(_project_path(right_path)) if right_path else None
    return left_result, right_result


def _favorite_comparison_item(
    title: str,
    *,
    note: str,
    left_path: Path,
    right_path: Path,
) -> Dict[str, str]:
    return {
        "title": title,
        "note": note,
        "left_result": _stored_result_path(left_path),
        "right_result": _stored_result_path(right_path),
    }


def read_favorite_comparisons(path: Path = FAVORITE_COMPARISONS_PATH) -> List[Dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    items: List[Dict[str, str]] = []
    for record in payload.get("favorite_comparisons", []):
        left_result = str(record.get("left_result", ""))
        right_result = str(record.get("right_result", ""))
        if not left_result or not right_result:
            continue
        items.append(
            {
                "title": str(record.get("title", "Favorite comparison")),
                "note": str(record.get("note", "")),
                "left_result": left_result,
                "right_result": right_result,
            }
        )
    return items[:MAX_FAVORITES]


def write_favorite_comparisons(items: Sequence[Dict[str, str]], path: Path = FAVORITE_COMPARISONS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "favorite_comparisons": [
            {
                "title": str(item["title"]),
                "note": str(item.get("note", "")),
                "left_result": str(item["left_result"]),
                "right_result": str(item["right_result"]),
            }
            for item in items[:MAX_FAVORITES]
        ]
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def load_favorite_comparison_item(item: Dict[str, str]) -> Tuple[Dict[str, object], Dict[str, object]]:
    left_result = load_existing_result_pair(_project_path(item["left_result"]))
    right_result = load_existing_result_pair(_project_path(item["right_result"]))
    return left_result, right_result


def read_gui_session_state(path: Path = GUI_SESSION_STATE_PATH) -> Dict[str, object] | None:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise TypeError("GUI session state must be a JSON object.")
    return payload


def write_gui_session_state(payload: Dict[str, object], path: Path = GUI_SESSION_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def detect_executable() -> Path | None:
    for candidate in (PROJECT_ROOT / "virtual_ecu", PROJECT_ROOT / "virtual_ecu.exe"):
        if candidate.exists():
            return candidate
    return None


def campaign_log_path(campaign_id: str, slot: str = "single") -> Path:
    return LOGS_DIR / f"gui_{slot}_{campaign_id}.csv"


def float_series(rows: Sequence[Dict[str, str]], key: str) -> List[float]:
    return [float(row[key]) for row in rows]


def int_series(rows: Sequence[Dict[str, str]], key: str) -> List[int]:
    return [int(float(row[key])) for row in rows]


def event_modes(first_row: Dict[str, str]) -> List[str]:
    modes = []

    for index in range(1, 5):
        mode_label = first_row.get(f"campaign_event_{index}_mode_label", "none")
        if mode_label and mode_label != "none":
            modes.append(mode_label)

    return modes


def event_behaviors(first_row: Dict[str, str]) -> List[str]:
    behaviors = []

    for index in range(1, 5):
        behavior_label = first_row.get(f"campaign_event_{index}_behavior_label", "none")
        if behavior_label and behavior_label != "none":
            behaviors.append(behavior_label)

    return behaviors


def infer_fault_class(first_row: Dict[str, str]) -> str:
    modes = event_modes(first_row)
    classes = {MODE_TO_CLASS.get(mode, "other fault") for mode in modes}

    if not modes:
        return "baseline"
    if len(classes) == 1:
        return next(iter(classes))
    return "mixed hardware-origin faults"


def campaign_story(campaign_id: str) -> Dict[str, str]:
    return CAMPAIGN_STORIES.get(
        campaign_id,
        {
            "campaign_name": campaign_id,
            "description": "No campaign-specific description is available.",
            "fault_class": "unknown",
            "hardware_source": "No campaign-specific cross-layer description is available.",
            "ecu_manifestation": "No campaign-specific ECU manifestation description is available.",
            "diagnostic_effect": "No campaign-specific diagnostic description is available.",
            "system_effect": "No campaign-specific system-level description is available.",
        },
    )


def format_latency(value: str) -> str:
    try:
        latency_ms = int(float(value))
    except (TypeError, ValueError):
        return "n/a"

    if latency_ms < 0:
        return "n/a"

    return f"{latency_ms} ms"


def format_temperature(value: str) -> str:
    try:
        return f"{float(value):.2f} C"
    except (TypeError, ValueError):
        return "n/a"


def summarize_fault_class(campaign_id: str, first_row: Dict[str, str] | None = None) -> str:
    if campaign_id in CAMPAIGN_STORIES:
        return CAMPAIGN_STORIES[campaign_id]["fault_class"]
    if first_row is not None:
        return infer_fault_class(first_row)
    return "unknown"


def metric_card_colors(metric_name: str, value: str) -> Tuple[str, str]:
    neutral = ("#eef3f7", "#1f2e3b")
    alert = ("#fce8e6", "#8a2f27")
    caution = ("#fff4dd", "#8a6120")
    info = ("#e8f0fb", "#1c4d8c")
    calm = ("#e8f4ec", "#245f3d")

    if value in {"n/a", "-", "none", "normal"}:
        return neutral

    if metric_name == "Final DTC":
        return alert if value != "none" else calm
    if metric_name == "Final Safe State":
        if value == "controlled_shutdown":
            return alert
        if value in {"limp_home", "precautionary_cooling"}:
            return caution
        return calm
    if metric_name == "Maximum Coolant Temperature":
        try:
            temp_c = float(value.split()[0])
        except (IndexError, ValueError):
            return neutral
        if temp_c >= 115.0:
            return alert
        if temp_c >= 108.0:
            return caution
        return calm
    if metric_name in {"Detection Latency", "Safe-State Latency"}:
        return info

    return neutral


def format_evidence_time(value: object) -> str:
    if value is None:
        return "n/a"

    try:
        return f"{float(value):.1f} s"
    except (TypeError, ValueError):
        return "n/a"


def wrap_evidence_text(value: str, *, width: int, max_lines: int = 2) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        return "n/a"

    lines = textwrap.wrap(normalized, width=width)
    if len(lines) <= max_lines:
        return "\n".join(lines)

    visible = lines[:max_lines]
    visible[-1] = textwrap.shorten(
        visible[-1] + " " + " ".join(lines[max_lines:]),
        width=width,
        placeholder="...",
    )
    return "\n".join(visible)


def _first_report_event(report: Dict[str, object], *, lane: str | None = None, effect_subtype: str | None = None) -> Dict[str, object] | None:
    for event in report.get("events", []):  # type: ignore[assignment]
        if lane is not None and event.get("lane") != lane:
            continue
        if effect_subtype is not None and event.get("effect_subtype") != effect_subtype:
            continue
        return event
    return None


def _chain_step(report: Dict[str, object], chain_stage: str) -> Dict[str, object] | None:
    for step in report.get("chain", []):  # type: ignore[assignment]
        if step.get("chain_stage") == chain_stage:
            return step
    return None


def _chain_evidence_row(
    run_label: str,
    report: Dict[str, object],
    *,
    stage_label: str,
    chain_stage: str,
    fallback_signal: str,
) -> Dict[str, str]:
    step = _chain_step(report, chain_stage)
    event = _first_report_event(report, lane=chain_stage)

    if step is None:
        return {
            "run": run_label,
            "stage": stage_label,
            "time": "n/a",
            "signal": fallback_signal,
            "explanation": "No evidence was extracted for this propagation stage.",
        }

    signal = str(event.get("signal", "")) if event is not None else ""
    if not signal:
        signal = str(step.get("evidence_label", fallback_signal))

    return {
        "run": run_label,
        "stage": stage_label,
        "time": format_evidence_time(step.get("evidence_time_s")),
        "signal": signal,
        "explanation": str(step.get("evidence_detail", "")),
    }


def _event_evidence_row(
    run_label: str,
    event: Dict[str, object] | None,
    *,
    stage_label: str,
    fallback_signal: str,
    fallback_explanation: str,
) -> Dict[str, str]:
    if event is None:
        return {
            "run": run_label,
            "stage": stage_label,
            "time": "n/a",
            "signal": fallback_signal,
            "explanation": fallback_explanation,
        }

    return {
        "run": run_label,
        "stage": stage_label,
        "time": format_evidence_time(event.get("time_s")),
        "signal": str(event.get("signal", fallback_signal)),
        "explanation": str(event.get("detail", fallback_explanation)),
    }


def propagation_evidence_rows(run_label: str, report: Dict[str, object]) -> List[Dict[str, str]]:
    """Summarize the report evidence shown beside the propagation timeline."""
    return [
        _chain_evidence_row(
            run_label,
            report,
            stage_label="Hardware-Origin Fault",
            chain_stage="hardware_origin",
            fallback_signal="fault injection schedule",
        ),
        _chain_evidence_row(
            run_label,
            report,
            stage_label="ECU-Visible Manifestation",
            chain_stage="ecu_manifestation",
            fallback_signal="ECU-visible fault manifestation",
        ),
        _chain_evidence_row(
            run_label,
            report,
            stage_label="First Diagnostic Evidence",
            chain_stage="diagnostic_effect",
            fallback_signal="primary_dtc_label",
        ),
        _event_evidence_row(
            run_label,
            _first_report_event(report, effect_subtype="safe_state"),
            stage_label="First Safe-State Transition",
            fallback_signal="safe_state_label",
            fallback_explanation="No non-normal safe-state transition occurred during this run.",
        ),
        _event_evidence_row(
            run_label,
            _first_report_event(report, effect_subtype="peak_temperature"),
            stage_label="Peak Thermal Severity",
            fallback_signal="coolant_temp_true_c",
            fallback_explanation="No peak-temperature evidence was extracted from the run.",
        ),
    ]


def comparison_export_dir(left_campaign_id: str, right_campaign_id: str) -> Path:
    return EXPORT_ROOT / f"{left_campaign_id}_vs_{right_campaign_id}"


def snapshot_export_dir(left_campaign_id: str, right_campaign_id: str) -> Path:
    return SNAPSHOT_ROOT / f"{left_campaign_id}_vs_{right_campaign_id}"


def presentation_bundle_dir(left_campaign_id: str, right_campaign_id: str) -> Path:
    return PRESENTATION_BUNDLE_ROOT / f"{left_campaign_id}_vs_{right_campaign_id}"


def write_report_csv(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["field", "left", "right"])
        writer.writeheader()
        writer.writerows(rows)


def write_snapshot_csv(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["section", "field", "left", "right", "value"])
        writer.writeheader()
        writer.writerows(rows)


def int_or_none(value: str) -> int | None:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return None if parsed < 0 else parsed


def float_or_none(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean_or_none(values: Sequence[float | int]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def mode_or_none(values: Iterable[str]) -> str:
    filtered = [value for value in values if isinstance(value, str) and value]
    if not filtered:
        return "n/a"

    counts: Dict[str, int] = {}
    for value in filtered:
        counts[value] = counts.get(value, 0) + 1

    top_count = max(counts.values())
    winners = sorted(value for value, count in counts.items() if count == top_count)
    return winners[0]


def safe_state_score(label: str) -> int:
    return SAFE_STATE_SEVERITY.get(label, 0)


def dtc_score(summary_row: Dict[str, str]) -> int:
    dtc_id = int_or_none(summary_row.get("final_primary_dtc_id", ""))
    if dtc_id is not None:
        return DTC_SEVERITY.get(dtc_id, 1 if dtc_id > 0 else 0)
    return 0 if summary_row.get("final_primary_dtc_label", "none") == "none" else 1


def summary_max_temp(summary_row: Dict[str, str]) -> float | None:
    return float_or_none(summary_row.get("max_coolant_temp_c", ""))


def summary_detection_latency(summary_row: Dict[str, str]) -> int | None:
    return int_or_none(summary_row.get("detection_latency_ms", ""))


def summary_safe_state_latency(summary_row: Dict[str, str]) -> int | None:
    return int_or_none(summary_row.get("safe_state_latency_ms", ""))


def summary_safe_mode_duration(summary_row: Dict[str, str]) -> int | None:
    return int_or_none(summary_row.get("safe_mode_duration_ms", ""))


def format_latency_value(value: int | None) -> str:
    return "n/a" if value is None else f"{value} ms"


def format_temp_value(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f} C"


def humanize_label(value: str) -> str:
    return value.replace("_", " ")


def normalize_safe_state_label(value: object) -> str:
    if value is None:
        return "unknown"

    text = str(value).strip()
    if not text:
        return "unknown"

    numeric_value = int_or_none(text)
    if numeric_value is not None:
        return SAFE_STATE_LABELS.get(numeric_value, text)

    normalized = text.lower().replace("-", "_").replace(" ", "_")
    return normalized


def safe_state_display_label(value: object) -> str:
    normalized = normalize_safe_state_label(value)
    if normalized == "unknown":
        return "Unknown"
    return humanize_label(normalized).title()


def compare_detection_statement(
    left_name: str,
    left_summary: Dict[str, str],
    right_name: str,
    right_summary: Dict[str, str],
) -> Tuple[str, str]:
    left_latency = summary_detection_latency(left_summary)
    right_latency = summary_detection_latency(right_summary)

    if left_latency is None and right_latency is None:
        return ("Detection", "Neither campaign confirms a fault during the run.")
    if left_latency is None:
        return ("Detection", f"{right_name} detects faster because it is the only case with confirmed fault detection ({right_latency} ms).")
    if right_latency is None:
        return ("Detection", f"{left_name} detects faster because it is the only case with confirmed fault detection ({left_latency} ms).")
    if left_latency < right_latency:
        return ("Detection", f"{left_name} detects faster ({left_latency} ms vs {right_latency} ms).")
    if right_latency < left_latency:
        return ("Detection", f"{right_name} detects faster ({right_latency} ms vs {left_latency} ms).")
    return ("Detection", f"Both campaigns detect at the same latency ({left_latency} ms).")


def comparison_verdict(
    left_name: str,
    left_summary: Dict[str, str],
    right_name: str,
    right_summary: Dict[str, str],
) -> Tuple[List[str], str]:
    verdict_lines: List[str] = []
    left_points = 0
    right_points = 0
    left_reasons: List[str] = []
    right_reasons: List[str] = []

    left_temp = summary_max_temp(left_summary)
    right_temp = summary_max_temp(right_summary)
    if left_temp is not None and right_temp is not None:
        if left_temp > right_temp:
            verdict_lines.append(
                f"Thermal severity: {left_name} peaks higher ({left_temp:.2f} C vs {right_temp:.2f} C)."
            )
            left_points += 1
            left_reasons.append("higher peak coolant temperature")
        elif right_temp > left_temp:
            verdict_lines.append(
                f"Thermal severity: {right_name} peaks higher ({right_temp:.2f} C vs {left_temp:.2f} C)."
            )
            right_points += 1
            right_reasons.append("higher peak coolant temperature")
        else:
            verdict_lines.append(f"Thermal severity: both sides reach the same peak coolant temperature ({left_temp:.2f} C).")
    else:
        verdict_lines.append("Thermal severity: peak coolant temperature is unavailable for one or both sides.")

    left_latency = summary_detection_latency(left_summary)
    right_latency = summary_detection_latency(right_summary)
    if left_latency is None and right_latency is None:
        verdict_lines.append("Fault detection: neither side confirms a fault during the run.")
    elif left_latency is None:
        verdict_lines.append(f"Fault detection: {right_name} detects first ({right_latency} ms); {left_name} has no confirmed detection.")
        right_points += 1
        right_reasons.append("faster confirmed detection")
    elif right_latency is None:
        verdict_lines.append(f"Fault detection: {left_name} detects first ({left_latency} ms); {right_name} has no confirmed detection.")
        left_points += 1
        left_reasons.append("faster confirmed detection")
    elif left_latency < right_latency:
        verdict_lines.append(f"Fault detection: {left_name} detects faster ({left_latency} ms vs {right_latency} ms).")
        left_points += 1
        left_reasons.append("faster confirmed detection")
    elif right_latency < left_latency:
        verdict_lines.append(f"Fault detection: {right_name} detects faster ({right_latency} ms vs {left_latency} ms).")
        right_points += 1
        right_reasons.append("faster confirmed detection")
    else:
        verdict_lines.append(f"Fault detection: both sides confirm at the same latency ({left_latency} ms).")

    left_state = left_summary.get("final_safe_state_label", "normal")
    right_state = right_summary.get("final_safe_state_label", "normal")
    left_state_score = safe_state_score(left_state)
    right_state_score = safe_state_score(right_state)
    left_safe_duration = summary_safe_mode_duration(left_summary) or 0
    right_safe_duration = summary_safe_mode_duration(right_summary) or 0
    left_safe_latency = summary_safe_state_latency(left_summary)
    right_safe_latency = summary_safe_state_latency(right_summary)

    left_safe_rank = (left_state_score, left_safe_duration, -(left_safe_latency if left_safe_latency is not None else 10**9))
    right_safe_rank = (right_state_score, right_safe_duration, -(right_safe_latency if right_safe_latency is not None else 10**9))
    if left_state_score > right_state_score:
        verdict_lines.append(
            f"Safe-state outcome: {left_name} reaches the harsher final protection state "
            f"({humanize_label(left_state)} vs {humanize_label(right_state)})."
        )
        left_points += 1
        left_reasons.append("more severe safe-state outcome")
    elif right_state_score > left_state_score:
        verdict_lines.append(
            f"Safe-state outcome: {right_name} reaches the harsher final protection state "
            f"({humanize_label(right_state)} vs {humanize_label(left_state)})."
        )
        right_points += 1
        right_reasons.append("more severe safe-state outcome")
    elif left_safe_duration > right_safe_duration:
        verdict_lines.append(
            f"Safe-state outcome: {left_name} spends longer in safe mode "
            f"({left_safe_duration} ms vs {right_safe_duration} ms total, first entry {format_latency_value(left_safe_latency)})."
        )
        left_points += 1
        left_reasons.append("longer safe-mode exposure")
    elif right_safe_duration > left_safe_duration:
        verdict_lines.append(
            f"Safe-state outcome: {right_name} spends longer in safe mode "
            f"({right_safe_duration} ms vs {left_safe_duration} ms total, first entry {format_latency_value(right_safe_latency)})."
        )
        right_points += 1
        right_reasons.append("longer safe-mode exposure")
    elif left_safe_latency is not None and right_safe_latency is not None and left_safe_latency < right_safe_latency:
        verdict_lines.append(
            f"Safe-state outcome: {left_name} enters protection earlier ({left_safe_latency} ms vs {right_safe_latency} ms)."
        )
        left_points += 1
        left_reasons.append("earlier protection entry")
    elif left_safe_latency is not None and right_safe_latency is not None and right_safe_latency < left_safe_latency:
        verdict_lines.append(
            f"Safe-state outcome: {right_name} enters protection earlier ({right_safe_latency} ms vs {left_safe_latency} ms)."
        )
        right_points += 1
        right_reasons.append("earlier protection entry")
    else:
        verdict_lines.append(
            f"Safe-state outcome: both sides finish at similar protection severity ({humanize_label(left_state)} vs {humanize_label(right_state)})."
        )

    left_dtc = left_summary.get("final_primary_dtc_label", "none")
    right_dtc = right_summary.get("final_primary_dtc_label", "none")
    left_end_rank = (dtc_score(left_summary), left_state_score, left_safe_duration)
    right_end_rank = (dtc_score(right_summary), right_state_score, right_safe_duration)
    if left_end_rank > right_end_rank:
        verdict_lines.append(
            f"End-of-run criticality: {left_name} finishes in the harsher end state ({humanize_label(left_dtc)} / {humanize_label(left_state)})."
        )
        left_points += 1
        left_reasons.append("harsher final DTC/safe-state combination")
    elif right_end_rank > left_end_rank:
        verdict_lines.append(
            f"End-of-run criticality: {right_name} finishes in the harsher end state ({humanize_label(right_dtc)} / {humanize_label(right_state)})."
        )
        right_points += 1
        right_reasons.append("harsher final DTC/safe-state combination")
    else:
        verdict_lines.append(
            f"End-of-run criticality: both sides finish with similar diagnostic/safety criticality ({humanize_label(left_dtc)} vs {humanize_label(right_dtc)})."
        )

    if left_points > right_points:
        reason_text = ", ".join(left_reasons[:2]) if left_reasons else "stronger overall comparison severity"
        takeaway = f"Overall takeaway: {left_name} is the stronger demonstration case overall, driven mainly by {reason_text}."
    elif right_points > left_points:
        reason_text = ", ".join(right_reasons[:2]) if right_reasons else "stronger overall comparison severity"
        takeaway = f"Overall takeaway: {right_name} is the stronger demonstration case overall, driven mainly by {reason_text}."
    else:
        takeaway = (
            f"Overall takeaway: the two cases are fairly balanced overall, so the best presentation choice depends on "
            "whether you want to emphasize thermal severity, detection timing, or safe-state behavior."
        )

    return verdict_lines, takeaway


def comparison_findings(
    left_name: str,
    left_summary: Dict[str, str],
    right_name: str,
    right_summary: Dict[str, str],
) -> Tuple[List[str], List[str]]:
    lines: List[str] = []
    interpretation: List[str] = []

    left_temp = summary_max_temp(left_summary)
    right_temp = summary_max_temp(right_summary)
    if left_temp is not None and right_temp is not None:
        if left_temp > right_temp:
            thermal_line = f"Thermal severity: {left_name} is more severe ({left_temp:.2f} C vs {right_temp:.2f} C peak coolant)."
            thermal_winner = left_name
        elif right_temp > left_temp:
            thermal_line = f"Thermal severity: {right_name} is more severe ({right_temp:.2f} C vs {left_temp:.2f} C peak coolant)."
            thermal_winner = right_name
        else:
            thermal_line = f"Thermal severity: both campaigns reach the same peak coolant temperature ({left_temp:.2f} C)."
            thermal_winner = "both campaigns"
    else:
        thermal_line = "Thermal severity: peak coolant temperature is not available for one or both campaigns."
        thermal_winner = "neither campaign"
    lines.append(thermal_line)

    _label, detection_line = compare_detection_statement(left_name, left_summary, right_name, right_summary)
    lines.append(f"Fault detection: {detection_line.split(': ', 1)[-1] if ': ' in detection_line else detection_line}")

    left_state = left_summary.get("final_safe_state_label", "normal")
    right_state = right_summary.get("final_safe_state_label", "normal")
    left_state_score = safe_state_score(left_state)
    right_state_score = safe_state_score(right_state)
    left_safe_duration = summary_safe_mode_duration(left_summary) or 0
    right_safe_duration = summary_safe_mode_duration(right_summary) or 0

    if (left_state_score, left_safe_duration) > (right_state_score, right_safe_duration):
        safe_winner = left_name
        safe_line = (
            f"Safe-state impact: {left_name} is stronger "
            f"({humanize_label(left_state)} final state, {format_latency_value(summary_safe_state_latency(left_summary))} entry, {left_safe_duration} ms safe-mode duration)."
        )
    elif (right_state_score, right_safe_duration) > (left_state_score, left_safe_duration):
        safe_winner = right_name
        safe_line = (
            f"Safe-state impact: {right_name} is stronger "
            f"({humanize_label(right_state)} final state, {format_latency_value(summary_safe_state_latency(right_summary))} entry, {right_safe_duration} ms safe-mode duration)."
        )
    else:
        safe_winner = "both campaigns"
        safe_line = f"Safe-state impact: both campaigns finish with comparable safe-state severity ({humanize_label(left_state)} vs {humanize_label(right_state)})."
    lines.append(safe_line)

    left_dtc = left_summary.get("final_primary_dtc_label", "none")
    right_dtc = right_summary.get("final_primary_dtc_label", "none")
    left_dtc_score = dtc_score(left_summary)
    right_dtc_score = dtc_score(right_summary)
    if (left_dtc_score, left_state_score) > (right_dtc_score, right_state_score):
        critical_winner = left_name
        critical_line = f"Critical end state: {left_name} is more critical at the end of the run ({humanize_label(left_dtc)} / {humanize_label(left_state)})."
    elif (right_dtc_score, right_state_score) > (left_dtc_score, left_state_score):
        critical_winner = right_name
        critical_line = f"Critical end state: {right_name} is more critical at the end of the run ({humanize_label(right_dtc)} / {humanize_label(right_state)})."
    else:
        critical_winner = "both campaigns"
        critical_line = f"Critical end state: both campaigns finish with similar end-of-run criticality ({humanize_label(left_dtc)} / {humanize_label(left_state)} vs {humanize_label(right_dtc)} / {humanize_label(right_state)})."
    lines.append(critical_line)

    interpretation.append(f"{thermal_winner.capitalize() if thermal_winner != 'both campaigns' else 'The two cases'} drives the stronger thermal outcome in this comparison.")
    interpretation.append(detection_line)
    interpretation.append(f"{safe_winner.capitalize() if safe_winner != 'both campaigns' else 'Both campaigns'} shows the stronger protection response at ECU safe-state level.")
    interpretation.append(f"{critical_winner.capitalize() if critical_winner != 'both campaigns' else 'The end states'} gives the more critical end-of-run diagnostic/safety outcome.")

    return lines, interpretation


def batch_findings(rows: Sequence[Dict[str, str]]) -> Tuple[List[str], List[str]]:
    fault_types = [fault_type for fault_type in FAULT_TYPE_ORDER if fault_type != "none" and any(row["fault_type"] == fault_type for row in rows)]
    type_rows = {fault_type: [row for row in rows if row["fault_type"] == fault_type] for fault_type in fault_types}

    detection_means = {
        fault_type: mean_or_none(
            [value for value in (int_or_none(row.get("detection_latency_ms", "")) for row in type_rows[fault_type]) if value is not None]
        )
        for fault_type in fault_types
    }
    temp_means = {
        fault_type: mean_or_none(
            [value for value in (float_or_none(row.get("max_coolant_temperature_c", "")) for row in type_rows[fault_type]) if value is not None]
        )
        for fault_type in fault_types
    }
    safe_duration_means = {
        fault_type: mean_or_none(
            [value for value in (int_or_none(row.get("safe_mode_duration_ms", "")) for row in type_rows[fault_type]) if value is not None]
        )
        for fault_type in fault_types
    }
    safe_state_scores = {
        fault_type: mean_or_none([safe_state_score(row.get("final_safe_state", "normal")) for row in type_rows[fault_type]])
        for fault_type in fault_types
    }

    valid_detection = {fault_type: value for fault_type, value in detection_means.items() if value is not None}
    fastest_detection = min(valid_detection, key=valid_detection.get) if valid_detection else None
    hottest_fault = max(temp_means, key=lambda fault_type: temp_means[fault_type] or float("-inf")) if temp_means else None
    strongest_safe = max(
        fault_types,
        key=lambda fault_type: (
            safe_state_scores.get(fault_type) or 0.0,
            safe_duration_means.get(fault_type) or 0.0,
            -(detection_means.get(fault_type) or 1_000_000.0),
        ),
    ) if fault_types else None

    lines: List[str] = []
    interpretation: List[str] = []

    if fastest_detection is not None:
        lines.append(
            f"Fastest mean detection: {FAULT_TYPE_DISPLAY.get(fastest_detection, fastest_detection)} ({detection_means[fastest_detection]:.1f} ms)."
        )
    else:
        lines.append("Fastest mean detection: no fault type shows confirmed detection in the loaded batch.")

    if hottest_fault is not None and temp_means[hottest_fault] is not None:
        lines.append(
            f"Highest mean max coolant temperature: {FAULT_TYPE_DISPLAY.get(hottest_fault, hottest_fault)} ({temp_means[hottest_fault]:.2f} C)."
        )
    else:
        lines.append("Highest mean max coolant temperature: not available from the loaded batch.")

    if strongest_safe is not None:
        lines.append(
            f"Strongest safe-state effect: {FAULT_TYPE_DISPLAY.get(strongest_safe, strongest_safe)} "
            f"(mean final-state severity {safe_state_scores[strongest_safe]:.2f}, mean safe-mode duration {(safe_duration_means[strongest_safe] or 0.0):.1f} ms)."
        )
    else:
        lines.append("Strongest safe-state effect: not available from the loaded batch.")

    timing_mean_temp = temp_means.get("stale_sensor_data")
    timing_safe_score = safe_state_scores.get("stale_sensor_data")
    timing_is_meaningful = (
        "stale_sensor_data" in type_rows
        and (
            (timing_mean_temp is not None and timing_mean_temp >= 108.0)
            or (timing_safe_score is not None and timing_safe_score > 0.0)
            or ((safe_duration_means.get("stale_sensor_data") or 0.0) > 0.0)
        )
    )
    if "stale_sensor_data" in type_rows:
        meaning = "does" if timing_is_meaningful else "does not yet"
        lines.append(
            f"Timing/communication case: Stale Sensor Data {meaning} appear as a meaningful study case "
            f"({format_temp_value(timing_mean_temp)} mean peak coolant, {(safe_duration_means.get('stale_sensor_data') or 0.0):.1f} ms mean safe-mode duration)."
        )
    else:
        lines.append("Timing/communication case: no stale-sensor-data runs are present in the loaded batch.")

    if hottest_fault is not None:
        interpretation.append(
            f"{FAULT_TYPE_DISPLAY.get(hottest_fault, hottest_fault)} currently drives the strongest thermal excursion in the aggregate study."
        )
    if fastest_detection is not None:
        interpretation.append(
            f"{FAULT_TYPE_DISPLAY.get(fastest_detection, fastest_detection)} is the most observable fault family at mean detection-latency level."
        )
    if strongest_safe is not None:
        interpretation.append(
            f"{FAULT_TYPE_DISPLAY.get(strongest_safe, strongest_safe)} shows the strongest protection-state consequence across the loaded batch."
        )
    interpretation.append(
        "The timing/communication path is now treated as a meaningful study case when stale-sensor-data runs produce clear thermal or protection impact."
        if timing_is_meaningful
        else "The timing/communication path is present, but its batch-level consequence remains milder than the strongest actuation or mixed-fault cases."
    )

    return lines, interpretation


def render_snapshot_markdown(snapshot: Dict[str, object]) -> str:
    left_campaign_id = str(snapshot["left_campaign_id"])
    right_campaign_id = str(snapshot["right_campaign_id"])
    left_campaign_name = str(snapshot["left_campaign_name"])
    right_campaign_name = str(snapshot["right_campaign_name"])
    left_fault_class = str(snapshot["left_fault_class"])
    right_fault_class = str(snapshot["right_fault_class"])
    metrics = snapshot["metrics"]  # type: ignore[assignment]
    findings = snapshot["findings"]  # type: ignore[assignment]
    interpretation = snapshot["interpretation"]  # type: ignore[assignment]

    lines = [
        "# Virtual ECU Results Snapshot",
        "",
        "## Comparison",
        "",
        f"- Left campaign: `{left_campaign_id}` ({left_campaign_name})",
        f"- Right campaign: `{right_campaign_id}` ({right_campaign_name})",
        f"- Left fault class: {left_fault_class}",
        f"- Right fault class: {right_fault_class}",
        "",
        "## Key Metrics",
        "",
        "| Metric | Left | Right |",
        "| --- | --- | --- |",
    ]

    for metric_name, values in metrics:
        lines.append(f"| {metric_name} | {values['left']} | {values['right']} |")

    lines.extend(["", "## Key Findings", ""])
    lines.extend(f"- {line}" for line in findings)
    lines.extend(["", "## Interpretation", ""])
    lines.extend(f"- {line}" for line in interpretation)
    lines.append("")
    return "\n".join(lines)


def snapshot_csv_rows(snapshot: Dict[str, object]) -> List[Dict[str, str]]:
    rows = [
        {
            "section": "comparison",
            "field": "left_campaign",
            "left": str(snapshot["left_campaign_id"]),
            "right": "",
            "value": str(snapshot["left_campaign_name"]),
        },
        {
            "section": "comparison",
            "field": "right_campaign",
            "left": "",
            "right": str(snapshot["right_campaign_id"]),
            "value": str(snapshot["right_campaign_name"]),
        },
        {
            "section": "comparison",
            "field": "fault_class",
            "left": str(snapshot["left_fault_class"]),
            "right": str(snapshot["right_fault_class"]),
            "value": "",
        },
    ]

    for metric_name, values in snapshot["metrics"]:  # type: ignore[index]
        rows.append(
            {
                "section": "metrics",
                "field": metric_name.lower().replace(" ", "_"),
                "left": values["left"],
                "right": values["right"],
                "value": "",
            }
        )

    for index, line in enumerate(snapshot["findings"], start=1):  # type: ignore[index]
        rows.append(
            {
                "section": "findings",
                "field": f"finding_{index}",
                "left": "",
                "right": "",
                "value": str(line),
            }
        )

    for index, line in enumerate(snapshot["interpretation"], start=1):  # type: ignore[index]
        rows.append(
            {
                "section": "interpretation",
                "field": f"line_{index}",
                "left": "",
                "right": "",
                "value": str(line),
            }
        )

    return rows


def save_snapshot_overview_image(path: Path, snapshot: Dict[str, object]) -> None:
    metrics = snapshot["metrics"]  # type: ignore[assignment]
    findings = snapshot["findings"]  # type: ignore[assignment]
    interpretation = snapshot["interpretation"]  # type: ignore[assignment]

    summary_lines = [
        f"Left: {snapshot['left_campaign_name']} ({snapshot['left_campaign_id']})",
        f"Right: {snapshot['right_campaign_name']} ({snapshot['right_campaign_id']})",
        f"Left fault class: {snapshot['left_fault_class']}",
        f"Right fault class: {snapshot['right_fault_class']}",
        "",
        "Key Metrics",
    ]
    for metric_name, values in metrics:
        summary_lines.append(f"{metric_name}: L={values['left']} | R={values['right']}")

    finding_lines = ["Key Findings"]
    finding_lines.extend(f"- {line}" for line in findings)

    interpretation_lines = ["Interpretation"]
    for line in interpretation:
        interpretation_lines.extend(textwrap.wrap(line, width=52) or [line])

    fig = plt.figure(figsize=(12, 8), constrained_layout=True)
    fig.patch.set_facecolor("#f4f6f8")
    grid = fig.add_gridspec(2, 2, height_ratios=[3, 2], width_ratios=[3, 2])

    title_ax = fig.add_subplot(grid[0, 0])
    findings_ax = fig.add_subplot(grid[0, 1])
    interpretation_ax = fig.add_subplot(grid[1, :])

    for axis in (title_ax, findings_ax, interpretation_ax):
        axis.axis("off")

    title_ax.text(
        0.0,
        1.0,
        "Virtual ECU Results Snapshot",
        fontsize=18,
        fontweight="bold",
        color="#1d3448",
        va="top",
    )
    title_ax.text(
        0.0,
        0.92,
        "\n".join(summary_lines),
        fontsize=11,
        color="#22313f",
        va="top",
        linespacing=1.5,
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#ffffff", "edgecolor": "#d8e0e7"},
    )
    findings_ax.text(
        0.0,
        1.0,
        "\n".join(finding_lines),
        fontsize=11,
        color="#22313f",
        va="top",
        linespacing=1.5,
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#ffffff", "edgecolor": "#d8e0e7"},
    )
    interpretation_ax.text(
        0.0,
        1.0,
        "\n".join(interpretation_lines),
        fontsize=11,
        color="#425160",
        va="top",
        linespacing=1.6,
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#ffffff", "edgecolor": "#d8e0e7"},
    )

    fig.savefig(path, dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)


def write_snapshot_bundle(export_dir: Path, snapshot: Dict[str, object]) -> List[Path]:
    export_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

    markdown_path = export_dir / "snapshot_summary.md"
    csv_path = export_dir / "snapshot_summary.csv"
    image_path = export_dir / "snapshot_overview.png"

    markdown_path.write_text(render_snapshot_markdown(snapshot), encoding="utf-8")
    write_snapshot_csv(csv_path, snapshot_csv_rows(snapshot))
    save_snapshot_overview_image(image_path, snapshot)

    return [markdown_path, csv_path, image_path]


def render_presentation_bundle_markdown(
    snapshot: Dict[str, object],
    verdict_lines: Sequence[str],
    takeaway_line: str,
    findings_lines: Sequence[str],
    interpretation_lines: Sequence[str],
) -> str:
    lines = [
        "# Virtual ECU Presentation Bundle",
        "",
        "## Comparison",
        "",
        f"- Left campaign: `{snapshot['left_campaign_id']}` ({snapshot['left_campaign_name']})",
        f"- Right campaign: `{snapshot['right_campaign_id']}` ({snapshot['right_campaign_name']})",
        f"- Left fault class: {snapshot['left_fault_class']}",
        f"- Right fault class: {snapshot['right_fault_class']}",
        "",
        "## Verdict",
        "",
    ]
    lines.extend(f"- {line}" for line in verdict_lines)
    lines.extend(["", "## Key Takeaway", "", takeaway_line, "", "## Key Metrics", "", "| Metric | Left | Right |", "| --- | --- | --- |"])

    for metric_name, values in snapshot["metrics"]:  # type: ignore[index]
        lines.append(f"| {metric_name} | {values['left']} | {values['right']} |")

    lines.extend(["", "## Findings", ""])
    lines.extend(f"- {line}" for line in findings_lines)
    lines.extend(["", "## Interpretation", ""])
    lines.extend(f"- {line}" for line in interpretation_lines)
    lines.append("")
    return "\n".join(lines)


def write_presentation_bundle_text(
    path: Path,
    snapshot: Dict[str, object],
    verdict_lines: Sequence[str],
    takeaway_line: str,
    findings_lines: Sequence[str],
    interpretation_lines: Sequence[str],
) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write("Virtual ECU Presentation Bundle\n")
        handle.write(f"Left campaign: {snapshot['left_campaign_id']} ({snapshot['left_campaign_name']})\n")
        handle.write(f"Right campaign: {snapshot['right_campaign_id']} ({snapshot['right_campaign_name']})\n")
        handle.write(f"Left fault class: {snapshot['left_fault_class']}\n")
        handle.write(f"Right fault class: {snapshot['right_fault_class']}\n\n")
        handle.write("Verdict\n")
        for line in verdict_lines:
            handle.write(f"- {line}\n")
        handle.write(f"\nKey takeaway\n{takeaway_line}\n\n")
        handle.write("Findings\n")
        for line in findings_lines:
            handle.write(f"- {line}\n")
        handle.write("\nInterpretation\n")
        for line in interpretation_lines:
            handle.write(f"- {line}\n")


def write_presentation_bundle_csv(path: Path, snapshot: Dict[str, object], takeaway_line: str) -> None:
    rows = snapshot_csv_rows(snapshot)
    rows.append(
        {
            "section": "verdict",
            "field": "key_takeaway",
            "left": "",
            "right": "",
            "value": takeaway_line,
        }
    )
    write_snapshot_csv(path, rows)


def write_comparison_report_bundle(
    export_dir: Path,
    left_campaign_id: str,
    right_campaign_id: str,
    left_fault_class: str,
    right_fault_class: str,
    metric_names: Sequence[str],
    summary_vars: Dict[str, Dict[str, tk.StringVar]],
    left_label: str,
    left_rows: Sequence[Dict[str, str]],
    right_label: str,
    right_rows: Sequence[Dict[str, str]],
) -> List[Path]:
    export_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

    report_rows = [
        {"field": "left_campaign_id", "left": left_campaign_id, "right": ""},
        {"field": "right_campaign_id", "left": right_campaign_id, "right": ""},
        {"field": "left_fault_class", "left": left_fault_class, "right": ""},
        {"field": "right_fault_class", "left": right_fault_class, "right": ""},
    ]

    for metric_name in metric_names:
        report_rows.append(
            {
                "field": metric_name.lower().replace(" ", "_"),
                "left": summary_vars["left"][metric_name].get(),
                "right": summary_vars["right"][metric_name].get(),
            }
        )

    csv_path = export_dir / "comparison_summary.csv"
    text_path = export_dir / "comparison_summary.txt"
    coolant_path = export_dir / "coolant_temperature_comparison.png"
    safe_state_path = export_dir / "safe_state_comparison.png"

    write_report_csv(csv_path, report_rows)

    with text_path.open("w", encoding="utf-8") as handle:
        handle.write("Virtual ECU Comparison Report\n")
        handle.write(f"Left campaign: {left_campaign_id}\n")
        handle.write(f"Right campaign: {right_campaign_id}\n")
        handle.write(f"Left fault class: {left_fault_class}\n")
        handle.write(f"Right fault class: {right_fault_class}\n\n")
        for metric_name in metric_names:
            handle.write(
                f"{metric_name}: left={summary_vars['left'][metric_name].get()}, "
                f"right={summary_vars['right'][metric_name].get()}\n"
            )

    save_coolant_comparison_plot(left_label, left_rows, right_label, right_rows, coolant_path)
    save_safe_state_comparison_plot(left_label, left_rows, right_label, right_rows, safe_state_path)

    generated_files = [csv_path, text_path, coolant_path, safe_state_path]
    left_permanent = bool(left_rows) and "permanent" in event_behaviors(left_rows[0])
    right_permanent = bool(right_rows) and "permanent" in event_behaviors(right_rows[0])
    if left_permanent or right_permanent:
        fan_path = export_dir / "fan_comparison.png"
        save_fan_comparison_plot(left_label, left_rows, right_label, right_rows, fan_path)
        generated_files.append(fan_path)

    generated_files.extend(save_propagation_comparison_bundle(export_dir, left_label, left_rows, right_label, right_rows))
    return generated_files


def save_coolant_comparison_plot(
    left_label: str,
    left_rows: Sequence[Dict[str, str]],
    right_label: str,
    right_rows: Sequence[Dict[str, str]],
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 4.8), constrained_layout=True)
    ax.plot(float_series(left_rows, "time_s"), float_series(left_rows, "coolant_temp_true_c"), color=LEFT_COLOR, linewidth=2.2, label=left_label)
    ax.plot(float_series(right_rows, "time_s"), float_series(right_rows, "coolant_temp_true_c"), color=RIGHT_COLOR, linewidth=2.2, linestyle="--", label=right_label)
    ax.axhline(108.0, color="#8c6b2d", linestyle="--", linewidth=1.1)
    ax.axhline(115.0, color="#7b4d57", linestyle=":", linewidth=1.1)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Coolant Temperature [C]")
    ax.set_title("Coolant Temperature Comparison")
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.8)
    ax.legend(loc="upper left", frameon=False)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def save_safe_state_comparison_plot(
    left_label: str,
    left_rows: Sequence[Dict[str, str]],
    right_label: str,
    right_rows: Sequence[Dict[str, str]],
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 4.8), constrained_layout=True)
    ax.step(float_series(left_rows, "time_s"), int_series(left_rows, "safe_state_id"), where="post", color=LEFT_COLOR, linewidth=2.2, label=left_label)
    ax.step(float_series(right_rows, "time_s"), int_series(right_rows, "safe_state_id"), where="post", color=RIGHT_COLOR, linewidth=2.2, linestyle="--", label=right_label)
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(["Normal", "Precautionary", "Limp Home", "Shutdown"])
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Safe State")
    ax.set_title("Safe-State Comparison")
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.8)
    ax.legend(loc="upper left", frameon=False)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def save_fan_comparison_plot(
    left_label: str,
    left_rows: Sequence[Dict[str, str]],
    right_label: str,
    right_rows: Sequence[Dict[str, str]],
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 4.8), constrained_layout=True)
    ax.plot(float_series(left_rows, "time_s"), float_series(left_rows, "fan_command"), color=LEFT_COLOR, linewidth=2.2, label=f"{left_label} command")
    ax.plot(float_series(left_rows, "time_s"), float_series(left_rows, "fan_actual"), color="#7d1f17", linewidth=1.8, linestyle=":", label=f"{left_label} actual")
    ax.plot(float_series(right_rows, "time_s"), float_series(right_rows, "fan_command"), color=RIGHT_COLOR, linewidth=2.2, linestyle="--", label=f"{right_label} command")
    ax.plot(float_series(right_rows, "time_s"), float_series(right_rows, "fan_actual"), color="#5e7fb0", linewidth=1.8, linestyle="-.", label=f"{right_label} actual")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Fan [-]")
    ax.set_ylim(0.0, 1.05)
    ax.set_title("Fan Command / Actual Comparison")
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.8)
    ax.legend(loc="upper left", ncol=2, frameon=False)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def save_propagation_comparison_bundle(
    export_dir: Path,
    left_label: str,
    left_rows: Sequence[Dict[str, str]],
    right_label: str,
    right_rows: Sequence[Dict[str, str]],
) -> List[Path]:
    left_report = build_propagation_report(left_rows)
    right_report = build_propagation_report(right_rows)

    csv_path = export_dir / "cross_layer_propagation_timeline.csv"
    summary_path = export_dir / "cross_layer_propagation_summary.txt"
    figure_path = export_dir / "cross_layer_propagation_timeline.png"

    write_propagation_csv(
        csv_path,
        [
            *propagation_csv_rows("left", left_report),
            *propagation_csv_rows("right", right_report),
        ],
    )
    write_propagation_summary(summary_path, [left_report, right_report], [left_label, right_label])
    save_propagation_plot(
        [left_label, right_label],
        [left_report, right_report],
        figure_path,
    )

    return [csv_path, summary_path, figure_path]


class PlotCanvas(ttk.Frame):
    """Small reusable plotting widget backed by a Tkinter Canvas."""

    def __init__(self, master: tk.Misc, title: str, *, canvas_height: int = 220) -> None:
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.title_var = tk.StringVar(value=title)
        self.base_canvas_height = canvas_height
        self.presentation_mode = False

        self.title_label = ttk.Label(self, textvariable=self.title_var, style="Section.TLabel")
        self.title_label.grid(
            row=0, column=0, sticky="w", padx=6, pady=(0, 4)
        )

        self.canvas = tk.Canvas(
            self,
            background="#ffffff",
            height=canvas_height,
            highlightthickness=1,
            highlightbackground="#c7d0d9",
        )
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _event: self.redraw())
        self._drawer = self._draw_message
        self._payload: object = "No data loaded yet."

    def set_title(self, title: str) -> None:
        self.title_var.set(title)

    def set_presentation_mode(self, enabled: bool) -> None:
        self.presentation_mode = enabled
        extra_height = 80 if enabled and self.base_canvas_height >= 600 else 40 if enabled else 0
        self.canvas.configure(height=self.base_canvas_height + extra_height)
        self.redraw()

    def show_message(self, text: str) -> None:
        self._drawer = self._draw_message
        self._payload = text
        self.redraw()

    def plot_lines(
        self,
        series: Sequence[Tuple[str, str, Sequence[float], Sequence[float], Tuple[int, ...] | None]],
        *,
        y_label: str,
        y_min: float | None = None,
        y_max: float | None = None,
        threshold_lines: Sequence[Tuple[float, str, str]] = (),
    ) -> None:
        self._drawer = self._draw_line_plot
        self._payload = {
            "series": [
                (label, color, list(x_values), list(y_values), dash)
                for label, color, x_values, y_values, dash in series
            ],
            "y_label": y_label,
            "y_min": y_min,
            "y_max": y_max,
            "threshold_lines": list(threshold_lines),
        }
        self.redraw()

    def plot_step_series(
        self,
        x_values: Sequence[float],
        y_values: Sequence[int],
        *,
        y_label: str,
        tick_labels: Dict[int, str],
    ) -> None:
        self._drawer = self._draw_step_plot
        self._payload = {
            "x_values": list(x_values),
            "y_values": list(y_values),
            "y_label": y_label,
            "tick_labels": dict(tick_labels),
        }
        self.redraw()

    def plot_step_comparison(
        self,
        series: Sequence[Tuple[str, str, Sequence[float], Sequence[int], Tuple[int, ...] | None]],
        *,
        y_label: str,
        tick_labels: Dict[int, str],
    ) -> None:
        self._drawer = self._draw_step_comparison_plot
        self._payload = {
            "series": [
                (label, color, list(x_values), list(y_values), dash)
                for label, color, x_values, y_values, dash in series
            ],
            "y_label": y_label,
            "tick_labels": dict(tick_labels),
        }
        self.redraw()

    def plot_bars(
        self,
        categories: Sequence[str],
        values: Sequence[float | None],
        *,
        y_label: str,
        bar_color: str = "#4c78a8",
    ) -> None:
        self._drawer = self._draw_bar_plot
        self._payload = {
            "categories": list(categories),
            "values": list(values),
            "y_label": y_label,
            "bar_color": bar_color,
        }
        self.redraw()

    def plot_stacked_bars(
        self,
        categories: Sequence[str],
        stacks: Sequence[Tuple[str, str, Sequence[float]]],
        *,
        y_label: str,
        max_value: float = 100.0,
        x_label: str = "Fault Type",
    ) -> None:
        self._drawer = self._draw_stacked_bar_plot
        self._payload = {
            "categories": list(categories),
            "stacks": [
                (label, color, list(values))
                for label, color, values in stacks
            ],
            "y_label": y_label,
            "max_value": max_value,
            "x_label": x_label,
        }
        self.redraw()

    def plot_propagation_timeline(
        self,
        labels: Sequence[str],
        reports: Sequence[Dict[str, object]],
    ) -> None:
        self._drawer = self._draw_propagation_timeline
        self._payload = {
            "labels": list(labels),
            "reports": list(reports),
        }
        self.redraw()

    def redraw(self) -> None:
        self.canvas.delete("all")
        self._drawer(self._payload)

    def _canvas_size(self) -> Tuple[int, int]:
        width = max(self.canvas.winfo_width(), 280)
        height = max(self.canvas.winfo_height(), 200)
        return width, height

    def _font(self, role: str) -> Tuple[str, int] | Tuple[str, int, str]:
        presentation = self.presentation_mode
        if role == "message":
            return ("TkDefaultFont", 12 if presentation else 10, "bold" if presentation else "normal")
        if role == "axis_label":
            return ("TkDefaultFont", 11 if presentation else 10, "bold" if presentation else "normal")
        if role == "tick":
            return ("TkDefaultFont", 10 if presentation else 9)
        if role == "legend":
            return ("TkDefaultFont", 10 if presentation else 9)
        if role == "threshold":
            return ("TkDefaultFont", 10 if presentation else 9, "bold" if presentation else "normal")
        if role == "bar_value":
            return ("TkDefaultFont", 10 if presentation else 9, "bold")
        return ("TkDefaultFont", 10)

    def _line_width(self, emphasis: bool = False) -> int:
        if self.presentation_mode:
            return 3 if emphasis else 2
        return 2 if emphasis else 1

    def _text_width(self, text: str, role: str) -> int:
        font = tkfont.Font(font=self._font(role))
        return int(font.measure(text))

    def _axis_left_margin(
        self,
        y_label: str,
        *,
        y_tick_labels: Sequence[str] = (),
        extra_left_margin: int = 0,
    ) -> int:
        base = 88 if self.presentation_mode else 82
        tick_width = max((self._text_width(label, "tick") for label in y_tick_labels), default=0)
        label_space = self._text_width(y_label, "axis_label")
        return max(base, tick_width + 30, min(128 if self.presentation_mode else 118, label_space + 22)) + extra_left_margin

    def _plot_bounds(
        self,
        *,
        left_margin: int = 82,
        top_margin: int = 18,
        right_margin: int = 34,
        bottom_margin: int = 54,
    ) -> Tuple[int, int, int, int]:
        width, height = self._canvas_size()
        left = left_margin
        top = top_margin
        right = max(width - right_margin, left + 40)
        bottom = max(height - bottom_margin, top + 40)
        return left, top, right, bottom

    def _draw_axes(
        self,
        y_label: str,
        x_label: str = "Time [s]",
        *,
        y_tick_labels: Sequence[str] = (),
        left_margin: int | None = None,
        top_margin: int = 18,
        right_margin: int = 34,
        bottom_margin: int = 54,
        extra_left_margin: int = 0,
    ) -> Tuple[int, int, int, int]:
        resolved_left_margin = left_margin if left_margin is not None else self._axis_left_margin(
            y_label,
            y_tick_labels=y_tick_labels,
            extra_left_margin=extra_left_margin,
        )
        left, top, right, bottom = self._plot_bounds(
            left_margin=resolved_left_margin,
            top_margin=top_margin,
            right_margin=right_margin,
            bottom_margin=bottom_margin,
        )
        self.canvas.create_line(left, bottom, right, bottom, fill="#4a5560", width=self._line_width())
        self.canvas.create_line(left, bottom, left, top, fill="#4a5560", width=self._line_width())
        self.canvas.create_text(
            (left + right) / 2,
            bottom + (30 if self.presentation_mode else 26),
            text=x_label,
            fill="#33404d",
            font=self._font("axis_label"),
        )
        self.canvas.create_text(
            max(18, left - (58 if self.presentation_mode else 52)),
            (top + bottom) / 2,
            text=y_label,
            fill="#33404d",
            angle=90,
            font=self._font("axis_label"),
        )
        return left, top, right, bottom

    def _legend_rows(
        self,
        entries: Sequence[Tuple[str, str, Tuple[int, ...] | None]],
        available_width: float,
    ) -> List[List[Tuple[str, str, Tuple[int, ...] | None]]]:
        rows: List[List[Tuple[str, str, Tuple[int, ...] | None]]] = []
        current_row: List[Tuple[str, str, Tuple[int, ...] | None]] = []
        current_width = 0.0

        for label, color, dash in entries:
            entry_width = 48 + len(label) * (7.6 if self.presentation_mode else 6.8)
            if current_row and current_width + entry_width > available_width:
                rows.append(current_row)
                current_row = []
                current_width = 0.0
            current_row.append((label, color, dash))
            current_width += entry_width

        if current_row:
            rows.append(current_row)

        return rows

    def _draw_legend(
        self,
        entries: Sequence[Tuple[str, str, Tuple[int, ...] | None]],
        *,
        left: int,
        top: int,
        right: int,
    ) -> int:
        if not entries:
            return 0

        rows = self._legend_rows(entries, max(right - left - 8, 120))
        y_pos = top
        for row in rows:
            x_pos = left
            for label, color, dash in row:
                self.canvas.create_line(
                    x_pos,
                    y_pos + 6,
                    x_pos + 18,
                    y_pos + 6,
                    fill=color,
                    width=self._line_width(emphasis=True),
                    dash=dash or (),
                )
                self.canvas.create_text(
                    x_pos + 24,
                    y_pos + 6,
                    text=label,
                    anchor="w",
                    fill="#33404d",
                    font=self._font("legend"),
                )
                x_pos += 48 + len(label) * (7.6 if self.presentation_mode else 6.8)
            y_pos += 22 if self.presentation_mode else 18

        row_height = 22 if self.presentation_mode else 18
        return max(row_height * len(rows) + 8, 0)

    def _bottom_margin_for_categories(self, categories: Sequence[str]) -> int:
        if not categories:
            return 64 if self.presentation_mode else 56
        longest = max(len(category) for category in categories)
        if longest > 22:
            return 104 if self.presentation_mode else 92
        if longest > 14:
            return 88 if self.presentation_mode else 76
        return 70 if self.presentation_mode else 60

    def _draw_message(self, payload: object) -> None:
        width, height = self._canvas_size()
        self.canvas.create_text(
            width / 2,
            height / 2,
            text=str(payload),
            fill="#506070",
            font=self._font("message"),
            width=max(width - 40, 120),
            justify="center",
        )

    def _draw_line_plot(self, payload: object) -> None:
        data = payload  # type: ignore[assignment]
        series = data["series"]
        y_label = data["y_label"]
        y_min = data["y_min"]
        y_max = data["y_max"]
        threshold_lines = data["threshold_lines"]

        if not series:
            self._draw_message("No plot data available.")
            return

        all_x = [x_value for _, _, x_values, _, _ in series for x_value in x_values]
        all_y = [y_value for _, _, _, y_values, _ in series for y_value in y_values]
        if not all_x or not all_y:
            self._draw_message("No plot data available.")
            return

        all_y.extend(value for value, _, _ in threshold_lines)

        min_x = min(all_x)
        max_x = max(all_x)
        min_y = min(all_y) if y_min is None else y_min
        max_y = max(all_y) if y_max is None else y_max

        if max_x <= min_x:
            max_x = min_x + 1.0
        if max_y <= min_y:
            max_y = min_y + 1.0

        y_padding = 0.08 * (max_y - min_y)
        min_y -= y_padding
        max_y += y_padding
        y_tick_labels = [f"{(min_y + tick * (max_y - min_y) / 4.0):.1f}" for tick in range(5)]

        legend_entries = [(label, color, dash) for label, color, _, _, dash in series]
        legend_height = self._draw_legend(legend_entries, left=96, top=10, right=self._canvas_size()[0] - 24)
        left, top, right, bottom = self._draw_axes(
            y_label,
            y_tick_labels=y_tick_labels,
            top_margin=18 + legend_height,
            bottom_margin=64,
            right_margin=52 if threshold_lines else 34,
        )
        def map_x(value: float) -> float:
            return left + (value - min_x) * (right - left) / (max_x - min_x)

        def map_y(value: float) -> float:
            return bottom - (value - min_y) * (bottom - top) / (max_y - min_y)

        for tick in range(5):
            y_value = min_y + tick * (max_y - min_y) / 4.0
            y_pos = map_y(y_value)
            self.canvas.create_line(left - 4, y_pos, right, y_pos, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(left - 10, y_pos, text=f"{y_value:.1f}", anchor="e", fill="#506070", font=self._font("tick"))

        for tick in range(5):
            x_value = min_x + tick * (max_x - min_x) / 4.0
            x_pos = map_x(x_value)
            self.canvas.create_line(x_pos, top, x_pos, bottom + 4, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(x_pos, bottom + 16, text=f"{x_value:.0f}", anchor="n", fill="#506070", font=self._font("tick"))

        for value, color, label in threshold_lines:
            y_pos = map_y(value)
            self.canvas.create_line(left, y_pos, right, y_pos, fill=color, dash=(6, 4), width=self._line_width())
            label_y = max(y_pos - 8, top + 8)
            self.canvas.create_text(right - 6, label_y, text=label, anchor="e", fill=color, font=self._font("threshold"))

        for label, color, x_values, y_values, dash in series:
            points = []
            for x_value, y_value in zip(x_values, y_values):
                points.extend((map_x(x_value), map_y(y_value)))

            if len(points) >= 4:
                self.canvas.create_line(*points, fill=color, width=self._line_width(emphasis=True), smooth=False, dash=dash or ())

    def _draw_step_plot(self, payload: object) -> None:
        data = payload  # type: ignore[assignment]
        x_values = data["x_values"]
        y_values = data["y_values"]
        y_label = data["y_label"]
        tick_labels = data["tick_labels"]

        if not x_values or not y_values:
            self._draw_message("No plot data available.")
            return

        state_labels = [tick_labels.get(state_id, str(state_id)) for state_id in range(4)]
        left, top, right, bottom = self._draw_axes(
            y_label,
            y_tick_labels=state_labels,
            bottom_margin=64,
        )
        min_x = min(x_values)
        max_x = max(x_values)

        if max_x <= min_x:
            max_x = min_x + 1.0

        def map_x(value: float) -> float:
            return left + (value - min_x) * (right - left) / (max_x - min_x)

        def map_y(state_id: int) -> float:
            return bottom - state_id * (bottom - top) / 3.0

        for state_id in range(4):
            y_pos = map_y(state_id)
            self.canvas.create_line(left - 4, y_pos, right, y_pos, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(
                left - 10,
                y_pos,
                text=tick_labels.get(state_id, str(state_id)),
                anchor="e",
                fill="#506070",
                font=self._font("tick"),
            )

        for tick in range(5):
            x_value = min_x + tick * (max_x - min_x) / 4.0
            x_pos = map_x(x_value)
            self.canvas.create_line(x_pos, top, x_pos, bottom + 4, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(x_pos, bottom + 16, text=f"{x_value:.0f}", anchor="n", fill="#506070", font=self._font("tick"))

        points = []
        for index, (x_value, y_value) in enumerate(zip(x_values, y_values)):
            x_pos = map_x(x_value)
            y_pos = map_y(y_value)
            points.extend((x_pos, y_pos))

            if index + 1 < len(x_values):
                next_x = map_x(x_values[index + 1])
                points.extend((next_x, y_pos))

        if len(points) >= 4:
            self.canvas.create_line(*points, fill="#1f5aa6", width=self._line_width(emphasis=True), smooth=False)

    def _draw_step_comparison_plot(self, payload: object) -> None:
        data = payload  # type: ignore[assignment]
        series = data["series"]
        y_label = data["y_label"]
        tick_labels = data["tick_labels"]

        if not series:
            self._draw_message("No plot data available.")
            return

        all_x = [x for _, _, x_values, _, _ in series for x in x_values]
        if not all_x:
            self._draw_message("No plot data available.")
            return

        legend_entries = [(label, color, dash) for label, color, _, _, dash in series]
        legend_height = self._draw_legend(legend_entries, left=96, top=10, right=self._canvas_size()[0] - 24)
        state_labels = [tick_labels.get(state_id, str(state_id)) for state_id in range(4)]
        left, top, right, bottom = self._draw_axes(
            y_label,
            y_tick_labels=state_labels,
            top_margin=18 + legend_height,
            bottom_margin=64,
        )
        min_x = min(all_x)
        max_x = max(all_x)

        if max_x <= min_x:
            max_x = min_x + 1.0

        def map_x(value: float) -> float:
            return left + (value - min_x) * (right - left) / (max_x - min_x)

        def map_y(state_id: int) -> float:
            return bottom - state_id * (bottom - top) / 3.0

        for state_id in range(4):
            y_pos = map_y(state_id)
            self.canvas.create_line(left - 4, y_pos, right, y_pos, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(
                left - 10,
                y_pos,
                text=tick_labels.get(state_id, str(state_id)),
                anchor="e",
                fill="#506070",
                font=self._font("tick"),
            )

        for tick in range(5):
            x_value = min_x + tick * (max_x - min_x) / 4.0
            x_pos = map_x(x_value)
            self.canvas.create_line(x_pos, top, x_pos, bottom + 4, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(x_pos, bottom + 16, text=f"{x_value:.0f}", anchor="n", fill="#506070", font=self._font("tick"))

        for label, color, x_values, y_values, dash in series:
            points = []
            for index, (x_value, y_value) in enumerate(zip(x_values, y_values)):
                x_pos = map_x(x_value)
                y_pos = map_y(y_value)
                points.extend((x_pos, y_pos))

                if index + 1 < len(x_values):
                    next_x = map_x(x_values[index + 1])
                    points.extend((next_x, y_pos))

            if len(points) >= 4:
                self.canvas.create_line(*points, fill=color, width=self._line_width(emphasis=True), dash=dash or ())

    def _draw_bar_plot(self, payload: object) -> None:
        data = payload  # type: ignore[assignment]
        categories = data["categories"]
        values = data["values"]
        y_label = data["y_label"]
        bar_color = data["bar_color"]

        if not categories or not values:
            self._draw_message("No plot data available.")
            return

        valid_values = [value for value in values if value is not None]
        if not valid_values:
            self._draw_message("No valid values available for this batch plot.")
            return

        bottom_margin = self._bottom_margin_for_categories(categories)
        max_value = max(valid_values)
        if max_value <= 0.0:
            max_value = 1.0
        max_value *= 1.12
        y_tick_labels = [f"{(tick * max_value / 4.0):.0f}" for tick in range(5)]
        left, top, right, bottom = self._draw_axes(
            y_label,
            x_label="Fault Type",
            y_tick_labels=y_tick_labels,
            bottom_margin=bottom_margin,
        )

        def map_y(value: float) -> float:
            return bottom - value * (bottom - top) / max_value

        bar_count = len(categories)
        slot_width = (right - left) / max(bar_count, 1)
        bar_width = slot_width * 0.58

        for tick in range(5):
            y_value = tick * max_value / 4.0
            y_pos = map_y(y_value)
            self.canvas.create_line(left - 4, y_pos, right, y_pos, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(left - 10, y_pos, text=f"{y_value:.0f}", anchor="e", fill="#506070", font=self._font("tick"))

        for index, (category, value) in enumerate(zip(categories, values)):
            center_x = left + (index + 0.5) * slot_width
            x0 = center_x - bar_width / 2.0
            x1 = center_x + bar_width / 2.0
            if value is None:
                self.canvas.create_text(center_x, bottom - 8, text="n/a", fill="#6a6a6a", font=self._font("bar_value"))
            else:
                y_top = map_y(value)
                self.canvas.create_rectangle(x0, y_top, x1, bottom, fill=bar_color, outline="#2f2f2f")
                self.canvas.create_text(center_x, y_top - 8, text=f"{value:.0f}", fill="#33404d", font=self._font("bar_value"))

            self.canvas.create_text(
                center_x,
                bottom + 14,
                text=category,
                anchor="n",
                fill="#506070",
                font=self._font("tick"),
                width=slot_width * 0.9,
            )

    def _draw_stacked_bar_plot(self, payload: object) -> None:
        data = payload  # type: ignore[assignment]
        categories = data["categories"]
        stacks = data["stacks"]
        y_label = data["y_label"]
        max_value = data["max_value"]
        x_label = data["x_label"]

        if not categories or not stacks:
            self._draw_message("No plot data available.")
            return

        legend_entries = [(label, color, None) for label, color, _ in stacks]
        legend_height = self._draw_legend(legend_entries, left=96, top=10, right=self._canvas_size()[0] - 24)
        bottom_margin = self._bottom_margin_for_categories(categories)
        if max_value <= 0.0:
            max_value = 1.0
        y_tick_labels = [
            f"{(tick * max_value / 4.0):.0f}" if max_value <= 100.0 else f"{(tick * max_value / 4.0):.1f}"
            for tick in range(5)
        ]
        left, top, right, bottom = self._draw_axes(
            y_label,
            x_label=x_label,
            y_tick_labels=y_tick_labels,
            top_margin=18 + legend_height,
            bottom_margin=bottom_margin,
        )

        def map_y(value: float) -> float:
            return bottom - value * (bottom - top) / max_value

        slot_width = (right - left) / max(len(categories), 1)
        bar_width = slot_width * 0.58
        cumulative = [0.0 for _ in categories]

        for tick in range(5):
            tick_value = tick * max_value / 4.0
            y_pos = map_y(tick_value)
            label = f"{tick_value:.0f}" if max_value <= 100.0 else f"{tick_value:.1f}"
            self.canvas.create_line(left - 4, y_pos, right, y_pos, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(left - 10, y_pos, text=label, anchor="e", fill="#506070", font=self._font("tick"))

        for _label, color, values in stacks:
            for index, value in enumerate(values):
                safe_value = max(float(value), 0.0)
                center_x = left + (index + 0.5) * slot_width
                x0 = center_x - bar_width / 2.0
                x1 = center_x + bar_width / 2.0
                y0 = map_y(cumulative[index] + safe_value)
                y1 = map_y(cumulative[index])
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="#2f2f2f")
                cumulative[index] += safe_value

        for index, category in enumerate(categories):
            center_x = left + (index + 0.5) * slot_width
            total_value = cumulative[index]
            self.canvas.create_text(
                center_x,
                map_y(total_value) - 10,
                text=f"{total_value:.0f}",
                fill="#33404d",
                font=self._font("bar_value"),
            )
            self.canvas.create_text(
                center_x,
                bottom + 14,
                text=category,
                anchor="n",
                fill="#506070",
                font=self._font("tick"),
                width=slot_width * 0.9,
            )

    def _draw_propagation_timeline(self, payload: object) -> None:
        data = payload  # type: ignore[assignment]
        labels = data["labels"]
        reports = data["reports"]

        if not reports:
            self._draw_message("No propagation data is available.")
            return

        lane_order = (
            "hardware_origin",
            "ecu_manifestation",
            "diagnostic_effect",
            "system_effect",
        )
        lane_positions = {lane: len(lane_order) - 1 - index for index, lane in enumerate(lane_order)}
        style_by_index = (
            (LEFT_COLOR, LEFT_DASH, 0.14),
            (RIGHT_COLOR, RIGHT_DASH, -0.14),
        )

        max_time_s = 0.0
        for report in reports:
            max_time_s = max(max_time_s, float(report.get("duration_s", 0.0)))
            for item in report.get("timeline_items", []):
                if item.get("item_type") == "interval":
                    max_time_s = max(max_time_s, float(item.get("end_s", 0.0)))
                max_time_s = max(max_time_s, float(item.get("time_s", 0.0)))

        if max_time_s <= 0.0:
            max_time_s = 1.0

        legend_entries = [
            (label, style_by_index[min(index, len(style_by_index) - 1)][0], style_by_index[min(index, len(style_by_index) - 1)][1])
            for index, label in enumerate(labels)
        ]
        legend_height = self._draw_legend(legend_entries, left=96, top=10, right=self._canvas_size()[0] - 24)
        lane_labels = [LANE_LABELS.get(lane, lane) for lane in lane_order]
        left, top, right, bottom = self._draw_axes(
            "Stage",
            y_tick_labels=lane_labels,
            top_margin=18 + legend_height,
            bottom_margin=74,
            extra_left_margin=54,
        )

        def map_x(value: float) -> float:
            return left + value * (right - left) / max_time_s

        lane_min = -0.35
        lane_max = 3.35

        def map_y(value: float) -> float:
            return bottom - (value - lane_min) * (bottom - top) / (lane_max - lane_min)

        lane_colors = {
            "hardware_origin": "#f6e6e2",
            "ecu_manifestation": "#eef4fb",
            "diagnostic_effect": "#f6f0dd",
            "system_effect": "#edf6ee",
        }

        for tick in range(6):
            x_value = tick * max_time_s / 5.0
            x_pos = map_x(x_value)
            self.canvas.create_line(x_pos, top, x_pos, bottom + 4, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(
                x_pos,
                bottom + 14,
                text=f"{x_value:.0f}",
                anchor="n",
                fill="#506070",
                font=self._font("tick"),
            )

        for lane in lane_order:
            lane_y = map_y(float(lane_positions[lane]))
            lane_top = map_y(float(lane_positions[lane]) + 0.42)
            lane_bottom = map_y(float(lane_positions[lane]) - 0.42)
            self.canvas.create_rectangle(
                left,
                lane_top,
                right,
                lane_bottom,
                fill=lane_colors[lane],
                outline="",
            )
            self.canvas.create_line(left - 4, lane_y, right, lane_y, fill="#dde5ec", dash=(2, 4))
            self.canvas.create_text(
                left - 10,
                lane_y,
                text=LANE_LABELS.get(lane, lane),
                anchor="e",
                fill="#506070",
                font=self._font("tick"),
            )

        arrow_x = left - 42
        self.canvas.create_line(arrow_x, map_y(3.25), arrow_x, map_y(-0.25), fill="#7b8b99", width=2, arrow=tk.LAST)
        self.canvas.create_text(
            arrow_x - 12,
            (map_y(3.25) + map_y(-0.25)) / 2.0,
            text="Propagation",
            angle=90,
            fill="#607180",
            font=self._font("legend"),
        )

        for report_index, report in enumerate(reports):
            color, dash, offset = style_by_index[min(report_index, len(style_by_index) - 1)]

            for item_index, item in enumerate(report.get("timeline_items", [])):
                lane = str(item.get("lane", "hardware_origin"))
                y_pos = map_y(lane_positions.get(lane, 0) + offset)

                if item.get("item_type") == "interval":
                    x0 = map_x(float(item.get("start_s", 0.0)))
                    x1 = map_x(float(item.get("end_s", 0.0)))
                    midpoint = (x0 + x1) / 2.0
                    label_offset = -14 if report_index == 0 else 14
                    self.canvas.create_line(
                        x0,
                        y_pos,
                        x1,
                        y_pos,
                        fill=color,
                        width=self._line_width(emphasis=True) + 2,
                        dash=dash or (),
                    )
                    self.canvas.create_line(x0, y_pos - 6, x0, y_pos + 6, fill=color, width=self._line_width())
                    self.canvas.create_line(x1, y_pos - 6, x1, y_pos + 6, fill=color, width=self._line_width())
                    self.canvas.create_text(
                        midpoint,
                        y_pos + label_offset,
                        text=str(item.get("evidence_label", item.get("short_label", ""))),
                        fill=color,
                        font=self._font("legend"),
                        width=max(x1 - x0 + 10, 80),
                    )
                    continue

                x_pos = map_x(float(item.get("time_s", 0.0)))
                marker_size = 4 if self.presentation_mode else 3
                label_offset = -15 if (report_index == 0) == (item_index % 2 == 0) else 15
                self.canvas.create_line(
                    x_pos,
                    y_pos - 7,
                    x_pos,
                    y_pos + 7,
                    fill=color,
                    width=self._line_width(),
                    dash=dash or (),
                )
                self.canvas.create_oval(
                    x_pos - marker_size,
                    y_pos - marker_size,
                    x_pos + marker_size,
                    y_pos + marker_size,
                    fill=color,
                    outline=color,
                )
                self.canvas.create_text(
                    x_pos,
                    y_pos + label_offset,
                    text=str(item.get("evidence_label", item.get("short_label", ""))),
                    fill=color,
                    font=self._font("tick"),
                    width=130 if self.presentation_mode else 104,
                )

        self.canvas.create_text(
            left,
            bottom + 34,
            anchor="w",
            text="Read top-to-bottom as: hardware-origin fault -> ECU manifestation -> diagnostic effect -> safe-state/system effect.",
            fill="#5b6b79",
            font=self._font("legend"),
        )


class ScrollableTabFrame(ttk.Frame):
    """Notebook tab wrapper with vertical scrolling."""

    def __init__(self, master: tk.Misc, *, padding: Tuple[int, int, int, int] = (4, 8, 4, 6)) -> None:
        super().__init__(master, style="Root.TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self,
            background=APP_BG,
            borderwidth=0,
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.content = ttk.Frame(self.canvas, padding=padding, style="Root.TFrame")
        self.content.columnconfigure(0, weight=1)
        self._window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        self.content.bind("<Enter>", self._bind_mousewheel)
        self.content.bind("<Leave>", self._unbind_mousewheel)

    def _on_content_configure(self, _event: tk.Event[tk.Misc]) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event[tk.Misc]) -> None:
        self.canvas.itemconfigure(self._window_id, width=event.width)

    def _bind_mousewheel(self, _event: tk.Event[tk.Misc]) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _unbind_mousewheel(self, _event: tk.Event[tk.Misc]) -> None:
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event: tk.Event[tk.Misc]) -> None:
        if getattr(event, "delta", 0) > 0:
            self.canvas.yview_scroll(-1, "units")
        elif getattr(event, "delta", 0) < 0:
            self.canvas.yview_scroll(1, "units")

    def _on_mousewheel_linux(self, event: tk.Event[tk.Misc]) -> None:
        button = getattr(event, "num", 0)
        if button == 4:
            self.canvas.yview_scroll(-1, "units")
        elif button == 5:
            self.canvas.yview_scroll(1, "units")


class FaultPathDiagram(ttk.Frame):
    """Canvas-based qualitative cross-layer ECU path visualization."""

    def __init__(self, master: tk.Misc, side_label: str, accent_color: str) -> None:
        super().__init__(master)
        self.side_label = side_label
        self.accent_color = accent_color
        self.campaign_id = "baseline"
        self.campaign_label = "Baseline"
        self.first_row: Dict[str, str] | None = None
        self.summary_row: Dict[str, str] | None = None
        self.affected_blocks: Tuple[str, ...] = ()
        self.fault_class_var = tk.StringVar(value="-")
        self.subsystem_var = tk.StringVar(value="-")
        self.outcome_var = tk.StringVar(value="-")
        self.note_var = tk.StringVar(value="-")
        self.stage_images = self._load_stage_images()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self.title_var = tk.StringVar(value=side_label)
        ttk.Label(self, textvariable=self.title_var, style="Section.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
            padx=6,
            pady=(0, 8),
        )
        summary = tk.Frame(self, bg="#f4f7fa", bd=0, highlightthickness=0)
        summary.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 8))
        for column in range(3):
            summary.grid_columnconfigure(column, weight=1)
        self._build_summary_stat(summary, 0, "Class", self.fault_class_var)
        self._build_summary_stat(summary, 1, "Origin", self.subsystem_var)
        self._build_summary_stat(summary, 2, "Outcome", self.outcome_var)

        self.canvas = tk.Canvas(
            self,
            background="#ffffff",
            height=250,
            highlightthickness=1,
            highlightbackground="#c7d0d9",
        )
        self.canvas.grid(row=2, column=0, sticky="nsew", padx=6)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())
        tk.Label(
            self,
            textvariable=self.note_var,
            bg="#f4f6f8",
            fg="#5b6b79",
            font=("TkDefaultFont", 9),
            justify="left",
            anchor="w",
            wraplength=620,
            padx=6,
            pady=0,
        ).grid(row=3, column=0, sticky="ew", padx=6, pady=(8, 0))
        self.set_campaign("baseline")

    def _load_stage_images(self) -> Dict[str, tk.PhotoImage]:
        asset_names = {
            "sensor_adc": "coolant Icon.png",
            "timing_link": "Timing_Link.png",
            "ecu_control_memory": "Control_memory.png",
            "actuator_power": "Actuation_Path_fan.png",
            "thermal_plant": "Plant_outcome_engine_temp.png",
        }
        images: Dict[str, tk.PhotoImage] = {}
        for block_id, _label in FAULT_PATH_BLOCKS:
            path = FAULT_PATH_ASSET_DIR / asset_names.get(block_id, f"{block_id}.png")
            if not path.exists():
                continue
            try:
                image = tk.PhotoImage(file=str(path))
            except tk.TclError:
                continue
            scale = max(1, (max(image.width(), image.height()) + 63) // 64)
            if scale > 1:
                image = image.subsample(scale, scale)
            images[block_id] = image
        return images

    def _highlighted_block_names(self) -> str:
        if not self.affected_blocks:
            return "Nominal path only"
        return ", ".join(FAULT_PATH_BLOCK_DISPLAY.get(block_id, block_id) for block_id in self.affected_blocks)

    def _primary_fault_block(self) -> str | None:
        return self.affected_blocks[0] if self.affected_blocks else None

    def _is_propagated_block(self, block_id: str) -> bool:
        if block_id not in self.affected_blocks:
            return False
        primary = self._primary_fault_block()
        return primary is not None and block_id != primary

    def _primary_subsystem_summary(self) -> str:
        if not self.affected_blocks:
            return "None"
        primary = self._primary_fault_block()
        if primary is None:
            return "None"
        return FAULT_PATH_BLOCK_CLASS.get(primary, FAULT_PATH_BLOCK_DISPLAY.get(primary, primary))

    def _outcome_summary(self, story: Dict[str, str]) -> str:
        if not self.affected_blocks:
            return "Nominal regulation"
        text = story.get("system_effect", "No system-level outcome available.")
        return textwrap.shorten(text, width=54, placeholder="...")

    def _footer_sentence(self, story: Dict[str, str]) -> str:
        if not self.affected_blocks:
            return "Reference case: all five stages remain nominal from sensing to plant outcome."
        primary = self._primary_fault_block()
        if primary is None:
            return textwrap.shorten(story.get("description", "Fault path overview."), width=88, placeholder="...")
        primary_label = FAULT_PATH_BLOCK_CLASS.get(primary, FAULT_PATH_BLOCK_DISPLAY.get(primary, primary))
        if "thermal_plant" in self.affected_blocks:
            return f"Fault begins in {primary_label} and propagates across the chain to the plant outcome."
        return f"Fault begins in {primary_label} and remains most visible before the final plant stage."

    def _outcome_level(self) -> Tuple[str, str, str]:
        if self.summary_row is None:
            return ("Normal", "#6f7f8d", "#f4f7fa")

        safe_state = str(self.summary_row.get("final_safe_state_label", "normal"))
        max_temp = float_or_none(str(self.summary_row.get("max_coolant_temp_c", "")))
        severity = safe_state_score(safe_state)
        if severity >= 2 or (max_temp is not None and max_temp >= 115.0):
            return ("Severe", "#b5483b", "#fdecea")
        if severity >= 1 or (max_temp is not None and max_temp >= 108.0):
            return ("Warning", "#a06b12", "#fff5df")
        return ("Normal", "#3f7f52", "#ebf6ee")

    def _build_summary_stat(self, parent: tk.Frame, column: int, title: str, variable: tk.StringVar) -> None:
        stat = tk.Frame(parent, bg="#ffffff", bd=1, relief="solid", highlightthickness=0)
        stat.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0 if column == 2 else 6), pady=0)
        tk.Label(
            stat,
            text=title,
            bg="#ffffff",
            fg="#6c7a88",
            font=("TkDefaultFont", 8, "bold"),
            anchor="w",
            justify="left",
            padx=10,
            pady=0,
        ).pack(fill="x", pady=(9, 2))
        tk.Label(
            stat,
            textvariable=variable,
            bg="#ffffff",
            fg="#22313f",
            font=("TkDefaultFont", 9),
            anchor="w",
            justify="left",
            wraplength=150,
            padx=10,
            pady=0,
        ).pack(fill="x", pady=(0, 9))

    def _draw_stage_visual(
        self,
        block_id: str,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        *,
        highlight: bool,
        severe_outcome: bool = False,
    ) -> None:
        image = self.stage_images.get(block_id)
        if image is not None:
            self.canvas.create_image((x0 + x1) / 2, (y0 + y1) / 2, image=image)
            return
        self._draw_block_icon(
            block_id,
            x0,
            y0,
            x1,
            y1,
            highlight=highlight,
            severe_outcome=severe_outcome,
        )

    def _draw_block_icon(
        self,
        block_id: str,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        *,
        highlight: bool,
        severe_outcome: bool = False,
    ) -> None:
        if severe_outcome:
            color = "#b5483b"
        elif highlight:
            color = self.accent_color
        else:
            color = "#7d8a96"
        inner_left = x0 + 10
        inner_top = y0 + 10
        inner_right = x1 - 10
        inner_bottom = y1 - 10
        center_x = (inner_left + inner_right) / 2
        center_y = (inner_top + inner_bottom) / 2

        if block_id == "sensor_adc":
            pipe_y = inner_bottom - 8
            self.canvas.create_line(inner_left + 2, pipe_y, inner_right - 4, pipe_y, fill=color, width=2)
            self.canvas.create_arc(
                inner_left + 2,
                pipe_y - 10,
                inner_left + 20,
                pipe_y + 8,
                start=180,
                extent=180,
                style=tk.ARC,
                outline=color,
                width=2,
            )
            self.canvas.create_line(center_x + 8, inner_top + 2, center_x + 8, pipe_y - 2, fill=color, width=2)
            self.canvas.create_oval(center_x + 1, inner_top + 16, center_x + 15, inner_top + 30, outline=color, width=2)
            self.canvas.create_oval(
                center_x + 5,
                inner_top + 24,
                center_x + 11,
                inner_top + 30,
                outline=color,
                fill=color,
                width=2,
            )
            for offset in (0, 6, 12):
                self.canvas.create_line(inner_left + 4 + offset, inner_top + 8, inner_left + 8 + offset, inner_top + 8, fill=color, width=2)
            return

        if block_id == "timing_link":
            left_box = (inner_left + 2, center_y - 10, inner_left + 22, center_y + 10)
            right_box = (inner_right - 22, center_y - 10, inner_right - 2, center_y + 10)
            self.canvas.create_rectangle(*left_box, outline=color, width=2)
            self.canvas.create_rectangle(*right_box, outline=color, width=2)
            self.canvas.create_line(left_box[2], center_y, right_box[0] - 10, center_y, fill=color, width=2, dash=(4, 3))
            self.canvas.create_polygon(
                right_box[0] - 12,
                center_y - 6,
                right_box[0] - 2,
                center_y,
                right_box[0] - 12,
                center_y + 6,
                fill=color,
                outline=color,
            )
            self.canvas.create_line(inner_left + 8, center_y - 16, inner_right - 8, center_y - 16, fill=color, width=2)
            self.canvas.create_line(inner_right - 18, center_y - 20, inner_right - 8, center_y - 16, fill=color, width=2)
            self.canvas.create_line(inner_right - 18, center_y - 12, inner_right - 8, center_y - 16, fill=color, width=2)
            return

        if block_id == "ecu_control_memory":
            self.canvas.create_rectangle(inner_left + 4, inner_top + 6, center_x + 8, inner_bottom - 4, outline=color, width=2)
            self.canvas.create_rectangle(center_x + 14, inner_top + 12, inner_right - 2, inner_bottom - 10, outline=color, width=2)
            for offset in (0, 8, 16):
                self.canvas.create_line(center_x + 18, inner_top + 18 + offset, inner_right - 6, inner_top + 18 + offset, fill=color, width=2)
            for offset in (0, 10, 20):
                self.canvas.create_line(inner_left, inner_top + 12 + offset, inner_left + 4, inner_top + 12 + offset, fill=color, width=2)
                self.canvas.create_line(center_x + 8, inner_top + 12 + offset, center_x + 12, inner_top + 12 + offset, fill=color, width=2)
            return

        if block_id == "actuator_power":
            driver_x1 = inner_left + 20
            self.canvas.create_rectangle(inner_left + 2, inner_top + 8, driver_x1, inner_bottom - 6, outline=color, width=2)
            self.canvas.create_line(driver_x1, center_y, inner_right - 28, center_y, fill=color, width=2)
            fan_cx = inner_right - 14
            fan_cy = center_y
            self.canvas.create_oval(fan_cx - 12, fan_cy - 12, fan_cx + 12, fan_cy + 12, outline=color, width=2)
            self.canvas.create_polygon(fan_cx, fan_cy - 2, fan_cx + 10, fan_cy - 8, fan_cx + 4, fan_cy + 2, outline=color, fill="", width=2)
            self.canvas.create_polygon(fan_cx + 2, fan_cy + 1, fan_cx + 8, fan_cy + 11, fan_cx - 2, fan_cy + 5, outline=color, fill="", width=2)
            self.canvas.create_polygon(fan_cx - 2, fan_cy + 1, fan_cx - 12, fan_cy - 3, fan_cx - 2, fan_cy - 7, outline=color, fill="", width=2)
            return

        self.canvas.create_rectangle(inner_left + 4, inner_top + 8, inner_right - 10, inner_bottom - 8, outline=color, width=2)
        for offset in (0, 10, 20):
            self.canvas.create_line(inner_left + 12, inner_top + 14 + offset, inner_right - 18, inner_top + 14 + offset, fill=color, width=2)
        self.canvas.create_line(inner_right - 8, inner_top + 12, inner_right + 4, inner_top + 4, fill=color, width=2)
        self.canvas.create_line(inner_right - 8, center_y, inner_right + 4, center_y - 8, fill=color, width=2)
        self.canvas.create_line(inner_right - 8, inner_bottom - 12, inner_right + 4, inner_bottom - 20, fill=color, width=2)
        self.canvas.create_oval(inner_left + 10, inner_top + 4, inner_left + 24, inner_top + 18, outline=color, width=2)
        self.canvas.create_line(inner_left + 17, inner_top + 18, inner_left + 17, inner_bottom - 2, fill=color, width=2)

    def export_canvas_snapshot(self, path: Path) -> Path | None:
        self.update_idletasks()
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        if width <= 1 or height <= 1:
            return None
        try:
            self.canvas.postscript(
                file=str(path),
                colormode="color",
                x=0,
                y=0,
                width=width,
                height=height,
            )
        except tk.TclError:
            return None
        return path

    def set_campaign(
        self,
        campaign_id: str,
        first_row: Dict[str, str] | None = None,
        summary_row: Dict[str, str] | None = None,
    ) -> None:
        story = story_for_run(campaign_id, first_row)
        self.campaign_id = campaign_id
        self.campaign_label = story["campaign_name"]
        self.first_row = first_row
        self.summary_row = summary_row
        self.affected_blocks = affected_blocks_for_run(campaign_id, first_row)
        self.fault_class_var.set(story["fault_class"])
        self.subsystem_var.set(self._primary_subsystem_summary())
        self.outcome_var.set(self._outcome_summary(story))
        self.note_var.set(self._footer_sentence(story))
        if self.affected_blocks:
            self.title_var.set(f"{self.side_label} Fault Path")
        else:
            self.title_var.set(f"{self.side_label} Reference Path")
        self.redraw()

    def redraw(self) -> None:
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 660)
        height = max(self.canvas.winfo_height(), 260)
        margin_x = 26
        top = 30
        block_gap = 18
        block_count = len(FAULT_PATH_BLOCKS)
        block_width = max((width - 2 * margin_x - block_gap * (block_count - 1)) / block_count, 96)
        block_height = 144
        origin_block = self._primary_fault_block()
        outcome_level, outcome_color, outcome_fill = self._outcome_level()
        has_fault = bool(self.affected_blocks)
        flow_y = top + 50
        heading_color = self.accent_color if has_fault else "#7c8a96"
        subtitle = self.campaign_label if has_fault else "Baseline reference"
        subtitle_bg = "#eef4fd" if has_fault else "#f4f6f8"
        subtitle_outline = self.accent_color if has_fault else "#d9e0e6"

        self.canvas.create_text(
            margin_x,
            14,
            anchor="w",
            text=subtitle,
            fill=heading_color,
            font=("TkDefaultFont", 9, "bold"),
        )
        self.canvas.create_rectangle(
            width - margin_x - 138,
            6,
            width - margin_x,
            22,
            fill=subtitle_bg,
            outline=subtitle_outline,
            width=1,
        )
        self.canvas.create_text(
            width - margin_x - 69,
            14,
            text="5-stage left to right flow",
            fill=heading_color,
            font=("TkDefaultFont", 8),
        )

        centers: Dict[str, Tuple[float, float]] = {}
        for index, (block_id, _label) in enumerate(FAULT_PATH_BLOCKS):
            x0 = margin_x + index * (block_width + block_gap)
            y0 = top
            x1 = x0 + block_width
            y1 = y0 + block_height
            is_origin = block_id == origin_block
            is_outcome = block_id == "thermal_plant"
            is_reference = not has_fault
            fill = "#fafbfd" if is_reference else "#eef4fd" if is_origin else outcome_fill if is_outcome and outcome_level != "Normal" else "#fbfcfe"
            outline = "#dde4ea" if is_reference else self.accent_color if is_origin else outcome_color if is_outcome and outcome_level != "Normal" else "#d3dce4"
            title_fill = "#8a97a3" if is_reference else self.accent_color if is_origin else outcome_color if is_outcome and outcome_level != "Normal" else "#5f707f"
            line_width = 3 if is_origin else 2 if is_outcome and outcome_level != "Normal" else 1
            label_text = FAULT_PATH_BLOCK_CLASS.get(block_id, "")

            self.canvas.create_rectangle(
                x0,
                y0,
                x1,
                y1,
                fill=fill,
                outline=outline,
                width=line_width,
            )
            self.canvas.create_text(
                (x0 + x1) / 2,
                y0 + 20,
                text=label_text,
                fill=title_fill,
                font=("TkDefaultFont", 9, "bold"),
                justify="center",
                width=max(block_width - 16, 52),
            )
            self._draw_stage_visual(
                block_id,
                x0 + 12,
                y0 + 40,
                x1 - 12,
                y0 + 104,
                highlight=is_origin,
                severe_outcome=is_outcome and outcome_level != "Normal",
            )
            centers[block_id] = ((x0 + x1) / 2, (y0 + y1) / 2)

            if index > 0:
                previous_id = FAULT_PATH_BLOCKS[index - 1][0]
                prev_x = centers[previous_id][0]
                previous_is_origin = previous_id == origin_block
                previous_is_propagated = self._is_propagated_block(previous_id)
                arrow_color = "#d5dce3" if is_reference else self.accent_color if previous_is_origin or previous_is_propagated else "#b5c0ca"
                self.canvas.create_line(
                    prev_x + block_width / 2,
                    flow_y,
                    x0 - 4,
                    flow_y,
                    fill=arrow_color,
                    width=2 if is_reference else 3 if previous_is_origin or previous_is_propagated else 2,
                    arrow=tk.LAST,
                )

            if is_origin:
                self.canvas.create_text(
                    (x0 + x1) / 2,
                    y1 + 14,
                    text="Fault origin",
                    fill=self.accent_color,
                    font=("TkDefaultFont", 8),
                    justify="center",
                    width=max(block_width - 10, 52),
                )
            elif is_outcome and has_fault and outcome_level != "Normal":
                self.canvas.create_text(
                    (x0 + x1) / 2,
                    y1 + 14,
                    text="Main outcome",
                    fill=outcome_color,
                    font=("TkDefaultFont", 8),
                    justify="center",
                    width=max(block_width - 10, 52),
                )


class ScenarioTimelineView(ttk.Frame):
    """Canvas-based live timeline for the ordered multi-fault scenario."""

    TITLE_FONT = ("TkDefaultFont", 11, "bold")
    META_FONT = ("TkDefaultFont", 9)
    AXIS_FONT = ("TkDefaultFont", 10)
    AXIS_BOLD_FONT = ("TkDefaultFont", 10, "bold")
    BADGE_FONT = ("TkDefaultFont", 8, "bold")
    HEADER_FONT = ("TkDefaultFont", 12, "bold")

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.events: List[Dict[str, object]] = []
        self._title_font = tkfont.Font(font=self.TITLE_FONT)
        self._meta_font = tkfont.Font(font=self.META_FONT)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            self,
            background="#ffffff",
            height=384,
            highlightthickness=1,
            highlightbackground="#c7d0d9",
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

    def set_events(self, events: Sequence[Dict[str, object]]) -> None:
        self.events = [dict(event) for event in events]
        self.redraw()

    def _event_duration_label(self, event: Dict[str, object]) -> str:
        behavior = str(event["fault_behavior"])
        duration_ms = int(event["duration_ms"])
        if behavior == "permanent" and duration_ms == 0:
            return "permanent"
        return f"{duration_ms / 1000.0:.1f}s"

    def _format_time_label(self, time_ms: int) -> str:
        if time_ms >= 10000:
            return f"{time_ms / 1000.0:.0f}s"
        return f"{time_ms / 1000.0:.1f}s"

    def _row_meta_label(self, event: Dict[str, object]) -> str:
        start_ms = int(event["start_ms"])
        return f"start {self._format_time_label(start_ms)}  |  {self._event_duration_label(event)}"

    def _timeline_span_ms(self) -> int:
        finite_durations = [int(event["duration_ms"]) for event in self.events if int(event["duration_ms"]) > 0]
        permanent_tail = max(finite_durations, default=12000)
        endpoints: List[int] = [30000]

        for event in self.events:
            start_ms = int(event["start_ms"])
            duration_ms = int(event["duration_ms"])
            behavior = str(event["fault_behavior"])
            if behavior == "permanent" and duration_ms == 0:
                endpoints.append(start_ms + permanent_tail)
            else:
                endpoints.append(start_ms + duration_ms)

        return max(endpoints)

    def _fit_label(self, text: str, font: tkfont.Font, max_width: int) -> str:
        if font.measure(text) <= max_width:
            return text
        ellipsis = "..."
        truncated = text
        while truncated and font.measure(truncated + ellipsis) > max_width:
            truncated = truncated[:-1]
        return (truncated.rstrip() + ellipsis) if truncated else ellipsis

    def redraw(self) -> None:
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 860)
        outer_pad = 18
        card_left = outer_pad
        card_right = width - outer_pad

        if not self.events:
            height = 260
            self.canvas.configure(height=height)
            self.canvas.create_rectangle(
                card_left,
                18,
                card_right,
                height - 18,
                fill="#fbfcfe",
                outline="#d5dde6",
                width=1,
            )
            self.canvas.create_text(
                width / 2,
                height / 2 - 12,
                anchor="center",
                text="Add events to preview the staged scenario.",
                fill="#667684",
                font=("TkDefaultFont", 12, "bold"),
                width=width - 80,
            )
            self.canvas.create_text(
                width / 2,
                height / 2 + 16,
                anchor="center",
                text="The timeline becomes the main scenario view once at least two events are staged.",
                fill="#7a8894",
                font=("TkDefaultFont", 9),
                width=width - 120,
            )
            return

        row_gap = 108
        row_height = 72
        header_top = 28
        chart_top = 108
        bottom_padding = 72
        height = max(412, chart_top + len(self.events) * row_gap + bottom_padding)
        self.canvas.configure(height=height)
        label_left = card_left + 26
        label_width = int(max(300, min(390, width * 0.36)))
        label_right = min(label_left + label_width, card_right - 320)
        axis_left = label_right + 42
        axis_right = card_right - 28
        axis_y = chart_top - 30
        row_line_left = axis_left
        row_line_right = axis_right
        span_ms = self._timeline_span_ms()

        def map_x(time_ms: int) -> float:
            if span_ms <= 0:
                return float(axis_left)
            return axis_left + (float(time_ms) / float(span_ms)) * (axis_right - axis_left)

        self.canvas.create_rectangle(
            card_left,
            18,
            card_right,
            height - 18,
            fill="#fbfcfe",
            outline="#d5dde6",
            width=1,
        )
        self.canvas.create_text(
            label_left,
            header_top,
            anchor="w",
            text=f"{len(self.events)} staged events in execution order",
            fill="#22313f",
            font=self.HEADER_FONT,
        )
        self.canvas.create_text(
            axis_right,
            header_top,
            anchor="e",
            text=f"Timeline span {self._format_time_label(span_ms)}",
            fill="#6a7987",
            font=self.AXIS_FONT,
        )
        self.canvas.create_text(
            label_left,
            chart_top - 42,
            anchor="w",
            text="Event list",
            fill="#6d7b89",
            font=self.AXIS_BOLD_FONT,
        )
        self.canvas.create_text(
            axis_left,
            chart_top - 42,
            anchor="w",
            text="Timeline view",
            fill="#6d7b89",
            font=self.AXIS_BOLD_FONT,
        )

        tick_fractions = [0.0, 0.5, 1.0]
        if axis_right - axis_left >= 760:
            tick_fractions = [0.0, 0.25, 0.5, 0.75, 1.0]
        elif axis_right - axis_left >= 520:
            tick_fractions = [0.0, 0.33, 0.66, 1.0]

        last_label_x = -9999.0
        for tick_index, fraction in enumerate(tick_fractions):
            tick_ms = int(round(span_ms * fraction))
            x = map_x(tick_ms)
            is_endpoint = tick_index in {0, len(tick_fractions) - 1}
            grid_color = "#dfe7ee" if is_endpoint else "#edf2f6"
            grid_bottom = chart_top + (len(self.events) - 1) * row_gap + row_height / 2 + 14
            if is_endpoint:
                self.canvas.create_line(x, axis_y, x, grid_bottom, fill=grid_color)
            else:
                self.canvas.create_line(x, axis_y, x, grid_bottom, fill=grid_color, dash=(2, 5))
            if x - last_label_x >= 58 or is_endpoint:
                self.canvas.create_text(
                    x,
                    axis_y - 12,
                    anchor="s",
                    text=self._format_time_label(tick_ms),
                    fill="#5f6f7d",
                    font=self.AXIS_BOLD_FONT if is_endpoint else self.AXIS_FONT,
                )
                last_label_x = x

        self.canvas.create_line(axis_left, axis_y, axis_right, axis_y, fill="#95a3af", width=2)
        self.canvas.create_oval(axis_left - 3, axis_y - 3, axis_left + 3, axis_y + 3, fill="#95a3af", outline="")
        self.canvas.create_oval(axis_right - 3, axis_y - 3, axis_right + 3, axis_y + 3, fill="#95a3af", outline="")

        for index, event in enumerate(self.events):
            row_top = chart_top + index * row_gap - 16
            row_bottom = row_top + row_height
            center_y = (row_top + row_bottom) / 2
            start_ms = int(event["start_ms"])
            duration_ms = int(event["duration_ms"])
            behavior = str(event["fault_behavior"])
            bar_end_ms = start_ms + duration_ms
            if behavior == "permanent" and duration_ms == 0:
                bar_end_ms = span_ms

            x0 = map_x(start_ms)
            x1 = map_x(max(bar_end_ms, start_ms + 1))
            color = SCENARIO_TIMELINE_COLORS.get(str(event["fault_type"]), "#5077b8")
            label = f"{index + 1}. {custom_mode_label(str(event['fault_type']))}"
            details = self._row_meta_label(event)
            details_text = self._fit_label(details, self._meta_font, max(120, label_right - label_left - 18))
            track_top = center_y - 12
            track_bottom = center_y + 12
            bar_top = center_y - 10
            bar_bottom = center_y + 10
            title_y = row_top + 12
            meta_y = row_top + 50

            if index > 0:
                separator_y = row_top - 14
                self.canvas.create_line(
                    card_left + 18,
                    separator_y,
                    card_right - 18,
                    separator_y,
                    fill="#eef3f7",
                )
            self.canvas.create_rectangle(
                label_left - 8,
                row_top + 4,
                label_right,
                row_bottom - 4,
                fill="#fcfdfe",
                outline="#e8eef4",
                width=1,
            )
            self.canvas.create_rectangle(label_left, row_top + 18, label_left + 14, row_top + 38, fill=color, outline="")
            self.canvas.create_text(
                label_left + 18,
                title_y,
                anchor="nw",
                text=label,
                fill="#22313f",
                font=self.TITLE_FONT,
                width=max(120, label_right - label_left - 48),
            )
            self.canvas.create_text(
                label_left + 18,
                meta_y,
                anchor="w",
                text=details_text,
                fill="#6b7a87",
                font=self.META_FONT,
            )
            self.canvas.create_rectangle(
                row_line_left,
                track_top,
                row_line_right,
                track_bottom,
                fill="#eef3f7",
                outline="#dde6ed",
                width=1,
            )
            self.canvas.create_line(row_line_left, center_y, row_line_right, center_y, fill="#f9fbfc", width=3)
            self.canvas.create_rectangle(
                x0,
                bar_top,
                max(x1, x0 + 12),
                bar_bottom,
                fill=color,
                outline=color,
                width=1,
            )
            self.canvas.create_line(x0, track_top - 7, x0, track_bottom + 7, fill=color, width=2)
            self.canvas.create_oval(x0 - 3, track_top - 10, x0 + 3, track_top - 4, fill=color, outline="")
            self.canvas.create_text(
                max(axis_left + 8, x0),
                track_top - 14,
                anchor="w",
                text=self._format_time_label(start_ms),
                fill="#566674",
                font=self.BADGE_FONT,
            )
            if behavior == "permanent" and duration_ms == 0:
                continuation_x = axis_right - 2
                self.canvas.create_line(continuation_x, track_top + 2, continuation_x, track_bottom - 2, fill=color, width=2)
                for stripe_offset in (30, 20, 10):
                    stripe_x = max(x0 + 16, axis_right - stripe_offset)
                    self.canvas.create_line(
                        stripe_x - 8,
                        bar_top + 2,
                        stripe_x,
                        bar_bottom - 2,
                        fill="#ffffff",
                        width=2,
                    )
            else:
                self.canvas.create_line(x1, track_top - 5, x1, track_bottom + 5, fill=color, width=2)


class VirtualECUGui(ctk.CTk if CTK_AVAILABLE else tk.Tk):  # type: ignore[misc, valid-type]
    METRIC_NAMES = (
        "Final DTC",
        "Final Safe State",
        "Maximum Coolant Temperature",
        "Detection Latency",
        "Safe-State Latency",
    )
    EMPHASIZED_METRICS = {
        "Final DTC",
        "Final Safe State",
        "Maximum Coolant Temperature",
        "Detection Latency",
        "Safe-State Latency",
    }
    SNAPSHOT_METRIC_NAMES = (
        "Final DTC",
        "Final Safe State",
        "Maximum Coolant Temperature",
        "Detection Latency",
        "Safe-State Latency",
    )
    COMPARISON_PLOT_OPTIONS = (
        "Coolant Temperature Comparison",
        "Safe-State Comparison",
        "Fan Command / Actual Comparison",
        "Cross-Layer Propagation Timeline",
    )
    RECOMMENDED_DEMO_COMPARISONS = (
        ("Baseline vs Fan Hot Stress", "baseline", "fan_stuck_hot_stress"),
        ("Baseline vs Calibration", "baseline", "calibration_memory_corruption"),
        ("Baseline vs Stale Sensor", "baseline", "stale_sensor_data_only"),
        ("Stale Mild vs Hot Stress", "stale_sensor_data_only", "stale_sensor_data_hot_stress"),
        ("Timing Stress vs Fan Hot Stress", "stale_sensor_data_hot_stress", "fan_stuck_hot_stress"),
    )
    BATCH_PLOT_OPTIONS = (
        "Mean Detection Latency",
        "Mean Safe-State Latency",
        "Mean Maximum Coolant Temperature",
        "Mean Safe-Mode Duration",
        "Final Safe-State Distribution",
    )
    BATCH_SAFE_STATE_COLORS = {
        "normal": "#7fbf7b",
        "precautionary_cooling": "#f2c14e",
        "limp_home": "#e07a5f",
        "controlled_shutdown": "#7b2d26",
        "unknown": "#8c99a5",
    }

    def __init__(self) -> None:
        if CTK_AVAILABLE:
            ctk.set_appearance_mode("light")
            ctk.set_default_color_theme("blue")
        super().__init__()
        self.title("Virtual ECU Research GUI")
        self.geometry("1360x1020")
        self.minsize(1180, 920)

        self.executable = detect_executable()
        self.left_campaign = tk.StringVar(value="baseline")
        self.right_campaign = tk.StringVar(value="fan_stuck_hot_stress")
        self.presentation_mode = tk.BooleanVar(value=False)
        self.auto_restore_session = tk.BooleanVar(value=True)
        self.comparison_plot_choice = tk.StringVar(value=self.COMPARISON_PLOT_OPTIONS[0])
        self.batch_plot_choice = tk.StringVar(value=self.BATCH_PLOT_OPTIONS[0])
        self.status_text = tk.StringVar(
            value="Fast start: load a Showcase preset, or click Run Built-In Comparison for the selected campaigns."
        )
        self.batch_status_text = tk.StringVar(value="Ready to load the default batch summary for sweep-level trends.")
        self.custom_status_text = tk.StringVar(
            value="Choose a single fault or multi-fault scenario, then use the main run actions to open figures immediately."
        )
        self.summary_resources_expanded = tk.BooleanVar(value=False)
        self.comparison_verdict_var = tk.StringVar(value="Run a comparison to generate a compact verdict.")
        self.comparison_takeaway_var = tk.StringVar(value="-")
        self.comparison_findings_var = tk.StringVar(value="Run a comparison to generate automatic findings.")
        self.comparison_interpretation_var = tk.StringVar(value="-")
        self.batch_findings_var = tk.StringVar(value="Load a batch aggregate summary CSV to generate automatic findings.")
        self.batch_interpretation_var = tk.StringVar(value="-")
        self.left_description_var = tk.StringVar(value="-")
        self.right_description_var = tk.StringVar(value="-")
        self.custom_fault_type = tk.StringVar(value=CUSTOM_FAULT_TYPES[0][0])
        self.custom_fault_behavior = tk.StringVar(value=CUSTOM_FAULT_BEHAVIORS[0][0])
        self.custom_start_ms = tk.StringVar(value="20000")
        self.custom_duration_ms = tk.StringVar(value="10000")
        self.custom_parameter = tk.StringVar(value=CUSTOM_DEFAULT_PARAMETERS[CUSTOM_FAULT_TYPES[0][0]])
        self.custom_preset_name = tk.StringVar(value="sensor_bias_demo_copy")
        self.custom_preset_choice = tk.StringVar(value="")
        self.showcase_presets: List[Dict[str, str]] = []
        self.showcase_preset_catalog: Dict[str, Dict[str, str]] = {}
        self.showcase_preset_choice = tk.StringVar(value="")
        self.showcase_description_var = tk.StringVar(value="Load a showcase preset to open a saved thesis/demo comparison.")
        self.recent_results: List[Dict[str, str]] = []
        self.favorite_comparisons: List[Dict[str, str]] = []
        self.favorite_choice = tk.StringVar(value="")
        self.favorite_title_var = tk.StringVar(value="")
        self.favorite_note_var = tk.StringVar(value="")
        self.multi_fault_type = tk.StringVar(value=CUSTOM_FAULT_TYPES[0][0])
        self.multi_fault_behavior = tk.StringVar(value=CUSTOM_FAULT_BEHAVIORS[0][0])
        self.multi_start_ms = tk.StringVar(value="20000")
        self.multi_duration_ms = tk.StringVar(value="10000")
        self.multi_parameter = tk.StringVar(value=CUSTOM_DEFAULT_PARAMETERS[CUSTOM_FAULT_TYPES[0][0]])
        self.multi_preset_name = tk.StringVar(value="sensor_bias_then_fan_loss_demo_copy")
        self.multi_preset_choice = tk.StringVar(value="")
        self.custom_saved_paths_var = tk.StringVar(value="-")
        self.custom_last_run_var = tk.StringVar(value="-")
        self.comparison_plot_help_var = tk.StringVar(
            value="Use the propagation view to read top-to-bottom from hardware-origin fault to ECU manifestation, diagnostics, and safe-state/system effect."
        )
        self.dashboard_comparison_var = tk.StringVar(value="No comparison loaded")
        self.dashboard_export_var = tk.StringVar(value="Run a left-versus-right comparison to enable exports")
        self.dashboard_batch_var = tk.StringVar(value="No batch aggregate loaded")
        self.dashboard_custom_var = tk.StringVar(value="No custom run yet")
        self.dashboard_runtime_var = tk.StringVar(value="Simulator executable detected" if self.executable else "Build the simulator before running campaigns")
        self.batch_csv_path = tk.StringVar(value=str(DEFAULT_BATCH_AGGREGATE_CSV))
        self.batch_run_count_var = tk.StringVar(value="-")
        self.batch_fault_classes_var = tk.StringVar(value="-")
        self.batch_fault_types_var = tk.StringVar(value="-")
        self.custom_summary_vars = {
            name: tk.StringVar(value="-")
            for name in ("Campaign Name", "Fault Class", *self.METRIC_NAMES)
        }
        self.custom_loaded_slot_var = tk.StringVar(value="-")

        self.summary_vars = {
            "left": {name: tk.StringVar(value="-") for name in ("Campaign Name", "Fault Class", *self.METRIC_NAMES)},
            "right": {name: tk.StringVar(value="-") for name in ("Campaign Name", "Fault Class", *self.METRIC_NAMES)},
        }
        self.context_vars = {
            "left": {
                "Fault Class": tk.StringVar(value="-"),
                "Hardware Source": tk.StringVar(value="-"),
                "ECU Manifestation": tk.StringVar(value="-"),
            },
            "right": {
                "Fault Class": tk.StringVar(value="-"),
                "Hardware Source": tk.StringVar(value="-"),
                "ECU Manifestation": tk.StringVar(value="-"),
            },
        }
        self.metric_cells: Dict[str, Dict[str, Dict[str, tk.Widget]]] = {"left": {}, "right": {}}
        self.current_comparison: Dict[str, object] | None = None
        self.current_plot_results: Dict[str, object] | None = None
        self.loaded_result_slots: Dict[str, Dict[str, object] | None] = {"left": None, "right": None}
        self.last_custom_result: Dict[str, object] | None = None
        self.batch_rows: List[Dict[str, str]] = []
        self.batch_table: ttk.Treeview | None = None
        self.batch_plot: PlotCanvas | None = None
        self.comparison_plot: PlotCanvas | None = None
        self.presentation_bundle_button: ttk.Button | None = None
        self.propagation_evidence_table: ttk.Treeview | None = None
        self.left_fault_path_diagram: FaultPathDiagram | None = None
        self.right_fault_path_diagram: FaultPathDiagram | None = None
        self.multi_timeline_view: ScenarioTimelineView | None = None
        self.notebook: ttk.Notebook | None = None
        self.custom_builder_notebook: ttk.Notebook | None = None
        self.comparison_figures_tab: ttk.Frame | None = None
        self.page_frames: Dict[str, tk.Widget] = {}
        self.page_labels: Dict[str, str] = {}
        self.sidebar_buttons: Dict[str, tk.Widget] = {}
        self.sidebar_status_label: tk.Widget | None = None
        self.showcase_preset_selector: ttk.Combobox | None = None
        self.recent_results_frame: ttk.Frame | None = None
        self.favorite_selector: ttk.Combobox | None = None
        self.favorites_frame: ttk.Frame | None = None
        self.custom_preset_catalog: Dict[str, Dict[str, object]] = {}
        self.custom_preset_selector: ttk.Combobox | None = None
        self.multi_preset_catalog: Dict[str, Dict[str, object]] = {}
        self.multi_preset_selector: ttk.Combobox | None = None
        self.multi_event_listbox: tk.Listbox | None = None
        self.custom_action_buttons: List[ttk.Button] = []
        self.multi_events: List[Dict[str, object]] = [
            default_custom_event("sensor_bias", "transient", 20000, 10000, 8.0),
            default_custom_event("fan_stuck_off", "permanent", 65000, 0, 0.0),
        ]

        self._refresh_showcase_presets()
        self._refresh_recent_results()
        self._refresh_favorite_comparisons()
        self._configure_style()
        self._build_layout()
        self._apply_presentation_mode()
        self._refresh_campaign_context()
        self._reset_summary_values()
        self._clear_custom_result_summary()
        self._refresh_custom_preset_catalog()
        self._refresh_multi_preset_catalog()
        self._clear_batch_results()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if self.executable is None:
            self.status_text.set(
                "Compiled virtual ECU executable not found. Build it first with 'make' or your local GCC toolchain."
            )
            self.run_compare_button.state(["disabled"])
            self.run_left_button.state(["disabled"])
            self.snapshot_button.state(["disabled"])
            self.export_button.state(["disabled"])
            if self.presentation_bundle_button is not None:
                self.presentation_bundle_button.state(["disabled"])
            self._set_custom_controls_enabled(False)

        if DEFAULT_BATCH_AGGREGATE_CSV.exists():
            self.load_batch_results()
        self.after(0, self._maybe_auto_restore_session)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.configure("Root.TFrame", background=APP_BG)
        style.configure("Panel.TFrame", background="#eef3f7")
        style.configure("Card.TFrame", background=CARD_BG)
        style.configure("SoftCard.TFrame", background=SOFT_CARD_BG)
        style.configure("Header.TLabel", font=(UI_FONT, 20, "bold"), foreground=TEXT_DARK, background=APP_BG)
        style.configure("Subheader.TLabel", font=(UI_FONT, 10), foreground=TEXT_MUTED, background=APP_BG)
        style.configure("Section.TLabel", font=(UI_FONT, 13, "bold"), foreground=TEXT_DARK, background=APP_BG)
        style.configure("CardTitle.TLabel", font=(UI_FONT, 13, "bold"), foreground=TEXT_DARK, background=CARD_BG)
        style.configure("CardHint.TLabel", font=(UI_FONT, 9), foreground=TEXT_MUTED, background=CARD_BG)
        style.configure("CardFieldName.TLabel", font=(UI_FONT, 10, "bold"), foreground="#22313f", background=CARD_BG)
        style.configure("SoftCardTitle.TLabel", font=(UI_FONT, 11, "bold"), foreground=TEXT_DARK, background=SOFT_CARD_BG)
        style.configure("SoftCardHint.TLabel", font=(UI_FONT, 9), foreground=TEXT_MUTED, background=SOFT_CARD_BG)
        style.configure("FieldName.TLabel", font=(UI_FONT, 10, "bold"), foreground="#22313f")
        style.configure("FieldValue.TLabel", font=(UI_FONT, 10), foreground="#374553")
        style.configure("Hint.TLabel", font=(UI_FONT, 9), foreground="#4d5c69")
        style.configure("ColumnHeader.TLabel", font=(UI_FONT, 10, "bold"), foreground="#1d3448")
        style.configure("MetricLabel.TLabel", font=(UI_FONT, 10, "bold"), foreground="#1f3040")
        style.configure("Primary.TButton", padding=(12, 7), font=(UI_FONT, 10, "bold"))
        style.configure("Secondary.TButton", padding=(10, 6))
        style.configure("Batch.Treeview", rowheight=26, font=(UI_FONT, 9))
        style.configure("Batch.Treeview.Heading", font=(UI_FONT, 9, "bold"))
        style.configure("Evidence.Treeview", rowheight=52, font=(UI_FONT, 9))
        style.configure("Evidence.Treeview.Heading", font=(UI_FONT, 9, "bold"))
        style.configure("Sidebar.TNotebook", background=APP_BG, borderwidth=0)
        style.configure("Sidebar.TNotebook.Tab", padding=0)
        try:
            style.layout("Sidebar.TNotebook.Tab", [])
        except tk.TclError:
            pass

    def _build_layout(self) -> None:
        if CTK_AVAILABLE:
            self.configure(fg_color=APP_BG)
        else:
            self.configure(background=APP_BG)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._build_sidebar()

        content_shell = ttk.Frame(self, padding=(0, 0, 0, 0), style="Root.TFrame")
        content_shell.grid(row=0, column=1, sticky="nsew")
        content_shell.columnconfigure(0, weight=1)
        content_shell.rowconfigure(1, weight=1)

        header = ttk.Frame(content_shell, padding=(22, 18, 24, 12), style="Root.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=0)

        ttk.Label(header, text="Virtual ECU Research Explorer", style="Header.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="A dashboard-style control room for running experiments, comparing fault behavior, inspecting propagation, and exporting research artifacts.",
            style="Subheader.TLabel",
            wraplength=920,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(2, 8))

        header_controls = ttk.Frame(header, style="Root.TFrame")
        header_controls.grid(row=0, column=1, rowspan=2, sticky="ne")
        ttk.Checkbutton(
            header_controls,
            text="Presentation Mode",
            variable=self.presentation_mode,
            command=self._on_presentation_mode_toggled,
        ).grid(row=0, column=0, sticky="e")
        ttk.Label(
            header_controls,
            textvariable=self.status_text,
            foreground="#3d4b59",
            wraplength=360,
            justify="right",
        ).grid(row=1, column=0, sticky="e", pady=(8, 0))

        notebook = ttk.Notebook(content_shell, style="Sidebar.TNotebook")
        notebook.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        notebook.bind("<<NotebookTabChanged>>", self._on_main_page_changed)
        self.notebook = notebook

        dashboard_tab = ScrollableTabFrame(notebook, padding=(0, 0, 0, 0))
        dashboard_tab.content.columnconfigure(0, weight=1)
        notebook.add(dashboard_tab, text="Dashboard")
        self._register_page("dashboard", "Dashboard", dashboard_tab)

        summary_tab = ScrollableTabFrame(notebook)
        summary_tab.content.columnconfigure(0, weight=1)
        notebook.add(summary_tab, text="Run / Load")
        self._register_page("summary", "Run / Load", summary_tab)

        figures_tab = ScrollableTabFrame(notebook)
        figures_tab.content.columnconfigure(0, weight=1)
        notebook.add(figures_tab, text="Compare Figures")
        self.comparison_figures_tab = figures_tab
        self._register_page("figures", "Compare Figures", figures_tab)

        custom_tab = ScrollableTabFrame(notebook)
        custom_tab.content.columnconfigure(0, weight=1)
        notebook.add(custom_tab, text="Custom Faults")
        self._register_page("custom", "Custom Faults", custom_tab)

        fault_path_tab = ScrollableTabFrame(notebook)
        fault_path_tab.content.columnconfigure(0, weight=1)
        notebook.add(fault_path_tab, text="Fault Path")
        self._register_page("fault_path", "Fault Path", fault_path_tab)

        batch_tab = ScrollableTabFrame(notebook)
        batch_tab.content.columnconfigure(0, weight=1)
        notebook.add(batch_tab, text="Batch Results")
        self._register_page("batch", "Batch Results", batch_tab)

        exports_tab = ScrollableTabFrame(notebook)
        exports_tab.content.columnconfigure(0, weight=1)
        notebook.add(exports_tab, text="Export Reports")
        self._register_page("exports", "Export Reports", exports_tab)

        self._build_dashboard_tab(dashboard_tab.content)
        self._build_comparison_summary_tab(summary_tab.content)
        self._build_comparison_figures_tab(figures_tab.content)
        self._build_custom_experiment_tab(custom_tab.content)
        self._build_fault_path_tab(fault_path_tab.content)
        self._build_batch_tab(batch_tab.content)
        self._build_exports_tab(exports_tab.content)
        self._set_active_nav("dashboard")

    def _build_sidebar(self) -> None:
        if CTK_AVAILABLE:
            sidebar = ctk.CTkFrame(self, width=248, corner_radius=0, fg_color=SIDEBAR_BG)
        else:
            sidebar = tk.Frame(self, width=248, bg=SIDEBAR_BG)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.columnconfigure(0, weight=1)

        if CTK_AVAILABLE:
            ctk.CTkLabel(
                sidebar,
                text="virtual ECU",
                text_color=SIDEBAR_TEXT,
                font=(UI_FONT, 20, "bold"),
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=22, pady=(26, 2))
            ctk.CTkLabel(
                sidebar,
                text="Research dashboard",
                text_color="#b7c3d4",
                font=(UI_FONT, 12),
                anchor="w",
            ).grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 20))
        else:
            tk.Label(
                sidebar,
                text="virtual ECU",
                bg=SIDEBAR_BG,
                fg=SIDEBAR_TEXT,
                font=(UI_FONT, 20, "bold"),
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=22, pady=(26, 2))
            tk.Label(
                sidebar,
                text="Research dashboard",
                bg=SIDEBAR_BG,
                fg="#b7c3d4",
                font=(UI_FONT, 12),
                anchor="w",
            ).grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 20))

        nav_items = (
            ("dashboard", "Dashboard"),
            ("summary", "1. Run / Load"),
            ("figures", "2. Compare"),
            ("fault_path", "3. Fault Path"),
            ("batch", "4. Batch Results"),
            ("exports", "5. Exports"),
            ("custom", "Custom Faults"),
        )
        for row, (page_key, label) in enumerate(nav_items, start=2):
            button = self._create_sidebar_button(sidebar, page_key, label)
            button.grid(row=row, column=0, sticky="ew", padx=14, pady=4)
            self.sidebar_buttons[page_key] = button

        sidebar.rowconfigure(10, weight=1)
        if CTK_AVAILABLE:
            self.sidebar_status_label = ctk.CTkLabel(
                sidebar,
                textvariable=self.dashboard_runtime_var,
                text_color="#d4deec",
                fg_color="#1b2b4a",
                corner_radius=12,
                font=(UI_FONT, 11),
                wraplength=190,
                justify="left",
                anchor="w",
            )
        else:
            self.sidebar_status_label = tk.Label(
                sidebar,
                textvariable=self.dashboard_runtime_var,
                bg="#1b2b4a",
                fg="#d4deec",
                font=(UI_FONT, 11),
                wraplength=190,
                justify="left",
                anchor="w",
                padx=12,
                pady=10,
            )
        self.sidebar_status_label.grid(row=11, column=0, sticky="ew", padx=16, pady=(12, 22))

    def _create_sidebar_button(self, parent: tk.Misc, page_key: str, label: str) -> tk.Widget:
        if CTK_AVAILABLE:
            return ctk.CTkButton(
                parent,
                text=label,
                command=lambda key=page_key: self._navigate_to_page(key),
                height=38,
                corner_radius=10,
                fg_color="transparent",
                hover_color=SIDEBAR_HOVER,
                text_color=SIDEBAR_TEXT,
                font=(UI_FONT, 13, "bold"),
                anchor="w",
            )
        return tk.Button(
            parent,
            text=label,
            command=lambda key=page_key: self._navigate_to_page(key),
            bg=SIDEBAR_BG,
            fg=SIDEBAR_TEXT,
            activebackground=SIDEBAR_HOVER,
            activeforeground=SIDEBAR_TEXT,
            relief="flat",
            borderwidth=0,
            anchor="w",
            padx=14,
            pady=9,
            font=(UI_FONT, 12, "bold"),
        )

    def _register_page(self, page_key: str, label: str, frame: tk.Widget) -> None:
        self.page_frames[page_key] = frame
        self.page_labels[page_key] = label

    def _navigate_to_page(self, page_key: str) -> None:
        if self.notebook is None:
            return
        frame = self.page_frames.get(page_key)
        if frame is None:
            return
        try:
            self.notebook.select(frame)
        except tk.TclError:
            return
        self._set_active_nav(page_key)

    def _on_main_page_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if self.notebook is None:
            return
        selected = self.notebook.select()
        for page_key, frame in self.page_frames.items():
            try:
                if str(frame) == selected:
                    self._set_active_nav(page_key)
                    return
            except tk.TclError:
                return

    def _set_active_nav(self, active_key: str) -> None:
        for page_key, button in self.sidebar_buttons.items():
            is_active = page_key == active_key
            if CTK_AVAILABLE:
                button.configure(  # type: ignore[attr-defined]
                    fg_color=SIDEBAR_ACTIVE if is_active else "transparent",
                    text_color="#ffffff" if is_active else SIDEBAR_TEXT,
                )
            else:
                button.configure(  # type: ignore[attr-defined]
                    bg=SIDEBAR_ACTIVE if is_active else SIDEBAR_BG,
                    fg="#ffffff" if is_active else SIDEBAR_TEXT,
                )

    def _modern_frame(
        self,
        parent: tk.Misc,
        *,
        fg_color: str = CARD_BG,
        corner_radius: int = 16,
        border_color: str = "#d9e2ec",
        border_width: int = 1,
    ) -> tk.Widget:
        if CTK_AVAILABLE:
            return ctk.CTkFrame(
                parent,
                fg_color=fg_color,
                corner_radius=corner_radius,
                border_color=border_color,
                border_width=border_width,
            )
        return tk.Frame(parent, bg=fg_color, bd=1 if border_width else 0, relief="solid", highlightthickness=0)

    def _modern_label(
        self,
        parent: tk.Misc,
        text: str = "",
        *,
        textvariable: tk.StringVar | None = None,
        font: Tuple[str, int] | Tuple[str, int, str] = (UI_FONT, 11),
        text_color: str = TEXT_DARK,
        fg_color: str = CARD_BG,
        wraplength: int | None = None,
        justify: str = "left",
        anchor: str = "w",
    ) -> tk.Widget:
        if CTK_AVAILABLE:
            return ctk.CTkLabel(
                parent,
                text=text,
                textvariable=textvariable,
                font=font,
                text_color=text_color,
                fg_color=fg_color,
                wraplength=wraplength or 0,
                justify=justify,
                anchor=anchor,
            )
        return tk.Label(
            parent,
            text=text,
            textvariable=textvariable,
            font=font,
            fg=text_color,
            bg=fg_color,
            wraplength=wraplength or 0,
            justify=justify,
            anchor=anchor,
        )

    def _modern_button(
        self,
        parent: tk.Misc,
        text: str,
        command,
        *,
        color: str = SIDEBAR_ACTIVE,
    ) -> tk.Widget:
        if CTK_AVAILABLE:
            return ctk.CTkButton(
                parent,
                text=text,
                command=command,
                fg_color=color,
                hover_color="#1c63b7",
                text_color="#ffffff",
                height=38,
                corner_radius=10,
                font=(UI_FONT, 12, "bold"),
            )
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="#ffffff",
            activebackground="#1c63b7",
            activeforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=8,
            font=(UI_FONT, 11, "bold"),
        )

    def _section_card(
        self,
        parent: tk.Misc,
        *,
        title: str,
        description: str = "",
        fg_color: str = CARD_BG,
        border_color: str = "#dce6f1",
    ) -> tk.Widget:
        card = self._modern_frame(parent, fg_color=fg_color, corner_radius=16, border_color=border_color)
        card.columnconfigure(0, weight=1)
        title_style = "CardTitle.TLabel" if fg_color == CARD_BG else "SoftCardTitle.TLabel"
        hint_style = "CardHint.TLabel" if fg_color == CARD_BG else "SoftCardHint.TLabel"
        ttk.Label(card, text=title, style=title_style).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=16,
            pady=(16, 2 if description else 12),
        )
        if description:
            ttk.Label(
                card,
                text=description,
                style=hint_style,
                wraplength=980,
                justify="left",
            ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        return card

    def _card_content(self, card: tk.Widget, *, row: int = 2, padding: Tuple[int, int, int, int] = (16, 0, 16, 16)) -> ttk.Frame:
        content = ttk.Frame(card, padding=padding, style="Card.TFrame")
        content.grid(row=row, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        return content

    def _dashboard_card(
        self,
        parent: tk.Misc,
        *,
        row: int,
        column: int,
        title: str,
        value_var: tk.StringVar,
        accent: str,
        padx: Tuple[int, int] = (0, 10),
    ) -> None:
        card = self._modern_frame(parent, fg_color=CARD_BG, border_color="#dce6f1")
        card.grid(row=row, column=column, sticky="nsew", padx=padx, pady=(0, 10))
        card.columnconfigure(0, weight=1)
        self._modern_label(
            card,
            text=title,
            font=(UI_FONT, 10, "bold"),
            text_color=TEXT_MUTED,
            fg_color=CARD_BG,
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        self._modern_label(
            card,
            textvariable=value_var,
            font=(UI_FONT, 14, "bold"),
            text_color=TEXT_DARK,
            fg_color=CARD_BG,
            wraplength=245,
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
        accent_bar = tk.Frame(card, bg=accent, height=3)
        accent_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

    def _build_dashboard_tab(self, parent: ttk.Frame) -> None:
        shell = ttk.Frame(parent, padding=(12, 8, 12, 14), style="Root.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)

        hero = self._modern_frame(shell, fg_color="#10233f", corner_radius=20, border_width=0)
        hero.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        hero.columnconfigure(0, weight=1)
        hero.columnconfigure(1, weight=0)
        self._modern_label(
            hero,
            text="Virtual ECU Experiment Dashboard",
            font=(UI_FONT, 24, "bold"),
            text_color="#ffffff",
            fg_color="#10233f",
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 4))
        self._modern_label(
            hero,
            text=(
                "Run or load an experiment, compare baseline-vs-fault behavior, inspect the propagation path, "
                "review batch trends, and export publication-friendly bundles from one guided workspace."
            ),
            font=(UI_FONT, 12),
            text_color="#d7e2f2",
            fg_color="#10233f",
            wraplength=820,
        ).grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 24))
        self._modern_button(hero, "Run Default Comparison", self.run_comparison, color=ACCENT_GREEN).grid(
            row=0, column=1, rowspan=2, sticky="e", padx=24, pady=24
        )

        metrics = ttk.Frame(shell, style="Root.TFrame")
        metrics.grid(row=1, column=0, sticky="ew")
        for column in range(4):
            metrics.columnconfigure(column, weight=1)
        self._dashboard_card(metrics, row=0, column=0, title="Current Comparison", value_var=self.dashboard_comparison_var, accent=SIDEBAR_ACTIVE)
        self._dashboard_card(metrics, row=0, column=1, title="Export Readiness", value_var=self.dashboard_export_var, accent=ACCENT_GREEN)
        self._dashboard_card(metrics, row=0, column=2, title="Batch Results", value_var=self.dashboard_batch_var, accent=ACCENT_AMBER)
        self._dashboard_card(metrics, row=0, column=3, title="Custom Builder", value_var=self.dashboard_custom_var, accent=LEFT_COLOR, padx=(0, 0))

        workflow = self._modern_frame(shell, fg_color=CARD_BG, corner_radius=18, border_color="#dce6f1")
        workflow.grid(row=2, column=0, sticky="ew", pady=(4, 14))
        workflow.columnconfigure(0, weight=1)
        self._modern_label(
            workflow,
            text="Guided Workflow",
            font=(UI_FONT, 16, "bold"),
            text_color=TEXT_DARK,
            fg_color=CARD_BG,
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 4))
        self._modern_label(
            workflow,
            text="The left navigation follows the research workflow: run or load, compare, inspect the fault path, review batch evidence, then export.",
            font=(UI_FONT, 10),
            text_color=TEXT_MUTED,
            fg_color=CARD_BG,
            wraplength=980,
        ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))

        steps = ttk.Frame(workflow, style="Root.TFrame")
        steps.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 18))
        for column in range(5):
            steps.columnconfigure(column, weight=1)

        step_defs = (
            ("1", "Run or Load", "Start from built-in campaigns, saved CSV logs, showcase presets, or custom scenarios.", "summary"),
            ("2", "Compare", "Read coolant, safe-state, fan, and propagation figures from the current result pair.", "figures"),
            ("3", "Fault Path", "Explain how a hardware-origin fault moves through ECU-visible symptoms.", "fault_path"),
            ("4", "Batch", "Summarize aggregate sweep behavior without changing batch CSV schemas.", "batch"),
            ("5", "Export", "Generate snapshots, reports, and presentation bundles for papers or demos.", "exports"),
        )
        for column, (number, title, body, page_key) in enumerate(step_defs):
            card = self._modern_frame(steps, fg_color=SOFT_CARD_BG, corner_radius=14, border_color="#e1e8f0")
            card.grid(row=0, column=column, sticky="nsew", padx=(0, 8 if column < 4 else 0))
            card.columnconfigure(0, weight=1)
            self._modern_label(
                card,
                text=number,
                font=(UI_FONT, 12, "bold"),
                text_color=SIDEBAR_ACTIVE,
                fg_color=SOFT_CARD_BG,
            ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 2))
            self._modern_label(
                card,
                text=title,
                font=(UI_FONT, 11, "bold"),
                text_color=TEXT_DARK,
                fg_color=SOFT_CARD_BG,
            ).grid(row=1, column=0, sticky="ew", padx=14)
            self._modern_label(
                card,
                text=body,
                font=(UI_FONT, 9),
                text_color=TEXT_MUTED,
                fg_color=SOFT_CARD_BG,
                wraplength=175,
            ).grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 12))
            self._modern_button(card, f"Open {title}", lambda key=page_key: self._navigate_to_page(key)).grid(
                row=3, column=0, sticky="ew", padx=14, pady=(0, 14)
            )

        actions = ttk.Frame(shell, style="Root.TFrame")
        actions.grid(row=3, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.columnconfigure(2, weight=1)

        action_defs = (
            ("Showcase Comparison", "Load the selected saved thesis/demo pair without rerunning the simulator.", self.load_selected_showcase_preset),
            ("Custom Fault Builder", "Create a single custom fault or staged multi-fault scenario.", lambda: self._navigate_to_page("custom")),
            ("Export Reports", "Open the export page for snapshots, full reports, and presentation bundles.", lambda: self._navigate_to_page("exports")),
        )
        for column, (title, body, command) in enumerate(action_defs):
            card = self._modern_frame(actions, fg_color=CARD_BG, corner_radius=16, border_color="#dce6f1")
            card.grid(row=0, column=column, sticky="nsew", padx=(0, 10 if column < 2 else 0))
            card.columnconfigure(0, weight=1)
            self._modern_label(
                card,
                text=title,
                font=(UI_FONT, 13, "bold"),
                text_color=TEXT_DARK,
                fg_color=CARD_BG,
            ).grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 4))
            self._modern_label(
                card,
                text=body,
                font=(UI_FONT, 10),
                text_color=TEXT_MUTED,
                fg_color=CARD_BG,
                wraplength=330,
            ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
            self._modern_button(card, title, command).grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))

    def _build_exports_tab(self, parent: ttk.Frame) -> None:
        self._build_tab_header(
            parent,
            row=0,
            title="Export Reports",
            description=(
                "Exports are generated from the currently loaded left-versus-right comparison. "
                "Run or load a comparison first, then create the report bundle that matches your paper or demo need."
            ),
        )

        shell = ttk.Frame(parent, padding=(12, 0, 12, 12), style="Root.TFrame")
        shell.grid(row=1, column=0, sticky="ew")
        shell.columnconfigure(0, weight=1)
        shell.columnconfigure(1, weight=1)
        shell.columnconfigure(2, weight=1)

        export_defs = (
            (
                "Results Snapshot",
                "Compact markdown, text, CSV, and propagation assets for quick sharing.",
                "Export Snapshot",
                self.export_results_snapshot,
                SIDEBAR_ACTIVE,
            ),
            (
                "Full Comparison Report",
                "Comparison CSV, markdown/text report, figures, and propagation bundle.",
                "Export Full Report",
                self.export_current_comparison,
                ACCENT_GREEN,
            ),
            (
                "Presentation Bundle",
                "Presentation-ready summary, snapshot image, report bundle, and fault-path snapshots.",
                "Export Presentation Bundle",
                self.export_presentation_bundle,
                LEFT_COLOR,
            ),
        )
        for column, (title, body, button_text, command, color) in enumerate(export_defs):
            card = self._modern_frame(shell, fg_color=CARD_BG, corner_radius=16, border_color="#dce6f1")
            card.grid(row=0, column=column, sticky="nsew", padx=(0, 10 if column < 2 else 0))
            card.columnconfigure(0, weight=1)
            self._modern_label(
                card,
                text=title,
                font=(UI_FONT, 14, "bold"),
                text_color=TEXT_DARK,
                fg_color=CARD_BG,
            ).grid(row=0, column=0, sticky="ew", padx=16, pady=(18, 4))
            self._modern_label(
                card,
                text=body,
                font=(UI_FONT, 10),
                text_color=TEXT_MUTED,
                fg_color=CARD_BG,
                wraplength=320,
            ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
            self._modern_button(card, button_text, command, color=color).grid(
                row=2, column=0, sticky="ew", padx=16, pady=(0, 18)
            )

        status = self._modern_frame(parent, fg_color=CARD_BG, corner_radius=16, border_color="#dce6f1")
        status.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        status.columnconfigure(0, weight=1)
        self._modern_label(
            status,
            text="Current Export Status",
            font=(UI_FONT, 13, "bold"),
            text_color=TEXT_DARK,
            fg_color=CARD_BG,
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 4))
        self._modern_label(
            status,
            textvariable=self.dashboard_export_var,
            font=(UI_FONT, 11),
            text_color=TEXT_MUTED,
            fg_color=CARD_BG,
            wraplength=980,
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))

    def _build_comparison_summary_tab(self, parent: ttk.Frame) -> None:
        self._build_comparison_landing_panel(parent)

        selectors_area = ttk.Frame(parent, padding=(12, 0, 12, 12), style="Root.TFrame")
        selectors_area.grid(row=1, column=0, sticky="ew")
        selectors_area.columnconfigure(0, weight=1)
        selectors_area.columnconfigure(1, weight=1)
        selectors_area.columnconfigure(2, weight=0)

        self._build_selector_card(
            selectors_area,
            0,
            "Left Campaign",
            self.left_campaign,
            self.left_description_var,
            self._on_campaign_changed,
        )
        self._build_selector_card(
            selectors_area,
            1,
            "Right Campaign",
            self.right_campaign,
            self.right_description_var,
            self._on_campaign_changed,
        )

        actions_card = self._section_card(
            selectors_area,
            title="Run, Load, Export",
            description="Start with a run action, load saved CSVs when needed, then export from the loaded comparison.",
        )
        actions_card.grid(row=0, column=2, rowspan=2, sticky="ne", padx=(12, 0))
        actions = self._card_content(actions_card)
        actions.columnconfigure(0, weight=1)

        primary_actions = ttk.Frame(actions, style="Root.TFrame")
        primary_actions.grid(row=0, column=0, sticky="ew")
        primary_actions.columnconfigure(0, weight=1)
        self.run_compare_button = ttk.Button(
            primary_actions,
            text="Run Built-In Comparison",
            command=self.run_comparison,
            style="Primary.TButton",
        )
        self.run_compare_button.grid(row=0, column=0, sticky="ew")
        self.run_left_button = ttk.Button(
            primary_actions,
            text="Run Left Only",
            command=self.run_left_only,
            style="Secondary.TButton",
        )
        self.run_left_button.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        load_actions = ttk.Frame(actions, style="Root.TFrame")
        load_actions.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        load_actions.columnconfigure(0, weight=1)
        ttk.Label(load_actions, text="Load saved results", style="CardFieldName.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(load_actions, text="Load Result as Left", command=self.load_existing_as_left).grid(
            row=1, column=0, sticky="ew", pady=(6, 0)
        )
        ttk.Button(load_actions, text="Load Result as Right", command=self.load_existing_as_right).grid(
            row=2, column=0, sticky="ew", pady=(8, 0)
        )

        export_actions = ttk.Frame(actions, style="Root.TFrame")
        export_actions.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        export_actions.columnconfigure(0, weight=1)
        ttk.Label(export_actions, text="Export outputs", style="CardFieldName.TLabel").grid(row=0, column=0, sticky="w")
        self.snapshot_button = ttk.Button(export_actions, text="Export Snapshot", command=self.export_results_snapshot)
        self.snapshot_button.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.snapshot_button.state(["disabled"])
        self.export_button = ttk.Button(export_actions, text="Export Full Report", command=self.export_current_comparison)
        self.export_button.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.export_button.state(["disabled"])
        self.presentation_bundle_button = ttk.Button(
            export_actions,
            text="Export Presentation Bundle",
            command=self.export_presentation_bundle,
        )
        self.presentation_bundle_button.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.presentation_bundle_button.state(["disabled"])

        info_area = ttk.Frame(parent, padding=(12, 0, 12, 12), style="Root.TFrame")
        info_area.grid(row=2, column=0, sticky="ew")
        info_area.columnconfigure(0, weight=3)
        info_area.columnconfigure(1, weight=2)

        summary_card = self._section_card(
            info_area,
            title="Comparison Metrics",
            description="Side-by-side campaign identity, fault class, diagnostics, thermal severity, and safety timing.",
        )
        summary_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        summary_frame = self._card_content(summary_card)
        summary_frame.columnconfigure(0, minsize=190)
        summary_frame.columnconfigure(1, weight=1)
        summary_frame.columnconfigure(2, weight=1)

        ttk.Label(summary_frame, text="", style="ColumnHeader.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(summary_frame, text="Left Run", style="ColumnHeader.TLabel").grid(row=0, column=1, sticky="w", pady=(0, 8))
        ttk.Label(summary_frame, text="Right Run", style="ColumnHeader.TLabel").grid(row=0, column=2, sticky="w", pady=(0, 8))

        summary_rows = ["Campaign Name", "Fault Class", *self.METRIC_NAMES]
        for row_index, metric_name in enumerate(summary_rows, start=1):
            ttk.Label(summary_frame, text=metric_name, style="MetricLabel.TLabel").grid(
                row=row_index, column=0, sticky="nw", padx=(0, 12), pady=4
            )
            self._add_metric_cell(summary_frame, row_index, 1, "left", metric_name)
            self._add_metric_cell(summary_frame, row_index, 2, "right", metric_name)

        ttk.Label(
            summary_frame,
            text="Comparison mode is the main research/demo view. Single-run mode remains available for a focused left-campaign inspection.",
            style="Hint.TLabel",
            wraplength=620,
            justify="left",
        ).grid(row=len(summary_rows) + 1, column=0, columnspan=3, sticky="w", pady=(10, 0))

        context_card = self._section_card(
            info_area,
            title="Campaign Context",
            description="A compact hardware-origin-to-ECU story for each side of the comparison.",
        )
        context_card.grid(row=0, column=1, sticky="nsew")
        context_frame = self._card_content(context_card)
        context_frame.columnconfigure(0, weight=1)
        context_frame.columnconfigure(1, weight=1)

        self._build_context_column(context_frame, 0, "Left Context", "left", LEFT_COLOR)
        self._build_context_column(context_frame, 1, "Right Context", "right", RIGHT_COLOR)

        verdict_card = self._section_card(
            parent,
            title="Comparison Verdict",
            description="Automatically generated findings and a short takeaway for narration or report drafting.",
        )
        verdict_card.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        verdict_frame = self._card_content(verdict_card)
        verdict_frame.columnconfigure(0, weight=1)
        self._build_findings_cards(
            verdict_frame,
            self.comparison_verdict_var,
            self.comparison_takeaway_var,
            wraplength=540,
            findings_title="Verdict",
            interpretation_title="Key Takeaway",
        )

        self._build_saved_resources_panel(parent)

    def _build_comparison_figures_tab(self, parent: ttk.Frame) -> None:
        self._build_tab_header(
            parent,
            row=0,
            title="Comparison Figures",
            description=(
                "Use this tab after loading or running a comparison. Keep the selector focused on one figure at a time "
                "for cleaner screenshots and easier narration."
            ),
        )

        plots = ttk.Frame(parent, padding=(12, 0, 12, 12), style="Root.TFrame")
        plots.grid(row=1, column=0, sticky="nsew")
        plots.columnconfigure(0, weight=1)
        plots.rowconfigure(1, weight=1, minsize=560)
        plots.rowconfigure(2, weight=0)

        plot_header_card = self._section_card(
            plots,
            title="Figure Selection",
            description="Choose the comparison view that best supports the current research question.",
        )
        plot_header_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        plot_header = self._card_content(plot_header_card)
        plot_header.columnconfigure(0, weight=0)
        plot_header.columnconfigure(1, weight=0)
        plot_header.columnconfigure(2, weight=1)

        ttk.Label(plot_header, text="Comparison Plot", style="CardFieldName.TLabel").grid(row=0, column=0, sticky="w")
        selector = ttk.Combobox(
            plot_header,
            textvariable=self.comparison_plot_choice,
            values=list(self.COMPARISON_PLOT_OPTIONS),
            state="readonly",
            width=34,
        )
        selector.grid(row=0, column=1, sticky="w", padx=(10, 0))
        selector.bind("<<ComboboxSelected>>", self._on_plot_selection_changed)
        ttk.Label(
            plot_header,
            textvariable=self.comparison_plot_help_var,
            style="CardHint.TLabel",
            wraplength=680,
            justify="left",
        ).grid(row=0, column=2, sticky="w", padx=(14, 0))

        plot_card = self._section_card(
            plots,
            title="Comparison Dashboard",
            description="The active figure uses the loaded left/right result pair and updates without changing result files.",
        )
        plot_card.grid(row=1, column=0, sticky="nsew")
        plot_card.rowconfigure(2, weight=1)
        plot_body = self._card_content(plot_card)
        plot_body.rowconfigure(0, weight=1, minsize=560)
        self.comparison_plot = PlotCanvas(
            plot_body,
            self.comparison_plot_choice.get(),
            canvas_height=560,
        )
        self.comparison_plot.grid(row=0, column=0, sticky="nsew")
        self.comparison_plot.show_message("Run a comparison from the Comparison Summary page to display the selected plot here.")
        self._build_propagation_evidence_panel(plots)

    def _build_propagation_evidence_panel(self, parent: ttk.Frame) -> None:
        panel_card = self._section_card(
            parent,
            title="Propagation Evidence",
            description="Compact evidence from the same propagation-report logic used by the timeline and exports.",
        )
        panel_card.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        panel = self._card_content(panel_card)
        panel.columnconfigure(0, weight=1)

        table_area = ttk.Frame(panel)
        table_area.grid(row=0, column=0, sticky="ew")
        table_area.columnconfigure(0, weight=1)
        table_area.rowconfigure(0, weight=1)

        columns = ("run", "stage", "time", "signal", "explanation")
        self.propagation_evidence_table = ttk.Treeview(
            table_area,
            columns=columns,
            show="headings",
            height=6,
            style="Evidence.Treeview",
        )
        headings = {
            "run": "Run",
            "stage": "Stage",
            "time": "Time",
            "signal": "Observed Signal / Event",
            "explanation": "Short Explanation",
        }
        widths = {
            "run": 170,
            "stage": 220,
            "time": 84,
            "signal": 300,
            "explanation": 620,
        }
        min_widths = {
            "run": 150,
            "stage": 190,
            "time": 76,
            "signal": 240,
            "explanation": 420,
        }
        anchors = {
            "run": tk.W,
            "stage": tk.W,
            "time": tk.CENTER,
            "signal": tk.W,
            "explanation": tk.W,
        }
        for column_id in columns:
            self.propagation_evidence_table.heading(column_id, text=headings[column_id])
            self.propagation_evidence_table.column(
                column_id,
                width=widths[column_id],
                minwidth=min_widths[column_id],
                anchor=anchors[column_id],
                stretch=column_id in {"stage", "signal", "explanation"},
            )

        self.propagation_evidence_table.tag_configure("evidence_hardware", background="#f8e8e4")
        self.propagation_evidence_table.tag_configure("evidence_ecu", background="#eef5fc")
        self.propagation_evidence_table.tag_configure("evidence_diagnostic", background="#f8f1dc")
        self.propagation_evidence_table.tag_configure("evidence_safe_state", background="#edf7ee")
        self.propagation_evidence_table.tag_configure("evidence_thermal", background="#f3eef8")
        self.propagation_evidence_table.tag_configure("evidence_empty", background="#f7f9fb")

        scroll = ttk.Scrollbar(table_area, orient="vertical", command=self.propagation_evidence_table.yview)
        self.propagation_evidence_table.configure(yscrollcommand=scroll.set)
        x_scroll = ttk.Scrollbar(table_area, orient="horizontal", command=self.propagation_evidence_table.xview)
        self.propagation_evidence_table.configure(xscrollcommand=x_scroll.set)
        self.propagation_evidence_table.grid(row=0, column=0, sticky="ew")
        x_scroll.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        scroll.grid(row=0, column=1, sticky="ns")
        self._clear_propagation_evidence()

    def _build_custom_experiment_tab(self, parent: ttk.Frame) -> None:
        self._build_tab_header(
            parent,
            row=0,
            title="Custom Experiment",
            description=(
                "Build a single fault or staged scenario, use the main run actions first, and keep presets or advanced "
                "placement for the cases where you need a more specific comparison layout."
            ),
        )

        content = ttk.Frame(parent, padding=(12, 0, 12, 12), style="Root.TFrame")
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=8)
        content.columnconfigure(1, weight=3)
        content.rowconfigure(0, weight=1)

        builder_notebook = ttk.Notebook(content)
        builder_notebook.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.custom_builder_notebook = builder_notebook

        single_tab = ttk.Frame(builder_notebook, style="Root.TFrame")
        multi_tab = ttk.Frame(builder_notebook, style="Root.TFrame")
        for builder_tab in (single_tab, multi_tab):
            builder_tab.columnconfigure(0, weight=1)
            builder_tab.rowconfigure(0, weight=1)
        builder_notebook.add(single_tab, text="1. Single Fault")
        builder_notebook.add(multi_tab, text="2. Multi-Fault Scenario")

        self._build_single_custom_builder(single_tab)
        self._build_multi_custom_builder(multi_tab)

        summary_card = self._section_card(
            content,
            title="Last Custom Run",
            description="Confirm what ran, where it was loaded, and which result files were generated.",
        )
        summary_card.grid(row=0, column=1, sticky="nsew")
        summary = self._card_content(summary_card)
        summary.columnconfigure(1, weight=1)

        self._build_custom_metric_row(summary, 1, "Campaign Name", self.custom_summary_vars["Campaign Name"], wraplength=300)
        self._build_custom_metric_row(summary, 2, "Loaded Into", self.custom_loaded_slot_var, wraplength=300)
        self._build_custom_metric_row(summary, 3, "Fault Class", self.custom_summary_vars["Fault Class"])
        self._build_custom_metric_row(summary, 4, "Final DTC", self.custom_summary_vars["Final DTC"])
        self._build_custom_metric_row(summary, 5, "Final Safe State", self.custom_summary_vars["Final Safe State"])
        self._build_custom_metric_row(summary, 6, "Maximum Coolant Temperature", self.custom_summary_vars["Maximum Coolant Temperature"])
        self._build_custom_metric_row(summary, 7, "Detection Latency", self.custom_summary_vars["Detection Latency"])
        self._build_custom_metric_row(summary, 8, "Safe-State Latency", self.custom_summary_vars["Safe-State Latency"])
        self._build_custom_metric_row(summary, 9, "Saved Files", self.custom_saved_paths_var, wraplength=300)
        self._build_custom_metric_row(summary, 10, "Last Loaded Mode", self.custom_last_run_var, wraplength=300)

    def _build_single_custom_builder(self, parent: ttk.Frame) -> None:
        builder = self._section_card(
            parent,
            title="Single-Fault Builder",
            description="Set one injected fault, optionally save it as a preset, then run or compare it from the main action card.",
        )
        builder.grid(row=0, column=0, sticky="nsew")
        builder.columnconfigure(0, weight=1)

        setup_card = self._section_card(
            builder,
            title="1. Fault Setup",
            description="Defaults are demo-ready; tune timing and severity only when the experiment needs it.",
            fg_color=SOFT_CARD_BG,
            border_color="#e1e8f0",
        )
        setup_card.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))
        setup = self._card_content(setup_card, padding=(14, 0, 14, 14))
        setup.columnconfigure(1, weight=1)
        setup.columnconfigure(3, weight=1)

        ttk.Label(setup, text="Fault Type", style="FieldName.TLabel").grid(row=0, column=0, sticky="w")
        type_box = ttk.Combobox(
            setup,
            textvariable=self.custom_fault_type,
            values=[fault_type for fault_type, _label in CUSTOM_FAULT_TYPES],
            state="readonly",
            width=32,
        )
        type_box.grid(row=0, column=1, sticky="ew", padx=(10, 18), pady=(0, 8))
        type_box.bind("<<ComboboxSelected>>", self._on_custom_fault_type_changed)

        ttk.Label(setup, text="Fault Behavior", style="FieldName.TLabel").grid(row=0, column=2, sticky="w")
        behavior_box = ttk.Combobox(
            setup,
            textvariable=self.custom_fault_behavior,
            values=[behavior for behavior, _label in CUSTOM_FAULT_BEHAVIORS],
            state="readonly",
            width=18,
        )
        behavior_box.grid(row=0, column=3, sticky="ew", padx=(10, 0), pady=(0, 8))
        behavior_box.bind("<<ComboboxSelected>>", self._on_custom_fault_behavior_changed)

        ttk.Label(setup, text="Fault Start [ms]", style="FieldName.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Entry(setup, textvariable=self.custom_start_ms, width=18).grid(row=1, column=1, sticky="w", padx=(10, 18), pady=(0, 8))

        ttk.Label(setup, text="Fault Duration [ms]", style="FieldName.TLabel").grid(row=1, column=2, sticky="w")
        ttk.Entry(setup, textvariable=self.custom_duration_ms, width=18).grid(row=1, column=3, sticky="w", padx=(10, 0), pady=(0, 8))

        ttk.Label(setup, text="Fault Parameter", style="FieldName.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Entry(setup, textvariable=self.custom_parameter, width=18).grid(row=2, column=1, sticky="w", padx=(10, 18))

        ttk.Label(
            setup,
            text=(
                "Defaults are demo-ready. Start/duration are milliseconds, parameter is the fault severity, and duration "
                "0 is used only for permanent faults."
            ),
            style="Hint.TLabel",
            wraplength=700,
            justify="left",
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(10, 0))

        presets_card = self._section_card(
            builder,
            title="2. Presets",
            description="Save repeatable single-fault configurations without changing preset file formats.",
            fg_color=SOFT_CARD_BG,
            border_color="#e1e8f0",
        )
        presets_card.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 10))
        presets = self._card_content(presets_card, padding=(14, 0, 14, 14))
        presets.columnconfigure(1, weight=1)
        presets.columnconfigure(3, weight=1)

        ttk.Label(presets, text="Preset Name", style="FieldName.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(presets, textvariable=self.custom_preset_name, width=24).grid(row=0, column=1, sticky="w", padx=(10, 18), pady=(0, 8))

        ttk.Label(presets, text="Saved / Starter Preset", style="FieldName.TLabel").grid(row=0, column=2, sticky="w")
        self.custom_preset_selector = ttk.Combobox(
            presets,
            textvariable=self.custom_preset_choice,
            state="readonly",
            width=26,
        )
        self.custom_preset_selector.grid(row=0, column=3, sticky="ew", padx=(10, 0), pady=(0, 8))

        preset_actions = ttk.Frame(presets, style="Root.TFrame")
        preset_actions.grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 8))
        ttk.Button(preset_actions, text="Save Preset", command=self.save_custom_preset).grid(row=0, column=0, sticky="w")
        ttk.Button(preset_actions, text="Load Preset", command=self.load_selected_custom_preset).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(preset_actions, text="Delete Preset", command=self.delete_selected_custom_preset).grid(row=0, column=2, sticky="w", padx=(8, 0))

        ttk.Label(
            presets,
            text=(
                "Presets are stored as lightweight JSON files in `presets/gui_custom/`. Built-in starter presets are "
                "always available for quick demo setup, and user-saved presets keep repeated experiments reproducible."
            ),
            style="Hint.TLabel",
            wraplength=720,
            justify="left",
        ).grid(row=2, column=0, columnspan=4, sticky="w")

        actions_outer = self._section_card(
            builder,
            title="3. Run Actions",
            description="Primary actions execute the custom run and open the comparison workflow automatically.",
            fg_color=SOFT_CARD_BG,
            border_color="#e1e8f0",
        )
        actions_outer.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))
        actions_card = self._card_content(actions_outer, padding=(14, 0, 14, 14))
        actions_card.columnconfigure(0, weight=1)

        primary_actions = ttk.Frame(actions_card, style="Root.TFrame")
        primary_actions.grid(row=0, column=0, sticky="w")
        run_show = ttk.Button(
            primary_actions,
            text="Run Single Fault",
            command=self.run_custom_only,
            style="Primary.TButton",
        )
        run_show.grid(row=0, column=0, sticky="w")
        compare_show = ttk.Button(
            primary_actions,
            text="Compare vs Baseline",
            command=self.compare_custom_vs_baseline,
            style="Secondary.TButton",
        )
        compare_show.grid(row=0, column=1, sticky="w", padx=(8, 0))

        ttk.Label(
            actions_card,
            text=(
                "Main actions: use these first during demos. They run the custom fault, load it into the comparison workflow, "
                "and open the Comparison Figures tab automatically."
            ),
            style="Hint.TLabel",
            wraplength=720,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(10, 8))

        advanced = ttk.Frame(actions_card, style="Root.TFrame")
        advanced.grid(row=2, column=0, sticky="w")

        ttk.Label(advanced, text="Advanced placement:", style="FieldName.TLabel").grid(row=0, column=0, sticky="w")
        run_only = ttk.Button(advanced, text="Run to Left Only", command=self.run_custom_only)
        run_only.grid(row=0, column=1, sticky="w", padx=(8, 0))
        load_left = ttk.Button(advanced, text="Load as Left", command=self.load_custom_as_left)
        load_left.grid(row=0, column=2, sticky="w", padx=(8, 0))
        load_right = ttk.Button(advanced, text="Load as Right", command=self.load_custom_as_right)
        load_right.grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Label(
            actions_card,
            text=(
                "Advanced actions reuse the currently selected built-in campaign on the other side when baseline is not the comparison you want."
            ),
            style="Hint.TLabel",
            wraplength=720,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(10, 6))

        ttk.Label(
            actions_card,
            textvariable=self.custom_status_text,
            style="Hint.TLabel",
            wraplength=720,
            justify="left",
        ).grid(row=4, column=0, sticky="w", pady=(2, 0))

        self.custom_action_buttons.extend([run_show, compare_show, run_only, load_left, load_right])

    def _build_multi_custom_builder(self, parent: ttk.Frame) -> None:
        builder = self._section_card(
            parent,
            title="Multi-Fault Scenario Builder",
            description="Build an ordered fault sequence, inspect the live timeline, then run the staged scenario.",
        )
        builder.grid(row=0, column=0, sticky="nsew")
        builder.columnconfigure(0, weight=1)
        builder.rowconfigure(3, weight=1)

        editor_card = self._section_card(
            builder,
            title="1. Event Editor",
            description="Define one event at a time, then add or update it in the ordered scenario list.",
            fg_color=SOFT_CARD_BG,
            border_color="#e1e8f0",
        )
        editor_card.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))
        editor = self._card_content(editor_card, padding=(14, 0, 14, 14))
        editor.columnconfigure(1, weight=1)
        editor.columnconfigure(3, weight=1)
        editor.columnconfigure(4, weight=1)

        ttk.Label(editor, text="Fault Type", style="FieldName.TLabel").grid(row=0, column=0, sticky="w")
        type_box = ttk.Combobox(
            editor,
            textvariable=self.multi_fault_type,
            values=[fault_type for fault_type, _label in CUSTOM_FAULT_TYPES],
            state="readonly",
            width=28,
        )
        type_box.grid(row=0, column=1, sticky="ew", padx=(10, 18), pady=(0, 8))
        type_box.bind("<<ComboboxSelected>>", self._on_multi_fault_type_changed)

        ttk.Label(editor, text="Fault Behavior", style="FieldName.TLabel").grid(row=0, column=2, sticky="w")
        behavior_box = ttk.Combobox(
            editor,
            textvariable=self.multi_fault_behavior,
            values=[behavior for behavior, _label in CUSTOM_FAULT_BEHAVIORS],
            state="readonly",
            width=16,
        )
        behavior_box.grid(row=0, column=3, sticky="ew", padx=(10, 18), pady=(0, 8))
        behavior_box.bind("<<ComboboxSelected>>", self._on_multi_fault_behavior_changed)

        ttk.Label(editor, text="Fault Parameter", style="FieldName.TLabel").grid(row=0, column=4, sticky="w")
        ttk.Entry(editor, textvariable=self.multi_parameter, width=16).grid(row=0, column=4, sticky="e", pady=(0, 8))

        ttk.Label(editor, text="Fault Start [ms]", style="FieldName.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Entry(editor, textvariable=self.multi_start_ms, width=18).grid(row=1, column=1, sticky="w", padx=(10, 18), pady=(0, 8))

        ttk.Label(editor, text="Fault Duration [ms]", style="FieldName.TLabel").grid(row=1, column=2, sticky="w")
        ttk.Entry(editor, textvariable=self.multi_duration_ms, width=18).grid(row=1, column=3, sticky="w", padx=(10, 18), pady=(0, 8))

        ttk.Label(
            editor,
            text=(
                "Keep start times in the same order as the event list for the clearest thesis/demo story. "
                "Duration 0 remains reserved for permanent faults."
            ),
            style="Hint.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=2, column=0, columnspan=5, sticky="w", pady=(2, 0))

        event_actions = ttk.Frame(editor, style="Root.TFrame")
        event_actions.grid(row=3, column=0, columnspan=5, sticky="w", pady=(10, 0))
        ttk.Button(event_actions, text="Add Event", command=self.add_multi_event).grid(row=0, column=0, sticky="w")
        ttk.Button(event_actions, text="Update Selected", command=self.update_multi_event).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(event_actions, text="Remove Selected", command=self.remove_multi_event).grid(row=0, column=2, sticky="w", padx=(8, 0))
        ttk.Button(event_actions, text="Move Up", command=self.move_multi_event_up).grid(row=0, column=3, sticky="w", padx=(8, 0))
        ttk.Button(event_actions, text="Move Down", command=self.move_multi_event_down).grid(row=0, column=4, sticky="w", padx=(8, 0))
        ttk.Button(event_actions, text="Clear Scenario", command=self.clear_multi_events).grid(row=0, column=5, sticky="w", padx=(8, 0))

        middle = ttk.Frame(builder, style="Root.TFrame")
        middle.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 10))
        middle.columnconfigure(0, weight=1)
        middle.rowconfigure(0, weight=0, minsize=220)
        middle.rowconfigure(1, weight=1, minsize=410)

        list_card = self._section_card(
            middle,
            title="2. Scenario Event List",
            description="The ordered list is the execution order used by the simulator command and timeline.",
            fg_color=SOFT_CARD_BG,
            border_color="#e1e8f0",
        )
        list_card.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        list_frame = self._card_content(list_card, padding=(14, 0, 14, 14))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=0)

        self.multi_event_listbox = tk.Listbox(
            list_frame,
            height=9,
            activestyle="none",
            exportselection=False,
            bg="#ffffff",
            fg="#1f2e3b",
            selectbackground="#d6e4f5",
            selectforeground="#17324d",
            font=("TkDefaultFont", 11),
        )
        self.multi_event_listbox.grid(row=0, column=0, sticky="nsew")
        self.multi_event_listbox.bind("<<ListboxSelect>>", self._on_multi_event_selected)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.multi_event_listbox.yview)
        self.multi_event_listbox.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")
        ttk.Label(
            list_frame,
            text="The ordered list is the execution order used by the timeline and the run actions.",
            style="Hint.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        timeline_card = self._section_card(
            middle,
            title="3. Scenario Timeline",
            description="A live visual check for sequencing, overlap, and thesis/demo storytelling.",
            fg_color=SOFT_CARD_BG,
            border_color="#e1e8f0",
        )
        timeline_card.grid(row=1, column=0, sticky="nsew")
        timeline_frame = self._card_content(timeline_card, padding=(14, 0, 14, 14))
        timeline_frame.columnconfigure(0, weight=1)
        timeline_frame.rowconfigure(0, weight=1)
        self.multi_timeline_view = ScenarioTimelineView(timeline_frame)
        self.multi_timeline_view.grid(row=0, column=0, sticky="nsew")

        ttk.Label(
            timeline_frame,
            text="The timeline updates live as events are added, edited, removed, or reordered.",
            style="Hint.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

        presets_card = self._section_card(
            builder,
            title="4. Scenario Presets",
            description="Store the full ordered event list in the same lightweight JSON preset format.",
            fg_color=SOFT_CARD_BG,
            border_color="#e1e8f0",
        )
        presets_card.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 10))
        presets = self._card_content(presets_card, padding=(14, 0, 14, 14))
        presets.columnconfigure(1, weight=1)
        presets.columnconfigure(3, weight=1)

        ttk.Label(
            presets,
            text=(
                "Scenario presets store the full ordered event list in the same "
                "`presets/gui_custom/` folder used by the single-fault builder."
            ),
            style="Hint.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        ttk.Label(presets, text="Preset Name", style="FieldName.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Entry(presets, textvariable=self.multi_preset_name, width=28).grid(row=1, column=1, sticky="w", padx=(10, 18), pady=(0, 8))

        ttk.Label(presets, text="Saved / Starter Preset", style="FieldName.TLabel").grid(row=1, column=2, sticky="w")
        self.multi_preset_selector = ttk.Combobox(
            presets,
            textvariable=self.multi_preset_choice,
            state="readonly",
            width=28,
        )
        self.multi_preset_selector.grid(row=1, column=3, sticky="ew", padx=(10, 0), pady=(0, 8))

        preset_actions = ttk.Frame(presets, style="Root.TFrame")
        preset_actions.grid(row=2, column=0, columnspan=4, sticky="w")
        ttk.Button(preset_actions, text="Save Scenario Preset", command=self.save_multi_preset).grid(row=0, column=0, sticky="w")
        ttk.Button(preset_actions, text="Load Scenario Preset", command=self.load_selected_multi_preset).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(preset_actions, text="Delete Scenario Preset", command=self.delete_selected_multi_preset).grid(row=0, column=2, sticky="w", padx=(8, 0))

        actions_outer = self._section_card(
            builder,
            title="5. Run Actions",
            description="Run the staged scenario alone or compare it against a baseline/reference campaign.",
            fg_color=SOFT_CARD_BG,
            border_color="#e1e8f0",
        )
        actions_outer.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 16))
        actions_card = self._card_content(actions_outer, padding=(14, 0, 14, 14))
        actions_card.columnconfigure(0, weight=1)

        primary_actions = ttk.Frame(actions_card, style="Root.TFrame")
        primary_actions.grid(row=0, column=0, sticky="w")
        run_show = ttk.Button(
            primary_actions,
            text="Run Scenario",
            command=self.run_multi_only,
            style="Primary.TButton",
        )
        run_show.grid(row=0, column=0, sticky="w")
        compare_show = ttk.Button(
            primary_actions,
            text="Compare vs Baseline",
            command=self.compare_multi_vs_baseline,
            style="Secondary.TButton",
        )
        compare_show.grid(row=0, column=1, sticky="w", padx=(8, 0))

        ttk.Label(
            actions_card,
            text=(
                "Main actions: use these first during demos. The scenario is executed, loaded into the comparison workflow, "
                "and the Comparison Figures tab opens automatically."
            ),
            style="Hint.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(10, 8))

        actions = ttk.Frame(actions_card, style="Root.TFrame")
        actions.grid(row=2, column=0, sticky="w")
        ttk.Label(actions, text="Advanced placement:", style="FieldName.TLabel").grid(row=0, column=0, sticky="w")
        run_only = ttk.Button(actions, text="Run to Left Only", command=self.run_multi_only)
        run_only.grid(row=0, column=1, sticky="w", padx=(8, 0))
        load_left = ttk.Button(actions, text="Load as Left", command=self.load_multi_as_left)
        load_left.grid(row=0, column=2, sticky="w", padx=(8, 0))
        load_right = ttk.Button(actions, text="Load as Right", command=self.load_multi_as_right)
        load_right.grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Label(
            actions_card,
            text="Advanced placement keeps the main run path clean when you need a specific left/right setup.",
            style="Hint.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(10, 6))

        ttk.Label(
            actions_card,
            textvariable=self.custom_status_text,
            style="Hint.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=4, column=0, sticky="w", pady=(2, 0))

        self.custom_action_buttons.extend([run_show, compare_show, run_only, load_left, load_right])
        self._refresh_multi_event_listbox(select_index=0 if self.multi_events else None)

    def _build_custom_metric_row(
        self,
        parent: ttk.Frame,
        row: int,
        title: str,
        variable: tk.StringVar,
        *,
        wraplength: int = 280,
    ) -> None:
        ttk.Label(parent, text=title, style="CardFieldName.TLabel").grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=4)
        ttk.Label(
            parent,
            textvariable=variable,
            style="CardHint.TLabel",
            wraplength=wraplength,
            justify="left",
        ).grid(row=row, column=1, sticky="w", pady=4)

    def _build_fault_path_tab(self, parent: ttk.Frame) -> None:
        self._build_tab_header(
            parent,
            row=0,
            title="Fault Path",
            description=(
                "Read the ECU fault story from left to right: sensing, timing/link, control/memory, actuation, and "
                "final plant outcome. The reference side stays quiet so the fault case is easier to scan."
            ),
        )

        diagram_area = ttk.Frame(parent, padding=(12, 0, 12, 12), style="Root.TFrame")
        diagram_area.grid(row=1, column=0, sticky="nsew")
        diagram_area.columnconfigure(0, weight=1)
        diagram_area.columnconfigure(1, weight=1)
        diagram_area.rowconfigure(0, weight=1)

        left_card = self._section_card(
            diagram_area,
            title="Left Fault Path",
            description="Reference or selected left-side run mapped onto the ECU signal/control/actuation path.",
        )
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_card.rowconfigure(2, weight=1)
        left_frame = self._card_content(left_card, padding=(10, 0, 10, 10))
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(0, weight=1)
        self.left_fault_path_diagram = FaultPathDiagram(left_frame, "Left", LEFT_COLOR)
        self.left_fault_path_diagram.grid(row=0, column=0, sticky="nsew")

        right_card = self._section_card(
            diagram_area,
            title="Right Fault Path",
            description="Fault-case path highlighting affected subsystems, propagated blocks, and safety outcome.",
        )
        right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right_card.rowconfigure(2, weight=1)
        right_frame = self._card_content(right_card, padding=(10, 0, 10, 10))
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)
        self.right_fault_path_diagram = FaultPathDiagram(right_frame, "Right", RIGHT_COLOR)
        self.right_fault_path_diagram.grid(row=0, column=0, sticky="nsew")
        self._refresh_fault_path_diagrams()

    def _build_batch_tab(self, parent: ttk.Frame) -> None:
        self._build_tab_header(
            parent,
            row=0,
            title="Batch Results",
            description=(
                "Use this tab as a compact viewing layer for aggregate sweeps. Keep it focused on quick comparison and "
                "use the analysis scripts when you need publication-grade tables or figures."
            ),
        )

        controls_card = self._section_card(
            parent,
            title="Batch Aggregate Summary",
            description="Load an aggregate sweep CSV and inspect high-level fault-type trends without changing the batch schema.",
        )
        controls_card.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        controls = self._card_content(controls_card)
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Aggregate CSV", style="CardFieldName.TLabel").grid(row=0, column=0, sticky="w")
        path_entry = ttk.Entry(controls, textvariable=self.batch_csv_path)
        path_entry.grid(row=0, column=1, sticky="ew", padx=(10, 10))
        ttk.Button(controls, text="Browse", command=self.browse_batch_results).grid(row=0, column=2, sticky="e")
        ttk.Button(controls, text="Load Aggregate CSV", command=self.load_batch_results, style="Primary.TButton").grid(
            row=0, column=3, sticky="e", padx=(8, 0)
        )

        ttk.Label(
            controls,
            text="This tab is a lightweight viewing layer for aggregate sweep results. Use the analysis scripts for publication tables and figures.",
            style="CardHint.TLabel",
            wraplength=940,
            justify="left",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 4))
        ttk.Label(controls, textvariable=self.batch_status_text, style="CardHint.TLabel", wraplength=940, justify="left").grid(
            row=2, column=0, columnspan=4, sticky="w"
        )

        overview = ttk.Frame(parent, padding=(12, 0, 12, 12), style="Root.TFrame")
        overview.grid(row=2, column=0, sticky="ew")
        overview.columnconfigure(0, weight=1)
        overview.columnconfigure(1, weight=1)
        overview.columnconfigure(2, weight=1)

        self._build_batch_stat_card(overview, 0, "Number of Runs", self.batch_run_count_var)
        self._build_batch_stat_card(overview, 1, "Fault Classes Present", self.batch_fault_classes_var)
        self._build_batch_stat_card(overview, 2, "Fault Types Present", self.batch_fault_types_var)

        findings_card = self._section_card(
            parent,
            title="Batch Findings",
            description="Automatic aggregate interpretation for sweep-level behavior and paper-writing notes.",
        )
        findings_card.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        findings_frame = self._card_content(findings_card)
        findings_frame.columnconfigure(0, weight=1)
        self._build_findings_cards(
            findings_frame,
            self.batch_findings_var,
            self.batch_interpretation_var,
            wraplength=540,
        )

        content = ttk.Frame(parent, padding=(12, 0, 12, 12), style="Root.TFrame")
        content.grid(row=4, column=0, sticky="nsew")
        content.columnconfigure(0, weight=5)
        content.columnconfigure(1, weight=4)
        content.rowconfigure(0, weight=1)

        table_card = self._section_card(
            content,
            title="Per-Fault-Type Averages",
            description="A compact table of observability, thermal severity, and final safety outcomes.",
        )
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        table_frame = self._card_content(table_card)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = (
            "fault_type",
            "runs",
            "mean_detection_latency",
            "mean_safe_state_latency",
            "mean_max_temp",
            "mean_safe_mode_duration",
            "dominant_safe_state",
        )
        self.batch_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=10,
            style="Batch.Treeview",
        )
        headings = {
            "fault_type": "Fault Type",
            "runs": "Runs",
            "mean_detection_latency": "Mean Detection [ms]",
            "mean_safe_state_latency": "Mean Safe State [ms]",
            "mean_max_temp": "Mean Max Temp [C]",
            "mean_safe_mode_duration": "Mean Safe-Mode [ms]",
            "dominant_safe_state": "Dominant Final State",
        }
        widths = {
            "fault_type": 190,
            "runs": 60,
            "mean_detection_latency": 120,
            "mean_safe_state_latency": 125,
            "mean_max_temp": 120,
            "mean_safe_mode_duration": 125,
            "dominant_safe_state": 150,
        }
        anchors = {
            "fault_type": tk.W,
            "runs": tk.CENTER,
            "mean_detection_latency": tk.CENTER,
            "mean_safe_state_latency": tk.CENTER,
            "mean_max_temp": tk.CENTER,
            "mean_safe_mode_duration": tk.CENTER,
            "dominant_safe_state": tk.CENTER,
        }
        for column_id in columns:
            self.batch_table.heading(column_id, text=headings[column_id])
            self.batch_table.column(column_id, width=widths[column_id], anchor=anchors[column_id], stretch=column_id == "fault_type")

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.batch_table.yview)
        self.batch_table.configure(yscrollcommand=scroll.set)
        self.batch_table.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        plot_card = self._section_card(
            content,
            title="Batch Comparison View",
            description="Switch between latency, temperature, duration, and final safe-state distribution views.",
        )
        plot_card.grid(row=0, column=1, sticky="nsew")
        plot_frame = self._card_content(plot_card)
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(2, weight=1, minsize=320)

        plot_header = ttk.Frame(plot_frame, style="Card.TFrame")
        plot_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        plot_header.columnconfigure(2, weight=1)

        ttk.Label(plot_header, text="Batch Plot", style="CardFieldName.TLabel").grid(row=0, column=0, sticky="w")
        selector = ttk.Combobox(
            plot_header,
            textvariable=self.batch_plot_choice,
            values=list(self.BATCH_PLOT_OPTIONS),
            state="readonly",
            width=31,
        )
        selector.grid(row=0, column=1, sticky="w", padx=(10, 0))
        selector.bind("<<ComboboxSelected>>", self._on_batch_plot_selection_changed)

        ttk.Label(
            plot_frame,
            text="Use the selector to switch between observability, thermal severity, and safe-state outcome views from the currently loaded aggregate summary.",
            style="CardHint.TLabel",
            wraplength=360,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 8))
        self.batch_plot = PlotCanvas(plot_frame, self.batch_plot_choice.get(), canvas_height=300)
        self.batch_plot.grid(row=2, column=0, sticky="nsew")
        self.batch_plot.show_message("Load a batch aggregate summary CSV to view the sweep-level comparison.")

    def _build_tab_header(self, parent: ttk.Frame, *, row: int, title: str, description: str) -> None:
        header = ttk.Frame(parent, padding=(12, 8, 12, 10), style="Root.TFrame")
        header.grid(row=row, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=title, style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text=description,
            style="Hint.TLabel",
            wraplength=1050,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _build_selector_card(
        self,
        parent: ttk.Frame,
        column: int,
        title: str,
        variable: tk.StringVar,
        description_var: tk.StringVar,
        callback,
    ) -> None:
        card = self._section_card(
            parent,
            title=title,
            description="Select the campaign and review its research context before running.",
        )
        card.grid(row=0, column=column, sticky="ew")
        content = self._card_content(card)
        content.columnconfigure(1, weight=1)

        ttk.Label(content, text="Campaign", style="CardFieldName.TLabel").grid(row=0, column=0, sticky="w")
        box = ttk.Combobox(
            content,
            textvariable=variable,
            values=[campaign_id for campaign_id, _label in CAMPAIGNS],
            state="readonly",
            width=32,
        )
        box.grid(row=0, column=1, sticky="w", padx=(10, 0))
        box.bind("<<ComboboxSelected>>", callback)

        ttk.Label(
            content,
            textvariable=description_var,
            style="CardHint.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=1, column=1, sticky="w", pady=(6, 0))

    def _build_batch_stat_card(self, parent: ttk.Frame, column: int, title: str, variable: tk.StringVar) -> None:
        card = self._modern_frame(parent, fg_color=CARD_BG, corner_radius=16, border_color="#dce6f1")
        card.grid(row=0, column=column, sticky="nsew", padx=(0, 10 if column < 2 else 0))
        self._modern_label(
            card,
            text=title,
            fg_color=CARD_BG,
            text_color=TEXT_MUTED,
            font=(UI_FONT, 10, "bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 2))
        self._modern_label(
            card,
            textvariable=variable,
            fg_color=CARD_BG,
            text_color=TEXT_DARK,
            font=(UI_FONT, 12, "bold"),
            justify="left",
            wraplength=300,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(0, 14))

    def _set_custom_controls_enabled(self, enabled: bool) -> None:
        state = ["!disabled"] if enabled else ["disabled"]
        for button in self.custom_action_buttons:
            button.state(state)

    def _open_comparison_figures_tab(self) -> None:
        if self.notebook is not None and self.comparison_figures_tab is not None:
            self.notebook.select(self.comparison_figures_tab)
            self._set_active_nav("figures")

    def _clear_custom_result_summary(self) -> None:
        for variable in self.custom_summary_vars.values():
            variable.set("-")
        self.custom_saved_paths_var.set("-")
        self.custom_last_run_var.set("-")
        self.custom_loaded_slot_var.set("-")
        self.last_custom_result = None
        self._refresh_dashboard_state()

    def _refresh_dashboard_state(self) -> None:
        if self.current_comparison is not None:
            left_name = self.summary_vars["left"]["Campaign Name"].get()
            right_name = self.summary_vars["right"]["Campaign Name"].get()
            self.dashboard_comparison_var.set(f"{left_name} vs {right_name}")
            self.dashboard_export_var.set("Ready: snapshot, full report, and presentation bundle can be exported.")
        elif self.current_plot_results is not None:
            left_name = self.summary_vars["left"]["Campaign Name"].get()
            self.dashboard_comparison_var.set(f"Single run loaded: {left_name}")
            self.dashboard_export_var.set("Load or run a right-side result to enable comparison exports.")
        else:
            self.dashboard_comparison_var.set("No comparison loaded")
            self.dashboard_export_var.set("Run a left-versus-right comparison to enable exports.")

        if self.batch_rows:
            self.dashboard_batch_var.set(f"{len(self.batch_rows)} aggregate rows loaded")
        else:
            self.dashboard_batch_var.set("No batch aggregate loaded")

        custom_name = self.custom_summary_vars["Campaign Name"].get()
        if custom_name and custom_name != "-":
            self.dashboard_custom_var.set(custom_name)
        else:
            self.dashboard_custom_var.set("No custom run yet")

    def _refresh_showcase_presets(self) -> None:
        try:
            presets = read_showcase_presets()
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.showcase_presets = []
            self.showcase_preset_catalog = {}
            self.showcase_preset_choice.set("")
            self.showcase_description_var.set(f"Showcase presets are unavailable: {exc}")
            return

        self.showcase_presets = presets
        self.showcase_preset_catalog = {preset["title"]: preset for preset in presets}
        choices = list(self.showcase_preset_catalog)
        if self.showcase_preset_selector is not None:
            self.showcase_preset_selector.configure(values=choices)

        if choices:
            if self.showcase_preset_choice.get() not in self.showcase_preset_catalog:
                self.showcase_preset_choice.set(choices[0])
            self._update_showcase_description()
        else:
            self.showcase_preset_choice.set("")
            self.showcase_description_var.set("No showcase presets are defined yet.")

    def _selected_showcase_preset(self) -> Dict[str, str] | None:
        title = self.showcase_preset_choice.get().strip()
        return self.showcase_preset_catalog.get(title)

    def _update_showcase_description(self) -> None:
        preset = self._selected_showcase_preset()
        if preset is None:
            self.showcase_description_var.set("Select a showcase preset to load a saved comparison.")
            return

        self.showcase_description_var.set(
            f"{preset['description']} Sources: {preset['left_result']} vs {preset['right_result']}."
        )

    def _refresh_recent_results(self) -> None:
        try:
            self.recent_results = read_recent_results()
        except (OSError, TypeError, json.JSONDecodeError):
            self.recent_results = []

    def _refresh_favorite_comparisons(self) -> None:
        try:
            self.favorite_comparisons = read_favorite_comparisons()
        except (OSError, TypeError, json.JSONDecodeError):
            self.favorite_comparisons = []

    def _favorite_titles(self) -> List[str]:
        return [favorite["title"] for favorite in self.favorite_comparisons]

    def _favorite_signature(self, item: Dict[str, str]) -> Tuple[str, str]:
        return (item["left_result"], item["right_result"])

    def _current_comparison_signature(self) -> Tuple[str, str] | None:
        if self.current_comparison is None:
            return None
        left_result = self.current_comparison["left"]  # type: ignore[index]
        right_result = self.current_comparison["right"]  # type: ignore[index]
        return (
            _stored_result_path(Path(left_result["log_path"])),  # type: ignore[arg-type]
            _stored_result_path(Path(right_result["log_path"])),  # type: ignore[arg-type]
        )

    def _default_favorite_title(self) -> str:
        left_name = self.summary_vars["left"]["Campaign Name"].get().strip() or "Left Run"
        right_name = self.summary_vars["right"]["Campaign Name"].get().strip() or "Right Run"
        return f"{left_name} vs {right_name}"

    def _prefill_favorite_editor(self) -> None:
        signature = self._current_comparison_signature()
        if signature is None:
            self.favorite_choice.set("")
            self.favorite_title_var.set("")
            self.favorite_note_var.set("")
            return

        for favorite in self.favorite_comparisons:
            if self._favorite_signature(favorite) == signature:
                self.favorite_choice.set(favorite["title"])
                self.favorite_title_var.set(favorite["title"])
                self.favorite_note_var.set(favorite.get("note", ""))
                return

        self.favorite_choice.set("")
        self.favorite_title_var.set(self._default_favorite_title())
        self.favorite_note_var.set("")

    def _refresh_favorites_panel(self) -> None:
        if self.favorites_frame is not None:
            for child in self.favorites_frame.winfo_children():
                child.destroy()

            if not self.favorite_comparisons:
                ttk.Label(
                    self.favorites_frame,
                    text="No favorites yet. Load or run a comparison, then pin it here.",
                    style="Hint.TLabel",
                    justify="left",
                ).grid(row=0, column=0, columnspan=3, sticky="w")
            else:
                for index, favorite in enumerate(self.favorite_comparisons[:MAX_FAVORITES]):
                    row = index // 3
                    column = index % 3
                    title = favorite["title"]
                    if len(title) > 38:
                        title = title[:35] + "..."
                    ttk.Button(
                        self.favorites_frame,
                        text=title,
                        command=lambda favorite_item=dict(favorite): self.load_favorite_comparison(favorite_item),
                    ).grid(row=row, column=column, sticky="ew", padx=(0, 8 if column < 2 else 0), pady=3)

        if self.favorite_selector is not None:
            self.favorite_selector.configure(values=self._favorite_titles())

        if self.favorite_comparisons:
            if self.favorite_choice.get() not in self._favorite_titles():
                self._prefill_favorite_editor()
            else:
                self._sync_selected_favorite_fields()
        else:
            self._prefill_favorite_editor()

    def _selected_favorite(self) -> Dict[str, str] | None:
        title = self.favorite_choice.get().strip()
        for favorite in self.favorite_comparisons:
            if favorite["title"] == title:
                return favorite
        return None

    def _sync_selected_favorite_fields(self) -> None:
        favorite = self._selected_favorite()
        if favorite is None:
            if not self.favorite_title_var.get().strip():
                self.favorite_title_var.set("")
            if not self.favorite_note_var.get().strip():
                self.favorite_note_var.set("")
            return
        self.favorite_title_var.set(favorite["title"])
        self.favorite_note_var.set(favorite.get("note", ""))

    def _save_favorites(self) -> None:
        write_favorite_comparisons(self.favorite_comparisons)
        self._refresh_favorites_panel()

    def _refresh_recent_results_panel(self) -> None:
        if self.recent_results_frame is None:
            return

        for child in self.recent_results_frame.winfo_children():
            child.destroy()

        if not self.recent_results:
            ttk.Label(
                self.recent_results_frame,
                text="No recent items yet. Run or load a comparison and it will appear here.",
                style="Hint.TLabel",
                justify="left",
            ).grid(row=0, column=0, columnspan=3, sticky="w")
            return

        for index, item in enumerate(self.recent_results[:MAX_RECENT_RESULTS]):
            row = index // 3
            column = index % 3
            title = item["title"]
            if len(title) > 38:
                title = title[:35] + "..."
            button_text = f"{title}"
            ttk.Button(
                self.recent_results_frame,
                text=button_text,
                command=lambda recent_item=dict(item): self.load_recent_result(recent_item),
            ).grid(row=row, column=column, sticky="ew", padx=(0, 8 if column < 2 else 0), pady=3)

    def _remember_recent_result(self, item: Dict[str, str]) -> None:
        key = (item["left_result"], item.get("right_result", ""))
        remaining = [
            existing
            for existing in self.recent_results
            if (existing.get("left_result", ""), existing.get("right_result", "")) != key
        ]
        self.recent_results = [item, *remaining][:MAX_RECENT_RESULTS]
        try:
            write_recent_results(self.recent_results)
        except OSError:
            return
        self._refresh_recent_results_panel()

    def _remember_results(
        self,
        left_result: Dict[str, object],
        right_result: Dict[str, object] | None,
        *,
        kind: str,
        title: str | None = None,
        description: str = "",
    ) -> None:
        left_path = Path(left_result["log_path"])  # type: ignore[arg-type]
        right_path = Path(right_result["log_path"]) if right_result is not None else None  # type: ignore[arg-type]
        left_label = self.summary_vars["left"]["Campaign Name"].get()
        right_label = self.summary_vars["right"]["Campaign Name"].get() if right_result is not None else ""
        item_title = title or (f"{left_label} vs {right_label}" if right_result is not None else left_label)
        item_description = description or (
            "Recent comparison loaded through the GUI." if right_result is not None else "Recent single result loaded through the GUI."
        )
        self._remember_recent_result(
            _recent_result_item(
                item_title,
                kind=kind,
                description=item_description,
                left_path=left_path,
                right_path=right_path,
            )
        )

    def load_recent_result(self, item: Dict[str, str]) -> None:
        try:
            left_result, right_result = load_recent_result_item(item)
        except (OSError, RuntimeError, csv.Error) as exc:
            self.status_text.set("Recent item load failed.")
            messagebox.showerror("Recent Item Load Failed", str(exc))
            return

        self._apply_results(left_result, right_result, remember_recent=False)
        self._remember_recent_result(item)
        self._open_comparison_figures_tab()
        self.status_text.set(f"Reloaded recent item: {item['title']}.")

    def clear_recent_results(self) -> None:
        self.recent_results = []
        try:
            write_recent_results(self.recent_results)
        except OSError as exc:
            messagebox.showerror("Clear Recent History Failed", str(exc))
            return
        self._refresh_recent_results_panel()
        self.status_text.set("Recent results history cleared.")

    def add_current_comparison_to_favorites(self) -> None:
        if self.current_comparison is None:
            messagebox.showinfo("No Comparison Loaded", "Load or run a left-versus-right comparison first.")
            return

        title = self.favorite_title_var.get().strip()
        if not title:
            title = self._default_favorite_title()
        note = self.favorite_note_var.get().strip()
        left_result = self.current_comparison["left"]  # type: ignore[index]
        right_result = self.current_comparison["right"]  # type: ignore[index]
        item = _favorite_comparison_item(
            title,
            note=note,
            left_path=Path(left_result["log_path"]),  # type: ignore[arg-type]
            right_path=Path(right_result["log_path"]),  # type: ignore[arg-type]
        )

        key = self._favorite_signature(item)
        conflicting_title = next(
            (
                existing
                for existing in self.favorite_comparisons
                if existing["title"] == title and self._favorite_signature(existing) != key
            ),
            None,
        )
        if conflicting_title is not None:
            messagebox.showerror(
                "Favorite Title Already Used",
                "Another pinned comparison already uses this title.\n\n"
                "Choose a different title or load that favorite and edit it directly.",
            )
            return

        remaining = [
            existing
            for existing in self.favorite_comparisons
            if self._favorite_signature(existing) != key
        ]
        self.favorite_comparisons = [item, *remaining][:MAX_FAVORITES]
        try:
            self._save_favorites()
        except OSError as exc:
            messagebox.showerror("Save Favorite Failed", str(exc))
            return
        self.favorite_choice.set(title)
        self.status_text.set(f"Pinned favorite comparison: {title}.")

    def update_selected_favorite(self) -> None:
        favorite = self._selected_favorite()
        if favorite is None:
            messagebox.showinfo("No Favorite Selected", "Select a favorite comparison first.")
            return

        title = self.favorite_title_var.get().strip()
        if not title:
            messagebox.showerror("Invalid Favorite Title", "Favorite title must contain at least one letter or number.")
            return

        conflict = next(
            (
                existing
                for existing in self.favorite_comparisons
                if existing["title"] == title and existing["title"] != favorite["title"]
            ),
            None,
        )
        if conflict is not None:
            messagebox.showerror(
                "Favorite Title Already Used",
                "Another pinned comparison already uses this title.\n\n"
                "Choose a different title for this favorite.",
            )
            return

        note = self.favorite_note_var.get().strip()
        updated: List[Dict[str, str]] = []
        for existing in self.favorite_comparisons:
            if existing["title"] == favorite["title"]:
                updated.append(
                    {
                        "title": title,
                        "note": note,
                        "left_result": existing["left_result"],
                        "right_result": existing["right_result"],
                    }
                )
            elif existing["title"] != title:
                updated.append(existing)
        self.favorite_comparisons = updated[:MAX_FAVORITES]
        try:
            self._save_favorites()
        except OSError as exc:
            messagebox.showerror("Update Favorite Failed", str(exc))
            return
        self.favorite_choice.set(title)
        self.status_text.set(f"Updated favorite comparison: {title}.")

    def remove_selected_favorite(self) -> None:
        favorite = self._selected_favorite()
        if favorite is None:
            messagebox.showinfo("No Favorite Selected", "Select a favorite comparison first.")
            return

        self.favorite_comparisons = [
            existing for existing in self.favorite_comparisons if existing["title"] != favorite["title"]
        ]
        try:
            self._save_favorites()
        except OSError as exc:
            messagebox.showerror("Remove Favorite Failed", str(exc))
            return
        self.status_text.set(f"Removed favorite comparison: {favorite['title']}.")

    def load_favorite_comparison(self, item: Dict[str, str]) -> None:
        try:
            left_result, right_result = load_favorite_comparison_item(item)
        except (OSError, RuntimeError, csv.Error) as exc:
            self.status_text.set("Favorite comparison load failed.")
            messagebox.showerror("Favorite Comparison Load Failed", str(exc))
            return

        self._apply_results(
            left_result,
            right_result,
            remember_recent=True,
            recent_kind="favorite",
            recent_title=item["title"],
            recent_description=item.get("note", "") or "Favorite comparison reloaded through the GUI.",
        )
        self.favorite_choice.set(item["title"])
        self._sync_selected_favorite_fields()
        self._open_comparison_figures_tab()
        self.status_text.set(f"Loaded favorite comparison: {item['title']}.")

    def _session_result_reference(self, result: Dict[str, object] | None) -> str:
        if result is None:
            return ""
        return _stored_result_path(Path(result["log_path"]))  # type: ignore[arg-type]

    def _selected_notebook_index(self, notebook: ttk.Notebook | None) -> int:
        if notebook is None:
            return 0
        try:
            return int(notebook.index(notebook.select()))
        except tk.TclError:
            return 0

    def _restore_notebook_index(self, notebook: ttk.Notebook | None, index: object) -> None:
        if notebook is None:
            return
        try:
            target_index = int(index)
        except (TypeError, ValueError):
            return
        try:
            tab_count = int(notebook.index("end"))
        except tk.TclError:
            return
        if tab_count <= 0:
            return
        notebook.select(max(0, min(target_index, tab_count - 1)))
        self._on_main_page_changed()

    def _session_multi_events_payload(self) -> List[Dict[str, object]]:
        events: List[Dict[str, object]] = []
        for event in self.multi_events:
            events.append(
                {
                    "fault_type": str(event["fault_type"]),
                    "fault_behavior": str(event["fault_behavior"]),
                    "start_ms": int(event["start_ms"]),
                    "duration_ms": int(event["duration_ms"]),
                    "parameter": float(event["parameter"]),
                }
            )
        return events

    def _collect_session_state(self) -> Dict[str, object]:
        return {
            "version": 1,
            "auto_restore_last_session": bool(self.auto_restore_session.get()),
            "comparison_controls": {
                "left_campaign": self.left_campaign.get().strip(),
                "right_campaign": self.right_campaign.get().strip(),
                "comparison_plot_choice": self.comparison_plot_choice.get().strip(),
                "selected_main_tab": self._selected_notebook_index(self.notebook),
                "selected_showcase_title": self.showcase_preset_choice.get().strip(),
                "selected_favorite_title": self.favorite_choice.get().strip(),
                "favorite_title_edit": self.favorite_title_var.get().strip(),
                "favorite_note_edit": self.favorite_note_var.get().strip(),
                "presentation_mode": bool(self.presentation_mode.get()),
            },
            "loaded_results": {
                "left_slot_result": self._session_result_reference(self.loaded_result_slots.get("left")),
                "right_slot_result": self._session_result_reference(self.loaded_result_slots.get("right")),
                "current_comparison_left": (
                    self._session_result_reference(self.current_comparison.get("left"))  # type: ignore[union-attr]
                    if self.current_comparison is not None
                    else ""
                ),
                "current_comparison_right": (
                    self._session_result_reference(self.current_comparison.get("right"))  # type: ignore[union-attr]
                    if self.current_comparison is not None
                    else ""
                ),
                "last_custom_result": self._session_result_reference(self.last_custom_result),
            },
            "custom_single_fault": {
                "fault_type": self.custom_fault_type.get().strip(),
                "fault_behavior": self.custom_fault_behavior.get().strip(),
                "start_ms": self.custom_start_ms.get().strip(),
                "duration_ms": self.custom_duration_ms.get().strip(),
                "parameter": self.custom_parameter.get().strip(),
                "preset_name": self.custom_preset_name.get().strip(),
                "preset_choice": self.custom_preset_choice.get().strip(),
            },
            "multi_fault_builder": {
                "fault_type": self.multi_fault_type.get().strip(),
                "fault_behavior": self.multi_fault_behavior.get().strip(),
                "start_ms": self.multi_start_ms.get().strip(),
                "duration_ms": self.multi_duration_ms.get().strip(),
                "parameter": self.multi_parameter.get().strip(),
                "preset_name": self.multi_preset_name.get().strip(),
                "preset_choice": self.multi_preset_choice.get().strip(),
                "selected_builder_tab": self._selected_notebook_index(self.custom_builder_notebook),
                "selected_event_index": self._selected_multi_event_index(),
                "events": self._session_multi_events_payload(),
            },
            "batch_results": {
                "csv_path": self.batch_csv_path.get().strip(),
                "plot_choice": self.batch_plot_choice.get().strip(),
            },
            "recent_context": {
                "status_text": self.status_text.get().strip(),
                "custom_status_text": self.custom_status_text.get().strip(),
                "batch_status_text": self.batch_status_text.get().strip(),
            },
        }

    def _apply_saved_custom_single_state(self, payload: Dict[str, object]) -> None:
        self.custom_fault_type.set(str(payload.get("fault_type", self.custom_fault_type.get())))
        self.custom_fault_behavior.set(str(payload.get("fault_behavior", self.custom_fault_behavior.get())))
        self.custom_start_ms.set(str(payload.get("start_ms", self.custom_start_ms.get())))
        self.custom_duration_ms.set(str(payload.get("duration_ms", self.custom_duration_ms.get())))
        self.custom_parameter.set(str(payload.get("parameter", self.custom_parameter.get())))
        self.custom_preset_name.set(str(payload.get("preset_name", self.custom_preset_name.get())))
        self.custom_preset_choice.set(str(payload.get("preset_choice", self.custom_preset_choice.get())))

    def _apply_saved_multi_builder_state(self, payload: Dict[str, object]) -> None:
        events: List[Dict[str, object]] = []
        for raw_event in payload.get("events", []):  # type: ignore[assignment]
            if not isinstance(raw_event, dict):
                continue
            try:
                events.append(
                    default_custom_event(
                        fault_type=str(raw_event["fault_type"]),
                        fault_behavior=str(raw_event["fault_behavior"]),
                        start_ms=int(raw_event["start_ms"]),
                        duration_ms=int(raw_event["duration_ms"]),
                        parameter=float(raw_event["parameter"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue

        self.multi_events = events
        selected_index = payload.get("selected_event_index")
        try:
            select_index = None if selected_index is None else int(selected_index)
        except (TypeError, ValueError):
            select_index = None
        self._refresh_multi_event_listbox(select_index=select_index)

        self.multi_fault_type.set(str(payload.get("fault_type", self.multi_fault_type.get())))
        self.multi_fault_behavior.set(str(payload.get("fault_behavior", self.multi_fault_behavior.get())))
        self.multi_start_ms.set(str(payload.get("start_ms", self.multi_start_ms.get())))
        self.multi_duration_ms.set(str(payload.get("duration_ms", self.multi_duration_ms.get())))
        self.multi_parameter.set(str(payload.get("parameter", self.multi_parameter.get())))
        self.multi_preset_name.set(str(payload.get("preset_name", self.multi_preset_name.get())))
        self.multi_preset_choice.set(str(payload.get("preset_choice", self.multi_preset_choice.get())))
        self._restore_notebook_index(self.custom_builder_notebook, payload.get("selected_builder_tab", 0))

    def _restore_loaded_results_from_session(self, payload: Dict[str, object]) -> None:
        left_ref = str(payload.get("left_slot_result", "")).strip()
        right_ref = str(payload.get("right_slot_result", "")).strip()

        left_result = load_existing_result_pair(_project_path(left_ref)) if left_ref else None
        right_result = load_existing_result_pair(_project_path(right_ref)) if right_ref else None

        self.loaded_result_slots = {"left": None, "right": None}
        if left_result is not None and right_result is not None:
            self._apply_results(left_result, right_result, remember_recent=False)
            return
        if left_result is not None:
            self._apply_results(left_result, None, remember_recent=False)
            return
        if right_result is not None:
            self._apply_existing_result("right", right_result)
            return
        self._reset_summary_values()

    def _save_session_toggle_only(self) -> None:
        try:
            existing = read_gui_session_state() or {}
        except (OSError, TypeError, json.JSONDecodeError):
            existing = {}
        existing["auto_restore_last_session"] = bool(self.auto_restore_session.get())
        try:
            write_gui_session_state(existing)
        except OSError:
            return

    def save_session_state(self, *, quiet: bool = False) -> None:
        try:
            write_gui_session_state(self._collect_session_state())
        except OSError as exc:
            if quiet:
                return
            messagebox.showerror("Save Session Failed", str(exc))
            return

        if quiet:
            return
        self.status_text.set(f"Saved GUI session to {GUI_SESSION_STATE_PATH.relative_to(PROJECT_ROOT)}.")

    def restore_session_state(self, *, quiet: bool = False) -> None:
        try:
            payload = read_gui_session_state()
        except (OSError, TypeError, json.JSONDecodeError) as exc:
            if quiet:
                self.status_text.set(f"Session restore skipped: {exc}")
                return
            messagebox.showerror("Restore Session Failed", str(exc))
            return

        if payload is None:
            message = f"No saved GUI session found at {GUI_SESSION_STATE_PATH.relative_to(PROJECT_ROOT)}."
            if quiet:
                self.status_text.set(message)
            else:
                messagebox.showinfo("No Saved Session", message)
            return

        try:
            self.auto_restore_session.set(bool(payload.get("auto_restore_last_session", self.auto_restore_session.get())))

            comparison_controls = payload.get("comparison_controls", {})
            if isinstance(comparison_controls, dict):
                self.left_campaign.set(str(comparison_controls.get("left_campaign", self.left_campaign.get())))
                self.right_campaign.set(str(comparison_controls.get("right_campaign", self.right_campaign.get())))
                plot_choice = str(comparison_controls.get("comparison_plot_choice", self.comparison_plot_choice.get()))
                if plot_choice in self.COMPARISON_PLOT_OPTIONS:
                    self.comparison_plot_choice.set(plot_choice)
                self.presentation_mode.set(bool(comparison_controls.get("presentation_mode", self.presentation_mode.get())))
                self.showcase_preset_choice.set(str(comparison_controls.get("selected_showcase_title", self.showcase_preset_choice.get())))
                self.favorite_choice.set(str(comparison_controls.get("selected_favorite_title", self.favorite_choice.get())))
                self.favorite_title_var.set(str(comparison_controls.get("favorite_title_edit", self.favorite_title_var.get())))
                self.favorite_note_var.set(str(comparison_controls.get("favorite_note_edit", self.favorite_note_var.get())))

            self._apply_presentation_mode()
            self._refresh_campaign_context()

            custom_single = payload.get("custom_single_fault", {})
            if isinstance(custom_single, dict):
                self._apply_saved_custom_single_state(custom_single)

            multi_builder = payload.get("multi_fault_builder", {})
            if isinstance(multi_builder, dict):
                self._apply_saved_multi_builder_state(multi_builder)

            batch_payload = payload.get("batch_results", {})
            if isinstance(batch_payload, dict):
                self.batch_csv_path.set(str(batch_payload.get("csv_path", self.batch_csv_path.get())))
                batch_plot_choice = str(batch_payload.get("plot_choice", self.batch_plot_choice.get()))
                if batch_plot_choice in self.BATCH_PLOT_OPTIONS:
                    self.batch_plot_choice.set(batch_plot_choice)
                if self.batch_csv_path.get().strip():
                    self.load_batch_results()

            loaded_results = payload.get("loaded_results", {})
            if isinstance(loaded_results, dict):
                self._restore_loaded_results_from_session(loaded_results)

            recent_context = payload.get("recent_context", {})
            if isinstance(recent_context, dict):
                if self.current_comparison is None and not self.loaded_result_slots.get("right"):
                    saved_status = str(recent_context.get("status_text", "")).strip()
                    if saved_status:
                        self.status_text.set(saved_status)
                saved_custom_status = str(recent_context.get("custom_status_text", "")).strip()
                if saved_custom_status:
                    self.custom_status_text.set(saved_custom_status)
                if not self.batch_rows:
                    saved_batch_status = str(recent_context.get("batch_status_text", "")).strip()
                    if saved_batch_status:
                        self.batch_status_text.set(saved_batch_status)

            if isinstance(comparison_controls, dict):
                self._restore_notebook_index(self.notebook, comparison_controls.get("selected_main_tab", 0))
                self._update_showcase_description()
                if self.favorite_choice.get().strip():
                    self._sync_selected_favorite_fields()

            if not quiet:
                self.status_text.set(f"Restored GUI session from {GUI_SESSION_STATE_PATH.relative_to(PROJECT_ROOT)}.")
        except (OSError, RuntimeError, csv.Error, KeyError, TypeError, ValueError) as exc:
            if quiet:
                self.status_text.set(f"Automatic session restore skipped: {exc}")
                return
            messagebox.showerror("Restore Session Failed", str(exc))

    def _maybe_auto_restore_session(self) -> None:
        try:
            payload = read_gui_session_state()
        except (OSError, TypeError, json.JSONDecodeError) as exc:
            self.status_text.set(f"Automatic session restore skipped: {exc}")
            return

        if payload is None:
            return
        self.auto_restore_session.set(bool(payload.get("auto_restore_last_session", self.auto_restore_session.get())))
        if not self.auto_restore_session.get():
            return
        self.restore_session_state(quiet=True)

    def _on_close(self) -> None:
        self.save_session_state(quiet=True)
        self.destroy()

    def _current_custom_form_config(self) -> Dict[str, object] | None:
        return self._validate_custom_config()

    def _apply_custom_config_to_form(self, config: Dict[str, object]) -> None:
        self.custom_fault_type.set(str(config["fault_type"]))
        self.custom_fault_behavior.set(str(config["fault_behavior"]))
        self.custom_start_ms.set(str(int(config["start_ms"])))
        self.custom_duration_ms.set(str(int(config["duration_ms"])))
        self.custom_parameter.set(f"{float(config['parameter']):g}")

    def _current_multi_form_config(self) -> Dict[str, object] | None:
        return self._validate_multi_scenario_config()

    def _apply_multi_config_to_form(self, config: Dict[str, object]) -> None:
        self.multi_events = [default_custom_event(**event) for event in config["events"]]  # type: ignore[arg-type]
        self._refresh_multi_event_listbox(select_index=0 if self.multi_events else None)

    def _refresh_custom_preset_catalog(self) -> None:
        catalog: Dict[str, Dict[str, object]] = {}

        for name, payload in BUILTIN_CUSTOM_PRESETS.items():
            catalog[name] = {
                "source": "builtin",
                "path": None,
                "config": dict(payload),
            }

        for path in list_custom_preset_files():
            try:
                payload = read_custom_preset(path)
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                continue
            if str(payload.get("preset_kind", "single")) != "single":
                continue
            catalog[str(payload["preset_name"])] = {
                "source": "file",
                "path": path,
                "config": payload,
            }

        self.custom_preset_catalog = dict(sorted(catalog.items(), key=lambda item: item[0]))
        choices = list(self.custom_preset_catalog)
        if self.custom_preset_selector is not None:
            self.custom_preset_selector.configure(values=choices)

        if choices:
            if self.custom_preset_choice.get() not in self.custom_preset_catalog:
                self.custom_preset_choice.set(choices[0])
        else:
            self.custom_preset_choice.set("")

    def _refresh_multi_preset_catalog(self) -> None:
        catalog: Dict[str, Dict[str, object]] = {}

        for name, payload in BUILTIN_MULTI_CUSTOM_PRESETS.items():
            catalog[name] = {
                "source": "builtin",
                "path": None,
                "config": dict(payload),
            }

        for path in list_custom_preset_files():
            try:
                payload = read_custom_preset(path)
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                continue
            if str(payload.get("preset_kind", "single")) != "multi":
                continue
            catalog[str(payload["preset_name"])] = {
                "source": "file",
                "path": path,
                "config": payload,
            }

        self.multi_preset_catalog = dict(sorted(catalog.items(), key=lambda item: item[0]))
        choices = list(self.multi_preset_catalog)
        if self.multi_preset_selector is not None:
            self.multi_preset_selector.configure(values=choices)

        if choices:
            if self.multi_preset_choice.get() not in self.multi_preset_catalog:
                self.multi_preset_choice.set(choices[0])
        else:
            self.multi_preset_choice.set("")

    def _selected_multi_event_index(self) -> int | None:
        if self.multi_event_listbox is None:
            return None
        selection = self.multi_event_listbox.curselection()
        if not selection or not self.multi_events:
            return None
        return int(selection[0])

    def _multi_event_display(self, event: Dict[str, object], index: int) -> str:
        behavior = str(event["fault_behavior"])
        start_ms = int(event["start_ms"])
        duration_ms = int(event["duration_ms"])
        duration_label = "onward" if behavior == "permanent" and duration_ms == 0 else f"{duration_ms} ms"
        return (
            f"{index + 1}. {custom_mode_label(str(event['fault_type']))} | {behavior} | "
            f"start {start_ms} ms | duration {duration_label} | p={float(event['parameter']):g}"
        )

    def _refresh_multi_event_listbox(self, *, select_index: int | None = None) -> None:
        if self.multi_timeline_view is not None:
            self.multi_timeline_view.set_events(self.multi_events)

        if self.multi_event_listbox is None:
            return

        self.multi_event_listbox.delete(0, tk.END)
        if not self.multi_events:
            self.multi_event_listbox.insert(tk.END, "Add 2 to 4 events to define a multi-fault scenario.")
            return

        for index, event in enumerate(self.multi_events):
            self.multi_event_listbox.insert(tk.END, self._multi_event_display(event, index))

        if select_index is None:
            select_index = 0
        select_index = max(0, min(select_index, len(self.multi_events) - 1))
        self.multi_event_listbox.selection_clear(0, tk.END)
        self.multi_event_listbox.selection_set(select_index)
        self.multi_event_listbox.activate(select_index)
        self._set_multi_editor_event(self.multi_events[select_index])

    def _set_multi_editor_event(self, event: Dict[str, object]) -> None:
        self.multi_fault_type.set(str(event["fault_type"]))
        self.multi_fault_behavior.set(str(event["fault_behavior"]))
        self.multi_start_ms.set(str(int(event["start_ms"])))
        self.multi_duration_ms.set(str(int(event["duration_ms"])))
        self.multi_parameter.set(f"{float(event['parameter']):g}")

    def save_custom_preset(self) -> None:
        config = self._current_custom_form_config()
        if config is None:
            return

        name = self.custom_preset_name.get().strip()
        sanitized = sanitize_preset_name(name)
        if not sanitized:
            messagebox.showerror(
                "Invalid Preset Name",
                "Preset name must contain at least one letter or number.",
            )
            return

        payload = custom_preset_payload(sanitized, config)
        path = preset_file_path(sanitized)
        write_custom_preset(path, payload)
        self.custom_preset_name.set(sanitized)
        self._refresh_custom_preset_catalog()
        self._refresh_multi_preset_catalog()
        self.custom_preset_choice.set(sanitized)
        self.custom_status_text.set(
            f"Saved preset '{sanitized}' to {path.relative_to(PROJECT_ROOT)}. You can now reload it for repeated demo or study runs."
        )

    def load_selected_custom_preset(self) -> None:
        preset_name = self.custom_preset_choice.get().strip()
        if not preset_name:
            messagebox.showinfo("No Preset Selected", "Select a built-in or saved preset first.")
            return

        record = self.custom_preset_catalog.get(preset_name)
        if record is None:
            messagebox.showerror("Preset Not Found", f"The selected preset '{preset_name}' is no longer available.")
            self._refresh_custom_preset_catalog()
            return

        config = dict(record["config"])  # type: ignore[arg-type]
        self._apply_custom_config_to_form(config)
        self.custom_preset_name.set(str(config["preset_name"]))
        source = "built-in starter preset" if record["source"] == "builtin" else f"saved preset from {Path(record['path']).relative_to(PROJECT_ROOT)}"
        self.custom_status_text.set(
            f"Loaded preset '{preset_name}' from the {source}. The Custom Experiment form is ready to run."
        )

    def delete_selected_custom_preset(self) -> None:
        preset_name = self.custom_preset_choice.get().strip()
        if not preset_name:
            messagebox.showinfo("No Preset Selected", "Select a saved preset first.")
            return

        record = self.custom_preset_catalog.get(preset_name)
        if record is None:
            messagebox.showerror("Preset Not Found", f"The selected preset '{preset_name}' is no longer available.")
            self._refresh_custom_preset_catalog()
            return

        if record["source"] != "file":
            messagebox.showinfo(
                "Built-In Preset",
                "Built-in starter presets stay available for demos and cannot be deleted.",
            )
            return

        path = Path(record["path"])  # type: ignore[arg-type]
        try:
            path.unlink()
        except OSError as exc:
            messagebox.showerror("Delete Failed", f"Failed to delete preset '{preset_name}': {exc}")
            return

        self._refresh_custom_preset_catalog()
        self._refresh_multi_preset_catalog()
        self.custom_status_text.set(
            f"Deleted preset '{preset_name}' from {path.relative_to(PROJECT_ROOT)}."
        )

    def _validate_custom_event_values(
        self,
        *,
        fault_type: str,
        behavior: str,
        start_text: str,
        duration_text: str,
        parameter_text: str,
        error_title: str,
    ) -> Dict[str, object] | None:
        try:
            start_ms = int(start_text.strip())
        except ValueError:
            messagebox.showerror(error_title, "Fault start time must be an integer number of milliseconds.")
            return None

        try:
            duration_ms = int(duration_text.strip())
        except ValueError:
            messagebox.showerror(error_title, "Fault duration must be an integer number of milliseconds.")
            return None

        try:
            parameter = float(parameter_text.strip())
        except ValueError:
            messagebox.showerror(error_title, "Fault parameter must be numeric.")
            return None

        if fault_type not in {mode for mode, _label in CUSTOM_FAULT_TYPES}:
            messagebox.showerror(error_title, "Select one of the supported custom fault types.")
            return None

        if behavior not in {name for name, _label in CUSTOM_FAULT_BEHAVIORS}:
            messagebox.showerror(error_title, "Select either transient or permanent fault behavior.")
            return None

        if start_ms < 0:
            messagebox.showerror(error_title, "Fault start time must be greater than or equal to 0 ms.")
            return None

        if duration_ms < 0:
            messagebox.showerror(error_title, "Fault duration must be greater than or equal to 0 ms.")
            return None

        if behavior != "permanent" and duration_ms == 0:
            messagebox.showerror(
                error_title,
                "Duration 0 is reserved for permanent faults because the simulator interprets it as persistent from the start time.",
            )
            return None

        return {
            "fault_type": fault_type,
            "fault_behavior": behavior,
            "start_ms": start_ms,
            "duration_ms": duration_ms,
            "parameter": parameter,
        }

    def _current_multi_editor_event(self) -> Dict[str, object] | None:
        return self._validate_custom_event_values(
            fault_type=self.multi_fault_type.get().strip(),
            behavior=self.multi_fault_behavior.get().strip(),
            start_text=self.multi_start_ms.get(),
            duration_text=self.multi_duration_ms.get(),
            parameter_text=self.multi_parameter.get(),
            error_title="Invalid Multi-Fault Event",
        )

    def add_multi_event(self) -> None:
        event = self._current_multi_editor_event()
        if event is None:
            return
        if len(self.multi_events) >= MAX_CUSTOM_SCENARIO_EVENTS:
            messagebox.showinfo(
                "Scenario Full",
                f"This lightweight builder supports up to {MAX_CUSTOM_SCENARIO_EVENTS} ordered fault events.",
            )
            return

        self.multi_events.append(event)
        self._refresh_multi_event_listbox(select_index=len(self.multi_events) - 1)
        self.custom_status_text.set(
            f"Added event {len(self.multi_events)} to the multi-fault scenario. Build 2 to {MAX_CUSTOM_SCENARIO_EVENTS} events, then run it."
        )

    def update_multi_event(self) -> None:
        index = self._selected_multi_event_index()
        if index is None:
            messagebox.showinfo("No Event Selected", "Select an event from the scenario list first.")
            return

        event = self._current_multi_editor_event()
        if event is None:
            return

        self.multi_events[index] = event
        self._refresh_multi_event_listbox(select_index=index)
        self.custom_status_text.set(f"Updated scenario event {index + 1}.")

    def remove_multi_event(self) -> None:
        index = self._selected_multi_event_index()
        if index is None:
            messagebox.showinfo("No Event Selected", "Select an event from the scenario list first.")
            return

        del self.multi_events[index]
        next_index = min(index, len(self.multi_events) - 1) if self.multi_events else None
        self._refresh_multi_event_listbox(select_index=next_index)
        self.custom_status_text.set("Removed the selected scenario event.")

    def move_multi_event_up(self) -> None:
        index = self._selected_multi_event_index()
        if index is None or index == 0:
            return

        self.multi_events[index - 1], self.multi_events[index] = self.multi_events[index], self.multi_events[index - 1]
        self._refresh_multi_event_listbox(select_index=index - 1)
        self.custom_status_text.set(f"Moved event {index + 1} up in the ordered scenario.")

    def move_multi_event_down(self) -> None:
        index = self._selected_multi_event_index()
        if index is None or index >= len(self.multi_events) - 1:
            return

        self.multi_events[index + 1], self.multi_events[index] = self.multi_events[index], self.multi_events[index + 1]
        self._refresh_multi_event_listbox(select_index=index + 1)
        self.custom_status_text.set(f"Moved event {index + 1} down in the ordered scenario.")

    def clear_multi_events(self) -> None:
        self.multi_events = []
        self._refresh_multi_event_listbox(select_index=None)
        self.custom_status_text.set("Cleared the current multi-fault scenario. Add 2 to 4 events to run a new one.")

    def save_multi_preset(self) -> None:
        config = self._current_multi_form_config()
        if config is None:
            return

        name = self.multi_preset_name.get().strip()
        sanitized = sanitize_preset_name(name)
        if not sanitized:
            messagebox.showerror(
                "Invalid Preset Name",
                "Preset name must contain at least one letter or number.",
            )
            return

        payload = custom_preset_payload(sanitized, config)
        path = preset_file_path(sanitized)
        write_custom_preset(path, payload)
        self.multi_preset_name.set(sanitized)
        self._refresh_custom_preset_catalog()
        self._refresh_multi_preset_catalog()
        self.multi_preset_choice.set(sanitized)
        self.custom_status_text.set(
            f"Saved multi-fault preset '{sanitized}' to {path.relative_to(PROJECT_ROOT)}."
        )

    def load_selected_multi_preset(self) -> None:
        preset_name = self.multi_preset_choice.get().strip()
        if not preset_name:
            messagebox.showinfo("No Preset Selected", "Select a built-in or saved multi-fault preset first.")
            return

        record = self.multi_preset_catalog.get(preset_name)
        if record is None:
            messagebox.showerror("Preset Not Found", f"The selected preset '{preset_name}' is no longer available.")
            self._refresh_multi_preset_catalog()
            return

        config = dict(record["config"])  # type: ignore[arg-type]
        self._apply_multi_config_to_form(config)
        self.multi_preset_name.set(str(config["preset_name"]))
        source = "built-in starter preset" if record["source"] == "builtin" else f"saved preset from {Path(record['path']).relative_to(PROJECT_ROOT)}"
        self.custom_status_text.set(
            f"Loaded multi-fault preset '{preset_name}' from the {source}. The ordered scenario is ready to run."
        )

    def delete_selected_multi_preset(self) -> None:
        preset_name = self.multi_preset_choice.get().strip()
        if not preset_name:
            messagebox.showinfo("No Preset Selected", "Select a saved multi-fault preset first.")
            return

        record = self.multi_preset_catalog.get(preset_name)
        if record is None:
            messagebox.showerror("Preset Not Found", f"The selected preset '{preset_name}' is no longer available.")
            self._refresh_multi_preset_catalog()
            return

        if record["source"] != "file":
            messagebox.showinfo(
                "Built-In Preset",
                "Built-in starter presets stay available for demos and cannot be deleted.",
            )
            return

        path = Path(record["path"])  # type: ignore[arg-type]
        try:
            path.unlink()
        except OSError as exc:
            messagebox.showerror("Delete Failed", f"Failed to delete preset '{preset_name}': {exc}")
            return

        self._refresh_custom_preset_catalog()
        self._refresh_multi_preset_catalog()
        self.custom_status_text.set(
            f"Deleted multi-fault preset '{preset_name}' from {path.relative_to(PROJECT_ROOT)}."
        )

    def _update_custom_result_summary(self, result: Dict[str, object], loaded_mode: str, loaded_slot: str) -> None:
        summary = result["summary_row"]  # type: ignore[assignment]
        first_row = result["raw_rows"][0]  # type: ignore[index]
        campaign_id = str(result["campaign_id"])
        self.custom_summary_vars["Campaign Name"].set(str(summary.get("campaign_label", campaign_id)))
        self.custom_loaded_slot_var.set(loaded_slot)
        self.custom_summary_vars["Fault Class"].set(summarize_fault_class(campaign_id, first_row))
        self.custom_summary_vars["Final DTC"].set(str(summary.get("final_primary_dtc_label", "none")))
        self.custom_summary_vars["Final Safe State"].set(str(summary.get("final_safe_state_label", "normal")))
        self.custom_summary_vars["Maximum Coolant Temperature"].set(format_temperature(str(summary.get("max_coolant_temp_c", ""))))
        self.custom_summary_vars["Detection Latency"].set(format_latency(str(summary.get("detection_latency_ms", ""))))
        self.custom_summary_vars["Safe-State Latency"].set(format_latency(str(summary.get("safe_state_latency_ms", ""))))
        self.custom_saved_paths_var.set(
            f"{Path(result['log_path']).relative_to(PROJECT_ROOT)}\n{Path(result['summary_path']).relative_to(PROJECT_ROOT)}"
        )
        self.custom_last_run_var.set(loaded_mode)
        self.last_custom_result = result
        self._refresh_dashboard_state()

    def _build_findings_cards(
        self,
        parent: ttk.Frame,
        findings_var: tk.StringVar,
        interpretation_var: tk.StringVar,
        *,
        wraplength: int,
        findings_title: str = "Key Findings",
        interpretation_title: str = "Interpretation",
    ) -> None:
        cards = ttk.Frame(parent, style="Root.TFrame")
        cards.grid(row=0, column=0, sticky="ew")
        cards.columnconfigure(0, weight=3)
        cards.columnconfigure(1, weight=2)

        self._build_text_card(
            cards,
            0,
            findings_title,
            findings_var,
            wraplength=wraplength,
            body_font=("TkDefaultFont", 10, "bold"),
            body_fg="#22313f",
        )
        self._build_text_card(
            cards,
            1,
            interpretation_title,
            interpretation_var,
            wraplength=wraplength,
            body_font=("TkDefaultFont", 10),
            body_fg="#425160",
        )

    def _build_text_card(
        self,
        parent: ttk.Frame,
        column: int,
        title: str,
        variable: tk.StringVar,
        *,
        wraplength: int,
        body_font: Tuple[str, int] | Tuple[str, int, str],
        body_fg: str,
    ) -> None:
        card = self._modern_frame(parent, fg_color=CARD_BG, corner_radius=14, border_color="#dce6f1")
        card.grid(row=0, column=column, sticky="nsew", padx=(0, 10 if column == 0 else 0))

        self._modern_label(
            card,
            text=title,
            fg_color=CARD_BG,
            text_color=TEXT_DARK,
            font=(UI_FONT, 11, "bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 4))
        self._modern_label(
            card,
            textvariable=variable,
            fg_color=CARD_BG,
            text_color=body_fg,
            font=(UI_FONT, body_font[1], body_font[2]) if len(body_font) > 2 else (UI_FONT, body_font[1]),
            justify="left",
            wraplength=wraplength,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(0, 14))

    def _build_quick_start_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Quick Start / Guided Use", padding=12)
        panel.grid(row=0, column=0, sticky="ew", padx=12, pady=(0, 10))
        for column in range(3):
            panel.columnconfigure(column, weight=1)

        ttk.Label(
            panel,
            text="Best first demo: open the saved Showcase preset Baseline vs Fan Hot Stress.",
            style="FieldName.TLabel",
            wraplength=980,
            justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

        quick_paths = (
            ("Showcase demo", "Comparison Summary -> Showcase / Demo Presets -> Open Showcase Comparison"),
            ("Built-in comparison", "Comparison Summary -> choose left/right campaigns -> Run Built-In Comparison"),
            ("Saved results", "Comparison Summary -> Load Saved CSV as Left/Right"),
            ("Single custom fault", "Custom Experiment -> Single Fault -> Compare vs Baseline & Open Figures"),
            ("Multi-fault scenario", "Custom Experiment -> Multi-Fault Scenario -> Compare vs Baseline & Open Figures"),
            ("Batch trends", "Batch Results -> Load Batch Results -> choose a batch plot"),
        )
        for index, (title, guidance) in enumerate(quick_paths):
            row = 1 + index // 3
            column = index % 3
            card = tk.Frame(panel, bg="#ffffff", bd=1, relief="solid", highlightthickness=0)
            card.grid(row=row, column=column, sticky="nsew", padx=(0, 8 if column < 2 else 0), pady=4)
            tk.Label(
                card,
                text=title,
                bg="#ffffff",
                fg="#22313f",
                font=("TkDefaultFont", 9, "bold"),
                anchor="w",
                padx=10,
                pady=0,
            ).pack(fill="x", pady=(8, 2))
            tk.Label(
                card,
                text=guidance,
                bg="#ffffff",
                fg="#4d5c69",
                font=("TkDefaultFont", 9),
                justify="left",
                wraplength=315,
                anchor="w",
                padx=10,
                pady=8,
            ).pack(fill="x")

        session_actions = ttk.Frame(panel, style="Root.TFrame")
        session_actions.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        session_actions.columnconfigure(0, weight=1)

        ttk.Label(
            session_actions,
            text="Session continuity: save the current GUI state, restore it later, or auto-restore the last saved session on startup.",
            style="Hint.TLabel",
            wraplength=860,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        action_buttons = ttk.Frame(session_actions, style="Root.TFrame")
        action_buttons.grid(row=0, column=1, sticky="e", padx=(12, 0))
        ttk.Button(action_buttons, text="Save Session", command=self.save_session_state).grid(row=0, column=0, sticky="e")
        ttk.Button(action_buttons, text="Restore Session", command=self.restore_session_state).grid(row=0, column=1, sticky="e", padx=(8, 0))
        ttk.Checkbutton(
            action_buttons,
            text="Auto-Restore Last Session",
            variable=self.auto_restore_session,
            command=self._save_session_toggle_only,
        ).grid(row=0, column=2, sticky="e", padx=(10, 0))

    def _build_comparison_landing_panel(self, parent: ttk.Frame) -> None:
        outer = ttk.Frame(parent, padding=(12, 0, 12, 10), style="Root.TFrame")
        outer.grid(row=0, column=0, sticky="ew")
        outer.columnconfigure(0, weight=1)

        panel = tk.Frame(outer, bg="#ffffff", bd=1, relief="solid", highlightthickness=0)
        panel.grid(row=0, column=0, sticky="ew")
        panel.grid_columnconfigure(0, weight=1)

        tk.Label(
            panel,
            text="Start a Comparison",
            bg="#ffffff",
            fg="#1d3448",
            font=("TkDefaultFont", 12, "bold"),
            anchor="w",
            padx=16,
            pady=0,
        ).grid(row=0, column=0, sticky="ew", pady=(14, 2))

        tk.Label(
            panel,
            text="Choose the left and right campaigns below, then run the comparison or load saved CSV results into the two sides.",
            bg="#ffffff",
            fg="#4d5c69",
            font=("TkDefaultFont", 10),
            justify="left",
            wraplength=980,
            anchor="w",
            padx=16,
            pady=0,
        ).grid(row=1, column=0, sticky="ew", pady=(0, 12))

        steps = ttk.Frame(panel, style="Root.TFrame")
        steps.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        for column in range(3):
            steps.columnconfigure(column, weight=1)

        step_cards = (
            ("1", "Choose Left / Right", "Use the two campaign selectors just below."),
            ("2", "Run or Load", "Use the action buttons on the right to run or load results."),
            ("3", "Need a Demo Start?", "Open Saved Resources below for the showcase comparison."),
        )
        for index, (number, title, text) in enumerate(step_cards):
            card = tk.Frame(steps, bg="#f8fafc", bd=1, relief="solid", highlightthickness=0)
            card.grid(row=0, column=index, sticky="ew", padx=(0, 8 if index < 2 else 0))
            tk.Label(
                card,
                text=number,
                bg="#e8f0fb",
                fg="#1c4d8c",
                font=("TkDefaultFont", 9, "bold"),
                width=3,
                anchor="center",
                padx=0,
                pady=4,
            ).pack(anchor="w", padx=12, pady=(12, 6))
            tk.Label(
                card,
                text=title,
                bg="#f8fafc",
                fg="#22313f",
                font=("TkDefaultFont", 9, "bold"),
                anchor="w",
                justify="left",
                padx=12,
                pady=0,
            ).pack(fill="x")
            tk.Label(
                card,
                text=text,
                bg="#f8fafc",
                fg="#5a6977",
                font=("TkDefaultFont", 9),
                justify="left",
                wraplength=240,
                anchor="w",
                padx=12,
                pady=0,
            ).pack(fill="x", pady=(4, 12))

    def _toggle_summary_resources(self) -> None:
        self.summary_resources_expanded.set(not self.summary_resources_expanded.get())
        self._refresh_summary_resources_panel()

    def _refresh_summary_resources_panel(self) -> None:
        if getattr(self, "summary_resources_body", None) is None or getattr(self, "summary_resources_toggle_button", None) is None:
            return
        expanded = self.summary_resources_expanded.get()
        self.summary_resources_toggle_button.configure(text="Hide Saved Resources" if expanded else "Show Saved Resources")
        if expanded:
            self.summary_resources_body.grid()
        else:
            self.summary_resources_body.grid_remove()

    def _build_saved_resources_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Saved Resources / Demo Aids", padding=12)
        panel.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=0)

        ttk.Label(
            panel,
            text="Showcase presets, demo shortcuts, favorites, recent results, and session continuity live here when you need them.",
            style="Hint.TLabel",
            wraplength=860,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        self.summary_resources_toggle_button = ttk.Button(panel, text="Show Saved Resources", command=self._toggle_summary_resources)
        self.summary_resources_toggle_button.grid(row=0, column=1, sticky="e", padx=(10, 0))

        body = ttk.Frame(panel, style="Root.TFrame")
        body.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        body.columnconfigure(0, weight=1)
        self.summary_resources_body = body

        session_row = ttk.LabelFrame(body, text="Session Continuity", padding=10)
        session_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        session_row.columnconfigure(0, weight=1)
        ttk.Label(
            session_row,
            text="Save the current GUI state, restore it later, or auto-restore the last saved session on startup.",
            style="Hint.TLabel",
            wraplength=860,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        session_actions = ttk.Frame(session_row, style="Root.TFrame")
        session_actions.grid(row=0, column=1, sticky="e", padx=(12, 0))
        ttk.Button(session_actions, text="Save Session", command=self.save_session_state).grid(row=0, column=0, sticky="e")
        ttk.Button(session_actions, text="Restore Session", command=self.restore_session_state).grid(row=0, column=1, sticky="e", padx=(8, 0))
        ttk.Checkbutton(
            session_actions,
            text="Auto-Restore Last Session",
            variable=self.auto_restore_session,
            command=self._save_session_toggle_only,
        ).grid(row=0, column=2, sticky="e", padx=(10, 0))

        resources_grid = ttk.Frame(body, style="Root.TFrame")
        resources_grid.grid(row=1, column=0, sticky="ew")
        resources_grid.columnconfigure(0, weight=1)
        resources_grid.columnconfigure(1, weight=1)

        left_resources = ttk.Frame(resources_grid, style="Root.TFrame")
        left_resources.grid(row=0, column=0, sticky="new", padx=(0, 8))
        left_resources.columnconfigure(0, weight=1)
        self._build_showcase_presets(left_resources)
        self._build_recommended_demo_shortcuts(left_resources)

        right_resources = ttk.Frame(resources_grid, style="Root.TFrame")
        right_resources.grid(row=0, column=1, sticky="new", padx=(8, 0))
        right_resources.columnconfigure(0, weight=1)
        self._build_favorite_comparisons(right_resources)
        self._build_recent_results(right_resources)

        self._refresh_summary_resources_panel()

    def _build_recommended_demo_shortcuts(self, parent: ttk.Frame) -> None:
        shortcuts = ttk.LabelFrame(parent, text="Run Built-In Demo Comparisons", padding=12)
        shortcuts.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        shortcuts.columnconfigure(0, weight=1)
        shortcuts.columnconfigure(1, weight=1)
        shortcuts.columnconfigure(2, weight=1)

        ttk.Label(
            shortcuts,
            text="One click runs a built-in left/right comparison and opens the figure workflow. Use Showcase presets below when you prefer saved results with no rerun.",
            style="Hint.TLabel",
            wraplength=980,
            justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        for index, (label, left_campaign, right_campaign) in enumerate(self.RECOMMENDED_DEMO_COMPARISONS):
            ttk.Button(
                shortcuts,
                text=label,
                command=lambda left=left_campaign, right=right_campaign: self._run_demo_comparison(left, right),
            ).grid(row=1 + index // 3, column=index % 3, sticky="ew", padx=(0, 8 if index % 3 < 2 else 0), pady=4)

    def _build_showcase_presets(self, parent: ttk.Frame) -> None:
        showcase = ttk.LabelFrame(parent, text="Showcase / Demo Presets", padding=12)
        showcase.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        showcase.columnconfigure(0, weight=0)
        showcase.columnconfigure(1, weight=1)
        showcase.columnconfigure(2, weight=0)

        ttk.Label(
            showcase,
            text="Recommended first step for demos: choose Baseline vs Fan Hot Stress and open the saved comparison.",
            style="Hint.TLabel",
            wraplength=980,
            justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Label(showcase, text="Preset", style="FieldName.TLabel").grid(row=1, column=0, sticky="w")
        self.showcase_preset_selector = ttk.Combobox(
            showcase,
            textvariable=self.showcase_preset_choice,
            values=list(self.showcase_preset_catalog),
            state="readonly",
            width=42,
        )
        self.showcase_preset_selector.grid(row=1, column=1, sticky="ew", padx=(10, 10))
        self.showcase_preset_selector.bind("<<ComboboxSelected>>", self._on_showcase_preset_selected)
        ttk.Button(showcase, text="Open Showcase Comparison", command=self.load_selected_showcase_preset).grid(
            row=1, column=2, sticky="e"
        )
        ttk.Label(
            showcase,
            textvariable=self.showcase_description_var,
            style="Hint.TLabel",
            wraplength=980,
            justify="left",
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))

    def _build_favorite_comparisons(self, parent: ttk.Frame) -> None:
        favorites = ttk.LabelFrame(parent, text="Favorites / Pinned Comparisons", padding=12)
        favorites.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        favorites.columnconfigure(0, weight=1)
        favorites.columnconfigure(1, weight=1)
        favorites.columnconfigure(2, weight=1)

        ttk.Label(
            favorites,
            text="Keep stable thesis/demo comparison pairs here. Favorites are intentional saved pairs, separate from Recent Results.",
            style="Hint.TLabel",
            wraplength=980,
            justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        self.favorites_frame = ttk.Frame(favorites, style="Root.TFrame")
        self.favorites_frame.grid(row=1, column=0, columnspan=3, sticky="ew")
        for column in range(3):
            self.favorites_frame.columnconfigure(column, weight=1)

        ttk.Label(favorites, text="Saved Favorite", style="FieldName.TLabel").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.favorite_selector = ttk.Combobox(
            favorites,
            textvariable=self.favorite_choice,
            state="readonly",
            width=38,
        )
        self.favorite_selector.grid(row=2, column=1, sticky="ew", padx=(10, 10), pady=(10, 0))
        self.favorite_selector.bind("<<ComboboxSelected>>", self._on_favorite_selected)
        ttk.Button(favorites, text="Load Favorite", command=self.load_selected_favorite).grid(
            row=2, column=2, sticky="e", pady=(10, 0)
        )

        ttk.Label(favorites, text="Display Title", style="FieldName.TLabel").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(favorites, textvariable=self.favorite_title_var).grid(row=3, column=1, sticky="ew", padx=(10, 10), pady=(8, 0))
        ttk.Button(favorites, text="Pin Current Pair", command=self.add_current_comparison_to_favorites).grid(
            row=3, column=2, sticky="e", pady=(8, 0)
        )

        ttk.Label(favorites, text="Note / Context", style="FieldName.TLabel").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(favorites, textvariable=self.favorite_note_var).grid(row=4, column=1, sticky="ew", padx=(10, 10), pady=(8, 0))
        actions = ttk.Frame(favorites, style="Root.TFrame")
        actions.grid(row=4, column=2, sticky="e", pady=(8, 0))
        ttk.Button(actions, text="Save Edits", command=self.update_selected_favorite).grid(row=0, column=0, sticky="e")
        ttk.Button(actions, text="Remove Pin", command=self.remove_selected_favorite).grid(row=0, column=1, sticky="e", padx=(8, 0))

        self._refresh_favorites_panel()

    def _build_recent_results(self, parent: ttk.Frame) -> None:
        recent = ttk.LabelFrame(parent, text="Recent Results / Comparisons", padding=12)
        recent.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        recent.columnconfigure(0, weight=1)
        recent.columnconfigure(1, weight=0)

        ttk.Label(
            recent,
            text=f"Reload the last {MAX_RECENT_RESULTS} saved comparisons or custom runs without browsing for CSV files.",
            style="Hint.TLabel",
            wraplength=900,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(recent, text="Clear Recent History", command=self.clear_recent_results).grid(
            row=0, column=1, sticky="e", padx=(10, 0)
        )

        self.recent_results_frame = ttk.Frame(recent, style="Root.TFrame")
        self.recent_results_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        for column in range(3):
            self.recent_results_frame.columnconfigure(column, weight=1)
        self._refresh_recent_results_panel()

    def _build_context_column(
        self,
        parent: ttk.Frame,
        column: int,
        title: str,
        slot: str,
        accent: str,
    ) -> None:
        block = tk.Frame(parent, bg="#ffffff", bd=1, relief="solid", highlightthickness=0)
        block.grid(row=0, column=column, sticky="nsew", padx=(0, 8 if column == 0 else 0))
        block.grid_propagate(True)

        accent_bar = tk.Frame(block, bg=accent, width=12)
        accent_bar.pack(side="left", fill="y")

        body = tk.Frame(block, bg="#ffffff")
        body.pack(side="left", fill="both", expand=True, padx=(0, 2))
        body.columnconfigure(0, weight=1)

        tk.Label(
            body,
            text=title,
            bg="#ffffff",
            fg="#1d3448",
            font=("TkDefaultFont", 10, "bold"),
            anchor="w",
            padx=16,
            pady=0,
        ).grid(row=0, column=0, sticky="ew", pady=(16, 2))
        tk.Label(
            body,
            text="Hardware-Origin -> ECU Story",
            bg="#ffffff",
            fg="#6a7a88",
            font=("TkDefaultFont", 9),
            anchor="w",
            padx=16,
            pady=0,
        ).grid(row=1, column=0, sticky="ew", pady=(0, 12))

        self._add_context_row(body, 2, "Fault Class", self.context_vars[slot]["Fault Class"], compact=True)
        self._add_context_row(body, 3, "Hardware Source", self.context_vars[slot]["Hardware Source"])
        self._add_context_row(body, 4, "ECU Manifestation", self.context_vars[slot]["ECU Manifestation"], is_last=True)

    def _add_context_row(
        self,
        parent: tk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        *,
        compact: bool = False,
        is_last: bool = False,
    ) -> None:
        card = tk.Frame(parent, bg="#f8fafc", bd=1, relief="solid", highlightthickness=0)
        card.grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 10 if not is_last else 14))
        card.columnconfigure(0, weight=1)

        tk.Label(
            card,
            text=label,
            bg="#f8fafc",
            fg="#566574",
            font=("TkDefaultFont", 9, "bold"),
            anchor="w",
            padx=12,
            pady=0,
        ).grid(row=0, column=0, sticky="ew", pady=(10, 2))
        tk.Label(
            card,
            textvariable=variable,
            bg="#f8fafc",
            fg="#374553",
            font=("TkDefaultFont", 10),
            wraplength=300 if compact else 312,
            justify="left",
            anchor="w",
            padx=12,
            pady=0,
        ).grid(row=1, column=0, sticky="ew", pady=(0, 10))

    def _add_metric_cell(self, parent: ttk.Frame, row: int, column: int, slot: str, metric_name: str) -> None:
        frame = tk.Frame(parent, bg="#eef3f7", bd=1, relief="solid", highlightthickness=0)
        frame.grid(row=row, column=column, sticky="ew", padx=(0, 8 if column == 1 else 0), pady=4)

        value = tk.Label(
            frame,
            textvariable=self.summary_vars[slot][metric_name],
            bg="#eef3f7",
            fg="#1f2e3b",
            font=("TkDefaultFont", 10, "bold"),
            anchor="w",
            justify="left",
            wraplength=235,
            padx=10,
            pady=8,
        )
        value.pack(fill="x")

        self.metric_cells[slot][metric_name] = {"frame": frame, "value": value}

    def _on_campaign_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._refresh_campaign_context()
        self._reset_summary_values()
        self._refresh_fault_path_diagrams()
        self.status_text.set("Campaign selection changed. Click Run Built-In Comparison to update the views.")

    def _on_custom_fault_type_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self.custom_parameter.set(CUSTOM_DEFAULT_PARAMETERS.get(self.custom_fault_type.get(), "0.0"))

    def _on_custom_fault_behavior_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if self.custom_fault_behavior.get() == "permanent":
            self.custom_duration_ms.set("0")
        elif self.custom_duration_ms.get().strip() == "0":
            self.custom_duration_ms.set("10000")

    def _on_multi_fault_type_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self.multi_parameter.set(CUSTOM_DEFAULT_PARAMETERS.get(self.multi_fault_type.get(), "0.0"))

    def _on_multi_fault_behavior_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if self.multi_fault_behavior.get() == "permanent":
            self.multi_duration_ms.set("0")
        elif self.multi_duration_ms.get().strip() == "0":
            self.multi_duration_ms.set("10000")

    def _on_multi_event_selected(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        index = self._selected_multi_event_index()
        if index is None:
            return
        self._set_multi_editor_event(self.multi_events[index])

    def _on_showcase_preset_selected(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._update_showcase_description()

    def _on_favorite_selected(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._sync_selected_favorite_fields()

    def _apply_demo_comparison(self, left_campaign: str, right_campaign: str) -> None:
        self.left_campaign.set(left_campaign)
        self.right_campaign.set(right_campaign)
        self._refresh_campaign_context()
        self._reset_summary_values()
        self._refresh_fault_path_diagrams()
        self.status_text.set(f"Selected built-in pair: {left_campaign} vs {right_campaign}. Click Run Built-In Comparison.")

    def _run_demo_comparison(self, left_campaign: str, right_campaign: str) -> None:
        self._apply_demo_comparison(left_campaign, right_campaign)
        self.status_text.set(f"Running built-in demo comparison: {left_campaign} vs {right_campaign}...")
        self.run_comparison()

    def _on_presentation_mode_toggled(self) -> None:
        self._apply_presentation_mode()

    def _metric_font(self, metric_name: str) -> Tuple[str, int, str]:
        if metric_name in {"Campaign Name", "Fault Class"}:
            return ("TkDefaultFont", 10, "bold")
        if metric_name in self.EMPHASIZED_METRICS:
            return ("TkDefaultFont", 11, "bold")
        return ("TkDefaultFont", 10, "bold")

    def _metric_wraplength(self, metric_name: str) -> int:
        if metric_name in self.EMPHASIZED_METRICS:
            return 250
        return 235

    def _metric_padding(self, metric_name: str) -> Tuple[int, int]:
        if metric_name in self.EMPHASIZED_METRICS:
            return (12, 11)
        return (10, 8)

    def _metric_cell_colors(self, metric_name: str, value: str) -> Tuple[str, str]:
        if metric_name in {"Campaign Name", "Fault Class"}:
            return ("#eef3f7", "#1f2e3b")
        return metric_card_colors(metric_name, value)

    def _apply_presentation_mode(self) -> None:
        if self.comparison_plot is not None:
            self.comparison_plot.set_presentation_mode(self.presentation_mode.get())
        self._refresh_selected_plot()

    def _on_plot_selection_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._refresh_selected_plot()

    def _on_batch_plot_selection_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._refresh_batch_plot()

    def _update_comparison_plot_help(self) -> None:
        selected_plot = self.comparison_plot_choice.get()

        default_help = {
            "Coolant Temperature Comparison": "Use this figure for the high-level thermal trajectory comparison and threshold crossing story.",
            "Safe-State Comparison": "Use this figure to show protection-state escalation timing and end-state severity across campaigns.",
            "Fan Command / Actual Comparison": "Use this figure when permanent actuation faults are present and you want a direct command-versus-realization view.",
            "Cross-Layer Propagation Timeline": "Use this figure to read top-to-bottom from hardware-origin fault to ECU manifestation, diagnostic effect, and safe-state/system effect.",
        }

        if selected_plot != "Cross-Layer Propagation Timeline" or self.current_plot_results is None:
            self.comparison_plot_help_var.set(default_help.get(selected_plot, "Select a comparison plot to inspect the current runs."))
            return

        left_result = self.current_plot_results["left"]  # type: ignore[index]
        right_result = self.current_plot_results["right"]  # type: ignore[index]
        left_report = build_propagation_report(left_result["raw_rows"])  # type: ignore[index]
        left_text = f"Left: {left_report['story']['headline']}"  # type: ignore[index]

        if right_result is None:
            self.comparison_plot_help_var.set(
                "Propagation view: read the chain top-to-bottom as hardware-origin fault -> ECU manifestation -> diagnostic effect -> safe-state/system effect.\n"
                + left_text
            )
            return

        right_report = build_propagation_report(right_result["raw_rows"])  # type: ignore[index]
        right_text = f"Right: {right_report['story']['headline']}"  # type: ignore[index]
        self.comparison_plot_help_var.set(
            "Propagation view: read the chain top-to-bottom as hardware-origin fault -> ECU manifestation -> diagnostic effect -> safe-state/system effect.\n"
            f"{left_text}\n{right_text}"
        )

    def browse_batch_results(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select Batch Aggregate Summary CSV",
            initialdir=str(DEFAULT_BATCH_AGGREGATE_CSV.parent if DEFAULT_BATCH_AGGREGATE_CSV.parent.exists() else PROJECT_ROOT),
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if selected:
            self.batch_csv_path.set(selected)

    def _clear_propagation_evidence(self) -> None:
        if self.propagation_evidence_table is None:
            return

        for item_id in self.propagation_evidence_table.get_children():
            self.propagation_evidence_table.delete(item_id)

        self.propagation_evidence_table.insert(
            "",
            "end",
            values=(
                "-",
                "Run comparison",
                "n/a",
                "-",
                "Run a campaign comparison to populate propagation evidence.",
            ),
            tags=("evidence_empty",),
        )

    def _set_propagation_evidence_rows(self, rows: Sequence[Dict[str, str]]) -> None:
        if self.propagation_evidence_table is None:
            return

        for item_id in self.propagation_evidence_table.get_children():
            self.propagation_evidence_table.delete(item_id)

        for row in rows:
            stage = row["stage"]
            self.propagation_evidence_table.insert(
                "",
                "end",
                values=(
                    row["run"],
                    EVIDENCE_STAGE_DISPLAY.get(stage, stage),
                    row["time"],
                    wrap_evidence_text(row["signal"], width=28, max_lines=2),
                    wrap_evidence_text(row["explanation"], width=76, max_lines=2),
                ),
                tags=(EVIDENCE_STAGE_TAGS.get(stage, "evidence_empty"),),
            )

    def _update_propagation_evidence(
        self,
        left_result: Dict[str, object],
        right_result: Dict[str, object] | None,
    ) -> None:
        left_rows = left_result["raw_rows"]  # type: ignore[assignment]
        left_label = self.summary_vars["left"]["Campaign Name"].get()
        reports = [(left_label, build_propagation_report(left_rows))]

        if right_result is not None:
            right_rows = right_result["raw_rows"]  # type: ignore[assignment]
            right_label = self.summary_vars["right"]["Campaign Name"].get()
            reports.append((right_label, build_propagation_report(right_rows)))

        evidence_rows: List[Dict[str, str]] = []
        for label, report in reports:
            evidence_rows.extend(propagation_evidence_rows(label, report))

        self._set_propagation_evidence_rows(evidence_rows)

    def load_batch_results(self) -> None:
        csv_path = Path(self.batch_csv_path.get()).expanduser()
        try:
            rows = read_csv_rows(csv_path)
        except FileNotFoundError:
            self._clear_batch_results()
            self.batch_status_text.set(f"Batch aggregate CSV not found: {csv_path}")
            return
        except (OSError, csv.Error) as exc:
            self._clear_batch_results()
            self.batch_status_text.set(f"Failed to load batch aggregate CSV: {exc}")
            return

        if not rows:
            self._clear_batch_results()
            self.batch_status_text.set(f"Batch aggregate CSV is empty: {csv_path}")
            return

        self._apply_batch_results(csv_path, rows)

    def _clear_batch_results(self) -> None:
        self.batch_rows = []
        self.batch_run_count_var.set("-")
        self.batch_fault_classes_var.set("-")
        self.batch_fault_types_var.set("-")
        self.batch_findings_var.set("Load the default aggregate CSV, or browse to another batch summary.")
        self.batch_interpretation_var.set("-")

        if self.batch_table is not None:
            for item_id in self.batch_table.get_children():
                self.batch_table.delete(item_id)

        if self.batch_plot is not None:
            self.batch_plot.set_title(self.batch_plot_choice.get())
            self.batch_plot.show_message("Load a batch aggregate CSV, then use the plot selector to inspect trends.")
        self._refresh_dashboard_state()

    def _apply_batch_results(self, csv_path: Path, rows: Sequence[Dict[str, str]]) -> None:
        self.batch_rows = list(rows)

        fault_classes = sorted({row["fault_class"] for row in rows if row.get("fault_class")})
        fault_types = self._ordered_fault_types(rows)
        self.batch_run_count_var.set(str(len(rows)))
        self.batch_fault_classes_var.set(", ".join(fault_classes) if fault_classes else "n/a")
        self.batch_fault_types_var.set(
            ", ".join(FAULT_TYPE_DISPLAY.get(fault_type, fault_type) for fault_type in fault_types) if fault_types else "n/a"
        )

        self._populate_batch_table(rows, fault_types)
        self.batch_status_text.set(f"Loaded {len(rows)} batch runs. Use the table and plot selector to inspect sweep-level trends.")
        self._update_batch_findings(rows)
        self._refresh_batch_plot()
        self._refresh_dashboard_state()

    def _ordered_fault_types(self, rows: Sequence[Dict[str, str]]) -> List[str]:
        present = {row["fault_type"] for row in rows if row.get("fault_type")}
        ordered = [fault_type for fault_type in FAULT_TYPE_ORDER if fault_type in present]
        extras = sorted(present - set(ordered))
        return ordered + extras

    def _populate_batch_table(self, rows: Sequence[Dict[str, str]], fault_types: Sequence[str]) -> None:
        if self.batch_table is None:
            return

        for item_id in self.batch_table.get_children():
            self.batch_table.delete(item_id)

        for fault_type in fault_types:
            type_rows = [row for row in rows if row["fault_type"] == fault_type]
            detection_values = [
                value
                for value in (int_or_none(row.get("detection_latency_ms", "")) for row in type_rows)
                if value is not None
            ]
            safe_state_latency_values = [
                value
                for value in (int_or_none(row.get("safe_state_latency_ms", "")) for row in type_rows)
                if value is not None
            ]
            max_temp_values = [
                value
                for value in (float_or_none(row.get("max_coolant_temperature_c", "")) for row in type_rows)
                if value is not None
            ]
            safe_mode_values = [
                value
                for value in (int_or_none(row.get("safe_mode_duration_ms", "")) for row in type_rows)
                if value is not None
            ]
            dominant_state = mode_or_none(row.get("final_safe_state", "") for row in type_rows)

            self.batch_table.insert(
                "",
                "end",
                values=(
                    FAULT_TYPE_DISPLAY.get(fault_type, fault_type),
                    str(len(type_rows)),
                    self._format_batch_number(mean_or_none(detection_values), decimals=1),
                    self._format_batch_number(mean_or_none(safe_state_latency_values), decimals=1),
                    self._format_batch_number(mean_or_none(max_temp_values), decimals=2),
                    self._format_batch_number(mean_or_none(safe_mode_values), decimals=1),
                    safe_state_display_label(dominant_state),
                ),
            )

    def _refresh_batch_plot(self) -> None:
        if self.batch_plot is None:
            return

        self.batch_plot.set_title(self.batch_plot_choice.get())

        if not self.batch_rows:
            self.batch_plot.show_message("Load a batch aggregate CSV, then use the plot selector to inspect trends.")
            return

        fault_types = self._ordered_fault_types(self.batch_rows)
        self._update_batch_plot(self.batch_rows, fault_types)

    def _batch_metric_values(
        self,
        rows: Sequence[Dict[str, str]],
        fault_type: str,
        column: str,
    ) -> List[float]:
        values: List[float] = []

        for row in rows:
            if row["fault_type"] != fault_type:
                continue

            if column == "max_coolant_temperature_c":
                parsed = float_or_none(row.get(column, ""))
            else:
                parsed = int_or_none(row.get(column, ""))

            if parsed is not None:
                values.append(float(parsed))

        return values

    def _update_batch_plot(self, rows: Sequence[Dict[str, str]], fault_types: Sequence[str]) -> None:
        if self.batch_plot is None:
            return

        selected_plot = self.batch_plot_choice.get()
        categories: List[str] = []
        values: List[float | None] = []

        plot_definitions = {
            "Mean Detection Latency": (
                "detection_latency_ms",
                "Mean Detection [ms]",
                "#5077b8",
                False,
            ),
            "Mean Safe-State Latency": (
                "safe_state_latency_ms",
                "Mean Safe-State [ms]",
                "#7a6fd0",
                True,
            ),
            "Mean Maximum Coolant Temperature": (
                "max_coolant_temperature_c",
                "Mean Max Temp [C]",
                "#cf6c54",
                False,
            ),
            "Mean Safe-Mode Duration": (
                "safe_mode_duration_ms",
                "Mean Safe-Mode [ms]",
                "#4c9f92",
                True,
            ),
        }

        if selected_plot == "Final Safe-State Distribution":
            self._update_batch_safe_state_distribution(rows, fault_types)
            return

        if selected_plot not in plot_definitions:
            self.batch_plot.show_message("Unknown batch plot selection.")
            return

        column, y_label, bar_color, skip_baseline_without_values = plot_definitions[selected_plot]

        for fault_type in fault_types:
            metric_values = self._batch_metric_values(rows, fault_type, column)
            mean_value = mean_or_none(metric_values)
            if fault_type == "none" and mean_value is None and skip_baseline_without_values:
                continue
            categories.append(FAULT_TYPE_DISPLAY.get(fault_type, fault_type))
            values.append(mean_value)

        if not categories:
            self.batch_plot.show_message(f"No valid values were found for {selected_plot.lower()} in this aggregate summary.")
            return

        self.batch_plot.plot_bars(
            categories,
            values,
            y_label=y_label,
            bar_color=bar_color,
        )

    def _update_batch_safe_state_distribution(
        self,
        rows: Sequence[Dict[str, str]],
        fault_types: Sequence[str],
    ) -> None:
        if self.batch_plot is None:
            return

        categories: List[str] = []
        present_states = {
            normalize_safe_state_label(row.get("final_safe_state", "unknown"))
            for row in rows
            if row.get("final_safe_state")
        }
        state_order = [state for state in SAFE_STATE_DISPLAY_ORDER if state in present_states]
        extra_states = sorted(state for state in present_states if state not in SAFE_STATE_DISPLAY_ORDER)
        if not state_order and not extra_states:
            state_order = ["unknown"]
        ordered_states = [*state_order, *extra_states]
        stacks = {state: [] for state in ordered_states}

        for fault_type in fault_types:
            type_rows = [row for row in rows if row["fault_type"] == fault_type]
            if not type_rows:
                continue

            categories.append(FAULT_TYPE_DISPLAY.get(fault_type, fault_type))
            total_runs = float(len(type_rows))
            normalized_states = [normalize_safe_state_label(row.get("final_safe_state", "unknown")) for row in type_rows]
            for state in ordered_states:
                count = sum(1 for normalized_state in normalized_states if normalized_state == state)
                stacks[state].append((100.0 * count) / total_runs)

        if not categories:
            self.batch_plot.show_message("No final safe-state data was found in this aggregate summary.")
            return

        self.batch_plot.plot_stacked_bars(
            categories,
            [
                (
                    safe_state_display_label(state),
                    self.BATCH_SAFE_STATE_COLORS.get(state, self.BATCH_SAFE_STATE_COLORS["unknown"]),
                    stacks[state],
                )
                for state in ordered_states
            ],
            y_label="Outcome Share [%]",
            max_value=100.0,
        )

    def _format_batch_number(self, value: float | None, decimals: int = 1) -> str:
        if value is None:
            return "n/a"
        return f"{value:.{decimals}f}"

    def _refresh_campaign_context(self) -> None:
        for slot, campaign_var, description_var in (
            ("left", self.left_campaign, self.left_description_var),
            ("right", self.right_campaign, self.right_description_var),
        ):
            story = campaign_story(campaign_var.get())
            description_var.set(story["description"])
            self.summary_vars[slot]["Campaign Name"].set(story["campaign_name"])
            self.summary_vars[slot]["Fault Class"].set(story["fault_class"])
            self.context_vars[slot]["Fault Class"].set(story["fault_class"])
            self.context_vars[slot]["Hardware Source"].set(story["hardware_source"])
            self.context_vars[slot]["ECU Manifestation"].set(story["ecu_manifestation"])

    def _refresh_fault_path_diagrams(self) -> None:
        if self.left_fault_path_diagram is not None:
            left_rows = None
            left_summary = None
            if self.current_plot_results is not None:
                left_rows = self.current_plot_results["left"]["raw_rows"]  # type: ignore[index]
                left_summary = self.current_plot_results["left"]["summary_row"]  # type: ignore[index]
            self.left_fault_path_diagram.set_campaign(
                self.left_campaign.get() if left_rows is None else str(self.current_plot_results["left"]["campaign_id"]),  # type: ignore[index]
                None if left_rows is None else left_rows[0],
                None if left_summary is None else left_summary,
            )
        if self.right_fault_path_diagram is not None:
            right_rows = None
            right_summary = None
            right_campaign_id = self.right_campaign.get()
            if self.current_plot_results is not None and self.current_plot_results["right"] is not None:
                right_rows = self.current_plot_results["right"]["raw_rows"]  # type: ignore[index]
                right_summary = self.current_plot_results["right"]["summary_row"]  # type: ignore[index]
                right_campaign_id = str(self.current_plot_results["right"]["campaign_id"])  # type: ignore[index]
            self.right_fault_path_diagram.set_campaign(
                right_campaign_id,
                None if right_rows is None else right_rows[0],
                None if right_summary is None else right_summary,
            )

    def _reset_summary_values(self) -> None:
        self.current_comparison = None
        self.current_plot_results = None
        self.loaded_result_slots = {"left": None, "right": None}
        self.snapshot_button.state(["disabled"])
        self.export_button.state(["disabled"])
        if self.presentation_bundle_button is not None:
            self.presentation_bundle_button.state(["disabled"])
        self.comparison_verdict_var.set("Run a comparison to generate a compact verdict.")
        self.comparison_takeaway_var.set("-")
        self.comparison_findings_var.set("Run a comparison to generate automatic findings.")
        self.comparison_interpretation_var.set("-")
        self._update_comparison_plot_help()
        for slot in ("left", "right"):
            for metric_name in self.METRIC_NAMES:
                self.summary_vars[slot][metric_name].set("-")
        self._refresh_metric_cells()
        if self.comparison_plot is not None:
            self.comparison_plot.set_title(self.comparison_plot_choice.get())
            self.comparison_plot.show_message("Run a comparison from the Comparison Summary page to display the selected plot here.")
        self._clear_propagation_evidence()
        self._refresh_fault_path_diagrams()
        self._refresh_dashboard_state()

    def run_left_only(self) -> None:
        self._run_campaigns(include_right=False)

    def run_comparison(self) -> None:
        self._run_campaigns(include_right=True)

    def load_existing_as_left(self) -> None:
        self._load_existing_result_into_slot("left")

    def load_existing_as_right(self) -> None:
        self._load_existing_result_into_slot("right")

    def load_selected_showcase_preset(self) -> None:
        preset = self._selected_showcase_preset()
        if preset is None:
            messagebox.showinfo("No Showcase Preset", "Select a showcase preset first.")
            return
        self._load_showcase_preset(preset)

    def load_selected_favorite(self) -> None:
        favorite = self._selected_favorite()
        if favorite is None:
            messagebox.showinfo("No Favorite Selected", "Select a favorite comparison first.")
            return
        self.load_favorite_comparison(favorite)

    def run_custom_only(self) -> None:
        self._run_custom_experiment("only")

    def load_custom_as_left(self) -> None:
        self._run_custom_experiment("left")

    def load_custom_as_right(self) -> None:
        self._run_custom_experiment("right")

    def compare_custom_vs_baseline(self) -> None:
        self._run_custom_experiment("baseline")

    def run_multi_only(self) -> None:
        self._run_multi_experiment("only")

    def load_multi_as_left(self) -> None:
        self._run_multi_experiment("left")

    def load_multi_as_right(self) -> None:
        self._run_multi_experiment("right")

    def compare_multi_vs_baseline(self) -> None:
        self._run_multi_experiment("baseline")

    def _validate_custom_config(self) -> Dict[str, object] | None:
        return self._validate_custom_event_values(
            fault_type=self.custom_fault_type.get().strip(),
            behavior=self.custom_fault_behavior.get().strip(),
            start_text=self.custom_start_ms.get(),
            duration_text=self.custom_duration_ms.get(),
            parameter_text=self.custom_parameter.get(),
            error_title="Invalid Custom Experiment",
        )

    def _validate_multi_scenario_config(self) -> Dict[str, object] | None:
        if len(self.multi_events) < 2:
            messagebox.showerror(
                "Invalid Multi-Fault Scenario",
                "Add at least two fault events before running a multi-fault scenario.",
            )
            return None

        if len(self.multi_events) > MAX_CUSTOM_SCENARIO_EVENTS:
            messagebox.showerror(
                "Invalid Multi-Fault Scenario",
                f"This lightweight builder supports at most {MAX_CUSTOM_SCENARIO_EVENTS} fault events.",
            )
            return None

        previous_start = -1
        normalized_events: List[Dict[str, object]] = []
        for index, event in enumerate(self.multi_events, start=1):
            validated = self._validate_custom_event_values(
                fault_type=str(event["fault_type"]),
                behavior=str(event["fault_behavior"]),
                start_text=str(event["start_ms"]),
                duration_text=str(event["duration_ms"]),
                parameter_text=str(event["parameter"]),
                error_title=f"Invalid Multi-Fault Scenario Event {index}",
            )
            if validated is None:
                return None

            start_ms = int(validated["start_ms"])
            if start_ms < previous_start:
                messagebox.showerror(
                    "Invalid Multi-Fault Scenario",
                    "Keep event start times in non-decreasing order so the ordered scenario remains easy to explain.",
                )
                return None

            previous_start = start_ms
            normalized_events.append(validated)

        return {
            "kind": "multi",
            "events": normalized_events,
        }

    def _run_custom_experiment(self, mode: str) -> None:
        config = self._validate_custom_config()
        if config is None:
            return
        self._run_custom_request(mode, config)

    def _run_multi_experiment(self, mode: str) -> None:
        config = self._validate_multi_scenario_config()
        if config is None:
            return
        self._run_custom_request(mode, config)

    def _run_custom_request(self, mode: str, config: Dict[str, object]) -> None:
        if self.executable is None:
            messagebox.showerror(
                "Executable Not Found",
                "The compiled virtual ECU executable was not found. Build it first with 'make'.",
            )
            return

        CUSTOM_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        run_noun = "custom multi-fault scenario" if str(config.get("kind", "single")) == "multi" else "custom experiment"
        mode_text = {
            "only": f"Running {run_noun}...",
            "left": f"Running {run_noun} as left vs {self.right_campaign.get()}...",
            "right": f"Running {run_noun} as right vs {self.left_campaign.get()}...",
            "baseline": f"Running {run_noun} vs baseline...",
        }.get(mode, f"Running {run_noun}...")
        self.status_text.set(mode_text)
        self.custom_status_text.set(
            f"Executing {custom_campaign_label(config)} via the simulator custom CLI path and loading the generated CSV outputs."
        )
        self.run_compare_button.state(["disabled"])
        self.run_left_button.state(["disabled"])
        self.snapshot_button.state(["disabled"])
        self.export_button.state(["disabled"])
        if self.presentation_bundle_button is not None:
            self.presentation_bundle_button.state(["disabled"])
        self._set_custom_controls_enabled(False)

        worker = threading.Thread(
            target=self._run_custom_experiment_worker,
            args=(mode, config),
            daemon=True,
        )
        worker.start()

    def _run_campaigns(self, include_right: bool) -> None:
        if self.executable is None:
            messagebox.showerror(
                "Executable Not Found",
                "The compiled virtual ECU executable was not found. Build it first with 'make'.",
            )
            return

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        left_campaign = self.left_campaign.get()
        right_campaign = self.right_campaign.get()
        left_name = campaign_story(left_campaign)["campaign_name"]
        right_name = campaign_story(right_campaign)["campaign_name"]
        self.status_text.set(
            f"Running built-in comparison: {left_name} vs {right_name}..."
            if include_right else f"Running selected left campaign: {left_name}..."
        )
        self.run_compare_button.state(["disabled"])
        self.run_left_button.state(["disabled"])
        self.snapshot_button.state(["disabled"])
        self.export_button.state(["disabled"])
        if self.presentation_bundle_button is not None:
            self.presentation_bundle_button.state(["disabled"])
        self._set_custom_controls_enabled(False)

        worker = threading.Thread(
            target=self._run_campaigns_worker,
            args=(include_right,),
            daemon=True,
        )
        worker.start()

    def _load_simulation_result(self, campaign_id: str, log_path: Path) -> Dict[str, object]:
        summary_path = summary_path_for(log_path)
        raw_rows = read_csv_rows(log_path)
        summary_rows = read_csv_rows(summary_path)
        validate_result_pair(raw_rows, summary_rows, raw_path=log_path, summary_path=summary_path)

        return {
            "campaign_id": campaign_id,
            "raw_rows": raw_rows,
            "summary_row": summary_rows[0],
            "log_path": log_path,
            "summary_path": summary_path,
        }

    def _run_single_campaign(self, campaign_id: str, slot: str) -> Dict[str, object]:
        log_path = campaign_log_path(campaign_id, slot)
        command = [str(self.executable), str(log_path), campaign_id]

        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout or "Unknown simulator failure.")

        return self._load_simulation_result(campaign_id, log_path)

    def _choose_existing_result_path(self) -> Path | None:
        selected = filedialog.askopenfilename(
            title="Select an existing virtual ECU raw CSV log",
            initialdir=str(LOGS_DIR if LOGS_DIR.exists() else PROJECT_ROOT),
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not selected:
            return None
        return Path(selected)

    def _load_existing_result_from_path(self, selected_path: Path) -> Dict[str, object]:
        return load_existing_result_pair(selected_path)

    def _load_existing_result_into_slot(self, slot: str) -> None:
        selected_path = self._choose_existing_result_path()
        if selected_path is None:
            return

        try:
            result = self._load_existing_result_from_path(selected_path)
        except (OSError, RuntimeError, csv.Error) as exc:
            self.status_text.set("Existing result load failed.")
            messagebox.showerror("Load Existing Results Failed", str(exc))
            return

        self._apply_existing_result(slot, result)

    def _load_showcase_preset(self, preset: Dict[str, str]) -> None:
        try:
            left_result, right_result = load_showcase_preset_results(preset)
        except (OSError, RuntimeError, csv.Error) as exc:
            self.status_text.set("Showcase preset load failed.")
            messagebox.showerror("Showcase Preset Load Failed", str(exc))
            return

        self._apply_results(
            left_result,
            right_result,
            remember_recent=False,
        )
        self._remember_results(
            left_result,
            right_result,
            kind="showcase",
            title=preset["title"],
            description=preset["description"],
        )
        self._open_comparison_figures_tab()
        self.showcase_description_var.set(preset["description"])
        self.status_text.set(f"Loaded showcase preset: {preset['title']}. Comparison Figures are ready.")

    def _run_custom_campaign(self, config: Dict[str, object]) -> Dict[str, object]:
        log_path = custom_log_path(config)
        if str(config.get("kind", "single")) == "multi":
            command = [str(self.executable), str(log_path), "custom_multi", str(len(custom_events(config)))]
            for event in custom_events(config):
                command.extend(
                    [
                        str(event["fault_type"]),
                        str(event["start_ms"]),
                        str(event["duration_ms"]),
                        str(event["fault_behavior"]),
                        f"{float(event['parameter']):g}",
                    ]
                )
        else:
            command = [
                str(self.executable),
                str(log_path),
                "custom",
                str(config["fault_type"]),
                str(config["start_ms"]),
                str(config["duration_ms"]),
                str(config["fault_behavior"]),
                f"{float(config['parameter']):g}",
            ]

        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout or "Unknown simulator failure.")

        result = self._load_simulation_result(custom_campaign_id(config), log_path)
        summary = dict(result["summary_row"])  # type: ignore[arg-type]
        summary["campaign_label"] = custom_campaign_label(config)
        result["summary_row"] = summary
        result["custom_config"] = dict(config)
        return result

    def _run_campaigns_worker(self, include_right: bool) -> None:
        try:
            left_result = self._run_single_campaign(self.left_campaign.get(), "left")
            right_result = self._run_single_campaign(self.right_campaign.get(), "right") if include_right else None
        except OSError as exc:
            message = f"Failed to run simulator: {exc}"
            self.after(0, lambda msg=message: self._show_error(msg))
            return
        except (RuntimeError, csv.Error) as exc:
            message = str(exc)
            self.after(0, lambda msg=message: self._show_error(msg))
            return

        self.after(0, lambda: self._apply_results(left_result, right_result))

    def _run_custom_experiment_worker(self, mode: str, config: Dict[str, object]) -> None:
        try:
            custom_result = self._run_custom_campaign(config)
            left_campaign_id = self.left_campaign.get()
            right_campaign_id = self.right_campaign.get()
            item_label = "Custom scenario" if str(config.get("kind", "single")) == "multi" else "Custom run"

            if mode == "only":
                left_result = custom_result
                right_result = None
                loaded_slot = "Left slot only"
                loaded_mode = f"{item_label} loaded as Left and Comparison Figures opened."
                completion_status = f"{item_label} loaded as Left and Comparison Figures opened."
                custom_status = f"{item_label} loaded as Left and Comparison Figures opened for immediate plot review."
            elif mode == "left":
                left_result = custom_result
                right_result = self._run_single_campaign(right_campaign_id, "right")
                right_name = campaign_story(right_campaign_id)["campaign_name"]
                loaded_slot = f"Left slot vs {right_name}"
                loaded_mode = f"{item_label} loaded as Left and Comparison Figures opened."
                completion_status = f"{item_label} loaded as Left and Comparison Figures opened."
                custom_status = (
                    f"{item_label} loaded as Left, compared against {right_name}, "
                    "and Comparison Figures opened."
                )
            elif mode == "right":
                left_result = self._run_single_campaign(left_campaign_id, "left")
                right_result = custom_result
                left_name = campaign_story(left_campaign_id)["campaign_name"]
                loaded_slot = f"Right slot vs {left_name}"
                loaded_mode = f"{item_label} loaded as Right and Comparison Figures opened."
                completion_status = f"{item_label} loaded as Right and Comparison Figures opened."
                custom_status = (
                    f"{item_label} loaded as Right, compared against {left_name}, "
                    "and Comparison Figures opened."
                )
            else:
                left_result = custom_result
                right_result = self._run_single_campaign("baseline", "right")
                loaded_slot = "Left slot vs Baseline"
                loaded_mode = f"{item_label} compared against Baseline and Comparison Figures opened."
                completion_status = f"{item_label} compared against Baseline and Comparison Figures opened."
                custom_status = f"{item_label} compared against Baseline and Comparison Figures opened."
        except OSError as exc:
            message = f"Failed to run simulator: {exc}"
            self.after(0, lambda msg=message: self._show_error(msg))
            return
        except (RuntimeError, csv.Error) as exc:
            message = str(exc)
            self.after(0, lambda msg=message: self._show_error(msg))
            return

        self.after(
            0,
            lambda: self._apply_custom_results(
                custom_result,
                loaded_mode,
                loaded_slot,
                completion_status,
                custom_status,
                left_result,
                right_result,
            ),
        )

    def _show_error(self, message: str) -> None:
        self.status_text.set("Run failed.")
        self.custom_status_text.set("Custom experiment run failed.")
        self.run_compare_button.state(["!disabled"])
        self.run_left_button.state(["!disabled"])
        self.snapshot_button.state(["disabled"])
        self.export_button.state(["disabled"])
        if self.presentation_bundle_button is not None:
            self.presentation_bundle_button.state(["disabled"])
        self._set_custom_controls_enabled(True)
        messagebox.showerror("Virtual ECU Run Failed", message)

    def _apply_existing_result(self, slot: str, result: Dict[str, object]) -> None:
        slot_label = "Left" if slot == "left" else "Right"
        self.loaded_result_slots[slot] = result
        left_result = self.loaded_result_slots["left"]
        right_result = self.loaded_result_slots["right"]

        if left_result is not None:
            self._apply_results(
                left_result,
                right_result,
                recent_kind="saved",
                recent_description="Saved CSV result loaded through the GUI.",
            )
            loaded_name = self.summary_vars[slot]["Campaign Name"].get()
            if right_result is not None:
                self.status_text.set(f"Loaded existing result as {slot_label}: {loaded_name}. Comparison is ready.")
            else:
                self.status_text.set(f"Loaded existing result as {slot_label}: {loaded_name}. Load a right result to compare.")
            self._open_comparison_figures_tab()
            return

        self.run_compare_button.state(["!disabled"])
        self.run_left_button.state(["!disabled"])
        self._set_custom_controls_enabled(True)
        self._clear_slot("left")
        self._apply_summary_slot("right", str(result["campaign_id"]), result["raw_rows"], result["summary_row"])
        self.current_comparison = None
        self.current_plot_results = None
        self.snapshot_button.state(["disabled"])
        self.export_button.state(["disabled"])
        if self.presentation_bundle_button is not None:
            self.presentation_bundle_button.state(["disabled"])
        if self.left_fault_path_diagram is not None:
            self.left_fault_path_diagram.set_campaign(self.left_campaign.get(), None, None)
        if self.right_fault_path_diagram is not None:
            right_rows = result["raw_rows"]  # type: ignore[assignment]
            self.right_fault_path_diagram.set_campaign(str(result["campaign_id"]), right_rows[0], result["summary_row"])  # type: ignore[arg-type]
        self._refresh_metric_cells()
        self.comparison_verdict_var.set("Load or run a left result to enable the comparison verdict.")
        self.comparison_takeaway_var.set("-")
        self.comparison_findings_var.set("Load or run a left result to enable left-versus-right findings.")
        self.comparison_interpretation_var.set("-")
        self._clear_propagation_evidence()
        if self.comparison_plot is not None:
            self.comparison_plot.show_message("Loaded an existing right result. Load or run a left result to display comparison figures.")
        loaded_name = self.summary_vars["right"]["Campaign Name"].get()
        self.status_text.set(f"Loaded existing result as Right: {loaded_name}. Load a left result to compare.")
        self._refresh_dashboard_state()

    def _apply_custom_results(
        self,
        custom_result: Dict[str, object],
        loaded_mode: str,
        loaded_slot: str,
        completion_status: str,
        custom_status: str,
        left_result: Dict[str, object],
        right_result: Dict[str, object] | None,
    ) -> None:
        self._update_custom_result_summary(custom_result, loaded_mode, loaded_slot)
        self._apply_results(left_result, right_result, remember_recent=False)
        self._remember_results(
            left_result,
            right_result,
            kind="custom",
            title=self.custom_summary_vars["Campaign Name"].get()
            if right_result is None
            else f"{self.custom_summary_vars['Campaign Name'].get()} comparison",
            description="Custom experiment or scenario run from the GUI.",
        )
        self._open_comparison_figures_tab()
        self.status_text.set(completion_status)
        self.custom_status_text.set(
            f"{custom_status} Saved files: {Path(custom_result['log_path']).relative_to(PROJECT_ROOT)} and "
            f"{Path(custom_result['summary_path']).relative_to(PROJECT_ROOT)}."
        )

    def _apply_results(
        self,
        left_result: Dict[str, object],
        right_result: Dict[str, object] | None,
        *,
        remember_recent: bool = True,
        recent_kind: str = "comparison",
        recent_title: str | None = None,
        recent_description: str = "",
    ) -> None:
        self.run_compare_button.state(["!disabled"])
        self.run_left_button.state(["!disabled"])
        self._set_custom_controls_enabled(True)
        self.loaded_result_slots["left"] = left_result
        self.loaded_result_slots["right"] = right_result

        left_campaign = str(left_result["campaign_id"])
        self._apply_summary_slot("left", left_campaign, left_result["raw_rows"], left_result["summary_row"])
        left_label = self.summary_vars["left"]["Campaign Name"].get()

        if right_result is not None:
            right_campaign = str(right_result["campaign_id"])
            self._apply_summary_slot("right", right_campaign, right_result["raw_rows"], right_result["summary_row"])
            right_label = self.summary_vars["right"]["Campaign Name"].get()
            self.status_text.set(f"Loaded comparison: {left_label} vs {right_label}.")
            self.current_comparison = {
                "left": left_result,
                "right": right_result,
            }
            self.snapshot_button.state(["!disabled"])
            self.export_button.state(["!disabled"])
            if self.presentation_bundle_button is not None:
                self.presentation_bundle_button.state(["!disabled"])
        else:
            self._clear_slot("right")
            self.status_text.set(f"Loaded left campaign: {left_label}.")
            self.current_comparison = None
            self.snapshot_button.state(["disabled"])
            self.export_button.state(["disabled"])
            if self.presentation_bundle_button is not None:
                self.presentation_bundle_button.state(["disabled"])

        self.current_plot_results = {
            "left": left_result,
            "right": right_result,
        }
        self._prefill_favorite_editor()
        self._refresh_fault_path_diagrams()
        self._refresh_metric_cells()
        self._update_comparison_findings(left_result, right_result)
        self._update_propagation_evidence(left_result, right_result)
        self._refresh_selected_plot()
        self._refresh_dashboard_state()
        if remember_recent:
            self._remember_results(
                left_result,
                right_result,
                kind=recent_kind,
                title=recent_title,
                description=recent_description,
            )

    def _update_comparison_findings(
        self,
        left_result: Dict[str, object],
        right_result: Dict[str, object] | None,
    ) -> None:
        if right_result is None:
            self.comparison_verdict_var.set("Verdict becomes available after a left-versus-right comparison run.")
            self.comparison_takeaway_var.set("-")
            self.comparison_findings_var.set("Findings become available after a left-versus-right comparison run.")
            self.comparison_interpretation_var.set("-")
            return

        left_name = self.summary_vars["left"]["Campaign Name"].get()
        right_name = self.summary_vars["right"]["Campaign Name"].get()
        left_summary = left_result["summary_row"]  # type: ignore[assignment]
        right_summary = right_result["summary_row"]  # type: ignore[assignment]

        verdict_lines, takeaway_line = comparison_verdict(left_name, left_summary, right_name, right_summary)
        self.comparison_verdict_var.set("\n".join(f"- {line}" for line in verdict_lines))
        self.comparison_takeaway_var.set(takeaway_line)

        finding_lines, interpretation_lines = comparison_findings(left_name, left_summary, right_name, right_summary)
        self.comparison_findings_var.set("\n".join(f"- {line}" for line in finding_lines))
        self.comparison_interpretation_var.set("\n".join(interpretation_lines))

    def _update_batch_findings(self, rows: Sequence[Dict[str, str]]) -> None:
        finding_lines, interpretation_lines = batch_findings(rows)
        self.batch_findings_var.set("\n".join(f"- {line}" for line in finding_lines))
        self.batch_interpretation_var.set("\n".join(interpretation_lines))

    def _apply_summary_slot(
        self,
        slot: str,
        campaign_id: str,
        raw_rows: object,
        summary_row: object,
    ) -> None:
        rows = raw_rows  # type: ignore[assignment]
        summary = summary_row  # type: ignore[assignment]
        first_row = rows[0]
        story = story_for_run(campaign_id, first_row, str(summary.get("campaign_label", campaign_id)))

        self.summary_vars[slot]["Campaign Name"].set(story["campaign_name"])
        self.summary_vars[slot]["Fault Class"].set(summarize_fault_class(campaign_id, first_row))
        self.context_vars[slot]["Fault Class"].set(story["fault_class"])
        self.context_vars[slot]["Hardware Source"].set(story["hardware_source"])
        self.context_vars[slot]["ECU Manifestation"].set(story["ecu_manifestation"])
        self.summary_vars[slot]["Final DTC"].set(summary.get("final_primary_dtc_label", "none"))
        self.summary_vars[slot]["Final Safe State"].set(summary.get("final_safe_state_label", "normal"))
        self.summary_vars[slot]["Maximum Coolant Temperature"].set(
            format_temperature(summary.get("max_coolant_temp_c", ""))
        )
        self.summary_vars[slot]["Detection Latency"].set(
            format_latency(summary.get("detection_latency_ms", ""))
        )
        self.summary_vars[slot]["Safe-State Latency"].set(
            format_latency(summary.get("safe_state_latency_ms", ""))
        )

    def _clear_slot(self, slot: str) -> None:
        story = campaign_story(self.right_campaign.get() if slot == "right" else self.left_campaign.get())
        self.summary_vars[slot]["Campaign Name"].set(story["campaign_name"])
        self.summary_vars[slot]["Fault Class"].set(story["fault_class"])
        self.context_vars[slot]["Fault Class"].set(story["fault_class"])
        self.context_vars[slot]["Hardware Source"].set(story["hardware_source"])
        self.context_vars[slot]["ECU Manifestation"].set(story["ecu_manifestation"])
        for metric_name in self.METRIC_NAMES:
            self.summary_vars[slot][metric_name].set("-")

    def _refresh_metric_cells(self) -> None:
        for slot in ("left", "right"):
            for metric_name, cell in self.metric_cells[slot].items():
                background, foreground = self._metric_cell_colors(metric_name, self.summary_vars[slot][metric_name].get())
                cell = self.metric_cells[slot][metric_name]
                frame = cell["frame"]
                value = cell["value"]
                x_padding, y_padding = self._metric_padding(metric_name)
                frame.configure(bg=background)
                value.configure(
                    bg=background,
                    fg=foreground,
                    font=self._metric_font(metric_name),
                    wraplength=self._metric_wraplength(metric_name),
                    padx=x_padding,
                    pady=y_padding,
                )

    def _refresh_selected_plot(self) -> None:
        if self.comparison_plot is None:
            return

        selected_plot = self.comparison_plot_choice.get()
        self._update_comparison_plot_help()
        self.comparison_plot.set_title(selected_plot)

        if self.current_plot_results is None:
            self.comparison_plot.show_message("Run a comparison from the Comparison Summary page to display the selected plot here.")
            return

        left_result = self.current_plot_results["left"]  # type: ignore[index]
        right_result = self.current_plot_results["right"]  # type: ignore[index]
        self._update_plots(left_result, right_result, selected_plot)

    def _update_plots(
        self,
        left_result: Dict[str, object],
        right_result: Dict[str, object] | None,
        selected_plot: str,
    ) -> None:
        if self.comparison_plot is None:
            return

        left_rows = left_result["raw_rows"]  # type: ignore[assignment]
        left_label = self.summary_vars["left"]["Campaign Name"].get()
        right_rows = right_result["raw_rows"] if right_result is not None else None  # type: ignore[assignment]

        if selected_plot == "Coolant Temperature Comparison":
            coolant_series = [
                (
                    left_label,
                    LEFT_COLOR,
                    float_series(left_rows, "time_s"),
                    float_series(left_rows, "coolant_temp_true_c"),
                    LEFT_DASH,
                )
            ]

            if right_rows is not None:
                coolant_series.append(
                    (
                        self.summary_vars["right"]["Campaign Name"].get(),
                        RIGHT_COLOR,
                        float_series(right_rows, "time_s"),
                        float_series(right_rows, "coolant_temp_true_c"),
                        RIGHT_DASH,
                    )
                )

            self.comparison_plot.plot_lines(
                coolant_series,
                y_label="Temp [C]",
                threshold_lines=((108.0, "#8c6b2d", "Warning"), (115.0, "#7b4d57", "Critical")),
            )
            return

        if selected_plot == "Safe-State Comparison":
            safe_series = [
                (
                    left_label,
                    LEFT_COLOR,
                    float_series(left_rows, "time_s"),
                    int_series(left_rows, "safe_state_id"),
                    LEFT_DASH,
                )
            ]

            if right_rows is not None:
                safe_series.append(
                    (
                        self.summary_vars["right"]["Campaign Name"].get(),
                        RIGHT_COLOR,
                        float_series(right_rows, "time_s"),
                        int_series(right_rows, "safe_state_id"),
                        RIGHT_DASH,
                    )
                )

            self.comparison_plot.plot_step_comparison(
                safe_series,
                y_label="State",
                tick_labels=SAFE_STATE_LABELS,
            )
            return

        if selected_plot == "Cross-Layer Propagation Timeline":
            reports = [build_propagation_report(left_rows)]
            labels = [left_label]

            if right_rows is not None:
                reports.append(build_propagation_report(right_rows))
                labels.append(self.summary_vars["right"]["Campaign Name"].get())

            self.comparison_plot.plot_propagation_timeline(labels, reports)
            return

        fan_series = [
            (
                f"{left_label} command",
                LEFT_COLOR,
                float_series(left_rows, "time_s"),
                float_series(left_rows, "fan_command"),
                LEFT_DASH,
            ),
            (
                f"{left_label} actual",
                "#7d1f17",
                float_series(left_rows, "time_s"),
                float_series(left_rows, "fan_actual"),
                (2, 3),
            ),
        ]
        left_permanent = "permanent" in event_behaviors(left_rows[0])
        right_permanent = False

        if right_rows is not None:
            right_label = self.summary_vars["right"]["Campaign Name"].get()
            right_permanent = "permanent" in event_behaviors(right_rows[0])
            fan_series.extend(
                (
                    (
                        f"{right_label} command",
                        RIGHT_COLOR,
                        float_series(right_rows, "time_s"),
                        float_series(right_rows, "fan_command"),
                        RIGHT_DASH,
                    ),
                    (
                        f"{right_label} actual",
                        "#5e7fb0",
                        float_series(right_rows, "time_s"),
                        float_series(right_rows, "fan_actual"),
                        (8, 3, 2, 3),
                    ),
                )
            )

        if left_permanent or right_permanent:
            self.comparison_plot.plot_lines(
                fan_series,
                y_label="Fan [-]",
                y_min=0.0,
                y_max=1.0,
            )
        else:
            self.comparison_plot.show_message(
                "Fan Command / Actual Comparison is only meaningful for campaigns with a permanent-fault phase. Neither selected run contains one."
            )

    def export_current_comparison(self) -> None:
        if self.current_comparison is None:
            messagebox.showinfo(
                "No Comparison Loaded",
                "Run a left-versus-right comparison first, then export the current report.",
            )
            return

        left_result = self.current_comparison["left"]  # type: ignore[index]
        right_result = self.current_comparison["right"]  # type: ignore[index]
        left_campaign_id = str(left_result["campaign_id"])
        right_campaign_id = str(right_result["campaign_id"])
        export_dir = comparison_export_dir(left_campaign_id, right_campaign_id)
        generated_files = write_comparison_report_bundle(
            export_dir,
            left_campaign_id,
            right_campaign_id,
            self.summary_vars["left"]["Fault Class"].get(),
            self.summary_vars["right"]["Fault Class"].get(),
            self.METRIC_NAMES,
            self.summary_vars,
            self.summary_vars["left"]["Campaign Name"].get(),
            left_result["raw_rows"],  # type: ignore[index]
            self.summary_vars["right"]["Campaign Name"].get(),
            right_result["raw_rows"],  # type: ignore[index]
        )

        self.status_text.set(f"Exported comparison report to {export_dir}")
        messagebox.showinfo(
            "Comparison Exported",
            "Saved the comparison report, plots, and propagation bundle to:\n"
            f"{export_dir}\n\n"
            + "\n".join(path.name for path in generated_files),
        )

    def _current_snapshot_payload(self) -> Dict[str, object]:
        if self.current_comparison is None:
            raise RuntimeError("No comparison is currently loaded.")

        left_result = self.current_comparison["left"]  # type: ignore[index]
        right_result = self.current_comparison["right"]  # type: ignore[index]
        metrics = []
        for metric_name in self.SNAPSHOT_METRIC_NAMES:
            metrics.append(
                (
                    metric_name,
                    {
                        "left": self.summary_vars["left"][metric_name].get(),
                        "right": self.summary_vars["right"][metric_name].get(),
                    },
                )
            )

        finding_lines = [
            line[2:] if line.startswith("- ") else line
            for line in self.comparison_findings_var.get().splitlines()
            if line.strip()
        ]
        interpretation_lines = [line for line in self.comparison_interpretation_var.get().splitlines() if line.strip() and line.strip() != "-"]

        return {
            "left_campaign_id": str(left_result["campaign_id"]),
            "right_campaign_id": str(right_result["campaign_id"]),
            "left_campaign_name": self.summary_vars["left"]["Campaign Name"].get(),
            "right_campaign_name": self.summary_vars["right"]["Campaign Name"].get(),
            "left_fault_class": self.summary_vars["left"]["Fault Class"].get(),
            "right_fault_class": self.summary_vars["right"]["Fault Class"].get(),
            "metrics": metrics,
            "findings": finding_lines,
            "interpretation": interpretation_lines,
        }

    def _export_fault_path_snapshots(self, export_dir: Path) -> List[Path]:
        files: List[Path] = []
        if self.left_fault_path_diagram is not None:
            left_path = export_dir / "fault_path_reference.eps"
            exported = self.left_fault_path_diagram.export_canvas_snapshot(left_path)
            if exported is not None:
                files.append(exported)
        if self.right_fault_path_diagram is not None:
            right_path = export_dir / "fault_path_fault_case.eps"
            exported = self.right_fault_path_diagram.export_canvas_snapshot(right_path)
            if exported is not None:
                files.append(exported)
        return files

    def export_presentation_bundle(self) -> None:
        if self.current_comparison is None:
            messagebox.showinfo(
                "No Comparison Loaded",
                "Run a left-versus-right comparison first, then export the current presentation bundle.",
            )
            return

        left_result = self.current_comparison["left"]  # type: ignore[index]
        right_result = self.current_comparison["right"]  # type: ignore[index]
        left_campaign_id = str(left_result["campaign_id"])
        right_campaign_id = str(right_result["campaign_id"])
        export_dir = presentation_bundle_dir(left_campaign_id, right_campaign_id)
        export_dir.mkdir(parents=True, exist_ok=True)

        snapshot = self._current_snapshot_payload()
        left_name = self.summary_vars["left"]["Campaign Name"].get()
        right_name = self.summary_vars["right"]["Campaign Name"].get()
        verdict_lines, takeaway_line = comparison_verdict(left_name, left_result["summary_row"], right_name, right_result["summary_row"])  # type: ignore[index]
        findings_lines = list(snapshot["findings"])  # type: ignore[arg-type]
        interpretation_lines = list(snapshot["interpretation"])  # type: ignore[arg-type]

        generated_files = write_comparison_report_bundle(
            export_dir,
            left_campaign_id,
            right_campaign_id,
            self.summary_vars["left"]["Fault Class"].get(),
            self.summary_vars["right"]["Fault Class"].get(),
            self.METRIC_NAMES,
            self.summary_vars,
            left_name,
            left_result["raw_rows"],  # type: ignore[index]
            right_name,
            right_result["raw_rows"],  # type: ignore[index]
        )
        generated_files.extend(write_snapshot_bundle(export_dir, snapshot))

        markdown_path = export_dir / "presentation_bundle.md"
        text_path = export_dir / "presentation_bundle.txt"
        csv_path = export_dir / "presentation_bundle.csv"
        markdown_path.write_text(
            render_presentation_bundle_markdown(
                snapshot,
                verdict_lines,
                takeaway_line,
                findings_lines,
                interpretation_lines,
            ),
            encoding="utf-8",
        )
        write_presentation_bundle_text(
            text_path,
            snapshot,
            verdict_lines,
            takeaway_line,
            findings_lines,
            interpretation_lines,
        )
        write_presentation_bundle_csv(csv_path, snapshot, takeaway_line)
        generated_files.extend([markdown_path, text_path, csv_path])
        generated_files.extend(self._export_fault_path_snapshots(export_dir))

        self.status_text.set(f"Exported presentation bundle to {export_dir}")
        messagebox.showinfo(
            "Presentation Bundle Exported",
            "Saved the presentation-ready comparison bundle to:\n"
            f"{export_dir}\n\n"
            + "\n".join(path.name for path in generated_files),
        )

    def export_results_snapshot(self) -> None:
        if self.current_comparison is None:
            messagebox.showinfo(
                "No Comparison Loaded",
                "Run a left-versus-right comparison first, then export the current results snapshot.",
            )
            return

        left_result = self.current_comparison["left"]  # type: ignore[index]
        right_result = self.current_comparison["right"]  # type: ignore[index]
        left_campaign_id = str(left_result["campaign_id"])
        right_campaign_id = str(right_result["campaign_id"])
        export_dir = snapshot_export_dir(left_campaign_id, right_campaign_id)
        snapshot = self._current_snapshot_payload()
        generated_files = write_snapshot_bundle(export_dir, snapshot)
        generated_files.extend(
            save_propagation_comparison_bundle(
                export_dir,
                self.summary_vars["left"]["Campaign Name"].get(),
                left_result["raw_rows"],  # type: ignore[index]
                self.summary_vars["right"]["Campaign Name"].get(),
                right_result["raw_rows"],  # type: ignore[index]
            )
        )
        self.status_text.set(f"Exported results snapshot to {export_dir}")
        messagebox.showinfo(
            "Results Snapshot Exported",
            "Saved the presentation-ready snapshot bundle to:\n"
            f"{export_dir}\n\n"
            + "\n".join(str(path.name) for path in generated_files),
        )


def main() -> None:
    app = VirtualECUGui()
    app.mainloop()


if __name__ == "__main__":
    main()
