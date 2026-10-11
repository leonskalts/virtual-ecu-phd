"""Run only after the complete parity gate; host timing, never WCET."""
import os,sys,ctypes,tarfile,io,json,subprocess
from pathlib import Path
sys.path.insert(0,'/tmp/clo-ml-deps')
import numpy as np
B=Path('/tmp/clo-native-resource');O=Path('results/native_resource_benchmark')
v=json.loads((O/'verification.json').read_text());assert v['passed'] and v['verified_frames']==2161800
assert not (O/'timing.json').exists(),'Do not overwrite measured results'
cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
lib=ctypes.CDLL(str(B/'native.so'));ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');lib.replay.argtypes=[ctypes.c_uint,ptr,ptr,ptr,ptr,ctypes.c_int]
alltimes=[];frames=0
with tarfile.open('results/ieee_origin_rf/runtime_evidence.tar.gz','r|gz') as ar:
 for member in ar:
  with np.load(io.BytesIO(ar.extractfile(member).read())) as z:
   p=np.ascontiguousarray(z['upstream'].T);e=np.ascontiguousarray(np.column_stack([z[k].T for k in ['strength','available','origin_support']]),dtype=float);out=np.empty((len(p),10));tm=np.empty((len(p),5))
   lib.replay(len(p),p,e,out,tm,1);alltimes.append(tm);frames+=len(p)
   if frames%240200==0:print('timed',frames,flush=True)
a=np.concatenate(alltimes);cols={'clover_replayable_upstream':a[:,0],'clover_decision_and_G2':a[:,1],'rf_features':a[:,2],'rf_tree_inference_and_gates':a[:,3],'clover_replayable_pipeline':a[:,4],'rf_features_plus_inference':a[:,2]+a[:,3],'rf_plus_clover_prefusion_arithmetic_sum':a[:,0]+a[:,2]+a[:,3]}
result={'frames':frames,'pinned_cpu':cpu,'clock':'CLOCK_MONOTONIC_RAW','unit':'ns','order':'CLOVER then RF, one sequential pass; no cache flush or real-time isolation; inter-frame Python/archive processing excluded','instrumentation':'Each interval includes clock-call overhead; CLOVER complete interval includes an extra internal boundary clock. RF summed intervals include two intervals. No subtraction. Interrupt/preemption included.','scope':'Replayable observation/provider-output boundary only. Complete producer-to-consumer pipeline NOT measured: records lack raw integrity envelopes, probe transactions and Triplex producer transitions. Shared-upstream figure excludes those stages; do not call it full shared cost.','statistics':{k:dict(zip(['median','p95','p99','maximum'],map(float,np.percentile(x,[50,95,99,100])))) for k,x in cols.items()}}
(O/'timing.json').write_text(json.dumps(result,indent=2))
s=(ctypes.c_ulong*4)();lib.sizes(s)
mem={'clover_state_bytes':s[0],'clover_G2_state_bytes':s[1],'rf_history_state_bytes':s[2],'rf_constant_model_bytes':s[3],'note':'ABI-specific x86_64; excludes common upstream providers, replay I/O and Python buffers; stack compiler reports are per-function, not a measured high-water mark.'}
(O/'memory.json').write_text(json.dumps(mem,indent=2))
(O/'binary_sections.txt').write_text(subprocess.check_output(['size','-A',str(B/'native.so')],text=True))
(O/'stack_usage.txt').write_text(''.join(p.read_text() for p in sorted(B.glob('*.su'))))
print(json.dumps(result,indent=2));print(mem)
