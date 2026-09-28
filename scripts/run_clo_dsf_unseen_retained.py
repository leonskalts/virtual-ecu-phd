#!/usr/bin/env python3
"""Single registered unseen evaluation; no scientific implementation changes."""
import csv,hashlib,io,json,subprocess,sys,tempfile,shutil,math
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'python')]
import run_clo_dsf_final_unseen as base
import run_clo_dsf_redundant_sensor as redundant
from virtual_ecu import clo_dsf_current as c
from virtual_ecu.clo_dsf_holdout import prepare_work,profile_identity
from virtual_ecu.clo_dsf_development import write_csv,sha,ORIGINS
from virtual_ecu.clo_dsf_candidate2_development import aggregate
from virtual_ecu.clo_dsf_final_reporting import wilson
OUT=base.OUT;SCRATCH=Path('/tmp/clo-unseen-retained');PRE='e8126d9f3da261a210f1d16c83d4af57245036e2'
METHODS=['Revised CLO-DSF','Pre-change CLO-DSF','Weighted Sum','Simple OR','Plain DS','Hybrid','Timing Monitor']
def write(path,rows):
 write_csv(path,rows);path.write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
def design():
 specs=base.design()
 for i,s in enumerate(specs):
  f=i//150;j=i%150
  s.update(run_id=f'final_retained_{i:04}',profile=f'final_retained_profile_{i:04}',group=f'final_retained_family_{f}',seed=17000011+f*2237+j*97,reference_seed=19000019+f*1877+j*101,reference_offset=(j%7-3)*.031,reference_noise=[.028,.057,.086][(j+f)%3],sensor_chain='none',sensor_ramp_rise_ms=0,benign_reference_magnitude=0,benign_reference_duration=0,on_ms=[500,800,1100][f%3],off_ms=[1500,1200,1700][f%3])
  profile=[]
  load=[.41,.53,.64,.76,.87,.95,.48,.68,.81,.91][f]
  for a,b,fac in [(0,18100,.76),(18100,42700,.94),(42700,66900,.67),(66900,91700,1),(91700,120000,.83)]:
   profile.append(dict(start_ms=a,end_ms=b,vehicle_speed_kph=(21.37+f*8.13+j*.0023)*fac,engine_load=(load+j*.000017)*fac,ambient_temp_c=18.713+f*2.07+j*.00137,external_airflow_factor=.031 if a>=66900 else 0,road_slope_percent=0))
  s['start_ms']=120100 if s['origin']=='NORMAL' else 19200+(j%13)*700+f*100
  s['duration_ms']=0 if s['behavior'] in ['permanent','none'] else 100 if s['model']=='deadline_miss' and s['behavior']=='transient' else [700,2300,6700,13700][(j+f)%4]
  s['target_updates_json']=json.dumps([[35700,103],[72700,92]] if (j+f)%2 else [])
  s['workload']='authorized_updates' if (j+f)%2 else 'static_target'
  s['sensor_variation']='0.018:0:12700'
  if s['origin']=='MEMORY':s['start_ms']=20100+(j%10)*100+f*1000
  if s['origin']=='ACTUATOR':
   a=j-96
   if s['model']=='pump_degraded':s['magnitude']=[.987,.963,.928,.857,.746,.597][a//3]
   if a%4==0:
    for p in profile:p.update(engine_load=.085+j*.000001,ambient_temp_c=8.713+f*.13,vehicle_speed_kph=73.317+j*.013)
    s['target_updates_json']='[]';s['workload']='static_target'
  if s['origin']=='SENSOR_CONTROL':
   k=j-72
   if k<8:
    s.update(sensor_chain='primary' if k<4 else 'reference',model='sensor_bias_ramp',behavior='permanent',magnitude=(-1 if k%2==0 else 1)*([1.63,2.57][(k//2)%2]+f*.006),duration_ms=0,sensor_ramp_rise_ms=[13700,31900,56300,71300][(k+f)%4])
   elif k<12:s.update(sensor_chain='common_mode',model='sensor_bias_ramp',behavior='permanent',magnitude=(-1 if k%2==0 else 1)*[1.63,2.57][(k//2)%2],duration_ms=0,sensor_ramp_rise_ms=[17300,43700][k%2])
   elif k<18:
    t=k-12;dur=[100,200,0][t%3]
    s.update(sensor_chain='primary' if t<3 else 'reference',model='sensor_bias',behavior='transient' if dur else 'permanent',magnitude=(-1 if (t+f)%2==0 else 1)*([.47,.66,.84][(t+f)%3]+f*.003),duration_ms=dur)
   else:
    t=k-18;dur=[200,700,0][t%3]
    s.update(sensor_chain='primary' if t<3 else 'reference',model='sensor_interface_intermittent',behavior='transient' if dur else 'permanent',magnitude=(-1 if (t+f)%2==0 else 1)*([.37,.56,.79][(t+f)%3]+f*.002),duration_ms=dur)
  if s['origin']=='NORMAL':
   k=j-120;s['sensor_variation']=['.025:0:12700','.085:0:16900','.065:1.35:18100','.035:2.1:22900','.095:0:13700','.045:.75:15700'][k//5]
   if k%5 in [1,2]:s.update(benign_reference_magnitude=.83 if k%5==1 else -.83,benign_reference_duration=100)
   if k%5 in [3,4]:s.update(benign_reference_magnitude=.32 if k%5==3 else -.32,benign_reference_duration=400 if k%5==3 else 1100)
  s['profile_json']=json.dumps(profile,sort_keys=True);s['profile_semantic_sha256']=profile_identity(profile)
  s.pop('configuration_sha256',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()
 return specs

def command(s,w):
 cmd=redundant.command(s,w)
 for k,v in {'--intermittent-on-ms':s['on_ms'],'--intermittent-off-ms':s['off_ms'],'--drop-every-n-updates':17}.items():
  if k in cmd:cmd[cmd.index(k)+1]=str(v)
 if s['benign_reference_duration']:cmd+=['--revised-reference-fault',f"2:30900:0:{s['benign_reference_duration']}:0:{s['benign_reference_magnitude']}"]
 return cmd

def history(specs):
 keys={s['profile_semantic_sha256'] for s in specs};assert len(keys)==1500
 audit=[];seen=set()
 def consume(label,data,blob):
  if blob in seen:return
  seen.add(blob)
  try:rs=list(csv.DictReader(io.StringIO(data)))
  except (csv.Error,UnicodeError):return
  if not rs:return
  profiles=set();identities=set()
  if {'start_ms','end_ms','vehicle_speed_kph','engine_load','ambient_temp_c'}<=rs[0].keys():profiles.add(profile_identity([{k:(r.get(k) or 0) for k in ['start_ms','end_ms','vehicle_speed_kph','engine_load','ambient_temp_c','external_airflow_factor','road_slope_percent']} for r in rs]))
  else:
   for r in rs:
    if r.get('profile_json'):profiles.add(profile_identity(json.loads(r['profile_json'])))
    elif r.get('profile_semantic_sha256'):profiles.add(r['profile_semantic_sha256'])
    if r.get('configuration_sha256'):identities.add(r['configuration_sha256'])
  if profiles or identities or 'manifest' in label:
   overlap=len(keys&profiles);assert overlap==0,label
   audit.append(dict(source=label,blob_sha=blob,rows=len(rs),prior_profile_identities=json.dumps(sorted(profiles)),prior_configuration_identities=json.dumps(sorted(identities)),shared_profiles=overlap,exact_overlap=0,proof='disjoint full physical profiles; manifest-only references covered by historical profile objects' if not profiles else 'disjoint full physical profiles'))
 # Preserve and read the replaced manifest before any result mutation.
 old=OUT/'campaign_manifest.csv';shutil.copyfile(old,SCRATCH/'previous_manifest.csv');consume('previous committed final_unseen manifest',old.read_text(),sha(old))
 for root in [ROOT/'results',ROOT/'presets']:
  for p in root.rglob('*.csv'):
   header=p.open().readline()
   if 'manifest' in p.name or 'profile_json' in header or 'profile_semantic_sha256' in header or ('vehicle_speed_kph' in header and 'end_ms' in header):consume(str(p.relative_to(ROOT)),p.read_text(),sha(p))
 for line in subprocess.check_output(['git','rev-list','--objects','--all'],cwd=ROOT,text=True).splitlines():
  parts=line.split(' ',1)
  if len(parts)!=2:continue
  blob,name=parts
  if name.endswith('.csv') and ('manifest' in name or '/profiles/' in name):
   data=subprocess.check_output(['git','cat-file','blob',blob],cwd=ROOT).decode();consume('git:'+blob+':'+name,data,blob)
 for p in Path('/tmp').glob('clo*/**/*manifest.csv'):
  if p==SCRATCH/'previous_manifest.csv':continue
  consume(str(p),p.read_text(),sha(p))
 return audit

def build(w):
 # Comparator implementation from committed pre-refinement source; same public ABI.
 old=subprocess.check_output(['git','show',PRE+':src/v7_3/clo_dsf_revised.c'],cwd=ROOT,text=True)
 for fn in ['clo_revised_init','clo_revised_extract','clo_revised_step']:old=old.replace(fn,fn.replace('clo_revised','clo_prechange'))
 mem=subprocess.check_output(['git','show',PRE+':src/memory_diagnostic.c'],cwd=ROOT,text=True).replace('memory_diagnostic_step','memory_diagnostic_old_step')
 adapter=(ROOT/'src/v7_3/revised_runtime.c').read_text().replace('static clo_revised_t prechange;','static clo_revised_t prechange;\nstatic memory_diagnostic_t old_probe;\nvoid memory_diagnostic_old_step(memory_diagnostic_t *,unsigned int,memory_read_fn,memory_write_fn,void *);')
 adapter=adapter.replace(' if(enabled && state->log_file)\n  memory_diagnostic_step',' if(enabled && state->log_file)\n  memory_diagnostic_old_step(&old_probe,state->time.time_ms,cross_layer_memory_read,cross_layer_memory_write,state);\n if(enabled && state->log_file)\n  memory_diagnostic_step')
 adapter=adapter.replace(' if(comparison) {',' if(comparison) {\n  runtime_observation_t legacy_o=o;legacy_o.memory_check_ms=old_probe.checked_ms;legacy_o.memory_check_valid=old_probe.valid;legacy_o.memory_check_failed=old_probe.failed;')
 assert 'clo_prechange_step(&prechange,&config,&o)' in adapter
 adapter=adapter.replace('clo_prechange_step(&prechange,&config,&o)','clo_prechange_step(&prechange,&config,&legacy_o)')
 objects=[]
 for name,source in [('prechange',old),('old_probe',mem),('adapter',adapter)]:
  p=w/(name+'.c');p.write_text(source);obj=p.with_suffix('.o');subprocess.run(['gcc','-std=c11','-O2','-Iinclude','-c',str(p),'-o',str(obj)],cwd=ROOT,check=True);objects.append(str(obj))
 objects += [str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o']
 objects += [str(ROOT/p) for p in ['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7/accepted_main.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o','src/v7_2/final_observation_io.o','src/v7_3/clo_dsf_revised.o']]
 exe=w/'comparison';subprocess.run(['gcc',*objects,'-Wl,--wrap=detection_algorithm_step','-Wl,--wrap=cross_layer_fault_step','-Wl,--wrap=sensors_step','-lm','-o',str(exe)],check=True);return exe

def active(s,t):
 start=s['start_ms'];d=s['duration_ms'];b=s['behavior']
 if t<start:return False
 if b=='permanent':return True
 if s['origin'] in ['MEMORY','TIMING','COMMUNICATION']:
  if t>=start+d:return False
  return b!='intermittent' or (t-start)%(s['on_ms']+s['off_ms'])<s['on_ms']
 return t<start+d or b=='intermittent' and start+d+1100<=t<start+2*d+1100

def subreport(rows):
 groups={
 'effective_memory':lambda r:r['origin']=='MEMORY' and r['effective_memory_corruption'],
 'dormant_memory':lambda r:r['model']=='stuck_bit' and not r['effective_memory_corruption'],
 'legal_updates':lambda r:not r['injected'] and r['workload']=='authorized_updates',
 'primary_slow':lambda r:r['sensor_chain']=='primary' and r['model']=='sensor_bias_ramp',
 'reference_slow':lambda r:r['sensor_chain']=='reference' and r['model']=='sensor_bias_ramp',
 'common_mode':lambda r:r['sensor_chain']=='common_mode',
 'weak_steps':lambda r:r['model']=='sensor_bias',
 'pulses':lambda r:r['model']=='sensor_interface_intermittent',
 'actuator_excited':lambda r:r['origin']=='ACTUATOR' and r['actuator_excited'],
 'actuator_unexcited':lambda r:r['origin']=='ACTUATOR' and not r['actuator_excited']}
 for b in ['transient','intermittent','permanent']:groups['actuator_'+b]=lambda r,b=b:r['origin']=='ACTUATOR' and r['behavior']==b
 sub=[]
 for method in METHODS:
  for g,fn in groups.items():
   rs=[r for r in rows if r['method']==method and fn(r)]
   if not rs:continue
   a=aggregate(rs);lo,hi=wilson(a['detected'],a['faulty_runs']);sub.append(dict(method=method,group=g,**a,ci_low=lo,ci_high=hi,probe_phase_misses=sum(r['model']=='stuck_bit' and not r['effective_memory_corruption'] and not r['detected'] and r['active_probe_checks']==0 for r in rs)))
 write(OUT/'subgroup_summary.csv',sub)

def main():
 if (SCRATCH/'started').exists():raise SystemExit('One-shot execution already started; no rerun')
 commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
 assert commit=='48315a665adb91b58be5b754c3bf2478be2fe105'
 assert subprocess.check_output(['git','diff','--name-only','HEAD'],text=True).splitlines()==['presets/gui_session_state.json']
 paths=subprocess.check_output(['git','ls-files'],text=True).splitlines();initial={p:sha(ROOT/p) for p in paths if (ROOT/p).is_file()};(SCRATCH/'initial.json').write_text(json.dumps(initial))
 scientific={p:h for p,h in initial.items() if p.startswith(('src/','include/','python/','scripts/','tests/')) or p.endswith(('.mk','.cfg')) or p=='Makefile'}
 scientific[str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
 specs=design();audit=history(specs);write(SCRATCH/'overlap_audit.csv',audit)
 print('History incorporated:',len(audit),'sources; overlap zero',flush=True)
 subprocess.run(['make','-B','-f','clo_dsf_revised.mk','-j4'],check=True,stdout=(SCRATCH/'build.log').open('w'),stderr=subprocess.STDOUT)
 with tempfile.TemporaryDirectory(prefix='clo-retained-unseen-') as temp:
  w=Path(temp);prepare_work(w,specs);exe=build(w)
  objects=[str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o'];check=w/'check'
  subprocess.run(['gcc','-std=c11','-Iinclude','tests/holdout_configuration_check.c',*objects,'-o',str(check)],check=True)
  for s in specs:
   cmd=command(s,w);p=subprocess.run([str(check),*cmd[2:]],capture_output=True,text=True)
   assert p.returncode==0,(s['run_id'],p.stderr)
   s['command_json']=json.dumps([v.replace(str(w),'$WORK').replace(str(ROOT),'$ROOT') for v in [str(exe),*cmd[1:]]])
  # Old manifest and identities already incorporated durably into scratch audit.
  shutil.rmtree(OUT);OUT.mkdir();shutil.copyfile(SCRATCH/'overlap_audit.csv',OUT/'overlap_audit.csv');write(OUT/'campaign_manifest.csv',specs)
  (OUT/'protocol.md').write_text(PROTOCOL.replace('$COMMIT',commit).replace('$UTC',datetime.now(timezone.utc).isoformat()))
  frozen={**scientific,**{str((OUT/n).relative_to(ROOT)):sha(OUT/n) for n in ['protocol.md','campaign_manifest.csv','overlap_audit.csv']}}
  (SCRATCH/'frozen.json').write_text(json.dumps(frozen))
  def verify():assert all(sha(ROOT/p)==v for p,v in frozen.items()),'Frozen hash mismatch: STOP'
  verify();(OUT/'validation_record.md').write_text('# Validation record\n\nCommit '+commit+'; pre-refinement '+PRE+'.\nRegistered before outcomes. Scientific, harness and protocol hashes:\n```json\n'+json.dumps(frozen,indent=2)+'\n```\n')
  (SCRATCH/'started').write_text('Protocol frozen; no rerun permitted')
  c.OUT=OUT;c.METHODS=METHODS;c.command=lambda s,w:[str(exe),*command(s,w)[1:]]
  original_read=c.read;observed={}
  def read(path):
   rr=original_read(path)
   if Path(path).name=='observations.csv':observed['rows']=rr
   return rr
  c.read=read
  retain={next(s['run_id'] for s in specs if s['origin']==o) for o in [*ORIGINS,'NORMAL']}

  for ch in ['primary','reference']:retain.add(next(s['run_id'] for s in specs if s['sensor_chain']==ch and s['model']=='sensor_bias_ramp' and s['run_id'] not in retain))
  assert len(retain)==8
  rows=[]
  for i,s in enumerate(specs):
   if i%50==0:verify()
   rr=c.execute(s,w,s['run_id'] in retain)
   obs=[o for o in observed['rows'] if active(s,int(o['time_ms']))]
   def num(v):
    try:return float(v)
    except ValueError:return float.fromhex(v)
   axis='pump' if s['model']=='pump_degraded' else 'fan'
   excited=int(any(abs(num(o[axis+'_command']))>1e-8 for o in obs)) if s['origin']=='ACTUATOR' else 0
   checks=len({o['memory_check_ms'] for o in obs if int(o['memory_check_valid']) and int(o['memory_check_ms'])==int(o['time_ms'])})
   for r in rr:
    if r['method']=='Timing Monitor' and r['origin']!='TIMING':continue
    r.pop('command_json',None);r.update(actuator_excited=excited,active_probe_checks=checks);rows.append(r)
   if (i+1)%50==0:print('Completed',i+1,'/1500',flush=True)
  verify();write(OUT/'case_summary.csv',rows);base.METHODS=METHODS;base.report(rows);subreport(rows)
  for p in OUT.glob('*.csv'):
   if p.name not in ['campaign_manifest.csv','overlap_audit.csv']:p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
  verify()
  with (OUT/'validation_record.md').open('a') as f:f.write('\n1500/1500 executed once; frozen identities unchanged. No selection, retuning or rerun. Regression pending.\n')
  (SCRATCH/'complete').write_text('1500 complete');print('FINAL UNSEEN COMPLETE; regression pending',flush=True)

PROTOCOL='''# Final retained CLO-DSF unseen protocol

Commit $COMMIT. Frozen UTC $UTC before outcomes. Pre-refinement comparator e8126d9f3da261a210f1d16c83d4af57245036e2. This is ONE final unseen evaluation; all prior campaigns are seen. No parameter selection, exclusion, rerun or redesign allowed, regardless of resulting percentage.

1500 deterministic simulations: 240 MEMORY, 240 TIMING, 240 COMMUNICATION, 240 SENSOR_CONTROL, 240 ACTUATOR, 300 benign. Ten operating families, each contributing equally. The origin-balanced distribution is fixed without outcomes. SENSOR_CONTROL per family: four primary slow drifts, four reference slow drifts, four common-mode controls, six weak steps, six pulses. Equal primary/reference abrupt faults, alternating signs; 100/200ms or permanent steps; 200/700ms or persistent pulse trains. Drift rises13700/31900/56300/71300ms; common-mode17300/43700ms. Full magnitudes, profiles, durations, onsets and effective seeds are in the manifest. Negative pulse magnitude follows unchanged signed injector semantics. No assumption that short pulses are distinguishable from benign excursions.

Memory includes both stuck polarities and bit flips, transient/intermittent/permanent; difficult100ms probe phases with500/1500,800/1200 or1100/1700ms on/off cycles. Effective/dormant status determined post hoc by actual register-shadow inconsistency, never supplied to inference. Dormant detection may legitimately arise from active write/read inconsistency. Probe-phase misses are undetected dormant runs with no active-window probe; other memory misses remain in overall statistics. Legal calibration updates tested independently in benign cases.

Actuator includes six degradation levels .987/.963/.928/.857/.746/.597, fan stuck off, all three behaviors. One quarter use predefined cold low-load profiles to test no-excitation limits. Excited means nonzero command to the affected actuator during its actual fault windows, determined post hoc. No exclusions for lack of excitation. Legacy intermittent actuator/sensor events retain the two-episode semantics and1100ms separation. Timing and communication retain valid ticks/delays/drops/replays, short700ms and longer finite disturbances. Continuous parameters/seeds/profiles are new; discrete valid bits/ticks may recur.

Benign: independent bounded reference noise, primary alternating variation and slow triangles, legal target changes, isolated positive/negative0.83C100ms reference excursions and small0.32C400/1100ms disagreement. No promise that every registered benign transient satisfies every detector contract; any alarms count as false positives. Every case lasts120s at100ms cadence. Thermal ramps arise from the shared registered operating profiles.

Audit all saved profile/identity tables, historical Git manifest/profile blobs on all refs, and surviving temporary overwritten manifests. Preserve old final_unseen manifest before replacement. Audit retains previous identity sets and content hashes. Disjoint complete physical profiles prove zero exact configuration equality independent of inconsistent older identity encodings. Legacy manifests referring to profile files are covered by historical profile objects. No claim about experiments with no recoverable configuration evidence.

Current inference is exact HEAD source, unchanged. Comparison-only temporary adapter runs pre-refinement source with its own original1000ms probe timestamps, using independently restored atomic transactions. Current phase-sweep remains unchanged. Same runtime stream for CURRENT, pre-refinement, frozen Fair Weighted Sum(choice6), Simple OR, Plain DS, Hybrid. Timing Monitor scored only on TIMING. No alternate algorithm tree. Ground truth used only for offline metrics.

Detection: first post-onset alarm; benign: any alarm; latency from scheduled activation. Report pre-onset alarms separately. Plant propagation uses the unchanged counterfactual evaluator. First-detection localization coverage/accuracy and all-alarm runtime localized accuracy/UNKNOWN/wrong samples/runs reported; sensor member remains unidentifiable. Per-origin and prescribed subgroups retained regardless of results. Wilson95 case-level intervals are descriptive because grouped deterministic cases are not independent population draws. Exact two-sided binomial McNemar for nonzero discordant fault detections, otherwise not applicable; paired counts and silent misses/benign/latency comparisons accompany it. Statistical evidence is limited to this campaign.

Max eight compressed traces preselected: first case per origin including NORMAL, plus first distinct primary/reference slow drift. Stream summaries and delete raw runs after scoring. Hashes checked before and after outcomes. One final full regression: build, compile, diff check, full tests,48 legacy,64 RTL. Preserve GUI, Hybrid/HETIA and legacy evidence. No commit/push.
'''
if __name__=='__main__':main()
