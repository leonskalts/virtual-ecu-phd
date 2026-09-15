"""Opt-in live Tk integration review: python3 tests/gui_v61_desktop_checks.py.

Uses the normal background-task implementation, redirects session/history/export
writes, and saves screenshots plus a machine-readable validation report.
"""
import copy
import faulthandler
faulthandler.dump_traceback_later(120, repeat=True)
import json
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import virtual_ecu_gui as gui
from virtual_ecu.cross_layer_ui import DEFAULTS,UI_MODELS,behaviors,backend_request,visible_fields
from virtual_ecu.cross_layer_gui import DEFAULT_RUNTIME_DIR
from virtual_ecu.gui_design import PAGE_LABELS,Tooltip
from gui_window_capture import capture

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/cross_layer_safety_v6_1/validation'
OUT.mkdir(parents=True,exist_ok=True)
shots=OUT/'screenshots';shots.mkdir(exist_ok=True)
report={'checks':[],'screenshots':[],'experiments':[],'errors':[],'geometry':[]}
saved_session=(ROOT/'presets/gui_session_state.json').read_bytes()
temporary=tempfile.TemporaryDirectory(prefix='vecu-gui-v61-')
for name in ('write_recent_results','write_favorite_comparisons','write_gui_session_state'):
 original=getattr(gui,name)
 def redirected(value,*args,_original=original,_name=name,**kwargs):
  return _original(value,path=Path(temporary.name)/(_name+'.json'))
 setattr(gui,name,redirected)
gui.VirtualECUGui._maybe_auto_restore_session=lambda self:None
# Export generation exercises the original actions in a new destination.
gui.EXPORT_ROOT=OUT/'exports/reports';gui.SNAPSHOT_ROOT=OUT/'exports/snapshots';gui.PRESENTATION_BUNDLE_ROOT=OUT/'exports/presentations'
gui.messagebox.showerror=lambda *a,**k:report['errors'].append(str(a))
gui.messagebox.showinfo=lambda *a,**k:None
app=gui.VirtualECUGui()
def callback_error(*args):report['errors'].append(str(args));traceback.print_exception(*args)
app.report_callback_exception=callback_error
panel=app.cross_layer_panel

def check(condition,name):
 if not condition:raise AssertionError(name)
 report['checks'].append(name)

def snapshot(name):
 path=shots/(name+'.png');capture(app,path);report['screenshots'].append(str(path.relative_to(ROOT)))

def scroll_to(widget):
 app.update_idletasks()
 frame=app.page_frames['cross_layer']
 height=frame.content.winfo_height()
 frame.canvas.yview_moveto(max(0,(widget.winfo_rooty()-frame.content.winfo_rooty())/height))

def steps():
 yield 1500
 check(panel.mode.get()=='Guided','Guided is default')
 check(not panel.results.winfo_manager() and panel.empty.winfo_manager()=='grid','Cross-Layer empty state hides results')
 original=panel.values();command=backend_request(original)
 panel.set_mode('Advanced');panel.set_mode('Guided')
 app.presentation_mode.set(True);app._apply_presentation_mode()
 app.presentation_mode.set(False);app._apply_presentation_mode()
 check(panel.values()==original and backend_request(panel.values())==command,'Visual modes preserve scientific configuration and command')
 for model,(layer,target) in UI_MODELS.items():
  panel.variables['Fault Layer'].set(layer);panel.variables['Fault Model'].set(model);panel._model_changed()
  for behavior in behaviors(model):
   panel.variables['Behavior'].set(behavior);panel._behavior_changed()
   for mode in ('Guided','Advanced'):
    panel.set_mode(mode)
    expected=visible_fields(panel.values(),mode,panel.contract_open.get())
    check(all((cell.winfo_manager()=='grid')==(name in expected) for name,cell in panel.field_rows.items()),f'{model}/{behavior}/{mode} shows only relevant fields')
 for name,value in DEFAULTS.items():panel.variables[name].set(value)
 panel._model_changed();panel.set_mode('Guided')
 # Version-specific loaders preserve historical N/A rather than infer new values.
 panel.load_results(ROOT/'results/cross_layer_safety_v1/raw/baseline.csv')
 check(bool(panel.loaded_summaries),'Legacy raw CSV loads')
 panel.load_results(ROOT/'results/cross_layer_safety_v1/cross_layer_run_summary.csv')
 check(bool(panel.loaded_summaries),'v1 summary loads')
 check(panel.result_fields['containment_success'].get()=='N/A','Unavailable v1 containment remains N/A')
 panel.load_results(ROOT/'results/cross_layer_safety_v2/campaign_runs.csv')
 check(bool(panel.loaded_summaries),'v2 campaign loads')
 panel.load_v3_analysis(ROOT/'results/cross_layer_safety_v3');check(bool(panel.analysis_panel.loaded_tables),'v3 analysis loads')
 panel.load_v4_results(ROOT/'results/cross_layer_safety_v4');check(bool(panel.runtime_panel.loaded_tables),'v4 runtime loads')
 panel.load_v5_results(ROOT/'results/cross_layer_safety_v5');check(bool(panel.validation_panel.table.get_children()),'v5 validation loads')
 check(panel.final_panel.load(ROOT/'results/cross_layer_safety_v6'),'v6 final validation loads')
 for child in (panel.analysis_panel,panel.runtime_panel,panel.validation_panel):child.grid_remove()
 panel.results.grid_remove();panel.empty.grid()
 app.reload_rtl_security_plot_viewer(show_error=False)
 # Run the redesigned GUI actions with the original background-task machinery.
 for model in ('bit_flip','task_delay','replayed_sample'):
  panel.variables['Fault Model'].set(model);panel._model_changed()
  panel.variables['Duration (ms)'].set('100')
  panel.status.set('Ready')
  panel.quick_run.invoke()
  start=time.monotonic()
  while not panel.status.get().startswith('Loaded '):
   if report['errors'] or time.monotonic()-start>90:raise AssertionError('GUI experiment did not complete: '+panel.status.get())
   yield 150
  check(bool(panel.loaded_summaries),model+' GUI results populate')
  check(panel.results.winfo_manager()=='grid' and not panel.empty.winfo_manager(),model+' loaded result state replaces empty state')
  destination=OUT/'gui_runs'/model;destination.mkdir(parents=True,exist_ok=True)
  for path in (DEFAULT_RUNTIME_DIR/'gui_single').glob('*.csv'):shutil.copy2(path,destination/path.name)
  report['experiments'].append({'model':model,'values':panel.values(),'command':backend_request(panel.values()),'summary':panel.loaded_summaries[0]})
  app._navigate_to_page('cross_layer');scroll_to(panel.results)
  yield 400
  snapshot('cross_layer_result_'+model)
 # Existing advanced configuration and session serialization remain available.
 before=app._validate_custom_config()
 check(before is not None,'Advanced builder existing single-fault validation works')
 check(app.custom_empty_state.winfo_manager()=='grid','Advanced builder empty state hides unavailable result inspector')
 app.save_session_state(quiet=True)
 check((Path(temporary.name)/'write_gui_session_state.json').is_file(),'Session writes original schema to isolated file')
 check((ROOT/'presets/gui_session_state.json').read_bytes()==saved_session,'Existing user session remains unchanged')
 for slot,model in (('left','bit_flip'),('right','task_delay')):
  result=app._load_existing_result_from_path(OUT/'gui_runs'/model/'single_experiment.csv')
  app._apply_existing_result(slot,result)
 check(app.current_comparison is not None,'Existing left/right comparison accepts new GUI runs')
 check('bit_flip' in app.workflow_summary_vars['figures'].get() and 'task_delay' in app.workflow_summary_vars['figures'].get(),'Comparison names show actual cross-layer fault metadata')
 for action in (app.export_results_snapshot,app.export_current_comparison,app.export_presentation_bundle):
  action();check(app.status_text.get().startswith('Exported '),action.__name__+' callable and completed')
 check('Completed' in app.workflow_summary_vars['exports'].get(),'Actual export destination appears in Last Export')
 # Three complete navigation and layout passes, with live drawable captures.
 for width,height in ((1366,768),(1920,1080),(2560,1440)):
  app.geometry(f'{width}x{height}+0+0');yield 350
  for page in PAGE_LABELS:
   app._navigate_to_page(page);app.page_frames[page].canvas.yview_moveto(0)
   yield 350
   check(app.notebook.select()==str(app.page_frames[page]),f'{width}x{height}/{page} navigation')
   report['geometry'].append({'page':page,'requested':[width,height],'actual':[app.winfo_width(),app.winfo_height()],
       'content_width':app.page_frames[page].content.winfo_width(),'requested_content_width':app.page_frames[page].content.winfo_reqwidth()})
   snapshot(f'{page}_{width}x{height}')
  print('Reviewed',width,height,flush=True)
 app.geometry('1366x768+0+0');app._navigate_to_page('cross_layer')
 for mode in ('Guided','Advanced'):
  panel.set_mode(mode);app.page_frames['cross_layer'].canvas.yview_moveto(0);yield 400;snapshot('cross_layer_'+mode.lower())
 app.presentation_mode.set(True);app._apply_presentation_mode();yield 350;snapshot('cross_layer_presentation')
 tip=Tooltip(panel.inputs['Replay Age (ms)'],'Age of the historical sample replayed instead of the current communication update.')
 tip.show();check(tip.window is not None,'Tooltip can be opened');yield 350;snapshot('cross_layer_tooltip');tip.hide()
 check(callable(panel.final_panel.run_mode),'Reproducibility controls callable')
 check(not report['errors'],'No Tk callback or GUI operation errors')
 print('Desktop checks passed:',len(report['checks']),flush=True)

generator=steps()
def advance():
 try:delay=next(generator)
 except StopIteration:
  report['status']='PASS';finish();return
 except Exception:
  report['status']='FAIL';report['errors'].append(traceback.format_exc());traceback.print_exc();finish();return
 app.after(delay,advance)
def finish():
 (OUT/'desktop_checks.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
 app.destroy();temporary.cleanup()
app.after(100,advance)
app.mainloop()
if report.get('status')!='PASS':sys.exit(1)
