#!/usr/bin/env python3
"""One in-place, group-separated integrity/event development experiment.

Temporary ablation builds only; no hidden labels in runtime inference. Reproduce
against the baseline and experimental hashes recorded in validation_record.md.
"""
import csv,hashlib,json,subprocess,sys,tempfile,difflib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'python'),str(ROOT/'scripts')]
from virtual_ecu import clo_dsf_current as c
from virtual_ecu.clo_dsf_holdout import prepare_work,profile_identity
from virtual_ecu.clo_dsf_development import write_csv,sha,ORIGINS
from virtual_ecu.clo_dsf_candidate2_development import aggregate
from virtual_ecu.clo_dsf_current_reporting import runtime_stats
import run_clo_dsf_sensor_response as response
OUT=c.OUT;BASE=Path('/tmp/clo-event90')
METHODS=['Pre-change CLO-DSF','Memory only','Event only','Revised CLO-DSF','Weighted Sum']

def design():
 specs=[];bs=['transient','intermittent','permanent']
 for f in range(10):
  cells=[]
  for bit in [(f+k)%5 for k in range(4)]:
   for polarity in [0,1]:
    for b in [bs[f%3],bs[(f+1)%3]]:cells.append(('MEMORY','stuck_bit',b,bit,polarity,0))
  for k in range(4):cells.append(('MEMORY','bit_flip',bs[(k+f)%3],(k+f)%5,0,0))
  for k in range(20):cells.append(('TIMING','deadline_miss' if k<8 else 'task_delay',bs[(k+f)%3],0 if k<8 else [300,500,900,1200][k%4],0,0))
  for k in range(20):
   m=['delayed_update','dropped_update','replayed_sample'][k%3];mag={'delayed_update':[100,700],'dropped_update':[1,5],'replayed_sample':[100,1500]}[m][(k//3)%2]
   cells.append(('COMMUNICATION',m,bs[(k//6+f)%3],mag,0,0))
  for mag in [-1.25,1.25,-2.85,2.85]:
   for rise in [11000,37000]:cells.append(('SENSOR_CONTROL','sensor_bias_ramp','permanent',mag,0,rise))
  for mag in [-round(.81+.023*f,4),round(.81+.023*f,4)]:
   for b in bs:cells.append(('SENSOR_CONTROL','sensor_bias',b,mag,0,0))
  for mag in [round(.36+.013*f,4),round(1.75+.019*f,4)]:
   for b in bs:cells.append(('SENSOR_CONTROL','sensor_interface_intermittent',b,mag,0,0))
  for k in range(20):cells.append(('ACTUATOR','pump_degraded' if k<15 else 'fan_stuck_off',bs[(k+f)%3],[.991,.977,.941,.823,.681][k%5] if k<15 else 0,0,0))
  cells += [('NORMAL','baseline','none',0,0,0)]*20
  for j,(origin,model,b,mag,polarity,rise) in enumerate(cells):
   profile=[dict(start_ms=a,end_ms=z,vehicle_speed_kph=(15.7+9.2*f+j*.0023)*fac,engine_load=([.39,.51,.62,.74,.85,.95,.46,.67,.81,.97][f]+j*.000017)*fac,ambient_temp_c=21.3+1.8*f+j*.0029+(1.6 if a>=66300 else 0),external_airflow_factor=0,road_slope_percent=0) for a,z,fac in [(0,18700,.68),(18700,33900,.96),(33900,52100,.78),(52100,66300,1),(66300,88700,.61),(88700,120000,.89)]]
   updates=[[36700,103],[74900,92]] if (j+f)%2 else []
   duration=0 if b in ['permanent','none'] else 100 if model=='deadline_miss' and b=='transient' else [200,800,1700,4700][(j+f)%4] if origin=='SENSOR_CONTROL' else [300,900,3700,15100][(j+f)%4] if origin=='COMMUNICATION' else [8700,13900,19300][(j+f)%3]
   variation=['0:0:11800','0.023:0:11800','0.061:0:15400','0.097:0:19800','0.037:1.5:17800','0.083:2.3:24200'][(j-100)%6] if origin=='NORMAL' else '0:0:11800'
   s=dict(run_id=f'event90_{len(specs):04}',origin=origin,model=model,behavior=b,magnitude=mag,stuck_polarity=polarity,start_ms=120100 if origin=='NORMAL' else 25100+(j%11)*400+f*100,duration_ms=duration,group=f'event90_family_{f}',partition='development-train' if f<6 else 'development-validation',profile=f'event90_profile_{len(specs):04}',profile_json=json.dumps(profile,sort_keys=True),target_updates_json=json.dumps(updates),workload='authorized_updates' if updates else 'static_target',seed=910009+f*1013+j*23,simulation_duration_ms=120000,sensor_variation=variation,sensor_ramp_rise_ms=rise,initially_latent_stuck=int(model=='stuck_bit' and ((92>>int(mag))&1)==polarity))
   s['profile_semantic_sha256']=profile_identity(profile);s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();specs.append(s)
 assert len(specs)==1200 and all(sum(s['origin']==o for s in specs)==200 for o in ORIGINS)
 assert len({s['profile_semantic_sha256'] for s in specs})==1200
 return specs

# Rejected experimental channels are reconstructed ONLY in temporary storage.
# The production CURRENT detector is unchanged after the failed validation gate.
EXPERIMENTAL_CHANNELS = r'''/* Passive encoded checkword, refreshed only from the authorized target shadow.
 * This checks stored contents even when control has not consumed them. It cannot
 * distinguish a stuck cell whose current contents equal its intended value. */
static double memory_integrity(clo_revised_t *s,const runtime_observation_t *o)
{
    if(!o->target_shadow_valid){s->integrity_valid=false;return 0;}
    if(!s->integrity_valid || s->integrity_shadow!=o->target_shadow_c) {
        s->integrity_shadow=o->target_shadow_c;
        s->integrity_checkword=(~o->target_shadow_c)&65535U;
        s->integrity_valid=true;
    }
    return o->target_register_c>65535U ||
        (o->target_register_c^s->integrity_checkword)!=65535U ? 1.0:0.0;
}

/* Signed short-window event integral. Use the same +/-0.10 C uncertainty,
 * 3 C/s^2 curvature allowance, 300 ms horizon and 2 C evidence scale as the
 * existing response envelope. Freeze the pre-event slope on the first abrupt
 * envelope violation; sum at most three same-sign excesses. Sign reversal,
 * recovery, missing samples and context changes clear the statistic. This is
 * one correlated sensor feature, max-merged, never another DS source. */
static double sensor_event(clo_revised_t *s,const runtime_observation_t *o)
{
    bool valid=s->response_count==5 && o->source_valid && o->source_previous_valid &&
        o->source_ms==o->time_ms && o->source_ms==s->response_last_ms+ECU_SENSOR_PERIOD_MS &&
        o->source_previous_ms==s->response_last_ms &&
        o->source_previous_c==s->response_history[4] && isfinite(o->source_c) &&
        o->engine_load==s->response_load && o->vehicle_speed_kph==s->response_speed &&
        o->ambient_c==s->response_ambient && o->control_target_c==s->response_target &&
        o->fan_actual==s->response_fan;
    if(!valid){s->event_active=false;s->event_sum=0;s->event_count=0;return 0;}
    if(!s->event_active) {
        s->event_anchor_ms=s->response_last_ms;s->event_anchor=s->response_history[4];
        s->event_slope=(s->response_history[4]-s->response_history[0])/
            (4.0*ECU_SENSOR_PERIOD_MS/1000.0);
        s->event_sum=0;s->event_count=0;s->event_sign=0;
    }
    double h=(o->source_ms-s->event_anchor_ms)/1000.0;
    double residual=o->source_c-s->event_anchor-s->event_slope*h;
    double excess=fabs(residual)-(.20+.50*h+1.50*h*h);
    int sign=residual>0?1:-1;
    if(h>.300001 || excess<=0 || (s->event_count && sign!=s->event_sign)) {
        s->event_active=false;s->event_sum=0;s->event_count=0;return 0;
    }
    s->event_active=true;s->event_sign=sign;s->event_count++;
    s->event_sum=fmin(2.0,s->event_sum+excess);
    double strength=s->event_count>=2?s->event_sum/2.0:0;
    if(h>=.299999)s->event_active=false;
    return strength;
}

'''
EXPERIMENTAL_FIELDS = '''    /* Bounded event evidence, sharing the trusted pre-event acquisition history. */
    double event_anchor, event_slope, event_sum;
    unsigned int event_anchor_ms, event_count;
    int event_sign;
    bool event_active;
    unsigned int integrity_shadow, integrity_checkword;
    bool integrity_valid;
'''

def experimental_sources(baseline,header):
 combined=baseline.replace('#include <string.h>',EXPERIMENTAL_CHANNELS+'#include <string.h>')
 combined=combined.replace('    clo_revised_extract(&s->evidence,o);','    clo_revised_extract(&s->evidence,o);\n    s->evidence.strength[2]=fmax(s->evidence.strength[2],memory_integrity(state,o));')
 combined=combined.replace('    local=fmax(local,sensor_response(state,o));','    local=fmax(local,sensor_event(state,o));\n    local=fmax(local,sensor_response(state,o));')
 return combined,header.replace('} clo_revised_t;',EXPERIMENTAL_FIELDS+'} clo_revised_t;')

def build(work):
 baseline=(BASE/'baseline.c').read_text();combined,header=experimental_sources(baseline,(BASE/'baseline.h').read_text())
 (work/'clo_dsf_revised.h').write_text(header)

 variants={'a0':baseline,'a1':combined.replace('    local=fmax(local,sensor_event(state,o));',''),'a2':combined.replace('    s->evidence.strength[2]=fmax(s->evidence.strength[2],memory_integrity(state,o));','')}
 objects=[]
 for name,source in variants.items():
  for fn in ['clo_revised_init','clo_revised_extract','clo_revised_step']:source=source.replace(fn,fn.replace('clo_revised',{'a0':'clo_prechange','a1':'clo_memory_only','a2':'clo_event_only'}[name]))
  p=work/(name+'.c');p.write_text(source);obj=p.with_suffix('.o');subprocess.run(['gcc','-std=c11','-O2','-I'+str(work),'-Iinclude','-c',str(p),'-o',str(obj)],cwd=ROOT,check=True);objects.append(str(obj))
 adapter=(ROOT/'src/v7_3/revised_runtime.c').read_text().replace('static clo_revised_t prechange;','static clo_revised_t prechange,memory_only,event_only;\nvoid clo_memory_only_step(clo_revised_t *,const clo_final_config_t *,const runtime_observation_t *);\nvoid clo_event_only_step(clo_revised_t *,const clo_final_config_t *,const runtime_observation_t *);')
 adapter=adapter.replace('clo_final_step(&previous,&config,&o);final_score(2,o.time_ms,&previous.output);','clo_final_step(&previous,&config,&o);clo_memory_only_step(&memory_only,&config,&o);final_score(2,o.time_ms,&memory_only.fusion.output);')
 adapter=adapter.replace('clo_dsf_step(&plain,&plain_config,CLO_PLAIN,&o);old_score(3,o.time_ms,&plain);','clo_event_only_step(&event_only,&config,&o);final_score(3,o.time_ms,&event_only.fusion.output);')
 adapter=adapter.replace('clo_revised_init(&prechange);','names[2]="Memory only";names[3]="Event only";clo_revised_init(&memory_only);clo_revised_init(&event_only);clo_revised_init(&prechange);')
 p=work/'adapter.c';p.write_text(adapter);obj=p.with_suffix('.o');subprocess.run(['gcc','-std=c11','-O2','-I'+str(work),'-Iinclude','-c',str(p),'-o',str(obj)],cwd=ROOT,check=True);objects.append(str(obj))
 objects += [str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o']
 p=work/'combined.c';p.write_text(combined);obj=p.with_suffix('.o');subprocess.run(['gcc','-std=c11','-O2','-I'+str(work),'-Iinclude','-c',str(p),'-o',str(obj)],cwd=ROOT,check=True);objects.append(str(obj))
 objects += [str(ROOT/p) for p in ['src/v7/ds_evidence.o','src/v7/clo_observability.o','src/v7/clo_dsf.o','src/v7/accepted_main.o','src/v7_1/candidate2_evidence.o','src/v7_1/candidate2_observability.o','src/v7_1/clo_dsf_candidate2.o','src/v7_2/clo_dsf_final.o','src/v7_2/final_observation_io.o']]
 exe=work/'ablation_ecu';subprocess.run(['gcc',*objects,'-Wl,--wrap=detection_algorithm_step','-Wl,--wrap=cross_layer_fault_step','-Wl,--wrap=sensors_step','-lm','-o',str(exe)],check=True);return exe

def report(rows):
 ablation=[];memory=[];events=[];local=[];conf=[];paired=[]
 for part in ['development-train','development-validation']:
  a={r['run_id']:r for r in rows if r['partition']==part and r['method']=='Pre-change CLO-DSF'}
  for m in METHODS:
   rs=[r for r in rows if r['partition']==part and r['method']==m]
   if not rs:continue
   for origin in ['ALL',*ORIGINS]:
    ss=[r for r in rs if origin=='ALL' or r['origin']==origin];ablation.append(dict(partition=part,method=m,group=origin,**aggregate(ss)))
    if m!='Weighted Sum':
     local.append(dict(partition=part,method=m,group=origin,first_localized=sum(r['detected'] and r['origin_at_alarm']!='UNKNOWN' for r in ss),first_correct=sum(r['localized_correct'] for r in ss),**runtime_stats(ss)))
     conf.append(dict(partition=part,method=m,origin=origin,**{o:sum(r['alarm_'+o] for r in ss) for o in ['UNKNOWN',*ORIGINS]}))
   for label,ss in {'effective_stuck':[r for r in rs if r['model']=='stuck_bit' and r['effective_memory_corruption']], 'effective_memory':[r for r in rs if r['origin']=='MEMORY' and r['effective_memory_corruption']], 'dormant_stuck':[r for r in rs if r['model']=='stuck_bit' and not r['effective_memory_corruption']], 'legal_updates':[r for r in rs if not r['injected'] and r['workload']=='authorized_updates']}.items():memory.append(dict(partition=part,method=m,group=label,**aggregate(ss)))
   for label,ss in {'weak_steps':[r for r in rs if r['model']=='sensor_bias'],'pulses':[r for r in rs if r['model']=='sensor_interface_intermittent'],'slow_drift':[r for r in rs if r['model']=='sensor_bias_ramp'],'positive':[r for r in rs if r['origin']=='SENSOR_CONTROL' and r['magnitude']>0],'negative':[r for r in rs if r['origin']=='SENSOR_CONTROL' and r['magnitude']<0],'low_magnitude':[r for r in rs if r['origin']=='SENSOR_CONTROL' and abs(r['magnitude'])<=1.1],'medium_magnitude':[r for r in rs if r['origin']=='SENSOR_CONTROL' and abs(r['magnitude'])>1.1]}.items():events.append(dict(partition=part,method=m,group=label,**aggregate(ss)))
   if m!='Pre-change CLO-DSF':
    rr=[r for r in rs if r['injected']];paired.append(dict(partition=part,method=m,both=sum(r['detected'] and a[r['run_id']]['detected'] for r in rr),only_new=sum(r['detected'] and not a[r['run_id']]['detected'] for r in rr),only_a0=sum(not r['detected'] and a[r['run_id']]['detected'] for r in rr),neither=sum(not r['detected'] and not a[r['run_id']]['detected'] for r in rr)))
 for name,data in [('ablation_summary.csv',ablation),('memory_integrity_summary.csv',memory),('event_detection_summary.csv',events),('localization_summary.csv',local),('confusion_summary.csv',conf),('baseline_comparison.csv',paired),('case_summary.csv',rows)]:write_csv(OUT/name,data)

def main():
 if (OUT/'campaign_manifest.csv').exists():
  with (OUT/'campaign_manifest.csv').open() as f:
   if any(r.get('run_id','').startswith('event90_') for r in csv.DictReader(f)):
    raise SystemExit('This development campaign is complete; refuse accidental rerun/replacement.')
 specs=design();prior=set()
 for folder in [ROOT/'results',BASE]:
  for p in folder.rglob('*manifest.csv'):
   with p.open() as f:
    for r in csv.DictReader(f):
     if r.get('profile_semantic_sha256'):prior.add(r['profile_semantic_sha256'])
 assert not prior & {s['profile_semantic_sha256'] for s in specs}
 assert not {s['group'] for s in specs if s['partition']=='development-train'}&{s['group'] for s in specs if s['partition']=='development-validation'}
 subprocess.run(['make','-B','-f','clo_dsf_revised.mk','-j4'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
 with tempfile.TemporaryDirectory(prefix='clo-event90-ablation-') as tmp:
  w=Path(tmp);prepare_work(w,specs);exe=build(w)
  def command(s,work):return [str(exe),*response.command(s,work)[1:]]
  c.command=command;c.METHODS=METHODS
  objects=[str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o'];check=w/'check';subprocess.run(['gcc','-std=c11','-Iinclude','tests/holdout_configuration_check.c',*objects,'-o',str(check)],cwd=ROOT,check=True)
  for s in specs:
   cmd=command(s,w);v=subprocess.run([str(check),*cmd[2:]],capture_output=True,text=True);assert not v.returncode,(s['run_id'],v.stderr)
   s['command_json']=json.dumps([x.replace(str(w),'$WORK').replace(str(ROOT),'$ROOT') for x in cmd])
  assert all(p.is_file() for p in OUT.iterdir())
  for p in OUT.iterdir():p.unlink()
  write_csv(OUT/'campaign_manifest.csv',specs)
  frozen={p:sha(ROOT/p) for p in ['src/v7_3/clo_dsf_revised.c','include/clo_dsf_revised.h','src/v7_3/revised_runtime.c','scripts/run_clo_dsf_integrity_event.py','results/cross_layer_safety_v7_3_dev/revised.cfg','results/clo_dsf_current/campaign_manifest.csv']}
  patch=''.join(difflib.unified_diff((BASE/'baseline.c').read_text().splitlines(True),experimental_sources((BASE/'baseline.c').read_text(),(BASE/'baseline.h').read_text())[0].splitlines(True),fromfile='baseline.c',tofile='experimental.c'))
  (OUT/'validation_record.md').write_text('# Integrity/event development record\n\nRegistered '+datetime.now(timezone.utc).isoformat()+' before outcomes. Baseline '+(BASE/'head').read_text().strip()+'.\n\n1200 unique new simulations:720 TRAIN (600 faults/120 benign),480 VALIDATION (400 faults/80 benign). Six versus four disjoint operating families, all new profiles. 200 faults per origin and200 benign total. Prior known holdout used only as development evidence, never as a new unseen evaluation. No final holdout run. Full commands and profiles in manifest.\n\nA0 baseline CURRENT, A1 passive periodic encoded memory checkword only, A2 short-window event integral only, A3 both, frozen Weighted Sum choice6. One physics run per case, observer-only ablations built temporarily, no maintained candidate tree. Independent scientific code never sees labels.\n\nMemory: bitwise-complement checkword refreshed from trusted shadow changed only by legitimate commit path; checked every acquisition/monitor tick, without relying on control execution. This is mathematically redundant for value-equal dormant stuck cells under the existing storage model. No active bit challenges or changed injector semantics. Effective/dormant classification strictly offline.\n\nEvent: pre-event5-sample slope, fixed300ms horizon; existing uncertainty bound0.20+0.50h+1.50h^2C; sum same-sign excesses over at most3samples, require2, divide by existing2C scale, clamp1. Reset on sign reversal, within-envelope residual, context transition or gap. Max merge into existing sensor feature; no new independent DS source; unchanged global thresholds and causal precedence. Slow slope and all other origin logic unchanged. Constants fixed before TRAIN; no planned parameter search.\n\nRetention per channel: strict validation detection gain versus A0, fewer silent plant misses for event; no lost A0 detections; no extra benign alarms (at most1/80 overall); no wrong origins; full effective-memory/timing/communication/actuator preservation; no new slow-drift alarms. Memory additionally assessed with encoded checkword versus the existing shadow. A channel with no new evidence/benefit is removed. No logic changes after validation except discarding rejected channels as predefined. Target90% is aspirational, not a cohort selection criterion.\n\nFrozen experimental hashes:\n```json\n'+json.dumps(frozen,indent=2)+'\n```\n\nExact baseline-to-experiment patch for reproducibility (temporary ablation source reconstruction):\n```diff\n'+patch+'```\n')
  retain={next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['origin']==o) for o in [*ORIGINS,'NORMAL']};retain.update(next(s['run_id'] for s in specs if s['partition']=='development-validation' and s['model']==m) for m in ['sensor_bias','sensor_interface_intermittent']);assert len(retain)==8
  rows=[]
  for part in ['development-train','development-validation']:
   assert all(sha(ROOT/p)==h for p,h in frozen.items())
   for i,s in enumerate([s for s in specs if s['partition']==part]):
    rr=c.execute(s,w,s['run_id'] in retain)
    for r in rr:r.pop('command_json',None)
    rows+=rr
    if (i+1)%60==0:print(part,i+1,flush=True)
   report(rows)
   with (OUT/'validation_record.md').open('a') as f:f.write('\n'+part+' complete with unchanged experimental settings.\n')
   print(part,'COMPLETE',flush=True)
   if part=='development-train':
    (BASE/'train_ready').write_text('TRAIN complete. No settings changed. Validation pending explicit local freeze acknowledgment.\n')
    print('TRAIN checkpoint: resume by creating /tmp/clo-event90/validation_go',flush=True)
    import time
    while not (BASE/'validation_go').exists():time.sleep(1)
  assert all(sha(ROOT/p)==h for p,h in frozen.items());print('1200-case campaign complete',flush=True)
if __name__=='__main__':main()
