#!/usr/bin/env python3
"""One split active-memory diagnostic experiment; no invented sensor anchor."""
import csv,json,hashlib,sys,subprocess,tempfile,copy
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'python'),str(ROOT/'scripts')]
import run_clo_dsf_integrity_event as prior
from virtual_ecu import clo_dsf_current as c
import run_clo_dsf_sensor_response as response
from virtual_ecu.clo_dsf_holdout import prepare_work,profile_identity
from virtual_ecu.clo_dsf_development import write_csv,sha,ORIGINS
OUT=c.OUT;BASE=Path('/tmp/clo-active-diagnostic')
METHODS=['Pre-change CLO-DSF','Memory only','Anchor unavailable','Revised CLO-DSF','Weighted Sum']

def design():
 specs=prior.design()
 for i,s in enumerate(specs):
  f=i//120;s['run_id']=s['run_id'].replace('event90_','active_');s['profile']=s['profile'].replace('event90_','active_');s['group']=s['group'].replace('event90_','active_')
  profile=json.loads(s['profile_json'])
  for z in profile:
   if z['start_ms']:z['start_ms']+=900
   if z['end_ms']<120000:z['end_ms']+=900
   z['vehicle_speed_kph']+=.9;z['ambient_temp_c']+=.43;z['engine_load']*=.983
   if f%2==0 and z['start_ms']==67200:z['engine_load']=0;z['vehicle_speed_kph']=0
  s['profile_json']=json.dumps(profile,sort_keys=True);s['profile_semantic_sha256']=profile_identity(profile)
  s['seed']+=300007
  if s['origin']!='NORMAL':s['start_ms']+=700
  if s['duration_ms'] and not (s['model']=='deadline_miss' and s['behavior']=='transient'):s['duration_ms']+=100
  s['target_updates_json']=json.dumps([[t+500,104 if v==103 else v] for t,v in json.loads(s['target_updates_json'])])
  if s['model']=='sensor_bias_ramp':s['magnitude']=(1 if s['magnitude']>0 else -1)*(1.4 if abs(s['magnitude'])<2 else 3.1);s['sensor_ramp_rise_ms']={11000:13000,37000:41000}[s['sensor_ramp_rise_ms']]
  if s['model']=='sensor_bias':s['magnitude']+=.011 if s['magnitude']>0 else -.011
  if s['model']=='sensor_interface_intermittent':s['magnitude']+=.013
  s['anchor_status']='unqualified_zero_load_interval' if f%2==0 else 'no_soak_interval'
  s.pop('configuration_sha256');s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()
 assert len(specs)==1200 and len({s['profile_semantic_sha256'] for s in specs})==1200
 return specs

def main():
 specs=design();old=set()
 for folder in [ROOT/'results',BASE]:
  for p in folder.rglob('*manifest.csv'):
   with p.open() as f:
    for r in csv.DictReader(f):
     if r.get('profile_semantic_sha256'):old.add(r['profile_semantic_sha256'])
 assert not old&{s['profile_semantic_sha256'] for s in specs}
 assert not {s['group'] for s in specs if s['partition']=='development-train'}&{s['group'] for s in specs if s['partition']=='development-validation'}
 with tempfile.TemporaryDirectory(prefix='clo-active-development-') as tmp:
  work=Path(tmp);c.build_prechange(work,BASE/'baseline.c');prepare_work(work,specs);c.METHODS=['Pre-change CLO-DSF','Revised CLO-DSF','Weighted Sum'];c.command=response.command
  objects=[str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o'];check=work/'check';subprocess.run(['gcc','-std=c11','-Iinclude','tests/holdout_configuration_check.c',*objects,'-o',str(check)],cwd=ROOT,check=True)
  for s in specs:
   cmd=response.command(s,work);v=subprocess.run([str(check),*cmd[2:]],capture_output=True,text=True);assert not v.returncode,(s['run_id'],v.stderr)
   s['command_json']=json.dumps([x.replace(str(work),'$WORK').replace(str(ROOT),'$ROOT') for x in cmd])
  assert all(p.is_file() for p in OUT.iterdir())
  for p in OUT.iterdir():p.unlink()
  write_csv(OUT/'campaign_manifest.csv',specs)
  source_names=['src/memory_diagnostic.c','include/memory_diagnostic.h','src/control.c','include/ecu_types.h','src/memory_diagnostic_backend.c','include/memory_diagnostic_backend.h','src/runtime_observation.c','include/runtime_observation.h','src/v7_3/clo_dsf_revised.c','src/v7_3/revised_runtime.c','scripts/run_clo_dsf_active_diagnostic.py','results/cross_layer_safety_v7_3_dev/revised.cfg','results/clo_dsf_current/campaign_manifest.csv']
  frozen={p:sha(ROOT/p) for p in source_names};(BASE/'frozen.json').write_text(json.dumps(frozen))
  (OUT/'validation_record.md').write_text('# Active diagnostic development\n\nRegistered '+datetime.now(timezone.utc).isoformat()+' before outcomes. Baseline '+(BASE/'head').read_text().strip()+'.1200 unique new simulations:720 TRAIN(600 faults/120 benign),480 VALIDATION(400 faults/80 benign). Six TRAIN versus four VALIDATION operating families; all profiles distinct; no overlap with prior inline manifests. All public configurations validated. No parameter search.\n\nMemory protocol:1000ms periodic atomic save/read,write0/read,write65535/read,restore/read. Seven memory accesses/check;16-byte per-ECU persistent state. Runtime checker receives only ordinary read/write callbacks. Virtual device backend enforces the already-active stuck-cell write constraint; inference/checker never sees bit identity or fault metadata. Normal scheduled injections and control writes unchanged. Transaction restores the actual saved word (not trusted shadow), never scrubs away a bit-flip or changes legal calibration metadata. Single-threaded scheduler excludes control/interrupt access during probes. Current plant simulator assigns no elapsed scheduler time to these accesses; hardware WCET is not measured. Results are conditional on this added storage-access contract.\n\nAnchor feasibility: no engine-off/no-heat mode, persistent base heat even at zero load, startup not ambient-soaked, no trustworthy independent equilibrium/soak certificate. No sensor anchor invented or fitted; no hidden temperature/equation inversion. Half the families contain a zero-load/zero-speed interval; it is explicitly NOT a qualified anchor. With-anchor denominator0, without-anchor all cases. A2 is exactlyA0(no anchor); A3 exactlyA1(memory only); aliases are clearly recorded, not distinct implemented sensors. Existing short-horizon sensor channel unchanged.\n\nA0 ignores added diagnostic observation; A1/A3 consume it as direct MEMORY/ABNORMAL support. All observers see the same physics stream. Weighted Sum remains choice6, unchanged. Effective/dormant labels use post-probe register-shadow mismatch only offline, so temporary diagnostic writes cannot fabricate effective corruption.\n\nRetention per implemented diagnostic: validation detection and dormant-memory detection improve; no lost A0 detections, no added benign alarms, no wrong confident origins, preserved full effective-memory/timing/communication/actuator detection; silent plant coverage non-regressing. No source/config changes after VALIDATION other than removal if rejected. Ninety-percent target cannot select settings or cohorts. Memory period chosen before outcomes; no thermal contract exists to calibrate. Eight representative validation traces preselected, no bulk raw retention. No unseen holdout/commit/push.\n\nFrozen identities:\n```json\n'+json.dumps(frozen,indent=2,sort_keys=True)+'\n```\n')
  retain={next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['origin']==o) for o in [*ORIGINS,'NORMAL']};retain.update(next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['model']==m) for m in ['sensor_bias','sensor_interface_intermittent'])
  base_read=c.read;probe={}
  def read(path):
   rr=base_read(path)
   if Path(path).name=='trace.csv':
    check_rows=[r for r in rr if int(r['memory_check_valid']) and r['time_ms']==r['memory_check_ms']]
    fail=[r for r in check_rows if int(r['memory_check_failed'])]
    probe.clear();probe.update(probe_checks=len(check_rows),probe_operations=7*len(check_rows),first_failed_probe_ms=int(fail[0]['time_ms']) if fail else -1)
   return rr
  c.read=read;rows=[];prior.OUT=OUT;prior.METHODS=METHODS
  for part in ['development-train','development-validation']:
   assert all(sha(ROOT/p)==h for p,h in frozen.items())
   for i,s in enumerate([s for s in specs if s['partition']==part]):
    rr=c.execute(s,work,s['run_id'] in retain)
    for r in rr:r.pop('command_json',None);r.update(probe);rows.append(r)
    for source,label in [('Pre-change CLO-DSF','Anchor unavailable'),('Revised CLO-DSF','Memory only')]:
     r=copy.deepcopy(next(r for r in rr if r['method']==source));r['method']=label;rows.append(r)
    if (i+1)%60==0:print(part,i+1,flush=True)
   prior.report(rows)
   with (OUT/'validation_record.md').open('a') as f:f.write('\n'+part+' completed with all frozen settings unchanged.\n')
   if part=='development-train':
    print('TRAIN READY; waiting for local unchanged-rule gate',flush=True);(BASE/'train_ready').write_text('ready')
    import time
    while not (BASE/'validation_go').exists():time.sleep(1)
  assert all(sha(ROOT/p)==h for p,h in frozen.items());print('1200-case ACTIVE campaign COMPLETE',flush=True)
if __name__=='__main__':main()
