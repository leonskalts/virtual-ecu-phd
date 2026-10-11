"""Observed stack watermark on all retained frames, no new simulations."""
import os,sys,ctypes,tarfile,io,json,subprocess
from pathlib import Path
sys.path.insert(0,'/tmp/clo-ml-deps')
import numpy as np
B=Path('/tmp/clo-native-resource');O=Path('results/native_resource_benchmark');assert json.loads((O/'verification.json').read_text())['passed']
subprocess.run(['gcc','-O2','-fno-fast-math','-ffp-contract=off','-fPIC','-shared','tools/native_resource/stack_watermark.c','-pthread','-o',str(B/'stack.so')],check=True)
lib=ctypes.CDLL(str(B/'native.so'));st=ctypes.CDLL(str(B/'stack.so'));ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');st.watermark.argtypes=[ctypes.c_void_p,ctypes.c_uint,ptr,ptr,ptr,ptr];st.watermark.restype=ctypes.c_ulong
x=np.zeros((1,));idle=st.watermark(None,0,x,x,x,x);peak=0;count=0
with tarfile.open('results/ieee_origin_rf/runtime_evidence.tar.gz','r|gz') as ar:
 for member in ar:
  with np.load(io.BytesIO(ar.extractfile(member).read())) as z:
   p=np.ascontiguousarray(z['upstream'].T);e=np.ascontiguousarray(np.column_stack([z[k].T for k in ['strength','available','origin_support']]),dtype=float);out=np.empty((len(p),10));tm=np.empty((len(p),5));used=st.watermark(ctypes.cast(lib.replay,ctypes.c_void_p),len(p),p,e,out,tm);peak=max(peak,used);count+=len(p)
   assert np.array_equal(out[:,:6],z['rf_probability'].T) and np.array_equal(out[:,8],z['clover_alarm']) and np.array_equal(out[:,9],z['clover_origin'])
   if count%480400==0:print('stack frames',count,flush=True)
result={'frames':count,'combined_observed_stack_high_water_bytes':peak,'empty_pthread_high_water_bytes':idle,'scope':'Complete common replay wrapper plus both sequential methods and pthread/TLS/runtime overhead; NOT separable per-method peaks. No subtraction claimed. Uninstrumented algorithm, external A5 stack watermark, 1 MiB dedicated pthread stack. Observed, not a proven bound.'}
(O/'stack_watermark.json').write_text(json.dumps(result,indent=2));print(result)
