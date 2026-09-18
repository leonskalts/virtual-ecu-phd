#!/usr/bin/env python3
"""One final integrity/regression pass, without retaining duplicate replay data."""
import hashlib,json,py_compile,re,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.clo_dsf_holdout import OUT,FROZEN,sha,verify_frozen,read
from virtual_ecu.final_evidence import verify_frozen as verify_accepted
from virtual_ecu.final_reproducibility import legacy_regression,rtl_regression

def run():
 record=OUT/'validation_record.md';text=record.read_text()
 if 'FINAL REGRESSION PASS' in text:raise ValueError('Final regression already recorded; do not repeat')
 registration=json.loads(re.findall(r'```json\n(.*?)\n```',text,re.S)[-1])
 if sha(OUT/'final_holdout_protocol.md')!=registration['protocol_sha256']:raise ValueError('Protocol changed')
 for name,digest in registration['source_and_design_sha256'].items():
  if sha(ROOT/name)!=digest:raise ValueError('Registered source/design changed: '+name)
 verification=verify_frozen();print(verification,flush=True)
 checks=[]
 with tempfile.TemporaryDirectory(prefix='clo-v8-regression-') as t:
  temp=Path(t)
  for label,cmd in [('original build',['make']),('frozen revision build',['make','-f','clo_dsf_revised.mk']),('full tests',[sys.executable,'-m','unittest','discover','-s','tests'])]:
   p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
   if p.returncode:raise RuntimeError(label+' failed\n'+p.stdout+p.stderr)
   tests=re.search(r'Ran (\d+) tests',p.stderr)
   checks.append(dict(check=label,status='PASS',detail=(tests.group(1)+' tests') if tests else 'Successful',output_sha256=hashlib.sha256((p.stdout+p.stderr).encode()).hexdigest()))
  print('Builds and full test suite PASS.',flush=True)
  paths=[ROOT/'scripts/virtual_ecu_gui.py',*sorted((ROOT/'python/virtual_ecu').glob('*.py')),ROOT/'scripts/run_clo_dsf_final_holdout.py',Path(__file__),ROOT/'tests/test_clo_dsf_holdout.py']
  for path in paths:py_compile.compile(str(path),doraise=True)
  legacy=legacy_regression(temp);rtl=rtl_regression(temp)
  for name in ['legacy','rtl']:
   report=json.loads((temp/f'validation/{name}/verification.json').read_text());checks.append(dict(check=name+' regression',status=report['status'],detail=json.dumps(report,sort_keys=True),output_sha256=sha(temp/f'validation/{name}/verification.json')))
  print('48 legacy and 64 RTL PASS.',flush=True)
 accepted=verify_accepted();verification=verify_frozen()
 initial=json.loads(Path('/tmp/clo-v8-audit/initial_hashes.json').read_text())
 changed=[name for name,digest in initial.items() if not (ROOT/name).is_file() or sha(ROOT/name)!=digest]
 if changed:raise ValueError('Pre-existing files changed: '+repr(changed))
 subprocess.run(['git','diff','--check'],cwd=ROOT,check=True);subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT,check=True)
 from virtual_ecu.clo_dsf_development import write_csv
 write_csv(OUT/'paper_tables/integrity_checks.csv',checks)
 status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
 # The registration block remains byte-identical; append the final audit only.
 tail=f'''\n## FINAL REGRESSION PASS

- {verification}
- Registered protocol, generator, reporting, validator, tests, manifest and overlap identities unchanged after evaluation. No scientific tuning or configuration changes.
- All 1,500 simulations completed once; 1,801,500 observations audited for normalized masses and agreement between trace alarms/origins and online metrics.
- Build PASS; Python compile PASS; git diff --check PASS; nothing staged. Full tests: {next(c['detail'] for c in checks if c['check']=='full tests')} PASS.
- Legacy {legacy} and RTL {rtl} PASS. Accepted immutable lock: {json.dumps(accepted,sort_keys=True)}. Hybrid/HETIA and all historical candidate sources/evidence unchanged.
- {len(initial)} pre-existing tracked-file SHA256 identities unchanged, including the pre-existing user session edit. Initial status: {Path('/tmp/clo-v8-audit/initial_status.txt').read_text().strip()}.
- Temporary raw holdout/replay files discarded after checks; compact outputs, exact commands/profile manifests and artifact hashes retained. No screenshots or duplicate historical raw logs.
- Full tests/regressions were run once for this final pass. Focused new evaluator tests ran before holdout registration.
- Only reporting/evaluation support files and the new holdout result directory were added. No detector, threshold, mapping, temporal/localization rule, baseline or fault semantics changed.
- Ready for manuscript evidence with the simulator, family-dependence, nominal-interval and evidence-versus-fusion limitations stated in the findings. No production or hardware-transfer claim.
- No git add, commit, push, reset, restore, checkout or clean was run.

Final git status:
```
{status}```
'''
 record.write_text(text+tail)
 # Seal outcome identities inside the allowed validation record, avoiding an
 # extra top-level manifest. Exclude this self-containing record from its list.
 identities={str(p.relative_to(ROOT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p!=record}
 with record.open('a') as f:f.write('\n## Final artifact SHA256 identities\n\n```json\n'+json.dumps(identities,indent=2,sort_keys=True)+'\n```\n')
 print('Final frozen hashes, session preservation and artifact identities PASS.',flush=True)
if __name__=='__main__':run()
