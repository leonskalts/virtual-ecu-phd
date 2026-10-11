"""Separate host ELF payloads; no changes to frozen sources or result files."""
import sys,json,gzip,hashlib,subprocess,shutil,pickle
from pathlib import Path
R=Path.cwd();B=Path('/tmp/clo-native-memory');O=R/'results/native_memory_footprint'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=[p for d in ['src','include','presets','results','tools/native_resource'] for p in (R/d).rglob('*') if p.is_file() and O not in p.parents and '__pycache__' not in str(p)]
if not (O/'preservation.json.gz').exists():
 with gzip.open(O/'preservation.json.gz','wt') as f:json.dump({str(p):sha(p) for p in paths},f)
 (O/'initial_status.txt').write_text(subprocess.check_output(['git','status','--short'],text=True))
# Reuse the exact previously verified hexadecimal export, checking its provenance.
prev=json.loads((R/'results/native_resource_benchmark/build_provenance.json').read_text())
sys.path[:0]=['/tmp/clo-ml-deps',str(R/'python')]
from virtual_ecu import origin_rf as rf
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
assert sha(B/'model.h')==prev['generated_model_sha256']
assign='\n'.join('o.'+x+'=p[%d];'%i for i,x in enumerate(rf.OBS))+'\n'+'\n'.join('o.timing.'+x+'=p[%d];'%(32+i) for i,x in enumerate(rf.TIMING))
(B/'assign.inc').write_text(assign)
(B/'ages.h').write_text('static const int age_columns[]={'+','.join(str(rf.FIELDS.index(x)-1) for x in sorted(rf.TIME_FIELDS))+'};')
core=gzip.decompress((R/'results/native_resource_benchmark/frozen_core.c.gz').read_bytes()).decode();assert hashlib.sha256(core.encode()).hexdigest()==prev['sha256'];(B/'core.inc').write_text(core)
s=(R/'tools/native_resource/replay.c').read_text()
common='#include <math.h>\n#include <stdint.h>\n#include <string.h>\n#include "clo_dsf_revised.h"\n#include "sensor_confirmation.h"\n'
cl=common+s[s.index('double triplex_extra_strength'):s.index('static double history')]
cl+='\nvoid method_reset(void){clo_triplex_core_init(&state);memset(&gate,0,sizeof(gate));}\nvoid method_step(const double*p,const double*e,double*out){(void)e;packet=p;runtime_observation_t o={0};\n#include "assign.inc"\ntriplex_extra_strength=p[55];triplex_extra_ambiguous=p[56];dc_mass=dc_origin=p[66];clo_triplex_core_step(&state,&config,&o);out[0]=alarm;out[1]=origin;}\n'
rf=common+'#include "model.h"\n#include "ages.h"\n'+s[s.index('static double history'):s.index('/* output:')]
rf+='\nvoid method_reset(void){memset(history,0,sizeof(history));memset(availability,0,sizeof(availability));head=0;}\nvoid method_step(const double*p,const double*e,double*out){double x[174];unsigned a,b;feature(p,e,x);infer(x,out,&a,&b);out[6]=a;out[7]=b;}\n'
flags=['-O2','-fno-fast-math','-ffp-contract=off','-fno-pie','-ffunction-sections','-fdata-sections','-fstack-usage','-I'+str(R/'include'),'-I'+str(B)]
commands=[]
def run(cmd):commands.append(cmd);subprocess.run(cmd,check=True,cwd=B)
for method,source in [('clover',cl),('rf',rf)]:
 d=B/method;d.mkdir(exist_ok=True);(d/'method.c').write_text(source)
 srcs=[d/'method.c']
 if method=='clover':srcs += [R/p for p in ['src/v7/ds_evidence.c','src/v7_1/candidate2_evidence.c','src/v7_1/candidate2_observability.c','src/v7_2/clo_dsf_final.c','src/v7_3/sensor_confirmation.c']]
 objs=[]
 for p in srcs:
  obj=d/(p.stem+'.o');run(['gcc',*flags,'-c',str(p),'-o',str(obj)]);objs.append(str(obj))
 # GC selects only production API dependencies. No replay harness in payload.o.
 run(['ld','-r','--gc-sections','-u','method_reset','-u','method_step','-Map='+str(d/'payload.map'),'-o',str(d/'payload.o'),*objs])
 run(['gcc',*flags,'-c',str(R/'tools/native_memory/driver.c'),'-o',str(d/'driver.o')])
 run(['gcc','-no-pie','-Wl,--gc-sections','-Wl,-Map='+str(d/'executable.map'),str(d/'driver.o'),str(d/'payload.o'),'-lm','-o',str(d/'replay')])
 for target in ['payload.o','replay']:
  for tool,args in [('size',['-A']),('readelf',['-SW']),('segments',['-lW']),('nm',['-S','--size-sort'])]:
   cmd=[('readelf' if tool=='segments' else tool),*args,str(d/target)]
   (d/(target+'.'+tool)).write_text(subprocess.check_output(cmd,text=True))
 # Keep compressed linker/inspection evidence only, no duplicated model binary.
 for p in d.iterdir():
  if p.suffix in ['.map','.size','.readelf','.segments','.nm','.su']:
   with gzip.open(O/(method+'_'+p.name+'.gz'),'wb') as f:f.write(p.read_bytes())
(O/'build.json').write_text(json.dumps({'commands':commands,'compiler':subprocess.check_output(['gcc','--version'],text=True),'ld':subprocess.check_output(['ld','--version'],text=True),'model_header_sha256':prev['generated_model_sha256'],'core_sha256':prev['sha256'],'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()},indent=2))
