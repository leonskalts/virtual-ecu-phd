"""Export frozen RF and assemble an isolated, semantics-preserving replay build."""
import sys,pickle,json,hashlib,subprocess,gzip
from pathlib import Path
sys.path[:0]=['/tmp/clo-ml-deps','python']
from virtual_ecu import origin_rf as rf
R=Path.cwd();B=Path('/tmp/clo-native-resource');O=R/'results/native_resource_benchmark'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if not (O/'preservation.json').exists() and not (O/'preservation.json.gz').exists():
 paths=[p for root in ['src','include','presets','results','docs','rtl'] for p in (R/root).rglob('*') if p.is_file() and O not in p.parents and '__pycache__' not in str(p)]
 (O/'preservation.json').write_text(json.dumps({str(p):sha(p) for p in paths},indent=2))
 (O/'initial_status.txt').write_text(subprocess.check_output(['git','status','--short'],text=True))
m=pickle.loads((R/'results/ieee_origin_rf/rf_model.pkl').read_bytes())
with (B/'model.h').open('w') as f:
 f.write('typedef struct {int left,right,feature; double threshold,p[6];} Node;\nstatic const Node nodes[]={\n')
 offsets=[];offset=0
 for est in m.estimators_:
  t=est.tree_;offsets.append(offset)
  for i in range(t.node_count):
   f.write('{%d,%d,%d,%s,{%s}},\n'%(t.children_left[i]+offset if t.children_left[i]>=0 else -1,t.children_right[i]+offset if t.children_right[i]>=0 else -1,t.feature[i],float(t.threshold[i]).hex(),','.join(float(v).hex() for v in t.value[i,0])))
  offset+=t.node_count
 f.write('};\nstatic const int roots[]={'+','.join(map(str,offsets))+'};\n')
frozen=Path('/tmp/clo-integrity-final-unseen/work/extended.c')
s=frozen.read_text() if frozen.exists() else gzip.decompress((O/'frozen_core.c.gz').read_bytes()).decode()
core_hash=hashlib.sha256(s.encode()).hexdigest()
# Hooks measure the existing boundary; no numerical or control-flow changes.
s=s.replace('    unsigned int direct=0, direct_count=0;','    native_boundary();\n    unsigned int direct=0, direct_count=0;')
(B/'core.inc').write_text(s)
assign='\n'.join('o.'+x+'=p[%d];'%i for i,x in enumerate(rf.OBS))+'\n'+'\n'.join('o.timing.'+x+'=p[%d];'%(32+i) for i,x in enumerate(rf.TIMING))
(B/'assign.inc').write_text(assign)
(B/'ages.h').write_text('static const int age_columns[]={'+','.join(str(rf.FIELDS.index(x)-1) for x in sorted(rf.TIME_FIELDS))+'};')
(O/'build_provenance.json').write_text(json.dumps({'frozen_core':str(frozen),'sha256':core_hash,'model_sha256':sha(R/'results/ieee_origin_rf/rf_model.pkl'),'generated_model_sha256':sha(B/'model.h'),'compiler':'gcc -O2 -fno-fast-math -ffp-contract=off -fPIC -fstack-usage','nodes':offset,'trees':len(offsets)},indent=2))
cmd=['gcc','-O2','-fno-fast-math','-ffp-contract=off','-fPIC','-fstack-usage','-shared','-Iinclude','-I'+str(B),'tools/native_resource/replay.c','src/v7/ds_evidence.c','src/v7/clo_observability.c','src/v7_1/candidate2_evidence.c','src/v7_1/candidate2_observability.c','src/v7_2/clo_dsf_final.c','src/v7_3/sensor_confirmation.c','-lm','-o',str(B/'native.so')]
subprocess.run(cmd,check=True)
