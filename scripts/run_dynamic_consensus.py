#!/usr/bin/env python3
"""One registered dynamic consensus development campaign; retained core untouched."""
import os,sys,json,inspect,subprocess,hashlib,gzip,pickle,collections,shutil,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=['/tmp/clo-ml-deps',str(ROOT/'scripts'),str(ROOT/'python')]
import numpy as np
import run_triplex_plus as r
import run_ml_assisted_clodsf as ml
import run_change_point as history
import select_triplex_plus as prior
B=Path('/tmp/clo-dynamic-consensus');O=ROOT/'results/dynamic_consensus_development';h=r.h;sha=r.sha;bench=r.bench

def dump(p,v):p.write_text(json.dumps(v,indent=2))
def verify():
 history.verify()
 historical=ROOT/'results/change_point_development/change_point_calibration.json'
 record=json.loads(historical.read_text())
 for name,value in record.get('artifact_hashes',{}).items():
  path=Path(name);path=path if path.is_absolute() else historical.parent/path
  assert sha(path)==value,str(path)
 if (B/'protected.json').exists():assert all(sha(Path(p))==v for p,v in json.loads((B/'protected.json').read_text()).items())
 if (B/'lock.json').exists():assert all(sha(Path(p))==v for p,v in json.loads((B/'lock.json').read_text()).items())

def design():
 templates=r.design();out=[]
 for f in range(58):
  part='TRAIN' if f<24 else 'CALIBRATION' if f<48 else 'VALIDATION';n=20 if f<24 else 10 if f<48 else 24;total=150 if f<24 else 100 if f<48 else 240;local=f if f<24 else f-24 if f<48 else f-48
  for j in range(total):
   fault=j<5*n;origin_index=j//n if fault else 5;k=j%n if fault else j-5*n
   idx=origin_index*24+(k+(local*7 if n<24 else 0))%24 if fault else 120+k%30
   s=dict(templates[(f%21)*150+idx]);i=len(out)
   s.update(run_id=f'dc_{i:04}',profile=f'dc_profile_{i:04}',group=f'dc_family_{f}',partition=part,seed=3801000031+i*251,reference_seed=3903000047+i*257,c_seed=4007000069+i*263)
   profile=json.loads(s['profile_json'])
   for z,v in enumerate(profile):
    v['ambient_temp_c']+=3.193+(f%7)*.173+j*.000061;v['engine_load']*=.917+(f%5)*.017;v['vehicle_speed_kph']+=3.751+i*.000019
    if not fault and k%10==3:v['vehicle_speed_kph']=[.37,87.13,23.17,12.73,94.11][z]
   s['c_phase_ms']=[11,37,73,97][f%4];s['c_quantum']=[.016,.024,.028][f%3]
   if fault:s['start_ms']+=2100+(f%9)*100
   if s['origin']=='SENSOR_CONTROL':
    si=local*n+k;domain=['A','B','C','AB','ABC'][si%5];cell=(si//5)%8;kind=['step','step','step','pulse','pulse','ramp','step','ramp'][cell]
    weak=[.42,.47,.50,.54,.58][(local+cell)%5];sign=-1 if (si//40+cell)%2 else 1
    mag=[sign*weak,-sign*weak,sign*1.09,sign*weak,sign*.67,3.19+f*.013,-sign*.51,-(2.97+f*.011)][cell]
    phase=([5,23,41] if part=='TRAIN' else [13,47,67] if part=='CALIBRATION' else [19,59,89])[(local+cell)%3]
    s.update(domain=domain,sensor_chain=domain,kind=kind,model={'step':'sensor_bias','pulse':'sensor_interface_intermittent','ramp':'sensor_bias_ramp'}[kind],magnitude=mag,behavior='transient' if kind=='pulse' else 'permanent',duration_ms=([50,150,250][local%3] if cell==3 else [700,1100,1700][local%3]) if kind=='pulse' else 0,sensor_ramp_rise_ms=[26900,48700,73900,96700][(local+cell)%4] if kind=='ramp' else 0,start_ms=25900+local*300+cell*400+phase,initially_latent_stuck=0,workload='dc_sensor',target_updates_json='[]')
   if not fault and k%3==0:
    s['benign_reference_magnitude']=(-1 if (local+k)%2 else 1)*[.2,.32,.5][(k//3+local)%3];s['benign_reference_duration']=[100,1100,2300,5100][(k//3+local)%4];s['workload']='legal_offset_'+str(s['benign_reference_duration'])
   s['profile_json']=json.dumps(profile,sort_keys=True);s['profile_semantic_sha256']=h.profile_identity(profile);s.pop('configuration_sha256',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();out.append(s)
 assert len(out)==8400
 return out


FRONT=r'''
#include "dynamic_consensus.h"
static FILE *dc_packet_log,*dc_input_log;
double dc_mass,dc_origin,dc_discount;
static memory_diagnostic_t dc_memory;
static clo_revised_t dc_memory_detector;
typedef struct {runtime_observation_t o;double extra,c;memory_diagnostic_t m[2];bool ambiguous,qualified;} dc_packet_t;
static void dc_probe(ecu_state_t *state){
 if(!state->log_file)return;
 static bool phases[100],initialized;
 if(!initialized){
  for(unsigned i=0;i<10;i++)phases[11*i]=true;
  for(unsigned n=10;n<40;n++){
   unsigned best=0,begin=0;
   for(unsigned i=0;i<100;i++)if(phases[i]){unsigned gap=1;while(!phases[(i+gap)%100])gap++;if(gap>best){best=gap;begin=i;}}
   phases[(begin+best/2)%100]=true;
  }initialized=true;
 }
 unsigned now=state->time.time_ms;
 if(now%100||!phases[(now/100)%100]||(dc_memory.valid&&now<=dc_memory.checked_ms))return;
 uint16_t before=state->control.target_register_c,saved=cross_layer_memory_read(state);
 cross_layer_memory_write(state,0);bool failed=cross_layer_memory_read(state)!=0;
 cross_layer_memory_write(state,UINT16_MAX);failed=(cross_layer_memory_read(state)!=UINT16_MAX)||failed;
 cross_layer_memory_write(state,saved);failed=(cross_layer_memory_read(state)!=saved)||failed;
 dc_memory.checked_ms=now;dc_memory.checks++;dc_memory.operations+=7;dc_memory.valid=true;dc_memory.failed=failed;
 if(before!=state->control.target_register_c)abort();
}
'''
REPLAY=r'''
static int dc_replay(const char *path,const char *parameters,const char *output){
 double v[17];FILE *f=fopen(parameters,"r");if(!f)return 2;
 for(unsigned i=0;i<17;i++)if(fscanf(f,"%lf",&v[i])!=1)return 3;fclose(f);
 dc_config_t c={0};for(unsigned i=0;i<3;i++){c.offset[i]=v[i];c.variance[i]=v[3+i];}
 c.process_variance=v[6];c.lambda=v[7];c.threshold=v[8];c.alpha=v[9];c.healthy_margin=v[10];c.consistency_bound=v[11];c.common_bound=v[12];c.origin_margin=v[13];c.robust=(unsigned)v[14];double discount=v[15];unsigned memory=(unsigned)v[16];
 if(final_config_read("results/cross_layer_safety_v7_3_dev/revised.cfg",&config))return 4;
 FILE *in=fopen(path,"rb"),*out=fopen(output,"w");if(!in||!out)return 5;
 benchmark_log=fopen(getenv("BENCHMARK_LOG"),"w");if(!benchmark_log)return 6;
 clo_revised_t detector[7];for(unsigned j=0;j<7;j++)clo_revised_init(&detector[j]);dc_state_t provider={0};dc_packet_t q;
 while(fread(&q,sizeof q,1,in)==1){
  dc_input_t u={.ms=q.o.time_ms,.y={q.o.source_c,q.o.reference_c,q.c},.context={q.o.engine_load,q.o.pump_command,q.o.fan_command,q.o.vehicle_speed_kph},.qualified=q.qualified};dynamic_consensus_step(&provider,&c,&u);if(!provider.stable)return 7;
  fprintf(out,"%u",u.ms);for(unsigned h=0;h<5;h++)fprintf(out,",%.17g",provider.filter[h].ell);
  fprintf(out,",%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%u,%u",provider.D,provider.margin,provider.consistency,provider.common,provider.q_healthy,provider.mass,provider.origin_mass,provider.best,provider.qualified);
  for(unsigned j=0;j<7;j++){
   runtime_observation_t x=q.o;if(j==4||j>=5){memory_diagnostic_t *m=&q.m[j==4?memory-1:j-5];x.memory_check_ms=m->checked_ms;x.memory_check_valid=m->valid;x.memory_check_failed=m->failed;}
   triplex_extra_strength=q.extra;triplex_extra_ambiguous=q.ambiguous;
   dc_mass=(j==1||j==3||j==4)?provider.mass:0;dc_origin=(j==1||j==3||j==4)?provider.origin_mass:0;dc_discount=(j>=2&&j<=4)?discount*provider.q_healthy:0;
   plus_arch=j;clo_triplex_core_step(&detector[j],&config,&x);clo_final_diagnostic(&detector[j].fusion.evidence,x.time_ms,3000);
   fprintf(out,",%u,%u,%.17g",detector[j].fusion.output.alarm,detector[j].fusion.output.estimated_origin,detector[j].fusion.output.anomaly_decision_score);
  }fprintf(out,"\n");
 }fclose(in);fclose(out);fclose(benchmark_log);return 0;
}
'''
INJECT=r'''
    bool dc_clean=independent<=1e-12 && fabs(o->coolant_measured_c-o->source_c)<=1e-6 && o->source_c>=ECU_SENSOR_IMPLAUSIBLE_LOW_C && o->source_c<=ECU_SENSOR_IMPLAUSIBLE_HIGH_C;
    for(unsigned dc_i=0;dc_i<3;dc_i++)if(s->evidence.available[dc_i] && s->evidence.strength[dc_i]>0)dc_clean=false;
    double dc_factor=dc_clean?1-fmin(.35,fmax(0,dc_discount)):1;
    local*=dc_factor;origin_local*=dc_factor;s->evidence.strength[3]*=dc_factor;
    local=fmax(local,dc_mass);origin_local=fmax(origin_local,dc_origin);
    s->evidence.strength[3] = fmax(s->evidence.strength[3], local);
'''
def build(w):
 oldadapt=r.adapt;oldbuild=r.t.build;getsource=r.inspect.getsource
 def adapt(a):
  a=oldadapt(a).replace('static unsigned plus_arch;',FRONT+'\nstatic unsigned plus_arch;')
  a=a.replace('if(enabled)plus_memory_acquire(state);','if(enabled){plus_memory_acquire(state);dc_probe(state);}')
  a=a.replace(' plus_stagger_init(&stagger);',' clo_revised_init(&dc_memory_detector);plus_stagger_init(&stagger);')
  start=a.index('static void plus_b_variation(diagnostic_readout_t *);');end=a.index('static FILE *benchmark_log;',start)
  a=a[:start]+a[end:]
  a=a.replace('plus_acquire(state,&o);','').replace('if(j>=2)plus_sensor_observation(&x);','').replace('plus_stagger_init(&stagger);','')
  a=a.replace('const char *extra_names[]={"M500"','const char *extra_names[]={"M2"')
  extra=r'''
 if(j==1){
  runtime_observation_t z=o;z.memory_check_ms=dc_memory.checked_ms;z.memory_check_valid=dc_memory.valid;z.memory_check_failed=dc_memory.failed;
  plus_arch=6;clo_triplex_core_step(&dc_memory_detector,&config,&z);clo_final_diagnostic(&dc_memory_detector.fusion.evidence,z.time_ms,3000);final_score(2,z.time_ms,&dc_memory_detector.fusion.output);
  if(!dc_packet_log)dc_packet_log=fopen(getenv("DC_PACKET"),"wb");if(!dc_input_log)dc_input_log=fopen(getenv("DC_INPUT"),"w");
  bool qualified=o.time_ms>=1000&&triplex.qualified&&triplex_detector.slew_qualification_count>=5&&o.source_valid&&o.source_ms==o.time_ms&&o.reference_valid&&!o.reference_failed&&o.reference_ms==o.time_ms&&o.sample_timestamp_ms==o.source_ms;
  dc_packet_t q={.o=o,.extra=triplex.strength,.c=triplex.aligned_c,.m={plus_memory[1],dc_memory},.ambiguous=triplex.ambiguous,.qualified=qualified};fwrite(&q,sizeof q,1,dc_packet_log);
  fprintf(dc_input_log,"%u,%.17g,%.17g,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n",o.time_ms,o.source_c-q.c,o.reference_c-q.c,qualified,triplex_detector.fusion.output.alarm,triplex_detector.fusion.output.estimated_origin,plus_detector[j].fusion.output.alarm,plus_detector[j].fusion.output.estimated_origin,dc_memory_detector.fusion.output.alarm,dc_memory_detector.fusion.output.estimated_origin,state->control.memory_diagnostic.checks,plus_memory[1].checks,dc_memory.checks,o.source_c,o.reference_c,q.c,o.engine_load,o.pump_command,o.fan_command,o.vehicle_speed_kph,q.extra);
 }
'''
  a=a.replace('  final_score(j+2,o.time_ms,&plus_detector[j].fusion.output);','  final_score(j+2,o.time_ms,&plus_detector[j].fusion.output);'+extra)
  a=a.replace('int main(int argc,char **argv)',REPLAY+'\nint main(int argc,char **argv)').replace(' int write=1;',' if(argc==5&&!strcmp(argv[1],"--dc-replay"))return dc_replay(argv[2],argv[3],argv[4]);\n int write=1;');return a
 source=getsource(oldbuild).replace('extended=core\n',"extended='extern double dc_mass,dc_origin,dc_discount;\\n'+core.replace('benchmark_capture(0,','benchmark_capture(1,')\n extended=extended.replace('    s->evidence.strength[3] = fmax(s->evidence.strength[3], local);',"+repr(INJECT)+")\n")
 source=source.replace("'src/v7_3/triplex_consistency.c']","'src/v7_3/triplex_consistency.c','src/v7_3/dynamic_consensus.c','src/v7_3/multirate_memory.c']")
 r.adapt=adapt;r.inspect.getsource=lambda fn:source if fn is oldbuild else getsource(fn)
 try:return r.build(w)
 finally:r.adapt=oldadapt;r.inspect.getsource=getsource

PROTOCOL=(ROOT/'scripts/dynamic_consensus_protocol.md').read_text()

def setup():
 verify();B.mkdir(exist_ok=True);O.mkdir(exist_ok=True);assert not (B/'specs.json').exists()
 protected={str(p):sha(p) for root in ['src','include','scripts','python','tests','presets'] for p in (ROOT/root).rglob('*') if p.is_file() and '__pycache__' not in str(p) and 'dynamic_consensus' not in p.name};protected.update({str(p):sha(p) for p in (ROOT/'results').rglob('*') if p.is_file() and 'dynamic_consensus_development' not in str(p)});dump(B/'protected.json',protected)
 ss=design();r.historical.OUT=B;r.historical.B=B;r.historical.historical_audit(ss);dump(B/'specs.json',ss);h.write(B/'prior_manifest.csv',ss)
 (O/'model_definition.md').write_text(PROTOCOL);dump(B/'registration.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),utc=r.now(),manifest_sha256=sha(B/'prior_manifest.csv'),protocol_sha256=sha(O/'model_definition.md')));print('REGISTERED8400',flush=True)

def collect(part,benign=False):
 verify();tag=part+('_BENIGN' if benign else '');assert not (B/(tag+'_started')).exists()
 if part=='VALIDATION':assert (B/'lock.json').exists()
 if part=='VALIDATION' and not benign:assert (B/'benign_gate.json').exists()
 (B/(tag+'_started')).write_text(r.now());ss=[s for s in json.loads((B/'specs.json').read_text()) if s['partition']==part and (s['origin']=='NORMAL' if benign else s['origin']!='NORMAL' if part=='VALIDATION' else True)]
 w=B/'work';w.mkdir(exist_ok=True);h.prepare_work(w,ss);exe=build(w)
 for key,name in [('TRIPLEX_LOG','triplex.csv'),('PLUS_META','plus_meta.csv'),('BENCHMARK_LOG','benchmark.csv'),('DC_PACKET','packet.bin'),('DC_INPUT','input.csv')]:os.environ[key]=str(w/name)
 os.environ['PLUS_HOST_MODE']='2';h.c.METHODS=['A0','M250','M2'];h.c.command=lambda s,w:r.t.command(s,w,exe)
 rows=[];(B/'tapes').mkdir(exist_ok=True);original=h.c.read;cache={}
 def read(p):
  rr=original(p)
  if Path(p).name=='observations.csv':cache['obs']=rr
  return rr
 h.c.read=read
 for i,s in enumerate(ss):
  rr=h.c.execute(s,w,False);a=np.loadtxt(w/'input.csv',delimiter=',');e=bench.evidence(np.loadtxt(w/'benchmark.csv',delimiter=','),6)
  active=[v for v in cache['obs'] if h.prior.prior.active(s,int(v['time_ms']))];axis='pump_command' if s['model']=='pump_degraded' else 'fan_command';num=lambda v:float.fromhex(v) if '0x' in str(v) else float(v)
  for row in rr:row.update(method={'A0':'A0','M250':'M1','M2':'M2'}[row['method']],initially_excited=int(s['origin']=='ACTUATOR' and bool(active) and num(active[0][axis])>0),actuator_excited=int(s['origin']=='ACTUATOR' and any(num(v[axis])>0 for v in active)))
  rows.extend(rr);target=np.array([s['origin']!='NORMAL' and (h.prior.prior.active(s,int(ms)) or h.prior.prior.active(s,max(0,int(ms)-99))) for ms in a[:,0]])
  np.savez_compressed(B/'tapes'/(s['run_id']+'.npz'),input=a,values=e.strength,available=e.available,subset=e.origin_subset,target=target)
  (B/'tapes'/(s['run_id']+'.bin.gz')).write_bytes(gzip.compress((w/'packet.bin').read_bytes(),mtime=0))
  for name in ['packet.bin','input.csv','benchmark.csv','triplex.csv','plus_meta.csv']:(w/name).unlink()
  if (i+1)%150==0:print(tag,i+1,'/',len(ss),flush=True)
 h.c.read=original;dump(B/(tag+'_rows.json'),rows);verify();print('COMPLETE',tag,flush=True)

def dataset(part):
 for row in json.loads((B/(part+'_rows.json')).read_text()):
  if row['method']=='A0':yield row,np.load(B/'tapes'/(row['run_id']+'.npz'))
if __name__=='__main__':
 if sys.argv[1]=='setup':setup()
 elif sys.argv[1]=='collect':collect(sys.argv[2],len(sys.argv)>3)
