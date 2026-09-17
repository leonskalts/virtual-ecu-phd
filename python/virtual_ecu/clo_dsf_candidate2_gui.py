"""Additive Candidate 2 panels. Candidate 1 modules and execution stay unchanged."""
from __future__ import annotations
import csv,gzip,subprocess,tkinter as tk
from pathlib import Path
from tkinter import ttk,filedialog,messagebox
ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'results/cross_layer_safety_v7_1_dev'
LABEL='CLO-DSF Candidate 2 (Experimental)'
C1_LABEL='CLO-DSF Candidate 1 (Frozen)'
ANOMALY=('detector_state','anomaly_belief','anomaly_plausibility','anomaly_decision_score','anomaly_ignorance','detection_conflict','alarm_timestamp_ms')
ORIGIN=('estimated_origin','origin_score','origin_belief','origin_plausibility','origin_margin','origin_ignorance','localization_conflict','propagation_support','localization_timestamp_ms')
def read_evidence(path):
 path=Path(path)
 with (gzip.open if path.suffix=='.gz' else open)(path,'rt',newline='') as f:rows=list(csv.DictReader(f))
 keys=('time_ms','alarm','localization_valid',*ANOMALY,*ORIGIN)
 if not rows or any(k not in rows[0] for k in keys):raise ValueError('Select a Candidate 2 runtime evidence sidecar')
 return [{k:r[k] for k in keys} for r in rows]
def run_experimental(path,positional,options):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 cfg=OUTPUT/'selected_config.cfg'
 if not cfg.exists():raise ValueError('Run the Candidate 2 development selection before using its GUI operating point')
 cmd=[str(ROOT/'virtual_ecu_v7_1'),str(path),*positional,*options,'--detector','clo_dsf_candidate2','--detector-action','observe_only','--c2-config',str(cfg)]
 p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return path
class Candidate2EvidenceView(ttk.LabelFrame):
 def __init__(self,parent):
  super().__init__(parent,text=LABEL+' · Runtime observations',padding=8);self.rows=[];self.values={}
  ttk.Label(self,text='CONFIRMED + UNKNOWN is valid: an anomaly can be detected before its origin is identifiable.',wraplength=780).grid(row=0,column=0,columnspan=2,sticky='w')
  self.selector=ttk.Combobox(self,state='readonly',width=20);self.selector.grid(row=1,column=0,sticky='w',pady=5);self.selector.bind('<<ComboboxSelected>>',lambda _:self.show(self.selector.current()))
  for column,(title,fields) in enumerate([('ANOMALY',ANOMALY),('ORIGIN',ORIGIN)]):
   pane=ttk.LabelFrame(self,text=title,padding=6);pane.grid(row=2,column=column,sticky='nsew',padx=4);self.columnconfigure(column,weight=1)
   for i,key in enumerate(fields):
    ttk.Label(pane,text=key.replace('_',' ').capitalize()).grid(row=i,column=0,sticky='w',padx=3)
    self.values[key]=tk.StringVar(self,value='N/A');ttk.Label(pane,textvariable=self.values[key]).grid(row=i,column=1,sticky='w',padx=8)
 def load(self,path):
  self.rows=read_evidence(path);self.selector.configure(values=[r['time_ms']+' ms' for r in self.rows]);index=next((i for i,r in enumerate(self.rows) if r['alarm']=='1'),len(self.rows)-1);self.selector.current(index);self.show(index)
 def show(self,index):
  if 0<=index<len(self.rows):
   for key,var in self.values.items():var.set(self.rows[index][key])
class Candidate2DevelopmentPanel(ttk.LabelFrame):
 def __init__(self,parent,app):
  super().__init__(parent,text='Candidate 2 · Development comparison',padding=8);self.app=app
  ttk.Label(self,text='DEVELOPMENT RESULTS — NOT FINAL HOLDOUT. Candidate 1 remains available above.',wraplength=780).grid(row=0,column=0,columnspan=2,sticky='w')
  ttk.Button(self,text='Run Candidate 2 Example',command=self.example).grid(row=1,column=0,sticky='w',pady=5)
  ttk.Button(self,text='Load Candidate 2 Development Study',command=self.load).grid(row=1,column=1,sticky='w')
  self.runtime=Candidate2EvidenceView(self);self.runtime.grid(row=2,column=0,columnspan=2,sticky='ew');self.runtime.grid_remove()
  self.table=ttk.Treeview(self,columns=('method','coverage','false','localization','accuracy','unknown'),show='headings',height=7)
  for key,title in [('method','Detector'),('coverage','Detection'),('false','Benign alarms'),('localization','Localization coverage'),('accuracy','Accuracy when localized'),('unknown','UNKNOWN')]:self.table.heading(key,text=title);self.table.column(key,width=190 if key=='method' else 140)
  self.table.grid(row=3,column=0,columnspan=2,sticky='ew');self.table.grid_remove()
  self.truth=ttk.Label(self,text='Evaluation ground truth: origin and plant effects are used only for scoring this table.',wraplength=780);self.truth.grid(row=4,column=0,columnspan=2,sticky='w');self.truth.grid_remove()
 def load(self):
  try:
   rows=list(csv.DictReader((OUTPUT/'candidate2_validation_summary.csv').open()));self.table.delete(*self.table.get_children())
   for r in rows:
    pct=lambda k:f'{float(r[k])*100:.1f}%' if r[k] else 'N/A'
    self.table.insert('','end',values=(r['method'],pct('coverage'),r['benign_false_alarms'],pct('localization_coverage'),pct('accuracy_when_localized'),pct('unknown_rate')))
   self.table.grid();self.truth.grid()
  except (OSError,ValueError) as e:messagebox.showerror('Candidate 2 development',str(e),parent=self)
 def example(self):
  def task():
   subprocess.run(['make'],cwd=ROOT,capture_output=True,check=True)
   return run_experimental(OUTPUT/'gui_runtime/example.csv',['baseline'],['--cross-layer-fault','task_delay','--fault-start-ms','32000','--fault-duration-ms','3000','--task-delay-ms','400','--fault-behavior','transient'])
  def done(path):self.runtime.load(str(path)+'.candidate2.csv');self.runtime.grid()
  self.app.run_background_task('Candidate 2 example','Running experimental observe-only detector.',task,on_success=done,on_error=lambda e:messagebox.showerror('Candidate 2',str(e),parent=self))
def install():
 """Extend the existing classes once, preserving their original method bodies."""
 from . import cross_layer_gui as cross,research_analysis_gui as research
 cls=cross.CrossLayerSafetyPanel
 if getattr(cls,'_candidate2_installed',False):return
 init,run,load=cls.__init__,cls.run_single,cls.load_results
 def init2(self,*a,**k):
  init(self,*a,**k)
  for widget in self.detector_row.winfo_children():
   if isinstance(widget,ttk.Combobox):widget.configure(values=('Hybrid Adaptive Kalman',C1_LABEL,LABEL),width=38)
  self.candidate2_evidence=Candidate2EvidenceView(self);self.candidate2_evidence.grid(row=14,column=0,sticky='ew',pady=8);self.candidate2_evidence.grid_remove()
 def run2(self):
  if self.experimental_detector.get()==C1_LABEL:
   self.experimental_detector.set(cross.CLO_LABEL)
   try:return run(self)
   finally:self.experimental_detector.set(C1_LABEL)
  if self.experimental_detector.get()!=LABEL:return run(self)
  try:positional,options=cross.backend_request(self.values())
  except ValueError as e:messagebox.showerror('Invalid cross-layer configuration',str(e),parent=self);return
  def task():
   subprocess.run(['make'],cwd=ROOT,capture_output=True,check=True)
   return run_experimental(OUTPUT/'gui_runtime/single_experiment.csv',positional,options)
  self._run('Running Candidate 2 experiment…',task)
 def load2(self,path=None):
  if path is None:
   selected=filedialog.askopenfilename(parent=self,initialdir=OUTPUT,filetypes=(('CSV results','*.csv'),))
   if not selected:return
   path=Path(selected)
  load(self,path);self.candidate2_evidence.grid_remove();sidecar=Path(str(path)+'.candidate2.csv')
  if sidecar.exists():
   try:self.candidate2_evidence.load(sidecar);self.candidate2_evidence.grid()
   except (OSError,ValueError) as e:messagebox.showerror('Candidate 2 runtime',str(e),parent=self)
 cls.__init__=init2;cls.run_single=run2;cls.load_results=load2;cls._candidate2_installed=True
 old=research.ResearchAnalysisWorkspace.__init__
 def research_init(self,*a,**k):
  old(self,*a,**k);self.candidate2_development=Candidate2DevelopmentPanel(self.headers['runtime_study'],self.app);self.candidate2_development.grid(row=4,column=0,sticky='ew',pady=10)
 research.ResearchAnalysisWorkspace.__init__=research_init
