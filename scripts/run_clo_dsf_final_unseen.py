#!/usr/bin/env python3
"""One-shot, preregistered evaluation of the committed CURRENT implementation."""
import csv, hashlib, io, json, math, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu import clo_dsf_current as current
from virtual_ecu.clo_dsf_holdout import prepare_work, profile_identity
from virtual_ecu.clo_dsf_development import write_csv, ORIGINS, sha
from virtual_ecu.clo_dsf_candidate2_development import aggregate
from virtual_ecu.clo_dsf_current_reporting import runtime_stats
from virtual_ecu.clo_dsf_final_reporting import wilson
OUT=ROOT/'results/clo_dsf_final_unseen'
METHODS=['Revised CLO-DSF','Weighted Sum','Simple OR','Plain DS','Hybrid','Timing Monitor']
BASE_COMMAND=current.command

def command(s,work):
    cmd=BASE_COMMAND(s,work)
    for key,value in {'--intermittent-on-ms':600,'--intermittent-off-ms':1300,'--drop-every-n-updates':13}.items():
        if key in cmd:cmd[cmd.index(key)+1]=str(value)
    return cmd

def design():
    specs=[]
    for f in range(10):
        cells=[]
        for bit in [(f+i)%5 for i in range(3)]:
            for polarity in [0,1]:
                for b in ['transient','intermittent','permanent']:cells.append(('MEMORY','stuck_bit',b,bit,polarity))
        for bit in [f%5,(f+2)%5]:
            for b in ['transient','intermittent','permanent']:cells.append(('MEMORY','bit_flip',b,bit,0))
        for m in ['deadline_miss','task_delay']:
            for mag in ([0]*4 if m=='deadline_miss' else [100,300,700,1100]):
                for b in ['transient','intermittent','permanent']:cells.append(('TIMING',m,b,mag,0))
        comm=[]
        for m,ms in [('delayed_update',[100,400,900]),('dropped_update',[1,2,5]),('replayed_sample',[100,700,1700])]:
            for mag in ms:
                for b in ['transient','intermittent','permanent']:comm.append(('COMMUNICATION',m,b,mag,0))
        cells += [comm[(i+f*3)%27] for i in range(24)]
        for m,ms in [('sensor_bias',[-1.05,1.05,-1.3,1.3]),('sensor_interface_intermittent',[.35,.65,2.3,6.7])]:
            for mag in ms:
                for b in ['transient','intermittent','permanent']:cells.append(('SENSOR_CONTROL',m,b,mag,0))
        for m,ms in [('pump_degraded',[.982,.956,.917,.843,.731,.583]),('fan_stuck_off',[0,0])]:
            for mag in ms:
                for b in ['transient','intermittent','permanent']:cells.append(('ACTUATOR',m,b,mag,0))
        cells += [('NORMAL','baseline','none',0,0)]*30
        for j,(origin,model,behavior,mag,polarity) in enumerate(cells):
            load=[.38,.47,.55,.63,.70,.77,.83,.89,.94,.97][f]
            profile=[dict(start_ms=a,end_ms=b,vehicle_speed_kph=(17+9*f)*fac,engine_load=(load+j*.000031)*fac,ambient_temp_c=19+2.3*f+j*.0019,external_airflow_factor=0,road_slope_percent=0) for a,b,fac in [(0,19300,.73),(19300,51700,1),(51700,89300,.79),(89300,120000,.91)]]
            updates=[[33700,101],[68300,92]] if (j+f)%2 else []
            variation=['0:0:7400','0.025:0:7400','0.075:0:9400','0.095:0:11400','0.035:0.8:14600','0.045:1.1:19400'][(j-120)//5] if origin=='NORMAL' else '0:0:7400'
            s=dict(run_id=f'unseen_{len(specs):04}',origin=origin,model=model,behavior=behavior,magnitude=mag,stuck_polarity=polarity,start_ms=120100 if origin=='NORMAL' else 21300+(j%11)*400+f*100,duration_ms=0 if behavior in ['permanent','none'] else 100 if model=='deadline_miss' and behavior=='transient' else [8300,11900,16700][(j+f)%3],group=f'unseen_family_{f}',partition='final-unseen',profile=f'unseen_profile_{len(specs):04}',profile_json=json.dumps(profile,sort_keys=True),target_updates_json=json.dumps(updates),workload='authorized_updates' if updates else 'static_target',seed=51001+f*503+j*7,simulation_duration_ms=120000,sensor_variation=variation,initially_latent_stuck=int(model=='stuck_bit' and ((92>>int(mag))&1)==polarity))
            s['profile_semantic_sha256']=profile_identity(profile)
            s['configuration_sha256']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()
            specs.append(s)
    assert len(specs)==1500 and all(sum(s['origin']==o for s in specs)==240 for o in ORIGINS)
    return specs

def audit(specs):
    """A disjoint complete physical profile is sufficient to disprove config equality."""
    keys={s['profile_semantic_sha256'] for s in specs};assert len(keys)==1500
    audit=[]
    paths=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    for name in paths:
        if not name.endswith('.csv') or not name.startswith(('results/','presets/')):continue
        p=ROOT/name
        # All saved profiles, plus every compact table carrying inline profile identities.
        with p.open() as fh:
            header=fh.readline().strip().split(',')
        if {'start_ms','end_ms','vehicle_speed_kph','engine_load','ambient_temp_c'}<=set(header):
            with p.open() as fh:old={profile_identity(list(csv.DictReader(fh)))}
        elif 'profile_json' in header or 'profile_semantic_sha256' in header:
            with p.open() as fh:
                old={profile_identity(json.loads(r['profile_json'])) if r.get('profile_json') else r['profile_semantic_sha256'] for r in csv.DictReader(fh)}
        else:continue
        n=len(keys&old);audit.append(dict(compared_to=name,prior_profiles=len(old),shared_profiles=n,exact_configuration_overlap=n,proof='complete physical profile disjoint'));assert n==0,name
    # Include overwritten CURRENT designs recoverable from all commit history.
    commits=subprocess.check_output(['git','log','--all','--format=%H','--','results/clo_dsf_current/configuration_manifest.csv'],cwd=ROOT,text=True).splitlines()
    for commit in commits:
        data=subprocess.check_output(['git','show',commit+':results/clo_dsf_current/configuration_manifest.csv'],cwd=ROOT,text=True)
        old={r['profile_semantic_sha256'] for r in csv.DictReader(io.StringIO(data))};n=len(keys&old);assert n==0
        audit.append(dict(compared_to=commit+':CURRENT manifest',prior_profiles=len(old),shared_profiles=n,exact_configuration_overlap=n,proof='complete physical profile disjoint'))
    # Previously overwritten local development manifests remain available in temporary provenance.
    for p in Path('/tmp').glob('clo*/**/*manifest.csv'):
        try:
            with p.open() as fh:rs=list(csv.DictReader(fh))
            if not rs or 'profile_semantic_sha256' not in rs[0]:continue
            old={r['profile_semantic_sha256'] for r in rs};n=len(keys&old);assert n==0
            audit.append(dict(compared_to=str(p),prior_profiles=len(old),shared_profiles=n,exact_configuration_overlap=n,proof='complete physical profile disjoint'))
        except (OSError,UnicodeError):continue
    write_csv(OUT/'overlap_audit.csv',audit)
    return paths

def report(rows):
    summaries=[];loc=[];conf=[];pairs=[]
    for m in METHODS:
        chosen=[r for r in rows if r['method']==m]
        groups={'ALL':chosen,**{o:[r for r in chosen if r['origin']==o] for o in ORIGINS},'effective_memory':[r for r in chosen if r['origin']=='MEMORY' and r['effective_memory_corruption']], 'dormant_memory':[r for r in chosen if r['model']=='stuck_bit' and not r['effective_memory_corruption']], 'weak_isolated_bias':[r for r in chosen if r['model']=='sensor_bias' and r['behavior']!='intermittent']}
        groups.update({model:[r for r in chosen if r['model']==model] for model in sorted({r['model'] for r in chosen})})
        for g,rs in groups.items():
            if not rs:continue
            a=aggregate(rs);a['ci_low'],a['ci_high']=wilson(a['detected'],a['faulty_runs']);summaries.append(dict(method=m,group=g,**a))
            if m=='Revised CLO-DSF' and g in ['ALL',*ORIGINS]:
                loc.append(dict(method=m,group=g,first_correct=a['correct_localizations'],first_localized=a['localized'],first_unknown=a['unknown'],**runtime_stats(rs)))
                for unit in ['first_detection','runtime_alarm_sample']:
                    conf.append(dict(origin=g,unit=unit,**{o:sum((r['detected'] and r['origin_at_alarm']==o) if unit=='first_detection' else r['alarm_'+o] for r in rs) for o in [*ORIGINS,'UNKNOWN']}))
    c={r['run_id']:r for r in rows if r['method']=='Revised CLO-DSF'};w={r['run_id']:r for r in rows if r['method']=='Weighted Sum'}
    for group in ['ALL',*ORIGINS,'NORMAL']:
        counts=[0]*4;faster=same=slower=0
        for k,a in c.items():
            if group=='ALL' and not a['injected'] or group!='ALL' and a['origin']!=group:continue
            b=w[k];da=a['detected'] if a['injected'] else a['false_alarm'];db=b['detected'] if b['injected'] else b['false_alarm']
            counts[0 if da and db else 1 if da else 2 if db else 3]+=1
            if a['detected'] and b['detected']:
                faster+=a['latency_ms']<b['latency_ms'];same+=a['latency_ms']==b['latency_ms'];slower+=a['latency_ms']>b['latency_ms']
        n=counts[1]+counts[2];p=min(1,2*sum(math.comb(n,i) for i in range(min(counts[1:3])+1))/2**n) if n else None
        pairs.append(dict(group=group,both=counts[0],only_clo=counts[1],only_weighted_sum=counts[2],neither=counts[3],mcnemar_exact_two_sided_p=p,discordant=n,clo_faster=faster,same_latency=same,clo_slower=slower))
    write_csv(OUT/'detection_summary.csv',summaries);write_csv(OUT/'localization_summary.csv',loc);write_csv(OUT/'confusion_summary.csv',conf);write_csv(OUT/'paired_comparison.csv',pairs)
    ci=[]
    a=next(s for s in summaries if s['method']=='Revised CLO-DSF' and s['group']=='ALL');rt=loc[0]
    for label,k,n in [('detection',a['detected'],a['faulty_runs']),('plant_detection',a['plant_manifestation_runs']-a['silent_plant'],a['plant_manifestation_runs']),('benign_alarms',a['benign_false_alarms'],a['benign_runs']),('first_accuracy',a['correct_localizations'],a['localized']),('runtime_accuracy',rt['correct_samples'],rt['localized_samples'])]:
        low,high=wilson(k,n);ci.append(dict(endpoint=label,numerator=k,denominator=n,ci_low=low,ci_high=high))
    write_csv(OUT/'confidence_summary.csv',ci)
    return summaries,loc,pairs

def main():
    if OUT.exists():raise SystemExit('Refuse rerun or overwrite of final unseen campaign')
    OUT.mkdir()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).splitlines()==['presets/gui_session_state.json']
    specs=design();paths=audit(specs)
    before={p:sha(ROOT/p) for p in paths if (ROOT/p).is_file()}
    Path('/tmp/clo-final-unseen/initial_hashes.json').write_text(json.dumps(before))
    scientific={p:h for p,h in before.items() if p.startswith(('src/','include/','python/','scripts/','tests/')) or p.endswith(('.mk','.cfg')) or p=='Makefile'}
    scientific[str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
    subprocess.run(['make','-B','-f','clo_dsf_revised.mk','-j4'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    current.OUT=OUT;current.METHODS=METHODS;current.command=command
    with tempfile.TemporaryDirectory(prefix='clo-final-unseen-runs-') as tmp:
        work=Path(tmp);prepare_work(work,specs)
        objects=[str(p) for p in (ROOT/'src').glob('*.o') if p.name!='main.o'];exe=work/'check'
        subprocess.run(['gcc','-std=c11','-Iinclude','tests/holdout_configuration_check.c',*objects,'-o',str(exe)],cwd=ROOT,check=True)
        for s in specs:
            cmd=command(s,work);subprocess.run([str(exe),*cmd[2:]],check=True,capture_output=True)
            s['command_json']=json.dumps([v.replace(str(work),'$WORK').replace(str(ROOT),'$ROOT') for v in cmd])
        write_csv(OUT/'campaign_manifest.csv',specs)
        protocol=f'''# Final unseen CURRENT validation

Commit: {commit}. Registered UTC {datetime.now(timezone.utc).isoformat()} before any outcomes.
1500 unique cases: 240 per fault origin, 300 benign. Ten new operating families;
new profiles, seeds, activation times, finite durations, continuous magnitudes.
Discrete bits/ticks and minimum short delays necessarily reuse physically valid values.
Seeds are effective only where supported by the original injector; deterministic
cases are not claimed to be independent random replicates. Exact commands and full
profiles are in the manifest. Profile disjointness proves zero exact overlap even
if historical seed/metadata representations differ. Audit covers saved profiles,
inline profiles, previous holdout, CURRENT history and surviving overwritten manifests.

MEMORY: stuck bits of both polarities and bit flips, static/legal updates. Effective
means observed register-shadow mismatch after onset, classified only after runtime.
Dormant means stuck-bit run with no such mismatch. TIMING: deadline/task delays.
COMMUNICATION: delays/drops/replays including shortest one-tick disturbances.
SENSOR_CONTROL: +/-1.05 and +/-1.30 C biases, .35/.65/2.3/6.7 C pulses.
Weak isolated subgroup is non-intermittent bias (80 cases), predeclared regardless
of outcomes. ACTUATOR: six pump degradation strengths plus fan-off cases.
Behavior is transient/intermittent/permanent where supported. Permanent duration
is explicitly zero, so legacy permanent sensor/actuator events truly continue.
Legacy intermittent events are two separated episodes, not an invented new injector.
Benign cases include static and legal target updates at33700/68300 ms, alternating
measurement variation and slow triangular drift using the committed workload adapter.
No noise is composed with transport faults. All cases last120s, 100ms ticks.

No selection, calibration or redesign. Known weak bias limits remain. CURRENT,
frozen Fair Weighted Sum (choice6), Simple OR, Plain DS and Hybrid observe the same
runtime stream. Timing Monitor is scored ONLY for timing cases. Other internal
observers may execute but are not reported. Source/config hashes recorded below.
No injection labels/truth enter inference; only offline evaluation uses them.

Detection is first post-onset alarm, latency relative to scheduled activation;
plant propagation uses unchanged reference-based evaluator. Pre-onset alarms are
reported separately. Benign alarms count any alarm. First-origin accuracy among
localized detections; coverage among detections; runtime known-origin accuracy,
UNKNOWN and wrong counts cover all alarm samples, including pre-onset samples.
Report per-origin, effective/dormant memory, weak isolated bias and actuator subtypes.
Wilson95 intervals are descriptive case intervals; correlated deterministic cases
are not random population samples. Paired exact two-sided binomial McNemar on
fault detection discordances if nonzero (otherwise not applicable); no population
superiority claim from this test alone. Paired benign counts and joint latencies
also reported. Retain all failures without changing settings or removing cases.

Keep eight traces chosen before outcomes: first of six origins, first isolated
negative bias, first weak pump case distinct from the initial actuator trace.
Process and delete per-run temporary raw data. Full regression after all1500:
build, compile, diff check, tests, legacy48, RTL64; hash checks before/after.
No commit/push; GUI session bytes preserved. No scientific implementation edits.
'''
        (OUT/'protocol.md').write_text(protocol)
        frozen={**scientific,**{str((OUT/n).relative_to(ROOT)):sha(OUT/n) for n in ['protocol.md','campaign_manifest.csv','overlap_audit.csv']}}
        def verify():
            assert all(sha(ROOT/p)==h for p,h in frozen.items()),'Scientific identity changed: STOP'
        verify()
        (OUT/'validation_record.md').write_text('# Validation record\n\nPre-outcome commit '+commit+'\n\nScientific and protocol SHA256 identities:\n```json\n'+json.dumps(frozen,indent=2,sort_keys=True)+'\n```\n\nBuilt from committed sources; all configurations passed public validation before execution.\n')
        retain={next(s['run_id'] for s in specs if s['origin']==o) for o in [*ORIGINS,'NORMAL']}
        retain.add(next(s['run_id'] for s in specs if s['model']=='sensor_bias' and s['behavior']=='permanent'))
        retain.add(next(s['run_id'] for s in specs if s['model']=='pump_degraded' and s['behavior']=='permanent'))
        assert len(retain)==8
        rows=[]
        for i,s in enumerate(specs):
            verify()
            result=current.execute(s,work,s['run_id'] in retain)
            for r in result:
                r.pop('command_json',None)
                if r['method']=='Timing Monitor' and r['origin']!='TIMING':continue
                rows.append(r)
            if (i+1)%50==0:print(f'Completed {i+1}/1500',flush=True)
        verify();write_csv(OUT/'case_summary.csv',rows);report(rows)
        with (OUT/'validation_record.md').open('a') as fh:fh.write('\n1500/1500 executed once. All registered scientific and protocol hashes unchanged after runtime. No outcomes used for tuning.\n')
        print('Final unseen runtime complete; regression pending.',flush=True)
if __name__=='__main__':main()
