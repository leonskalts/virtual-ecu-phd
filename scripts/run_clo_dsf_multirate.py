#!/usr/bin/env python3
"""Multi-rate DEVELOPMENT ablations; retained detector and plant untouched."""
import sys,os,json,inspect,hashlib,time,subprocess,shutil,collections
from pathlib import Path
import numpy as np
import run_clo_dsf_triplex as t
h=t.h;ROOT=t.ROOT;O=ROOT/'results/clo_dsf_current';B=Path('/tmp/clo-multirate')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
NAMES=['A0','A1','S50','S25','M500','M250','B50_500','B50_250','B25_500','B25_250']
FRONT=r'''
#include "multirate_triplex.h"
#include "multirate_memory.h"
#include <time.h>
static diagnostic_temperature_t mr_sensor[2][3];
static mr_triplex_t mr_evidence[2];
static memory_diagnostic_t mr_memory[2];
static clo_revised_t mr_detectors[8];
static unsigned mr_last_ms,mr_selected_sensor,mr_selected_memory;
static float mr_last_physical;
static bool mr_initialized,mr_validation;
static double mr_pending[2],mr_sensor_seconds[2],mr_memory_seconds[2],mr_core_seconds[10];
static bool mr_pending_ambiguous[2];
static unsigned long mr_acquisitions[2];
static FILE *mr_log,*mr_meta;
static float sensor_variation(unsigned int);
static void mr_reference_adjust(diagnostic_readout_t *);
static double seconds(void){return (double)clock()/CLOCKS_PER_SEC;}
static bool mr_enabled(unsigned s,unsigned m){return !mr_validation||((!s||s==mr_selected_sensor)&&(!m||m==mr_selected_memory));}
static void mr_memory_acquire(ecu_state_t *state){
 if(!enabled||!state->log_file)return;
 for(unsigned k=0;k<2;k++){
  unsigned rate=k?250:500;if(!mr_enabled(0,rate))continue;
  uint16_t before=state->control.target_register_c;double begin=seconds();
  mr_memory_step(&mr_memory[k],state->time.time_ms,rate,cross_layer_memory_read,cross_layer_memory_write,state);
  mr_memory_seconds[k]+=seconds()-begin;
  if(before!=state->control.target_register_c)abort();
 }
}
static void mr_acquire(ecu_state_t *state){
 if(!state->log_file)return;
 unsigned now=state->time.time_ms;float physical=state->plant.coolant_temp_true_c;
 for(unsigned k=0;k<2;k++){mr_pending[k]=0;mr_pending_ambiguous[k]=false;}
 if(!mr_initialized){mr_last_physical=physical;mr_initialized=true;}
 for(unsigned k=0;k<2;k++){
  unsigned period=k?25:50;if(!mr_enabled(period,0))continue;double begin=seconds();
  for(unsigned at=mr_last_ms+period;at<=now;at+=period){
   /* Sensor-model boundary only: linear within-step interpolation, as retained C.
    * Samples are delivered in a batch at now; control never consumes them. */
   float at_physical=mr_last_physical+(physical-mr_last_physical)*(float)(at-mr_last_ms)/(now-mr_last_ms);
   float values[3];bool valid=true;
   for(unsigned member=0;member<3;member++){
    diagnostic_temperature_t *sensor=&mr_sensor[k][member];
    unsigned previous_next=sensor->next_ms;
    if(diagnostic_temperature_sample(sensor,at,at_physical)){
     mr_acquisitions[k]+=(sensor->next_ms-previous_next)/period;inject_value(&sensor->output.value_c,member,sensor->output.sample_ms);
     if(member==0)sensor->output.value_c+=sensor_variation(sensor->output.sample_ms);
     if(member==1)mr_reference_adjust(&sensor->output);
    }
    values[member]=sensor->output.value_c;
    valid=valid&&sensor->output.valid&&sensor->output.sample_ms<=at&&at-sensor->output.sample_ms<=period;
   }
   mr_triplex_step(&mr_evidence[k],at,values,valid);
   if(mr_evidence[k].strength>mr_pending[k]){mr_pending[k]=mr_evidence[k].strength;mr_pending_ambiguous[k]=mr_evidence[k].ambiguous;}
   fprintf(mr_log,"%u,%u,%.17g,%u,%d,%u,%u,%u\n",at,period,mr_evidence[k].strength,mr_evidence[k].qualified_count,mr_evidence[k].ambiguous,mr_sensor[k][0].output.sample_ms,mr_sensor[k][1].output.sample_ms,mr_sensor[k][2].output.sample_ms);
  }
  mr_sensor_seconds[k]+=seconds()-begin;
 }
 mr_last_ms=now;mr_last_physical=physical;
}
'''
INIT=r'''
 mr_validation=getenv("MR_VALIDATION")!=NULL;
 mr_selected_sensor=(unsigned)strtoul(getenv("MR_SENSOR")?getenv("MR_SENSOR"):"50",NULL,10);
 mr_selected_memory=(unsigned)strtoul(getenv("MR_MEMORY")?getenv("MR_MEMORY"):"500",NULL,10);
 mr_log=fopen(getenv("MR_LOG"),"w");mr_meta=fopen(getenv("MR_META"),"w");if(!mr_log||!mr_meta)return 1;
 const char *mr_names[]={"A0","A1","S50","S25","M500","M250","B50_500","B50_250","B25_500","B25_250"};
 for(unsigned j=0;j<10;j++)names[j]=mr_names[j];
 if(mr_validation){for(unsigned j=2;j<10;j++)names[j]="UNUSED";
  names[mr_selected_sensor==50?2:3]="A2";names[mr_selected_memory==500?4:5]="A3";
  names[6+(mr_selected_sensor==25?2:0)+(mr_selected_memory==250?1:0)]="A4";
 }
 for(unsigned k=0;k<2;k++){
  unsigned period=k?25:50;mr_triplex_init(&mr_evidence[k],period);
  diagnostic_temperature_init(&mr_sensor[k][0],seed+101,0,0,0,.01,0,period,0,20);
  diagnostic_temperature_init(&mr_sensor[k][1],reference_seed+103,reference_offset,0,reference_noise,.01,0,period,period/3,25);
  diagnostic_temperature_init(&mr_sensor[k][2],seed+107,offset,gain,noise,quantum,reference,period,2*period/3,30);
 }
 for(unsigned j=0;j<8;j++)clo_revised_init(&mr_detectors[j]);
'''
STEP=r'''
  const unsigned sr[8]={50,25,0,0,50,50,25,25};
  const unsigned mr[8]={0,0,500,250,500,250,500,250};
  for(unsigned j=0;j<8;j++){
   if(!mr_enabled(sr[j],mr[j]))continue;
   if(getenv("MR_BENCH")&&!(sr[j]&&mr[j]))continue;
   runtime_observation_t extra=o;
   if(mr[j]){
    memory_diagnostic_t *m=&mr_memory[mr[j]==250?1:0];
    bool old_failure=o.memory_check_valid&&o.memory_check_failed&&o.memory_check_ms<=o.time_ms&&o.time_ms-o.memory_check_ms<MEMORY_DIAGNOSTIC_MAX_INTERVAL_MS;
    if(m->valid&&!old_failure){extra.memory_check_ms=m->checked_ms;extra.memory_check_valid=m->valid;extra.memory_check_failed=m->failed;}
   }
   triplex_extra_strength=triplex.strength;triplex_extra_ambiguous=triplex.ambiguous;
   if(sr[j]&&mr_pending[sr[j]==25?1:0]>triplex_extra_strength){triplex_extra_strength=mr_pending[sr[j]==25?1:0];triplex_extra_ambiguous=mr_pending_ambiguous[sr[j]==25?1:0];}
   double begin=seconds();clo_triplex_core_step(&mr_detectors[j],&config,&extra);clo_final_diagnostic(&mr_detectors[j].fusion.evidence,o.time_ms,3000);mr_core_seconds[j+2]+=seconds()-begin;
   final_score(j+2,o.time_ms,&mr_detectors[j].fusion.output);
  }
  fprintf(mr_meta,"%u,%u,%u,%d,%u,%u,%d,%u,%u,%d,%lu,%lu,%.9g,%.9g,%.9g,%.9g,%.9g,%zu\n",o.time_ms,state->control.memory_diagnostic.checks,o.memory_check_ms,o.memory_check_failed,mr_memory[0].checks,mr_memory[0].checked_ms,mr_memory[0].failed,mr_memory[1].checks,mr_memory[1].checked_ms,mr_memory[1].failed,mr_acquisitions[0],mr_acquisitions[1],mr_sensor_seconds[0],mr_sensor_seconds[1],mr_memory_seconds[0],mr_memory_seconds[1],mr_core_seconds[1],sizeof(mr_triplex_t)+3*sizeof(diagnostic_temperature_t)+sizeof(memory_diagnostic_t));
'''
def adapt(adapter):
 adapter=adapter.replace('#define METHODS 8','#define METHODS 10')
 # FRONT is inserted before enabled is declared: memory helper uses the existing
 # experiment log presence guard rather than the later static declaration.
 front=FRONT.replace('if(!enabled||!state->log_file)return;','if(!state->log_file)return;')
 pos=adapter.index('static const char *names');adapter=adapter[:pos]+front+'\n'+adapter[pos:]
 needle='cross_layer_memory_read,cross_layer_memory_write,state);\n}';assert needle in adapter
 adapter=adapter.replace(needle,'cross_layer_memory_read,cross_layer_memory_write,state);\n if(enabled)mr_memory_acquire(state);\n}',1)
 adapter=adapter.replace(' diagnostic_acquire(state);',' diagnostic_acquire(state);\n mr_acquire(state);')
 helper=r'''static void mr_reference_adjust(diagnostic_readout_t *r){
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
 adapter=adapter.replace('static const char *metrics_path;',helper+'\nstatic const char *metrics_path;')

 adapter=adapter.replace(' triplex_consistency_init(&triplex);clo_revised_init(&triplex_detector);',' triplex_consistency_init(&triplex);clo_revised_init(&triplex_detector);\n'+INIT)
 needle='  clo_triplex_core_step(&triplex_detector,&config,&o);clo_final_diagnostic(&triplex_detector.fusion.evidence,o.time_ms,3000);'
 adapter=adapter.replace(needle,'  double mr_begin=seconds();\n'+needle+'\n  mr_core_seconds[1]+=seconds()-mr_begin;')
 adapter=adapter.replace('  final_score(1,o.time_ms,&triplex_detector.fusion.output);','  final_score(1,o.time_ms,&triplex_detector.fusion.output);\n'+STEP)
 return adapter

def build(w):
 source=inspect.getsource(t.build).replace('def build(w):','def generated_build(w):').replace(' objs=[]',' adapter=adapt(adapter)\n objs=[]')
 source=source.replace("'src/v7_3/triplex_consistency.c']","'src/v7_3/triplex_consistency.c','src/v7_3/multirate_triplex.c','src/v7_3/multirate_memory.c']")
 ns=dict(t.__dict__);ns['adapt']=adapt;exec(source,ns);return ns['generated_build'](w)

def design():
 templates=t.prior.design();cs=t.design();ss=[]
 for f in range(18):
  for j in range(150):
   i=f*150+j;s=dict(templates[(f%16)*150+j]);c=cs[(f%16)*150+j]
   for k in ['c_offset','c_gain','c_noise','c_quantum','c_adc_gain','c_phase_ms','c_lag_ms']:s[k]=c[k]
   s.update(run_id=f'multirate_{i:04}',profile=f'multirate_profile_{i:04}',group=f'multirate_family_{f}',partition='TRAIN' if f<8 else 'CALIBRATION' if f<13 else 'VALIDATION',seed=1439000011+i*229,reference_seed=1471000033+i*233,c_seed=1493000039+i*239,domain='NONE',kind='none')
   pp=json.loads(s['profile_json'])
   for p in pp:p['engine_load']*=.983;p['ambient_temp_c']+=.593+f*.021+j*.000037;p['vehicle_speed_kph']+=1.113+i*.000019
   if s['origin']!='NORMAL':s['start_ms']+=100*(1+(f+j)%7)
   if s['origin']=='MEMORY':
    s['start_ms']=21900+f*700+(j%10)*100
    if s['behavior']!='permanent':s['duration_ms']=[100,200,400,700,1200,2400][(j+f)%6]
   if 72<=j<96:
    k=j-72;domain=['A','B','AB'][k//8];cell=k%8;kind=['ramp','step','pulse'][(cell+f+k//8)%3]
    mag=(-1 if (cell+f)%2 else 1)*(2.67+f*.011 if kind=='ramp' else [.57,.73,.91,1.09][(cell+f)%4])
    duration=[25,50,75,100,150,250,700,1300][(cell+f)%8] if kind=='pulse' else 0
    s.update(origin='SENSOR_CONTROL',domain=domain,kind=kind,sensor_chain=domain,model={'ramp':'sensor_bias_ramp','step':'sensor_bias','pulse':'sensor_interface_intermittent'}[kind],behavior='transient' if duration else 'permanent',magnitude=mag,duration_ms=duration,sensor_ramp_rise_ms=[20700,40100,63700,82700][(cell+f)%4] if kind=='ramp' else 0,start_ms=23125+f*275+cell*325,initially_latent_stuck=0,target_updates_json='[]',workload='multirate_sensor')
   s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=h.profile_identity(pp);s.pop('configuration_sha256',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();ss.append(s)
 return ss

PROTOCOL='''# Preregistered multi-rate observability DEVELOPMENT
Frozen Triplex commit a340ca5cf0473d7dc572f7cd63e44fbc25b175a7 remains baseline. Its completed91.75% unseen is now development/reference for this architecture attempt, retained unchanged. No unseen,commit,push. No tuning against historical outcomes.

2700 new configurations: TRAIN1200 (8families), CALIBRATION750 (5), VALIDATION750 (5): final600fault+150benign,120per original origin. Full actuator templates, including unexcited cases, retained unchanged. Sensor A/B/AB balanced; steps,pulses,drift,off-grid starts and25–1300ms pulses. Memory effective/dormant,100–2400ms finite windows,phases andintermittency. Benign existing noise,legal updates,cold and dynamic profiles retained. Profile and seed identities new.

Simulation/control/plant100ms unchanged. Diagnostic50/25ms conversions use the retained sensor-model linear interpolation convention inside each100ms plant interval, independent phases0,p/3,2p/3, ADC noise/quantization/calibration, and fixed thermal lag20/25/30ms for A/B/C. This is a virtual sensor feasibility assumption, not a measured hardware bandwidth claim. Faults are applied by the frontend to acquired values, never passed to evidence. Controller samples,random streams,plant and original injection unchanged. Diagnostics are batched at next100ms tick; no fictitious sub-tick decision latency. Explicit source timestamps and freshness; no future readout reaches runtime inference.

Retained FAST/SLOW unchanged. Additional FAST uses exact same0.40C floor,1.2C/s bound,300ms anchor,two-sample same-sign consistency andone-second edge history. Time bounds remain in milliseconds,not faster counters. Single spike rejected. Startup500ms qualification. Max qualified evidence within only the current100ms batch,reset each tick; no300ms latch. Existing SLOW32s remains baseline. Three pairs share ONE sensor DS source; no independent voting per acquisition. If no additional qualified evidence, baseline behavior.

Memory extra schedules500ms average(600/400 gaps),250ms average(300/200),same atomic0/65535/read/restore transaction as retained probe. Both run on100ms scheduler; no claims for windows between scheduler updates. Only diagnostic status copied into variant observations; target register asserted unchanged after each probe. Existing probe continues for baseline comparability.7operations/probe,not hardware WCET.

TRAIN/CAL compare A0,A1,S50,S25,M500,M250 andfour combinations; no thresholds fitted. Choose slowest sensor/memory rates achieving any gain with no paired losses, no added benign alarms and no added wrong confident runs in BOTH TRAIN andCAL. If50 achieves at least95% of25 gains, prefer50; memory500 similarly. If no candidate qualifies, still evaluate the prespecified lowest-complexity50/500 combination as a failed-feasibility candidate, not a tuned rescue. Lock choice before VALIDATION; only A0,A1,A2selectedsensor,A3selectedmemory,A4both evaluated there. Promotion>=94%,gain>=2pp,benign<=1%,zero wrong runs,plant>=98%,no timing/comm/effective-memory/AB losses. If simpler ablation meets gates and supplies>=95% ofcombined gains, prefer it. No changes after validation, reject ifgates fail.

Miss causes post-hoc only: sensor no100ms observation,single observation,weak multiple,topology,other; memory noactive probe intersection,failed readback without alarm,nonvisible,other. Truth never enters provider. Instrument diagnostic CPU-time and counts; report component overhead not embedded WCET or full-platform timing. No raw bulk traces retained.
'''

def setup():
 assert not B.exists();B.mkdir();ss=design();assert len(ss)==2700
 keys={s['profile_semantic_sha256'] for s in ss}
 historical=[]
 for p in (ROOT/'results').rglob('*manifest*.csv'):
  for r in h.records(p):
   if r.get('profile_semantic_sha256'):historical.append(r['profile_semantic_sha256'])
 assert not keys&set(historical)
 paths=[p for root in ['src','include','scripts','python'] for p in Path(root).rglob('*') if p.is_file() and p.suffix in ['.c','.h','.py']]+[Path('presets/gui_session_state.json')]
 (B/'initial.json').write_text(json.dumps({str(p):sha(p) for p in paths},indent=2))
 (B/'specs.json').write_text(json.dumps(ss));h.write(O/'multirate_manifest.csv',ss);(O/'multirate_protocol.md').write_text(PROTOCOL)
 (O/'multirate_reference_status.md').write_text('The a340ca5c frozen Triplex final unseen result remains unchanged on disk. For this subsequent architecture study it is DEVELOPMENT/REFERENCE evidence, not independent validation of multi-rate diagnostics. No outcomes from it are used to select rates.\n')
 print('Registered2700 new cases; zero profile overlap.',flush=True)

def run(part):
 assert not (B/(part+'_started')).exists()
 if part=='VALIDATION':
  lock=json.loads((O/'multirate_selection.json').read_text());assert all(sha(p)==v for p,v in lock['files'].items());os.environ['MR_VALIDATION']='1';os.environ['MR_SENSOR']=str(lock['sensor']);os.environ['MR_MEMORY']=str(lock['memory']);methods=['A0','A1','A2','A3','A4']
 else:os.environ.pop('MR_VALIDATION',None);methods=NAMES
 ss=json.loads((B/'specs.json').read_text());selected=[s for s in ss if s['partition']==part];w=B/'work';w.mkdir(exist_ok=True);h.prepare_work(w,ss);exe=build(w)
 for key,name in [('TRIPLEX_LOG','triplex.csv'),('MR_LOG','mr.csv'),('MR_META','mr_meta.csv')]:os.environ[key]=str(w/name)
 h.c.METHODS=methods;h.c.command=lambda s,w:t.command(s,w,exe);read0=h.c.read;cache={}
 def read(p):
  rr=read0(p)
  if Path(p).name=='observations.csv':cache['obs']=rr
  return rr
 h.c.read=read;rows=[];(B/(part+'_started')).write_text('started')
 with (B/(part+'_checkpoint.jsonl')).open('w') as ck:
  for i,s in enumerate(selected):
   start=time.perf_counter();rr=h.c.execute(s,w,False);elapsed=time.perf_counter()-start
   a=np.loadtxt(w/'triplex.csv',delimiter=',');mr=np.loadtxt(w/'mr.csv',delimiter=',');meta=np.loadtxt(w/'mr_meta.csv',delimiter=',');last=meta[-1]
   obs=[o for o in cache['obs'] if h.prior.prior.active(s,int(o['time_ms']))];axis='pump_command' if s['model']=='pump_degraded' else 'fan_command'
   def num(x):return float.fromhex(x) if '0x' in str(x).lower() else float(x)
   ticks=[int(o['time_ms']) for o in obs];probes={int(x[2]) for x in meta if x[1]>0}
   active_probes=sum(h.prior.prior.active(s,p) for p in probes)
   for r in rr:
    r.pop('command_json',None);r.update(original_space=1,initially_excited=int(s['origin']=='ACTUATOR' and bool(obs) and num(obs[0][axis])>0),actuator_excited=int(s['origin']=='ACTUATOR' and any(num(o[axis])>0 for o in obs)),pattern_A_BC=int(sum(a[:,4]==1)),pattern_B_AC=int(sum(a[:,4]==2)),pattern_C_AB=int(sum(a[:,4]==3)),pattern_all_disagree=int(sum(a[:,4]==4)),triplex_peak=float(a[:,1].max()),triplex_qualified_samples=int(sum(a[:,2])),ambiguous_samples=int(sum(a[:,3])),observations_in_fault=len(ticks),old_probes_in_fault=active_probes,host_run_seconds=elapsed,extra_acquisitions50=int(last[10]),extra_acquisitions25=int(last[11]),old_probe_count=int(last[1]),extra_probe_count500=int(last[4]),extra_probe_count250=int(last[7]),sensor_cpu50=float(last[12]),sensor_cpu25=float(last[13]),memory_cpu500=float(last[14]),memory_cpu250=float(last[15]),triplex_cpu=float(last[16]),extra_state_bytes=int(last[17]))
    r['temporal_miss_cause']=''
    if r['method']=='A1' and r['injected'] and not r['detected']:
     if s['origin']=='SENSOR_CONTROL':r['temporal_miss_cause']='A' if not ticks else 'B' if len(ticks)==1 else 'D' if any(x[3] for x in a if h.prior.prior.active(s,int(x[0]))) else 'E' if any(x[1]>=.5 for x in a if h.prior.prior.active(s,int(x[0]))) else 'C'
     if s['origin']=='MEMORY':r['temporal_miss_cause']='A' if not active_probes else 'B' if any(int(x[3]) for x in meta if h.prior.prior.active(s,int(x[0]))) else 'C'
    rows.append(r)
   ck.write(json.dumps(rr)+'\n');ck.flush()
   for name in ['triplex.csv','mr.csv','mr_meta.csv']:(w/name).unlink()
   if (i+1)%50==0:print(part,i+1,'/',len(selected),flush=True)
 h.write(B/(part+'_rows.csv'),rows);(B/(part+'_complete')).write_text('complete');shutil.rmtree(w)

if __name__=='__main__':
 if sys.argv[1]=='setup':setup()
 elif sys.argv[1]=='run':run(sys.argv[2])
