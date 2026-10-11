#!/usr/bin/env python3
"""One registered multiscale parity development campaign; retained core untouched."""
import os,sys,json,inspect,subprocess,hashlib,gzip,pickle,collections,shutil,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=['/tmp/clo-ml-deps',str(ROOT/'scripts'),str(ROOT/'python')]
import numpy as np
import run_triplex_plus as r
import run_ml_assisted_clodsf as ml
import select_triplex_plus as prior
B=Path('/tmp/clo-parity-space');O=ROOT/'results/parity_space_development';h=r.h;sha=r.sha;bench=r.bench

def dump(p,v):p.write_text(json.dumps(v,indent=2))
def verify():
 ml.verify()
 if (B/'protected.json').exists():assert all(sha(Path(p))==v for p,v in json.loads((B/'protected.json').read_text()).items())
 if (B/'lock.json').exists():assert all(sha(Path(p))==v for p,v in json.loads((B/'lock.json').read_text()).items())

def design():
 templates=r.design();out=[];index=0
 for f in range(36):
  part='TRAIN' if f<16 else 'CALIBRATION' if f<26 else 'VALIDATION';n=20 if f<16 else 18 if f<26 else 24;local=f if f<16 else f-16 if f<26 else f-26
  for j in range(150):
   fault=j<5*n;origin_index=j//n if fault else 5;k=j%n if fault else j-5*n
   idx=origin_index*24+(k+(local*5 if n<24 else 0))%24 if fault else 120+k%30
   s=dict(templates[(f%21)*150+idx]);i=index;index+=1
   s.update(run_id=f'parity_{i:04}',profile=f'parity_profile_{i:04}',group=f'parity_family_{f}',partition=part,seed=3101000007+i*251,reference_seed=3203000011+i*257,c_seed=3307000019+i*263)
   p=json.loads(s['profile_json'])
   for z,v in enumerate(p):
    v['ambient_temp_c']+=1.823+(f%7)*.137+j*.000057;v['engine_load']*=.941+(f%5)*.013;v['vehicle_speed_kph']+=1.913+i*.000017
    if not fault and k%10==3:v['vehicle_speed_kph']=[.43,84.73,26.91,11.13,91.87][z]
   s['c_phase_ms']=[1,29,67,97][f%4];s['c_quantum']=[.016,.02,.024][f%3]
   if fault:s['start_ms']+=1700+(f%9)*100
   if s['origin']=='SENSOR_CONTROL':
    si=local*n+k;domain=['A','B','C','AB','ABC'][si%5];cell=(si//5)%8;kind=['step','step','step','pulse','pulse','ramp','step','ramp'][cell]
    weak=[.43,.55][local%2] if part=='TRAIN' else [.46,.52][local%2] if part=='CALIBRATION' else .49
    mag=[.49,weak,(-1 if local%2 else 1)*1.03,.49,(-1 if local%2 else 1)*.63,3.07+f*.011,-.49,-(2.87+f*.009)][cell]
    phase=([3,19,37] if part=='TRAIN' else [11,43,61] if part=='CALIBRATION' else [17,53,83])[(local+cell)%3]
    s.update(domain=domain,sensor_chain=domain,kind=kind,model={'step':'sensor_bias','pulse':'sensor_interface_intermittent','ramp':'sensor_bias_ramp'}[kind],magnitude=mag,behavior='transient' if kind=='pulse' else 'permanent',duration_ms=([50,150,250][local%3] if cell==3 else [700,1100,1700][local%3]) if kind=='pulse' else 0,sensor_ramp_rise_ms=[25300,47100,71300,93700][(local+cell)%4] if kind=='ramp' else 0,start_ms=24100+local*300+cell*400+phase,initially_latent_stuck=0,workload='parity_sensor',target_updates_json='[]')
   if not fault and k%3==0:s['benign_reference_magnitude']=[.3,.5,.7][(k//3+local)%3];s['benign_reference_duration']=100
   s['profile_json']=json.dumps(p,sort_keys=True);s['profile_semantic_sha256']=h.profile_identity(p);s.pop('configuration_sha256',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();out.append(s)
 assert len(out)==5400
 return out

FRONT=r'''
#include "triplex_parity.h"
static FILE *parity_packet_log,*parity_input_log;
double parity_mass,parity_origin_mass;
typedef struct {runtime_observation_t o;double extra,ac,bc;unsigned checked;bool failed,valid,ambiguous,qualified;} parity_packet_t;
'''
REPLAY=r'''
static int parity_replay(const char *path,const char *parameters,const char *output){
 parity_config_t p;FILE *f=fopen(parameters,"r");if(!f)return 2;
 if(fscanf(f,"%lf %lf %lf %lf %lf %lf %lf %lf %lf",&p.mu[0],&p.mu[1],&p.l00,&p.l10,&p.l11,&p.tau,&p.saturation,&p.beta,&p.dominance)!=9)return 3;fclose(f);
 if(final_config_read("results/cross_layer_safety_v7_3_dev/revised.cfg",&config))return 4;
 FILE *in=fopen(path,"rb"),*out=fopen(output,"w");if(!in||!out)return 5;
 benchmark_log=fopen(getenv("BENCHMARK_LOG"),"w");if(!benchmark_log)return 6;
 clo_revised_t detector[4];for(unsigned j=0;j<4;j++)clo_revised_init(&detector[j]);parity_state_t provider={0};parity_packet_t q;
 while(fread(&q,sizeof q,1,in)==1){
  parity_input_t u={q.o.time_ms,q.ac,q.bc,q.qualified};triplex_parity_step(&provider,&p,&u);
  if(!provider.stable)return 7;
  fprintf(out,"%u,%.17g,%.17g,%.17g,%u,%u,%.17g",q.o.time_ms,provider.g,provider.m,provider.current_m,provider.window,provider.direction,provider.mass);
  for(unsigned k=0;k<4;k++)fprintf(out,",%.17g",provider.directional[k]);
  for(unsigned j=0;j<4;j++){
   runtime_observation_t x=q.o;if(j>=2){x.memory_check_ms=q.checked;x.memory_check_valid=q.valid;x.memory_check_failed=q.failed;}
   triplex_extra_strength=q.extra;triplex_extra_ambiguous=q.ambiguous;parity_mass=(j&1)?provider.mass:0;parity_origin_mass=(j&1)?provider.origin_mass:0;
   plus_arch=j;clo_triplex_core_step(&detector[j],&config,&x);clo_final_diagnostic(&detector[j].fusion.evidence,x.time_ms,3000);
   fprintf(out,",%u,%u,%.17g",detector[j].fusion.output.alarm,detector[j].fusion.output.estimated_origin,detector[j].fusion.output.anomaly_decision_score);
  }fprintf(out,"\n");
 }
 fclose(in);fclose(out);fclose(benchmark_log);return 0;
}
'''
def build(w):
 oldadapt=r.adapt;oldbuild=r.t.build;getsource=r.inspect.getsource
 def adapt(a):
  a=oldadapt(a).replace('static unsigned plus_arch;',FRONT+'\nstatic unsigned plus_arch;')
  extra=r'''
 if(j==1){
  if(!parity_packet_log)parity_packet_log=fopen(getenv("PARITY_PACKET"),"wb");
  if(!parity_input_log)parity_input_log=fopen(getenv("PARITY_INPUT"),"w");
  bool qualified=o.time_ms>=1000&&triplex.qualified&&triplex_detector.slew_qualification_count>=5&&o.source_valid&&o.source_ms==o.time_ms&&o.reference_valid&&!o.reference_failed&&o.reference_ms==o.time_ms&&o.sample_timestamp_ms==o.source_ms;
  parity_packet_t q={.o=o,.extra=triplex.strength,.ac=o.source_c-triplex.aligned_c,.bc=o.reference_c-triplex.aligned_c,.checked=plus_memory[1].checked_ms,.failed=plus_memory[1].failed,.valid=plus_memory[1].valid,.ambiguous=triplex.ambiguous,.qualified=qualified};fwrite(&q,sizeof q,1,parity_packet_log);
  fprintf(parity_input_log,"%u,%.17g,%.17g,%u,%u,%u,%u,%u,%u,%u\n",o.time_ms,q.ac,q.bc,qualified,triplex_detector.fusion.output.alarm,triplex_detector.fusion.output.estimated_origin,plus_detector[j].fusion.output.alarm,plus_detector[j].fusion.output.estimated_origin,state->control.memory_diagnostic.checks,plus_memory[1].checks);
 }
'''
  a=a.replace('  final_score(j+2,o.time_ms,&plus_detector[j].fusion.output);','  final_score(j+2,o.time_ms,&plus_detector[j].fusion.output);'+extra)
  a=a.replace('int main(int argc,char **argv)',REPLAY+'\nint main(int argc,char **argv)').replace(' int write=1;',' if(argc==5&&!strcmp(argv[1],"--parity-replay"))return parity_replay(argv[2],argv[3],argv[4]);\n int write=1;');return a
 source=getsource(oldbuild).replace('extended=core\n',"extended='extern double parity_mass,parity_origin_mass;\\n'+core\n extended=extended.replace('    s->evidence.strength[3] = fmax(s->evidence.strength[3], local);','    local=fmax(local,parity_mass);origin_local=fmax(origin_local,parity_origin_mass);\\n    s->evidence.strength[3] = fmax(s->evidence.strength[3], local);')\n")
 # r.build also replaces extended=core to tag benchmark capture; do it explicitly.
 source=source.replace("extended='extern double parity_mass,parity_origin_mass;\\n'+core", "extended='extern double parity_mass,parity_origin_mass;\\n'+core.replace('benchmark_capture(0,','benchmark_capture(1,')")
 source=source.replace("'src/v7_3/triplex_consistency.c']","'src/v7_3/triplex_consistency.c','src/v7_3/triplex_parity.c']")
 # Preserve r.build's existing memory links despite extending the link list.
 source=source.replace("'src/v7_3/triplex_parity.c']","'src/v7_3/triplex_parity.c','src/v7_3/triplex_plus.c','src/v7_3/multirate_memory.c']")
 r.adapt=adapt;r.inspect.getsource=lambda fn:source if fn is oldbuild else getsource(fn)
 try:return r.build(w)
 finally:r.adapt=oldadapt;r.inspect.getsource=getsource

PROTOCOL='''# Multiscale Triplex parity-space development: preregistration
5400 new scenarios in disjoint profile families. TRAIN2400=1600fault/800benign, CAL1500=900fault/600benign, VALID1500=1200fault/300benign; VALID240faults per origin. Equal origin representation within partitions; retain dormant memory and idle actuator cases. Sensor geometry A/B/C/AB/ABC with weak signed steps, stronger steps, short/long pulses and drift; near-boundary TRAIN .43/.55 and CAL .46/.52, fixed VALID .49. Phase sets TRAIN3/19/37, CAL11/43/61, VALID17/53/83ms. No composition changes after outcomes. Benign noise, legal reference excursions, target/load/speed/ambient transitions and C phase/quantization edges. Warm-engine initialization is unchanged; cold ambient is not cold-soak initialization.
Use only p=[A-alignedC,B-alignedC] from retained causal alignment. Qualified after startup1000ms, retained slew qualification, fresh A/B, qualified C, current consumption. Noncontiguous/unqualified observations reset history. W={1,2,4,8}. H={A[1,0],B[0,1],C[-1,-1],AB[1,1]}; squared scores make C/AB exactly indistinguishable. A/BC and B/AC cuts likewise do not prove which side failed. Global equal ABC change is parity-unobservable; causal alignment can introduce small transient projection artifacts, which are not independent absolute-temperature information.
Benign TRAIN covariance candidates C0 standard covariance+global .0004 C^2 diagonal regularization, C1 Huber Mahalanobis weights min(1,2.5/distance),20iterations with same floor. Deterministic at most24 qualified samples/run. Select by benign-only stability: worst absolute log eigenvalue ratio between TRAIN and benign CAL covariance under same estimator, plus .01 log(condition). No fault recall. Use Cholesky solves, no matrix inverse. Direction/window maximum G and Mahalanobis maximum M retained. CAL run maximum R=max_t G calibrates multiplicity over time/windows/directions. For target epsilon use k=ceil((n+1)*(1-epsilon)), ascending kth score; if k>n threshold infinity. Strict G>tau. Descriptive epsilon0 uses observed maximum only (no finite-sample zero-FPR guarantee); .005/.01/.02/.05 use finite-sample rule. Primary .01 fixed. Exchangeability is not guaranteed by deterministic grouped simulations; observed validation performance is decisive.
Soft strength=beta*clip((G-tau)/((saturation-1)*tau),0,1). CAL grid beta{.25,.5},saturation{1.5,2}; fixed dominance2. Candidate selection CAL requires benign<=1%,zero wrong confident FAULT origins,no startup/critical-origin loss; then maximum sensor detection,plant coverage,first-origin correctness,lower beta,larger saturation. If none passes, reject and evaluate fixed beta.25/saturation2 diagnostic reference. Parity and old sensor residuals share data: combine by MAX within the existing one sensor channel, not separate independent votes. Only a dominant A or B cut contributes parity origin strength; C/AB tie or insufficient dominance contributes no origin mass. Existing physical origin evidence, causal precedence, thresholds and Dempster rule unchanged. No confident member diagnosis. Optional memory is exact existing250ms average/300msmaximum alternating200/300 implementation, atomic save/test/restore, independently ablated.
A0 retained, A1 parity, A2memory, A3both. One physical simulation includes readback-and-restore diagnostics with plant invariance assertion; diagnostic replay only, no physical re-execution for parameter choices. Fair SVM-R has six qualified cross-layer streams,availability,causal1s mean/max plus raw parity and qualification, using250ms memory observability. SVM-P adds current Mahalanobis, four direction maxima,Gmax,Mmax. TRAIN-only balanced SVC linearC.1,linearC1,RBFC1,StandardScaler,up to8uniformframes/class/run. CAL selection default balanced run accuracy,then recall,then simpler predefined order. Each matched<=1% threshold uses benign CAL run-max margins with the same finite-sample order rule. No localization from SVM. No fault/scenario/time/hidden-truth fields in features; labels offline only.
Lock sources,models,covariance,mapping,thresholds,manifest before any VALID; benign VALID first. No post-validation changes. Promotion A3>=1pp overA0,zero parity detection losses A1vsA0/A3vsA2,benign<=1%,zero wrong confident FAULT origins,no Timing/Communication/effectiveMemory loss,plant>=98%,and first-localization accuracy including UNKNOWN not lower than A0, runtime fault localized accuracy not lower. Memory alone may be retained independently only with additional dormant detection,no losses or new benign/wrong origins; parity never retained just because memory improved. Full regression if any new architecture retained. No unseen/commit/push. Preserve all historical evidence and GUI. Intervals/tests descriptive for grouped deterministic cases. Causally aligned geometry/GLRT/Mahalanobis/conformal methods are established; no mathematical novelty claimed.
Output only requested fourteen summary/definition files; manifest,models,locks and audit metadata embedded in covariance_model.json/thresholds.json, plus deterministic generator. No bulk traces retained. Temporary per-frame packets deleted after accounting. Planned representative traces0.
'''
def setup():
 verify();B.mkdir(exist_ok=True);O.mkdir(exist_ok=True);assert not (B/'specs.json').exists()
 protected={str(p):sha(p) for root in ['src','include','scripts','python','tests','presets'] for p in (ROOT/root).rglob('*') if p.is_file() and '__pycache__' not in str(p) and 'parity_space' not in p.name and 'triplex_parity' not in p.name};dump(B/'protected.json',protected)
 ss=design();r.historical.OUT=B;r.historical.B=B;r.historical.historical_audit(ss);dump(B/'specs.json',ss);h.write(B/'prior_manifest.csv',ss)
 (O/'parity_definition.md').write_text(PROTOCOL);dump(B/'registration.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),utc=r.now(),manifest_sha256=sha(B/'prior_manifest.csv'),protocol_sha256=sha(O/'parity_definition.md')));print('REGISTERED5400',flush=True)

def collect(part,benign=False):
 verify();tag=part+('_BENIGN' if benign else '');assert not (B/(tag+'_started')).exists()
 if part=='VALIDATION':assert (B/'lock.json').exists()
 if part=='VALIDATION' and not benign:assert (B/'benign_gate.json').exists()
 (B/(tag+'_started')).write_text(r.now());ss=[s for s in json.loads((B/'specs.json').read_text()) if s['partition']==part and (s['origin']=='NORMAL' if benign else s['origin']!='NORMAL' if part=='VALIDATION' else True)]
 w=B/'work';w.mkdir(exist_ok=True);h.prepare_work(w,ss);exe=build(w)
 for key,name in [('TRIPLEX_LOG','triplex.csv'),('PLUS_META','plus_meta.csv'),('BENCHMARK_LOG','benchmark.csv'),('PARITY_PACKET','packet.bin'),('PARITY_INPUT','input.csv')]:os.environ[key]=str(w/name)
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
