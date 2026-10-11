"""Verify separate executable outputs and observe per-method touched stack."""
import sys,subprocess,tarfile,io,json,struct,hashlib
from pathlib import Path
sys.path[:0]=['/tmp/clo-ml-deps','python']
import numpy as np
from virtual_ecu.origin_rf import decisions
B=Path('/tmp/clo-native-memory');O=Path('results/native_memory_footprint')
methods=sys.argv[1:] or ['clover','rf']
for m in methods:
 subprocess.run(['gcc','-O2','-fno-fast-math','-ffp-contract=off','-fno-pie','-no-pie','-Wl,--gc-sections','tools/native_memory/stack_driver.c','tools/native_memory/stack_call.S',str(B/m/'payload.o'),'-lm','-o',str(B/m/'stack_replay')],check=True)
# One normal separately linked executable plus one external-stack executable per method.
procs={(m,mode):subprocess.Popen([str(B/m/mode)],stdin=subprocess.PIPE,stdout=subprocess.PIPE) for m in methods for mode in ['replay','stack_replay']}
peak={m:0 for m in methods};frames=0;maxerr=0
try:
 with tarfile.open('results/ieee_origin_rf/runtime_evidence.tar.gz','r|gz') as ar:
  for member in ar:
   with np.load(io.BytesIO(ar.extractfile(member).read())) as z:
    p=z['upstream'].T;e=np.column_stack([z[k].T for k in ['strength','available','origin_support']]);data=np.ascontiguousarray(np.column_stack([p,e]),dtype='<f8');n=len(data);ra,ro=decisions(z['rf_probability'].T,.9155568509788313,.7,0)
    for (m,mode),proc in procs.items():
     proc.stdin.write(struct.pack('<I',n));proc.stdin.write(data.tobytes());proc.stdin.flush()
     raw=proc.stdout.read(n*8*8);assert len(raw)==n*64,(m,mode,proc.poll());out=np.frombuffer(raw,dtype='<f8').reshape(n,8)
     if m=='clover':assert np.array_equal(out[:,0],z['clover_alarm']) and np.array_equal(out[:,1],z['clover_origin']),(m,mode,member.name)
     else:
      err=float(np.max(abs(out[:,:6]-z['rf_probability'].T)));maxerr=max(maxerr,err)
      assert err==0 and np.array_equal(out[:,6],ra) and np.array_equal(out[:,7],ro),(m,mode,member.name,err)
     if mode=='stack_replay':peak[m]=max(peak[m],struct.unpack('<Q',proc.stdout.read(8))[0])
    frames+=n
    if frames%240200==0:print('verified separate ELFs / stack',frames,flush=True)
 result={'passed':frames==2161800,'frames_per_executable':frames,'executables':len(procs),'probability_max_absolute_error':maxerr,'alarm_origin_mismatches':0,'observed_touched_stack_bytes':peak,'stack_scope':'Per-method method_step call on dedicated 1MiB x86-64 SysV stack; includes return address and called libc/libm, excludes replay worker/pthread. Dynamic binding warmed, method state reset before full case. A5 watermark detects writes, not untouched reservations; not proven WCET/stack bound. Reset stack not measured dynamically; compiler .su retained. No state/stack double counting.'}
 (O/('verification_'+ '_'.join(methods)+'.json')).write_text(json.dumps(result,indent=2));print(result)
except BaseException as ex:
 (O/('verification_failure_'+ '_'.join(methods)+'.json')).write_text(json.dumps({'error':repr(ex),'frames':frames}));raise
finally:
 for proc in procs.values():
  proc.stdin.close();proc.wait()
