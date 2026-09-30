"""Shared reproducibility utilities and physical templates; no rejected detector."""
import sys,json,hashlib
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'python')]
import run_clo_dsf_final_freeze as base
from virtual_ecu import clo_dsf_current as c
from virtual_ecu.clo_dsf_holdout import prepare_work,profile_identity
from virtual_ecu.clo_dsf_final_reporting import records,wilson
from virtual_ecu.clo_dsf_candidate2_development import aggregate
from virtual_ecu.clo_dsf_current_reporting import runtime_stats
old=SimpleNamespace(OUT=ROOT/'results/clo_dsf_current',prior=base,c=c,prepare_work=prepare_work,profile_identity=profile_identity,records=records,wilson=wilson,aggregate=aggregate,runtime_stats=runtime_stats,write=base.write)
def design():
 t=base.design();out=[]
 for f in range(16):
  for j in range(150):
   s=dict(t[(f%10)*150+j]);i=len(out);load=.355+(f*.127)% .59;speed=21.137+f*5.813;ambient=14.731+f*1.513
   pp=[dict(start_ms=a,end_ms=b,engine_load=(load+j*.000017)*fac,ambient_temp_c=ambient+j*.00131+(1.27 if a>=69100 else 0),vehicle_speed_kph=(speed+j*.0037)*fac,external_airflow_factor=.053 if a>=45700 else 0,road_slope_percent=0) for a,b,fac in [(0,17300,.73),(17300,45700,.96),(45700,69100,.79),(69100,95100,1),(95100,120000,.86)]]
   if (s['origin']=='ACTUATOR' and (j-96)%4==0) or (s['origin']=='NORMAL' and j>=144):
    for p in pp:p.update(engine_load=.0787+f*.00023+j*.0000013,ambient_temp_c=8.783+f*.151,vehicle_speed_kph=70.137+f*.193+j*.0013)
   s.update(run_id=f'binary_{i:04}',profile=f'binary_profile_{i:04}',group=f'binary_family_{f}',partition='TRAIN' if f<8 else 'CALIBRATION' if f<12 else 'VALIDATION',seed=523000021+f*2621+j*127,reference_seed=563000033+f*2393+j*131)
   if s['origin']!='NORMAL':s['start_ms']+=100*(1+(f+j)%9)
   if s['origin']=='SENSOR_CONTROL':s['magnitude']+=.039 if s['magnitude']>0 else -.039
   s['profile_json']=json.dumps(pp,sort_keys=True);s['profile_semantic_sha256']=profile_identity(pp);s.pop('configuration_sha256',None);s.pop('command_json',None);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();out.append(s)
 assert len({s['profile_semantic_sha256'] for s in out})==2400
 return out
