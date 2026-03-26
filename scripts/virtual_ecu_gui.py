#!/usr/bin/env python3
"""Simple Tkinter frontend for the virtual ECU simulator."""

from __future__ import annotations

import csv
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = PROJECT_ROOT / "logs"

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


def campaign_log_path(campaign_id: str) -> Path:
    return LOGS_DIR / f"gui_{campaign_id}.csv"


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


class VirtualECUGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Virtual ECU Research GUI")
        self.geometry("1240x920")
        self.minsize(1040, 800)

        self.executable = detect_executable()
        self.selected_campaign = tk.StringVar(value="baseline")
        self.status_text = tk.StringVar(value="Select a campaign and run the simulator.")
        self.campaign_description_var = tk.StringVar(value="-")
        self.summary_vars = {
            "Campaign Name": tk.StringVar(value="-"),
            "Fault Class": tk.StringVar(value="-"),
            "Final DTC": tk.StringVar(value="-"),
            "Final Safe State": tk.StringVar(value="-"),
            "Maximum Coolant Temperature": tk.StringVar(value="-"),
            "Detection Latency": tk.StringVar(value="-"),
            "Safe-State Latency": tk.StringVar(value="-"),
        }
        self.story_vars = {
            "Fault Class": tk.StringVar(value="-"),
            "Hardware-Origin Fault Source": tk.StringVar(value="-"),
            "ECU-Level Manifestation": tk.StringVar(value="-"),
            "Expected Diagnostic Effect": tk.StringVar(value="-"),
            "Expected Safe-State / System Effect": tk.StringVar(value="-"),
        }
        self.metric_card_widgets: Dict[str, Dict[str, tk.Widget]] = {}

        self._configure_style()
        self._build_layout()
        self._refresh_campaign_story()
        self._refresh_metric_cards()

        if self.executable is None:
            self.status_text.set(
                "Compiled virtual ECU executable not found. Build it first with 'make' or your local GCC toolchain."
            )
            self.run_button.state(["disabled"])

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.configure("Root.TFrame", background="#f4f6f8")
        style.configure("Header.TLabel", font=("TkDefaultFont", 16, "bold"), background="#f4f6f8")
        style.configure("Subheader.TLabel", font=("TkDefaultFont", 10), foreground="#465564", background="#f4f6f8")
        style.configure("Section.TLabel", font=("TkDefaultFont", 11, "bold"))
        style.configure("FieldName.TLabel", font=("TkDefaultFont", 10, "bold"), foreground="#22313f")
        style.configure("FieldValue.TLabel", font=("TkDefaultFont", 10), foreground="#374553")
        style.configure("Hint.TLabel", font=("TkDefaultFont", 9), foreground="#4d5c69")
        style.configure("CrossTitle.TLabel", font=("TkDefaultFont", 10, "bold"), foreground="#1d3448")
        style.configure("CrossValue.TLabel", font=("TkDefaultFont", 10), foreground="#374553")

    def _build_layout(self) -> None:
        self.configure(background="#f4f6f8")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, padding=(16, 14, 16, 10), style="Root.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(3, weight=1)

        ttk.Label(header, text="Virtual ECU Cross-Layer Campaign Explorer", style="Header.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        ttk.Label(
            header,
            text="Hardware-origin fault abstraction to ECU diagnostics, safety response, and thermal outcome.",
            style="Subheader.TLabel",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 12))
        ttk.Label(header, text="Campaign", style="FieldName.TLabel").grid(row=2, column=0, sticky="w")

        campaign_box = ttk.Combobox(
            header,
            textvariable=self.selected_campaign,
            values=[campaign_id for campaign_id, _label in CAMPAIGNS],
            state="readonly",
            width=32,
        )
        campaign_box.grid(row=2, column=1, sticky="w", padx=(10, 12))
        campaign_box.bind("<<ComboboxSelected>>", self._on_campaign_changed)

        self.run_button = ttk.Button(header, text="Run Selected Campaign", command=self.run_selected_campaign)
        self.run_button.grid(row=2, column=2, sticky="w")

        ttk.Label(
            header,
            textvariable=self.campaign_description_var,
            style="Hint.TLabel",
            wraplength=640,
            justify="left",
        ).grid(row=3, column=1, columnspan=2, sticky="w", pady=(8, 0))

        ttk.Label(header, textvariable=self.status_text, foreground="#3d4b59").grid(
            row=0, column=3, rowspan=4, sticky="e", padx=(24, 0)
        )

        info_area = ttk.Frame(self, padding=(16, 0, 16, 12), style="Root.TFrame")
        info_area.grid(row=1, column=0, sticky="ew")
        info_area.columnconfigure(0, weight=1)
        info_area.columnconfigure(1, weight=2)

        summary_frame = ttk.LabelFrame(info_area, text="Run Summary", padding=14)
        summary_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.columnconfigure(1, weight=1)

        summary_header = ttk.Frame(summary_frame, style="Root.TFrame")
        summary_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        summary_header.columnconfigure(1, weight=1)

        ttk.Label(summary_header, text="Campaign Name", style="FieldName.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 10)
        )
        ttk.Label(
            summary_header,
            textvariable=self.summary_vars["Campaign Name"],
            style="FieldValue.TLabel",
            wraplength=280,
            justify="left",
        ).grid(row=0, column=1, sticky="w")
        ttk.Label(summary_header, text="Fault Class", style="FieldName.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=(6, 0)
        )
        ttk.Label(
            summary_header,
            textvariable=self.summary_vars["Fault Class"],
            style="FieldValue.TLabel",
            wraplength=280,
            justify="left",
        ).grid(row=1, column=1, sticky="w", pady=(6, 0))

        metric_cards = ttk.Frame(summary_frame, style="Root.TFrame")
        metric_cards.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        metric_cards.columnconfigure(0, weight=1)
        metric_cards.columnconfigure(1, weight=1)

        card_names = [
            "Final DTC",
            "Final Safe State",
            "Maximum Coolant Temperature",
            "Detection Latency",
            "Safe-State Latency",
        ]

        for index, name in enumerate(card_names):
            row = index // 2
            column = index % 2
            self._add_metric_card(metric_cards, row, column, name, self.summary_vars[name])

        ttk.Label(
            summary_frame,
            text="Key run outcomes are emphasized here for fast demo narration and comparison.",
            style="Hint.TLabel",
            wraplength=360,
            justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w")

        story_frame = ttk.LabelFrame(info_area, text="Cross-Layer Interpretation", padding=14)
        story_frame.grid(row=0, column=1, sticky="nsew")
        story_frame.columnconfigure(0, weight=1)

        ttk.Label(
            story_frame,
            text="Hardware-origin fault -> ECU-level manifestation -> diagnostic and safe-state effect",
            style="Hint.TLabel",
            wraplength=600,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        self._add_emphasis_readout(story_frame, 1, "Fault Class", self.story_vars["Fault Class"])
        self._add_cross_layer_block(
            story_frame,
            2,
            "1. Plausible Hardware-Origin Fault Source",
            self.story_vars["Hardware-Origin Fault Source"],
            accent="#8a6120",
        )
        self._add_cross_layer_block(
            story_frame,
            3,
            "2. ECU-Level Manifestation",
            self.story_vars["ECU-Level Manifestation"],
            accent="#1c4d8c",
        )
        self._add_cross_layer_block(
            story_frame,
            4,
            "3. Expected Diagnostic Effect",
            self.story_vars["Expected Diagnostic Effect"],
            accent="#8a2f27",
        )
        self._add_cross_layer_block(
            story_frame,
            5,
            "4. Expected Safe-State / System Effect",
            self.story_vars["Expected Safe-State / System Effect"],
            accent="#245f3d",
        )

        plots = ttk.Frame(self, padding=(16, 0, 16, 16), style="Root.TFrame")
        plots.grid(row=2, column=0, sticky="nsew")
        plots.columnconfigure(0, weight=1)
        plots.rowconfigure(0, weight=2)
        plots.rowconfigure(1, weight=1)
        plots.rowconfigure(2, weight=1)

        self.coolant_plot = PlotCanvas(plots, "Coolant Temperature vs Time")
        self.coolant_plot.grid(row=0, column=0, sticky="nsew", pady=(0, 12))

        self.safe_state_plot = PlotCanvas(plots, "Safe State vs Time")
        self.safe_state_plot.grid(row=1, column=0, sticky="nsew", pady=(0, 12))

        self.fan_plot = PlotCanvas(plots, "Fan Command vs Fan Actual")
        self.fan_plot.grid(row=2, column=0, sticky="nsew")
        self.fan_plot.show_message("Fan tracking plot appears after a permanent-fault run.")

    def _add_metric_card(
        self,
        parent: ttk.Frame,
        row: int,
        column: int,
        label: str,
        variable: tk.StringVar,
    ) -> None:
        card = tk.Frame(parent, bg="#eef3f7", bd=1, relief="solid", highlightthickness=0)
        card.grid(row=row, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0), pady=(0, 8))
        parent.rowconfigure(row, weight=1)

        title_label = tk.Label(
            card,
            text=label,
            bg="#eef3f7",
            fg="#4e5d6b",
            font=("TkDefaultFont", 9, "bold"),
            anchor="w",
            justify="left",
        )
        title_label.pack(fill="x", padx=10, pady=(8, 2))

        value_label = tk.Label(
            card,
            textvariable=variable,
            bg="#eef3f7",
            fg="#1f2e3b",
            font=("TkDefaultFont", 12, "bold"),
            anchor="w",
            justify="left",
            wraplength=170,
        )
        value_label.pack(fill="x", padx=10, pady=(0, 10))

        self.metric_card_widgets[label] = {
            "frame": card,
            "title": title_label,
            "value": value_label,
        }

    def _add_emphasis_readout(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
    ) -> None:
        container = ttk.Frame(parent, padding=(0, 0, 0, 10), style="Root.TFrame")
        container.grid(row=row, column=0, sticky="ew")
        container.columnconfigure(0, minsize=120)
        container.columnconfigure(1, weight=1)

        ttk.Label(container, text=label, style="FieldName.TLabel").grid(row=0, column=0, sticky="nw", padx=(0, 10))
        ttk.Label(
            container,
            textvariable=variable,
            style="FieldValue.TLabel",
            wraplength=620,
            justify="left",
        ).grid(row=0, column=1, sticky="nw")

    def _add_cross_layer_block(
        self,
        parent: ttk.Frame,
        row: int,
        title: str,
        variable: tk.StringVar,
        *,
        accent: str,
    ) -> None:
        block = tk.Frame(parent, bg="#ffffff", bd=1, relief="solid", highlightthickness=0)
        block.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        accent_bar = tk.Frame(block, bg=accent, width=8)
        accent_bar.pack(side="left", fill="y")

        body = ttk.Frame(block, padding=(12, 10, 12, 10), style="Root.TFrame")
        body.pack(side="left", fill="both", expand=True)

        ttk.Label(body, text=title, style="CrossTitle.TLabel").pack(anchor="w")
        ttk.Label(
            body,
            textvariable=variable,
            style="CrossValue.TLabel",
            wraplength=610,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

    def _on_campaign_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._refresh_campaign_story()
        self._reset_run_specific_summary()

    def _refresh_campaign_story(self) -> None:
        campaign_id = self.selected_campaign.get()
        story = campaign_story(campaign_id)
        self.campaign_description_var.set(story["description"])

        self.story_vars["Fault Class"].set(story["fault_class"])
        self.story_vars["Hardware-Origin Fault Source"].set(story["hardware_source"])
        self.story_vars["ECU-Level Manifestation"].set(story["ecu_manifestation"])
        self.story_vars["Expected Diagnostic Effect"].set(story["diagnostic_effect"])
        self.story_vars["Expected Safe-State / System Effect"].set(story["system_effect"])
        self.summary_vars["Campaign Name"].set(story["campaign_name"])
        self.summary_vars["Fault Class"].set(story["fault_class"])

    def _reset_run_specific_summary(self) -> None:
        for key in (
            "Final DTC",
            "Final Safe State",
            "Maximum Coolant Temperature",
            "Detection Latency",
            "Safe-State Latency",
        ):
            self.summary_vars[key].set("-")
        self._refresh_metric_cards()

    def run_selected_campaign(self) -> None:
        if self.executable is None:
            messagebox.showerror(
                "Executable Not Found",
                "The compiled virtual ECU executable was not found. Build it first with 'make'.",
            )
            return

        campaign_id = self.selected_campaign.get()
        log_path = campaign_log_path(campaign_id)

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.status_text.set(f"Running {campaign_id}...")
        self.run_button.state(["disabled"])

        worker = threading.Thread(
            target=self._run_campaign_worker,
            args=(campaign_id, log_path),
            daemon=True,
        )
        worker.start()

    def _run_campaign_worker(self, campaign_id: str, log_path: Path) -> None:
        summary_path = summary_path_for(log_path)
        command = [str(self.executable), str(log_path), campaign_id]

        try:
            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            message = f"Failed to run simulator: {exc}"
            self.after(0, lambda msg=message: self._show_error(msg))
            return

        if completed.returncode != 0:
            output = (completed.stderr or completed.stdout or "Unknown simulator failure.").strip()
            self.after(0, lambda msg=output: self._show_error(msg))
            return

        try:
            raw_rows = read_csv_rows(log_path)
            summary_rows = read_csv_rows(summary_path)
        except (OSError, csv.Error) as exc:
            message = f"Failed to load generated CSV files: {exc}"
            self.after(0, lambda msg=message: self._show_error(msg))
            return

        if not raw_rows or not summary_rows:
            self.after(
                0,
                lambda msg="The simulator completed but did not generate readable CSV data.": self._show_error(msg),
            )
            return

        self.after(0, lambda: self._apply_run_results(campaign_id, raw_rows, summary_rows[0]))

    def _show_error(self, message: str) -> None:
        self.status_text.set("Run failed.")
        self.run_button.state(["!disabled"])
        messagebox.showerror("Virtual ECU Run Failed", message)

    def _apply_run_results(
        self,
        campaign_id: str,
        raw_rows: Sequence[Dict[str, str]],
        summary_row: Dict[str, str],
    ) -> None:
        first_row = raw_rows[0]
        self.status_text.set(f"Loaded {campaign_id} from generated CSV output.")
        self.run_button.state(["!disabled"])
        self._refresh_campaign_story()

        self.summary_vars["Campaign Name"].set(summary_row.get("campaign_label", campaign_id))
        self.summary_vars["Fault Class"].set(summarize_fault_class(campaign_id, first_row))
        self.summary_vars["Final DTC"].set(summary_row.get("final_primary_dtc_label", "none"))
        self.summary_vars["Final Safe State"].set(summary_row.get("final_safe_state_label", "normal"))
        self.summary_vars["Maximum Coolant Temperature"].set(
            format_temperature(summary_row.get("max_coolant_temp_c", ""))
        )
        self.summary_vars["Detection Latency"].set(
            format_latency(summary_row.get("detection_latency_ms", ""))
        )
        self.summary_vars["Safe-State Latency"].set(
            format_latency(summary_row.get("safe_state_latency_ms", ""))
        )
        self._refresh_metric_cards()

        time_s = float_series(raw_rows, "time_s")
        coolant_temp = float_series(raw_rows, "coolant_temp_true_c")
        safe_state = int_series(raw_rows, "safe_state_id")
        fan_command = float_series(raw_rows, "fan_command")
        fan_actual = float_series(raw_rows, "fan_actual")

        self.coolant_plot.plot_lines(
            time_s,
            (("Coolant temperature", "#c4473a", coolant_temp),),
            y_label="Temp [C]",
            threshold_lines=((108.0, "#8c6b2d", "Warning"), (115.0, "#7b4d57", "Critical")),
        )
        self.safe_state_plot.plot_step_series(
            time_s,
            safe_state,
            y_label="State",
            tick_labels=SAFE_STATE_LABELS,
        )

        if "permanent" in event_behaviors(first_row):
            self.fan_plot.plot_lines(
                time_s,
                (
                    ("Fan command", "#1f5aa6", fan_command),
                    ("Fan actual", "#111111", fan_actual),
                ),
                y_label="Fan [-]",
                y_min=0.0,
                y_max=1.0,
            )
        else:
            self.fan_plot.show_message(
                "This campaign does not contain a permanent injected fault, so the fan tracking plot is hidden."
            )

    def _refresh_metric_cards(self) -> None:
        for metric_name, widgets in self.metric_card_widgets.items():
            background, foreground = metric_card_colors(metric_name, self.summary_vars[metric_name].get())
            frame = widgets["frame"]
            title = widgets["title"]
            value = widgets["value"]
            frame.configure(bg=background)
            title.configure(bg=background)
            value.configure(bg=background, fg=foreground)


def main() -> None:
    app = VirtualECUGui()
    app.mainloop()


if __name__ == "__main__":
    main()
