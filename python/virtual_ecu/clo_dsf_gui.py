"""Additive v7 views: runtime sidecar and clearly separate development scoring."""
from __future__ import annotations
import csv
import gzip
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'results/cross_layer_safety_v7_dev'
LABEL='CLO-DSF (Experimental)'
RUNTIME_FIELDS=(('Detector State','detector_state'),('Estimated Fault Origin','estimated_origin'),
                ('Origin Decision Score','origin_score'),('Ignorance','ignorance_mass'),
                ('Evidence Conflict','conflict_mass'),('Propagation Support','propagation_support'))


def read_evidence(path):
    path=Path(path)
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt',newline='') as f:rows=list(csv.DictReader(f))
    if not rows or any(key not in rows[0] for _,key in RUNTIME_FIELDS):raise ValueError('Select a CLO-DSF runtime evidence sidecar')
    # Return only an explicit runtime allowlist; arbitrary CSV columns never enter this view.
    return [{key:row.get(key,'N/A') for key in ['time_ms','alarm',*[k for _,k in RUNTIME_FIELDS]]} for row in rows]


def run_experimental(path,positional,options):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    command=[str(ROOT/'virtual_ecu_v7'),str(path),*positional,*options,
             '--detector','clo_dsf','--detector-action','observe_only']
    config=OUTPUT/'selected_config.cfg'
    if config.exists():command+=['--clo-config',str(config)]
    process=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    if process.returncode:raise RuntimeError(process.stderr or process.stdout)
    return path


class CloEvidenceView(ttk.LabelFrame):
    def __init__(self,parent):
        super().__init__(parent,text='CLO-DSF (Experimental) · Runtime evidence',padding=8)
        self.rows=[];self.time=tk.StringVar(self);self.values={}
        ttk.Label(self,text='Runtime observations only · Observe-only development detector').grid(row=0,column=0,columnspan=3,sticky='w')
        self.selector=ttk.Combobox(self,textvariable=self.time,state='readonly',width=18)
        self.selector.grid(row=1,column=0,sticky='w',pady=5)
        self.selector.bind('<<ComboboxSelected>>',lambda _:self.show(self.selector.current()))
        for i,(label,key) in enumerate(RUNTIME_FIELDS):
            self.values[key]=tk.StringVar(self,value='N/A')
            card=ttk.LabelFrame(self,text=label,padding=6);card.grid(row=2+i//3,column=i%3,sticky='ew',padx=3,pady=3)
            ttk.Label(card,textvariable=self.values[key]).pack(anchor='w');self.columnconfigure(i%3,weight=1)
    def load(self,path):
        self.rows=read_evidence(path)
        self.selector.configure(values=[r['time_ms']+' ms' for r in self.rows])
        index=next((i for i,r in enumerate(self.rows) if r['alarm']=='1'),len(self.rows)-1)
        self.selector.current(index);self.show(index)
    def show(self,index):
        if 0<=index<len(self.rows):
            for key,var in self.values.items():var.set(self.rows[index][key])


class CloDevelopmentPanel(ttk.LabelFrame):
    def __init__(self,parent,app):
        super().__init__(parent,text='Experimental / Development Detector',padding=8)
        self.app=app
        self.choice=tk.StringVar(self,value='Select development detector')
        ttk.Combobox(self,textvariable=self.choice,values=(LABEL,),state='readonly',width=32).grid(row=0,column=0,sticky='w')
        ttk.Button(self,text='Run CLO-DSF Example',command=self.example).grid(row=0,column=1,padx=6)
        ttk.Button(self,text='Load Development Study',command=self.load).grid(row=0,column=2,padx=6)
        ttk.Label(self,text='DEVELOPMENT RESULTS — NOT FINAL HOLDOUT. Existing detector study defaults remain available.',wraplength=780).grid(row=1,column=0,columnspan=3,sticky='w',pady=5)
        self.runtime=CloEvidenceView(self);self.runtime.grid(row=2,column=0,columnspan=3,sticky='ew');self.runtime.grid_remove()
        self.table=ttk.Treeview(self,columns=('method','coverage','false','localization','unknown'),show='headings',height=5)
        for key,title in [('method','Detector'),('coverage','Coverage'),('false','Benign Alarms'),('localization','Localization Accuracy'),('unknown','UNKNOWN Rate')]:
            self.table.heading(key,text=title);self.table.column(key,width={'method':155,'coverage':95,'false':125,'localization':175,'unknown':110}[key])
        self.table.grid(row=3,column=0,columnspan=3,sticky='ew');self.table.grid_remove()
        self.truth=ttk.Label(self,text='Evaluation Ground Truth: origin and plant effects are used only for scoring the development table.',wraplength=780)
        self.truth.grid(row=4,column=0,columnspan=3,sticky='w',pady=5);self.truth.grid_remove()
    def load(self):
        try:
            with (OUTPUT/'clo_dsf_baseline_comparison.csv').open() as f:rows=list(csv.DictReader(f))
            self.table.delete(*self.table.get_children())
            for row in rows:
                if row['partition']!='development-validation':continue
                percent=lambda value:f'{float(value)*100:.2f}%' if value else 'N/A'
                self.table.insert('','end',values=(row['method'],percent(row['coverage']),row['benign_false_alarms'],
                                                 percent(row['localization_accuracy']),percent(row['unknown_rate'])))
            self.table.grid();self.truth.grid();self.choice.set(LABEL)
        except (OSError,ValueError) as exc:messagebox.showerror('CLO-DSF development',str(exc),parent=self)
    def example(self):
        self.choice.set(LABEL)
        path=OUTPUT/'gui_runtime/example.csv'
        def task():
            subprocess.run(['make'],cwd=ROOT,check=True,capture_output=True)
            return run_experimental(path,['baseline'],['--cross-layer-fault','task_delay','--fault-start-ms','45000','--fault-duration-ms','4000','--task-delay-ms','300','--fault-behavior','transient'])
        def done(result):
            self.runtime.load(str(result)+'.clo_dsf.csv');self.runtime.grid()
        self.app.run_background_task('CLO-DSF example','Running experimental observe-only detector.',task,on_success=done,
                                      on_error=lambda e:messagebox.showerror('CLO-DSF',str(e),parent=self))
