"""Additive final view, activated only after a scientific freeze exists."""
import csv,json,subprocess
from uuid import uuid4
from pathlib import Path
from tkinter import ttk,filedialog,messagebox
from .clo_dsf_candidate2_gui import Candidate2EvidenceView,Candidate2DevelopmentPanel,read_evidence
ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'results/cross_layer_safety_v7_2_confirmation'
LABEL='CLO-DSF (Frozen Pre-Holdout)'
def new_runtime_path(name):
 # Future exploratory GUI runs must never overwrite sealed confirmation evidence.
 return OUTPUT/'gui_runtime'/uuid4().hex/name
def path_label(mask):
 channels=['Timing','Communication','Memory/control','Sensor/control','Actuator','Plant symptom'];bits=int(mask)
 return '; '.join(channels[i]+' → '+channels[j] for i in range(6) for j in range(6) if bits&(1<<(6*i+j))) or 'None observed'
def run_final(path,positional,options):
 if not (OUTPUT/'clo_dsf_final_config.json').exists():raise ValueError('The final scientific freeze is not available')
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 subprocess.run(['make','-f','clo_dsf_final_optimized.mk'],cwd=ROOT,check=True,capture_output=True)
 optimized=ROOT/'virtual_ecu_v7_2_optimized';verified=OUTPUT/'benchmark/equivalence.json'
 use_opt=optimized.exists() and verified.exists() and json.loads(verified.read_text())['status']=='PASS'
 exe=optimized if use_opt else ROOT/'virtual_ecu_v7_2_reference'
 p=subprocess.run([str(exe),str(path),*positional,*options,'--detector','clo_dsf_final','--detector-action','observe_only','--final-config',str(OUTPUT/'final_reference.cfg')],cwd=ROOT,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return path
class FinalEvidenceView(Candidate2EvidenceView):
 def __init__(self,parent):
  super().__init__(parent);self.configure(text=LABEL+' · Runtime evidence')
  for pane in self.winfo_children():
   if isinstance(pane,ttk.LabelFrame):
    for child in pane.winfo_children():
     if isinstance(child,ttk.Label) and child.cget('text')=='Propagation support':child.configure(text='Observed evidence path')
  ttk.Label(self,text='Observed evidence path: diagnostic only — does not affect decisions.',wraplength=780).grid(row=3,column=0,columnspan=2,sticky='w',pady=6)
 def load(self,path):
  import gzip
  p=Path(path)
  with (gzip.open if p.suffix=='.gz' else open)(p,'rt',newline='') as f:raw=list(csv.DictReader(f))
  super().load(path)
  for row,original in zip(self.rows,raw):row['propagation_support']=path_label(original['observed_evidence_path'])
  self.show(self.selector.current())
class FinalDevelopmentPanel(Candidate2DevelopmentPanel):
 def __init__(self,parent,app):
  super().__init__(parent,app);self.configure(text='Frozen CLO-DSF · Development confirmation')
  for child in self.winfo_children():
   if isinstance(child,ttk.Label) and 'DEVELOPMENT RESULTS' in child.cget('text'):child.configure(text='DEVELOPMENT CONFIRMATION — NOT FINAL HOLDOUT. Historical candidates remain available above.')
   if isinstance(child,ttk.Button):child.configure(text=child.cget('text').replace('Candidate 2','Frozen CLO-DSF').replace('Development Study','Confirmation Study'))
  self.runtime.destroy();self.runtime=FinalEvidenceView(self);self.runtime.grid(row=2,column=0,columnspan=2,sticky='ew');self.runtime.grid_remove()
 def load(self):
  try:
   with (OUTPUT/'final_candidate_baseline_comparison.csv').open() as f:rows=list(csv.DictReader(f))
   self.table.delete(*self.table.get_children())
   for r in rows:
    pct=lambda k:f'{float(r[k])*100:.1f}%' if r[k] else 'N/A'
    self.table.insert('','end',values=(r['method'],pct('coverage'),r['benign_false_alarms'],pct('localization_coverage'),pct('accuracy_when_localized'),pct('unknown_rate')))
   self.table.grid();self.truth.grid()
  except (OSError,ValueError) as e:messagebox.showerror('Final CLO-DSF confirmation',str(e),parent=self)
 def example(self):
  def task():return run_final(new_runtime_path('example.csv'),['baseline'],['--cross-layer-fault','task_delay','--fault-start-ms','30500','--fault-duration-ms','4500','--task-delay-ms','600','--fault-behavior','transient'])
  def done(path):self.runtime.load(str(path)+'.final.csv');self.runtime.grid()
  self.app.run_background_task('Frozen CLO-DSF example','Running observe-only frozen pre-holdout detector.',task,on_success=done,on_error=lambda e:messagebox.showerror('Frozen CLO-DSF',str(e),parent=self))
def install():
 if not (OUTPUT/'clo_dsf_final_config.json').exists():return
 from . import cross_layer_gui as cross,research_analysis_gui as research
 cls=cross.CrossLayerSafetyPanel
 if getattr(cls,'_final_installed',False):return
 old_init,old_run,old_load=cls.__init__,cls.run_single,cls.load_results
 def init(self,*a,**k):
  old_init(self,*a,**k)
  for w in self.detector_row.winfo_children():
   if isinstance(w,ttk.Combobox):w.configure(values=('Hybrid Adaptive Kalman',LABEL,*[v for v in w['values'] if v!='Hybrid Adaptive Kalman']),width=40)
  self.final_evidence=FinalEvidenceView(self);self.final_evidence.grid(row=15,column=0,sticky='ew',pady=8);self.final_evidence.grid_remove()
 def run(self):
  if self.experimental_detector.get()!=LABEL:return old_run(self)
  try:positional,options=cross.backend_request(self.values())
  except ValueError as e:messagebox.showerror('Invalid final configuration',str(e),parent=self);return
  self._run('Running frozen CLO-DSF…',lambda:run_final(new_runtime_path('single_experiment.csv'),positional,options))
 def load(self,path=None):
  if path is None:
   value=filedialog.askopenfilename(parent=self,initialdir=OUTPUT,filetypes=(('CSV results','*.csv'),))
   if not value:return
   path=Path(value)
  old_load(self,path);self.final_evidence.grid_remove();sidecar=Path(str(path)+'.final.csv')
  if sidecar.exists():
   try:self.final_evidence.load(sidecar);self.final_evidence.grid()
   except (OSError,ValueError) as e:messagebox.showerror('Frozen CLO-DSF evidence',str(e),parent=self)
 cls.__init__=init;cls.run_single=run;cls.load_results=load;cls._final_installed=True
 old=research.ResearchAnalysisWorkspace.__init__
 def research_init(self,*a,**k):
  old(self,*a,**k);self.final_development=FinalDevelopmentPanel(self.headers['runtime_study'],self.app);self.final_development.grid(row=5,column=0,sticky='ew',pady=10)
 research.ResearchAnalysisWorkspace.__init__=research_init
