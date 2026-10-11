"""Full retained-frame parity gate. No timing until this passes."""
import sys,ctypes,tarfile,io,json,time
from pathlib import Path
sys.path.insert(0,'/tmp/clo-ml-deps')
import numpy as np
B=Path('/tmp/clo-native-resource');O=Path('results/native_resource_benchmark')
lib=ctypes.CDLL(str(B/'native.so'));ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');lib.replay.argtypes=[ctypes.c_uint,ptr,ptr,ptr,ptr,ctypes.c_int]
count=0;maxerr=0.;errors=[]
with tarfile.open('results/ieee_origin_rf/runtime_evidence.tar.gz','r|gz') as ar:
 for member in ar:
  with np.load(io.BytesIO(ar.extractfile(member).read())) as z:
   p=np.ascontiguousarray(z['upstream'].T);e=np.ascontiguousarray(np.column_stack([z[k].T for k in ['strength','available','origin_support']]),dtype=float);out=np.empty((len(p),10));tm=np.empty((len(p),5));lib.replay(len(p),p,e,out,tm,0)
   err=np.max(np.abs(out[:,:6]-z['rf_probability'].T));maxerr=max(maxerr,float(err))
   from importlib import import_module
   sys.path.insert(0,'python');rf=import_module('virtual_ecu.origin_rf');ra,ro=rf.decisions(z['rf_probability'].T,.9155568509788313,.7,0)
   checks={'probabilities':np.allclose(out[:,:6],z['rf_probability'].T,rtol=0,atol=1e-14),'rf_alarm':np.array_equal(out[:,6],ra),'rf_origin':np.array_equal(out[:,7],ro),'clover_alarm':np.array_equal(out[:,8],z['clover_alarm']),'clover_origin':np.array_equal(out[:,9],z['clover_origin'])}
   if not all(checks.values()):
    errors.append({'case':member.name,'checks':checks,'max_probability_error':float(err),'first_clover_mismatches':np.flatnonzero(out[:,8]!=z['clover_alarm'])[:10].tolist()});break
   count+=len(p)
   if count%120100==0:print('verified',count,flush=True)
result={'passed':not errors and count==2161800,'verified_frames':count,'probability_absolute_tolerance':1e-14,'max_probability_error':maxerr,'errors':errors}
(O/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if errors:sys.exit(1)
