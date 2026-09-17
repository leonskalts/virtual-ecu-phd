"""Opt-in GUI checks; all session/export/evidence writes confined to v7 or /tmp.

Run with --legacy to replay the unchanged v6.2 desktop suite into v7 storage.
"""
from pathlib import Path
import os
import sys
import tempfile
import json
import time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests'),str(ROOT/'python')]
OUT=ROOT/'results/cross_layer_safety_v7_dev/validation/gui_v7'
OUT.mkdir(parents=True,exist_ok=True)
font_dir=Path(tempfile.mkdtemp(prefix='clo-fonts-'))
expand=os.path.expanduser
# Third-party GUI import attempts to install fonts into ~/.fonts. Redirect only
# that cache, without changing HOME or any user files.
with patch('os.path.expanduser',side_effect=lambda p:str(font_dir) if p=='~/.fonts/' else expand(p)):
    import virtual_ecu_gui as gui
from virtual_ecu.clo_dsf_gui import LABEL
from virtual_ecu import cross_layer_gui
from gui_window_capture import capture

if '--legacy' in sys.argv:
    original=ROOT/'tests/gui_v62_desktop_checks.py'
    source=original.read_text().replace("OUT=ROOT/'results/cross_layer_safety_v6_2/validation'", "OUT=ROOT/'results/cross_layer_safety_v7_dev/validation/gui_v62'")
    exec(compile(source,str(original),'exec'),{'__file__':str(original),'__name__':'__main__'})
    sys.exit(0)

session=(ROOT/'presets/gui_session_state.json').read_bytes()
temporary=tempfile.TemporaryDirectory(prefix='clo-gui-state-')
for name in ['write_recent_results','write_favorite_comparisons','write_gui_session_state']:
    original=getattr(gui,name)
    def redirected(value,*args,_original=original,_name=name,**kwargs):
        return _original(value,path=Path(temporary.name)/(_name+'.json'))
    setattr(gui,name,redirected)
gui.VirtualECUGui._maybe_auto_restore_session=lambda self:None
errors=[];checks=[]
import threading
threading.excepthook=lambda args:errors.append(str(args.exc_value))
gui.messagebox.showerror=lambda *a,**k:errors.append(str(a))
app=gui.VirtualECUGui()
app.report_callback_exception=lambda *a:errors.append(str(a))

def check(condition,name):
    assert condition,name
    checks.append(name);print('PASS',name,flush=True)

def wait_for(predicate,timeout=60):
    limit=time.monotonic()+timeout
    failure=[]
    def poll():
        if errors:
            failure.append(str(errors));app.quit()
        elif predicate():app.quit()
        elif time.monotonic()>limit:
            failure.append('Timed out waiting for GUI worker');app.quit()
        else:app.after(30,poll)
    app.after(30,poll)
    app.mainloop()
    if failure:raise AssertionError(failure)
    app.update()

try:
    ready_at=time.monotonic()+1.5
    wait_for(lambda:time.monotonic()>=ready_at)
    panel=app.cross_layer_panel
    check(panel.experimental_detector.get()=='Hybrid Adaptive Kalman','Hybrid remains default')
    panel.set_mode('Guided');check(not panel.detector_row.winfo_manager(),'Experimental selector hidden in Guided')
    panel.set_mode('Advanced');check(panel.detector_row.winfo_manager()=='grid','Experimental selector available in Advanced')
    app._navigate_to_page('cross_layer');panel.experimental_detector.set(LABEL)
    panel.variables['Fault Model'].set('task_delay');panel.variables['Fault Layer'].set('timing')
    panel.variables['Duration (ms)'].set('4000');panel.variables['Behavior'].set('transient');panel._model_changed()
    panel.run_single();wait_for(lambda:panel.status.get().startswith('Loaded '))
    check(bool(panel.clo_evidence.rows),'Advanced execution loads runtime sidecar')
    check(any(r['detector_state']=='CONFIRMED' for r in panel.clo_evidence.rows),'Live C detector confirms timing anomaly')
    check(any(r['estimated_origin']=='TIMING' for r in panel.clo_evidence.rows),'Runtime view shows estimated TIMING')
    check(not any('true_origin' in r for r in panel.clo_evidence.rows),'Runtime view excludes evaluation truth')
    panel.clo_evidence.selector.current(0);panel.clo_evidence.show(0)
    check(panel.clo_evidence.values['detector_state'].get()=='NORMAL','Evidence selector can inspect pre-anomaly state')
    app.page_frames['cross_layer'].canvas.yview_moveto(1);app.update();capture(app,OUT/'advanced_runtime.png')
    app.research_workspace.show('runtime_study');development=app.research_workspace.clo_development
    development.load();app.update()
    check(len(development.table.get_children())==13,'Detector Study loads all development comparisons')
    check(development.truth.winfo_manager()=='grid','Evaluation Ground Truth section is separate')
    development.example();wait_for(lambda:bool(development.runtime.rows))
    check(any(r['alarm']=='1' for r in development.runtime.rows),'Detector Study example executes v7 C path')
    app.page_frames['runtime_study'].canvas.yview_moveto(0);app.update();capture(app,OUT/'detector_study.png')
    panel.load_results(ROOT/'results/cross_layer_safety_v1/raw/baseline.csv')
    check(not panel.clo_evidence.winfo_manager(),'Old CSV hides unavailable v7 evidence')
    panel.final_panel.load(ROOT/'results/cross_layer_safety_v6')
    check((ROOT/'presets/gui_session_state.json').read_bytes()==session,'User session preserved byte-for-byte')
    check(not errors,'No Tk callback errors')
    (OUT/'desktop_checks.json').write_text(json.dumps({'status':'PASS','checks':checks,'errors':errors},indent=2)+'\n')
finally:
    app.destroy();temporary.cleanup()
