#!/usr/bin/env python3
"""Restricted sensor ML evidence development; no production source edits."""
import os,sys,json,inspect,subprocess,hashlib,pickle,gzip,collections,time,shutil,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=['/tmp/clo-ml-deps',str(ROOT/'scripts'),str(ROOT/'python')]
import numpy as np
import run_triplex_plus as old
import run_clo_dsf_triplex as t
import run_comparative_benchmark as bench
from scipy.special import expit
from scipy.stats import binomtest
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
B=Path('/tmp/clo-ml-assisted');O=ROOT/'results/ml_assisted_clodsf_development';h=t.h;sha=t.sha
FEATURES=['sensor_strength','sensor_mean1s','sensor_max1s','sensor_derivative','A_minus_B','A_minus_C','B_minus_C','AB_fast','AB_slow','AC_strength','BC_strength','qualified_history']
def dump(p,v):p.write_text(json.dumps(v,indent=2))
def verify():
 old.verify()
 if (B/'protected.json').exists():assert all(sha(Path(p))==v for p,v in json.loads((B/'protected.json').read_text()).items())
 if (O/'validation_lock.json').exists():assert all(sha(Path(p))==v for p,v in json.loads((O/'validation_lock.json').read_text()).items())

def design():
 templates=old.design();out=[]
 for f in range(26):
  for j in range(150):
   i=f*150+j;s=dict(templates[(f%21)*150+j]);s.update(run_id=f'mlassist_{i:04}',profile=f'mlassist_profile_{i:04}',group=f'mlassist_family_{f}',partition='TRAIN' if f<12 else 'CALIBRATION' if f<18 else 'VALIDATION',seed=2701000009+i*233,reference_seed=2803000019+i*239,c_seed=2909000021+i*241)
   p=json.loads(s['profile_json'])
   for k,v in enumerate(p):
    v['ambient_temp_c']+=1.419+((f*5)%9)*.173+j*.000041;v['vehicle_speed_kph']+=2.731+i*.000023;v['engine_load']*=.953+(f%5)*.011
    if j%10==2:v['vehicle_speed_kph']=[.71,81.17,37.3,12.37,94.31][k]+f*.001
   if s['origin']!='NORMAL':s['start_ms']+=1300+(f%8)*100
   if s['origin']=='SENSOR_CONTROL':
    k=j-72;domain=['A','B','AB','C'][k//6];cell=k%6;kind=['step','step','pulse','pulse','ramp','step'][cell]
    mag=.49 if cell==0 else (-1 if (cell+f)%2 else 1)*(.93 if kind=='step' else .49 if cell==2 else .93 if cell==3 else 2.83+f*.019)
    duration=[50,150,250][f%3] if cell==2 else [500,900,1500][f%3] if cell==3 else 0
    # Fault phase sets are disjoint between TRAIN, CAL and VALIDATION.
    phase=([7,23,41] if f<12 else [13,31,53] if f<18 else [17,47,79])[(f+cell)%3]
    s.update(domain=domain,kind=kind,sensor_chain=domain,model={'step':'sensor_bias','pulse':'sensor_interface_intermittent','ramp':'sensor_bias_ramp'}[kind],magnitude=mag,behavior='transient' if duration else 'permanent',duration_ms=duration,sensor_ramp_rise_ms=[24700,45900,69300,91700][(f+cell)%4] if kind=='ramp' else 0,start_ms=23000+f*300+cell*400+phase)
   if s['origin']=='NORMAL' and 126<=j<144 and j%2==0:
    s['benign_reference_magnitude']=[.3,.5,.7][((j-126)//2+f)%3];s['benign_reference_duration']=100
   s['profile_json']=json.dumps(p,sort_keys=True);s['profile_semantic_sha256']=h.profile_identity(p);s.pop('configuration_sha256',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();out.append(s)
 return out

FRONT=r'''
#include "ml_sensor_weak.h"
static FILE *ml_packet_log,*ml_feature_log;
typedef struct {runtime_observation_t o;double extra;bool ambiguous;} ml_packet_t;
'''
REPLAY=r'''
static int ml_replay(const char *packet,const char *mass,const char *out){
 if(final_config_read("results/cross_layer_safety_v7_3_dev/revised.cfg",&config))return 1;
 FILE *p=fopen(packet,"rb"),*m=fopen(mass,"r"),*f=fopen(out,"w");if(!p||!m||!f)return 2;
 clo_revised_t s;clo_revised_init(&s);ml_packet_t q;double value;
 while(fread(&q,sizeof q,1,p)==1){if(fscanf(m,"%lf",&value)!=1)return 3;
  triplex_extra_strength=q.extra;triplex_extra_ambiguous=q.ambiguous;ml_extra_mass=value;
  clo_triplex_core_step(&s,&config,&q.o);clo_final_diagnostic(&s.fusion.evidence,q.o.time_ms,3000);
  fprintf(f,"%u,%u,%u,%.17g,%.17g\n",q.o.time_ms,s.fusion.output.alarm,s.fusion.output.estimated_origin,s.fusion.output.anomaly_decision_score,s.fusion.output.origin_score);
 }
 fclose(p);fclose(m);fclose(f);return 0;
}
'''
def build(w):
 source=inspect.getsource(t.build)
 source=source.replace("extended=core\n","extended=core\n extended='extern double ml_extra_mass;\\n'+extended\n extended=extended.replace('    { /* Temporal fusion is always part of the final algorithm. */', '    if(ml_extra_mass>0){support(&channel,C2_D_ABNORMAL,ml_extra_mass);if(!combine(&detect,&channel,NULL,&v->detection_conflict))v->detection_fallback=true;}\\n    { /* Temporal fusion is always part of the final algorithm. */')\n")
 # combine requires a non-null per-step conflict slot; use a local temporary.
 source=source.replace('if(ml_extra_mass>0){support','if(ml_extra_mass>0){double ml_conflict=0;support').replace('combine(&detect,&channel,NULL,','combine(&detect,&channel,&ml_conflict,')
 source=source.replace(' objs=[]',' adapter=adapt(adapter)\n objs=[]')
 def adapt(a):
  pos=a.index('static const char *names');a=a[:pos]+FRONT+'\ndouble ml_extra_mass;\n'+a[pos:]
  needle='  final_score(1,o.time_ms,&triplex_detector.fusion.output);'
  extra=r'''
 if(!ml_packet_log)ml_packet_log=fopen(getenv("ML_PACKET"),"wb");
 if(!ml_feature_log)ml_feature_log=fopen(getenv("ML_FEATURES"),"w");
 ml_packet_t q={.o=o,.extra=triplex.strength,.ambiguous=triplex.ambiguous};fwrite(&q,sizeof q,1,ml_packet_log);
 bool qualified=o.time_ms>=1000&&triplex.qualified&&triplex_detector.slew_qualification_count>=5&&o.source_valid&&o.source_ms==o.time_ms&&o.reference_valid&&!o.reference_failed&&o.reference_ms==o.time_ms&&o.sample_timestamp_ms==o.source_ms;
 fprintf(ml_feature_log,"%u,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%u,%u,%u",o.time_ms,triplex_detector.fusion.evidence.strength[3],(double)o.source_c-o.reference_c,(double)o.source_c-triplex.aligned_c,(double)o.reference_c-triplex.aligned_c,triplex_detector.fast_strength,triplex_detector.reference_strength,triplex.ac_strength,triplex.bc_strength,qualified,triplex_detector.fusion.output.alarm,triplex_detector.fusion.output.estimated_origin);
 for(unsigned k=0;k<6;k++)fprintf(ml_feature_log,",%.17g,%u",triplex_detector.fusion.evidence.strength[k],triplex_detector.fusion.evidence.available[k]);fprintf(ml_feature_log,"\n");
'''
  a=a.replace(needle,needle+extra);a=a.replace('names[0]="A0";names[1]="A1";','names[0]="CURRENT";names[1]="A0";')
  a=a.replace('int main(int argc,char **argv)',REPLAY+'\nint main(int argc,char **argv)');a=a.replace(' int write=1;', ' if(argc==5&&!strcmp(argv[1],"--ml-replay"))return ml_replay(argv[2],argv[3],argv[4]);\n int write=1;')
  return a
 ns=dict(t.__dict__,adapt=adapt);exec(source,ns);return ns['build'](w)

def setup():
 verify();assert not (B/'specs.json').exists();protected={str(p):sha(p) for parent in ['src','include','scripts','python','tests','presets'] for p in (ROOT/parent).rglob('*') if p.is_file() and '__pycache__' not in str(p) and 'ml_sensor' not in p.name and 'ml_assisted' not in p.name};dump(B/'protected.json',protected)
 ss=design();old.historical.OUT=O;old.historical.B=B;old.historical.historical_audit(ss);dump(B/'specs.json',ss);h.write(O/'campaign_manifest.csv',ss)
 (O/'protocol.md').write_text('''# Restricted ML sensor evidence development
3900 new configurations, grouped TRAIN1800/CAL900/VALID1200. Fault/benign1440/360,720/180,960/240. 24 faults per main origin and30benign per family;26 disjoint profile families. New profiles,seeds and phase sets. SENSOR_CONTROL24/family: six cells each A,B,AB,C; +.49step, stronger signed steps, short50/150/250ms pulses,long500/900/1500ms pulses,and slow drift. Keep dormant memory and unexcited actuators. Benign includes legal B excursions+.3/+.5/+.7C for100ms, noise, transients and target updates. No250ms memory or analytical provider. Zero historical config/profile/seed overlap audit. Cold-ambient startups use unchanged warm-engine initialization; no cold-soak claim.
ML provider binary target SENSOR_CONTROL active/just-delivered vs all other frames; labels offline only. Twelve sensor-only features. M0 linearC1; M1 RBFC1 gamma=scale; balanced class weights. At most eight uniformly sampled frames per class per run, TRAIN only. RBF provider admissible only <=256support vectors and >=1pp CAL gain over linear at the strict gate. Linear collapses to12weights for runtime. Standalone models use the identical feature set, global any-fault target, same TRAIN sampling, no support-vector restriction (not handicapped); select CAL run balanced accuracy, then sensitivity, then linear. This sensor-only standalone comparison is not the historical full-cross-layer SVM benchmark.
Platt logistic scaling of TRAIN-fitted provider margins on CAL only, no class weighting for calibration. Qualified CAL frames sampled uniformly16/run to limit within-run dependence. Global alpha grid .05/.10/.20; G0 physical qualified sensor strength>0; G1 same plus q>=.8; G2 q>=.8 for3 consecutive qualified frames. All gates additionally require startup complete,10consecutive fresh valid feature-history frames and no stale consumption. Unavailable=>vacuous evidence. A2 uses selected alpha with no anti-FP gate but the mandatory qualification. One anomaly simple-support mass alpha*q, remainder ignorance; no normal or origin mass. Dempster mathematics and global thresholds unchanged. Origin mass is entirely physical; existing localization thresholds/causal rules apply, so weak ML-led detections may remain UNKNOWN. Correlated feature-derived evidence is discounted, not asserted independent.
CAL selection first requires benign<=1%,wrong confident runs0,no startup regression,no critical-origin loss; then maximum detection, plant detection, lower alpha, simpler gate. If none qualifies, reject approach and evaluate conservative fixed linear/.05/G1 as a rejected diagnostic reference. Choose RBF only under the above complexity/gain conditions. No fault-subtype thresholds. Standalone matched-FPR threshold selected only from CAL benign run maxima to allow floor(.01*Nbenign)alarm runs; no validation threshold adjustment.
Freeze models,Platt mapping,alpha,gate,thresholds,features and source hashes before any validation. Run benign validation first, report its gate, then complete all registered fault comparisons even if gate fails; no post-result changes. A3 promotion requires >=1pp vsA0,benign<=1%,plant>=98%,zero wrong confident origins,100% first-detection accuracy including UNKNOWN as not correct,no timing/comm/effective-memory/actuator loss. No final unseen/commit/push. CIs and paired tests descriptive for deterministic grouped data. Preserve GUI and all prior evidence. Raw runtime packets/features temporary; keep <=8 representative compressed traces (planned0).
''');dump(O/'registration.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),utc=old.now(),manifest_sha256=sha(O/'campaign_manifest.csv'),protocol_sha256=sha(O/'protocol.md')));print('REGISTERED3900',flush=True)

def features(a):
 n=len(a);v=a[:,1];qual=a[:,9].astype(bool);consecutive=0;valid=np.zeros(n,bool)
 for i in range(n):
  consecutive=consecutive+1 if qual[i] else 0;valid[i]=consecutive>=10
 pad=np.pad(v,(9,0));win=np.lib.stride_tricks.sliding_window_view(pad,10)
 x=np.column_stack((v,win.mean(1),win.max(1),np.r_[0,np.diff(v)]/.1,a[:,2:9],valid))
 assert x.shape[1]==12
 return x,valid

def collect(part,benign=False):
 verify();tag=part+('_BENIGN' if benign else '');assert not (B/(tag+'_started')).exists();(B/(tag+'_started')).write_text(old.now());ss=[s for s in json.loads((B/'specs.json').read_text()) if s['partition']==part and (s['origin']=='NORMAL' if benign else s['origin']!='NORMAL' if part=='VALIDATION' else True)]
 if part=='VALIDATION':assert (O/'validation_lock.json').exists()
 if part=='VALIDATION' and not benign:assert (O/'benign_gate.json').exists()
 w=B/'work';w.mkdir(exist_ok=True);h.prepare_work(w,ss);exe=build(w)
 for k,name in [('TRIPLEX_LOG','triplex.csv'),('ML_PACKET','packet.bin'),('ML_FEATURES','features.csv')]:os.environ[k]=str(w/name)
 h.c.METHODS=['A0'];h.c.command=lambda s,w:t.command(s,w,exe);rows=[];(B/'tapes').mkdir(exist_ok=True)
 read0=h.c.read;cache={}
 def read(p):
  rr=read0(p)
  if Path(p).name=='observations.csv':cache['obs']=rr
  return rr
 h.c.read=read
 for i,s in enumerate(ss):
  row=h.c.execute(s,w,False)[0];a=np.loadtxt(w/'features.csv',delimiter=',');x,qualified=features(a)
  active=[z for z in cache['obs'] if h.prior.prior.active(s,int(z['time_ms']))];axis='pump_command' if s['model']=='pump_degraded' else 'fan_command';num=lambda z:float.fromhex(z) if '0x' in str(z) else float(z)
  row.update(initially_excited=int(s['origin']=='ACTUATOR' and bool(active) and num(active[0][axis])>0),actuator_excited=int(s['origin']=='ACTUATOR' and any(num(z[axis])>0 for z in active)));rows.append(row)
  active=np.array([s['origin']!='NORMAL' and (h.prior.prior.active(s,int(ms)) or h.prior.prior.active(s,max(0,int(ms)-99))) for ms in a[:,0]])
  np.savez_compressed(B/'tapes'/(s['run_id']+'.npz'),features=x,qualified=qualified,time=a[:,0].astype(int),values=a[:,12::2],available=a[:,13::2].astype(bool),alarm=a[:,10].astype(bool),origin=a[:,11].astype(int)>>1,sensor_target=active&(s['origin']=='SENSOR_CONTROL'),fault_target=active)
  (B/'tapes'/(s['run_id']+'.bin.gz')).write_bytes(gzip.compress((w/'packet.bin').read_bytes(),mtime=0))
  for name in ['packet.bin','features.csv','triplex.csv']:(w/name).unlink()
  if (i+1)%100==0:print(tag,i+1,'/',len(ss),flush=True)
 h.c.read=read0;dump(B/(tag+'_rows.json'),rows);verify();print('COMPLETE',tag,flush=True)

def dataset(part):
 for row in json.loads((B/(part+'_rows.json')).read_text()):
  yield row,np.load(B/'tapes'/(row['run_id']+'.npz'))
def margin(model,x):
 if model[1].kernel=='linear':return model[0].transform(x)@model[1].coef_[0]+model[1].intercept_[0]
 from scipy.spatial.distance import cdist
 z=model[0].transform(x);sv=model[1];out=[]
 # Exact RBF kernel, vectorized in bounded chunks; no model approximation.
 for start in range(0,len(z),128):
  kernel=np.exp(-sv._gamma*cdist(z[start:start+128],sv.support_vectors_,'sqeuclidean'))
  out.append(kernel@sv.dual_coef_[0]+sv.intercept_[0])
 return np.concatenate(out)
def fit():
 verify();record=[]
 for target,tag in [('sensor_target','provider'),('fault_target','standalone')]:
  xx=[];yy=[]
  for row,a in dataset('TRAIN'):
   idx=[];y=a[target]
   for c in [0,1]:
    pool=np.flatnonzero((y==c)&(a['qualified'] if tag=='provider' else np.ones(len(y),bool)))
    if len(pool):idx.extend(pool[np.unique(np.linspace(0,len(pool)-1,8,dtype=int))])
   if idx:xx.append(a['features'][idx]);yy.append(y[idx])
  x=np.concatenate(xx);y=np.concatenate(yy)
  for kind in ['linear','rbf']:
   model=make_pipeline(StandardScaler(),SVC(C=1,kernel=kind,gamma='scale',class_weight='balanced',cache_size=512));model.fit(x,y);(B/(tag+'_'+kind+'.pkl')).write_bytes(pickle.dumps(model,protocol=4));record.append(dict(target=tag,type=kind,training_frames=len(y),positive_frames=int(y.sum()),support_vectors=len(model[1].support_),compact=kind=='linear' or len(model[1].support_)<=256));print('FIT',record[-1],flush=True)
 dump(O/'model_training.json',record)
 # Persist margins for TRAIN/CAL once; no repeated expensive SVC evaluation.
 for part in ['TRAIN','CALIBRATION']:
  models={tag+'_'+kind:pickle.loads((B/(tag+'_'+kind+'.pkl')).read_bytes()) for tag in ['provider','standalone'] for kind in ['linear','rbf']}
  for i,(row,a) in enumerate(dataset(part)):
   np.savez_compressed(B/'tapes'/(row['run_id']+'_margins.npz'),**{k:margin(m,a['features']) for k,m in models.items()})
   if (i+1)%150==0:print('MARGINS',part,i+1,flush=True)
 print('FIT COMPLETE',flush=True)

if __name__=='__main__':
 if sys.argv[1]=='setup':setup()
 elif sys.argv[1]=='collect':collect(sys.argv[2],len(sys.argv)>3)
 elif sys.argv[1]=='fit':fit()
