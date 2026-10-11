"""RF B: reconstruct the identical pre-fusion providers, never CLOVER predictions."""
import re,subprocess,gzip,json
from pathlib import Path
R=Path.cwd();B=Path('/tmp/clo-native-memory');O=R/'results/native_memory_footprint';d=B/'rf_pipeline';d.mkdir(exist_ok=True)
core=(B/'core.inc').read_text();start=core.index('void clo_triplex_core_step(');cut=core.index('    /* Establish precedence',start)
prefix=core[:start]+core[start:cut].replace('void clo_triplex_core_step(','void shared_provider_step(')
prefix+='''
 unsigned subsets[6]={2,4,1,12,16,31};
 for(unsigned i=0;i<6;i++){
  bool available=s->evidence.available[i];
  if(i==3){if(state->slew_qualification_count<5 && origin_local<=0 && s->evidence.strength[i]<=local)available=false;if(origin_local>0)subsets[i]=8;}
  shared_e[i]=s->evidence.strength[i];shared_e[6+i]=available;shared_e[12+i]=subsets[i];
 }
}
'''
# Remove declarations of observer callbacks (unused); retain all provider arithmetic verbatim.
prefix=prefix.replace('void ba_capture(const clo_revised_t *,const runtime_observation_t *,double);','').replace('void benchmark_capture(unsigned,const clo_revised_t *,const runtime_observation_t *,double,double);','')
rf=(B/'rf/method.c').read_text();rf=rf.replace('void method_reset(void)','static void rf_reset(void)').replace('void method_step(const double*p,const double*e,double*out)','static void rf_step(const double*p,const double*e,double*out)')
source='''#include <stdbool.h>
double triplex_extra_strength,dc_mass,dc_origin,dc_discount,ba_provider[7];
bool triplex_extra_ambiguous;
static double shared_e[18];
'''+prefix+'\n'+rf+'''
static clo_revised_t provider_state;
static const clo_final_config_t provider_config={1,.8,.35,.5,.55,.15,.5,1};
void method_reset(void){clo_triplex_core_init(&provider_state);rf_reset();}
void method_step(const double*p,const double*unused,double*out){(void)unused;runtime_observation_t o={0};
#include "assign.inc"
triplex_extra_strength=p[55];triplex_extra_ambiguous=p[56];dc_mass=dc_origin=p[66];
shared_provider_step(&provider_state,&provider_config,&o);rf_step(p,shared_e,out);}
'''
(d/'method.c').write_text(source)
flags=['-O2','-fno-fast-math','-ffp-contract=off','-fno-pie','-ffunction-sections','-fdata-sections','-fstack-usage','-I'+str(R/'include'),'-I'+str(B)]
cmds=[]
def run(cmd):cmds.append(cmd);subprocess.run(cmd,check=True,cwd=B)
objs=[]
for p in [d/'method.c',R/'src/v7_1/candidate2_evidence.c',R/'src/v7_2/clo_dsf_final.c',R/'src/v7/ds_evidence.c']:
 obj=d/(p.stem+'.o');run(['gcc',*flags,'-c',str(p),'-o',str(obj)]);objs.append(str(obj))
run(['ld','-r','--gc-sections','-u','method_reset','-u','method_step','-Map='+str(d/'payload.map'),'-o',str(d/'payload.o'),*objs])
run(['gcc','-no-pie','-Wl,--gc-sections','-Wl,-Map='+str(d/'executable.map'),str(B/'rf/driver.o'),str(d/'payload.o'),'-lm','-o',str(d/'replay')])
for target in ['payload.o','replay']:
 for tool,args in [('size',['-A']),('readelf',['-SW']),('segments',['-lW']),('nm',['-S','--size-sort'])]:
  (d/(target+'.'+tool)).write_text(subprocess.check_output([('readelf' if tool=='segments' else tool),*args,str(d/target)],text=True))
for p in d.iterdir():
 if p.suffix in ['.map','.size','.readelf','.segments','.nm','.su']:
  with gzip.open(O/('rf_pipeline_'+p.name+'.gz'),'wb') as f:f.write(p.read_bytes())
(O/'pipeline_build.json').write_text(json.dumps({'commands':cmds,'definition':'RF plus exact frozen pre-fusion provider prefix and availability/support mapping. No DS decision/prediction fed to RF. Upstream integrity/Triplex/M2 transaction engines excluded identically to CLOVER replay.'},indent=2))
