#!/usr/bin/env python3
"""Final retained detector: one locked campaign, no search or reruns."""
import sys,json,hashlib,subprocess,csv,shutil,math
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'python')]
import run_clo_dsf_unseen_retained as prior
from virtual_ecu import clo_dsf_current as c
from virtual_ecu.clo_dsf_holdout import prepare_work,profile_identity
from virtual_ecu.clo_dsf_development import sha,ORIGINS
from virtual_ecu.clo_dsf_final_reporting import records,wilson
from virtual_ecu.clo_dsf_candidate2_development import aggregate
from virtual_ecu.clo_dsf_current_reporting import runtime_stats
B=Path('/tmp/clo-final-freeze');OUT=ROOT/'results/clo_dsf_final_unseen';write=prior.write
METHODS=['Revised CLO-DSF','Weighted Sum','Simple OR','Plain DS','v7.2 CLO-DSF','Hybrid','Timing Monitor']
SEED=982451653
PROTOCOL='''# FINAL unseen protocol: retained CURRENT only

Development is closed. No rejected provider/model is linked or loaded. Use the
recorded Git commit and its exact virtual_ecu_v7_3 binary; frozen cfg and Weighted
Sum choice6 unchanged. No algorithm selection, tuning or case replacement.

1500 cases,1200 faults/300 benign,240 each MEMORY/TIMING/COMMUNICATION/
SENSOR_CONTROL/ACTUATOR. Ten fixed families; each24 per origin/30benign.
The design is deterministic from master seed982451653 (explicit affine primary
and reference seed schedules, no random manifest selection). All parameters and
physical profiles are in campaign_manifest.csv. Every120s mission has100ms cadence.

Sensor per family:4primary slow,4reference slow,4common-mode slow,6weak steps,
6pulses. New drift times[14900,35300,58700,76900]ms and common-mode[21100,47900]ms;
new signed magnitudes, both sensor members,100/200ms or permanent weak steps,
200/700ms or persistent pulses. No common-mode exception from denominator.
Memory keeps valid stuck bits/polarities/bit-flip semantics and all three behaviors;
new activation phases and[500,900,1700,2700]ms finite windows; intermittent
on/off[600/1400,900/1600,1200/1800]ms. Effective/dormant categories are post-hoc
register-shadow consistency; dormant probes may detect a value-consistent cell.
Actuators include pump scales[.989,.971,.937,.873,.769,.619],fan stuck off, all
three behaviors,one quarter predefined cold low-load profiles. Actual initial
command at first active observation determines initially-excited/unexcited;
throughout-window excitation also reported separately. No-excitation is not an
exclusion. Timing/communication include finite[900,3100,7900,14900]ms disturbances
and valid transient deadline misses. Discrete fault types/bits can recur.
Benign per family six cold cases and24 varied profiles, normal command transitions,
legal calibration updates, bounded independent noise and brief disagreement.

New profiles differ from all recovered historical profiles. Historical registry
preserves32k+ profile identities/34k+ configuration identities from working files,
all Git manifest/profile blobs and surviving overwritten scratch manifests/audits,
including TRAIN/CALIBRATION/VALIDATION and prior holdouts. Audit disjoint complete
physical profiles, which prove zero exact configuration overlap despite older
inconsistent hash schemas. No claim covers irrecoverable unrecorded experiments.

Write/hash manifest,protocol,audit,scientific files,seed and commit before execution.
Run every case exactly once; checkpoint summaries before postprocessing. Abort and
record genuine collector/software errors separately, never rerun or replace cases.
Poor metrics are valid final results. No bulk traces; zero representative traces
selected. Temporary run files are deleted after scoring.

Evaluate CURRENT, frozen Fair Weighted Sum,Simple OR,Plain DS,v7.2 CLO-DSF,Hybrid
on identical observations. Timing Monitor only on TIMING. Counterfactual hidden
plant data is used only by unchanged offline propagation scoring, never inference.
Detection is any post-onset alarm, including after clearance; report pre-onset
alarms separately. Benign alarm is any alarm during the whole mission. Latency
is activation-to-first-post-onset alarm, median/P95 among detections. Run-level
precision is detected fault runs/(detected fault runs+benign alarm runs).
Plant manifestation threshold/semantics unchanged. First-detection accuracy among
localized detections and all-runtime accuracy among localized alarm samples are
separate; UNKNOWN/coverage include all alarms, including benign/pre-onset samples.
Wilson95 intervals are descriptive case-level intervals for grouped deterministic
cases, not independent population sampling guarantees. Exact two-sided McNemar is
the binomial discordance test; no superiority claim from marginal percentages alone.

Report overall detection,consequence-conditioned detection,benign alarms,
localization reliability and latent/unobservable categories separately. Do not
substitute one metric for another or make certification claims. Full pre-freeze
regression must pass before commit/push and this lock. Verify all scientific hashes
and GUI after execution. Results reference that exact pushed freeze commit.
'''
def design():
 specs=prior.design()
 for i,s in enumerate(specs):
  f=i//150;j=i%150;pp=json.loads(s['profile_json'])
  for p in pp:p['engine_load']*=.941;p['ambient_temp_c']+=1.173+i*.000031;p['vehicle_speed_kph']+=1.731+i*.000023
  s.update(run_id=f'final_locked_{i:04}',profile=f'final_locked_profile_{i:04}',group=f'final_locked_family_{f}',partition='FINAL_UNSEEN',seed=SEED+f*2417+j*103,reference_seed=SEED+10000019+f*1999+j*107,on_ms=[600,900,1200][f%3],off_ms=[1400,1600,1800][f%3])
  if s['origin']!='NORMAL':s['start_ms']=23100+(j%13)*500+f*200
  if s['behavior'] not in ['permanent','none'] and s['model']!='deadline_miss':s['duration_ms']=[900,3100,7900,14900][(j+f)%4]
  if s['origin']=='MEMORY':
   s['start_ms']=21700+(j%10)*100+f*1100
   if s['behavior']!='permanent':s['duration_ms']=[500,900,1700,2700][(j+f)%4]
  if s['origin']=='ACTUATOR' and s['model']=='pump_degraded':s['magnitude']=[.989,.971,.937,.873,.769,.619][(j-96)//3]
  if s['origin']=='SENSOR_CONTROL':
   k=j-72;s['magnitude']+=(.043+f*.001) if s['magnitude']>0 else -(.043+f*.001)
   if s['model']=='sensor_bias_ramp':s['sensor_ramp_rise_ms']=[21100,47900][k%2] if s['sensor_chain']=='common_mode' else [14900,35300,58700,76900][(k+f)%4]
   elif s['model']=='sensor_bias':s['duration_ms']=[100,200,0][(k-12)%3]
   else:s['duration_ms']=[200,700,0][(k-18)%3]
  if s['origin']=='NORMAL' and j>=144:
   for p in pp:p.update(engine_load=.088+j*.000001,ambient_temp_c=9.713+f*.137,vehicle_speed_kph=75.117+j*.011)
   s['workload']='benign_cold' # preserve explicit legal updates/noise where present
  s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=profile_identity(pp);s.pop('configuration_sha256',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()
 assert len(specs)==1500 and len({s['profile_semantic_sha256'] for s in specs})==1500
 assert all(sum(s['origin']==o for s in specs)==240 for o in ORIGINS)
 return specs

def verify():
 lock=json.loads((OUT/'hashes.json').read_text());assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==lock['commit']
 for p,v in lock['files'].items():assert sha(ROOT/p)==v,'Frozen hash mismatch: '+p
 assert sha(ROOT/'presets/gui_session_state.json')==lock['local_gui_sha256']
 return lock

def lock():
 assert not (B/'holdout_started').exists() and not (B/'holdout_locked').exists()
 dirty=subprocess.check_output(['git','status','--porcelain'],text=True).splitlines();assert all(x[3:]=='presets/gui_session_state.json' for x in dirty),dirty
 specs=design();registry=ROOT/'results/clo_dsf_current/historical_identity_registry.csv';old=records(registry)
 profiles={r['profile_semantic_sha256'] for r in old if r['profile_semantic_sha256']};configs={r['configuration_sha256'] for r in old if r['configuration_sha256']}
 assert not profiles&{s['profile_semantic_sha256'] for s in specs};assert not configs&{s['configuration_sha256'] for s in specs}
 # The immediate replaced manifest must be read and included explicitly too.
 previous=records(OUT/'campaign_manifest.csv');prior_profiles={r['profile_semantic_sha256'] for r in previous};assert not prior_profiles&{s['profile_semantic_sha256'] for s in specs}
 assert prior_profiles<=profiles
 w=B/'holdout_work';w.mkdir();prepare_work(w,specs)
 objects=[str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o'];check=w/'check';subprocess.run(['gcc','-std=c11','-Iinclude','tests/holdout_configuration_check.c',*objects,'-o',str(check)],check=True)
 for s in specs:
  cmd=prior.command(s,w);p=subprocess.run([str(check),*cmd[2:]],capture_output=True,text=True);assert p.returncode==0,(s['run_id'],p.stderr)
  s['command_json']=json.dumps([v.replace(str(w),'$WORK').replace(str(ROOT),'$ROOT') for v in cmd])
 audit=[dict(source=str(registry.relative_to(ROOT)),sha256=sha(registry),historical_profiles=len(profiles),historical_configurations=len(configs),profile_overlap=0,exact_overlap=0),dict(source='immediate previous final campaign',sha256=sha(OUT/'campaign_manifest.csv'),historical_profiles=len(prior_profiles),historical_configurations=len(previous),profile_overlap=0,exact_overlap=0)]
 shutil.rmtree(OUT);OUT.mkdir();write(OUT/'campaign_manifest.csv',specs);write(OUT/'overlap_audit.csv',audit);(OUT/'protocol.md').write_text(PROTOCOL)
 commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();tracked=subprocess.check_output(['git','ls-files'],text=True).splitlines()
 scientific={p:sha(ROOT/p) for p in tracked if (ROOT/p).is_file() and (p.startswith(('src/','include/','python/','scripts/','tests/')) or p.endswith(('.mk','.cfg')) or p in ['Makefile','virtual_ecu','virtual_ecu_v7_3'])}
 for p in [OUT/'campaign_manifest.csv',OUT/'overlap_audit.csv',OUT/'protocol.md']:scientific[str(p.relative_to(ROOT))]=sha(p)
 record=dict(commit=commit,seed=SEED,locked_utc=datetime.now(timezone.utc).isoformat(),manifest_sha256=sha(OUT/'campaign_manifest.csv'),local_gui_sha256=sha(ROOT/'presets/gui_session_state.json'),files=scientific)
 (OUT/'hashes.json').write_text(json.dumps(record,indent=2));(OUT/'validation_record.md').write_text('# Final validation record\n\nExact freeze commit '+commit+'\nManifest '+record['manifest_sha256']+'\nSeed '+str(SEED)+'\nHistorical overlap0. Protocol locked before outcomes.\n\nPre-freeze regression:\n```json\n'+(B/'regression.json').read_text()+'\n```\n')
 verify();(B/'holdout_locked').write_text('locked');print('LOCKED',commit,record['manifest_sha256'],flush=True)

def run():
 assert (B/'holdout_locked').exists() and not (B/'holdout_started').exists();verify();(B/'holdout_started').write_text(datetime.now(timezone.utc).isoformat())
 specs=records(OUT/'campaign_manifest.csv');w=B/'holdout_work';c.OUT=OUT;c.METHODS=METHODS;c.command=prior.command;old=c.read;cache={}
 def read(p):
  rr=old(p)
  if Path(p).name in ['trace.csv','observations.csv']:cache[Path(p).name]=rr
  return rr
 c.read=read;rows=[]
 with (B/'holdout_checkpoint.jsonl').open('w') as checkpoint:
  for i,s in enumerate(specs):
   if i%50==0:verify()
   try:
    rr=c.execute(s,w,False);checkpoint.write(json.dumps(rr)+'\n');checkpoint.flush()
    obs=[o for o in cache['observations.csv'] if prior.active(s,int(o['time_ms']))];tr=[o for o in cache['trace.csv'] if prior.active(s,int(o['time_ms']))]
    def number(v):return float.fromhex(v) if '0x' in str(v).lower() else float(v)
    axis='pump_command' if s['model']=='pump_degraded' else 'fan_command'
    excited=int(s['origin']=='ACTUATOR' and any(abs(number(o[axis]))>1e-8 for o in obs))
    initial=int(s['origin']=='ACTUATOR' and bool(obs) and abs(number(obs[0][axis]))>1e-8)
    checks=sum(int(t['memory_check_valid']) and int(t['memory_check_ms'])==int(t['time_ms']) for t in tr)
    for r in rr:
     if r['method']=='Timing Monitor' and r['origin']!='TIMING':continue
     r.pop('command_json',None);r.update(actuator_excited=excited,initially_excited=initial,active_probe_checks=checks);rows.append(r)
   except Exception as e:
    (OUT/'execution_failure.json').write_text(json.dumps(dict(run=s['run_id'],completed=i,error=repr(e),rerun=False)));raise
   if (i+1)%50==0:print('Completed',i+1,'/1500',flush=True)
 verify();write(OUT/'case_summary.csv',rows);(B/'holdout_complete').write_text('1500 once');report(rows);shutil.rmtree(w)

def report(rows=None):
 if rows is None:rows=records(OUT/'case_summary.csv')
 verify();summary=[];local=[];sub=[]
 filters={'effective_memory':lambda r:r['origin']=='MEMORY' and r['effective_memory_corruption'],'dormant_memory':lambda r:r['origin']=='MEMORY' and r['model']=='stuck_bit' and not r['effective_memory_corruption'],'independent_slow_drift':lambda r:r['model']=='sensor_bias_ramp' and r['sensor_chain'] in ['primary','reference'],'common_mode':lambda r:r['sensor_chain']=='common_mode','weak_steps':lambda r:r['model']=='sensor_bias','pulses':lambda r:r['model']=='sensor_interface_intermittent','excited_actuator':lambda r:r['origin']=='ACTUATOR' and r['initially_excited'],'initially_unexcited_actuator':lambda r:r['origin']=='ACTUATOR' and not r['initially_excited'],'throughout_unexcited_actuator':lambda r:r['origin']=='ACTUATOR' and not r['actuator_excited'],'cold_benign':lambda r:r['origin']=='NORMAL' and r['workload']=='benign_cold'}
 for method in METHODS:
  rr=[r for r in rows if r['method']==method]
  for group in ['ALL',*ORIGINS]:
   ss=[r for r in rr if group=='ALL' or r['origin']==group]
   if not ss:continue
   a=aggregate(ss);lo,hi=wilson(a['detected'],a['faulty_runs']);summary.append(dict(method=method,group=group,**a,wilson95_low=lo,wilson95_high=hi));local.append(dict(method=method,group=group,**runtime_stats(ss),first_correct=a['correct_localizations'],first_localized=a['localized'],first_unknown=a['unknown'],first_detected=a['detected']))
  for group,fn in filters.items():
   ss=[r for r in rr if fn(r)]
   if ss:sub.append(dict(method=method,group=group,**aggregate(ss)))
 write(OUT/'detection_summary.csv',summary);write(OUT/'baseline_comparison.csv',[r for r in summary if r['group']=='ALL']);write(OUT/'subgroup_summary.csv',sub);write(OUT/'localization_summary.csv',local)
 current={r['run_id']:r for r in rows if r['method']=='Revised CLO-DSF' and r['injected']};ws={r['run_id']:r for r in rows if r['method']=='Weighted Sum' and r['injected']};pair=dict(both=0,clo_only=0,weighted_only=0,neither=0)
 for k,a in current.items():
  b=ws[k];key='both' if a['detected'] and b['detected'] else 'clo_only' if a['detected'] else 'weighted_only' if b['detected'] else 'neither';pair[key]+=1
 n=pair['clo_only']+pair['weighted_only'];k=min(pair['clo_only'],pair['weighted_only']);pair['mcnemar_exact_p']=min(1,2*sum(math.comb(n,j) for j in range(k+1))/2**n) if n else 1.;write(OUT/'paired_comparison.csv',[pair])
 a=next(r for r in summary if r['method']=='Revised CLO-DSF' and r['group']=='ALL');rt=next(r for r in local if r['method']=='Revised CLO-DSF' and r['group']=='ALL');safety=dict(plant_faults=a['plant_manifestation_runs'],plant_detected=a['plant_manifestation_runs']-a['silent_plant'],pre=a['pre_plant_alarms'],same=a['same_plant_alarms'],post=a['post_plant_alarms'])
 (OUT/'findings.md').write_text('# Final unseen retained CLO-DSF\n\nNo tuning, replacement, rerun or algorithm change. Overall and consequence-conditioned denominators remain separate; latent faults are not excluded.\n\n'+json.dumps(dict(overall=a,localization=rt,safety=safety,paired=pair),indent=2)+'\n\nSee subgroup and baseline CSVs. All timings are simulated. Case-level Wilson intervals are descriptive for a grouped deterministic campaign. No certification or out-of-domain guarantees.\n')
 with (OUT/'validation_record.md').open('a') as f:f.write('\n1500/1500 executions completed exactly once; all scientific/config/manifest/GUI hashes unchanged after execution. No rejected extension loaded. Full regression passed before freeze. No post-outcome tuning.\n')
 print('FINAL COMPLETE',a['detected'],'/1200',flush=True)
if __name__=='__main__':{'lock':lock,'run':run,'report':report}[sys.argv[1]]()
