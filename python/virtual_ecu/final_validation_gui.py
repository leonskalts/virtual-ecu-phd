"""Small final research summary; keep all version-specific legacy loaders intact."""
import json
import re
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter.scrolledtext import ScrolledText

from .final_evidence import ROOT, OUTPUT, GENERATOR
from .gui_design import action_button, StatusBanner, MetricGrid, section

FIELDS = (
    'Timing Holdout Coverage', 'Timing Coverage 95% CI', 'Legal Timing Alarms',
    'Legal Timing False-Alarm 95% CI', 'Plant-Propagating Timing Detection',
    'Cross-Layer Detection', 'Detection Given Plant Propagation', 'Silent Plant Propagation',
    'Current Recommended Timing Monitor', 'Current Default Safety Policy',
)


def read_final_summary(path):
    """Version-specific fields are never reconstructed from an older metric schema."""
    document = json.loads((Path(path)/'research_summary.json').read_text())
    if document.get('schema_version') != 6:
        raise ValueError('Select a v6 final validation package; use the existing version-specific loaders for older evidence.')
    fields = document.get('fields', {})
    if not isinstance(fields, dict):
        raise ValueError('Invalid v6 summary fields')
    return {name: 'N/A' if fields.get(name) in (None, '') else str(fields[name]) for name in FIELDS}


def format_final_metric(value):
    value = value.strip() or 'N/A'
    ratio = r'(\d+)\s*/\s*(\d+)'
    match = re.fullmatch(ratio + r'\s*\(([^)]+)\)', value)
    if match:
        return f'{match[1]} / {match[2]}', match[3]
    match = re.fullmatch(ratio + r'; pre-plant ' + ratio, value)
    if match:
        return f'{match[1]} / {match[2]}', f'{match[3]} / {match[4]} detected pre-plant'
    match = re.fullmatch(ratio, value)
    return (f'{match[1]} / {match[2]}', '') if match else (value, '')


class FinalValidationPanel(ttk.LabelFrame):
    def __init__(self, parent, background_task):
        super().__init__(parent, text='Research Summary / Final Validation', padding=8)
        self.background_task = background_task
        self.directory = OUTPUT
        self.fields = {name: tk.StringVar(self, value='N/A') for name in FIELDS}
        self.buttons = []
        bar = ttk.Frame(self);bar.grid(row=0,column=0,sticky='w')
        for index,(label,callback) in enumerate([
            ('Load Final Validation',self.load), ('Open Final Report',self.open_report),
            ('Run Quick Reproducibility Check',lambda:self.run_mode('--quick-check')),
            ('Regenerate Analysis',lambda:self.run_mode('--analysis-only')),
        ]):
            button=action_button(bar,label,callback)
            button.grid(row=index//2,column=index%2,padx=4,pady=4);self.buttons.append(button)
        self.metric_grid=MetricGrid(self)
        self.metric_grid.grid(row=1,column=0,sticky='ew',pady=10)
        self.cards={name:self.metric_grid.add(name,self.fields[name],formatter=format_final_metric) for name in FIELDS[:8]}
        policy=section(self,'Current research configuration',2)
        for row,name in enumerate(FIELDS[8:]):
            ttk.Label(policy,text=name).grid(row=row,column=0,sticky='w',pady=4)
            ttk.Label(policy,textvariable=self.fields[name],style='MetricTitle.TLabel',wraplength=400).grid(row=row,column=1,sticky='w',padx=18)
        self.status=tk.StringVar(self,value='Load a local v6 package, or regenerate analysis from the accepted v5 evidence.')
        StatusBanner(self,self.status).grid(row=3,column=0,sticky='ew',pady=8)
        ttk.Label(self,text='Simulation evidence; descriptive confidence bounds. Hazard prevention is unproven in the empty holdout hazard cohort. Host measurements are not embedded WCET.',wraplength=760).grid(row=5,column=0,sticky='w')
        ttk.Label(self,text='Simulation evidence with bounded confidence intervals. These results do not establish fleet reliability, embedded WCET, certification, or generalized hazard prevention.',wraplength=900,style='Help.TLabel').grid(row=4,column=0,sticky='ew',pady=8)
        self.columnconfigure(0,weight=1)
        if (OUTPUT/'research_summary.json').is_file():self.load(OUTPUT)

    def load(self,path=None):
        if path is None:
            path=filedialog.askdirectory(parent=self,initialdir=self.directory,title='Load Final Validation')
            if not path:return False
        self.directory=Path(path)
        try:
            values=read_final_summary(self.directory)
            for name,value in values.items():self.fields[name].set(value)
            self.status.set(f'Loaded v6 final evidence: {self.directory}')
            return True
        except (OSError,ValueError,TypeError) as exc:
            for value in self.fields.values():value.set('N/A')
            self.status.set(f'Final summary unavailable: {exc}. Select the v6 folder or run Regenerate Analysis with accepted v1–v5 evidence installed.')
            return False

    def open_report(self):
        path=self.directory/'final_report.md'
        try:content=path.read_text()
        except OSError:
            self.status.set('Final report is missing. Load a v6 package or run Regenerate Analysis.')
            return None
        window=tk.Toplevel(self);window.title('Cross-Layer Safety — Final Evidence Report');window.geometry('900x650')
        text=ScrolledText(window,wrap='word',font=('TkDefaultFont',11),padx=15,pady=12)
        text.pack(fill='both',expand=True);text.insert('1.0',content);text.configure(state='disabled')
        self.status.set(f'Opened {path}')
        return window

    def run_mode(self,mode):
        title='Quick reproducibility check' if mode=='--quick-check' else 'Regenerating final analysis'
        directory=ROOT/'results/cross_layer_safety_v6_1/final_validation'
        def task():
            result=subprocess.run([sys.executable,str(ROOT/GENERATOR),mode,'--output-dir',str(directory)],cwd=ROOT,capture_output=True,text=True)
            logs=directory/'validation'
            # The CLI rejects accepted output folders before any mutation. Do not
            # create a GUI log there when the requested destination is invalid.
            if result.returncode:
                raise RuntimeError(result.stderr or result.stdout)
            logs.mkdir(parents=True,exist_ok=True)
            (logs/('gui_'+mode[2:]+'.log')).write_text(result.stdout+result.stderr)
            return directory
        def success(path):
            self.load(path);self.status.set('Completed · '+title+' passed. Generated copy: '+str(path))
        self.status.set('Running · '+title+'; the application remains responsive.')
        self.background_task(title,'Accepted evidence stays read-only.',task,on_success=success,
                             on_error=lambda exc:self.status.set(f'{title} failed: {exc}'),
                             buttons_to_disable=tuple(self.buttons),success_action=title)
