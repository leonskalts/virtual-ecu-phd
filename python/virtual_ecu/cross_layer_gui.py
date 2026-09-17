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
from .cross_layer_analysis_gui import ScientificAnalysisPanel
from .runtime_safety_gui import RuntimeSafetyPanel
from .validation_v5_gui import ValidationV5Panel
from .final_validation_gui import FinalValidationPanel
from .runtime_safety_study import runtime_summary
from .gui_design import THEME_COLORS, THEME_FONTS, Tooltip, help_for, section, action_button, StatusBanner
from .clo_dsf_gui import CloEvidenceView, LABEL as CLO_LABEL, run_experimental
from .cross_layer_ui import (DEFAULTS, UI_MODELS, LAYER_LABELS, CONTRACT, behaviors,
                             visible_fields, backend_request, interpretation, propagation_states)

DEFAULT_RUNTIME_DIR = PROJECT_ROOT / "results/cross_layer_safety_v6_1/runtime"


class CrossLayerSafetyPanel(ttk.Frame):
    def __init__(self, parent: tk.Widget, background_task: Callable, final_parent=None) -> None:
        super().__init__(parent, padding=12)
        self.background_task = background_task
        self.columnconfigure(0, weight=1)
        self.variables = {name: tk.StringVar(self, value=value) for name, value in DEFAULTS.items()}
        self.mode = tk.StringVar(self, value="Guided")
        self.contract_open = tk.BooleanVar(self, value=False)
        self.inputs, self.field_rows = {}, {}
        heading = section(self, "Cross-Layer Safety", 0)
        ttk.Label(heading, text="Configure one fault, run the experiment, then inspect its observed effects.", style="Help.TLabel").grid(row=0, column=0, sticky="w")
        modes = ttk.Frame(heading); modes.grid(row=1, column=0, sticky="w", pady=(8,0))
        for i, name in enumerate(("Guided", "Advanced")):
            ttk.Radiobutton(modes, text=name, value=name, variable=self.mode, command=self._refresh_fields).grid(row=0,column=i,padx=(0,18))
        self.mode_note = ttk.Label(heading, style="Help.TLabel", wraplength=740)
        self.mode_note.grid(row=2,column=0,sticky="w",pady=(6,0))
        self.quick_run=action_button(heading,"Run Experiment",self.run_single)
        self.quick_run.grid(row=1,column=1,rowspan=2,sticky="e",padx=8)
        selection = section(self, "1–3  •  Choose the fault", 1)
        for i in range(3): selection.columnconfigure(i, weight=1, uniform="step")
        choices = {"Fault Layer": tuple(LAYER_LABELS.values()), "Fault Model": tuple(MODEL_TARGETS),
                   "Behavior": behaviors("bit_flip"), "Fault Target": ("control_target_register",),
                   "Stuck Polarity": ("0", "1"), "Timing Monitor": ("Disabled", "Observe Only", "Protective Action"),
                   "Communication Safety Response": ("Observe Only", "Protective Action")}
        self.experimental_detector = tk.StringVar(self, value="Hybrid Adaptive Kalman")
        self.layer_choice = tk.StringVar(self, value="Memory")
        for i, (name, title) in enumerate((("Fault Layer", "Step 1 · Fault layer"), ("Fault Model", "Step 2 · Fault model"), ("Behavior", "Step 3 · Behavior"))):
            cell = ttk.Frame(selection);cell.grid(row=0,column=i,sticky="ew",padx=(0,8));cell.columnconfigure(0,weight=1)
            ttk.Label(cell,text=title).grid(row=0,column=0,sticky="w",pady=(0,5))
            variable = self.layer_choice if name == "Fault Layer" else self.variables[name]
            values = tuple(LAYER_LABELS) if name == "Fault Layer" else choices[name]
            widget=ttk.Combobox(cell,textvariable=variable,values=values,state="readonly",width=18)
            widget.grid(row=1,column=0,sticky="ew");self.inputs[name]=widget
        self.inputs["Fault Layer"].bind("<<ComboboxSelected>>", self._layer_selected)
        self.inputs["Fault Model"].bind("<<ComboboxSelected>>", self._model_changed)
        self.inputs["Behavior"].bind("<<ComboboxSelected>>", self._behavior_changed)
        parameters = section(self, "Step 4 · Configure relevant parameters", 2)
        self.parameter_note = ttk.Label(parameters,style="Help.TLabel",wraplength=740)
        self.parameter_note.grid(row=0,column=0,sticky="w",pady=(0,8))
        parameter_grid=ttk.Frame(parameters);parameter_grid.grid(row=1,column=0,sticky="ew")
        for c in range(2):parameter_grid.columnconfigure(c,weight=1,uniform="parameter")
        monitoring=ttk.LabelFrame(parameters,text="Monitoring",padding=8)
        monitoring.grid(row=2,column=0,sticky="ew",pady=(10,0))
        self.monitoring_grid=monitoring
        for c in range(2):monitoring.columnconfigure(c,weight=1,uniform="monitoring")
        contract = section(self, "Advanced Safety Contract", 3)
        ttk.Checkbutton(contract,text="Expand contract in Guided mode",variable=self.contract_open,command=self._refresh_fields).grid(row=0,column=0,sticky="w")
        ttk.Label(contract,text="These values use the frozen research defaults. Change them only for controlled advanced studies.",style="Help.TLabel",wraplength=740).grid(row=1,column=0,sticky="w",pady=5)
        self.contract_grid=ttk.Frame(contract);self.contract_grid.grid(row=2,column=0,sticky="ew")
        for c in range(2):self.contract_grid.columnconfigure(c,weight=1,uniform="contract")
        for name, variable in self.variables.items():
            if name in ("Fault Layer","Fault Model","Behavior"):continue
            owner=(self.contract_grid if name in CONTRACT else self.monitoring_grid if name in ("Timing Monitor","Communication Safety Response") else parameter_grid)
            cell=ttk.Frame(owner,padding=(0,3,12,3));cell.columnconfigure(1,weight=1)
            label=ttk.Label(cell,text=name,wraplength=145,width=21)
            label.grid(row=0,column=0,sticky="w",padx=(0,8))
            widget=ttk.Combobox(cell,textvariable=variable,values=choices[name],state="readonly",width=18) if name in choices else ttk.Entry(cell,textvariable=variable,width=18)
            widget.grid(row=0,column=1,sticky="ew")
            self.field_rows[name]=cell;self.inputs[name]=widget
            note=help_for(name)
            if note:Tooltip(label,note);Tooltip(widget,note)
        self.detector_row=ttk.Frame(parameters)
        self.detector_row.grid(row=3,column=0,sticky="ew",pady=6)
        ttk.Label(self.detector_row,text="Experimental / Development Detector").pack(side="left",padx=(0,8))
        ttk.Combobox(self.detector_row,textvariable=self.experimental_detector,
                     values=("Hybrid Adaptive Kalman",CLO_LABEL),state="readonly",width=30).pack(side="left")
        self.parameter_grid=parameter_grid
        self.helper=ttk.Label(self,text="100 ms ticks • 120 s default profile • Hybrid Adaptive Kalman, observe-only detector action. Monitor response controls are independent. Permanent faults persist to the end.",style="Help.TLabel",wraplength=800)
        self.helper.grid(row=4,column=0,sticky="ew",pady=(0,8))
        self.experimental_detector.trace_add("write",lambda *_:self._refresh_fields())
        bar=section(self,"Run or load evidence",5)
        self.buttons=[]
        for index,(label,command) in enumerate((
            ("Run Experiment",self.run_single),("Run Cross-Layer Study",self.run_study),("Load Results",self.load_results),
            ("Run Campaign",self.run_campaign),("Load Campaign Results",self.load_campaign_results),
            ("Load v3 Analysis",self.load_v3_analysis),("Load v4 Runtime Safety",self.load_v4_results),("Load V5 Validation",self.load_v5_results))):
            button=action_button(bar,label,command);button.grid(row=index//3,column=index%3,sticky="ew",padx=4,pady=4)
            bar.columnconfigure(index%3,weight=1);self.buttons.append(button)
        self.buttons.append(self.quick_run)
        self.status=tk.StringVar(self,value="Ready · Configure a single fault or load existing evidence.")
        StatusBanner(self,self.status).grid(row=6,column=0,sticky="ew",pady=8)
        self.empty=section(self,"No experiment loaded",7)
        ttk.Label(self.empty,text='Configure a fault above and select Run Experiment, or load an existing validation result.',wraplength=760).grid(row=0,column=0,columnspan=3,sticky="w",pady=(0,8))
        for i,(label,command) in enumerate((("Run Example",self.run_single),("Load V5 Validation",self.load_v5_results),("Load Latest Results",self.load_latest))):
            button=action_button(self.empty,label,command);button.grid(row=1,column=i,padx=4,sticky="ew");self.buttons.append(button)
        self.results=section(self,"Experiment results",8)
        self.results.grid_remove()
        self.loaded_summaries=[];self.result_fields={}
        cards=ttk.Frame(self.results);cards.grid(row=0,column=0,sticky="ew")
        for index,(label,key) in enumerate((("Injected Fault","fault_model"),("Detected","detected"),("Detection Latency (ms)","cross_layer_detection_latency_ms"),
            ("Plant Manifestation","plant_manifestation"),("Hazard Entered","hazard_entered"),("Safe State","safe_state_reached"),("Containment","containment_success"),("Propagation Depth","propagation_depth"),
            ("FTTI Met","ftti_met"),("Silent Corruption","silent_corruption"),("Critical Exposure (ms)","critical_exposure_time_ms"))):
            var=tk.StringVar(self,value="N/A");self.result_fields[key]=var
            card=ttk.LabelFrame(cards,text=label,padding=8);card.grid(row=index//4,column=index%4,sticky="nsew",padx=3,pady=4);cards.columnconfigure(index%4,weight=1,uniform="metric")
            ttk.Label(card,textvariable=var,wraplength=175).pack(anchor="w")
            if help_for(label):Tooltip(card,help_for(label))
        self.interpretation=tk.StringVar(self)
        ttk.Label(self.results,text="Experiment interpretation",font=THEME_FONTS["section_title"]).grid(row=1,column=0,sticky="w",pady=(12,4))
        ttk.Label(self.results,textvariable=self.interpretation,wraplength=800).grid(row=2,column=0,sticky="ew")
        self.path_summary=ttk.Frame(self.results);self.path_summary.grid(row=3,column=0,sticky="ew",pady=12)
        ttk.Label(self.results,text="Visual path: reached / N/A (unavailable or not reached). Exact timestamps remain in the table below.",style="Help.TLabel",wraplength=800).grid(row=4,column=0,sticky="w")
        columns=("Run","Injected","Detected","Plant Manifestation","Safe State","Detection Latency (ms)","Propagation Depth")
        self.table=ttk.Treeview(self.results,columns=columns,show="headings",height=5)
        for column in columns:self.table.heading(column,text=column);self.table.column(column,width=145,minwidth=85)
        self.table.grid(row=5,column=0,sticky="ew",pady=(10,0))
        scrollbar=ttk.Scrollbar(self.results,orient="horizontal",command=self.table.xview);scrollbar.grid(row=6,column=0,sticky="ew");self.table.configure(xscrollcommand=scrollbar.set)
        self.timeline=ttk.Treeview(self.results,columns=("stage","timestamp","latency","reached"),show="headings",height=12)
        for column,label in (("stage","Stage"),("timestamp","Timestamp (ms)"),("latency","From injection (ms)"),("reached","Reached / N/A")):
            self.timeline.heading(column,text=label);self.timeline.column(column,width=180,minwidth=80)
        self.timeline.grid(row=7,column=0,sticky="ew",pady=10)
        self.table.bind("<<TreeviewSelect>>",self._selection_changed)
        self.analysis_panel=ScientificAnalysisPanel(self);self.analysis_panel.grid(row=9,column=0,sticky="ew",pady=10);self.analysis_panel.grid_remove()
        self.runtime_panel=RuntimeSafetyPanel(self);self.runtime_panel.grid(row=10,column=0,sticky="ew",pady=10);self.runtime_panel.grid_remove()
        self.validation_panel=ValidationV5Panel(self);self.validation_panel.grid(row=11,column=0,sticky="ew",pady=10);self.validation_panel.grid_remove()
        self.clo_evidence=CloEvidenceView(self)
        self.clo_evidence.grid(row=13,column=0,sticky="ew",pady=8)
        self.clo_evidence.grid_remove()
        self.final_panel=FinalValidationPanel(final_parent if final_parent is not None else self,self.background_task)
        self.final_panel.grid(row=0 if final_parent is not None else 12,column=0,sticky="ew",pady=10)
        self._refresh_fields()

    def values(self):
        return {name:variable.get() for name,variable in self.variables.items()}

    def set_mode(self, mode):
        if mode not in ("Guided","Advanced"):raise ValueError(mode)
        self.mode.set(mode)
        self._refresh_fields()

    def set_presentation_mode(self, enabled):
        self.helper.grid_remove() if enabled else self.helper.grid()

    def _refresh_fields(self):
        visible=visible_fields(self.values(),self.mode.get(),self.contract_open.get())
        self.detector_row.grid() if self.mode.get()=="Advanced" else self.detector_row.grid_remove()
        self.helper.configure(text="100 ms ticks · 120 s profile · "+self.experimental_detector.get()+
                              ", observe-only detector action. Monitor response controls are independent.")
        counts={self.parameter_grid:0,self.contract_grid:0,self.monitoring_grid:0}
        for name,cell in self.field_rows.items():
            cell.grid_remove()
            if name in visible:
                owner=cell.master;index=counts[owner];counts[owner]+=1
                cell.grid(row=index//2,column=index%2,sticky="ew")
        model=self.variables["Fault Model"].get()
        self.inputs["Fault Model"].configure(values=tuple(m for m,pair in UI_MODELS.items() if pair[0]==self.variables["Fault Layer"].get()))
        self.inputs["Behavior"].configure(values=behaviors(model))
        self.mode_note.configure(text="Guided: relevant fault parameters and monitoring modes." if self.mode.get()=="Guided" else "Advanced: relevant parameters, deterministic seed and all safety contract values.")
        self.parameter_note.configure(text="Single transient deadline miss uses one 100 ms tick." if model=="deadline_miss" and self.variables["Behavior"].get()=="transient" else "Only fields used by this fault are shown. Switching visual modes preserves every value.")

    def _layer_selected(self,event=None):
        self.variables["Fault Layer"].set(LAYER_LABELS[self.layer_choice.get()])
        self._layer_changed()

    def _behavior_changed(self,event=None):
        self._model_changed()

    def load_latest(self):
        paths=list(DEFAULT_RUNTIME_DIR.rglob("single_experiment.csv"))
        if paths:self.load_results(max(paths,key=lambda path:path.stat().st_mtime))
        else:self.status.set("No Results · Run an experiment or use Load Results to select a saved CSV.")

    def load_v5_results(self, path=None):
        self.validation_panel.grid()
        self.validation_panel.load(path)
        self.update_idletasks()
        ancestor = self.master
        while ancestor is not None:
            if isinstance(ancestor, tk.Canvas):
                ancestor.yview_moveto(1.0)
                break
            ancestor = ancestor.master

    def load_v4_results(self, path=None):
        self.runtime_panel.grid()
        self.runtime_panel.load(path)
        self.status.set(self.runtime_panel.status.get())
        if self.runtime_panel.loaded_tables:
            self.update_idletasks()
            ancestor = self.master
            while ancestor is not None:
                if isinstance(ancestor, tk.Canvas):
                    ancestor.yview_moveto(1.0)
                    break
                ancestor = ancestor.master

    def load_v3_analysis(self, path=None):
        self.analysis_panel.grid()
        self.analysis_panel.load(path)
        self.status.set(self.analysis_panel.status.get())
        if self.analysis_panel.loaded_tables:
            self.update_idletasks()
            ancestor = self.master
            while ancestor is not None:
                if isinstance(ancestor, tk.Canvas):
                    ancestor.yview_moveto(1.0)
                    break
                ancestor = ancestor.master

    def _layer_changed(self, _event=None):
        layer=self.variables["Fault Layer"].get()
        if UI_MODELS[self.variables["Fault Model"].get()][0] != layer:
            self.variables["Fault Model"].set(next(m for m,pair in UI_MODELS.items() if pair[0]==layer))
        self._model_changed()

    def _model_changed(self, _event=None):
        model=self.variables["Fault Model"].get()
        layer,target=UI_MODELS[model]
        self.variables["Fault Layer"].set(layer)
        self.layer_choice.set(next(label for label,value in LAYER_LABELS.items() if value==layer))
        self.variables["Fault Target"].set(target)
        self.inputs["Fault Target"].configure(values=(target,))
        if self.variables["Behavior"].get() not in behaviors(model):self.variables["Behavior"].set("transient")
        if model=="deadline_miss" and self.variables["Behavior"].get()=="transient":self.variables["Duration (ms)"].set("100")
        self._refresh_fields()

    def _selection_changed(self, _event=None):
        selection = self.table.selection()
        if not selection:
            return
        row = self.loaded_summaries[int(selection[0])]
        self.empty.grid_remove()
        self.results.grid()
        self.interpretation.set(interpretation(row))
        for child in self.path_summary.winfo_children():child.destroy()
        for i,(label,state,timestamp) in enumerate(propagation_states(row)):
            cell=ttk.LabelFrame(self.path_summary,text=label,padding=8)
            cell.grid(row=i//3,column=i%3,sticky="ew",padx=3,pady=3)
            self.path_summary.columnconfigure(i%3,weight=1)
            ttk.Label(cell,text=f"{state} · {timestamp}" + (" ms" if timestamp!="N/A" else ""),foreground=THEME_COLORS["primary"] if state=="reached" else THEME_COLORS["text_secondary"]).pack(anchor="w")
        self.runtime_panel.show_run(row)
        for key, variable in self.result_fields.items():
            variable.set("N/A" if row.get(key) in (None, "") else str(row[key]))
        self.timeline.delete(*self.timeline.get_children())
        injection = row.get("fault_injection_ms")
        for key in (*STAGES, "hazard_entry_ms", "hazard_exit_ms", "containment_time_ms"):
            value = row.get(key)
            reached = value not in (None, "", "-1", -1, "N/A")
            latency = int(value)-int(injection) if reached and injection not in (None, "", "-1", -1, "N/A") else None
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
            positional, options = backend_request(self.values())
        except ValueError as exc:
            messagebox.showerror("Invalid cross-layer configuration", str(exc), parent=self)
            return
        experimental = self.experimental_detector.get() == CLO_LABEL
        path = (PROJECT_ROOT / "results/cross_layer_safety_v7_dev/gui_runtime" if experimental else DEFAULT_RUNTIME_DIR / "gui_single") / "single_experiment.csv"

        def task() -> Path:
            completed = subprocess.run(["make"], cwd=PROJECT_ROOT, capture_output=True, text=True)
            if completed.returncode:
                raise RuntimeError(completed.stderr or completed.stdout)
            if experimental:
                run_experimental(path, positional, options)
            else:
                run_experiment(path, positional, [*options, "--detector", "hybrid_adaptive_kalman",
                                                   "--detector-action", "observe_only"])
            return path

        self._run("Running cross-layer experiment…", task)

    def run_study(self) -> None:
        seed = self.variables["Seed"].get()

        def task() -> Path:
            completed = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "scripts" / "run_cross_layer_safety_study.py"),
                 "--seed", seed, "--output-dir", str(DEFAULT_RUNTIME_DIR / "v1_compatibility_study")], cwd=PROJECT_ROOT, capture_output=True, text=True)
            if completed.returncode:
                raise RuntimeError(completed.stderr or completed.stdout)
            return DEFAULT_RUNTIME_DIR / "v1_compatibility_study" / "cross_layer_run_summary.csv"

        self._run("Running five-case cross-layer study…", task)

    def run_campaign(self):
        selected = filedialog.askopenfilename(parent=self, initialdir=DEFAULT_STUDY.parent,
            initialfile=DEFAULT_STUDY.name, filetypes=(("YAML study", "*.yaml *.yml"), ("JSON study", "*.json")))
        if not selected:
            return
        def task():
            completed = subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts/run_cross_layer_campaign.py"),
                selected, "--output-dir", str(DEFAULT_RUNTIME_DIR / "legacy_campaign")], cwd=PROJECT_ROOT, capture_output=True, text=True)
            if completed.returncode:
                raise RuntimeError(completed.stderr or completed.stdout)
            return DEFAULT_RUNTIME_DIR / "legacy_campaign" / "campaign_runs.csv"
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
            sidecar = Path(str(path)+".clo_dsf.csv")
            self.clo_evidence.grid_remove()
            if sidecar.exists():
                self.clo_evidence.load(sidecar)
                self.clo_evidence.grid()
            if "telemetry_available" in rows[0] and "run_id" in rows[0]:
                summaries = rows
            elif "time_ms" in rows[0]:
                summaries = [{"run_id": path.stem, **summarize_rows(rows), **runtime_summary(rows)}]
                if rows[-1].get("runtime_safety_enabled") == "1":
                    self.runtime_panel.grid()
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
