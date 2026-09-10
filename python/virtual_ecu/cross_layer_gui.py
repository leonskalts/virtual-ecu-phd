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
    run_experiment, summarize_rows, MODEL_TARGETS, STAGES,
)

from .cross_layer_campaign import DEFAULT_CAMPAIGN_DIR, DEFAULT_STUDY


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
                ("Intermittent ON (ms)", "100"), ("Intermittent OFF (ms)", "500"),
                ("Stuck Polarity", "1"), ("Communication Delay (ms)", "300"),
                ("Drop Count", "3"), ("Drop Every N Updates", "0"),
                ("Replay Age (ms)", "500"), ("Task Delay (ms)", "200"),
                ("FTTI (ms)", "5000"), ("Warning Threshold (°C)", "108"),
                ("Critical Threshold (°C)", "115"), ("Max Critical Exposure (ms)", "1000"),
            )
        }
        choices = {
            "Fault Layer": ("memory", "timing", "communication"),
            "Fault Model": tuple(MODEL_TARGETS),
            "Fault Target": ("control_target_register",), "Behavior": ("transient", "intermittent", "permanent"),
            "Stuck Polarity": ("0", "1"),
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
        self.inputs["Behavior"].bind("<<ComboboxSelected>>", self._model_changed)
        self._model_changed()
        form_end = len(self.variables) + 1
        ttk.Label(self, text=(
            "100 ms ticks; memory bits 0–5. Intermittent duration bounds the ON/OFF train. "
            "Permanent faults persist to the end. Campaign settings come from a study file.\n"
            "Single runs use the default 120 s operating profile, Hybrid Adaptive Kalman, "
            "and the limp-home detector action."), wraplength=760, justify="left").grid(
                row=form_end, column=0, columnspan=2, sticky="w", pady=12)
        buttons = ttk.Frame(self)
        buttons.grid(row=form_end+1, column=0, columnspan=2, sticky="w")
        self.buttons = []
        for column, (text, command) in enumerate((
            ("Run Single Experiment", self.run_single),
            ("Run Cross-Layer Study", self.run_study), ("Load Results", self.load_results),
            ("Run Campaign", self.run_campaign), ("Load Campaign Results", self.load_campaign_results),
        )):
            button = ttk.Button(buttons, text=text, command=command)
            button.grid(row=column//3, column=column%3, padx=(0, 8), pady=4)
            self.buttons.append(button)
        self.status = tk.StringVar(self, value="Load raw CSV, v1 summary, or v2 campaign_runs.csv.")
        ttk.Label(self, textvariable=self.status, wraplength=760).grid(
            row=form_end+2, column=0, columnspan=2, sticky="w", pady=10)
        columns = ("Run", "Injected", "Detected", "Plant Manifestation", "Safe State",
                   "Detection Latency (ms)", "Propagation Depth")
        self.table = ttk.Treeview(self, columns=columns, show="headings", height=7)
        for column in columns:
            self.table.heading(column, text=column)
            self.table.column(column, width=145 if column == "Run" else 115, minwidth=75)
        self.table.grid(row=form_end+3, column=0, columnspan=2, sticky="nsew")
        scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.table.xview)
        scrollbar.grid(row=form_end+4, column=0, columnspan=2, sticky="ew")
        self.table.configure(xscrollcommand=scrollbar.set)
        ttk.Label(self, text=(
            "N/A means unavailable or not reached. Plant manifestation uses a 0.01 °C "
            "difference from the fault-free reference. Safe State means applied protective "
            "mode; it does not establish hazard containment."), wraplength=760, justify="left").grid(
                row=form_end+5, column=0, columnspan=2, sticky="w", pady=12)

        self.loaded_summaries = []
        self.result_fields = {}
        cards = ttk.Frame(self)
        cards.grid(row=form_end+6, column=0, columnspan=2, sticky="ew", pady=10)
        for index, (label, key) in enumerate((
            ("Detection", "detected"), ("Plant Manifestation", "plant_manifestation"),
            ("Hazard Entered", "hazard_entered"), ("Safe State", "safe_state_reached"),
            ("Containment", "containment_success"), ("FTTI Met", "ftti_met"),
            ("Silent Corruption", "silent_corruption"), ("Unsafe Exposure (ms)", "critical_exposure_time_ms"),
            ("Propagation Depth", "propagation_depth"),
        )):
            variable = tk.StringVar(self, value="N/A")
            self.result_fields[key] = variable
            box = ttk.LabelFrame(cards, text=label, padding=8)
            box.grid(row=index//3, column=index%3, sticky="ew", padx=4, pady=4)
            ttk.Label(box, textvariable=variable).pack(anchor="w")
            cards.columnconfigure(index%3, weight=1)
        self.timeline = ttk.Treeview(self, columns=("stage", "timestamp", "latency", "reached"), show="headings", height=11)
        for column, label in (("stage", "Stage"), ("timestamp", "Timestamp (ms)"),
                              ("latency", "From injection (ms)"), ("reached", "Reached / N/A")):
            self.timeline.heading(column, text=label)
        self.timeline.grid(row=form_end+7, column=0, columnspan=2, sticky="ew", pady=10)
        self.table.bind("<<TreeviewSelect>>", self._selection_changed)

    def _layer_changed(self, _event: object = None) -> None:
        layer = self.variables["Fault Layer"].get()
        if MODEL_TARGETS[self.variables["Fault Model"].get()][0] != layer:
            self.variables["Fault Model"].set(next(m for m, pair in MODEL_TARGETS.items() if pair[0] == layer))
        self._model_changed()

    def _model_changed(self, _event: object = None) -> None:
        model = self.variables["Fault Model"].get()
        behavior = self.variables["Behavior"].get()
        layer, target = MODEL_TARGETS[model]
        self.variables["Fault Layer"].set(layer)
        self.variables["Fault Target"].set(target)
        self.inputs["Fault Target"].configure(values=(target,))
        active = {
            "Bit Index": layer == "memory", "Stuck Polarity": model == "stuck_bit",
            "Intermittent ON (ms)": behavior == "intermittent",
            "Intermittent OFF (ms)": behavior == "intermittent",
            "Communication Delay (ms)": model == "delayed_update",
            "Drop Count": model == "dropped_update", "Drop Every N Updates": model == "dropped_update",
            "Replay Age (ms)": model == "replayed_sample", "Task Delay (ms)": model == "task_delay",
            "Duration (ms)": behavior != "permanent" and not (model == "deadline_miss" and behavior == "transient"),
        }
        for key, enabled in active.items():
            self.inputs[key].configure(state=("readonly" if key == "Stuck Polarity" else "normal") if enabled else "disabled")
        if model == "deadline_miss" and behavior == "transient":
            self.variables["Duration (ms)"].set("100")

    def _selection_changed(self, _event=None):
        selection = self.table.selection()
        if not selection:
            return
        row = self.loaded_summaries[int(selection[0])]
        for key, variable in self.result_fields.items():
            variable.set("N/A" if row.get(key) in (None, "") else str(row[key]))
        self.timeline.delete(*self.timeline.get_children())
        injection = row.get("fault_injection_ms")
        for key in (*STAGES, "hazard_entry_ms", "hazard_exit_ms", "containment_time_ms"):
            value = row.get(key)
            reached = value not in (None, "", "-1")
            latency = int(value)-int(injection) if reached and injection not in (None, "") else None
            label = key.replace("propagation_", "").replace("_ms", "").replace("_", " ")
            self.timeline.insert("", "end", values=(label, value if reached else "N/A",
                latency if latency is not None and latency >= 0 else "N/A", "reached" if reached else "N/A"))

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
                behavior=self.variables["Behavior"].get(),
                intermittent_on_ms=int(self.variables["Intermittent ON (ms)"].get()),
                intermittent_off_ms=int(self.variables["Intermittent OFF (ms)"].get()),
                stuck_polarity=int(self.variables["Stuck Polarity"].get()),
                communication_delay_ms=int(self.variables["Communication Delay (ms)"].get()),
                drop_count=int(self.variables["Drop Count"].get()),
                drop_every_n_updates=int(self.variables["Drop Every N Updates"].get()),
                replay_age_ms=int(self.variables["Replay Age (ms)"].get()),
                task_delay_ms=int(self.variables["Task Delay (ms)"].get()),
            )
        except ValueError as exc:
            messagebox.showerror("Invalid cross-layer configuration", str(exc), parent=self)
            return
        options += ["--hazard-monitor", "on", "--ftti-ms", self.variables["FTTI (ms)"].get(),
                    "--hazard-warning-c", self.variables["Warning Threshold (°C)"].get(),
                    "--hazard-critical-c", self.variables["Critical Threshold (°C)"].get(),
                    "--max-critical-exposure-ms", self.variables["Max Critical Exposure (ms)"].get()]
        path = DEFAULT_CAMPAIGN_DIR / "gui_single" / "single_experiment.csv"

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
                 "--seed", seed, "--output-dir", str(DEFAULT_CAMPAIGN_DIR / "v1_compatibility_study")], cwd=PROJECT_ROOT, capture_output=True, text=True)
            if completed.returncode:
                raise RuntimeError(completed.stderr or completed.stdout)
            return DEFAULT_CAMPAIGN_DIR / "v1_compatibility_study" / "cross_layer_run_summary.csv"

        self._run("Running five-case cross-layer study…", task)

    def run_campaign(self):
        selected = filedialog.askopenfilename(parent=self, initialdir=DEFAULT_STUDY.parent,
            initialfile=DEFAULT_STUDY.name, filetypes=(("YAML study", "*.yaml *.yml"), ("JSON study", "*.json")))
        if not selected:
            return
        def task():
            completed = subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts/run_cross_layer_campaign.py"),
                selected], cwd=PROJECT_ROOT, capture_output=True, text=True)
            if completed.returncode:
                raise RuntimeError(completed.stderr or completed.stdout)
            return DEFAULT_CAMPAIGN_DIR / "campaign_runs.csv"
        self._run("Running configured cross-layer campaign…", task)

    def load_campaign_results(self):
        selected = filedialog.askopenfilename(parent=self, initialdir=DEFAULT_CAMPAIGN_DIR,
            initialfile="campaign_runs.csv", filetypes=(("Campaign CSV", "*.csv"),))
        if selected:
            self.load_results(Path(selected))

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
            self.loaded_summaries = summaries
            for index, summary in enumerate(summaries):
                values = ["N/A" if summary.get(key) in (None, "") else summary[key] for key in keys]
                self.table.insert("", "end", iid=str(index), values=values)
            if summaries:
                self.table.selection_set("0")
                self._selection_changed()
            self.status.set(f"Loaded {path}")
        except (OSError, ValueError) as exc:
            self.status.set(f"Load failed: {exc}")
            messagebox.showerror("Cross-Layer Safety", str(exc), parent=self)
