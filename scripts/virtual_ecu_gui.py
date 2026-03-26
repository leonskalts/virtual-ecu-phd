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
        self.geometry("1180x860")
        self.minsize(980, 760)

        self.executable = detect_executable()
        self.selected_campaign = tk.StringVar(value="baseline")
        self.status_text = tk.StringVar(value="Select a campaign and run the simulator.")
        self.summary_vars = {
            "Campaign Name": tk.StringVar(value="-"),
            "Fault Class": tk.StringVar(value="-"),
            "Final DTC": tk.StringVar(value="-"),
            "Final Safe State": tk.StringVar(value="-"),
            "Maximum Coolant Temperature": tk.StringVar(value="-"),
            "Detection Latency": tk.StringVar(value="-"),
            "Safe-State Latency": tk.StringVar(value="-"),
        }

        self._configure_style()
        self._build_layout()

        if self.executable is None:
            self.status_text.set(
                "Compiled virtual ECU executable not found. Build it first with 'make' or your local GCC toolchain."
            )
            self.run_button.state(["disabled"])

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.configure("Header.TLabel", font=("TkDefaultFont", 14, "bold"))
        style.configure("Section.TLabel", font=("TkDefaultFont", 11, "bold"))

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, padding=12)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(3, weight=1)

        ttk.Label(header, text="Virtual ECU Campaign Runner", style="Header.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(header, text="Campaign:").grid(row=1, column=0, sticky="w", pady=(12, 0))

        campaign_box = ttk.Combobox(
            header,
            textvariable=self.selected_campaign,
            values=[campaign_id for campaign_id, _label in CAMPAIGNS],
            state="readonly",
            width=32,
        )
        campaign_box.grid(row=1, column=1, sticky="w", padx=(8, 10), pady=(12, 0))

        self.run_button = ttk.Button(header, text="Run Campaign", command=self.run_selected_campaign)
        self.run_button.grid(row=1, column=2, sticky="w", pady=(12, 0))

        ttk.Label(header, textvariable=self.status_text, foreground="#3d4b59").grid(
            row=0, column=3, rowspan=2, sticky="e", padx=(20, 0)
        )

        summary_frame = ttk.LabelFrame(self, text="Run Summary", padding=12)
        summary_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        summary_frame.columnconfigure(1, weight=1)
        summary_frame.columnconfigure(3, weight=1)

        row = 0
        column = 0
        for label, variable in self.summary_vars.items():
            ttk.Label(summary_frame, text=f"{label}:").grid(
                row=row, column=column, sticky="w", padx=(0, 8), pady=4
            )
            ttk.Label(summary_frame, textvariable=variable).grid(
                row=row, column=column + 1, sticky="w", padx=(0, 18), pady=4
            )
            row += 1
            if row == 4:
                row = 0
                column = 2

        plots = ttk.Frame(self, padding=(12, 0, 12, 12))
        plots.grid(row=2, column=0, sticky="nsew")
        plots.columnconfigure(0, weight=1)
        plots.rowconfigure(0, weight=2)
        plots.rowconfigure(1, weight=1)
        plots.rowconfigure(2, weight=1)

        self.coolant_plot = PlotCanvas(plots, "Coolant Temperature vs Time")
        self.coolant_plot.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        self.safe_state_plot = PlotCanvas(plots, "Safe State vs Time")
        self.safe_state_plot.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        self.fan_plot = PlotCanvas(plots, "Fan Command vs Fan Actual")
        self.fan_plot.grid(row=2, column=0, sticky="nsew")
        self.fan_plot.show_message("Fan tracking plot appears after a permanent-fault run.")

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

        self.summary_vars["Campaign Name"].set(summary_row.get("campaign_label", campaign_id))
        self.summary_vars["Fault Class"].set(infer_fault_class(first_row))
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


def main() -> None:
    app = VirtualECUGui()
    app.mainloop()


if __name__ == "__main__":
    main()
