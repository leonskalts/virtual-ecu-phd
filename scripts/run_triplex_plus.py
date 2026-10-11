#!/usr/bin/env python3
"""One new Triplex-Plus development study; frozen production sources untouched."""
import sys,os,json,inspect,subprocess,hashlib,shutil,time,collections,pickle
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'python')]
import numpy as np
import run_clo_dsf_triplex as t
import run_comparative_benchmark as bench
import run_clo_dsf_triplex_final_unseen as historical
from virtual_ecu import comparative_backends as be
from virtual_ecu.clo_dsf_candidate2_development import derived
h=t.h;B=Path('/tmp/clo-triplex-plus');O=ROOT/'results/triplex_plus_development';sha=t.sha
NAMES=['A0','M500','M250','S0','S500','S250']
def dump(p,v):p.write_text(json.dumps(v,indent=2))
def now():return datetime.now(timezone.utc).isoformat()
def verify():
 bench.verify();bench.check_lock()
 prior=ROOT/'results/comparative_benchmark'
 assert all(sha(prior/p)==v for p,v in json.loads((prior/'artifact_hashes.json').read_text()).items())
 if (B/'initial.json').exists():assert all(sha(Path(p))==v for p,v in json.loads((B/'initial.json').read_text()).items())
 if (O/'validation_lock.json').exists():assert all(sha(Path(p))==v for p,v in json.loads((O/'validation_lock.json').read_text())['files'].items())

FRONT=r'''
#include "triplex_plus.h"
#include "multirate_memory.h"
#include <time.h>
static unsigned plus_arch;
static plus_stagger_t stagger;
static redundant_temperature_t stagger_b;
static diagnostic_temperature_t stagger_c;
static unsigned next_b=33,next_c=66,previous_physical_ms;
static float previous_physical;
static bool plus_initialized;
static memory_diagnostic_t plus_memory[2];
static clo_revised_t plus_detector[5];
static FILE *plus_meta;
static unsigned long plus_acquisitions[3];
static double sensor_cpu,memory_cpu[2],core_cpu[6];
static unsigned plus_host_mode=99;
static bool plus_sensor_enabled(void){return plus_host_mode==99||plus_host_mode>=3;}
static bool plus_memory_enabled(unsigned i){return plus_host_mode==99||plus_host_mode==i+1||plus_host_mode==i+4;}
static double cpu(void){return (double)clock()/CLOCKS_PER_SEC;}
static void plus_memory_acquire(ecu_state_t *state){
 if(!state->log_file)return;
 for(unsigned k=0;k<2;k++)if(plus_memory_enabled(k)){
  uint16_t before=state->control.target_register_c;double begin=cpu();
  mr_memory_step(&plus_memory[k],state->time.time_ms,k?250:500,cross_layer_memory_read,cross_layer_memory_write,state);
  memory_cpu[k]+=cpu()-begin;if(before!=state->control.target_register_c)abort();
 }
}
static void plus_b_variation(diagnostic_readout_t *);
static void plus_acquire(ecu_state_t *state,const runtime_observation_t *o){
 if(!plus_sensor_enabled())return;
 double begin=cpu();unsigned now=o->time_ms;float physical=state->plant.coolant_temp_true_c;
 stagger.strength=0;
 if(!plus_initialized){previous_physical=physical;previous_physical_ms=now;plus_initialized=true;}
 /* Physical interpolation exists ONLY in the unchanged sensor-model boundary.
  * Runtime evidence sees timestamped readouts in chronological order. A(now)
  * is delivered AFTER all earlier B/C conversions, never used to predict them. */
 while(next_b<=now||next_c<=now){
  unsigned at=next_b<next_c?next_b:next_c;
  double w=now>previous_physical_ms?(double)(at-previous_physical_ms)/(now-previous_physical_ms):1;
  float physical_at=previous_physical+(float)w*(physical-previous_physical);
  if(at==next_b){
   redundant_temperature_sample(&stagger_b,at,physical_at);next_b+=100;plus_acquisitions[1]++;
   diagnostic_readout_t v={.value_c=stagger_b.value_c,.sample_ms=stagger_b.sample_ms,.valid=stagger_b.valid,.failed=stagger_b.failed};
   inject_value(&v.value_c,1,at);plus_b_variation(&v);plus_stagger_readout(&stagger,1,&v);
  }else{
   diagnostic_temperature_sample(&stagger_c,at,physical_at);next_c+=100;plus_acquisitions[2]++;
   diagnostic_readout_t v=stagger_c.output;inject_value(&v.value_c,2,v.sample_ms);plus_stagger_readout(&stagger,2,&v);
  }
  plus_stagger_pairs(&stagger,at);
 }
 diagnostic_readout_t a={.value_c=o->source_c,.sample_ms=o->source_ms,.valid=o->source_valid};
 plus_stagger_readout(&stagger,0,&a);plus_acquisitions[0]++;plus_stagger_pairs(&stagger,now);
 previous_physical=physical;previous_physical_ms=now;sensor_cpu+=cpu()-begin;
}
static void plus_sensor_observation(runtime_observation_t *o){
 double a=0,b=0,c=0,ua=0,ub=0,uc=0;
 bool va=plus_stagger_align(&stagger,0,o->time_ms,&a,&ua);
 bool vb=plus_stagger_align(&stagger,1,o->time_ms,&b,&ub);
 bool vc=plus_stagger_align(&stagger,2,o->time_ms,&c,&uc);
 o->reference_enabled=true;o->reference_valid=va&&vb;o->reference_failed=false;o->reference_ms=o->time_ms;
 if(va&&vb)o->reference_c=o->source_c+(float)plus_conservative_difference(b-o->source_c,ub);
 triplex_extra_strength=stagger.strength;
 triplex_extra_ambiguous=va&&vb&&vc&&fabs(a-b)>.90+ua+ub&&fabs(a-c)>.90+ua+uc&&fabs(b-c)>.90+ub+uc;
 if(o->time_ms>500&&(stagger_c.output.failed||(stagger_c.output.valid&&o->time_ms>stagger_c.output.sample_ms+200)))triplex_extra_strength=1;
}
'''
HELPER=r'''
static void plus_b_variation(diagnostic_readout_t *r){
 unsigned now=r->sample_ms;
 if(!reference_fault_kind||now<reference_fault_start)return;
 unsigned age=now-reference_fault_start;
 if(reference_fault_duration&&age>=reference_fault_duration)return;
 if(reference_fault_period&&age%reference_fault_period>=reference_fault_period/2)return;
 if(reference_fault_kind==3){r->valid=false;r->failed=true;return;}
 float amount=reference_fault_magnitude;
 if(reference_fault_kind==1)amount*=fminf(1,(float)age/reference_fault_rise);
 if(reference_fault_kind==4){unsigned phase=(now/100)%6;amount*=phase==0||phase==3?1:phase==1||phase==4?-.5f:0;}
 r->value_c+=amount;
}
'''
INIT=r'''
 plus_meta=fopen(getenv("PLUS_META"),"w");if(!plus_meta)return 1;
 if(getenv("PLUS_HOST_MODE"))plus_host_mode=(unsigned)strtoul(getenv("PLUS_HOST_MODE"),NULL,10);
 names[0]="CURRENT";names[1]="A0";
 const char *extra_names[]={"M500","M250","S0","S500","S250"};
 for(unsigned j=0;j<5;j++){names[j+2]=extra_names[j];clo_revised_init(&plus_detector[j]);}
 plus_stagger_init(&stagger);
 redundant_temperature_init(&stagger_b,reference_seed,reference_offset,reference_noise);
 diagnostic_temperature_init(&stagger_c,seed,offset,gain,noise,quantum,reference,100,66,lag);
'''
STEP=r'''
 const unsigned memory_index[5]={1,2,0,1,2};
 for(unsigned j=0;j<5;j++){
  if(plus_host_mode!=99&&plus_host_mode!=j+1)continue;
  runtime_observation_t x=o;
  if(memory_index[j]){
   memory_diagnostic_t *m=&plus_memory[memory_index[j]-1];
   x.memory_check_ms=m->checked_ms;x.memory_check_valid=m->valid;x.memory_check_failed=m->failed;
  }
  triplex_extra_strength=triplex.strength;triplex_extra_ambiguous=triplex.ambiguous;
  if(j>=2)plus_sensor_observation(&x);
  plus_arch=j+1;double begin=cpu();clo_triplex_core_step(&plus_detector[j],&config,&x);
  core_cpu[j+1]+=cpu()-begin;clo_final_diagnostic(&plus_detector[j].fusion.evidence,o.time_ms,3000);
  final_score(j+2,o.time_ms,&plus_detector[j].fusion.output);
 }
 fprintf(plus_meta,"%u,%u,%u,%u,%lu,%lu,%lu,%.9g,%.9g,%.9g,%.9g,%u,%u,%zu",o.time_ms,state->control.memory_diagnostic.checks,plus_memory[0].checks,plus_memory[1].checks,plus_acquisitions[0],plus_acquisitions[1],plus_acquisitions[2],sensor_cpu,memory_cpu[0],memory_cpu[1],core_cpu[0],stagger.accepted_pairs,stagger.rejected_alignment,sizeof(plus_stagger_t)+sizeof(stagger_b)+sizeof(stagger_c));
 const clo_revised_t *all[6]={&triplex_detector,&plus_detector[0],&plus_detector[1],&plus_detector[2],&plus_detector[3],&plus_detector[4]};
 for(unsigned j=0;j<6;j++)fprintf(plus_meta,",%u,%u",all[j]->fusion.output.alarm,all[j]->fusion.output.estimated_origin);
 fprintf(plus_meta,"\n");
'''
def adapt(adapter):
 capture=bench.CAPTURE.replace(' const clo_evidence_t *e=', ' if(arch==0)return;arch=plus_arch;\n const clo_evidence_t *e=')
 pos=adapter.index('static const char *names');adapter=adapter[:pos]+FRONT+capture+'\n'+adapter[pos:]
 needle='cross_layer_memory_read,cross_layer_memory_write,state);\n}';assert needle in adapter
 adapter=adapter.replace(needle,'cross_layer_memory_read,cross_layer_memory_write,state);\n if(enabled)plus_memory_acquire(state);\n}',1)
 adapter=adapter.replace('static const char *metrics_path;',HELPER+'\nstatic const char *metrics_path;')
 adapter=adapter.replace('runtime_observation_capture(state,&o);','runtime_observation_capture(state,&o);plus_acquire(state,&o);')
 adapter=adapter.replace('names[0]="A0";','benchmark_log=fopen(getenv("BENCHMARK_LOG"),"w");if(!benchmark_log)return 1;names[0]="A0";')
 adapter=adapter.replace(' triplex_consistency_init(&triplex);clo_revised_init(&triplex_detector);',' triplex_consistency_init(&triplex);clo_revised_init(&triplex_detector);\n'+INIT)
 needle='  clo_triplex_core_step(&triplex_detector,&config,&o);clo_final_diagnostic(&triplex_detector.fusion.evidence,o.time_ms,3000);'
 adapter=adapter.replace(needle,'  plus_arch=0;double begin=cpu();\n'+needle+'\n  core_cpu[0]+=cpu()-begin;')
 adapter=adapter.replace('  final_score(1,o.time_ms,&triplex_detector.fusion.output);','  final_score(1,o.time_ms,&triplex_detector.fusion.output);\n'+STEP)
 return adapter

def build(w):
 source=inspect.getsource(t.build)
 prototype='\nvoid benchmark_capture(unsigned,const clo_revised_t *,const runtime_observation_t *,double,double);\n'
 source=source.replace("core=(ROOT/'src/v7_3/clo_dsf_revised.c').read_text();bridge=core+", "core=(ROOT/'src/v7_3/clo_dsf_revised.c').read_text();core=core.replace('#include <math.h>', '#include <math.h>'+"+repr(prototype)+");core=core.replace('    unsigned int direct=0, direct_count=0;', '    benchmark_capture(0,state,o,origin_local,local);\\n    unsigned int direct=0, direct_count=0;');bridge=core+")
 source=source.replace('extended=core\n',"extended=core.replace('benchmark_capture(0,','benchmark_capture(1,')\n")
 source=source.replace(' objs=[]',' adapter=adapt(adapter)\n objs=[]')
 source=source.replace("'src/v7_3/triplex_consistency.c']","'src/v7_3/triplex_consistency.c','src/v7_3/triplex_plus.c','src/v7_3/multirate_memory.c']")
 ns=dict(t.__dict__,adapt=adapt);exec(source,ns);return ns['build'](w)

def design():
 templates=t.prior.design();cs=t.design();ss=[]
 for f in range(21):
  for j in range(150):
   i=f*150+j;s=dict(templates[(f%16)*150+j]);c=cs[(f%16)*150+j]
   for k in ['c_offset','c_gain','c_noise','c_quantum','c_adc_gain','c_phase_ms','c_lag_ms']:s[k]=c[k]
   s.update(run_id=f'plus_{i:04}',profile=f'plus_profile_{i:04}',group=f'plus_family_{f}',partition='TRAIN' if f<10 else 'CALIBRATION' if f<15 else 'VALIDATION',seed=1913000003+i*193,reference_seed=1973000011+i*197,c_seed=1997000033+i*199,domain='NONE',kind='none')
   pp=json.loads(s['profile_json'])
   for p in pp:p['engine_load']*=.977;p['ambient_temp_c']+=.817+f*.029+j*.000043;p['vehicle_speed_kph']+=1.731+i*.000029
   if s['origin']!='NORMAL':s['start_ms']+=100*(1+(f+j)%11)
   if s['origin']=='MEMORY':
    s['start_ms']=21700+f*500+(j%10)*100
    if s['behavior']!='permanent':s['duration_ms']=[100,200,400,700,1300,2300][(j+f)%6]
   if s['origin']=='SENSOR_CONTROL':
    k=j-72;domain=['A','B','AB'][k//8];cell=k%8;kind=['ramp','step','pulse'][(cell+f+k//8)%3]
    mag=(-1 if (cell+f)%2 else 1)*(2.71+f*.013 if kind=='ramp' else [.49,.65,.81,1.01][(cell+f)%4])
    duration=[50,100,150,250,500,900][(cell+f)%6] if kind=='pulse' else 0
    s.update(domain=domain,kind=kind,sensor_chain=domain,model={'ramp':'sensor_bias_ramp','step':'sensor_bias','pulse':'sensor_interface_intermittent'}[kind],behavior='transient' if duration else 'permanent',magnitude=mag,duration_ms=duration,sensor_ramp_rise_ms=[21300,41300,65300,85700][(cell+f)%4] if kind=='ramp' else 0,start_ms=23717+f*271+cell*337,initially_latent_stuck=0,target_updates_json='[]',workload='plus_sensor')
   s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=h.profile_identity(pp);s.pop('configuration_sha256',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();ss.append(s)
 return ss

def setup():
 verify();assert not (B/'registered.json').exists()
 paths=[p for root in ['src','include','scripts','python'] for p in Path(root).rglob('*') if p.is_file() and p.suffix in ['.c','.h','.py'] and 'triplex_plus' not in p.name]+[Path('presets/gui_session_state.json')]
 dump(B/'initial.json',{str(p):sha(p) for p in paths})
 ss=design();assert len(ss)==3150
 historical.OUT=O;historical.B=B;count=historical.historical_audit(ss)
 h.write(O/'campaign_manifest.csv',ss);dump(B/'specs.json',ss)
 dump(B/'registered.json',dict(utc=now(),manifest_sha256=sha(O/'campaign_manifest.csv'),protocol_sha256=sha(O/'protocol.md'),historical_sources=count,overlap=0))
 print('REGISTERED3150 TRAIN1500 CAL750 VALID900; zero overlap',flush=True)

def run(part):
 verify();assert not (B/(part+'_started')).exists()
 ss=[s for s in json.loads((B/'specs.json').read_text()) if s['partition']==part];w=B/'work';w.mkdir(exist_ok=True);h.prepare_work(w,ss);exe=build(w)
 for key,name in [('TRIPLEX_LOG','triplex.csv'),('PLUS_META','plus_meta.csv'),('BENCHMARK_LOG','benchmark.csv')]:os.environ[key]=str(w/name)
 h.c.METHODS=NAMES;h.c.command=lambda s,w:t.command(s,w,exe);read0=h.c.read;cache={}
 def read(p):
  rr=read0(p)
  if Path(p).name=='observations.csv':cache['obs']=rr
  return rr
 h.c.read=read
 tape=B/'tapes'/part;tape.mkdir(parents=True,exist_ok=True);rows=[]
 (B/(part+'_started')).write_text(now())
 with (B/(part+'_checkpoint.jsonl')).open('w') as ck:
  for i,s in enumerate(ss):
   start=time.perf_counter();rr=h.c.execute(s,w,False);elapsed=time.perf_counter()-start
   a=np.loadtxt(w/'benchmark.csv',delimiter=',');meta=np.loadtxt(w/'plus_meta.csv',delimiter=',');last=meta[-1]
   ev=[bench.evidence(a,k) for k in range(6)]
   obs=[o for o in cache['obs'] if h.prior.prior.active(s,int(o['time_ms']))];axis='pump_command' if s['model']=='pump_degraded' else 'fan_command'
   num=lambda x:float.fromhex(x) if '0x' in str(x).lower() else float(x)
   for r in rr:r.update(initially_excited=int(s['origin']=='ACTUATOR' and bool(obs) and num(obs[0][axis])>0),actuator_excited=int(s['origin']=='ACTUATOR' and any(num(o[axis])>0 for o in obs)),old_probe_count=int(last[1]),probe_count500=int(last[2]),probe_count250=int(last[3]),sensor_acquisitions_A=int(last[4]),sensor_acquisitions_B=int(last[5]),sensor_acquisitions_C=int(last[6]),sensor_cpu=float(last[7]),memory_cpu500=float(last[8]),memory_cpu250=float(last[9]),old_core_cpu=float(last[10]),accepted_pairs=int(last[11]),rejected_alignment=int(last[12]),sensor_state_bytes=int(last[13]),host_seconds=elapsed)
   y=np.array([s['origin']!='NORMAL' and ((s['start_ms']<=ms and (not s['duration_ms'] or ms<s['start_ms']+s['duration_ms']+100)) if s['origin']=='SENSOR_CONTROL' else (h.prior.prior.active(s,int(ms)) or h.prior.prior.active(s,max(0,int(ms)-99)))) for ms in ev[0].time_ms])
   np.savez_compressed(tape/(s['run_id']+'.npz'),time=ev[0].time_ms,values=np.stack([e.strength for e in ev]),available=np.stack([e.available for e in ev]),subsets=np.stack([e.origin_subset for e in ev]),alarm_origin=meta[:,14:].reshape(-1,6,2).astype(int),y=y)
   rows.extend(rr);ck.write(json.dumps(rr)+'\n');ck.flush()
   for name in ['benchmark.csv','plus_meta.csv','triplex.csv']:(w/name).unlink()
   if (i+1)%50==0:print(part,i+1,'/',len(ss),flush=True)
 dump(B/(part+'_rows.json'),rows);h.write(O/(part.lower()+'_ablation.csv'),[dict(method=m,**bench.summary([r for r in rows if r['method']==m])) for m in NAMES]);(B/(part+'_complete')).write_text(now());shutil.rmtree(w);verify()

if __name__=='__main__':
 if sys.argv[1]=='setup':setup()
 elif sys.argv[1]=='run':run(sys.argv[2])
