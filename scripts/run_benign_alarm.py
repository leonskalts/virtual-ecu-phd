#!/usr/bin/env python3
"""Provenance confirmation study; original scientific implementation untouched."""
import os,sys,json,csv,base64,zlib,subprocess,hashlib,collections,shutil,pickle
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=['/tmp/clo-ml-deps',str(ROOT/'scripts'),str(ROOT/'python')]
import numpy as np
import run_digital_integrity as old
B=Path('/tmp/clo-benign-alarm');O=ROOT/'results/benign_alarm_development';h=old.h;dump=old.dump;sha=old.sha
AUDIT=r'''
#include "sensor_confirmation.h"
static sensor_confirmation_t ba_gate[5];
static unsigned ba_choice=99;
static FILE *ba_log;
static di_bank_t *ba_current;
double ba_provider[7];
void ba_capture(const clo_revised_t *s,const runtime_observation_t *o,double qualified){
 if(plus_arch!=6)return;
 if(!ba_log)ba_log=fopen(getenv("BA_LOG"),"w");
 const clo_evidence_t *e=&s->fusion.evidence;unsigned other=0;
 for(unsigned i=0;i<6;i++)if(i!=3&&e->available[i]&&e->strength[i]>0)other|=1U<<i;
 bool fail=false;for(unsigned i=0;i<3;i++)if(ba_current->until[i]&&o->time_ms<ba_current->until[i])fail=true;
 fprintf(ba_log,"%u,%u,%u,%u,%u,%.17g",o->time_ms,ba_current->available,ba_current->bad,fail,other,qualified);
 for(unsigned i=0;i<6;i++)fprintf(ba_log,",%.17g",e->available[i]?e->strength[i]:0.);
 for(unsigned i=0;i<7;i++)fprintf(ba_log,",%.17g",ba_provider[i]);
 fprintf(ba_log,",%.17g,%u,%u,%u",s->fusion.output.anomaly_decision_score,s->fusion.output.alarm,s->fusion.output.estimated_origin,s->direct_origins);
 const unsigned count[5]={0,2,3,1,3};const double threshold[5]={0,.5,.5,.75,.75};
 if(getenv("BA_CHOICE"))ba_choice=(unsigned)strtoul(getenv("BA_CHOICE"),NULL,10);
 for(unsigned k=0;k<5;k++){
  int alarm=-1;
  if(ba_choice==99||k==0||k==ba_choice)alarm=sensor_confirmation_step(&ba_gate[k],o->time_ms,ba_current->available==7&&!ba_current->bad&&!fail,other||s->direct_origins,qualified,s->fusion.output.alarm,count[k],threshold[k]);
  fprintf(ba_log,",%d",alarm);
 }fprintf(ba_log,"\n");
}
'''
def build(w):
 exe=old.build(w);a=w/'adapter.c';s=a.read_text();needle='static const char *names';assert needle in s;s=s.replace(needle,AUDIT+'\n'+needle,1);s=s.replace('  plus_arch=6;clo_triplex_core_step','  ba_current=di_bank(state);plus_arch=6;clo_triplex_core_step');a.write_text(s)
 e=w/'extended.c';s=e.read_text();s=s.replace('#include <math.h>','#include <math.h>\nextern double ba_provider[7];\nvoid ba_capture(const clo_revised_t *,const runtime_observation_t *,double);')
 s=s.replace('double local = local_sensor_strength(o);','double local = local_sensor_strength(o);ba_provider[0]=s->evidence.strength[3];ba_provider[1]=local;')
 needle='double independent=fmax(sensor_response(state,o),redundant_sensor(state,o));';assert needle in s
 s=s.replace(needle,'ba_provider[2]=local;ba_provider[3]=sensor_response(state,o);ba_provider[4]=redundant_sensor(state,o);double independent=fmax(ba_provider[3],ba_provider[4]);')
 s=s.replace('independent=fmax(independent,fast_redundant_sensor(state,o));','ba_provider[5]=fast_redundant_sensor(state,o);ba_provider[6]=triplex_extra_strength;independent=fmax(independent,ba_provider[5]);')
 needle='if(v->localization_valid && v->localization_timestamp_ms<0)v->localization_timestamp_ms=(int)o->time_ms;';assert needle in s;s=s.replace(needle,needle+'\n    ba_capture(state,o,origin_local);');e.write_text(s)
 obj=w/'sensor_confirmation.o';subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Iinclude','-c','src/v7_3/sensor_confirmation.c','-o',str(obj)],check=True)
 for p in [a,e]:subprocess.run(['gcc','-std=c11','-O2','-Iinclude','-c',str(p),'-o',str(p.with_suffix('.o'))],check=True)
 objs=[str(p) for p in w.glob('*.o') if p.name not in ['dynamic_consensus.o']]+[str(p) for p in (ROOT/'src').glob('*.o') if p.name not in ['main.o','diagnostic_temperature.o']]+[str(ROOT/p) for p in ['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7/accepted_main.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o','src/v7_2/final_observation_io.o']]
 subprocess.run(['gcc',*objs,'-Wl,--wrap=detection_algorithm_step','-Wl,--wrap=cross_layer_fault_step','-Wl,--wrap=sensors_step','-Wl,--wrap=redundant_temperature_sample','-Wl,--wrap=diagnostic_temperature_sample','-lm','-o',str(exe)],check=True);return exe

def load_old():
 p=json.loads((old.O/'study_record.json').read_text());rr=json.loads(zlib.decompress(base64.b85decode(p['case_metrics']['data'])));ss={x['run_id']:x for x in json.loads((old.B/'specs.json').read_text())};return ss,rr

def execute_setup(w,ss):
 w.mkdir(exist_ok=True);h.prepare_work(w,ss);exe=build(w)
 for k,v in [('TRIPLEX_LOG','triplex.csv'),('PLUS_META','plus_meta.csv'),('BENCHMARK_LOG','benchmark.csv'),('DC_INPUT','input.csv'),('DI_LOG','integrity.csv'),('BA_LOG','audit.csv')]:os.environ[k]=str(w/v)
 os.environ['PLUS_HOST_MODE']='2';h.c.METHODS=['M2'];h.c.command=lambda s,w:old.d.r.t.command(s,w,exe)
 return exe

def consecutive(mask):
 count=maximum=0
 for x in mask:
  count=count+1 if x else 0;maximum=max(maximum,count)
 return maximum

def audit():
 B.mkdir(exist_ok=True);O.mkdir(exist_ok=True);assert not (O/'historical_alarm_audit.csv').exists()
 paths=[p for root in ['src','include','scripts','python','tests','presets','results'] for p in (ROOT/root).rglob('*') if p.is_file() and '__pycache__' not in str(p) and 'benign_alarm' not in str(p) and 'sensor_confirmation' not in str(p)];dump(B/'protected.json',{str(p):sha(p) for p in paths})
 ss,rr=load_old();rows=[r for r in rr if r['method']=='A2' and r['run_id'] in ss and ss[r['run_id']]['partition']=='VALIDATION' and (ss[r['run_id']]['origin']!='NORMAL' or r['false_alarm'])];assert len(rows)==1255
 w=B/'audit_work';execute_setup(w,[ss[r['run_id']] for r in rows]);out=[];fault=[];parity=0
 for i,r in enumerate(rows):
  s=ss[r['run_id']];actual=h.c.execute(s,w,False)[0]
  for k in ['detected','false_alarm','first_post_alarm_ms','alarm_samples','wrong_localized_runtime_samples','alarm_UNKNOWN',*['alarm_'+o for o in old.d.r.be.ORIGINS]]:assert actual[k]==r[k],(s['run_id'],k,actual[k],r[k])
  parity+=1;a=np.loadtxt(w/'audit.csv',delimiter=',');alarm=a[:,20]>0;eligible=(a[:,1]==7)&(a[:,2]==0)&(a[:,3]==0)&(a[:,4]==0)&(a[:,22]==0)
  names=['base_acquisition_consumption','absolute_slew','two_edge_slew','trajectory_response','AB_slow','AB_fast','triplex'];providers={n:float(a[alarm,12+j].max()) if alarm.any() else 0 for j,n in enumerate(names)}
  x=dict(run_id=s['run_id'],origin=s['origin'],workload=s['workload'],benign_reference_magnitude=s.get('benign_reference_magnitude'),benign_reference_duration=s.get('benign_reference_duration'),detected=r['detected'],alarm_samples=int(alarm.sum()),integrity_fail_samples=int(np.count_nonzero(a[:,3])),other_support_alarm_samples=int(np.count_nonzero(alarm&(a[:,4]>0))),eligible_alarm_samples=int(np.count_nonzero(alarm&eligible)),sensor_min_at_alarm=float(a[alarm,9].min()) if alarm.any() else 0,sensor_max_at_alarm=float(a[alarm,9].max()) if alarm.any() else 0,qualified_max=float(a[:,5].max()),max_consecutive_qualified_05=consecutive(eligible&(a[:,5]>=.5)),max_consecutive_qualified_075=consecutive(eligible&(a[:,5]>=.75)),**providers)
  (out if s['origin']=='NORMAL' else fault).append(x)
  for name in ['audit.csv','input.csv','integrity.csv','benchmark.csv','triplex.csv','plus_meta.csv']:(w/name).unlink()
  if (i+1)%150==0:print('AUDIT',i+1,'/',len(rows),flush=True)
 h.write(O/'historical_alarm_audit.csv',out);h.write(O/'historical_fault_support_audit.csv',fault);dump(O/'audit_record.json',dict(cases=parity,benign=55,faults=1200,exact_A2_metric_parity=True,scope='Seen root-cause reconstruction only; not selection or new validation. No raw traces retained.'));print('AUDIT COMPLETE',flush=True)

def verify():
 for manifest in ['protected.json','lock.json']:
  if (B/manifest).exists():
   for p,v in json.loads((B/manifest).read_text()).items():assert sha(Path(p))==v,p

def design():
 original=old.design();out=[]
 for s0 in original:
  s=dict(s0);old_index=int(s['run_id'].split('_')[1]);fault=s['origin']!='NORMAL'
  if s['partition']=='TRAIN' and fault and old_index%150%20>=10:continue
  copies=2 if s['partition']=='VALIDATION' and not fault else 1
  for duplicate in range(copies):
   s=dict(s0);i=len(out);f=int(s['group'].split('_')[-1]);s.update(run_id=f'ba_{i:04}',profile=f'ba_profile_{i:04}',group=f'ba_family_{f}',seed=510100001+i*283,reference_seed=610300003+i*293,c_seed=710700007+i*307)
   pp=json.loads(s['profile_json'])
   for j,p in enumerate(pp):p['ambient_temp_c']+=.371+i*.0000047;p['engine_load']*=.993+(f%4)*.007;p['vehicle_speed_kph']+=1.173+i*.000009
   if not fault:
    # Same legal noise/offset envelope across splits; new combinations/streams.
    s['reference_noise']=[.019,.031,.047,.063][(i+f)%4];s['c_noise']=[.009,.017,.029,.041][(i//3+f)%4]
    s['c_quantum']=[.012,.020,.028,.036][(i//5+f)%4]
    if duplicate:
     s['benign_reference_magnitude']=-float(s.get('benign_reference_magnitude',0));s['sensor_variation']=['0.018:0:13700','0.029:0.013:19100','0.037:0.021:23300'][i%3]
     for j,p in enumerate(pp):p['ambient_temp_c']+=.281;p['engine_load']*=1.011;p['vehicle_speed_kph']+=.439
   else:s['start_ms']+=107 if s['origin']=='SENSOR_CONTROL' else 200
   if s['origin']=='SENSOR_CONTROL':s['magnitude']*=.991;s['sensor_ramp_rise_ms']+=433 if s['kind']=='ramp' else 0
   s['c_phase_ms']=(int(s['c_phase_ms'])+6)%100;s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=h.profile_identity(pp);s.pop('configuration_sha256',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();out.append(s)
 assert len(out)==8400
 assert collections.Counter(s['partition'] for s in out)=={'TRAIN':2400,'CALIBRATION':2400,'VALIDATION':3600}
 return out

def setup():
 verify();assert not (B/'specs.json').exists();ss=design();old.d.r.historical.OUT=B;old.d.r.historical.B=B;old.d.r.historical.historical_audit(ss)
 audit=list(csv.DictReader((B/'historical_overlap_audit.csv').open()));profiles={s['profile_semantic_sha256'] for s in ss};ids={s['configuration_sha256'] for s in ss};seeds={str(s['seed']) for s in ss}
 for path in [*list((ROOT/'results').rglob('*.json')),*list(Path('/tmp').glob('clo*/specs.json'))]:
  if B in path.parents or O in path.parents:continue
  try:p=json.loads(path.read_text())
  except (ValueError,OSError):continue
  rows=p if isinstance(p,list) else p.get('manifest',[]) if isinstance(p,dict) else []
  if not isinstance(rows,list) or not rows or not isinstance(rows[0],dict):continue
  op=set();oi=set();osd=set()
  for s in rows:
   if s.get('profile_json'):op.add(h.profile_identity(json.loads(s['profile_json'])))
   elif s.get('profile_semantic_sha256'):op.add(s['profile_semantic_sha256'])
   if s.get('configuration_sha256'):oi.add(s['configuration_sha256'])
   if s.get('seed'):osd.add(str(s['seed']))
  if not(op or oi):continue
  assert not profiles&op,str(path);assert not ids&oi,str(path);assert not seeds&osd,str(path)
  audit.append(dict(source=str(path),sha256=sha(path),rows=len(rows),profile_identities=len(op),configuration_identities=len(oi),seeds=len(osd),profile_overlap=0,configuration_overlap=0,seed_overlap=0))
 assert len(profiles)==len(ss);parts=['TRAIN','CALIBRATION','VALIDATION'];groups=[{s['group'] for s in ss if s['partition']==p} for p in parts];assert all(not a&b for i,a in enumerate(groups) for b in groups[i+1:])
 dump(B/'specs.json',ss);h.write(O/'campaign_manifest.csv',ss);h.write(O/'overlap_audit.csv',audit);shutil.copy2(ROOT/'scripts/benign_alarm_protocol.md',O/'protocol.md')
 dump(O/'registration.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),utc=old.d.r.now(),manifest_sha256=sha(O/'campaign_manifest.csv'),protocol_sha256=sha(O/'protocol.md'),historical_sources=len(audit),overlap=0,partitions={p:dict(collections.Counter(s['origin'] for s in ss if s['partition']==p)) for p in parts}));print('REGISTERED 8400; zero overlap',flush=True)

def frozen_svm():
 p=json.loads((old.O/'study_record.json').read_text());blob=zlib.decompress(base64.b85decode(p['svm_model']['data']));selected=json.loads((old.O/'svm_selection.json').read_text())['selection'];return pickle.loads(blob),selected,hashlib.sha256(blob).hexdigest()

def collect(part):
 verify();assert not (B/(part+'_started')).exists();choice=99
 if part=='VALIDATION':assert (B/'lock.json').exists();choice=json.loads((O/'selection.json').read_text())['selected']
 (B/(part+'_started')).write_text(old.d.r.now());ss=[s for s in json.loads((B/'specs.json').read_text()) if s['partition']==part];w=B/('work_'+part);execute_setup(w,ss);os.environ['BA_CHOICE']=str(choice);model,svm_selection,model_hash=frozen_svm();rows=[];audits=[]
 for i,s in enumerate(ss):
  base=h.c.execute(s,w,False)[0];base['method']='A2 original';a=np.loadtxt(w/'input.csv',delimiter=',');it=np.loadtxt(w/'integrity.csv',delimiter=',');q=np.loadtxt(w/'audit.csv',delimiter=',');e=old.d.bench.evidence(np.loadtxt(w/'benchmark.csv',delimiter=','),6);assert np.array_equal(a[:,0],q[:,0]) and np.array_equal(a[:,0],e.time_ms)
  base['integrity_observed']=int(np.any(it[:,2]));base['integrity_samples']=int(np.count_nonzero(it[:,2]));rows.append(base)
  assert np.array_equal(q[:,20],q[:,23]),s['run_id']
  bypass=(q[:,1]!=7)|(q[:,2]>0)|(q[:,3]>0)|(q[:,4]>0)|(q[:,22]>0)
  for k in range(5) if choice==99 else sorted({0,choice}):
   assert np.array_equal(q[bypass,23+k],q[bypass,20]),(s['run_id'],k,'bypass')
   assert not np.any((q[:,23+k]>0)&(q[:,20]==0)),(s['run_id'],k,'invented alarm')
  for k in range(1,5) if choice==99 else [choice]:
   alarm=q[:,23+k]>0;origin=np.where(alarm,q[:,21].astype(int)>>1,0);name='G'+str(k) if choice==99 else 'Refined';rows.append(old.d.bench.score(base,e,name,(alarm,origin)))
  payload=dict(input=a,integrity=it[:,1:],values=e.strength,available=e.available,subset=e.origin_subset);margin=old.d.ml.margin(model,old.features(payload))
  for threshold,name in [(0,'default'),(svm_selection['threshold'],'CAL1')]:rows.append(old.d.bench.score(base,e,'SVM-INT '+name,(margin>threshold,np.zeros(len(margin),int))))
  if not base['injected'] and base['false_alarm']:
   alarm=q[:,20]>0;audits.append(dict(run_id=s['run_id'],partition=part,workload=s['workload'],baseline_alarm_samples=int(alarm.sum()),integrity_fail_samples=int(np.count_nonzero(it[:,2])),other_support_alarm_samples=int(np.count_nonzero(alarm&(q[:,4]>0))),qualified_peak=float(q[alarm,5].max()),max_consecutive_05=consecutive((q[:,5]>=.5)&(q[:,1]==7)&(q[:,3]==0)&(q[:,4]==0)&(q[:,22]==0)),**{f'G{k}_alarm_samples':int(np.count_nonzero(q[:,23+k]>0)) for k in range(1,5) if choice==99 or k==choice}))
  for name in ['audit.csv','input.csv','integrity.csv','benchmark.csv','triplex.csv','plus_meta.csv']:(w/name).unlink()
  if (i+1)%150==0:print(part,i+1,'/',len(ss),flush=True)
 dump(B/(part+'_rows.json'),rows);h.write(O/(part.lower()+'_benign_audit.csv'),audits or [dict(note='No baseline benign alarms')]);verify();print('COMPLETE',part,flush=True)

def select():
 verify();records=[];parts={p:json.loads((B/(p+'_rows.json')).read_text()) for p in ['TRAIN','CALIBRATION']}
 for k in range(5):
  m='A2 original' if not k else 'G'+str(k);rec=dict(index=k,method=m);eligible=True
  for part,rr in parts.items():
   b={x['run_id']:x for x in rr if x['method']=='A2 original'};a={x['run_id']:x for x in rr if x['method']==m};fault=[x for x in b.values() if x['injected']];lost=[key for key,x in b.items() if x['detected'] and not a[key]['detected']];pl=[key for key in lost if b[key]['plant_manifestation']];it=[key for key in lost if b[key]['integrity_observed']];wrong=sum(bool(x['wrong_localized_runtime_samples']) for x in a.values() if x['injected']);ben=sum(x['false_alarm'] for x in a.values());rec[part]=dict(detected=sum(x['detected'] for x in a.values()),benign=ben,lost=lost,plant_lost=pl,integrity_lost=it,wrong_fault_runs=wrong)
   eligible &= not pl and not it and not wrong and len(lost)<=.0025*len(fault) and (part!='CALIBRATION' or ben<=6)
  rec['eligible']=bool(eligible);records.append(rec)
 good=[x for x in records if x['eligible']];winner=min(good,key=lambda x:(x['CALIBRATION']['benign'],x['TRAIN']['benign'],len(x['TRAIN']['lost'])+len(x['CALIBRATION']['lost']),x['index'])) if good else records[0]
 model,svm_selection,mhash=frozen_svm();dump(O/'selection.json',dict(selected=winner['index'],eligible=bool(good),family=records,svm_unchanged=dict(sha256=mhash,**svm_selection),selection_data='NEW TRAIN/CAL only'))
 paths=[ROOT/p for p in ['include/sensor_confirmation.h','src/v7_3/sensor_confirmation.c','tests/test_sensor_confirmation.py','scripts/run_benign_alarm.py','scripts/benign_alarm_protocol.md','scripts/report_benign_alarm.py','scripts/finalize_benign_alarm.py']]+[B/'specs.json',O/'campaign_manifest.csv',O/'overlap_audit.csv',O/'protocol.md',O/'selection.json',O/'registration.json']
 dump(B/'lock.json',{str(p):sha(p) for p in paths});print('LOCKED',winner,flush=True)
if __name__=='__main__':
 if sys.argv[1]=='collect':collect(sys.argv[2])
 else:globals()[sys.argv[1]]()
