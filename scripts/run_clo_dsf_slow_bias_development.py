#!/usr/bin/env python3
"""One CURRENT slow-bias development pass; no unsupported drift channel."""
import hashlib,json,shutil,sys,tempfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'python'),str(ROOT/'scripts')]
import run_clo_dsf_sensor_response as previous
from virtual_ecu import clo_dsf_current as c
from virtual_ecu.clo_dsf_development import write_csv,sha,ORIGINS
from virtual_ecu.clo_dsf_holdout import profile_identity
from virtual_ecu.clo_dsf_final_reporting import records
OUT=c.OUT

def design():
 specs=previous.design()
 for s in specs:
  s['run_id']=s['run_id'].replace('response_','slow_');s['profile']=s['profile'].replace('response_','slow_');s['group']=s['group'].replace('response_','slow_')
  profile=json.loads(s['profile_json'])
  for segment in profile:
   if segment['start_ms']:segment['start_ms']+=700
   if segment['end_ms']<120000:segment['end_ms']+=700
   segment['engine_load']+=.005;segment['vehicle_speed_kph']+=1.2;segment['ambient_temp_c']+=.4
  s['profile_json']=json.dumps(profile,sort_keys=True)
  s['profile_semantic_sha256']=profile_identity(profile)
  s['seed']+=100003
  if s['origin']!='NORMAL':s['start_ms']+=1100
  s['target_updates_json']=json.dumps([[t+800,v] for t,v in json.loads(s['target_updates_json'])])
  if s['model']=='sensor_bias_ramp':
   s['sensor_ramp_rise_ms']={2000:5000,10000:15000,30000:40000}[s['sensor_ramp_rise_ms']]
   s['magnitude']=(1 if s['magnitude']>0 else -1)*{.9:1.,2.2:2.4,4.4:4.8}[abs(s['magnitude'])]
  s.pop('configuration_sha256');s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()
 assert len(specs)==900 and len({s['profile_semantic_sha256'] for s in specs})==900
 assert not {s['group'] for s in specs if s['partition']=='development-train'}&{s['group'] for s in specs if s['partition']=='development-validation'}
 return specs

def main():
 baseline=Path('/tmp/clo-slow-pass/prechange.c');assert baseline.read_bytes()==(ROOT/'src/v7_3/clo_dsf_revised.c').read_bytes()
 specs=design();c.command=previous.command
 prior={r['profile_semantic_sha256'] for r in records(OUT/'development_manifest.csv')};assert not prior&{s['profile_semantic_sha256'] for s in specs}
 with tempfile.TemporaryDirectory(prefix='clo-slow-development-') as tmp:
  work=Path(tmp);c.build_prechange(work,baseline);c.prepare(specs,work)
  assert all(p.is_file() for p in OUT.iterdir())
  for p in OUT.iterdir():p.unlink()
  for s in specs:s['command_json']=json.dumps([v.replace(str(work),'$WORK').replace(str(ROOT),'$ROOT') for v in previous.command(s,work)])
  write_csv(OUT/'development_manifest.csv',specs);shutil.copy2('/tmp/clo-slow-pass/slow_bias_inspection.csv',OUT/'slow_bias_inspection.csv')
  frozen={p:sha(ROOT/p) for p in ['src/v7_3/clo_dsf_revised.c','include/clo_dsf_revised.h','src/v7_3/revised_runtime.c','scripts/run_clo_dsf_slow_bias_development.py','scripts/run_clo_dsf_sensor_response.py','docs/clo_dsf_current.md','results/cross_layer_safety_v7_3_dev/revised.cfg','results/clo_dsf_current/development_manifest.csv']}
  (OUT/'validation_record.md').write_text('# Slow-bias development record\n\nRegistered '+datetime.now(timezone.utc).isoformat()+' before outcomes.900 new cases:600 TRAIN/300 VALIDATION. No parameter search; no drift channel selected. A0 and retained CURRENT are byte-identical; A1 is therefore not a distinct proposed detector. The historical CSV label Revised CLO-DSF denotes retained CURRENT.\n\nScientific/design hashes:\n```json\n'+json.dumps(frozen,indent=2)+'\n```\n\nPre-change core SHA256 '+sha(baseline)+'\n')
  retained={next(s['run_id'] for s in specs if s['origin']==o) for o in [*ORIGINS,'NORMAL']}
  retained.update(next(s['run_id'] for s in specs if s['model']==m) for m in ['sensor_bias_ramp','sensor_interface_intermittent'])
  rows=[]
  for part in ['development-train','development-validation']:
   assert all(sha(ROOT/p)==h for p,h in frozen.items())
   selected=[s for s in specs if s['partition']==part]
   for i,s in enumerate(selected):
    result=c.execute(s,work,s['run_id'] in retained)
    for r in result:r.pop('command_json',None)
    rows+=result
    if (i+1)%50==0:print(part,i+1,'/',len(selected),flush=True)
   previous.report(rows)
   a={r['run_id']:r for r in rows if r['method']=='Revised CLO-DSF'};b={r['run_id']:r for r in rows if r['method']=='Pre-change CLO-DSF'}
   assert all({k:v for k,v in r.items() if k!='method'}=={k:v for k,v in b[n].items() if k!='method'} for n,r in a.items())
   with (OUT/'validation_record.md').open('a') as f:f.write('\n'+part+' complete; all A0/retained rows exactly equal except method name; no tuning.\n')
  assert all(sha(ROOT/p)==h for p,h in frozen.items())
 print('900-case slow-bias development complete',flush=True)
if __name__=='__main__':main()
