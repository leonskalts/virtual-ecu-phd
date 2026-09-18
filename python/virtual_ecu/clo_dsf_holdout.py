"""One-shot unseen holdout orchestration; never modifies frozen inference."""
import csv,hashlib,itertools,json,math,shutil,subprocess,tempfile
from datetime import datetime,timezone
from pathlib import Path
from .clo_dsf_development import ROOT,ORIGINS,write_csv,sha
from .clo_dsf_candidate2_development import command as legacy_command,derived,aggregate,NONLOCAL
from .clo_dsf_final_reporting import records,wilson
from .cross_layer_safety import summarize_rows,read_rows
OUT=ROOT/'results/cross_layer_safety_v8_final_holdout'
FROZEN=ROOT/'results/cross_layer_safety_v7_3_dev'
METHODS=['Simple OR','Weighted Sum','Plain DS','v7.2 CLO-DSF','Revised CLO-DSF','Hybrid','Timing Monitor']
PROFILES=[dict(name='h8_cruise',load=.44,speed=62,ambient=21),dict(name='h8_urban',load=.63,speed=24,ambient=34),dict(name='h8_slow',load=.79,speed=9,ambient=38),dict(name='h8_fast',load=.93,speed=108,ambient=29),dict(name='h8_hot',load=.985,speed=6,ambient=41)]
MODELS={'MEMORY':{'bit_flip':[0,4],'stuck_bit':[0,4]},'TIMING':{'deadline_miss':[0,0],'task_delay':[800,1300]},'COMMUNICATION':{'delayed_update':[300,600],'dropped_update':[3,8],'replayed_sample':[600,1700]},'SENSOR_CONTROL':{'sensor_bias':[-3.5,6.5],'sensor_interface_intermittent':[3.5,7.5]},'ACTUATOR':{'pump_degraded':[.965,.81],'fan_stuck_off':[0,0]}}
BEHAVIORS=['transient','intermittent','permanent']
SEEDS=[101,137,179,223]

def read(path):
 with Path(path).open(newline='') as f:return list(csv.DictReader(f))
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def verify_frozen():
 p=subprocess.run(['python3','scripts/freeze_clo_dsf_revised.py','--verify'],cwd=ROOT,capture_output=True,text=True)
 if p.returncode:raise RuntimeError('STOP: frozen v7.3 identity mismatch\n'+p.stdout+p.stderr)
 return p.stdout.strip()
def profile_rows(p):
 return [dict(start_ms=a,end_ms=b,vehicle_speed_kph=max(0,p['speed']*f),engine_load=max(.05,min(1,p['load']*f)),ambient_temp_c=p['ambient'],external_airflow_factor=0,road_slope_percent=0) for a,b,f in [(0,21300,.66),(21300,57900,1),(57900,92300,.82),(92300,120000,.94)]]
def profile_identity(rows):
 return digest([{k:float(v) for k,v in sorted(row.items())} for row in rows])
def physical(s,profile_hash):
 return digest([s['model'],s['behavior'],profile_hash,int(s['start_ms']),None if s['behavior']=='permanent' else int(s['duration_ms']),None if s['model'] in ['baseline','deadline_miss','fan_stuck_off'] else float(s['magnitude'])])
def design():
 specs=[]
 for origin,models in MODELS.items():
  for model,magnitudes in models.items():
   for bi,behavior in enumerate(BEHAVIORS):
    cell=[]
    for severity,magnitude in enumerate(magnitudes):
     for pi,p in enumerate(PROFILES):
      for oi,onset in enumerate([18700,43900,81700,96700]):
       offset=severity*1700 if (model=='deadline_miss' and behavior in ['transient','permanent']) or (model=='fan_stuck_off' and behavior=='permanent') else 0
       s=dict(origin=origin,model=model,behavior=behavior,magnitude=magnitude,severity=severity,profile=p['name'],start_ms=onset+offset,duration_ms=100 if model=='deadline_miss' and behavior=='transient' else [1400,7300][severity],group=f'{origin}/{model}/{behavior}',seed=SEEDS[(pi+oi+severity)%4],stuck_polarity=(pi+oi+severity)%2,simulation_duration_ms=120000,profile_json=json.dumps(profile_rows(p),sort_keys=True,separators=(',',':')))
       cell.append(s)
    if origin=='COMMUNICATION':
     # Predetermined stratification: 80 per model, 27/27/26 per behavior;
     # no outcome-dependent inclusion or favorable severity subset.
     cell=sorted(cell,key=lambda s:digest(['v8-holdout-stratum',s]))[:[27,27,26][bi]]
    specs+=cell
 for p in PROFILES:
  for i,(lo,so,ao) in enumerate(itertools.product([-.09,-.03,.01,.045],[-4,-1,0,2,5],[-2,0,3])):
   name=f"benign_{p['name']}_{i:02}";values=dict(load=p['load']+lo,speed=p['speed']+so,ambient=p['ambient']+ao)
   specs.append(dict(origin='NORMAL',model='baseline',behavior='none',magnitude=0,severity=0,profile=name,start_ms=120100,duration_ms=0,group=f"NORMAL/{p['name']}",seed=SEEDS[i%4],stuck_polarity=0,simulation_duration_ms=120000,profile_json=json.dumps(profile_rows(values),sort_keys=True,separators=(',',':'))))
 for i,s in enumerate(specs):
  s.update(run_id=f'holdout_{i:04}',partition='final-unseen-holdout',intermittent_on_ms=700,intermittent_off_ms=1100,legacy_second_event_gap_ms=1100,drop_every_n_updates=11)
  s['profile_semantic_sha256']=profile_identity(json.loads(s['profile_json']));s['configuration_sha256']=physical(s,s['profile_semantic_sha256'])
 assert len(specs)==1500 and all(sum(s['origin']==o for s in specs)==240 for o in ORIGINS)
 return specs

def overlap(specs):
 keys={s['configuration_sha256'] for s in specs};assert len(keys)==len(specs)
 audit=[dict(compared_to='Within final holdout',configurations=len(specs),exact_overlap=len(specs)-len(keys))]
 for folder,manifest in [('cross_layer_safety_v7_dev','development_split_manifest.csv'),('cross_layer_safety_v7_1_dev','development_split_manifest.csv'),('cross_layer_safety_v7_2_confirmation','confirmation_configuration_manifest.csv'),('cross_layer_safety_v7_2_confirmation/validation/invalid_attempt_01','confirmation_configuration_manifest.csv'),('cross_layer_safety_v7_3_dev','development_split_manifest.csv')]:
  old=ROOT/'results'/folder;prior=read(old/manifest);profiles={};oldkeys=set()
  for s in prior:
   if s['profile'] not in profiles:profiles[s['profile']]=profile_identity(read(old/'profiles'/f"{s['profile']}.csv"))
   oldkeys.add(physical(s,profiles[s['profile']]))
  n=len(keys&oldkeys);assert n==0,folder
  audit.append(dict(compared_to=folder,configurations=len(oldkeys),exact_overlap=n))
 write_csv(OUT/'configuration_overlap_audit.csv',audit)

PROFILE_COLUMNS=['start_ms','end_ms','vehicle_speed_kph','engine_load','ambient_temp_c','external_airflow_factor','road_slope_percent']
def prepare_work(work,specs):
 for folder in ['profiles','raw']:(work/folder).mkdir(exist_ok=True)
 for s in specs:write_csv(work/'profiles'/f"{s['profile']}.csv",[{k:row[k] for k in PROFILE_COLUMNS} for row in json.loads(s['profile_json'])])
def command(s,work):
 cmd=legacy_command(s,work,'validation',FROZEN/'revised.cfg',6);cmd=cmd[:cmd.index('--c2-config')];cmd[0]=str(ROOT/'virtual_ecu_v7_3')
 for key,value in {'--fault-seed':s['seed'],'--seed':s['seed'],'--intermittent-on-ms':700,'--intermittent-off-ms':1100,'--drop-every-n-updates':11,'--stuck-polarity':s['stuck_polarity']}.items():
  if key in cmd:cmd[cmd.index(key)+1]=str(value)
 if 'custom_multi' in cmd:
  i=cmd.index('custom_multi');cmd[i+8]=str(s['start_ms']+s['duration_ms']+1100)
 return cmd+['--revised-config',str(FROZEN/'revised.cfg'),'--revised-c2-config',str(ROOT/'results/cross_layer_safety_v7_1_dev/selected_config.cfg'),'--revised-comparison','--revised-evaluation-start',str(s['start_ms']),'--revised-weighted-choice','6','--revised-evidence',str(work/'trace.csv'),'--revised-observations',str(work/'observations.csv'),'--revised-metrics',str(work/'metrics.csv')]

def validate(specs,work):
 exe=work/'config_check';objects=[str(p) for p in sorted((ROOT/'src').glob('*.o')) if p.name!='main.o']
 subprocess.run(['gcc','-std=c11','-Iinclude','tests/holdout_configuration_check.c',*objects,'-o',str(exe)],cwd=ROOT,check=True)
 for s in specs:
  cmd=command(s,work);p=subprocess.run([str(exe),*cmd[2:]],capture_output=True,text=True)
  if p.returncode:raise ValueError(s['run_id']+': '+p.stderr)
  assert s['start_ms']%100==0 and s['duration_ms']%100==0
  if 'custom_multi' in cmd:assert s['start_ms']+2*s['duration_ms']+1100<=120000

def register(specs,verification):
 sources=[Path(__file__),ROOT/'scripts/run_clo_dsf_final_holdout.py',ROOT/'python/virtual_ecu/clo_dsf_holdout_reporting.py',ROOT/'scripts/validate_clo_dsf_final_holdout.py',ROOT/'tests/test_clo_dsf_holdout.py',ROOT/'tests/holdout_configuration_check.c']
 identities={str(p.relative_to(ROOT)):sha(p) for p in sources}
 identities.update({str((OUT/name).relative_to(ROOT)):sha(OUT/name) for name in ['final_holdout_manifest.csv','configuration_overlap_audit.csv']})
 stamp=datetime.now(timezone.utc).isoformat()
 protocol=f'''# Final unseen CLO-DSF holdout — registered before outcomes

Registered UTC: {stamp}. Baseline: {(Path('/tmp/clo-v8-audit/baseline.txt')).read_text().strip()}.
{verification}
Frozen v7.3 manifest SHA256: {sha(FROZEN/'clo_dsf_revised_hashes.json')}.
No detector, baseline, fault semantics or scientific parameter may change.
No search, recalibration, early stopping, outcome-dependent sampling or retuning.
All 1,500 valid unique cases must run once; errors stop the campaign and remain
visible. A registered campaign refuses overwrite or silent restart.

## Design

1,200 faults (240 each MEMORY, TIMING, COMMUNICATION, SENSOR_CONTROL, ACTUATOR)
and 300 benign cases. Five new piecewise driving profiles; four onset bases
18700/43900/81700/96700 ms; ordinary durations 1400/7300 ms; 120000 ms runs.
Profile segments 0/21300/57900/92300/120000 use factors .66/1/.82/.94.
Seeds 101/137/179/223; deterministic injectors do not create independent random
replications. Every exact profile, magnitude, onset, duration, seed and polarity
is in final_holdout_manifest.csv, including full profile contents. Profiles are
materialized only in temporary work space. No historical file is overwritten.

All model/behavior groups are present. Non-communication models have 40 cases
per behavior; communication has 80/model, using hash-selected 27 transient,
27 intermittent, 26 permanent cases from a fixed 40-case grid. The hash selection
is completely determined before any outcomes. Benign offsets form a 4x5x3 grid
per base profile. Hardware intermittent windows are 700 on/1100 off; legacy
intermittent is two transients separated by 1100 ms. Drop interval is 11 updates.

New continuous magnitudes: pump .965/.81; sensor bias -3.5/6.5; intermittent
sensor 3.5/7.5; task delay 800/1300 ms; communication delay 300/600 ms;
drop counts 3/8; replay ages 600/1700 ms. Memory bits 0/4 necessarily reuse
members of the finite supported bit domain; stuck polarity varies. Fan-stuck
has no magnitude, and a transient deadline miss necessarily lasts one tick
(100 ms). Severity-equivalent permanent/deadline cases use distinct 1700 ms
onset offsets. Novelty is in exact complete configurations, not a claim of
new fault mechanisms or unseen values for every categorical parameter.

Overlap audit canonicalizes numeric profile contents (not filenames or CSV
formatting), model, behavior, onset and meaningful magnitude/duration. It
conservatively ignores seed/polarity and ignored permanent durations. Exact
overlap is zero within this cohort and against ALL Candidate 1, Candidate 2,
v7.2 (including its abandoned draft), and v7.3 TRAIN/VALIDATION configurations.
Every final command passed the unchanged C configuration validator without
simulation before registration. No favorable subsets may be dropped.

## Execution and frozen comparators

Execute the exact frozen virtual_ecu_v7_3 binary with revised.cfg, the frozen
Candidate 2 configuration and Weighted Sum choice 6. All observer states see
the same runtime observations in one physics execution and remain observe-only.
Report Simple OR, frozen Fair Weighted Sum, Plain DS, frozen v7.2, frozen v7.3,
Hybrid, and Timing Monitor restricted to timing and benign cases. The existing
binary also computes Candidate 2 internally; it is not an additional reported
holdout comparison. All old baselines use their ORIGINAL extraction. None gain
the revised actuator evidence. The old Hybrid inputs remain unchanged.
No ground truth, injected origin, activation flag or reference deviation enters
v7.3 inference. Evaluation onset and truth are used solely in post-hoc scoring.

## Fixed metrics and comparisons

Fault detection uses the frozen evaluator's first new post-onset alarm edge.
Any benign alarm is a false alarm. Report all fault cases, including no-effect
latent faults, in recall denominators. Precision is TP/(TP+benign false alarms).
Latency is first post-onset alarm minus onset among detections; misses are never
assigned zero latency. Median/P95 use the frozen linear quantile convention.
Plant propagation uses the unchanged accepted reference comparison after runtime.
Report plant-conditional coverage and silent plant cases; pre/same/post timestamps
are restricted to detected plant-propagating cases. Other detected faults with
no plant manifestation are separate, not misclassified as pre-plant alarms.

First-alarm localization coverage includes non-UNKNOWN outputs among detections;
accuracy is correct among those outputs, UNKNOWN is reported separately. Include
all five true origins, UNKNOWN and misses in the confusion table. Report wrong
localized steps throughout runtime and correctly localized-before-plant cases.
Wilson two-sided 95% intervals use z=1.959963984540054 for detection, each origin,
plant coverage, silent plant rate, benign alarm rate, precision, localization
coverage, conditional accuracy, UNKNOWN, wrong-origin rate and pre-plant/localized
before-plant proportions. Macro coverage is the unweighted origin mean; no false
binomial CI is attached to a macro mean. Correlated designed families limit
population interpretation of all nominal intervals.

Pair v7.3 with Weighted Sum and v7.2 by run ID: both/only-v7.3/only-comparator/neither.
For zero or fewer than ten discordant pairs, give counts only and no McNemar p.
For at least ten, report the exact two-sided conditional binomial McNemar tail
2*sum(binomial(n,k), k<=min(discordant directions))/2**n, capped at one.
Treat p as descriptive under an IID assumption, not proof across correlated
families. Empirical binary superiority on this fixed modeled holdout requires
positive net paired detections, no higher benign alarm count, and p<.05 when
the test is eligible. No claim of universal/DS-specific superiority follows.

Subgroups are predeclared by origin/model/behavior (and severity in a companion
table). Generalization beyond intermittent actuator faults means a positive
net gain over v7.2 outside ACTUATOR/intermittent; report exact contributing
subtypes, not a blanket cross-origin improvement. Show all actuator subtypes,
communication, memory, timing and sensor/control. Test whether stuck-bit runs
whose nominal target remains unchanged still evade detection; do not remove
them from overall coverage. Report unexcited actuator misses honestly.

## Post-hoc identifiability and artifacts

After each C runtime finishes, hash the complete allowed-observation stream and
complete six-channel evidence/availability stream using exact serialized values,
and inspect the trace for scoring consistency. Group these signatures and join
origin labels ONLY after all runtime executions. No signature or post-hoc label
is fed back into any detector. Full raw-history equivalence and feature-history
equivalence are different claims. No tolerance-based grouping is invented.

Temporary raw, summary, evidence and observation CSVs are discarded after offline
summaries/signatures and SHA256 identities are recorded. Retain compact per-run
metrics, exact commands with a reproducible temporary-workspace token, profile
manifest, input/output signatures, subgroup/identifiability tables and a few
paper figures. The listed top-level artifacts are the only output files.

After evaluation verify every frozen v7.3 hash again, build/compile, run all tests,
48 legacy cases and 64 RTL cases in temporary directories, and verify original
tracked files/session plus Hybrid/HETIA identities. No commit/push.

Methods: [NIST Wilson intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm),
[paired McNemar definition](https://www.stat.ethz.ch/R-manual/R-devel/library/stats/html/mcnemar.test.html),
[exact paired binomial calculation](https://pdixon.stat.iastate.edu/stat511/notes/part%202b.pdf).

## Pre-outcome source and design identities

```json
{json.dumps(identities,indent=2,sort_keys=True)}
```
'''
 (OUT/'final_holdout_protocol.md').write_text(protocol)
 registration=dict(registered_utc=stamp,protocol_sha256=sha(OUT/'final_holdout_protocol.md'),source_and_design_sha256=identities,frozen_manifest_sha256=sha(FROZEN/'clo_dsf_revised_hashes.json'),outcomes_seen=False)
 (OUT/'validation_record.md').write_text('# Final holdout validation record\n\nPre-outcome registration (immutable):\n```json\n'+json.dumps(registration,indent=2,sort_keys=True)+'\n```\n\nExecution pending.\n')
 return registration

def check_registration(reg):
 assert sha(OUT/'final_holdout_protocol.md')==reg['protocol_sha256']
 assert all(sha(ROOT/k)==v for k,v in reg['source_and_design_sha256'].items())

def execute(s,work):
 cmd=command(s,work);p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(s['run_id']+' failed: '+p.stdout+p.stderr)
 raw=Path(cmd[1]);summary=summarize_rows(read_rows(raw));outcomes=[]
 for row in read(work/'metrics.csv'):
  if row['method'] not in METHODS:continue
  if None in row:raise ValueError('Malformed online metrics')
  r={k:v for k,v in s.items() if k!='profile_json'};r.update(row)
  for k in row:
   if k not in ['method','origin_at_alarm','leading_at_alarm','first_origin']:r[k]=float(row[k]) if k.startswith(('mean_','origin_')) else int(row[k])
  r['injected']=int(s['origin']!='NORMAL');r['detected']=int(r['injected'] and r['first_post_alarm_ms']>=0);r['false_alarm']=int(not r['injected'] and r['first_alarm_ms']>=0);r['latency_ms']=r['first_post_alarm_ms']-s['start_ms'] if r['detected'] else None
  for k in ['control_effect','actuator_effect','plant_manifestation','propagation_plant_ms','propagation_control_ms','propagation_actuator_command_ms']:r[k]=summary[k]
  r['silent_plant']=int(r['injected'] and r['plant_manifestation']==1 and not r['detected']);derived(r)
  r['wrong_localized_runtime_samples']=sum(r['alarm_'+origin] for origin in ORIGINS if origin!=s['origin']);outcomes.append(r)
 # These files are read only AFTER the runtime process has exited.
 obs_hash=hashlib.sha256();evidence_hash=hashlib.sha256();max_target=0.;gap=0.;active_gap=0.;samples=0
 with (work/'observations.csv').open(newline='') as f:
  for o in csv.DictReader(f):
   obs_hash.update((','.join(o.values())+'\n').encode());samples+=1
   now=int(o['time_ms']);max_target=max(max_target,abs(float.fromhex(o['control_target_c'])-92))
   current=max(abs(float.fromhex(o['pump_command'])-float.fromhex(o['pump_actual'])),abs(float.fromhex(o['fan_command'])-float.fromhex(o['fan_actual'])));gap=max(gap,current)
   if now>=s['start_ms']:active_gap=max(active_gap,current)
 wrong=0;trace_alarms=0;mass_error=0.;trace_samples=0
 with (work/'trace.csv').open(newline='') as f:
  for t in csv.DictReader(f):
   evidence_hash.update((','.join(t[k] for k in t if k.endswith('_evidence') or k.endswith('_detection_reliability'))+'\n').encode());trace_samples+=1
   alarm=int(t['alarm']);trace_alarms+=alarm
   wrong+=alarm and t['estimated_origin'] not in ['UNKNOWN',s['origin']]
   mass_error=max(mass_error,abs(sum(float(t[f'origin_mass_{i}']) for i in range(1,32))-1),abs(sum(float(t[k]) for k in ['detection_mass_normal','detection_mass_abnormal','detection_mass_ignorance'])-1))
 revised=next(r for r in outcomes if r['method']=='Revised CLO-DSF')
 assert samples==trace_samples==revised['samples']==1201
 assert trace_alarms==revised['alarm_samples'] and wrong==revised['wrong_localized_runtime_samples'] and mass_error<1e-12
 signatures=dict(run_id=s['run_id'],origin_evaluation_only=s['origin'],model=s['model'],behavior=s['behavior'],observation_history_sha256=obs_hash.hexdigest(),evidence_history_sha256=evidence_hash.hexdigest(),samples=samples,max_target_deviation=max_target,max_response_gap=gap,max_post_onset_response_gap=active_gap,latent_stuck_target_unchanged=int(s['model']=='stuck_bit' and max_target==0),wrong_localized_runtime_samples=wrong,max_mass_normalization_error=mass_error)
 provenance=dict(run_id=s['run_id'],command_json=json.dumps([v.replace(str(work),'{WORK}') for v in cmd]),raw_sha256=sha(raw),summary_sha256=sha(raw.with_name(raw.stem+'_summary.csv')),observation_csv_sha256=sha(work/'observations.csv'),trace_sha256=sha(work/'trace.csv'),metrics_sha256=sha(work/'metrics.csv'))
 for path in [raw,raw.with_name(raw.stem+'_summary.csv'),work/'observations.csv',work/'trace.csv',work/'metrics.csv']:path.unlink()
 return outcomes,signatures,provenance

def amend_serialization(original):
 # A disclosed pre-outcome I/O correction, not an outcome-driven redesign.
 stamp=datetime.now(timezone.utc).isoformat()
 identities={name:sha(ROOT/name) for name in original['source_and_design_sha256']}
 identities['tests/holdout_configuration_check.c']=sha(ROOT/'tests/holdout_configuration_check.c')
 identities[str((OUT/'paper_tables/pre_outcome_registration_history.csv').relative_to(ROOT))]=sha(OUT/'paper_tables/pre_outcome_registration_history.csv')
 with (OUT/'final_holdout_protocol.md').open('a') as f:f.write('\n## Pre-outcome serialization amendment\n\n'+stamp+' UTC. The first process stopped in profile loading before any simulation (zero completed cases). JSON key order had been used as positional CSV column order. Only materialization now uses the C reader\'s required seven-column order. The public C profile loader and coverage validator now check every command before execution. All manifest values, profile semantics, seeds, case selection, metrics, decision rules, detector and baseline identities remain unchanged. The original source/protocol contents and hashes are preserved in paper_tables/pre_outcome_registration_history.csv. The erroneous input attempt is not represented as an observed simulation. This explicit pre-outcome amendment authorizes one execution of the same 1500 configurations, with no substitution or tuning.\n\nUpdated pre-outcome identities:\n```json\n'+json.dumps(identities,indent=2,sort_keys=True)+'\n```\n')
 reg=dict(registered_utc=stamp,protocol_sha256=sha(OUT/'final_holdout_protocol.md'),source_and_design_sha256=identities,frozen_manifest_sha256=sha(FROZEN/'clo_dsf_revised_hashes.json'),outcomes_seen=False,completed_simulations_before_amendment=0)
 with (OUT/'validation_record.md').open('a') as f:f.write('\nPre-outcome amendment registration (initial registration retained above):\n```json\n'+json.dumps(reg,indent=2,sort_keys=True)+'\n```\n')
 return reg

def append_csv(path,items):
 exists=path.exists()
 with path.open('a',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(items[0]))
  if not exists:writer.writeheader()
  writer.writerows(items)

def run(repair_profile_order=False):
 verification=verify_frozen() # Mandatory STOP gate before design or any run.
 if (OUT/'final_holdout_protocol.md').exists() and not repair_profile_order:raise ValueError('Holdout already registered: refuse rerun or overwrite')
 OUT.mkdir(exist_ok=True);(OUT/'paper_tables').mkdir(exist_ok=True);(OUT/'paper_figures').mkdir(exist_ok=True)
 if repair_profile_order:
  import re
  text=(OUT/'validation_record.md').read_text()
  assert 'holdout_0000 after 0 completed cases' in text
  assert not (OUT/'paper_tables/per_run_outcomes.csv').exists()
  original=json.loads(re.search(r'```json\n(.*?)\n```',text,re.S).group(1))
  for name in ['final_holdout_manifest.csv','configuration_overlap_audit.csv']:
   path=OUT/name;assert sha(path)==original['source_and_design_sha256'][str(path.relative_to(ROOT))]
  specs=records(OUT/'final_holdout_manifest.csv')
 else:
  specs=design();write_csv(OUT/'final_holdout_manifest.csv',specs);overlap(specs)
 with tempfile.TemporaryDirectory(prefix='clo-v8-runtime-') as temporary:
  work=Path(temporary);prepare_work(work,specs);validate(specs,work)
  reg=amend_serialization(original) if repair_profile_order else register(specs,verification)
  check_registration(reg)
  print('REGISTERED: 1500 unique cases, zero overlap, all C configurations valid. Outcomes start now.',flush=True)
  rows=[];signatures=[];provenance=[]
  for i,s in enumerate(specs):
   try:result,signature,proof=execute(s,work)
   except Exception as error:
    with (OUT/'validation_record.md').open('a') as f:f.write(f'\nEXECUTION STOPPED at {s["run_id"]} after {i} completed cases: {error!r}. No rerun or tuning.\n')
    raise
   rows+=result;signatures.append(signature);provenance.append(proof)
   append_csv(OUT/'paper_tables/per_run_outcomes.csv',result);append_csv(OUT/'paper_tables/runtime_signatures.csv',[signature]);append_csv(OUT/'paper_tables/run_provenance.csv',[proof])
   if (i+1)%50==0:print(f'HOLDOUT {i+1}/1500',flush=True)
  check_registration(reg)
 print(verify_frozen(),flush=True)
 from .clo_dsf_holdout_reporting import report
 report(rows,signatures)
 with (OUT/'validation_record.md').open('a') as f:f.write('\nAll 1500 runtime executions completed. Registered identities and all 9494 frozen v7.3 identities verified after execution. Final regression pending.\n')
 print('Holdout complete; no tuning or scientific changes. Final regression remains.',flush=True)
