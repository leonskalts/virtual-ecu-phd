#!/usr/bin/env python3
"""Single grouped triplex observability development; no unseen or parameter search."""
import sys,os,json,hashlib,subprocess,shutil,csv,collections,tarfile
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'python')]
import clo_dsf_triplex_support as prior
h=prior.old;B=Path('/tmp/clo-triplex');OUT=h.OUT
write=h.write;sha=h.prior.sha
PROTOCOL='''# Triplex coolant observability architecture and preregistered protocol

One 2400-case DEVELOPMENT campaign, no unseen or commit/push.16 distinct physical
families,150 simulations per family; TRAIN8families1200cases, CALIBRATION4families
600cases, VALIDATION4families600cases. Per family18MEMORY,18TIMING,18COMMUNICATION,
18ACTUATOR,48SENSOR_CONTROL,30BENIGN. The four non-sensor origins remain balanced.
Sensor emphasis is explicit and not chosen to achieve the95% target. Within sensor
space:8each A,B,C,AB,ABC and4each AC,BC. S1 original faults=A,B,AB only; S2 includes
all48sensor cells. Other origins belong to both overall denominators. Each600-case
partition thus contains384 original-space faults,480 expanded faults,120benign.

New physical profiles/seeds and group-wise separation. All families are disjoint
across partitions, including offsets/gains/noise/ADC references and acquisition
phases. Cell kinds recur, but complete configuration families never cross partitions.
Original templates supply valid memory/timing/communication/actuator semantics.
Sensor injection is a separate acquisition-boundary model shared identically by
A0 and A1: signed ramps,weak steps,rectangular pulses,stuck conversion output; C-only
also includes timestamp freeze. No detector reads injection configuration or truth.
C-only faults affect diagnostic coverage, not the control plant; report expanded
and original fault spaces separately. Never exclude common/global/unexcited cases.

C measures the SAME physical coolant quantity through its own gain,calibration
bias,noise PRNG,ADC reference gain,quantization,100ms schedule with independent
phase,acquisition/readout state. Optional first-order lag is implemented; the
registered cohort uses zero lag to isolate acquisition diversity (not a perfect
sensor:gain/offset/noise/quantization/phase remain nonzero). Physical interpolation
between simulator integration endpoints occurs only inside the sensor model.
Runtime inference sees only C output/status/timestamps and past C samples. A causal
linear projection over<=100ms aligns C to the A/B epoch; no future sample or plant
truth. Five consecutive qualified C readouts gate disagreement evidence.

A-B remains unchanged. A-C and B-C each reuse the EXACT existing FAST/SLOW code,
including .90C SLOW envelope,320samples,.40C FAST floor,1.2C/s bound,existing
same-sign integration and edge persistence. MAX of the three pair strengths feeds
ONE existing sensor evidence channel: do not count correlated pairs as independent
DS votes. No changes to global thresholds,reliabilities,classical fusion,temporal
fusion,memory/timing/communication/actuator providers or causal precedence.
Fresh explicit C failure or acquired C stale>200ms after startup is a new independent
acquisition-status contract,using the existing100ms cadence and two missed periods.
No active excitation or pre-mission BIST. A2/A3 do not exist (see failure-domain audit).

Member patterns are disagreement cuts:A|BC,B|AC,C|AB; each retains single-versus-pair
ambiguity. A matching pair never proves healthy. All mutually disagree outside the
existing .90C envelope => UNKNOWN main origin unless earlier direct non-sensor
causal evidence already exists. SENSOR_CONTROL domain evidence is otherwise causal
as before; no confident faulty-member claim. Pair pattern diagnostics are reported
separately from main origin. C is not a trusted oracle.

All parameters fixed before TRAIN. No parameter search; TRAIN and CALIBRATION are
feasibility/safety audits only. Freeze source/config/protocol hashes after CALIBRATION,
then run untouched VALIDATION once. Report even failures; no rescue tuning. Retain
only if original-space>=95%,ABcommon>=80%,benign<=1%,zero wrong confident samples,
no timing/communication/effective-memory loss,plant detection no worse. Also require
expanded-space>=95% to avoid exploiting the added sensor fault denominator. A0/A1
observe identical physical runs; default CURRENT production remains unchanged unless
all gates pass. Historical final evidence remains intact and is development/reference
knowledge for this new architecture, never reused as its final unseen evidence.

Alarm/propagation/latency metrics use existing collector semantics (post-onset rising
alarm edge; all-runtime localization includes pre-onset/benign samples). Independent
hidden counterfactual plant is used ONLY for post-hoc propagation scoring. Wilson
CIs are descriptive for a grouped deterministic design. Exact McNemar is descriptive.
Miss accounting precedence:global ABC=>redundancy-limited; actuator never excited or
memory no positive runtime evidence=>unobservable; no usable C qualification during
sensor episode=>qualification-limited; evidence first appears after horizon/onset
clearance constraints=>latency-limited where witnessed; otherwise algorithm-limited.
Accounting is post-hoc, not an inference feature. Avoid asserting absence of all
physical information from a low current provider score.

Storage:preserve superseded CURRENT artifacts byte-for-byte in a results-only archive
outside CURRENT, no duplicate source tree. CURRENT contains only requested7files,
with protocol/lock/manifest hashes embedded here. Deterministic manifest reconstructs
from the saved runner; no bulk traces; plan zero representative traces. Raw run CSVs
deleted immediately after scoring; temporary build and profiles removed after audit.
'''

def design():
 templates=prior.design();out=[]
 for f in range(16):
  base=templates[f*150:(f+1)*150]
  for j in range(150):
   if j<72:idx=(j//18)*24+(j%18) if j<54 else 96+j-54
   elif j<120:idx=72
   else:idx=j
   s=dict(base[idx]);s.update(run_id=f'triplex_{f*150+j:04}',profile=f'triplex_profile_{f*150+j:04}',group=f'triplex_family_{f}',domain='NONE',kind='none',c_seed=641000039+f*2711+j*137,c_offset=(-1 if f%2 else 1)*(.055+f*.0031),c_gain=(-1 if f%3 else 1)*(.00031+f*.000021),c_noise=.012+f*.0007,c_quantum=.02,c_adc_gain=(-1 if f%2 else 1)*(.00017+f*.000011),c_phase_ms=13+f*5,c_lag_ms=0)
   pp=json.loads(s['profile_json'])
   for p in pp:p['engine_load']*=.973;p['ambient_temp_c']+=.683+j*.000017;p['vehicle_speed_kph']+=2.179+j*.000021
   s['seed']+=103001;s['reference_seed']+=109009
   if s['origin']!='NORMAL':s['start_ms']+=300+(f%3)*100
   if 72<=j<120:
    k=j-72;domain=['A','B','C','AB','ABC'][k//8] if k<40 else 'AC' if k<44 else 'BC';cell=k%8 if k<40 else k%4
    kind=['ramp','ramp','step','step','pulse','pulse','stuck','freeze' if domain=='C' else 'step'][cell]
    mag=(-1 if (cell+f)%2 else 1)*((2.57+f*.019) if kind=='ramp' else (.63+f*.006 if cell%2 else .97+f*.006))
    duration=([100,300,700,1100][(f+cell)%4] if kind=='pulse' else 900 if kind=='freeze' else 0)
    s.update(origin='SENSOR_CONTROL',domain=domain,kind=kind,sensor_chain=domain,model={'ramp':'sensor_bias_ramp','step':'sensor_bias','pulse':'sensor_interface_intermittent','stuck':'sensor_stuck','freeze':'sensor_acquisition_freeze'}[kind],behavior='transient' if duration else 'permanent',magnitude=mag,duration_ms=duration,sensor_ramp_rise_ms=[19300,37700,61300,81700][(f+cell)%4] if kind=='ramp' else 0,start_ms=21900+(f%4)*700+cell*300,initially_latent_stuck=0,target_updates_json='[]',workload='triplex_fault')
   s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=h.profile_identity(pp);s.pop('configuration_sha256',None);s.pop('command_json',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();out.append(s)
 assert len(out)==2400 and len({s['profile_semantic_sha256'] for s in out})==2400
 return out

# The experiment injector runs at the sensor frontend; it is never an inference API.
FRONT=r'''
#include "triplex_consistency.h"
static diagnostic_temperature_t diagnostic_c;
static triplex_consistency_t triplex;
static clo_revised_t triplex_detector;
static FILE *triplex_log;
double triplex_extra_strength;
bool triplex_extra_ambiguous;
void clo_triplex_core_step(clo_revised_t *,const clo_final_config_t *,const runtime_observation_t *);
static unsigned injection_mask,injection_kind,injection_start,injection_duration,injection_rise;
static double injection_magnitude;
static bool held[3];static float held_value[3];static diagnostic_readout_t frozen_c;
static void inject_value(float *value,unsigned member,unsigned now){
 if(!(injection_mask&(1U<<member))||now<injection_start||(injection_duration&&now>=injection_start+injection_duration))return;
 if(injection_kind==4){if(!held[member]){held[member]=true;held_value[member]=*value;}*value=held_value[member];}
 else if(injection_kind!=5)*value+=(float)(injection_magnitude*(injection_kind==1?fmin(1.,(double)(now-injection_start)/injection_rise):1));
}
static void diagnostic_acquire(ecu_state_t *state){
 if(!state->log_file)return;
 bool acquired=diagnostic_temperature_sample(&diagnostic_c,state->time.time_ms,state->plant.coolant_temp_true_c);
 unsigned now=state->time.time_ms;
 if(acquired)inject_value(&diagnostic_c.output.value_c,2,diagnostic_c.output.sample_ms);
 if(injection_kind==5 && (injection_mask&4) && now>=injection_start && (!injection_duration||now<injection_start+injection_duration)){
  if(!held[2]){frozen_c=diagnostic_c.output;held[2]=true;}diagnostic_c.output=frozen_c;
 }
 inject_value(&state->sensors.coolant_source_c,0,now);state->sensors.coolant_temp_meas_c=state->sensors.coolant_source_c;
 inject_value(&state->temperature_reference.value_c,1,now);
}
'''
def build(w):
 core=(ROOT/'src/v7_3/clo_dsf_revised.c').read_text();bridge=core+'\ndouble clo_existing_pair_strength(clo_revised_t *s,const runtime_observation_t *o){return fmax(redundant_sensor(s,o),fast_redundant_sensor(s,o));}\n'
 extended=core
 for fn in ['clo_revised_init','clo_revised_extract','clo_revised_step']:extended=extended.replace(fn,fn.replace('clo_revised','clo_triplex_core'))
 extended='extern double triplex_extra_strength;\n#include <stdbool.h>\nextern bool triplex_extra_ambiguous;\n'+extended
 needle='independent=fmax(independent,fast_redundant_sensor(state,o));';assert needle in extended;extended=extended.replace(needle,needle+'\n    independent=fmax(independent,triplex_extra_strength);')
 extended=extended.replace('if(state->ambiguous_onset)v->localization_valid=false;','if(state->ambiguous_onset || (triplex_extra_ambiguous && !state->direct_origins))v->localization_valid=false;')
 frozen=subprocess.check_output(['git','show','9f993587:src/v7_3/clo_dsf_revised.c'],text=True)
 for fn in ['clo_revised_init','clo_revised_extract','clo_revised_step']:frozen=frozen.replace(fn,fn.replace('clo_revised','clo_prechange'))
 adapter=(ROOT/'src/v7_3/revised_runtime.c').read_text();where=adapter.index('static const char *names');adapter=adapter[:where]+FRONT+'\n'+adapter[where:]
 adapter=adapter.replace(' reference_acquire(state);',' reference_acquire(state);\n diagnostic_acquire(state);')
 # Do not overwrite delivered primary value for non-sensor cases (communication).
 adapter=adapter.replace(' inject_value(&state->sensors.coolant_source_c,0,now);state->sensors.coolant_temp_meas_c=state->sensors.coolant_source_c;',' if(injection_mask&1){inject_value(&state->sensors.coolant_source_c,0,now);state->sensors.coolant_temp_meas_c=state->sensors.coolant_source_c;}')
 start=adapter.index(' if(comparison) {',adapter.index('void __wrap_detection_algorithm_step'));end=adapter.index('\n if(primary)',start)
 block=r''' if(comparison) {
  clo_prechange_step(&prechange,&config,&o);clo_final_diagnostic(&prechange.fusion.evidence,o.time_ms,3000);
  if(memcmp(&prechange,&detector,sizeof(detector)))abort();
  triplex_consistency_step(&triplex,&o,&diagnostic_c.output);triplex_extra_strength=triplex.strength;triplex_extra_ambiguous=triplex.ambiguous;
  clo_triplex_core_step(&triplex_detector,&config,&o);clo_final_diagnostic(&triplex_detector.fusion.evidence,o.time_ms,3000);
  final_score(1,o.time_ms,&triplex_detector.fusion.output);
  fprintf(triplex_log,"%u,%.17g,%d,%d,%u,%.17g,%.17g,%d,%u,%d,%u\n",o.time_ms,triplex.strength,triplex.qualified,triplex.ambiguous,triplex.member_pattern,triplex.ac_strength,triplex.bc_strength,triplex_detector.fusion.output.alarm,triplex_detector.fusion.output.estimated_origin,detector.fusion.output.alarm,detector.fusion.output.estimated_origin);
 }'''
 adapter=adapter[:start]+block+adapter[end:]
 init=r''' names[0]="A0";names[1]="A1";triplex_log=fopen(getenv("TRIPLEX_LOG"),"w");if(!triplex_log)return 1;
 unsigned seed,phase;float offset,gain,noise,quantum,reference,lag;
 if(sscanf(getenv("TRIPLEX_SENSOR"),"%u:%f:%f:%f:%f:%f:%u:%f",&seed,&offset,&gain,&noise,&quantum,&reference,&phase,&lag)!=8)return 1;
 diagnostic_temperature_init(&diagnostic_c,seed,offset,gain,noise,quantum,reference,100,phase,lag);
 if(sscanf(getenv("TRIPLEX_FAULT"),"%u:%u:%u:%u:%u:%lf",&injection_mask,&injection_kind,&injection_start,&injection_duration,&injection_rise,&injection_magnitude)!=6)return 1;
 triplex_consistency_init(&triplex);clo_revised_init(&triplex_detector);
'''
 adapter=adapter.replace(' clo_revised_init(&prechange);',init+' clo_revised_init(&prechange);')
 objs=[]
 for name,source in [('bridge',bridge),('extended',extended),('frozen',frozen),('adapter',adapter)]:
  p=w/(name+'.c');p.write_text(source);obj=p.with_suffix('.o');subprocess.run(['gcc','-std=c11','-O2','-Iinclude','-c',str(p),'-o',str(obj)],check=True);objs.append(str(obj))
 for name in ['src/v7_3/diagnostic_temperature.c','src/v7_3/triplex_consistency.c']:
  obj=w/(Path(name).stem+'.o');subprocess.run(['gcc','-std=c11','-O2','-Iinclude','-c',name,'-o',str(obj)],check=True);objs.append(str(obj))
 objs += [str(p) for p in (ROOT/'src').glob('*.o') if p.name not in ['main.o','diagnostic_temperature.o']]
 objs += [str(ROOT/p) for p in ['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7/accepted_main.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o','src/v7_2/final_observation_io.o']]
 exe=w/'compare';subprocess.run(['gcc',*objs,'-Wl,--wrap=detection_algorithm_step','-Wl,--wrap=cross_layer_fault_step','-Wl,--wrap=sensors_step','-lm','-o',str(exe)],check=True);return exe

def command(s,w,exe):
 physical=dict(s)
 if s['origin']=='SENSOR_CONTROL':physical.update(model='sensor_bias',sensor_chain='primary',magnitude=0,sensor_ramp_rise_ms=0)
 cmd=[str(exe),*h.prior.prior.command(physical,w)[1:]]
 os.environ['TRIPLEX_SENSOR']=':'.join(str(s[k]) for k in ['c_seed','c_offset','c_gain','c_noise','c_quantum','c_adc_gain','c_phase_ms','c_lag_ms'])
 mask=sum(1<<i for i,ch in enumerate('ABC') if ch in s['domain']) if s['origin']=='SENSOR_CONTROL' else 0
 kind={'none':0,'ramp':1,'step':2,'pulse':3,'stuck':4,'freeze':5}[s['kind']]
 os.environ['TRIPLEX_FAULT']=f"{mask}:{kind}:{s['start_ms']}:{s['duration_ms']}:{s['sensor_ramp_rise_ms']}:{s['magnitude']}"
 return cmd

def setup():
 assert not (B/'registered').exists();ss=design();keys={s['profile_semantic_sha256'] for s in ss};sources=[]
 for p in (ROOT/'results').rglob('*.csv'):
  if not any(n in p.name for n in ['manifest','registry']):continue
  with p.open() as f:
   r=csv.DictReader(f)
   if not r.fieldnames or 'profile_semantic_sha256' not in r.fieldnames:continue
   rows=list(r);assert not keys&{r['profile_semantic_sha256'] for r in rows};sources.append(dict(path=str(p),sha256=sha(p),rows=len(rows)))
 (B/'specs.json').write_text(json.dumps(ss));write(B/'manifest.csv',ss);(B/'history_audit.json').write_text(json.dumps(sources,indent=2));(B/'registered').write_text(datetime.now(timezone.utc).isoformat())
 archive=ROOT/'results/clo_dsf_current_history.tar.gz';assert not archive.exists();shutil.copyfile(B/'previous_current.tar.gz',archive)
 for p in OUT.iterdir():
  if p.is_file():p.unlink()
 (OUT/'architecture_definition.md').write_text(PROTOCOL+f'\nRegistered UTC:{(B/"registered").read_text()}\nManifest SHA256:{sha(B/"manifest.csv")}\nHistory archive SHA256:{sha(archive)}\n')
 print('Registered',len(ss),'historical sources',len(sources),flush=True)

def run(part):
 assert not (B/(part+'_started')).exists()
 if part=='VALIDATION':
  lock=json.loads((B/'lock.json').read_text());assert all(sha(Path(p))==v for p,v in lock['files'].items())
 ss=json.loads((B/'specs.json').read_text());w=B/'work';w.mkdir(exist_ok=True);h.prepare_work(w,ss);exe=build(w);os.environ['TRIPLEX_LOG']=str(w/'triplex.csv');h.c.METHODS=['A0','A1'];h.c.command=lambda s,w:command(s,w,exe)
 read0=h.c.read;cache={}
 def read(p):
  rr=read0(p)
  if Path(p).name in ['observations.csv','trace.csv']:cache[Path(p).name]=rr
  return rr
 h.c.read=read;rows=[];selected=[s for s in ss if s['partition']==part];(B/(part+'_started')).write_text(datetime.now(timezone.utc).isoformat())
 with (B/(part+'_checkpoint.jsonl')).open('w') as ck:
  for i,s in enumerate(selected):
   rr=h.c.execute(s,w,False);a=np.loadtxt(w/'triplex.csv',delimiter=',');(w/'triplex.csv').unlink()
   active=(a[:,0]>=s['start_ms']) & ((a[:,0]<s['start_ms']+s['duration_ms']) if s['duration_ms'] and s['origin']=='SENSOR_CONTROL' else True)
   obs=[o for o in cache['observations.csv'] if h.prior.prior.active(s,int(o['time_ms']))];axis='pump_command' if s['model']=='pump_degraded' else 'fan_command'
   def num(x):return float.fromhex(x) if '0x' in x.lower() else float(x)
   for r in rr:
    r.pop('command_json',None);r.update(original_space=int(s['domain'] in ['NONE','A','B','AB']),initially_excited=int(s['origin']=='ACTUATOR' and bool(obs) and num(obs[0][axis])>0),actuator_excited=int(s['origin']=='ACTUATOR' and any(num(o[axis])>0 for o in obs)),triplex_peak=float(a[active,1].max()) if active.any() else 0,triplex_qualified_samples=int(a[active,2].sum()),ambiguous_samples=int(a[:,3].sum()),pattern_A_BC=int(np.sum(active&(a[:,4]==1))),pattern_B_AC=int(np.sum(active&(a[:,4]==2))),pattern_C_AB=int(np.sum(active&(a[:,4]==3))),pattern_all_disagree=int(np.sum(active&(a[:,4]==4))))
    r['miss_limit']=''
    if r['injected'] and not r['detected']:
     r['miss_limit']='redundancy-limited' if s['domain']=='ABC' else 'genuinely unobservable' if s['origin']=='ACTUATOR' and not r['actuator_excited'] or s['origin']=='MEMORY' and r['first_positive_feature_ms']<0 else 'qualification-limited' if s['origin']=='SENSOR_CONTROL' and not r['triplex_qualified_samples'] else 'algorithm-limited'
    rows.append(r)
   ck.write(json.dumps(rr)+'\n');ck.flush()
   if (i+1)%50==0:print(part,i+1,'/',len(selected),flush=True)
 write(B/(part+'_rows.csv'),rows);(B/(part+'_complete')).write_text('complete')

def lock():
 assert (B/'CALIBRATION_complete').exists() and not (B/'VALIDATION_started').exists()
 paths=[Path(__file__),ROOT/'src/v7_3/diagnostic_temperature.c',ROOT/'include/diagnostic_temperature.h',ROOT/'src/v7_3/triplex_consistency.c',ROOT/'include/triplex_consistency.h',ROOT/'src/v7_3/clo_dsf_revised.c',ROOT/'include/clo_dsf_revised.h',h.c.CONFIG,OUT/'architecture_definition.md',OUT/'failure_domain_model.md',B/'manifest.csv']
 r=dict(locked_at=datetime.now(timezone.utc).isoformat(),selection='A1 fixed observability extension; no fitted parameters',files={str(p):sha(p) for p in paths});(B/'lock.json').write_text(json.dumps(r,indent=2));print('LOCKED',flush=True)

if __name__=='__main__':
 if sys.argv[1]=='setup':setup()
 elif sys.argv[1]=='run':run(sys.argv[2])
 elif sys.argv[1]=='lock':lock()
