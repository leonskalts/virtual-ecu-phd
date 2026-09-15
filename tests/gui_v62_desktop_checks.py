"""Opt-in live Tk integration review: python3 tests/gui_v62_desktop_checks.py.

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
from virtual_ecu import cross_layer_gui
from virtual_ecu.final_validation_gui import read_final_summary,format_final_metric
from virtual_ecu.gui_design import RESEARCH_VIEWS,MetricCard
from tkinter import ttk,font
from virtual_ecu.gui_design import PAGE_LABELS,Tooltip
from gui_window_capture import capture

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/cross_layer_safety_v6_2/validation'
OUT.mkdir(parents=True,exist_ok=True)
shots=OUT/'screenshots';shots.mkdir(exist_ok=True)
report={'checks':[],'screenshots':[],'experiments':[],'errors':[],'geometry':[]}
saved_session=(ROOT/'presets/gui_session_state.json').read_bytes()
temporary=tempfile.TemporaryDirectory(prefix='vecu-gui-v62-')
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
cross_layer_gui.DEFAULT_RUNTIME_DIR=OUT.parent/'runtime'
print('Constructing GUI',flush=True)
app=gui.VirtualECUGui()
print('GUI constructed',flush=True)
def callback_error(*args):report['errors'].append(str(args));traceback.print_exception(*args)
app.report_callback_exception=callback_error
panel=app.cross_layer_panel

def check(condition,name):
 if not condition:raise AssertionError(name)
 report['checks'].append(name)
 print('PASS',name,flush=True)

def snapshot(name):
 path=shots/(name+'.png');capture(app,path);report['screenshots'].append(str(path.relative_to(ROOT)))

def scroll_to(widget):
 app.update_idletasks()
 frame=app.page_frames['cross_layer']
 height=frame.content.winfo_height()
 frame.canvas.yview_moveto(max(0,(widget.winfo_rooty()-frame.content.winfo_rooty())/height))

def widgets(root):
 for child in root.winfo_children():
  yield child
  yield from widgets(child)


def steps():
 yield 1500
 check(set(app.sidebar_buttons)=={'dashboard','summary','figures','fault_path','cross_layer','research_analysis','rtl_security','exports','final_validation','custom'},'Consolidated ten-entry sidebar')
 app._navigate_to_page('research_analysis');yield 200
 check(app.notebook.select()==str(app.page_frames['research_analysis']),'Research overview is first entry')
 # Invoke BOTH real Dashboard buttons. Do not replace navigation callbacks.
 launches=[w for w in widgets(app.page_frames['dashboard']) if hasattr(w,'invoke') and str(w.cget('text'))=='Start Guided Experiment']
 check(len(launches)==2,'Both Dashboard Guided launch buttons found')
 panel.variables['Seed'].set('92');panel.variables['FTTI (ms)'].set('7000');panel.variables['Replay Age (ms)'].set('1200')
 original=panel.values();command=backend_request(original)
 for index,button in enumerate(launches):
  panel.set_mode('Advanced');app._navigate_to_page('dashboard');button.invoke();yield 150
  check(app.notebook.select()==str(app.page_frames['cross_layer']) and panel.mode.get()=='Guided',f'Dashboard button {index+1} opens visibly Guided')
  check(panel.values()==original and backend_request(panel.values())==command,f'Dashboard button {index+1} preserves advanced values and command')
  panel.set_mode('Advanced')
  check(panel.field_rows['Seed'].winfo_manager()=='grid' and panel.field_rows['FTTI (ms)'].winfo_manager()=='grid','Advanced fields reappear with stored values')
 panel.set_mode('Advanced');app._navigate_to_page('dashboard')
 research=[w for w in widgets(app.page_frames['dashboard']) if hasattr(w,'invoke') and str(w.cget('text'))=='Open Research Workspace'][0]
 research.invoke();yield 150
 check(panel.mode.get()=='Advanced' and panel.values()==original,'Research launch preserves Cross-Layer mode and values')
 app._navigate_to_page('cross_layer');check(panel.mode.get()=='Advanced','Direct navigation preserves mode')
 app.presentation_mode.set(True);app._apply_presentation_mode()
 check(panel.values()==original and backend_request(panel.values())==command,'Presentation preserves exact scientific command')
 app.presentation_mode.set(False);app._apply_presentation_mode()
 # The original numeric saved state still points to the same implementation.
 for index,key in ((5,'batch'),(6,'runtime_study'),(7,'parameter_sweep')):
  app._restore_notebook_index(app.notebook,index);yield 150
  check(app.notebook.select()==str(app.page_frames[key]) and app.research_workspace.selection.get()==key,'Saved index '+str(index)+' opens '+key)
  app._navigate_to_page('rtl_security');app._navigate_to_page('research_analysis');yield 100
  check(app.notebook.select()==str(app.page_frames[key]),'Research reentry remembers '+key)
  app._navigate_to_page(key);yield 100
  check(app.research_workspace.selected==key,'Old internal ID routes '+key)
 # Navigation must never start a study. Observe the normal task entrypoint.
 tasks=[];background=app.run_background_task
 def observed(*args,**kwargs):tasks.append(str(args[0]));return background(*args,**kwargs)
 app.run_background_task=observed
 for key in RESEARCH_VIEWS:
  app.research_workspace.show(key);yield 100
 check(not tasks,'Research selection never reruns studies')
 app.run_background_task=background
 app.load_batch_results(update_activity=False)
 start=time.monotonic()
 while len(app.batch_rows)!=47:
  if time.monotonic()-start>30:raise AssertionError(app.batch_status_text.get())
  yield 100
 check(len(app.batch_rows)==47,'Original 47-run aggregate loads')
 app.load_runtime_intervention_study(show_error=False)
 check(len(app.runtime_study_rows)==90,'Original 90-run Detector Study loads')
 report['detector_summary']={k:v.get() for k,v in app.runtime_study_summary_vars.items()}
 app.load_parameter_sweep_results(show_error=False)
 check(len(app.parameter_sweep_rows)==7,'All seven paper-facing sweep detectors load')
 report['sweep_summary']={k:v.get() for k,v in app.parameter_sweep_summary_vars.items()}
 report['sweep_cards']={k:v.get() for k,v in app.sweep_card_vars.items()}
 check('kalman filter' in app.sweep_cards['Best Coverage'].detail.get().lower() and 'Hybrid Adaptive Kalman' in app.sweep_cards['Best Coverage'].detail.get(),'Best coverage preserves Kalman/Hybrid tie')
 check('Threshold' in app.sweep_cards['Best Median Latency'].detail.get() and 'Hybrid Adaptive Kalman' in app.sweep_cards['Best Median Latency'].detail.get(),'Best latency preserves Threshold/Hybrid tie')
 final=panel.final_panel
 expected=read_final_summary(ROOT/'results/cross_layer_safety_v6')
 check(final.load(ROOT/'results/cross_layer_safety_v6'),'Final v6 package loads')
 for name,card in final.cards.items():
  check((card.value.get(),card.detail.get())==format_final_metric(expected[name]),'Loaded final card exactly formats '+name)
  check(not card.value_label.cget('font') and font.Font(app,font=ttk.Style(app).lookup('MetricValue.TLabel','font')).actual('size')>=21,'Metric font is prominent: '+name)
 check(not final.load(Path(temporary.name)/'missing'),'Missing final evidence fails gracefully')
 check(all(card.value.get()=='N/A' for card in final.cards.values()),'Unavailable final cards show N/A')
 final.load(ROOT/'results/cross_layer_safety_v6')
 # Existing legacy/version-specific loading remains callable with actual files.
 panel.load_results(ROOT/'results/cross_layer_safety_v1/raw/baseline.csv');check(bool(panel.loaded_summaries),'Legacy raw CSV loads')
 panel.load_results(ROOT/'results/cross_layer_safety_v1/cross_layer_run_summary.csv');check(panel.result_fields['containment_success'].get()=='N/A','v1 unavailable containment remains N/A')
 panel.load_results(ROOT/'results/cross_layer_safety_v2/campaign_runs.csv');check(bool(panel.loaded_summaries),'v2 campaign loads')
 panel.load_v3_analysis(ROOT/'results/cross_layer_safety_v3');check(bool(panel.analysis_panel.loaded_tables),'v3 analysis loads')
 panel.load_v4_results(ROOT/'results/cross_layer_safety_v4');check(bool(panel.runtime_panel.loaded_tables),'v4 runtime loads')
 panel.load_v5_results(ROOT/'results/cross_layer_safety_v5');check(bool(panel.validation_panel.table.get_children()),'v5 validation loads')
 for child in (panel.analysis_panel,panel.runtime_panel,panel.validation_panel):child.grid_remove()
 app.reload_rtl_security_plot_viewer(show_error=False)
 check(bool(app.rtl_run_summary_vars['trojan']['RTL Target'].get()),'RTL Security loads independently')
 # Verify the empty builder using its actual current scenario, then zero events.
 app._navigate_to_page('custom');app.custom_builder_notebook.select(1);yield 150
 count=len(app.multi_events)
 check(str(count)+' staged events configured' in app.custom_empty_summary.get(),'Builder staged count reflects current scenario')
 saved_events=copy.deepcopy(app.multi_events)
 app.clear_multi_events();yield 150
 check('No staged events configured' in app.custom_empty_summary.get(),'Zero-event builder is purposeful')
 check(app.custom_empty_buttons['add'].winfo_manager()=='grid' and not app.custom_empty_buttons['run'].winfo_manager(),'Zero-event actions offer Add Event and hide invalid Run')
 frame=app.page_frames['custom'];app.update_idletasks()
 frame.canvas.yview_moveto((app.custom_empty_state.winfo_rooty()-frame.content.winfo_rooty())/frame.content.winfo_height());yield 150
 snapshot('builder_zero_events')
 frame.canvas.yview_moveto(0)
 app.custom_empty_buttons['add'].invoke();yield 150
 check(len(app.multi_events)==1 and '1 staged events configured' in app.custom_empty_summary.get(),'Empty-state Add Event uses existing event validation')
 app.custom_empty_buttons['add'].invoke();yield 150
 check(len(app.multi_events)==2 and app.custom_empty_buttons['run'].winfo_manager()=='grid','Two events enable existing run workflow')
 # Button dispatch verified without executing a second, unrelated experiment.
 invoked=[]
 for name,key in (('run_multi_only','run'),('compare_multi_vs_baseline','compare')):
  original_method=getattr(app,name);setattr(app,name,lambda name=name:invoked.append(name))
  app.custom_empty_buttons[key].invoke();setattr(app,name,original_method)
 check(invoked==['run_multi_only','compare_multi_vs_baseline'],'Builder empty actions dispatch original multi callbacks')
 app.custom_builder_notebook.select(0);yield 100
 check('Single-fault scenario configured' in app.custom_empty_summary.get(),'Single-fault builder state is accurate')
 for name,key in (('run_custom_only','run'),('compare_custom_vs_baseline','compare')):
  original_method=getattr(app,name);setattr(app,name,lambda name=name:invoked.append(name))
  app.custom_empty_buttons[key].invoke();setattr(app,name,original_method)
 check(invoked[-2:]==['run_custom_only','compare_custom_vs_baseline'],'Builder empty actions dispatch original single callbacks')
 app.multi_events=saved_events;app._refresh_multi_event_listbox();app.custom_builder_notebook.select(1)
 # One actual Guided experiment, through the unchanged background worker.
 for name,value in DEFAULTS.items():panel.variables[name].set(value)
 panel._model_changed();launches[0].invoke();panel.status.set('Ready');panel.quick_run.invoke()
 start=time.monotonic()
 while not panel.status.get().startswith('Loaded '):
  if report['errors'] or time.monotonic()-start>90:raise AssertionError(panel.status.get())
  yield 150
 check(bool(panel.loaded_summaries),'Actual Guided run completes and populates results')
 report['experiments'].append({'values':panel.values(),'command':backend_request(panel.values()),'summary':panel.loaded_summaries[0]})
 check(panel.loaded_summaries[0]['detected']==1,'Representative Guided bit flip retains detection')
 check((cross_layer_gui.DEFAULT_RUNTIME_DIR/'gui_single/single_experiment.csv').read_bytes()==(ROOT/'results/cross_layer_safety_v6_1/validation/gui_runs/bit_flip/single_experiment.csv').read_bytes(),'Guided raw CSV matches pre-v6.2 experiment byte for byte')
 # Load actual saved comparison pairs, leaving all inputs read-only.
 app.current_plot_results=None;app.refresh_comparison_cards()
 check(all(v.get()=='N/A' for v in app.comparison_card_vars.values()),'No comparison shows proper empty state')
 for slot,model in (('left','bit_flip'),('right','task_delay')):
  result=app._load_existing_result_from_path(ROOT/'results/cross_layer_safety_v6_1/validation/gui_runs'/model/'single_experiment.csv')
  app._apply_existing_result(slot,result)
 app._navigate_to_page('figures');yield 150
 check(all(card.winfo_ismapped() for card in app.comparison_cards.values()),'Loaded comparison cards are visibly mapped')
 check('bit_flip' in app.comparison_card_vars['Left Case'].get(),'Left comparison card uses loaded case')
 check('task_delay' in app.comparison_card_vars['Right Case'].get(),'Right comparison card uses loaded case')
 check('Recorded maximum coolant' in app.comparison_card_vars['Key Difference'].get(),'Cross-layer key difference uses stored evidence')
 app.comparison_details_toggle.invoke();yield 100
 check(app.comparison_details.winfo_manager()=='grid','Detailed comparison remains accessible')
 app.comparison_details_toggle.invoke()
 app.last_custom_result=result;app.custom_last_run_var.set('Loaded result');yield 150
 check(not app.custom_empty_state.winfo_manager(),'Loaded result replaces builder empty state')
 app.last_custom_result=None;app.custom_last_run_var.set('No result');yield 150
 for action in (app.export_results_snapshot,app.export_current_comparison,app.export_presentation_bundle):
  action();check(app.status_text.get().startswith('Exported '),action.__name__+' completed')
 app.save_session_state(quiet=True)
 check((Path(temporary.name)/'write_gui_session_state.json').is_file(),'Session schema serializes to isolated file')
 check((ROOT/'presets/gui_session_state.json').read_bytes()==saved_session,'Existing user session preserved byte for byte')
 for width,height in ((1366,768),(1920,1080),(2560,1440)):
  app.geometry(f'{width}x{height}+0+0');yield 350
  for page in PAGE_LABELS:
   if page=='research_analysis':app.research_workspace.show(page)
   else:app._navigate_to_page(page)
   app.page_frames[page].canvas.yview_moveto(0);yield 250
   check(app.notebook.select()==str(app.page_frames[page]),f'{width}x{height}/{page} navigation')
   report['geometry'].append({'page':page,'requested':[width,height],'actual':[app.winfo_width(),app.winfo_height()],
       'content_width':app.page_frames[page].content.winfo_width(),'requested_content_width':app.page_frames[page].content.winfo_reqwidth()})
   for card in (w for w in widgets(app.page_frames[page]) if isinstance(w,MetricCard) and w.winfo_ismapped()):
    check(all(label.winfo_reqwidth()<=label.winfo_width()+2 for label in (card.title_label,card.value_label,card.detail_label)),f'{width}x{height}/{page} card text fits allocated width')
   snapshot(f'{page}_{width}x{height}')
  app._navigate_to_page('custom');app.update_idletasks()
  frame=app.page_frames['custom']
  frame.canvas.yview_moveto((app.custom_empty_state.winfo_rooty()-frame.content.winfo_rooty())/frame.content.winfo_height());yield 150
  snapshot(f'custom_empty_{width}x{height}')
  print('Reviewed',width,height,flush=True)
 # All changed pages in presentation mode, including the internal selector bar.
 app.geometry('1366x768+0+0');app.presentation_mode.set(True);app._apply_presentation_mode()
 for page in ('research_analysis','batch','runtime_study','parameter_sweep','final_validation','figures','cross_layer','custom'):
  if page=='research_analysis':app.research_workspace.show(page)
  else:app._navigate_to_page(page)
  app.page_frames[page].canvas.yview_moveto(0);yield 250
  snapshot(page+'_presentation')
  check(app.notebook.select()==str(app.page_frames[page]),page+' presentation navigation')
 app.presentation_mode.set(False);app._apply_presentation_mode()
 check(not report['errors'],'No Tk callbacks or GUI operations failed')
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
