#!/usr/bin/env python3
"""Seal a completed DEVELOPMENT audit package, without freezing a new candidate."""
import csv,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/cross_layer_safety_v7_1_dev'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def verify():
 manifest=json.loads((OUT/'candidate2_development_hashes.json').read_text())
 for name,digest in manifest['sha256'].items():
  if sha(ROOT/name)!=digest:raise ValueError('Development artifact changed: '+name)
 subprocess.run(['python3','scripts/verify_clo_dsf_candidate.py'],cwd=ROOT,check=True)
 print(f"Verified {len(manifest['sha256'])} Candidate 2 development identities; no new final-holdout candidate frozen.")
def package():
 if (OUT/'candidate2_development_hashes.json').exists():raise ValueError('Package already sealed; use --verify')
 selection=json.loads((OUT/'selection_record.json').read_text());assert sha(OUT/'selected_config.cfg')==selection['selected_config_sha256'];assert selection['validation_seen'] is False
 pre=json.loads((OUT/'preregistered_protocol.json').read_text())
 for name,digest in pre['source_sha256'].items():assert sha(ROOT/name)==digest
 assert sha(OUT/'selection_protocol.md')==pre['protocol_sha256'];assert sha(ROOT/'studies/clo_dsf_candidate2_development_v1.yaml')==pre['study_sha256']
 decision=json.loads((OUT/'candidate2_freeze_decision.json').read_text());assert not decision['frozen']
 regress=json.loads((OUT/'scientific_regression.json').read_text());assert regress['status']=='PASS'
 for folder in ['gui_candidate2','gui_legacy']:assert json.loads((OUT/f'validation/{folder}/desktop_checks.json').read_text())['status']=='PASS'
 assert json.loads((OUT/'validation/trace_audit.json').read_text())['status']=='PASS'
 tests=(OUT/'validation/complete_tests.log').read_text();assert tests.rstrip().endswith('OK')
 subprocess.run(['make'],cwd=ROOT,check=True,capture_output=True);subprocess.run(['git','diff','--check'],cwd=ROOT,check=True);subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT,check=True)
 snapshot=Path('/tmp/clo-c2-preflight/existing_hashes.json');preservation={}
 if snapshot.exists():
  originals=json.loads(snapshot.read_text());changed=[name for name,h in originals.items() if not (ROOT/name).is_file() or sha(ROOT/name)!=h]
  assert set(changed)=={'Makefile','scripts/virtual_ecu_gui.py'},changed
  preservation=dict(existing_files=len(originals),unchanged_files=len(originals)-len(changed),additive_integration_only=changed,candidate1_and_all_historical_evidence_unchanged=True,session_byte_identical=True)
  dest=OUT/'validation/preflight';dest.mkdir(exist_ok=True)
  for name in ['status.txt','log.txt','diff-stat.txt','session.sha256','tests.log','regression.log','existing_hashes.json']:shutil.copyfile(snapshot.parent/name,dest/name)
 status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True);(OUT/'validation/final_git_status.txt').write_text(status)
 maps=[]
 for channel,support,kind in [('timing',['TIMING'],'DIRECT'),('communication',['COMMUNICATION'],'DIRECT'),('memory_control',['MEMORY'],'DIRECT'),('sensor_control',['COMMUNICATION','SENSOR_CONTROL'],'INDIRECT'),('actuator',['ACTUATOR'],'DIRECT'),('plant',['MEMORY','TIMING','COMMUNICATION','SENSOR_CONTROL','ACTUATOR'],'INDIRECT/VACUOUS')]:
  maps.append(dict(channel=channel,detection_support='ABNORMAL',origin_support='|'.join(support),origin_class=kind,detection_reliability=selection['parameters']['r_detection'],origin_reliability=selection['parameters']['r_origin_indirect'] if kind.startswith('INDIRECT') else selection['parameters']['r_origin_direct']))
 with (OUT/'candidate2_observability_mapping.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(maps[0]));w.writeheader();w.writerows(maps)
 config=dict(status='LOCKED DEVELOPMENT EVALUATION POINT; NOT A FROZEN FINAL-HOLDOUT CANDIDATE',parameters=selection['parameters'],frames={'detection':['NORMAL','ABNORMAL'],'localization':['MEMORY','TIMING','COMMUNICATION','SENSOR_CONTROL','ACTUATOR']},storage_partitions={'detection':[1,62],'localization':[33,2,4,8,16]},theta_storage_mask=63,origin_betp='Logical five-origin cardinality, not six storage bits',conflict_rule='Dempster',total_conflict_epsilon=1e-12,total_conflict_action='Flagged vacuous fallback',evidence_transforms='Exact additive copy of frozen Candidate 1; see design document and hashed evidence source',observability_mapping=maps,propagation_graph={'timing':['sensor_control','actuator','plant'],'communication':['sensor_control','actuator','plant'],'memory_control':['sensor_control','actuator','plant'],'sensor_control':['actuator','plant'],'actuator':['plant'],'plant':[]},propagation_active_threshold=.5,propagation_condition='Both episodes active, strict upstream onset before downstream, no future/reversed/simultaneous/expired edge',propagation_effect='Origin reliability only, min(1,r*(1+bonus)); selected bonus 0',temporal_cadence_ms=100,combination_order=['timing','communication','memory_control','sensor_control','actuator','plant','discounted previous same-frame state'],absence_policy='Vacuous in both frames; never negative NORMAL support',decision='Detection belief only; consecutive confirmed samples; reset below confirmed threshold',origin_decision='Confirmed plus top logical BetP, margin and ignorance gates; otherwise UNKNOWN',weighted_sum={'weights':[.2,.2,.2,.1,.2,.1],'threshold':.04,'persistence':1},candidate1_frozen_hashes=sha(ROOT/'results/cross_layer_safety_v7_dev/clo_dsf_candidate_hashes.json'))
 write(OUT/'candidate2_evaluation_config.json',config)
 write(OUT/'validation/preservation.json',preservation)
 record=f'''# Candidate 2 validation record

Status: PASS — completed development evaluation; no new candidate freeze and no final holdout.

- Committed baseline: d757539df55ca5e93fe45c810d3e2c5d6fdf547b.
- Initial Candidate 1 working tree, all its sources/configuration/evidence and user session are byte-identical. Final preservation audit: {preservation.get('unchanged_files')} of {preservation.get('existing_files')} existing files unchanged; only Makefile and scripts/virtual_ecu_gui.py receive additive Candidate 2 integration. The original Candidate 1 GNUmakefile and GUI modules remain unchanged.
- Accepted lock: 141 source/configuration entries and 5866 evidence entries pass; HETIA, v1–v6, Hybrid, timing and HT1–HT4 remain unchanged.
- Legacy regression: 48 cases against compiled accepted baseline, raw/summary bytes match.
- RTL regression: 64 cases, all historical fields/metrics match (relocated output paths excluded).
- Representative v5 replay: eight accepted cases, byte-identical raw/summary/event files.
- Candidate 1 replay: six origins/cohorts, byte-identical raw/summary/evidence/metrics. Six additional new-cohort comparisons verify the Candidate 1 bank matches its frozen executable.
- Build: make passes without warnings. Python compile of scripts/virtual_ecu_gui.py and python/virtual_ecu/*.py passes. git diff --check passes. No staged diff.
- Complete test suite: 228 tests PASS, including numerical frame algebra, temporal behavior, hidden injector-label invariance, independent detection/origin outputs, strict configuration parsing, feature parity and development selection audits.
- Desktop: 17 Candidate 2 checks PASS and 181 unchanged legacy desktop checks PASS. Advanced and Research examples execute C; historical and Candidate 1 results load; CONFIRMED + UNKNOWN displays normally. Session/history/export writes are redirected. Local display access required sandbox escalation; approved desktop checks did not alter user files.
- Runtime trace audit: 396 selected-validation runs, 475596 rows. Normalized masses, five-origin logical BetP/margin, binary positive support, state/timestamp consistency and online metric agreement pass. There are 1603 confirmed-UNKNOWN runtime rows.
- Campaign: 1140 unique configurations, TRAIN 744, VALIDATION 396. No semantic duplicates, no group leakage, no exact Candidate 1 validation overlap. Validation executed once after selection; raw commands and traces retained.
- Predeclared runtime source, study, protocol and selected-config hashes remain identical after validation. Weighted Sum and Candidate 2 selected before validation. No scientific parameter or algorithm changes after validation.
- Reporting correction only: selected TRAIN .55/.15 localization readout matches its online bank; actual later-localization timestamps were recovered from that bank (243 correct localizations before plant). This changes no selection objective, runtime or validation output. Historical search-table later-localization placeholders were not used for selection; see reporting_adjustments.json.
- Host overhead: 30 interleaved samples plus warmup per mode, recorded with raw samples. No embedded WCET claim.
- Final disposition: selected origin discounting is dominated on measured decision endpoints by the no-origin-discount ablation; fair Weighted Sum matches binary detection. Do not freeze or silently simplify using this validation. Candidate 1 remains frozen. candidate2_development_hashes.json seals reproducible evidence only, not a final-holdout candidate contract.

Commands and complete output are retained in validation/ and the scripts directory. The final git status is in validation/final_git_status.txt. No git add, commit, push, reset, restore, checkout or clean was run.
'''
 (OUT/'candidate2_validation_record.md').write_text(record);(OUT/'validation_record.md').write_text(record)
 # Include every development artifact, and all source/config/build dependencies needed to identify this revision.
 sources=[*sorted((ROOT/'src/v7_1').glob('*.c')),*sorted((ROOT/'src/v7').glob('*.c')),ROOT/'include/clo_dsf_candidate2.h',ROOT/'include/clo_dsf.h',ROOT/'include/ds_evidence.h',ROOT/'include/runtime_observation.h',ROOT/'include/runtime_timing_observation.h',ROOT/'include/config.h',ROOT/'src/runtime_observation.c',ROOT/'src/main.c',ROOT/'src/scheduler.c',ROOT/'Makefile',ROOT/'GNUmakefile',ROOT/'clo_dsf_candidate2.mk',ROOT/'scripts/virtual_ecu_gui.py',ROOT/'docs/clo_dsf_candidate2_design.md',ROOT/'studies/clo_dsf_candidate2_development_v1.yaml',*sorted((ROOT/'python/virtual_ecu').glob('clo_dsf_candidate2*.py')),*sorted((ROOT/'scripts').glob('*candidate2*.py')),*sorted((ROOT/'tests').glob('*candidate2*'))]
 sources=[p for p in sources if p.is_file()];artifacts=[p for p in OUT.rglob('*') if p.is_file()]
 write(OUT/'candidate2_development_hashes.json',dict(purpose='Completed DEVELOPMENT identity; NOT final-holdout candidate freeze',candidate2_frozen=False,holdout_created=False,sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(sources+artifacts))}))
 verify()
if __name__=='__main__':verify() if '--verify' in sys.argv else package()
