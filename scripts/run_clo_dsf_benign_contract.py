#!/usr/bin/env python3
"""Benign-only empirical contract experiment; no fault-driven fitting or tuning."""
import csv,hashlib,json,math,shutil,subprocess,sys,tempfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'python'),str(ROOT/'scripts')]
import run_clo_dsf_slow_bias_development as prior
import run_clo_dsf_sensor_response as response
from virtual_ecu import clo_dsf_current as c
from virtual_ecu.clo_dsf_holdout import prepare_work,profile_identity,read
from virtual_ecu.clo_dsf_development import write_csv,sha,ORIGINS
from virtual_ecu.clo_dsf_candidate2_development import aggregate
from virtual_ecu.clo_dsf_current_reporting import runtime_stats
OUT=c.OUT;BASE=Path('/tmp/clo-benign-contract')
METHODS=['Pre-change CLO-DSF','Contract only','Revised CLO-DSF','Weighted Sum']
THERMAL_C=r'''
#include "clo_dsf_revised.h"
#include <stdio.h>
#include <math.h>
static double coef[6],bound,lo[4],hi[4];
static unsigned horizon,persistence;
static int loaded;
int thermal_load(const char *path) {
 FILE *f=fopen(path,"r");if(!f)return -1;
 for(int i=0;i<6;i++)if(fscanf(f,"%lf",&coef[i])!=1||!isfinite(coef[i])){fclose(f);return -1;}
 if(fscanf(f,"%lf %u %u",&bound,&horizon,&persistence)!=3 || bound<=0 || !isfinite(bound)||horizon<100||!persistence){fclose(f);return -1;}
 for(int i=0;i<4;i++)if(fscanf(f,"%lf %lf",&lo[i],&hi[i])!=2||!isfinite(lo[i])||!isfinite(hi[i])||hi[i]<lo[i]){fclose(f);return -1;}
 char extra;if(fscanf(f," %c",&extra)==1){fclose(f);return -1;}fclose(f);loaded=1;return 0;
}
double thermal_strength(clo_revised_t *s,const runtime_observation_t *o) {
 s->thermal_evidence=0;s->thermal_residual=0;
 double x[4]={o->engine_load,o->vehicle_speed_kph/100.,o->ambient_c/40.,(o->pump_actual+o->fan_actual)/2.};
 int valid=loaded&&o->source_valid&&o->source_ms==o->time_ms&&isfinite(o->source_c);
 for(int i=0;i<4;i++)if(!isfinite(x[i])||x[i]<lo[i]-.05*(hi[i]-lo[i])||x[i]>hi[i]+.05*(hi[i]-lo[i]))valid=0;
 if(!valid){s->thermal_valid=false;s->thermal_streak=0;return 0;}
 if(!s->thermal_valid||o->time_ms!=s->thermal_ms+100||o->time_ms-s->thermal_anchor_ms>=horizon) {
  s->thermal_valid=true;s->thermal_pred=o->source_c;s->thermal_anchor_ms=o->time_ms;s->thermal_streak=0;
 } else {
  double rate=coef[0]+coef[5]*s->thermal_pred/100.;
  for(int i=0;i<4;i++)rate+=coef[i+1]*s->thermal_context[i];
  s->thermal_pred+=.1*rate;
  s->thermal_residual=o->source_c-s->thermal_pred;
  int sign=s->thermal_residual>0?1:-1;
  if(fabs(s->thermal_residual)>bound) {
   s->thermal_streak=sign==s->thermal_sign?s->thermal_streak+1:1;s->thermal_sign=sign;
   if(s->thermal_streak>=persistence)s->thermal_evidence=fmin(1.,(fabs(s->thermal_residual)-bound)/2.);
  } else s->thermal_streak=0;
 }
 s->thermal_ms=o->time_ms;for(int i=0;i<4;i++)s->thermal_context[i]=x[i];
 return s->thermal_evidence;
}
'''

def design():
 faults=[s for s in prior.design() if s['origin']!='NORMAL']
 specs=[]
 for s in faults:
  s=dict(s);s['run_id']=s['run_id'].replace('slow_','contract_');s['profile']=s['profile'].replace('slow_','contract_');s['group']=s['group'].replace('slow_','contract_');s['seed']+=170003;s['start_ms']+=600
  profile=json.loads(s['profile_json'])
  for seg in profile:seg['ambient_temp_c']+=.27;seg['vehicle_speed_kph']+=.7
  s['profile_json']=json.dumps(profile,sort_keys=True);s['profile_semantic_sha256']=profile_identity(profile);specs.append(s)
 for j in range(360):
  train=j<240;k=j if train else j-240
  load=[.30,.45,.60,.75,.97][k%5] if train else [.38,.53,.68,.83,.94][k%5]
  ambient=[18,24,30,36,42][(k//5)%5] if train else [21,27,33,39][(k//5)%4]
  speed=[5,30,60,90,115][(k//25)%5] if train else [17,43,73,103][(k//20)%4]
  profile=[dict(start_ms=a,end_ms=b,vehicle_speed_kph=speed*f,engine_load=load*f,ambient_temp_c=ambient+(0 if z<2 else 1.7),external_airflow_factor=0,road_slope_percent=0) for z,(a,b,f) in enumerate([(0,17300,.67),(17300,41700,1),(41700,73300,.71),(73300,120000,.89)])]
  # Tiny unique context offsets prevent exact profile reuse without changing domains.
  for seg in profile:seg['ambient_temp_c']+=j*.00031
  updates=[[32100,99],[64700,92]] if k%2 else []
  s=dict(run_id=f'contract_benign_{j:04}',origin='NORMAL',model='baseline',behavior='none',magnitude=0,stuck_polarity=0,start_ms=120100,duration_ms=0,group=f'benign_{"train" if train else "validation"}_{k//15}',partition='benign-characterization' if train else 'development-validation',profile=f'contract_benign_profile_{j:04}',profile_json=json.dumps(profile,sort_keys=True),target_updates_json=json.dumps(updates),workload='authorized_updates' if updates else 'static_target',seed=310001+j*17,simulation_duration_ms=120000,sensor_ramp_rise_ms=0,sensor_variation=['0:0:8600','0.025:0:8600','0.065:0:8600','0.095:0:8600','0.04:1.4:14600','0.08:2.4:8200'][k%6],initially_latent_stuck=0)
  s['profile_semantic_sha256']=profile_identity(profile);specs.append(s)
 for s in specs:
  s.pop('configuration_sha256',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()
 assert len(specs)==1080 and len({s['profile_semantic_sha256'] for s in specs})==1080
 return specs

def sample_rows(work):
 result=[]
 for t,o in zip(read(work/'trace.csv'),read(work/'observations.csv')):
  def f(k):return float.fromhex(o[k])
  result.append((int(t['time_ms']),float(t['source_c']),f('engine_load'),f('vehicle_speed_kph')/100,f('ambient_c')/40,(f('pump_actual')+f('fan_actual'))/2))
 return result

def fit(streams):
 # Normal equations for a deliberately reduced contextual rate model. Pump and
 # fan are collapsed into one cooling index: not a copy/inversion of plant code.
 mat=[[0.]*6 for _ in range(6)];rhs=[0.]*6;count=0
 for rs in streams:
  for i in range(0,len(rs)-10,10):
   block=rs[i:i+10];x=[1.,*[sum(r[k] for r in block)/10 for k in range(2,6)],sum(r[1] for r in block)/1000]
   y=rs[i+10][1]-rs[i][1];count+=1
   for j in range(6):
    rhs[j]+=x[j]*y
    for k in range(6):mat[j][k]+=x[j]*x[k]
 for i in range(1,6):mat[i][i]+=.1
 aug=[mat[i]+[rhs[i]] for i in range(6)]
 for j in range(6):
  q=max(range(j,6),key=lambda i:abs(aug[i][j]));aug[j],aug[q]=aug[q],aug[j];d=aug[j][j];assert abs(d)>1e-10
  aug[j]=[v/d for v in aug[j]]
  for i in range(6):
   if i!=j:
    d=aug[i][j];aug[i]=[v-d*w for v,w in zip(aug[i],aug[j])]
 coef=[aug[i][-1] for i in range(6)];errors=[]
 for rs in streams:
  pred=rs[0][1];anchor=rs[0][0];peak=0
  for prev,now in zip(rs,rs[1:]):
   if now[0]-anchor>=20000:pred=now[1];anchor=now[0];continue
   x=[1.,*prev[2:6],pred/100];pred+=.1*sum(a*b for a,b in zip(coef,x));peak=max(peak,abs(now[1]-pred))
  errors.append(peak)
 bound=1.25*max(errors)+.20
 ranges=[(min(r[k] for rs in streams for r in rs),max(r[k] for rs in streams for r in rs)) for k in range(2,6)]
 return coef,bound,ranges,errors,count

def build(work):
 header=(ROOT/'include/clo_dsf_revised.h').read_text().replace('    bool response_active;','''    bool response_active;
    double thermal_pred,thermal_residual,thermal_evidence,thermal_context[4];
    unsigned thermal_ms,thermal_anchor_ms,thermal_streak;
    int thermal_sign; bool thermal_valid;''').replace('#endif','int thermal_load(const char *path);\ndouble thermal_strength(clo_revised_t *,const runtime_observation_t *);\n#endif')
 (work/'clo_dsf_revised.h').write_text(header)
 baseline=(ROOT/'src/v7_3/clo_dsf_revised.c').read_text()
 combined=baseline.replace('    s->evidence.strength[3] = fmax(s->evidence.strength[3], local);','    local=fmax(local,thermal_strength(state,o));\n    s->evidence.strength[3] = fmax(s->evidence.strength[3], local);')
 variants={'combined':combined,'a0':baseline,'only':combined.replace('    local=fmax(local,sensor_response(state,o));','    /* 300ms forecast disabled for ablation only. */')}
 objects=[]
 for name,src in variants.items():
  if name!='combined':
   for fn in ['clo_revised_init','clo_revised_extract','clo_revised_step']:src=src.replace(fn,fn.replace('clo_revised','clo_prechange' if name=='a0' else 'clo_contract_only'))
  path=work/(name+'.c');path.write_text(src);obj=path.with_suffix('.o')
  subprocess.run(['gcc','-std=c11','-O2','-I'+str(work),'-Iinclude','-c',str(path),'-o',str(obj)],cwd=ROOT,check=True);objects.append(str(obj))
 adapter=(ROOT/'src/v7_3/revised_runtime.c').read_text()
 adapter=adapter.replace('static clo_revised_t prechange;','static clo_revised_t prechange,contract_only;\nvoid clo_contract_only_step(clo_revised_t *,const clo_final_config_t *,const runtime_observation_t *);')
 adapter=adapter.replace('  clo_final_step(&previous,&config,&o);final_score(2,o.time_ms,&previous.output);','  clo_final_step(&previous,&config,&o);\n  clo_contract_only_step(&contract_only,&config,&o);final_score(2,o.time_ms,&contract_only.fusion.output);')
 adapter=adapter.replace('else if(!strcmp(key,"--revised-evidence"))','else if(!strcmp(key,"--revised-thermal-contract")){if(thermal_load(argv[i]))return 1;}\n   else if(!strcmp(key,"--revised-evidence"))')
 adapter=adapter.replace(' clo_revised_init(&prechange);',' names[2]="Contract only";clo_revised_init(&contract_only);\n clo_revised_init(&prechange);')
 (work/'adapter.c').write_text(adapter);(work/'thermal.c').write_text(THERMAL_C)
 for name in ['adapter','thermal']:
  obj=work/(name+'.o');subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-O2','-I'+str(work),'-Iinclude','-c',str(work/(name+'.c')),'-o',str(obj)],cwd=ROOT,check=True);objects.append(str(obj))
 objects += [str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o']
 objects += [str(ROOT/p) for p in ['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7/accepted_main.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o','src/v7_2/final_observation_io.o']]
 exe=work/'contract_ecu';subprocess.run(['gcc',*objects,'-Wl,--wrap=detection_algorithm_step','-Wl,--wrap=cross_layer_fault_step','-Wl,--wrap=sensors_step','-lm','-o',str(exe)],check=True)
 return exe

def report(rows):
 summaries=[];local=[];conf=[];paired=[]
 for part in ['development-train','development-validation']:
  for method in METHODS:
   rs=[r for r in rows if r['partition']==part and r['method']==method]
   groups={'ALL':rs,**{o:[r for r in rs if r['origin']==o] for o in ORIGINS},'slow_drift':[r for r in rs if r['model']=='sensor_bias_ramp'],'weak_steps':[r for r in rs if r['model']=='sensor_bias' and abs(r['magnitude'])<=1.1],'pulses':[r for r in rs if r['model']=='sensor_interface_intermittent'],'effective_memory':[r for r in rs if r['origin']=='MEMORY' and r['effective_memory_corruption']],'dormant_memory':[r for r in rs if r['model']=='stuck_bit' and not r['effective_memory_corruption']]}
   for group,subset in groups.items():
    if subset:summaries.append(dict(partition=part,method=method,group=group,**aggregate(subset)))
   if method!='Weighted Sum':
    for origin in ['ALL',*ORIGINS]:
     subset=[r for r in rs if origin=='ALL' or r['origin']==origin];local.append(dict(partition=part,method=method,origin=origin,**runtime_stats(subset)))
     conf.append(dict(partition=part,method=method,origin=origin,**{o:sum(r['alarm_'+o] for r in subset) for o in ['UNKNOWN',*ORIGINS]}))
  a={r['run_id']:r for r in rows if r['partition']==part and r['method']=='Pre-change CLO-DSF'}
  for method in ['Contract only','Revised CLO-DSF','Weighted Sum']:
   bb={r['run_id']:r for r in rows if r['partition']==part and r['method']==method};counts=[0]*4
   for k,x in a.items():
    if not x['injected']:continue
    y=bb[k];counts[0 if x['detected'] and y['detected'] else 1 if y['detected'] else 2 if x['detected'] else 3]+=1
   paired.append(dict(partition=part,method=method,both=counts[0],only_method=counts[1],only_a0=counts[2],neither=counts[3]))
 write_csv(OUT/'validation_summary.csv',summaries);write_csv(OUT/'localization_summary.csv',local);write_csv(OUT/'confusion_summary.csv',conf);write_csv(OUT/'ablation_comparison.csv',paired);write_csv(OUT/'case_summary.csv',rows)
 return summaries,local

def main():
 specs=design();assert not {r['profile_semantic_sha256'] for r in records_manifest()}&{s['profile_semantic_sha256'] for s in specs}
 # Clean fitting data are generated first. No fault trace/outcome is accessed.
 with tempfile.TemporaryDirectory(prefix='benign-contract-') as tmp:
  work=Path(tmp);prepare_work(work,specs)
  train=[s for s in specs if s['partition']=='benign-characterization'];streams=[]
  for i,s in enumerate(train):
   cmd=response.command(s,work);assert s['model']=='baseline' and 'baseline' in cmd and '--revised-sensor-ramp' not in cmd
   subprocess.run(cmd,cwd=ROOT,check=True,capture_output=True);streams.append(sample_rows(work))
   for p in (work/'raw').glob('*'):p.unlink()
   for name in ['trace.csv','observations.csv','metrics.csv']:(work/name).unlink()
   if (i+1)%40==0:print('Benign characterization',i+1,'/240',flush=True)
  coef,bound,ranges,errors,n=fit(streams);streams.clear()
  assert all(p.is_file() for p in OUT.iterdir())
  for p in OUT.iterdir():p.unlink()
  write_csv(OUT/'benign_contract_dataset_manifest.csv',specs)
  contract=OUT/'thermal_contract.cfg';contract.write_text(' '.join(format(v,'.17g') for v in coef)+'\n'+format(bound,'.17g')+' 20000 5\n'+'\n'.join(f'{lo:.17g} {hi:.17g}' for lo,hi in ranges)+'\n')
  write_csv(OUT/'characterization_summary.csv',[dict(run_id=s['run_id'],fit_samples=120,free_prediction_max_error_c=e) for s,e in zip(train,errors)])
  frozen={p:sha(ROOT/p) for p in ['src/v7_3/clo_dsf_revised.c','include/clo_dsf_revised.h','src/v7_3/revised_runtime.c','scripts/run_clo_dsf_benign_contract.py','results/clo_dsf_current/thermal_contract.cfg','results/clo_dsf_current/benign_contract_dataset_manifest.csv']}
  (OUT/'validation_record.md').write_text('# Benign-only thermal contract experiment\n\nContract frozen '+datetime.now(timezone.utc).isoformat()+' before any fault evaluation.240 clean TRAIN profiles;120 separate benign VALIDATION profiles;720 fault profiles (480 TRAIN/240 VALIDATION). Total1080 unique simulations.\n\nProtocol: fit ridge(.1) six-coefficient rate model only to measured benign one-second differences. Inputs:intercept/load/speed/ambient/mean actual pump-fan action/previous predicted temperature. Collapse pump/fan into one feature; no thermal plant equations/constants copied. Free-run20s from a measured conditional baseline; do not learn a measured long-term slope. Bound=1.25*maximum TRAIN20s prediction error+0.20C. Runtime requires5 same-sign violating ticks, uses2C normalization and existing global thresholds. Every20s the relative evolution window expires and reanchors; constant pre-existing offsets are not identifiable. Outside calibrated context plus5% margin:abstain. Recover when residual returns inside envelope. No tuning on benign VALIDATION or any faults.\n\nA0=current (existing300ms forecast); contract-only disables only300ms predictor; combined retains it. Original sensor primitives and every other channel/causal rule are common. Research executables built in temporary storage from recorded source and this script; production CURRENT unchanged unless retention criteria pass.\n\nPredeclared retention:at least25% slow-drift detection on VALIDATION, fewer silent plant misses, at most1 benign validation alarm, no wrong origin, no A0 fault detection losses, full effective-memory and preserved origin detection. No cosmetic TRAIN gain retained.\n\nContract fits '+str(n)+' one-second samples; bound='+str(bound)+'C.\n\nFreeze identities:\n```json\n'+json.dumps(frozen,indent=2)+'\n```\n')
  print('CONTRACT FROZEN',coef,'bound',bound,flush=True)
  exe=build(work)
  def command(s,w):return [str(exe),*response.command(s,w)[1:],'--revised-thermal-contract',str(contract)]
  c.command=command;c.METHODS=METHODS
  retain={next(s['run_id'] for s in specs if s['origin']==o and s['partition']!='benign-characterization') for o in [*ORIGINS,'NORMAL']};retain.update(next(s['run_id'] for s in specs if s['model']==m) for m in ['sensor_bias_ramp','sensor_interface_intermittent'])
  evaluation=[s for s in specs if s['partition']!='benign-characterization'];rows=[]
  for i,s in enumerate(evaluation):
   assert all(sha(ROOT/p)==h for p,h in frozen.items())
   rows+=c.execute(s,work,s['run_id'] in retain)
   if (i+1)%60==0:print('Frozen evaluation',i+1,'/840',flush=True)
  summaries,local=report(rows)
  a={r['run_id']:r for r in rows if r['partition']=='development-validation' and r['method']=='Pre-change CLO-DSF'};b={r['run_id']:r for r in rows if r['partition']=='development-validation' and r['method']=='Revised CLO-DSF'}
  slow=[r for r in b.values() if r['model']=='sensor_bias_ramp']
  eligible=sum(r['detected'] for r in slow)>=math.ceil(.25*len(slow)) and sum(r['silent_plant'] for r in b.values())<sum(r['silent_plant'] for r in a.values()) and sum(r['false_alarm'] for r in b.values())<=1 and not any(r['wrong_localized_runtime_samples'] for r in b.values()) and all(r['detected']>=a[k]['detected'] for k,r in b.items())
  with (OUT/'validation_record.md').open('a') as f:f.write('\n1080 unique simulations complete. No fault-driven fitting/tuning. All frozen identities unchanged. Contract retention gate: '+str(eligible)+'.\n')
  print('RETENTION_GATE',eligible,flush=True)

def records_manifest():
 from virtual_ecu.clo_dsf_final_reporting import records
 return records(OUT/'development_manifest.csv')
if __name__=='__main__':main()
