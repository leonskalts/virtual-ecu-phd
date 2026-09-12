"""V4 result cards and three compact study views; no simulator logic."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox

from .cross_layer_safety import read_rows
from .runtime_safety_study import DEFAULT_OUTPUT

CARDS=(('Timing Contract Violation','timing_contract_violation_observed'),
       ('Timing Monitor Alarm','timing_monitor_detected'),
       ('Existing Detector Alarm','existing_detector_alarm_observed'),
       ('First Detection Mechanism','first_detection_mechanism'),
       ('Safety Action Requested','safety_action_requested'),
       ('Safety Action Time (ms)','runtime_safety_first_action_ms'),
       ('False / Unnecessary Intervention','intervention_class'))
TABLES={
    'Timing Monitor Validation':('timing_monitor_runs.csv',('run_id','mode_id','fault_model','observe_consequence','timing_monitor_detected','timing_detection_latency_ms','intervention_class')),
    'Timing Ablation':('timing_monitor_ablation.csv',('mode_id','detected','injected_runs','false_alarms','benign_runs','plant_propagating_timing_misses','median_detection_latency_ms')),
    'Communication Safety Response':('communication_response_runs.csv',('run_id','mode_id','fault_model','detected','attributable_hazard','fixed_cohort_containment','intervention_class')),
}


class RuntimeSafetyPanel(ttk.LabelFrame):
    def __init__(self,parent):
        super().__init__(parent,text='Runtime Safety (v4)',padding=8)
        self.columnconfigure(0,weight=1)
        self.fields={};cards=ttk.Frame(self);cards.grid(row=0,column=0,sticky='ew')
        for index,(label,key) in enumerate(CARDS):
            var=tk.StringVar(self,value='N/A');self.fields[key]=var
            box=ttk.LabelFrame(cards,text=label,padding=5);box.grid(row=index//2,column=index%2,sticky='ew',padx=3,pady=3)
            ttk.Label(box,textvariable=var,wraplength=400).pack(anchor='w');cards.columnconfigure(index%2,weight=1)
        ttk.Label(self,text='Alarms and incremental policy actions are separate. Unnecessary intervention requires a matched no-action run; single-run classification is N/A.',wraplength=760).grid(row=1,column=0,sticky='w',pady=5)
        self.selection=tk.StringVar(self,value=next(iter(TABLES)))
        selector=ttk.Combobox(self,values=tuple(TABLES),textvariable=self.selection,state='readonly',width=36)
        selector.grid(row=2,column=0,sticky='w',pady=5);selector.bind('<<ComboboxSelected>>',self.show_table)
        self.table=ttk.Treeview(self,show='headings',height=6);self.table.grid(row=3,column=0,sticky='ew')
        scroll=ttk.Scrollbar(self,orient='horizontal',command=self.table.xview);scroll.grid(row=4,column=0,sticky='ew')
        vertical=ttk.Scrollbar(self,orient='vertical',command=self.table.yview);vertical.grid(row=3,column=1,sticky='ns')
        self.table.configure(xscrollcommand=scroll.set,yscrollcommand=vertical.set)
        self.table.bind('<<TreeviewSelect>>',self._selected)
        self.loaded_tables={};self.visible_rows=[]
        self.status=tk.StringVar(self,value='Load the v4 result directory, or run a single experiment with the runtime controls.')
        ttk.Label(self,textvariable=self.status,wraplength=760).grid(row=5,column=0,sticky='w',pady=5)

    def show_run(self,row):
        for key,var in self.fields.items():var.set('N/A' if row.get(key) in (None,'') else str(row[key]))

    def _selected(self,_event=None):
        selection=self.table.selection()
        if selection:self.show_run(self.visible_rows[int(selection[0])])

    def show_table(self,_event=None):
        name=self.selection.get();self.visible_rows=self.loaded_tables.get(name,[])
        columns=TABLES[name][1];self.table.delete(*self.table.get_children());self.table.configure(columns=columns)
        for key in columns:
            self.table.heading(key,text=key.replace('_',' '));self.table.column(key,width=180,minwidth=90)
        for index,row in enumerate(self.visible_rows):self.table.insert('','end',iid=str(index),values=['N/A' if row.get(k) in ('',None) else row[k] for k in columns])
        if self.visible_rows:self.table.selection_set('0');self._selected()

    def load(self,path=None):
        if path is None:
            selected=filedialog.askdirectory(parent=self,initialdir=DEFAULT_OUTPUT,title='Load v4 Runtime Safety Results')
            if not selected:return
            path=Path(selected)
        try:
            self.loaded_tables={name:read_rows(Path(path)/filename) for name,(filename,_) in TABLES.items()}
            self.show_table();self.status.set(f'Loaded runtime safety results: {path}')
        except (OSError,ValueError,KeyError) as exc:
            self.status.set(f'Load failed: {exc}');messagebox.showerror('Runtime Safety',str(exc),parent=self)
