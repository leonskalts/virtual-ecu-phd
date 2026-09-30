#!/usr/bin/env python3
"""One immutable primary+secondary evaluation of frozen classical Triplex."""
import sys,json,hashlib,csv,io,tarfile,subprocess,collections,shutil
from pathlib import Path
from datetime import datetime,timezone
import run_clo_dsf_triplex as t
ROOT=t.ROOT;OUT=ROOT/'results/clo_dsf_triplex_final_unseen';B=Path('/tmp/clo-triplex-final-unseen')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
PROTOCOL='''# Final Triplex unseen protocol
Development is closed. Exactly one primary1500 (1200fault/300benign) and separate secondary300 fault cohort. Primary240 per MEMORY/TIMING/COMMUNICATION/SENSOR_CONTROL/ACTUATOR; A/B/AB80each, ramp/step/pulse80each. Ten deterministic operating families, fresh profiles/seeds/epochs. Memory uses existing effective/dormant bit/polarity cells, varied phase and valid temporal behaviors. All18pump+6fan templates per family retained, including cold initially-unexcited contexts. No subgroup or parameter choice depends on these outcomes. Benign includes legal target updates, startup, independent measurement variation and dynamic load/speed/ambient profiles.

Secondary ten families: each C15 (3each bias,slow,step,pulse,acquisition),ABC5,AC5,BC5. C-only bias denotes an offset present from startup; steps begin later. Timestamp-freeze uses existing acquisition-freeze semantics; no novel fault/provider. Never mix secondary into primary headline.

B0 CURRENT and B1 TRIPLEX consume the SAME physical runs. Exact validated Triplex build/hook with classical DS only; no alternative fusion,latch,telemetry,excitation or hidden truth in inference. Baseline full-state equality to historical classical source9f993587 is asserted every sample. Fault labels are used solely by the simulator injection boundary and offline accounting. Independent C model unchanged. No parameter calibration.

Before running either cohort: verify frozen HEAD/scientific hashes, register both manifests,seeds and subgroup counts, audit working-tree/Git historical and archived campaign/profile identities. Lock manifests and scripts. Execute each case once; stream and delete raw files, retain compact sufficient statistics. No outcome inspection before each full cohort completes. No reruns for poor results; only documented collector/execution failure may be handled separately.

Metrics: post-onset rising-edge detection, first-detection and all-alarm-sample localization, existing counterfactual plant propagation, latency among detected faults, paired counts and exact two-sided McNemar, Wilson95. Groups are deterministic, not a probability sample; CIs/tests descriptive. UNKNOWN is not a wrong confident origin. Report active-diagnostic detection of dormant stored-value states separately. Idle pump-performance degradation is unobservable in the modeled architecture until actuator excitation occurs. No healthy evidence invented for unavailable observations.

No source/threshold/config edits after lock; no post-outcome tuning. Report failures honestly. Primary >90%,plant>=95%,benign<=1%,zero/near-zero wrong origins are questions, not rerun criteria. Final result files are not committed automatically.
'''
def design():
 templates=t.prior.design();out=[]
 for i in range(1800):
  secondary=i>=1500;z=i-1500 if secondary else i;f=z//(30 if secondary else 150);j=z%(30 if secondary else 150)
  s=dict(templates[f*150+(72+j%24 if secondary else j)])
  s.update(run_id=f'triplex_final_{i:04}',profile=f'triplex_final_profile_{i:04}',group=f'final_family_{f}',partition='SECONDARY' if secondary else 'PRIMARY',seed=1237000001+i*211,reference_seed=1291000003+i*223,c_seed=1327000007+i*227,domain='NONE',kind='none',subgroup='base',c_offset=(f%5-2)*.0417,c_gain=(f%3-1)*.00047,c_noise=.0193+f*.00061,c_quantum=[.019,.023,.027][f%3],c_adc_gain=(f%4-1.5)*.00019,c_phase_ms=17+f*7,c_lag_ms=0)
  load=[.39,.48,.57,.66,.75,.84,.93,.43,.63,.83][f]
  pp=[dict(start_ms=a,end_ms=b,engine_load=(load+i*.00000017)*fac,ambient_temp_c=13.417+f*1.913+i*.000019+(1.37 if a>=70300 else 0),vehicle_speed_kph=(24.173+f*6.713+i*.000023)*fac,external_airflow_factor=.057 if a>=46300 else 0,road_slope_percent=0) for a,b,fac in [(0,17900,.74),(17900,46300,.95),(46300,70300,.81),(70300,96700,1),(96700,120000,.85)]]
  if not secondary and ((s['origin']=='ACTUATOR' and (j-96)%4==0) or (s['origin']=='NORMAL' and j>=144)):
   for p in pp:p.update(engine_load=.0813+f*.00027+i*.00000013,ambient_temp_c=9.137+f*.163+i*.000017,vehicle_speed_kph=72.319+f*.217+i*.000021)
  if s['origin']!='NORMAL':s['start_ms']=23900+(j%13)*500+f*100
  s['on_ms']=[700,1000,1300][f%3];s['off_ms']=[1300,1700,1900][f%3]
  if s['behavior'] not in ['permanent','none'] and s['model']!='deadline_miss':s['duration_ms']=[1100,3300,8100,15100][(j+f)%4]
  if s['origin']=='MEMORY':
   s['start_ms']=22300+(j%10)*100+f*1300
   if s['behavior']!='permanent':s['duration_ms']=[300,700,1500,2900][(j+f)%4]
  if s['origin']=='ACTUATOR' and s['model']=='pump_degraded':s['magnitude']=[.991,.967,.931,.861,.753,.607][(j-96)//3]
  if secondary or s['origin']=='SENSOR_CONTROL':
   if secondary:
    if j<15:domain='C';kind=['bias','ramp','step','pulse','freeze'][j//3];cell=j%3;s['subgroup']='C_'+kind
    else:domain=['ABC','AC','BC'][(j-15)//5];cell=(j-15)%5;kind=['ramp','ramp','step','pulse','pulse'][cell];s['subgroup']=domain
   else:
    k=j-72;domain=['A','B','AB'][k//8];cell=k%8;kind=['ramp','step','pulse'][(cell+f+k//8)%3];s['subgroup']=domain+'_'+kind
   mag=(-1 if (cell+f)%2 else 1)*(2.63+f*.017 if kind=='ramp' else 1.73+f*.013 if kind=='bias' else [.53,.71,.93,1.11][(cell+f)%4])
   duration=[100,300,700,1300][(cell+f)%4] if kind=='pulse' else [200,900,1700][cell%3] if kind=='freeze' else 0
   physical_kind='step' if kind=='bias' else kind
   s.update(origin='SENSOR_CONTROL',domain=domain,kind=physical_kind,sensor_chain=domain,model={'ramp':'sensor_bias_ramp','step':'sensor_bias','pulse':'sensor_interface_intermittent','freeze':'sensor_acquisition_freeze'}[physical_kind],behavior='transient' if duration else 'permanent',magnitude=mag,duration_ms=duration,sensor_ramp_rise_ms=[20300,39700,63100,83900][(cell+f)%4] if kind=='ramp' else 0,start_ms=0 if kind=='bias' else 23300+f*300+cell*400,initially_latent_stuck=0,target_updates_json='[]',workload='triplex_fault')
  s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=t.h.profile_identity(pp);s.pop('configuration_sha256',None);s.pop('command_json',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();out.append(s)
 assert len(out)==1800 and len({s['profile_semantic_sha256'] for s in out})==1800
 assert all(sum(s['partition']=='PRIMARY' and s['origin']==o for s in out)==240 for o in t.h.prior.ORIGINS)
 return out

def historical_audit(ss):
 keys={s['profile_semantic_sha256'] for s in ss};ids={s['configuration_sha256'] for s in ss};seeds={str(s['seed']) for s in ss};seen=set();audit=[]
 def consume(label,data):
  digest=hashlib.sha256(data).hexdigest()
  if digest in seen:return
  seen.add(digest)
  try:rows=list(csv.DictReader(io.StringIO(data.decode())))
  except (UnicodeError,csv.Error):return
  if not rows:return
  profiles=set();configs=set();prior_seeds=set()
  if {'start_ms','end_ms','vehicle_speed_kph','engine_load','ambient_temp_c'}<=rows[0].keys():profiles.add(t.h.profile_identity([{k:r.get(k) or 0 for k in ['start_ms','end_ms','vehicle_speed_kph','engine_load','ambient_temp_c','external_airflow_factor','road_slope_percent']} for r in rows]))
  for r in rows:
   if r.get('profile_json'):profiles.add(t.h.profile_identity(json.loads(r['profile_json'])))
   elif r.get('profile_semantic_sha256'):profiles.add(r['profile_semantic_sha256'])
   if r.get('configuration_sha256'):configs.add(r['configuration_sha256'])
   if r.get('seed'):prior_seeds.add(r['seed'])
  if profiles or configs or prior_seeds:
   assert not keys&profiles,label;assert not ids&configs,label;assert not seeds&prior_seeds,label
   audit.append(dict(source=label,sha256=digest,rows=len(rows),profile_identities=len(profiles),configuration_identities=len(configs),seeds=len(prior_seeds),profile_overlap=0,configuration_overlap=0,seed_overlap=0))
 def archive(label,data):
  with tarfile.open(fileobj=io.BytesIO(data),mode='r:*') as tf:
   for member in tf.getmembers():
    if not member.isfile():continue
    if member.name.endswith('.csv'):consume(label+'!'+member.name,tf.extractfile(member).read())
    elif member.name.endswith(('.tar.gz','.tgz')):archive(label+'!'+member.name,tf.extractfile(member).read())
 for root in [ROOT/'results',ROOT/'presets']:
  for p in root.rglob('*.csv'):
   if OUT in p.parents:continue
   with p.open() as f:header=f.readline()
   if any(x in header for x in ['profile_json','profile_semantic_sha256','configuration_sha256']) or '/profiles/' in str(p) or 'manifest' in p.name or 'registry' in p.name:consume(str(p.relative_to(ROOT)),p.read_bytes())
 for p in (ROOT/'results').glob('*.tar.gz'):archive(str(p.relative_to(ROOT)),p.read_bytes())
 for line in subprocess.check_output(['git','rev-list','--objects','--all'],text=True).splitlines():
  parts=line.split(' ',1)
  if len(parts)!=2:continue
  blob,name=parts
  if name.endswith('.csv') and any(x in name for x in ['manifest','registry','split_','/profiles/']):consume('git:'+blob+':'+name,subprocess.check_output(['git','cat-file','blob',blob]))
 for p in Path('/tmp').glob('clo*/**/*manifest.csv'):
  if B in p.parents:continue
  consume(str(p),p.read_bytes())
 t.write(OUT/'historical_overlap_audit.csv',audit)
 return len(audit)

def verify():
 lock=json.loads((OUT/'hashes.json').read_text());assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==lock['commit']
 assert all(sha(p)==v for p,v in lock['scientific_files'].items())
 assert sha(OUT/'primary_manifest.csv')==lock['primary_manifest_sha256'];assert sha(OUT/'secondary_manifest.csv')==lock['secondary_manifest_sha256']
 assert sha(OUT/'protocol.md')==lock['protocol_sha256']
 assert sha(B/'specs.json')==lock['specs_sha256']
 return lock

def setup():
 assert not OUT.exists() and not B.exists(),'Never overwrite or regenerate'
 dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],text=True).splitlines();assert all(x[3:]=='presets/gui_session_state.json' for x in dirty),dirty
 commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert subprocess.check_output(['git','rev-parse','@{upstream}'],text=True).strip()==commit
 B.mkdir();OUT.mkdir();ss=design();historical_sources=historical_audit(ss)
 t.write(OUT/'primary_manifest.csv',[s for s in ss if s['partition']=='PRIMARY']);t.write(OUT/'secondary_manifest.csv',[s for s in ss if s['partition']=='SECONDARY']);(B/'specs.json').write_text(json.dumps(ss));(OUT/'protocol.md').write_text(PROTOCOL)
 paths=[p for root in ['src','include','scripts','python'] for p in Path(root).rglob('*') if p.is_file() and p.suffix in ['.c','.h','.py']]+[t.h.c.CONFIG,Path('presets/gui_session_state.json')]
 lock=dict(commit=commit,locked_utc=datetime.now(timezone.utc).isoformat(),historical_sources=historical_sources,historical_overlap=0,primary_manifest_sha256=sha(OUT/'primary_manifest.csv'),secondary_manifest_sha256=sha(OUT/'secondary_manifest.csv'),protocol_sha256=sha(OUT/'protocol.md'),specs_sha256=sha(B/'specs.json'),seed_formula='i=0..1799; scenario1237000001+211i; B1291000003+223i; C1327000007+227i',counts={part:dict(collections.Counter(s['origin'] for s in ss if s['partition']==part)) for part in ['PRIMARY','SECONDARY']},subgroup_counts={part:dict(collections.Counter(s['subgroup'] for s in ss if s['partition']==part)) for part in ['PRIMARY','SECONDARY']},scientific_files={str(p):sha(p) for p in paths})
 (OUT/'hashes.json').write_text(json.dumps(lock,indent=2));print('LOCKED',commit,historical_sources,'historical sources; overlap0',flush=True)

def run(part):
 assert part in ['PRIMARY','SECONDARY'];verify()
 if part=='SECONDARY':assert (B/'PRIMARY_complete').exists()
 t.B=B;t.run(part);verify();shutil.rmtree(B/'work');print(part,'COMPLETE; hashes unchanged',flush=True)
if __name__=='__main__':
 if sys.argv[1]=='setup':setup()
 elif sys.argv[1]=='run':run(sys.argv[2])
 elif sys.argv[1]=='verify':verify();print('Verified')
