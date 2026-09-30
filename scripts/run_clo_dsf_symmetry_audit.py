#!/usr/bin/env python3
"""New development/validation verification of unchanged triplex, no tuning."""
import sys,json,hashlib,csv,subprocess,inspect
from pathlib import Path
import run_clo_dsf_triplex as t
B=Path('/tmp/clo-triplex-symmetry');O=t.OUT
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def design(families,partition):
 base=t.prior.design();cbase=t.design();out=[]
 for f in families:
  for j in range(150):
   s=dict(base[f*150+j]);c=cbase[f*150+j]
   for key in ['c_offset','c_gain','c_noise','c_quantum','c_adc_gain','c_phase_ms','c_lag_ms']:s[key]=c[key]
   s.update(domain='NONE',kind='none',c_seed=811000031+f*3313+j*163,run_id=f'symmetry_{f:02}_{j:03}',profile=f'symmetry_profile_{f:02}_{j:03}',group=f'symmetry_family_{f}',partition=partition,seed=823000019+f*3371+j*167,reference_seed=827000029+f*3391+j*173)
   pp=json.loads(s['profile_json'])
   for p in pp:p['ambient_temp_c']+=.283+j*.000023;p['engine_load']*=.991;p['vehicle_speed_kph']+=.719+j*.000031
   if s['origin']!='NORMAL':s['start_ms']+=100*(1+(f+j)%6)
   if 72<=j<96:
    k=j-72;domain=['A','B','AB'][k//8];cell=k%8;kind=['ramp','step','pulse'][(cell+f+k//8)%3]
    magnitude=(-1 if (cell+f)%2 else 1)*(2.61+f*.017 if kind=='ramp' else .66+f*.004 if cell%2 else .98+f*.004)
    duration=[100,300,700,1100][(f+cell)%4] if kind=='pulse' else 0
    s.update(origin='SENSOR_CONTROL',domain=domain,kind=kind,sensor_chain=domain,model={'ramp':'sensor_bias_ramp','step':'sensor_bias','pulse':'sensor_interface_intermittent'}[kind],behavior='transient' if duration else 'permanent',magnitude=magnitude,duration_ms=duration,sensor_ramp_rise_ms=[19700,38300,61900,82300][(f+cell)%4] if kind=='ramp' else 0,start_ms=22700+(f%4)*700+cell*300,initially_latent_stuck=0,target_updates_json='[]',workload='triplex_fault')
   s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=t.h.profile_identity(pp);s.pop('configuration_sha256',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();out.append(s)
 return out

def setup():
 assert not B.exists();B.mkdir()
 paths=[p for root in ['src','include'] for p in Path(root).rglob('*') if p.is_file()]+[Path('presets/gui_session_state.json')]
 (B/'initial.json').write_text(json.dumps({str(p):sha(p) for p in paths},indent=2))
 ss=design([0],'TRAIN')+design([4],'CALIBRATION');(B/'specs.json').write_text(json.dumps(ss));t.write(O/'symmetry_development_manifest.csv',ss)
 (O/'symmetry_protocol.md').write_text('''# Preregistered symmetry audit verification
No algorithm fix selected after code audit and permutation tests. No tuning or parameter selection. TRAIN150 family0; CALIBRATION150 family4. Freeze sources before generating VALIDATION600 families12–15:96 each of five original fault origins plus120 benign. Sensor A/B/AB32 each; ramp/step/pulse32 each. Balanced signs, short/long pulses, fixed new magnitudes/rates/seeds/profiles. Full actuator templates retain cold initially-unexcited cases. Original space only; no C fault expansion. Runtime inference unchanged. No latch or unseen.\n\nA0/A1 same observations. Report all outcomes; no exclusions/retries/tuning after validation. Retain only >=91% original, benign<=1%, zero wrong origins, plant>=95%, AB>=90%, no paired timing/communication/effective-memory losses. Full regression only if retained. Historic summaries/manifests remain unchanged. Raw per-run data deleted; no new representative traces planned.\n''')

def freeze():
 assert (B/'TRAIN_complete').exists() and (B/'CALIBRATION_complete').exists() and not (B/'lock.json').exists()
 initial=json.loads((B/'initial.json').read_text());assert all(sha(p)==v for p,v in initial.items())
 files={**initial,str(Path(__file__).resolve()):sha(__file__),str(O/'symmetry_protocol.md'):sha(O/'symmetry_protocol.md'),str(Path(t.__file__).resolve()):sha(t.__file__)}
 # Freeze implementation first; only then create untouched validation cases.
 (B/'lock.json').write_text(json.dumps({'files':files},indent=2))
 ss=json.loads((B/'specs.json').read_text())+design([12,13,14,15],'VALIDATION');val=ss[300:]
 assert len(val)==600 and all(sum(s['origin']==o for s in val)==96 for o in t.h.prior.ORIGINS)
 old=json.loads(Path('/tmp/clo-triplex-latch/specs.json').read_text());assert not {s['profile_semantic_sha256'] for s in ss}&{s['profile_semantic_sha256'] for s in old}
 (B/'specs.json').write_text(json.dumps(ss));t.write(O/'symmetry_validation_manifest.csv',val)
 lock=json.loads((B/'lock.json').read_text());lock['files'][str(O/'symmetry_validation_manifest.csv')]=sha(O/'symmetry_validation_manifest.csv');lock['files'][str(B/'specs.json')]=sha(B/'specs.json');(B/'lock.json').write_text(json.dumps(lock,indent=2));(O/'symmetry_lock.json').write_text(json.dumps(lock,indent=2))
 print('Frozen; 600 new validation cases registered.',flush=True)
if __name__=='__main__':
 if sys.argv[1]=='setup':setup()
 elif sys.argv[1]=='freeze':freeze()
 elif sys.argv[1]=='run':t.B=B;t.run(sys.argv[2])
