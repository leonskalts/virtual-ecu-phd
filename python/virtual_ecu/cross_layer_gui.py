"""Minimal Cross-Layer Safety panel, independent of existing GUI pages."""
from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from .cross_layer_safety import (
    DEFAULT_OUTPUT_DIR, PROJECT_ROOT, fault_options, read_rows,
    run_experiment, summarize_rows,
)


class CrossLayerSafetyPanel(ttk.Frame):
    def __init__(self, parent: tk.Widget, background_task: Callable) -> None:
        super().__init__(parent, padding=12)
        self.background_task = background_task
        self.columnconfigure(1, weight=1)
        ttk.Label(self, text="Cross-Layer Safety", font=("TkDefaultFont", 17, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        self.variables = {
            name: tk.StringVar(self, value=value) for name, value in (
                ("Fault Layer", "memory"), ("Fault Model", "bit_flip"),
                ("Fault Target", "control_target_register"), ("Behavior", "transient"),
                ("Start Time (ms)", "45000"), ("Duration (ms)", "100"),
                ("Bit Index", "5"), ("Seed", "42"),
            )
        }
        choices = {
            "Fault Layer": ("memory", "timing"),
            "Fault Model": ("bit_flip", "deadline_miss"),
            "Fault Target": ("control_target_register",), "Behavior": ("transient",),
        }
        self.inputs = {}
        for row, (label, variable) in enumerate(self.variables.items(), 1):
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=(0, 16), pady=3)
            if label in choices:
                widget = ttk.Combobox(self, textvariable=variable, values=choices[label], state="readonly")
            else:
                widget = ttk.Entry(self, textvariable=variable)
            widget.grid(row=row, column=1, sticky="ew", pady=3)
            self.inputs[label] = widget
        self.inputs["Fault Layer"].bind("<<ComboboxSelected>>", self._layer_changed)
        self.inputs["Fault Model"].bind("<<ComboboxSelected>>", self._model_changed)
        ttk.Label(self, text=(
            "100 ms schedule; transient faults only. Memory bit indices: 0–5. "
            "A deadline miss skips one execution (duration 100 ms).\n"
            "Runs use the default 120 s operating profile, Hybrid Adaptive Kalman, "
            "and the limp-home detector action."), wraplength=760, justify="left").grid(
                row=9, column=0, columnspan=2, sticky="w", pady=12)
        buttons = ttk.Frame(self)
        buttons.grid(row=10, column=0, columnspan=2, sticky="w")
        self.buttons = []
        for column, (text, command) in enumerate((
            ("Run Single Experiment", self.run_single),
            ("Run Cross-Layer Study", self.run_study), ("Load Results", self.load_results),
        )):
            button = ttk.Button(buttons, text=text, command=command)
            button.grid(row=0, column=column, padx=(0, 8), pady=4)
            self.buttons.append(button)
        self.status = tk.StringVar(self, value="Load a raw experiment CSV or cross_layer_run_summary.csv.")
        ttk.Label(self, textvariable=self.status, wraplength=760).grid(
            row=11, column=0, columnspan=2, sticky="w", pady=10)
        columns = ("Run", "Injected", "Detected", "Plant Manifestation", "Safe State",
                   "Detection Latency (ms)", "Propagation Depth")
        self.table = ttk.Treeview(self, columns=columns, show="headings", height=7)
        for column in columns:
            self.table.heading(column, text=column)
            self.table.column(column, width=145 if column == "Run" else 115, minwidth=75)
        self.table.grid(row=12, column=0, columnspan=2, sticky="nsew")
        scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.table.xview)
        scrollbar.grid(row=13, column=0, columnspan=2, sticky="ew")
        self.table.configure(xscrollcommand=scrollbar.set)
        ttk.Label(self, text=(
            "N/A means unavailable or not reached. Plant manifestation uses a 0.01 °C "
            "difference from the fault-free reference. Safe State means applied protective "
            "mode; it does not establish hazard containment."), wraplength=760, justify="left").grid(
                row=14, column=0, columnspan=2, sticky="w", pady=12)

    def _layer_changed(self, _event: object = None) -> None:
        self.variables["Fault Model"].set(
            "bit_flip" if self.variables["Fault Layer"].get() == "memory" else "deadline_miss")
        self._model_changed()

    def _model_changed(self, _event: object = None) -> None:
        memory = self.variables["Fault Model"].get() == "bit_flip"
        self.variables["Fault Layer"].set("memory" if memory else "timing")
        target = "control_target_register" if memory else "control_task"
        self.variables["Fault Target"].set(target)
        self.inputs["Fault Target"].configure(values=(target,))
        self.inputs["Bit Index"].configure(state="normal" if memory else "disabled")
        self.inputs["Duration (ms)"].configure(state="normal" if memory else "disabled")
        if not memory:
            self.variables["Duration (ms)"].set("100")

    def _run(self, description: str, task: Callable) -> None:
        self.status.set(description)

        def on_error(exc: Exception) -> None:
            self.status.set(f"Failed: {exc}")
            messagebox.showerror("Cross-Layer Safety", str(exc), parent=self)

        self.background_task(description, "Running deterministic Virtual ECU experiments.", task,
                             on_success=lambda path: self.load_results(Path(path)),
                             on_error=on_error, buttons_to_disable=tuple(self.buttons),
                             success_action="Cross-Layer Safety")

    def run_single(self) -> None:
        try:
            options = fault_options(
                self.variables["Fault Model"].get(),
                start_ms=int(self.variables["Start Time (ms)"].get()),
                duration_ms=int(self.variables["Duration (ms)"].get()),
                bit_index=int(self.variables["Bit Index"].get()),
                seed=int(self.variables["Seed"].get()),
            )
        except ValueError as exc:
            messagebox.showerror("Invalid cross-layer configuration", str(exc), parent=self)
            return
        path = DEFAULT_OUTPUT_DIR / "raw" / "single_experiment.csv"

        def task() -> Path:
            completed = subprocess.run(["make"], cwd=PROJECT_ROOT, capture_output=True, text=True)
            if completed.returncode:
                raise RuntimeError(completed.stderr or completed.stdout)
            run_experiment(path, ["baseline"], [*options, "--detector", "hybrid_adaptive_kalman",
                                               "--detector-action", "limp_home"])
            return path

        self._run("Running cross-layer experiment…", task)

    def run_study(self) -> None:
        seed = self.variables["Seed"].get()

        def task() -> Path:
            completed = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "scripts" / "run_cross_layer_safety_study.py"),
                 "--seed", seed], cwd=PROJECT_ROOT, capture_output=True, text=True)
            if completed.returncode:
                raise RuntimeError(completed.stderr or completed.stdout)
            return DEFAULT_OUTPUT_DIR / "cross_layer_run_summary.csv"

        self._run("Running five-case cross-layer study…", task)

    def load_results(self, path: Path | None = None) -> None:
        if path is None:
            selected = filedialog.askopenfilename(parent=self, initialdir=DEFAULT_OUTPUT_DIR,
                                                 filetypes=(("CSV results", "*.csv"),))
            if not selected:
                return
            path = Path(selected)
        try:
            rows = read_rows(path)
            if "telemetry_available" in rows[0] and "run_id" in rows[0]:
                summaries = rows
            elif "time_ms" in rows[0]:
                summaries = [{"run_id": path.stem, **summarize_rows(rows)}]
            else:
                raise ValueError("Select a raw experiment CSV or cross_layer_run_summary.csv.")
            self.table.delete(*self.table.get_children())
            keys = ("run_id", "injected", "detected", "plant_manifestation", "safe_state_reached",
                    "cross_layer_detection_latency_ms", "propagation_depth")
            for summary in summaries:
                values = ["N/A" if summary.get(key) in (None, "") else summary[key] for key in keys]
                self.table.insert("", "end", values=values)
            self.status.set(f"Loaded {path}")
        except (OSError, ValueError) as exc:
            self.status.set(f"Load failed: {exc}")
            messagebox.showerror("Cross-Layer Safety", str(exc), parent=self)
