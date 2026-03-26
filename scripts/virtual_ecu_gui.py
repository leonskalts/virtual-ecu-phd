#!/usr/bin/env python3
"""Simple Tkinter frontend for the virtual ECU simulator."""

from __future__ import annotations

import csv
import os
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ImportError as exc:  # pragma: no cover - import failure is environment-specific.
    raise SystemExit(
        "Tkinter is not available in this Python installation. "
        "Install the Tk package for Python and try again."
    ) from exc

os.environ.setdefault("MPLCONFIGDIR", "/tmp/virtual_ecu_mpl")

import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = PROJECT_ROOT / "logs"
EXPORT_ROOT = PROJECT_ROOT / "results" / "gui_comparison_reports"

CAMPAIGNS: Sequence[Tuple[str, str]] = (
    ("baseline", "Baseline"),
    ("sensor_bias_only", "Sensor Bias Only"),
    ("sensor_interface_intermittent", "Sensor Interface Intermittent"),
    ("pump_degraded_only", "Pump Degraded Only"),
    ("fan_stuck_only", "Fan Stuck Only"),
    ("fan_stuck_hot_stress", "Fan Stuck Hot Stress"),
    ("calibration_memory_corruption", "Calibration Memory Corruption"),
    ("paper_default", "Paper Default"),
)

MODE_TO_CLASS = {
    "sensor_bias": "sensing-path fault",
    "sensor_interface_intermittent": "sensing-path fault",
    "pump_degraded": "actuation-path fault",
    "fan_stuck_off": "actuation-path fault",
    "calibration_memory_corruption": "computation/memory-path fault",
}

SAFE_STATE_LABELS = {
    0: "normal",
    1: "precautionary_cooling",
    2: "limp_home",
    3: "controlled_shutdown",
}

LEFT_COLOR = "#c4473a"
RIGHT_COLOR = "#1f5aa6"
LEFT_DASH = None
RIGHT_DASH = (6, 4)

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


def summary_path_for(log_path: Path) -> Path:
    if log_path.suffix.lower() == ".csv":
        return log_path.with_name(f"{log_path.stem}_summary.csv")
    return log_path.with_name(f"{log_path.name}_summary.csv")


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


def comparison_export_dir(left_campaign_id: str, right_campaign_id: str) -> Path:
    return EXPORT_ROOT / f"{left_campaign_id}_vs_{right_campaign_id}"


def write_report_csv(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["field", "left", "right"])
        writer.writeheader()
        writer.writerows(rows)


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


class PlotCanvas(ttk.Frame):
    """Small reusable plotting widget backed by a Tkinter Canvas."""

    def __init__(self, master: tk.Misc, title: str) -> None:
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text=title, style="Section.TLabel").grid(
            row=0, column=0, sticky="w", padx=6, pady=(0, 4)
        )

        self.canvas = tk.Canvas(self, background="#ffffff", highlightthickness=1, highlightbackground="#c7d0d9")
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _event: self.redraw())
        self._drawer = self._draw_message
        self._payload: object = "No data loaded yet."

    def show_message(self, text: str) -> None:
        self._drawer = self._draw_message
        self._payload = text
        self.redraw()

    def plot_lines(
        self,
        x_values: Sequence[float],
        series: Sequence[Tuple[str, str, Sequence[float]]],
        *,
        y_label: str,
        y_min: float | None = None,
        y_max: float | None = None,
        threshold_lines: Sequence[Tuple[float, str, str]] = (),
    ) -> None:
        self._drawer = self._draw_line_plot
        self._payload = {
            "x_values": list(x_values),
            "series": [(label, color, list(values)) for label, color, values in series],
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

    def redraw(self) -> None:
        self.canvas.delete("all")
        self._drawer(self._payload)

    def _canvas_size(self) -> Tuple[int, int]:
        width = max(self.canvas.winfo_width(), 240)
        height = max(self.canvas.winfo_height(), 180)
        return width, height

    def _plot_bounds(self) -> Tuple[int, int, int, int]:
        width, height = self._canvas_size()
        return 58, 18, width - 20, height - 34

    def _draw_axes(self, y_label: str, x_label: str = "Time [s]") -> Tuple[int, int, int, int]:
        left, top, right, bottom = self._plot_bounds()
        self.canvas.create_line(left, bottom, right, bottom, fill="#4a5560", width=1)
        self.canvas.create_line(left, bottom, left, top, fill="#4a5560", width=1)
        self.canvas.create_text((left + right) / 2, bottom + 20, text=x_label, fill="#33404d")
        self.canvas.create_text(18, (top + bottom) / 2, text=y_label, fill="#33404d", angle=90)
        return left, top, right, bottom

    def _draw_message(self, payload: object) -> None:
        width, height = self._canvas_size()
        self.canvas.create_text(
            width / 2,
            height / 2,
            text=str(payload),
            fill="#506070",
            width=max(width - 40, 120),
            justify="center",
        )

    def _draw_line_plot(self, payload: object) -> None:
        data = payload  # type: ignore[assignment]
        x_values = data["x_values"]
        series = data["series"]
        y_label = data["y_label"]
        y_min = data["y_min"]
        y_max = data["y_max"]
        threshold_lines = data["threshold_lines"]

        if not x_values or not series:
            self._draw_message("No plot data available.")
            return

        left, top, right, bottom = self._draw_axes(y_label)
        all_y = [y for _, _, values in series for y in values]
        all_y.extend(value for value, _, _ in threshold_lines)

        min_x = min(x_values)
        max_x = max(x_values)
        min_y = min(all_y) if y_min is None else y_min
        max_y = max(all_y) if y_max is None else y_max

        if max_x <= min_x:
            max_x = min_x + 1.0
        if max_y <= min_y:
            max_y = min_y + 1.0

        min_y -= 0.05 * (max_y - min_y)
        max_y += 0.05 * (max_y - min_y)

        def map_x(value: float) -> float:
            return left + (value - min_x) * (right - left) / (max_x - min_x)

        def map_y(value: float) -> float:
            return bottom - (value - min_y) * (bottom - top) / (max_y - min_y)

        for tick in range(5):
            y_value = min_y + tick * (max_y - min_y) / 4.0
            y_pos = map_y(y_value)
            self.canvas.create_line(left - 4, y_pos, right, y_pos, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(left - 8, y_pos, text=f"{y_value:.1f}", anchor="e", fill="#506070")

        for tick in range(5):
            x_value = min_x + tick * (max_x - min_x) / 4.0
            x_pos = map_x(x_value)
            self.canvas.create_line(x_pos, top, x_pos, bottom + 4, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(x_pos, bottom + 16, text=f"{x_value:.0f}", anchor="n", fill="#506070")

        for value, color, label in threshold_lines:
            y_pos = map_y(value)
            self.canvas.create_line(left, y_pos, right, y_pos, fill=color, dash=(6, 4))
            self.canvas.create_text(right - 2, y_pos - 8, text=label, anchor="e", fill=color)

        legend_x = left + 6
        legend_y = top + 8
        for label, color, values in series:
            points = []
            for x_value, y_value in zip(x_values, values):
                points.extend((map_x(x_value), map_y(y_value)))

            if len(points) >= 4:
                self.canvas.create_line(*points, fill=color, width=2, smooth=False)

            self.canvas.create_line(legend_x, legend_y + 5, legend_x + 18, legend_y + 5, fill=color, width=2)
            self.canvas.create_text(legend_x + 24, legend_y + 5, text=label, anchor="w", fill="#33404d")
            legend_y += 18

    def _draw_step_plot(self, payload: object) -> None:
        data = payload  # type: ignore[assignment]
        x_values = data["x_values"]
        y_values = data["y_values"]
        y_label = data["y_label"]
        tick_labels = data["tick_labels"]

        if not x_values or not y_values:
            self._draw_message("No plot data available.")
            return

        left, top, right, bottom = self._draw_axes(y_label)
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
            self.canvas.create_text(left - 8, y_pos, text=tick_labels.get(state_id, str(state_id)), anchor="e", fill="#506070")

        for tick in range(5):
            x_value = min_x + tick * (max_x - min_x) / 4.0
            x_pos = map_x(x_value)
            self.canvas.create_line(x_pos, top, x_pos, bottom + 4, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(x_pos, bottom + 16, text=f"{x_value:.0f}", anchor="n", fill="#506070")

        points = []
        for index, (x_value, y_value) in enumerate(zip(x_values, y_values)):
            x_pos = map_x(x_value)
            y_pos = map_y(y_value)
            points.extend((x_pos, y_pos))

            if index + 1 < len(x_values):
                next_x = map_x(x_values[index + 1])
                points.extend((next_x, y_pos))

        if len(points) >= 4:
            self.canvas.create_line(*points, fill="#1f5aa6", width=2, smooth=False)

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

        left, top, right, bottom = self._draw_axes(y_label)
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
                left - 8,
                y_pos,
                text=tick_labels.get(state_id, str(state_id)),
                anchor="e",
                fill="#506070",
            )

        for tick in range(5):
            x_value = min_x + tick * (max_x - min_x) / 4.0
            x_pos = map_x(x_value)
            self.canvas.create_line(x_pos, top, x_pos, bottom + 4, fill="#e7edf2", dash=(2, 4))
            self.canvas.create_text(x_pos, bottom + 16, text=f"{x_value:.0f}", anchor="n", fill="#506070")

        legend_x = left + 8
        legend_y = top + 8

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
                self.canvas.create_line(*points, fill=color, width=2, dash=dash or ())

            self.canvas.create_line(
                legend_x,
                legend_y + 5,
                legend_x + 20,
                legend_y + 5,
                fill=color,
                width=2,
                dash=dash or (),
            )
            self.canvas.create_text(legend_x + 26, legend_y + 5, text=label, anchor="w", fill="#33404d")
            legend_y += 18


class VirtualECUGui(tk.Tk):
    METRIC_NAMES = (
        "Final DTC",
        "Final Safe State",
        "Maximum Coolant Temperature",
        "Detection Latency",
        "Safe-State Latency",
    )

    def __init__(self) -> None:
        super().__init__()
        self.title("Virtual ECU Research GUI")
        self.geometry("1320x980")
        self.minsize(1120, 860)

        self.executable = detect_executable()
        self.left_campaign = tk.StringVar(value="baseline")
        self.right_campaign = tk.StringVar(value="fan_stuck_hot_stress")
        self.status_text = tk.StringVar(value="Select two campaigns and run a comparison.")
        self.left_description_var = tk.StringVar(value="-")
        self.right_description_var = tk.StringVar(value="-")

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

        self._configure_style()
        self._build_layout()
        self._refresh_campaign_context()
        self._reset_summary_values()

        if self.executable is None:
            self.status_text.set(
                "Compiled virtual ECU executable not found. Build it first with 'make' or your local GCC toolchain."
            )
            self.run_compare_button.state(["disabled"])
            self.run_left_button.state(["disabled"])
            self.export_button.state(["disabled"])

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.configure("Root.TFrame", background="#f4f6f8")
        style.configure("Panel.TFrame", background="#eef3f7")
        style.configure("Header.TLabel", font=("TkDefaultFont", 16, "bold"), background="#f4f6f8")
        style.configure("Subheader.TLabel", font=("TkDefaultFont", 10), foreground="#465564", background="#f4f6f8")
        style.configure("Section.TLabel", font=("TkDefaultFont", 11, "bold"))
        style.configure("FieldName.TLabel", font=("TkDefaultFont", 10, "bold"), foreground="#22313f")
        style.configure("FieldValue.TLabel", font=("TkDefaultFont", 10), foreground="#374553")
        style.configure("Hint.TLabel", font=("TkDefaultFont", 9), foreground="#4d5c69")
        style.configure("ColumnHeader.TLabel", font=("TkDefaultFont", 10, "bold"), foreground="#1d3448")
        style.configure("MetricLabel.TLabel", font=("TkDefaultFont", 10, "bold"), foreground="#2a3947")

    def _build_layout(self) -> None:
        self.configure(background="#f4f6f8")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, padding=(16, 14, 16, 10), style="Root.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, weight=1)

        ttk.Label(header, text="Virtual ECU Comparison Explorer", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            header,
            text="Comparison mode highlights how different hardware-origin fault campaigns change diagnostics, safety response, and thermal behavior.",
            style="Subheader.TLabel",
            wraplength=860,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 12))
        ttk.Label(header, textvariable=self.status_text, foreground="#3d4b59").grid(
            row=0, column=2, rowspan=2, sticky="e"
        )

        selectors = ttk.Frame(header, style="Root.TFrame")
        selectors.grid(row=2, column=0, columnspan=2, sticky="ew")
        selectors.columnconfigure(0, weight=1)
        selectors.columnconfigure(1, weight=1)

        self._build_selector_card(
            selectors,
            0,
            "Left Campaign",
            self.left_campaign,
            self.left_description_var,
            self._on_campaign_changed,
        )
        self._build_selector_card(
            selectors,
            1,
            "Right Campaign",
            self.right_campaign,
            self.right_description_var,
            self._on_campaign_changed,
        )

        actions = ttk.Frame(header, style="Root.TFrame")
        actions.grid(row=2, column=2, sticky="e")

        self.run_compare_button = ttk.Button(actions, text="Run Comparison", command=self.run_comparison)
        self.run_compare_button.grid(row=0, column=0, sticky="e")
        self.run_left_button = ttk.Button(actions, text="Run Left Only", command=self.run_left_only)
        self.run_left_button.grid(row=1, column=0, sticky="e", pady=(8, 0))
        self.export_button = ttk.Button(actions, text="Export Comparison Report", command=self.export_current_comparison)
        self.export_button.grid(row=2, column=0, sticky="e", pady=(8, 0))
        self.export_button.state(["disabled"])

        info_area = ttk.Frame(self, padding=(16, 0, 16, 12), style="Root.TFrame")
        info_area.grid(row=1, column=0, sticky="ew")
        info_area.columnconfigure(0, weight=3)
        info_area.columnconfigure(1, weight=2)

        summary_frame = ttk.LabelFrame(info_area, text="Comparison Summary", padding=14)
        summary_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
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

        context_frame = ttk.LabelFrame(info_area, text="Campaign Context", padding=14)
        context_frame.grid(row=0, column=1, sticky="nsew")
        context_frame.columnconfigure(0, weight=1)
        context_frame.columnconfigure(1, weight=1)

        self._build_context_column(context_frame, 0, "Left Context", "left", LEFT_COLOR)
        self._build_context_column(context_frame, 1, "Right Context", "right", RIGHT_COLOR)

        plots = ttk.Frame(self, padding=(16, 0, 16, 16), style="Root.TFrame")
        plots.grid(row=2, column=0, sticky="nsew")
        plots.columnconfigure(0, weight=1)
        plots.rowconfigure(0, weight=2)
        plots.rowconfigure(1, weight=1)
        plots.rowconfigure(2, weight=1)

        self.coolant_plot = PlotCanvas(plots, "Coolant Temperature Comparison")
        self.coolant_plot.grid(row=0, column=0, sticky="nsew", pady=(0, 12))

        self.safe_state_plot = PlotCanvas(plots, "Safe-State Comparison")
        self.safe_state_plot.grid(row=1, column=0, sticky="nsew", pady=(0, 12))

        self.fan_plot = PlotCanvas(plots, "Fan Command / Actual Comparison")
        self.fan_plot.grid(row=2, column=0, sticky="nsew")
        self.fan_plot.show_message("Run a comparison to overlay fan command and actual response.")

    def _build_selector_card(
        self,
        parent: ttk.Frame,
        column: int,
        title: str,
        variable: tk.StringVar,
        description_var: tk.StringVar,
        callback,
    ) -> None:
        card = ttk.Frame(parent, padding=(0, 0, 16 if column == 0 else 0, 0), style="Root.TFrame")
        card.grid(row=0, column=column, sticky="ew")
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text=title, style="FieldName.TLabel").grid(row=0, column=0, sticky="w")
        box = ttk.Combobox(
            card,
            textvariable=variable,
            values=[campaign_id for campaign_id, _label in CAMPAIGNS],
            state="readonly",
            width=32,
        )
        box.grid(row=0, column=1, sticky="w", padx=(10, 0))
        box.bind("<<ComboboxSelected>>", callback)

        ttk.Label(
            card,
            textvariable=description_var,
            style="Hint.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=1, column=1, sticky="w", pady=(6, 0))

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

        accent_bar = tk.Frame(block, bg=accent, width=10)
        accent_bar.pack(side="left", fill="y")

        body = ttk.Frame(block, padding=(12, 10, 12, 10), style="Root.TFrame")
        body.pack(side="left", fill="both", expand=True)

        ttk.Label(body, text=title, style="ColumnHeader.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self._add_context_row(body, 1, "Fault Class", self.context_vars[slot]["Fault Class"])
        self._add_context_row(body, 2, "Hardware Source", self.context_vars[slot]["Hardware Source"])
        self._add_context_row(body, 3, "ECU Manifestation", self.context_vars[slot]["ECU Manifestation"])

    def _add_context_row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label, style="FieldName.TLabel").grid(row=row, column=0, sticky="nw", pady=(0, 2))
        ttk.Label(
            parent,
            textvariable=variable,
            style="FieldValue.TLabel",
            wraplength=320,
            justify="left",
        ).grid(row=row + 1, column=0, sticky="nw", pady=(0, 8))

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

    def _reset_summary_values(self) -> None:
        self.current_comparison = None
        self.export_button.state(["disabled"])
        for slot in ("left", "right"):
            for metric_name in self.METRIC_NAMES:
                self.summary_vars[slot][metric_name].set("-")
        self._refresh_metric_cells()

    def run_left_only(self) -> None:
        self._run_campaigns(include_right=False)

    def run_comparison(self) -> None:
        self._run_campaigns(include_right=True)

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
        self.status_text.set(
            f"Running comparison: {left_campaign} vs {right_campaign}..."
            if include_right else f"Running left campaign: {left_campaign}..."
        )
        self.run_compare_button.state(["disabled"])
        self.run_left_button.state(["disabled"])
        self.export_button.state(["disabled"])

        worker = threading.Thread(
            target=self._run_campaigns_worker,
            args=(include_right,),
            daemon=True,
        )
        worker.start()

    def _run_single_campaign(self, campaign_id: str, slot: str) -> Dict[str, object]:
        log_path = campaign_log_path(campaign_id, slot)
        summary_path = summary_path_for(log_path)
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

        raw_rows = read_csv_rows(log_path)
        summary_rows = read_csv_rows(summary_path)
        if not raw_rows or not summary_rows:
            raise RuntimeError("The simulator completed but did not generate readable CSV data.")

        return {
            "campaign_id": campaign_id,
            "raw_rows": raw_rows,
            "summary_row": summary_rows[0],
        }

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

    def _show_error(self, message: str) -> None:
        self.status_text.set("Run failed.")
        self.run_compare_button.state(["!disabled"])
        self.run_left_button.state(["!disabled"])
        self.export_button.state(["disabled"])
        messagebox.showerror("Virtual ECU Run Failed", message)

    def _apply_results(
        self,
        left_result: Dict[str, object],
        right_result: Dict[str, object] | None,
    ) -> None:
        self.run_compare_button.state(["!disabled"])
        self.run_left_button.state(["!disabled"])

        left_campaign = str(left_result["campaign_id"])
        self._apply_summary_slot("left", left_campaign, left_result["raw_rows"], left_result["summary_row"])

        if right_result is not None:
            right_campaign = str(right_result["campaign_id"])
            self._apply_summary_slot("right", right_campaign, right_result["raw_rows"], right_result["summary_row"])
            self.status_text.set(f"Loaded comparison: {left_campaign} vs {right_campaign}.")
            self.current_comparison = {
                "left": left_result,
                "right": right_result,
            }
            self.export_button.state(["!disabled"])
        else:
            self._clear_slot("right")
            self.status_text.set(f"Loaded left campaign: {left_campaign}.")
            self.current_comparison = None
            self.export_button.state(["disabled"])

        self._refresh_metric_cells()
        self._update_plots(left_result, right_result)

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

        self.summary_vars[slot]["Campaign Name"].set(summary.get("campaign_label", campaign_id))
        self.summary_vars[slot]["Fault Class"].set(summarize_fault_class(campaign_id, first_row))
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
        for metric_name in self.METRIC_NAMES:
            self.summary_vars[slot][metric_name].set("-")

    def _refresh_metric_cells(self) -> None:
        for slot in ("left", "right"):
            for metric_name in self.METRIC_NAMES:
                background, foreground = metric_card_colors(metric_name, self.summary_vars[slot][metric_name].get())
                cell = self.metric_cells[slot][metric_name]
                frame = cell["frame"]
                value = cell["value"]
                frame.configure(bg=background)
                value.configure(bg=background, fg=foreground)

    def _update_plots(
        self,
        left_result: Dict[str, object],
        right_result: Dict[str, object] | None,
    ) -> None:
        left_rows = left_result["raw_rows"]  # type: ignore[assignment]
        left_label = self.summary_vars["left"]["Campaign Name"].get()

        coolant_series = [
            (
                left_label,
                LEFT_COLOR,
                float_series(left_rows, "coolant_temp_true_c"),
            )
        ]
        time_axis = float_series(left_rows, "time_s")

        if right_result is not None:
            right_rows = right_result["raw_rows"]  # type: ignore[assignment]
            right_label = self.summary_vars["right"]["Campaign Name"].get()
            coolant_series.append(
                (
                    right_label,
                    RIGHT_COLOR,
                    float_series(right_rows, "coolant_temp_true_c"),
                )
            )

        self.coolant_plot.plot_lines(
            time_axis,
            coolant_series,
            y_label="Temp [C]",
            threshold_lines=((108.0, "#8c6b2d", "Warning"), (115.0, "#7b4d57", "Critical")),
        )

        safe_series = [
            (
                left_label,
                LEFT_COLOR,
                float_series(left_rows, "time_s"),
                int_series(left_rows, "safe_state_id"),
                LEFT_DASH,
            )
        ]

        if right_result is not None:
            right_rows = right_result["raw_rows"]  # type: ignore[assignment]
            safe_series.append(
                (
                    self.summary_vars["right"]["Campaign Name"].get(),
                    RIGHT_COLOR,
                    float_series(right_rows, "time_s"),
                    int_series(right_rows, "safe_state_id"),
                    RIGHT_DASH,
                )
            )

        self.safe_state_plot.plot_step_comparison(
            safe_series,
            y_label="State",
            tick_labels=SAFE_STATE_LABELS,
        )

        fan_series = [
            (f"{left_label} command", LEFT_COLOR, float_series(left_rows, "fan_command")),
            (f"{left_label} actual", "#7d1f17", float_series(left_rows, "fan_actual")),
        ]
        fan_time_axis = float_series(left_rows, "time_s")
        left_permanent = "permanent" in event_behaviors(left_rows[0])
        right_permanent = False

        if right_result is not None:
            right_rows = right_result["raw_rows"]  # type: ignore[assignment]
            right_label = self.summary_vars["right"]["Campaign Name"].get()
            right_permanent = "permanent" in event_behaviors(right_rows[0])
            fan_series.extend(
                (
                    (f"{right_label} command", RIGHT_COLOR, float_series(right_rows, "fan_command")),
                    (f"{right_label} actual", "#5e7fb0", float_series(right_rows, "fan_actual")),
                )
            )

        if left_permanent or right_permanent:
            self.fan_plot.plot_lines(
                fan_time_axis,
                fan_series,
                y_label="Fan [-]",
                y_min=0.0,
                y_max=1.0,
            )
        else:
            self.fan_plot.show_message(
                "Neither selected campaign contains a permanent-fault phase, so the fan comparison is hidden."
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
        export_dir.mkdir(parents=True, exist_ok=True)
        os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

        report_rows = [
            {"field": "left_campaign_id", "left": left_campaign_id, "right": ""},
            {"field": "right_campaign_id", "left": right_campaign_id, "right": ""},
            {"field": "left_fault_class", "left": self.summary_vars["left"]["Fault Class"].get(), "right": ""},
            {"field": "right_fault_class", "left": self.summary_vars["right"]["Fault Class"].get(), "right": ""},
        ]

        for metric_name in self.METRIC_NAMES:
            report_rows.append(
                {
                    "field": metric_name.lower().replace(" ", "_"),
                    "left": self.summary_vars["left"][metric_name].get(),
                    "right": self.summary_vars["right"][metric_name].get(),
                }
            )

        write_report_csv(export_dir / "comparison_summary.csv", report_rows)

        with (export_dir / "comparison_summary.txt").open("w", encoding="utf-8") as handle:
            handle.write("Virtual ECU Comparison Report\n")
            handle.write(f"Left campaign: {left_campaign_id}\n")
            handle.write(f"Right campaign: {right_campaign_id}\n")
            handle.write(f"Left fault class: {self.summary_vars['left']['Fault Class'].get()}\n")
            handle.write(f"Right fault class: {self.summary_vars['right']['Fault Class'].get()}\n\n")
            for metric_name in self.METRIC_NAMES:
                handle.write(
                    f"{metric_name}: left={self.summary_vars['left'][metric_name].get()}, "
                    f"right={self.summary_vars['right'][metric_name].get()}\n"
                )

        left_rows = left_result["raw_rows"]  # type: ignore[index]
        right_rows = right_result["raw_rows"]  # type: ignore[index]
        left_label = self.summary_vars["left"]["Campaign Name"].get()
        right_label = self.summary_vars["right"]["Campaign Name"].get()

        save_coolant_comparison_plot(
            left_label,
            left_rows,
            right_label,
            right_rows,
            export_dir / "coolant_temperature_comparison.png",
        )
        save_safe_state_comparison_plot(
            left_label,
            left_rows,
            right_label,
            right_rows,
            export_dir / "safe_state_comparison.png",
        )

        left_permanent = "permanent" in event_behaviors(left_rows[0])
        right_permanent = "permanent" in event_behaviors(right_rows[0])
        if left_permanent or right_permanent:
            save_fan_comparison_plot(
                left_label,
                left_rows,
                right_label,
                right_rows,
                export_dir / "fan_comparison.png",
            )

        self.status_text.set(f"Exported comparison report to {export_dir}")
        messagebox.showinfo(
            "Comparison Exported",
            f"Saved the comparison report and plot images to:\n{export_dir}",
        )


def main() -> None:
    app = VirtualECUGui()
    app.mainloop()


if __name__ == "__main__":
    main()
