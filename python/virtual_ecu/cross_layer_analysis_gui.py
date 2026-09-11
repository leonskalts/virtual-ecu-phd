"""Compact, read-only v3 analysis view embedded in the existing safety page."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .cross_layer_analysis import DEFAULT_OUTPUT
from .cross_layer_safety import read_rows

CARDS = (
    ('Overall Detection Coverage','overall_detection_coverage'),
    ('Detection Given Plant Propagation','detection_coverage_given_plant_propagation'),
    ('Detection Given Hazard','detection_coverage_given_hazard'),
    ('Silent Plant Propagation','silent_plant_propagation_rate'),
    ('Silent Hazard','silent_hazard_rate'),
    ('Hazard Rate','hazard_rate'),
    ('Hardened Containment Rate','hardened_containment_rate'),
    ('Manifestation-Based FTTI Success','manifestation_based_experimental_ftti'),
)
TABLES = {
    'Silent Corruption Severity': ('silent_corruption_grouped_summary.csv', ('dimension','group','category','count','denominator','percent')),
    'Timing Miss Analysis': ('timing_fault_analysis.csv', ('run_id','detected','timing_consequence','timing_metadata_only','max_physical_deviation_c','miss_reason')),
    'Fault Observability Matrix': ('observability_matrix.csv', None),
    'Safety Severity': ('safety_severity_summary.csv', ('dimension','group','category','count','denominator','percent')),
}


class ScientificAnalysisPanel(ttk.LabelFrame):
    def __init__(self,parent):
        super().__init__(parent,text='Scientific Analysis (v3)',padding=8)
        self.columnconfigure(0,weight=1)
        self.fields={}
        cards=ttk.Frame(self);cards.grid(row=0,column=0,sticky='ew')
        for index,(label,key) in enumerate(CARDS):
            variable=tk.StringVar(self,value='N/A');self.fields[key]=variable
            box=ttk.LabelFrame(cards,text=label,padding=6)
            box.grid(row=index//2,column=index%2,sticky='ew',padx=3,pady=3)
            ttk.Label(box,textvariable=variable).pack(anchor='w')
            cards.columnconfigure(index%2,weight=1)
        ttk.Label(self,text='Rates show numerator / eligible runs. Silent plant is conditional on plant propagation; silent hazard is conditional on hazard. Experimental FTTI, not a certified safety limit.',wraplength=760).grid(row=1,column=0,sticky='w',pady=6)
        self.selection=tk.StringVar(self,value=next(iter(TABLES)))
        selector=ttk.Combobox(self,textvariable=self.selection,values=tuple(TABLES),state='readonly')
        selector.grid(row=2,column=0,sticky='w',pady=5)
        selector.bind('<<ComboboxSelected>>',self.show_table)
        self.table=ttk.Treeview(self,show='headings',height=6)
        self.table.grid(row=3,column=0,sticky='ew')
        horizontal=ttk.Scrollbar(self,orient='horizontal',command=self.table.xview)
        horizontal.grid(row=4,column=0,sticky='ew')
        vertical=ttk.Scrollbar(self,orient='vertical',command=self.table.yview)
        vertical.grid(row=3,column=1,sticky='ns')
        self.table.configure(xscrollcommand=horizontal.set,yscrollcommand=vertical.set)
        self.status=tk.StringVar(self,value='Load a v3 evidence directory to inspect scientific outcomes.')
        ttk.Label(self,textvariable=self.status,wraplength=760).grid(row=5,column=0,sticky='w',pady=5)
        self.loaded_tables={}

    def load(self,path=None):
        if path is None:
            selected=filedialog.askdirectory(parent=self,initialdir=DEFAULT_OUTPUT,title='Load v3 Analysis')
            if not selected:return
            path=Path(selected)
        try:
            path=Path(path)
            metrics=read_rows(path/'scientific_metric_summary.csv')
            overall={r['metric']:r for r in metrics if r['dimension']=='overall'}
            tables={name:read_rows(path/filename) for name,(filename,_) in TABLES.items()}
            values={}
            for _,key in CARDS:
                row=overall.get(key)
                if row is None:raise ValueError(f'Missing v3 metric: {key}')
                denominator=int(row['denominator'])
                values[key]=(f"{float(row['percent']):.2f}% ({row['numerator']}/{denominator})"
                             if denominator and row['percent'] else 'N/A (0 eligible)')
            self.loaded_tables=tables
            for key,value in values.items():self.fields[key].set(value)
            self.show_table()
            self.status.set(f'Loaded v3 analysis: {path}')
        except (OSError,ValueError,KeyError) as exc:
            self.status.set(f'Analysis load failed: {exc}')
            messagebox.showerror('Scientific Analysis',str(exc),parent=self)

    def show_table(self,_event=None):
        name=self.selection.get()
        rows=self.loaded_tables.get(name,[])
        columns=TABLES[name][1] or (tuple(rows[0]) if rows else ('fault_model',))
        self.table.delete(*self.table.get_children())
        self.table.configure(columns=columns)
        for key in columns:
            self.table.heading(key,text=key.replace('_',' '))
            self.table.column(key,width=190 if key in ('run_id','miss_reason') else 150,minwidth=90)
        for row in rows:
            self.table.insert('','end',values=['N/A' if row.get(k) in ('',None) else row[k] for k in columns])
