#!/usr/bin/env python3
"""Conditionally freeze the validated revision; never generate a holdout."""
import hashlib,json,py_compile,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.clo_dsf_revised_development import OUT,OLD,sha,write_json
from virtual_ecu.clo_dsf_final_reporting import records
MANIFEST=OUT/'clo_dsf_revised_hashes.json'

def check(hashes):
 changed=[name for name,digest in hashes.items() if not (ROOT/name).is_file() or sha(ROOT/name)!=digest]
 if changed:raise ValueError('Changed frozen identity: '+repr(changed))

def verify():
 j=json.loads(MANIFEST.read_text());check(j['sha256'])
 check(json.loads((OUT/'preregistered_development.json').read_text())['source_sha256'])
 print(f"PASS: {len(j['sha256'])} frozen revision/dependency/artifact identities. No final holdout.")

def freeze():
 if MANIFEST.exists():raise ValueError('Already frozen; use --verify')
 decision=json.loads((OUT/'scientific_decision.json').read_text());reg=json.loads((OUT/'validation/regression.json').read_text())
 if reg['status']!='PASS' or reg['legacy_cases']!=48 or reg['rtl_cases']!=64:raise ValueError('Regression gate failed')
 check(json.loads((OUT/'preregistered_development.json').read_text())['source_sha256'])
 selection=json.loads((OUT/'selection_record.json').read_text())
 if selection['validation_seen'] or selection['parameters_changed']:raise ValueError('Selection isolation failed')
 if sha(OUT/'revised.cfg')!=selection['config_sha256']:raise ValueError('Parameters changed')
 if (OUT/'revised.cfg').read_bytes()!=(OLD/'final_reference.cfg').read_bytes():raise ValueError('Parameters differ from v7.2')
 stamp=datetime.now(timezone.utc).isoformat();justified=decision['scientifically_justified']
 write_json(OUT/'freeze_decision.json',dict(frozen=justified,decided_at_utc=stamp,holdout_created=False,parameters_changed=False,regression_passed=True,reason='Eight additional correctly localized validation faults; silent plant misses 14 to 6, no detection losses, no new benign alarms or wrong origins. Gains are confined to weak intermittent pump degradation; model-specific actuator contract limits scope.' if justified else 'No clearly better validated scientific trade-off; reject without tuning'))
 if not justified:
  print('Freeze NO. No parameter edits or holdout.');return
 config=json.loads((OLD/'clo_dsf_final_config.json').read_text())
 config.update(schema_version='7.3',algorithm='CLO-DSF revised actuator contract',status='FROZEN PRE-HOLDOUT DEVELOPMENT CANDIDATE',frozen_at_utc=stamp,committed_baseline=(OUT/'validation/baseline.txt').read_text().strip(),parameters_may_change=False)
 config['channels'][4]['transform']='Available iff all four command/actual values finite and time_ms modulo ECU_ACTUATOR_PERIOD_MS == 0. e=1 iff either actual lies outside [nextafterf(clamp(command),-INFINITY),nextafterf(clamp(command),INFINITY)], otherwise e=0. Unavailable is vacuous.'
 config['actuator_contract']={'source':'Unchanged src/actuators.c and src/scheduler.c: immediate clamped response before detector sampling','trusted_inputs':['pump_command','pump_actual','fan_command','fan_actual','time_ms'],'new_observables':False,'physical_hardware_validated':False,'restriction':'Requires a separately justified physical error/dynamics envelope and trustworthy synchronized response sensing before hardware use','extra_tunable_parameters':0,'replacement_not_duplicate_evidence':True}
 config['parameter_provenance']={'source':str((OLD/'final_reference.cfg').relative_to(ROOT)),'sha256':sha(OLD/'final_reference.cfg'),'copy':'Byte-identical eight-value configuration','search':False}
 config['validation_scope']={'unique_development_configurations':1125,'train':735,'validation':390,'holdout_created':False,'benefit_family':'weak intermittent pump degradation','no_DS_superiority_claim':True}
 write_json(OUT/'clo_dsf_revised_config.json',config)
 contract=f'''# CLO-DSF v7.3 frozen development contract

Frozen {stamp}. Baseline {config['committed_baseline']}.
No final unseen paper holdout has been created, inspected or executed.

## Scientific identity

Normative machine-readable specification:
results/cross_layer_safety_v7_3_dev/clo_dsf_revised_config.json.
Exact eight-value configuration: results/cross_layer_safety_v7_3_dev/revised.cfg,
byte-identical to v7.2. Reference implementation: src/v7_3/clo_dsf_revised.c.
The source includes the unmodified v7.2 inference body and substitutes only
actuator evidence extraction. Development rationale and protocol are in
docs/clo_dsf_revised_development.md; preregistered identities and the pre-validation
selection record remain archived. No parameter search or post-validation edits.

One replacement source: synchronous actuator command/response conformance.
On the 100 ms actuator cadence, all four values must be finite. Expected response
is clamp(command,0,1); its immediate predecessor and successor representable
float values bound the accepted response. A response outside either pump or fan
interval gives e_act=1; otherwise e_act=0. Unavailable/off-cadence is vacuous.
No duplicate source, fitted severity threshold, origin reliability discount,
propagation bonus, injector label, self-test label proxy or experiment truth.

Detection frame NORMAL/ABNORMAL and five-origin localization remain independent.
Dempster fusion, fixed channel order, vacuous fallback, temporal retention .8,
r_detection 1, suspect .35, confirmation .5, persistence 1, localization .55,
margin .15 and ignorance limit .5 are immutable. UNKNOWN is valid. Conflict,
ignorance and timestamps remain visible; episode paths remain diagnostic-only.
Duplicate/backward samples are ignored. All unchanged semantics are specified
by the hashed v7.2 algorithm and complete revised machine configuration.

## Why freeze, and limits

On new group-held development validation, revision detects 260/300 versus
v7.2 252/300 and frozen Weighted Sum 251/300. Plant-propagating detection is
198/204, versus v7.2 190/204. Silent plant cases fall 14 to 6. No detection loss,
zero benign alarms among 90 cases, 200/260 localized (76.92%), all correct;
60 UNKNOWN and zero wrong localized runtime samples. Median/P95 is 0/200 ms.
All eight gains over v7.2 are .98 intermittent pump degradations across four
profiles/two onsets. This is a material and mechanistically explained reduction
in silent plant misses, not a freeze based merely on a small percentage gain.
The minimum A0/A1 ablation changes only this source; no A2 is needed.

Results are designed correlated development cases, not population safety or
final unseen evidence. Gains do not prove DS is uniquely effective: Weighted Sum
was frozen with its original inputs, and an enhanced pool with the same new
contract source was not evaluated. Six silent communication misses remain;
14 memory and six unexcited pump faults also remain undetected. Sensor/control
origin remains UNKNOWN. The virtual actuator is noiseless and instantaneous;
physical response feedback needs independent trust and a validated physical
error/dynamics envelope. This one-ULP contract is not a hardware tolerance.

## Integrity and future use

269 tests, 48 legacy regressions, 64 RTL regressions and six representative
seven-baseline parity replays passed. Historical source/evidence and the user's
session edit remain unchanged. Verify all hashes before a separately generated
new unseen holdout. After this freeze do not modify scientific parameters,
evidence semantics or localization logic. Any further scientific revision must
receive a new development identity and fresh evaluation.

Build: make -f clo_dsf_revised.mk
Verify: python3 scripts/freeze_clo_dsf_revised.py --verify
Run example (new output destination):
./virtual_ecu_v7_3 /tmp/revised.csv baseline --detector clo_dsf_revised --detector-action observe_only --revised-config results/cross_layer_safety_v7_3_dev/revised.cfg

No optimization, embedded WCET, production readiness or compliance claim is made.
'''
 (ROOT/'docs/clo_dsf_revised_frozen_contract.md').write_text(contract)
 # Only reporting/package Python changed after the one full regression pass.
 for p in [Path(__file__),ROOT/'scripts/report_clo_dsf_revised_development.py']:py_compile.compile(str(p),doraise=True)
 subprocess.run(['git','diff','--check'],cwd=ROOT,check=True);subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT,check=True)
 status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True);(OUT/'validation/final_git_status.txt').write_text(status)
 tests=(OUT/'validation/complete_tests.log').read_text()
 if 'Ran 269 tests' not in tests or not tests.rstrip().endswith('OK'):raise ValueError('Expected completed test suite')
 record=f'''# v7.3 validation record

PASS. One final full regression pass, with focused revision tests beforehand.
Frozen development candidate only. No final paper holdout created or executed.

- Baseline: {config['committed_baseline']}. Initial git status/session identity retained.
- {reg['preexisting_files_verified']} pre-existing tracked file identities verified; zero changes. User session byte-identical. Candidate 1/2/v7.2 manifests and v1–v6 accepted locks PASS; Hybrid/HETIA unchanged.
- Builds: original make and make -f clo_dsf_revised.mk PASS without warnings. Python compile PASS. git diff --check PASS. Nothing staged.
- Complete suite: 269 tests PASS, including new contract, finite/cadence/rounding boundaries, hidden-label invariance, unchanged-channel parity, diagnostic separation, group isolation and preregistration.
- Legacy regression: 48 cases against compiled accepted baseline, raw/summary bytes identical.
- RTL regression: 64 cases, all historical fields and comparison outcomes unchanged. Temporary replay artifacts were discarded after comparison; their hashes and verification records remain. No duplicate historical traces retained.
- Frozen comparator integration: six TRAIN cases spanning all origins/benign replayed through original v7.2. All seven common comparator metrics match exactly, including original Weighted Sum and v7.2.
- Registered new development cohort: 1,125 unique, TRAIN 735, VALIDATION 390; zero physical historical overlap and zero model/behavior group leakage. No parameter search. All C configurations validated before simulation; a pre-simulation duplicate-profile draft was corrected before registration.
- TRAIN passed the fixed contradiction gates; selection_record.json was written with validation_seen=false and unchanged source/configuration hashes before VALIDATION. All registered valid runs completed once. No post-validation scientific edits.
- Validation: 260/300 detection, 198/204 plant-propagating detection, six silent plant cases, zero benign alarms in 90, 200 correct localized outputs, 60 UNKNOWN, zero wrong origins at any runtime sample; latency 0/200 ms median/P95.
- Minimum ablation: v7.2 to revised changes only actuator evidence. Eight extra detections/correct origins and eight fewer silent plant cases; no detection losses, no extra false alarms. Nine cases detected only by revised versus frozen Weighted Sum, zero only by Weighted Sum.
- Scope: benefits are weak intermittent pump degradations, under the simulator's synchronous ideal response contract. No hardware/generalization/DS-superiority/statistical-significance claim. Remaining six pump misses have zero command during both injected intervals; all remaining silent plant misses are communication.
- Reporting refinement only: final findings explicitly distinguish those unexcited pump cases and narrow gain family. Frozen algorithm/configuration/registered generator were never edited after TRAIN/VALIDATION.
- Exact allowlisted inputs, per-run online metrics, commands and raw/summary/trace hashes retained; no screenshots, GUI modifications or unnecessary full trace copies. No embedded benchmark claim.

Frozen contract: docs/clo_dsf_revised_frozen_contract.md.
Config: clo_dsf_revised_config.json and revised.cfg.
Manifest: clo_dsf_revised_hashes.json includes complete historical dependencies and all new source/artifacts. Verify with python3 scripts/freeze_clo_dsf_revised.py --verify.
No git add, commit, push, reset, restore, checkout or clean was performed.
'''
 (OUT/'validation_record.md').write_text(record)
 history=OLD/'clo_dsf_final_hashes.json';files={ROOT/name for name in json.loads(history.read_text())['sha256']};files.add(history)
 files.update(p for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST)
 files.update(ROOT.glob('src/v7_3/*.c'));files.update(ROOT.glob('scripts/*clo_dsf_revised*.py'));files.update(ROOT.glob('tests/*clo*revised*'))
 files.update(ROOT/name for name in ['clo_dsf_revised.mk','include/clo_dsf_revised.h','python/virtual_ecu/clo_dsf_revised_development.py','docs/clo_dsf_revised_development.md','docs/clo_dsf_revised_frozen_contract.md','virtual_ecu_v7_3'])
 write_json(MANIFEST,dict(status='FROZEN PRE-HOLDOUT DEVELOPMENT CANDIDATE',frozen_at_utc=stamp,holdout_created=False,scientific_parameters_immutable=True,sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(files) if p.is_file()}))
 verify()
if __name__=='__main__':
 if sys.argv[1:]==['--verify']:verify()
 elif not sys.argv[1:]:freeze()
 else:raise SystemExit('Usage: freeze_clo_dsf_revised.py [--verify]')
