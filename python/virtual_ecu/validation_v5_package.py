"""Finalize reproducible dataset provenance without asserting unrun regressions."""
import hashlib,json,shutil
from pathlib import Path
from .cross_layer_safety import PROJECT_ROOT
from .validation_v5_design import freeze,STUDY
from .validation_v5_report import records


def finalize(output):
 out=Path(output).resolve();freeze(out)
 required=['v5_run_manifest.csv','timing_holdout_runs.csv','timing_holdout_summary.csv','timing_ablation_holdout.csv',
  'timing_benign_summary.csv','communication_validation_runs.csv','communication_policy_summary.csv',
  'cross_layer_holdout_runs.csv','cross_layer_holdout_summary.csv','stuck_dynamic_matched_comparison.csv',
  'recovery_horizon_analysis.csv','intervention_cost_summary.csv','statistical_confidence_summary.csv',
  'monitor_overhead_summary.csv','v5_scientific_findings.md','final_configuration_recommendation.md']
 for name in required:
  if not (out/name).is_file():raise ValueError(f'Missing required artifact {name}')
 manifest=records(out/'v5_run_manifest.csv');assert len(manifest)==1833
 for name in ['timing_monitor_frozen_contract_v5.md','cross_layer_v5_validation_protocol.md']:
  shutil.copyfile(PROJECT_ROOT/'docs'/name,out/'contracts'/name)
 shutil.copyfile(STUDY,out/'contracts/cross_layer_v5_holdout.yaml')
 raw={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((out/'raw').rglob('*.csv'))}
 for r in manifest:assert raw[str(Path(r['raw_csv']).relative_to(out))]==r['raw_sha256'],r['run_id']
 (out/'raw_sha256.json').write_text(json.dumps(raw,indent=2,sort_keys=True)+'\n')
 source=[*sorted((PROJECT_ROOT/'src').glob('*.c')),*sorted((PROJECT_ROOT/'include').glob('*.h')),
  *sorted((PROJECT_ROOT/'python/virtual_ecu').glob('validation_v5_*.py')),PROJECT_ROOT/'python/virtual_ecu/cross_layer_gui.py',
  PROJECT_ROOT/'scripts/run_cross_layer_v5_validation.py',PROJECT_ROOT/'tests/test_validation_v5.py',STUDY]
 (out/'implementation_sha256.json').write_text(json.dumps({str(p.relative_to(PROJECT_ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source},sort_keys=True,indent=2)+'\n')
 session=out/'validation/session_validation.md'
 text=f'''# V5 validation record

Accepted baseline: da126cb. Frozen combined timing monitor and three specified
policies remain unchanged; supported-domain and event-CSV correctness corrections
are recorded separately in contracts/design_correction.md. The frozen manifest
matches the current monitor/policy/scheduler source hashes and final design.

## Dataset generation checks

- 1,833 main study simulations: 822 timing, 333 communication, 543 cross-layer,
  135 unique matched temporal runs.
- Three auxiliary no-fault references and 33 recovery-horizon simulations give
  1,869 study/reference executions. Reproduction, host benchmarks and synthetic
  tests are separate and do not inflate statistical denominators.
- Primary timing denominator: 714 unique configured cases. Three native C
  ablations replay these same traces; they are not 2,142 independent simulations.
- Required CSV/Markdown outputs exist; raw hashes verified for all main run IDs.
- {len(raw)} raw/summary/per-job event CSV files are hashed in raw_sha256.json,
  including recovery traces and auxiliary references.
- Source/profile/configuration provenance is captured in the frozen contract and
  implementation_sha256.json. Nine figures and candidate tables A–F are supplied.
- Completed-run output schema and reference/output paths are explicit in the
  commands and manifest. N/A is never counted as zero or successful containment.

Host timings are deliberately machine-dependent. The no-op comparison build is
only a measurement instrument, never a holdout binary. Exact nominal output bytes
are asserted equal between benchmark variants. Frozen monitor logic is still the
production C source in all holdout and ablation runs.

## Session verification

'''
 text+=('[Full test, GUI, regression and reproduction record](validation/session_validation.md).\n' if session.exists() else 'Dataset generation does not itself rerun all legacy/GUI tests. No separate session verification record is present in this output directory.\n')
 text+='\nReproduce with `python3 scripts/run_cross_layer_v5_validation.py`. Existing v1/v2/v3/v4 evidence is protected against output overlap. Changes are left unstaged; this runner does not commit or push.\n'
 (out/'v5_validation_record.md').write_text(text)
 return raw
