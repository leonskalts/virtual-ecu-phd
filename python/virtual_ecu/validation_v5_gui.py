"""Compact read-only inspection of the frozen v5 evidence package."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from .cross_layer_safety import read_rows
from .validation_v5_design import OUTPUT

VIEWS={
 'Timing Holdout':('timing_holdout_summary.csv',('metric','numerator','denominator','percent','ci95_lower_percent','ci95_upper_percent','value_ms')),
 'Benign Timing':('timing_benign_summary.csv',('dimension','group','metric','numerator','denominator','percent','ci95_upper_percent')),
 'Policy Comparison':('intervention_cost_summary.csv',('study_kind','policy','run_count','hazards','critical_exposure_ms','contained','containment_eligible','unnecessary_interventions','limp_home_duration_ms_total')),
 'Recovery Horizon':('recovery_horizon_analysis.csv',('run_id','policy','anchor_kind','anchor_ms','horizon_ms','available','containment_success','stable_below_warning_latency_ms')),
 'Cross-Layer Holdout':('cross_layer_holdout_summary.csv',('dimension','group','metric','numerator','denominator','percent','ci95_lower_percent','ci95_upper_percent')),
 'Matched Stuck/Dynamic Comparison':('stuck_dynamic_matched_comparison.csv',('match_id','polarity','flip_detected','permanent_detected','intermittent_detected','flip_plant_manifestation','permanent_plant_manifestation','intermittent_plant_manifestation')),
 'Monitor Overhead':('monitor_overhead_summary.csv',('metric','value','unit','n','scope')),
}

class ValidationV5Panel(ttk.LabelFrame):
 def __init__(self,parent):
  super().__init__(parent,text='V5 Final Validation',padding=8);self.columnconfigure(0,weight=1)
  ttk.Label(self,text='Frozen rules; paired policies. Confidence intervals describe this designed matrix, not fleet reliability. Host overhead is not embedded WCET.',wraplength=760).grid(row=0,column=0,sticky='w',pady=5)
  self.selection=tk.StringVar(self,value='Timing Holdout')
  selector=ttk.Combobox(self,textvariable=self.selection,values=tuple(VIEWS),state='readonly',width=40);selector.grid(row=1,column=0,sticky='w');selector.bind('<<ComboboxSelected>>',self.show_table)
  self.table=ttk.Treeview(self,show='headings',height=9);self.table.grid(row=2,column=0,sticky='ew',pady=5)
  vertical=ttk.Scrollbar(self,orient='vertical',command=self.table.yview);vertical.grid(row=2,column=1,sticky='ns')
  horizontal=ttk.Scrollbar(self,orient='horizontal',command=self.table.xview);horizontal.grid(row=3,column=0,sticky='ew')
  self.table.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
  self.status=tk.StringVar(self,value='Load V5 Validation');ttk.Label(self,textvariable=self.status,wraplength=760).grid(row=4,column=0,sticky='w')
  self.loaded_tables={}
 def show_table(self,_event=None):
  name=self.selection.get();columns=VIEWS[name][1];self.table.delete(*self.table.get_children());self.table.configure(columns=columns)
  for c in columns:self.table.heading(c,text=c.replace('_',' '));self.table.column(c,width=180,minwidth=100)
  rows=self.loaded_tables.get(name,[])
  for i,r in enumerate(rows):self.table.insert('','end',iid=str(i),values=['N/A' if r.get(c) in ('',None) else r[c] for c in columns])
  self.status.set(f'{name}: {len(rows)} rows. Empty endpoints remain N/A.')
 def load(self,path=None):
  if path is None:
   path=filedialog.askdirectory(parent=self,initialdir=OUTPUT,title='Load V5 Validation')
   if not path:return
  try:
   self.loaded_tables={name:read_rows(Path(path)/filename) for name,(filename,_) in VIEWS.items()};self.show_table()
  except (OSError,ValueError,KeyError) as exc:messagebox.showerror('V5 Validation',str(exc),parent=self);self.status.set(str(exc))
