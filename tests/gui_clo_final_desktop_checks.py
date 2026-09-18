"""Opt-in actual desktop test; session and historical evidence are read-only."""
from pathlib import Path
import os,sys,tempfile,json,time,threading
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests'),str(ROOT/'python')]
OUT=ROOT/'results/cross_layer_safety_v7_2_confirmation/validation/gui_final';OUT.mkdir(parents=True,exist_ok=True)
fonts=Path(tempfile.mkdtemp(prefix='candidate2-fonts-'));expand=os.path.expanduser
with patch('os.path.expanduser',side_effect=lambda p:str(fonts) if p=='~/.fonts/' else expand(p)):
 import virtual_ecu_final_gui as launcher
 gui=launcher.gui
from virtual_ecu.clo_dsf_final_gui import LABEL,FinalEvidenceView
from virtual_ecu.clo_dsf_candidate2_gui import C1_LABEL
from gui_window_capture import capture
session=(ROOT/'presets/gui_session_state.json').read_bytes();temp=tempfile.TemporaryDirectory(prefix='candidate2-gui-')
for name in ['write_recent_results','write_favorite_comparisons','write_gui_session_state']:
 original=getattr(gui,name)
 def redirected(value,*args,_original=original,_name=name,**kwargs):return _original(value,path=Path(temp.name)/(_name+'.json'))
 setattr(gui,name,redirected)
gui.VirtualECUGui._maybe_auto_restore_session=lambda self:None
errors=[];checks=[];threading.excepthook=lambda a:errors.append(str(a.exc_value));gui.messagebox.showerror=lambda *a,**k:errors.append(str(a))
app=gui.VirtualECUGui();app.report_callback_exception=lambda *a:errors.append(str(a))
def check(value,name):assert value,name;checks.append(name);print('PASS',name,flush=True)
def wait_for(predicate,timeout=60):
 limit=time.monotonic()+timeout;failure=[]
 def poll():
  if errors:failure.append(str(errors));app.quit()
  elif predicate():app.quit()
  elif time.monotonic()>limit:failure.append('GUI worker timeout');app.quit()
  else:app.after(30,poll)
 app.after(30,poll);app.mainloop()
 if failure:raise AssertionError(failure)
 app.update()
try:
 ready=time.monotonic()+1.5;wait_for(lambda:time.monotonic()>=ready);panel=app.cross_layer_panel
 check(panel.experimental_detector.get()=='Hybrid Adaptive Kalman','Hybrid default preserved')
 panel.set_mode('Guided');check(not panel.detector_row.winfo_manager(),'Advanced detector choices hidden in Guided')
 panel.set_mode('Advanced');check(panel.detector_row.winfo_manager()=='grid','Advanced detector selector visible')
 from tkinter import ttk
 combo=next(w for w in panel.detector_row.winfo_children() if isinstance(w,ttk.Combobox));check(C1_LABEL in combo['values'] and LABEL in combo['values'],'Both candidate identities selectable')
 app._navigate_to_page('cross_layer');panel.experimental_detector.set(LABEL);panel.variables['Fault Model'].set('task_delay');panel.variables['Fault Layer'].set('timing');panel.variables['Duration (ms)'].set('3000');panel.variables['Behavior'].set('transient');panel._model_changed();panel.run_single();wait_for(lambda:panel.status.get().startswith('Loaded '))
 check(bool(panel.final_evidence.rows),'Advanced run loads Final CLO-DSF runtime sidecar')
 check(any(r['detector_state']=='CONFIRMED' and r['estimated_origin']=='TIMING' for r in panel.final_evidence.rows),'Live runtime detects and localizes timing')
 check(not any('true_origin' in k for r in panel.final_evidence.rows for k in r),'Runtime panel excludes evaluation labels')
 panel.final_evidence.selector.current(0);panel.final_evidence.show(0);check(panel.final_evidence.values['detector_state'].get()=='NORMAL','Runtime selector shows initial state')
 # Load an actual selected-validation sensor trace with CONFIRMED + UNKNOWN.
 import csv
 manifest=list(csv.DictReader((ROOT/'results/cross_layer_safety_v7_2_confirmation/confirmation_configuration_manifest.csv').open()));spec=next(s for s in manifest if s['origin']=='SENSOR_CONTROL')
 panel.final_evidence.load(ROOT/f"results/cross_layer_safety_v7_2_confirmation/traces/{spec['run_id']}.final.csv.gz")
 check(panel.final_evidence.values['detector_state'].get()=='CONFIRMED' and panel.final_evidence.values['estimated_origin'].get()=='UNKNOWN','Confirmed anomaly with UNKNOWN origin is displayed as valid')
 app.page_frames['cross_layer'].canvas.yview_moveto(1);app.update();capture(app,OUT/'advanced_candidate2.png')
 # Capture the same runtime component in a focused window so every field is readable.
 import tkinter as tk
 preview=tk.Toplevel(app);preview.geometry('1100x480');preview.title('Final CLO-DSF runtime evidence')
 view=FinalEvidenceView(preview);view.pack(fill='both',expand=True,padx=8,pady=8)
 view.load(ROOT/f"results/cross_layer_safety_v7_2_confirmation/traces/{spec['run_id']}.final.csv.gz")
 ready=time.monotonic()+.5;wait_for(lambda:time.monotonic()>=ready);capture(preview,OUT/'separate_anomaly_origin.png');preview.destroy()
 app.research_workspace.show('runtime_study');dev=app.research_workspace.final_development;dev.load();app.update();check(len(dev.table.get_children())==10,'Confirmation comparison includes all ten methods and ablations');check(dev.truth.winfo_manager()=='grid','Evaluation table ground truth is separate')
 check(hasattr(app.research_workspace,'clo_development'),'Original Candidate 1 study panel retained')
 dev.example();wait_for(lambda:bool(dev.runtime.rows));check(any(r['alarm']=='1' for r in dev.runtime.rows),'Research example executes Final CLO-DSF C path')
 app.page_frames['runtime_study'].canvas.yview_moveto(.2);app.update();capture(app,OUT/'development_comparison.png')
 panel.load_results(ROOT/'results/cross_layer_safety_v7_dev/gui_runtime/single_experiment.csv');check(bool(panel.clo_evidence.rows) and not panel.final_evidence.winfo_manager(),'Frozen Candidate 1 runtime result still loads')
 panel.load_results(ROOT/'results/cross_layer_safety_v7_1_dev/gui_runtime/single_experiment.csv');check(bool(panel.candidate2_evidence.rows) and not panel.final_evidence.winfo_manager(),'Historical Candidate 2 runtime still loads')
 panel.load_results(ROOT/'results/cross_layer_safety_v1/raw/baseline.csv');check(not panel.final_evidence.winfo_manager(),'Historical CSV hides unavailable Final CLO-DSF evidence')
 panel.final_panel.load(ROOT/'results/cross_layer_safety_v6');check((ROOT/'presets/gui_session_state.json').read_bytes()==session,'User session byte-identical');check(not errors,'No GUI callback errors')
 (OUT/'desktop_checks.json').write_text(json.dumps(dict(status='PASS',checks=checks,errors=errors),indent=2)+'\n')
finally:app.destroy();temp.cleanup()
