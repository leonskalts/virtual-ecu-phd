import sys,csv,json,hashlib,subprocess,tempfile,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'python'),str(ROOT/'scripts')]
from virtual_ecu.clo_dsf_final_reporting import records
from virtual_ecu.clo_dsf_holdout import prepare_work
import run_clo_dsf_sensor_response as response
BASE=Path('/tmp/clo-complementarity');OUT=ROOT/'results/clo_dsf_current'

def main():
 BASE.mkdir(exist_ok=True)
 rows=[r for r in records(OUT/'case_summary.csv') if r['partition']=='development-train']
 a={r['run_id']:r for r in rows if r['method']=='Pre-change CLO-DSF'};ws={r['run_id']:r for r in rows if r['method']=='Weighted Sum'}
 chosen={k:'C_WS_only' for k,r in a.items() if r['injected'] and not r['detected'] and ws[k]['detected']}
 chosen.update({k:'E_WS_benign_alarm' for k,r in ws.items() if r['false_alarm']})
 # Never select or inspect VALIDATION records or outcomes for gate development.
 specs=[r for r in records(OUT/'campaign_manifest.csv') if r['partition']=='development-train' and r['run_id'] in chosen]
 assert len(specs)==112
 before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/v7_3/clo_dsf_revised.c',ROOT/'include/clo_dsf_revised.h',ROOT/'src/v7_3/revised_runtime.c',ROOT/'presets/gui_session_state.json',ROOT/'virtual_ecu_v7_3',OUT/'case_summary.csv',OUT/'campaign_manifest.csv']}
 (BASE/'before.json').write_text(json.dumps(before))
 summary=[];gatecounts=collections.defaultdict(collections.Counter)
 with tempfile.TemporaryDirectory(prefix='clo-train-disagreement-') as tmp:
  work=Path(tmp);prepare_work(work,specs)
  adapter=(ROOT/'src/v7_3/revised_runtime.c').read_text()
  adapter=adapter.replace('static FILE *trace,*observations;','static FILE *trace,*observations;\nstatic double analysis_ws;')
  adapter=adapter.replace(' if(trace)log_row(trace,o.time_ms,&detector,&o);','')
  adapter=adapter.replace('  simple_score(4,o.time_ms,peak>=.5);','  analysis_ws=ws;\n  simple_score(4,o.time_ms,peak>=.5);')
  adapter=adapter.replace(' if(primary){state->detection.current_score=', ' if(trace)log_row(trace,o.time_ms,&detector,&o);\n if(primary){state->detection.current_score=')
  adapter=adapter.replace('response_residual_c,response_strength\\n','response_residual_c,response_strength,analysis_ws,ws_timing,ws_communication,ws_memory,ws_sensor,ws_actuator,ws_plant\\n')
  needle='provenance->response_residual,provenance->response_strength);'
  start=adapter.index('    fprintf(f,",%.17g,%.17g,%.17g,%u,%u,%d,')
  end=adapter.index(needle,start)+len(needle)
  block=adapter[start:end].replace('%.17g,%.17g\\n"','%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\\n"').replace(needle,'provenance->response_residual,provenance->response_strength,analysis_ws,previous.evidence.strength[0],previous.evidence.strength[1],previous.evidence.strength[2],previous.evidence.strength[3],previous.evidence.strength[4],previous.evidence.strength[5]);')
  adapter=adapter[:start]+block+adapter[end:]
  path=work/'analysis_adapter.c';path.write_text(adapter);obj=path.with_suffix('.o')
  subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-O2','-Iinclude','-c',str(path),'-o',str(obj)],cwd=ROOT,check=True)
  objects=[str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o']
  objects += [str(ROOT/p) for p in ['src/v7_3/clo_dsf_revised.o','src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7/accepted_main.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o','src/v7_2/final_observation_io.o']]
  exe=work/'analysis_ecu';subprocess.run(['gcc',str(obj),*objects,'-Wl,--wrap=detection_algorithm_step','-Wl,--wrap=cross_layer_fault_step','-Wl,--wrap=sensors_step','-lm','-o',str(exe)],check=True)
  for i,s in enumerate(specs):
   cmd=response.command(s,work);cmd[0]=str(exe);v=subprocess.run(cmd,capture_output=True,text=True);assert not v.returncode,v.stderr
   trace=list(csv.DictReader((work/'trace.csv').open()));metrics={r['method']:r for r in csv.DictReader((work/'metrics.csv').open())}
   # Confirm same committed A0/WS decision stream summaries as original TRAIN records.
   for m,prior in [('Revised CLO-DSF',a[s['run_id']]),('Weighted Sum',ws[s['run_id']])]:
    for k in ['first_alarm_ms','first_post_alarm_ms','alarm_samples','alarm_UNKNOWN']:
     assert int(metrics[m][k])==prior[k],(s['run_id'],m,k)
   active=[];hits=set();streak=0;maxstreak=0;maxbelief=0;maxdiv=0;maxfiltered=0;maxconflict=0;minign=1;maxplaus=0;maxsensor=0;first=None;calexplained=0;support2=0;prior_suspect=-1;recenthits=0
   timeline=[]
   for r in trace:
    t=int(r['time_ms']);weighted=float(r['analysis_ws']);wa=weighted>=.04;timeline.append(int(wa));belief=float(r['anomaly_belief'])
    if belief>=.35:prior_suspect=t
    if not wa:continue
    if first is None:first=t
    active.append(r)
    values=[float(r[k+'_evidence']) for k in ['timing','communication','memory_control','sensor_control','actuator','plant']]
    div=sum(x>0 for x in values);maxdiv=max(maxdiv,div);maxbelief=max(maxbelief,belief);maxsensor=max(maxsensor,values[3]);maxconflict=max(maxconflict,float(r['detection_conflict']));minign=min(minign,float(r['anomaly_ignorance']));maxplaus=max(maxplaus,float(r['anomaly_plausibility']))
    trusted=int(r['target_shadow_valid']) and r['target_register_c']==r['target_shadow_c'] and float(r['control_target_c'])==float(r['target_shadow_c'])
    filtered=weighted-(.2*float(r['ws_memory']) if trusted else 0);maxfiltered=max(maxfiltered,filtered)
    calexplained+=trusted and .2*float(r['ws_memory'])>=.04
    corroborating=values[0]>0 or values[1]>0 or values[2]>0 or values[4]>0;support2+=div>=2
    streak=streak+1 if belief>=.35 else 0;maxstreak=max(maxstreak,streak)
    if belief>=.35:hits.add('WS_and_current_suspect')
    if maxstreak>=2:hits.add('WS_and_suspect_2ticks')
    if div>=2:hits.add('WS_and_two_current_channels')
    if corroborating:hits.add('WS_and_direct_nonsensor_contract')
    if filtered>=.04:hits.add('WS_without_explained_legal_memory')
    if prior_suspect>=0 and t-prior_suspect<=300:hits.add('WS_and_suspect_within_300ms')
   for g in hits:gatecounts[g][chosen[s['run_id']]]+=1
   summary.append(dict(run_id=s['run_id'],cohort=chosen[s['run_id']],first_ws_ms=first,ws_alarm_samples=len(active),ws_timeline_sha256=hashlib.sha256(bytes(timeline)).hexdigest(),legal_memory_explained_samples=calexplained,max_current_belief_during_ws=maxbelief,min_current_ignorance_during_ws=minign,max_current_plausibility_during_ws=maxplaus,max_current_conflict_during_ws=maxconflict,max_current_active_channels=maxdiv,max_current_sensor_during_ws=maxsensor,max_ws_after_removing_explained_memory=maxfiltered,max_suspect_streak_during_ws=maxstreak,gates=';'.join(sorted(hits))))
   for p in (work/'raw').glob('*'):p.unlink()
   for n in ['trace.csv','metrics.csv','observations.csv']:(work/n).unlink()
   if (i+1)%28==0:print('TRAIN diagnostic replays',i+1,'/112',flush=True)
 assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in before.items())
 with (BASE/'runtime_disagreement.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(summary[0]),lineterminator='\n');writer.writeheader();writer.writerows(summary)
 (BASE/'gate_counts.json').write_text(json.dumps(gatecounts,indent=2));print(json.dumps(gatecounts,indent=2));print('TIMELINES',collections.Counter(r['ws_timeline_sha256'] for r in summary))
 for cohort in ['C_WS_only','E_WS_benign_alarm']:
  rr=[r for r in summary if r['cohort']==cohort];print(cohort,{k:(min(r[k] for r in rr),max(r[k] for r in rr)) for k in ['ws_alarm_samples','legal_memory_explained_samples','max_current_belief_during_ws','max_current_active_channels','max_ws_after_removing_explained_memory','max_current_plausibility_during_ws','max_current_conflict_during_ws']})

if __name__=='__main__':main()
