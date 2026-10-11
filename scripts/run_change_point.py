#!/usr/bin/env python3
"""One registered multiscale cp development campaign; retained core untouched."""
import os,sys,json,inspect,subprocess,hashlib,gzip,pickle,collections,shutil,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=['/tmp/clo-ml-deps',str(ROOT/'scripts'),str(ROOT/'python')]
import numpy as np
import run_triplex_plus as r
import run_ml_assisted_clodsf as ml
import run_parity_space as history
import select_triplex_plus as prior
B=Path('/tmp/clo-change-point');O=ROOT/'results/change_point_development';h=r.h;sha=r.sha;bench=r.bench

def dump(p,v):p.write_text(json.dumps(v,indent=2))
def verify():
 history.verify()
 historical=ROOT/'results/parity_space_development/thresholds.json'
 record=json.loads(historical.read_text())
 for name,value in record.get('artifact_hashes',{}).items():
  path=Path(name);path=path if path.is_absolute() else historical.parent/path
  assert sha(path)==value,str(path)
 if (B/'protected.json').exists():assert all(sha(Path(p))==v for p,v in json.loads((B/'protected.json').read_text()).items())
 if (B/'lock.json').exists():assert all(sha(Path(p))==v for p,v in json.loads((B/'lock.json').read_text()).items())

def design():
 templates=r.design();out=[]
 for f in range(50):
  part='TRAIN' if f<20 else 'CALIBRATION' if f<40 else 'VALIDATION';n=20 if f<20 else 10 if f<40 else 24;total=150 if f<20 else 100 if f<40 else 240;local=f if f<20 else f-20 if f<40 else f-40
  for j in range(total):
   fault=j<5*n;origin_index=j//n if fault else 5;k=j%n if fault else j-5*n
   idx=origin_index*24+(k+(local*7 if n<24 else 0))%24 if fault else 120+k%30
   s=dict(templates[(f%21)*150+idx]);i=len(out)
   s.update(run_id=f'cp_{i:04}',profile=f'cp_profile_{i:04}',group=f'cp_family_{f}',partition=part,seed=3501000031+i*251,reference_seed=3603000047+i*257,c_seed=3707000069+i*263)
   profile=json.loads(s['profile_json'])
   for z,v in enumerate(profile):
    v['ambient_temp_c']+=2.713+(f%7)*.173+j*.000061;v['engine_load']*=.917+(f%5)*.017;v['vehicle_speed_kph']+=2.317+i*.000019
    if not fault and k%10==3:v['vehicle_speed_kph']=[.37,87.13,23.17,12.73,94.11][z]
   s['c_phase_ms']=[7,31,71,93][f%4];s['c_quantum']=[.014,.022,.026][f%3]
   if fault:s['start_ms']+=2100+(f%9)*100
   if s['origin']=='SENSOR_CONTROL':
    si=local*n+k;domain=['A','B','C','AB','ABC'][si%5];cell=(si//5)%8;kind=['step','step','step','pulse','pulse','ramp','step','ramp'][cell]
    weak=[.41,.46,.49,.53,.57][(local+cell)%5];sign=-1 if (si//40+cell)%2 else 1
    mag=[sign*weak,-sign*weak,sign*1.07,sign*weak,sign*.67,3.13+f*.013,-sign*.51,-(2.93+f*.011)][cell]
    phase=([5,23,41] if part=='TRAIN' else [13,47,67] if part=='CALIBRATION' else [19,59,89])[(local+cell)%3]
    s.update(domain=domain,sensor_chain=domain,kind=kind,model={'step':'sensor_bias','pulse':'sensor_interface_intermittent','ramp':'sensor_bias_ramp'}[kind],magnitude=mag,behavior='transient' if kind=='pulse' else 'permanent',duration_ms=([50,150,250][local%3] if cell==3 else [700,1100,1700][local%3]) if kind=='pulse' else 0,sensor_ramp_rise_ms=[25700,47900,72700,95300][(local+cell)%4] if kind=='ramp' else 0,start_ms=24700+local*300+cell*400+phase,initially_latent_stuck=0,workload='cp_sensor',target_updates_json='[]')
   if not fault and k%3==0:
    s['benign_reference_magnitude']=(-1 if (local+k)%2 else 1)*[.2,.32,.5][(k//3+local)%3];s['benign_reference_duration']=[100,1100,2300,5100][(k//3+local)%4];s['workload']='legal_offset_'+str(s['benign_reference_duration'])
   s['profile_json']=json.dumps(profile,sort_keys=True);s['profile_semantic_sha256']=h.profile_identity(profile);s.pop('configuration_sha256',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();out.append(s)
 assert len(out)==7400
 return out

FRONT=r'''
#include "triplex_change_point.h"
static FILE *cp_packet_log,*cp_input_log;
double cp_mass;
typedef struct {runtime_observation_t o;double extra,ac,bc;unsigned checked;bool failed,valid,ambiguous,qualified;} cp_packet_t;
'''
REPLAY=r'''
static int cp_replay(const char *path,const char *parameters,const char *output){
 cp_config_t p={0};FILE *f=fopen(parameters,"r");if(!f)return 2;
 double v[18];for(unsigned i=0;i<18;i++)if(fscanf(f,"%lf",&v[i])!=1)return 3;fclose(f);
 for(unsigned i=0;i<2;i++)p.mu[i]=v[i];for(unsigned i=0;i<3;i++)p.chol[i]=v[2+i];
 for(unsigned k=0;k<2;k++){for(unsigned i=0;i<2;i++)p.slope_mu[k][i]=v[5+5*k+i];for(unsigned i=0;i<3;i++)p.slope_chol[k][i]=v[7+5*k+i];}
 p.threshold=v[15];p.gamma=v[16];p.combination=(unsigned)v[17];
 f=fopen(getenv("CP_CDF"),"rb");if(!f)return 8;
 for(unsigned j=0;j<3;j++){if(fread(&p.cdf_n[j],4,1,f)!=1)return 9;double *cdf=malloc(sizeof(double)*p.cdf_n[j]);if(!cdf||fread(cdf,sizeof(double),p.cdf_n[j],f)!=p.cdf_n[j])return 10;p.cdf[j]=cdf;}fclose(f);
 if(final_config_read("results/cross_layer_safety_v7_3_dev/revised.cfg",&config))return 4;
 FILE *in=fopen(path,"rb"),*out=fopen(output,"w");if(!in||!out)return 5;
 benchmark_log=fopen(getenv("BENCHMARK_LOG"),"w");if(!benchmark_log)return 6;
 bool light=getenv("CP_LIGHT")&&atoi(getenv("CP_LIGHT"));bool skip_base=getenv("CP_SKIP_BASE")&&atoi(getenv("CP_SKIP_BASE"));
 clo_revised_t detector[7];for(unsigned j=0;j<7;j++)clo_revised_init(&detector[j]);cp_state_t provider={0};cp_packet_t q;
 while(fread(&q,sizeof q,1,in)==1){
  cp_input_t u={q.o.time_ms,q.ac,q.bc,q.qualified};triplex_cp_step(&provider,&p,&u);if(!provider.stable)return 7;
  fprintf(out,"%u",q.o.time_ms);
  for(unsigned j=0;j<3;j++)fprintf(out,",%.17g",provider.raw[j]);
  for(unsigned j=0;j<3;j++)fprintf(out,",%.17g",provider.p[j]);
  fprintf(out,",%.17g,%.17g",provider.rarity,provider.mass);
  for(unsigned j=0;j<3;j++)fprintf(out,",%.17g",provider.isolated_mass[j]);
  fprintf(out,",%u,%u,%u,%u",provider.start_step,provider.start_transient,provider.end_transient,provider.drift_window);
  for(unsigned k=0;k<2;k++)for(unsigned j=0;j<2;j++)fprintf(out,",%.17g",provider.slope[k][j]);
  for(unsigned j=0;j<3;j++)fprintf(out,",%u",provider.available[j]);
  for(unsigned j=0;j<7;j++){
   if((light&&j>=4)||(skip_base&&(j==0||j==2))){fprintf(out,",0,0,0");continue;}
   runtime_observation_t x=q.o;if(j>=2){x.memory_check_ms=q.checked;x.memory_check_valid=q.valid;x.memory_check_failed=q.failed;}
   triplex_extra_strength=q.extra;triplex_extra_ambiguous=q.ambiguous;cp_mass=j==1||j==3?provider.mass:j>=4?provider.isolated_mass[j-4]:0;
   plus_arch=j;clo_triplex_core_step(&detector[j],&config,&x);clo_final_diagnostic(&detector[j].fusion.evidence,x.time_ms,3000);
   fprintf(out,",%u,%u,%.17g",detector[j].fusion.output.alarm,detector[j].fusion.output.estimated_origin,detector[j].fusion.output.anomaly_decision_score);
  }fprintf(out,"\n");
 }
 for(unsigned j=0;j<3;j++)free((void*)p.cdf[j]);fclose(in);fclose(out);fclose(benchmark_log);return 0;
}
'''

def build(w):
 oldadapt=r.adapt;oldbuild=r.t.build;getsource=r.inspect.getsource
 def adapt(a):
  a=oldadapt(a).replace('static unsigned plus_arch;',FRONT+'\nstatic unsigned plus_arch;')
  extra=r'''
 if(j==1){
  if(!cp_packet_log)cp_packet_log=fopen(getenv("CP_PACKET"),"wb");
  if(!cp_input_log)cp_input_log=fopen(getenv("CP_INPUT"),"w");
  bool qualified=o.time_ms>=1000&&triplex.qualified&&triplex_detector.slew_qualification_count>=5&&o.source_valid&&o.source_ms==o.time_ms&&o.reference_valid&&!o.reference_failed&&o.reference_ms==o.time_ms&&o.sample_timestamp_ms==o.source_ms;
  cp_packet_t q={.o=o,.extra=triplex.strength,.ac=o.source_c-triplex.aligned_c,.bc=o.reference_c-triplex.aligned_c,.checked=plus_memory[1].checked_ms,.failed=plus_memory[1].failed,.valid=plus_memory[1].valid,.ambiguous=triplex.ambiguous,.qualified=qualified};fwrite(&q,sizeof q,1,cp_packet_log);
  fprintf(cp_input_log,"%u,%.17g,%.17g,%u,%u,%u,%u,%u,%u,%u\n",o.time_ms,q.ac,q.bc,qualified,triplex_detector.fusion.output.alarm,triplex_detector.fusion.output.estimated_origin,plus_detector[j].fusion.output.alarm,plus_detector[j].fusion.output.estimated_origin,state->control.memory_diagnostic.checks,plus_memory[1].checks);
 }
'''
  a=a.replace('  final_score(j+2,o.time_ms,&plus_detector[j].fusion.output);','  final_score(j+2,o.time_ms,&plus_detector[j].fusion.output);'+extra)
  a=a.replace('int main(int argc,char **argv)',REPLAY+'\nint main(int argc,char **argv)').replace(' int write=1;',' if(argc==5&&!strcmp(argv[1],"--cp-replay"))return cp_replay(argv[2],argv[3],argv[4]);\n int write=1;');return a
 source=getsource(oldbuild).replace('extended=core\n',"extended='extern double cp_mass;\\n'+core\n extended=extended.replace('    s->evidence.strength[3] = fmax(s->evidence.strength[3], local);','    local=fmax(local,cp_mass);\\n    s->evidence.strength[3] = fmax(s->evidence.strength[3], local);')\n")
 # r.build also replaces extended=core to tag benchmark capture; do it explicitly.
 source=source.replace("extended='extern double cp_mass;\\n'+core", "extended='extern double cp_mass;\\n'+core.replace('benchmark_capture(0,','benchmark_capture(1,')")
 source=source.replace("'src/v7_3/triplex_consistency.c']","'src/v7_3/triplex_consistency.c','src/v7_3/triplex_change_point.c']")
 # Preserve r.build's existing memory links despite extending the link list.
 source=source.replace("'src/v7_3/triplex_change_point.c']","'src/v7_3/triplex_change_point.c','src/v7_3/triplex_plus.c','src/v7_3/multirate_memory.c']")
 r.adapt=adapt;r.inspect.getsource=lambda fn:source if fn is oldbuild else getsource(fn)
 try:return r.build(w)
 finally:r.adapt=oldadapt;r.inspect.getsource=getsource

PROTOCOL=(ROOT/'scripts/change_point_protocol.md').read_text()

def setup():
 verify();B.mkdir(exist_ok=True);O.mkdir(exist_ok=True);assert not (B/'specs.json').exists()
 protected={str(p):sha(p) for root in ['src','include','scripts','python','tests','presets'] for p in (ROOT/root).rglob('*') if p.is_file() and '__pycache__' not in str(p) and 'change_point' not in p.name};dump(B/'protected.json',protected)
 ss=design();r.historical.OUT=B;r.historical.B=B;r.historical.historical_audit(ss);dump(B/'specs.json',ss);h.write(B/'prior_manifest.csv',ss)
 (O/'detector_definition.md').write_text(PROTOCOL);dump(B/'registration.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),utc=r.now(),manifest_sha256=sha(B/'prior_manifest.csv'),protocol_sha256=sha(O/'detector_definition.md')));print('REGISTERED7400',flush=True)

def collect(part,benign=False):
 verify();tag=part+('_BENIGN' if benign else '');assert not (B/(tag+'_started')).exists()
 if part=='VALIDATION':assert (B/'lock.json').exists()
 if part=='VALIDATION' and not benign:assert (B/'benign_gate.json').exists()
 (B/(tag+'_started')).write_text(r.now());ss=[s for s in json.loads((B/'specs.json').read_text()) if s['partition']==part and (s['origin']=='NORMAL' if benign else s['origin']!='NORMAL' if part=='VALIDATION' else True)]
 w=B/'work';w.mkdir(exist_ok=True);h.prepare_work(w,ss);exe=build(w)
 for key,name in [('TRIPLEX_LOG','triplex.csv'),('PLUS_META','plus_meta.csv'),('BENCHMARK_LOG','benchmark.csv'),('CP_PACKET','packet.bin'),('CP_INPUT','input.csv')]:os.environ[key]=str(w/name)
 os.environ['PLUS_HOST_MODE']='2';h.c.METHODS=['A0','M250'];h.c.command=lambda s,w:r.t.command(s,w,exe)
 rows=[];(B/'tapes').mkdir(exist_ok=True);original=h.c.read;cache={}
 def read(p):
  rr=original(p)
  if Path(p).name=='observations.csv':cache['obs']=rr
  return rr
 h.c.read=read
 for i,s in enumerate(ss):
  rr=h.c.execute(s,w,False);a=np.loadtxt(w/'input.csv',delimiter=',');e=bench.evidence(np.loadtxt(w/'benchmark.csv',delimiter=','),2)
  active=[v for v in cache['obs'] if h.prior.prior.active(s,int(v['time_ms']))];axis='pump_command' if s['model']=='pump_degraded' else 'fan_command';num=lambda v:float.fromhex(v) if '0x' in str(v) else float(v)
  for row in rr:row.update(method='A0' if row['method']=='A0' else 'A2',initially_excited=int(s['origin']=='ACTUATOR' and bool(active) and num(active[0][axis])>0),actuator_excited=int(s['origin']=='ACTUATOR' and any(num(v[axis])>0 for v in active)))
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
