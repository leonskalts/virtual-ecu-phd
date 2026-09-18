#!/usr/bin/env python3
"""Seal the completed pre-holdout implementation; --verify is strictly read-only."""
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/cross_layer_safety_v7_2_confirmation'
MANIFEST = OUT / 'clo_dsf_final_hashes.json'
SCIENCE = OUT / 'clo_dsf_final_scientific_hashes.json'


def sha(path):
    with path.open('rb') as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
        return digest.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_hashes(hashes):
    changed = [name for name, expected in hashes.items()
               if not (ROOT / name).is_file() or sha(ROOT / name) != expected]
    require(not changed, 'Changed or missing identities: ' + repr(changed))
    return len(hashes)


def verify():
    manifest = json.loads(MANIFEST.read_text())
    count = check_hashes(manifest['sha256'])
    science_count = check_hashes(json.loads(SCIENCE.read_text())['sha256'])
    subprocess.run([sys.executable, 'scripts/package_clo_dsf_candidate2_development.py', '--verify'],
                   cwd=ROOT, check=True)
    print(f'PASS: {count} final implementation/artifact identities; '
          f'{science_count} pre-optimization scientific identities; Candidate 1/2 hashes valid.')
    print('Frozen pre-holdout development candidate. No final holdout created or run.')


def package():
    require(not MANIFEST.exists(), 'Final package already sealed; use --verify')
    check_hashes(json.loads(SCIENCE.read_text())['sha256'])
    decision = json.loads((OUT / 'freeze_decision.json').read_text())
    require(decision['freeze'] and not decision['holdout_created'] and
            decision['mathematical_freeze_before_optimization'], 'Scientific freeze gate failed')
    equivalence = json.loads((OUT / 'benchmark/equivalence.json').read_text())
    require(equivalence['status'] == 'PASS' and equivalence['runs'] == 900 and
            equivalence['observations'] == 1080900 and equivalence['bit_identical_complete_state'] and
            equivalence['decision_discrepancies'] == 0, 'Exact equivalence gate failed')
    regression = json.loads((OUT / 'validation/preservation.json').read_text())
    require(regression['status'] == 'PASS' and regression['legacy_cases'] == 48 and
            regression['rtl_cases'] == 64 and len(regression['v5_replays']) == 8,
            'Accepted regression gate failed')
    gui_counts = {}
    for folder in ['gui_final', 'gui_legacy']:
        report = json.loads((OUT / f'validation/{folder}/desktop_checks.json').read_text())
        require(report['status'] == 'PASS' and not report['errors'], 'Desktop gate failed: ' + folder)
        gui_counts[folder] = len(report['checks'])
    tests = (OUT / 'validation/complete_tests.log').read_text()
    require('Ran 258 tests' in tests and tests.rstrip().endswith('OK'), 'Complete test gate failed')
    checks = json.loads((OUT / 'validation/final_checks.json').read_text())
    require(all(v == 'PASS' for v in checks.values()), 'Build/compile/diff gate failed')
    benchmark = json.loads((OUT / 'benchmark/overhead.json').read_text())
    require(all(r['n'] >= 31 for r in benchmark['summary']), 'Benchmark replication gate failed')
    preflight = Path('/tmp/clo-final-preflight')
    originals = json.loads((preflight / 'existing_hashes.json').read_text())
    original_count = check_hashes(originals)
    subprocess.run([sys.executable, 'scripts/package_clo_dsf_candidate2_development.py', '--verify'],
                   cwd=ROOT, check=True)
    destination = OUT / 'validation/preflight'
    destination.mkdir(exist_ok=True)
    for path in sorted(preflight.iterdir()):
        if path.is_file():
            shutil.copyfile(path, destination / path.name)
    write(OUT / 'validation/final_preservation.json', {
        'status': 'PASS', 'existing_files_verified': original_count, 'changed_files': [],
        'user_session_byte_identical': True, 'candidate1_hashes_valid': True,
        'candidate2_hashes_valid': True, 'scientific_hashes_valid': True,
        'gui_checks': gui_counts,
    })
    baseline = (preflight / 'baseline.txt').read_text().strip()
    status = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True)
    subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=ROOT, check=True)
    (OUT / 'validation/final_git_status.txt').write_text(status)
    record = f'''# Final CLO-DSF validation record

Status: PASS. Frozen DEVELOPMENT candidate, ready for a separately generated unseen holdout.
No final holdout has been created, inspected or run. No scientific parameter search or post-confirmation tuning occurred.

- Committed baseline: {baseline}. The pre-existing user session edit is byte-identical. All {original_count} pre-existing tracked/result files match the initial snapshot. No pre-existing source, configuration, manifest or evidence file was modified. Candidate 1 and Candidate 2 historical hash verification passes.
- Historical gate: all 396 Candidate 2 validation cases replayed before final implementation; raw, summary and comparison metrics reproduced. No-origin-discount: 262 detected, 202 correct first origins, 60 UNKNOWN, zero wrong origins.
- Correction disclosed: the first campaign attempt used illegal injector settings and stopped after 16 completed runs. Its complete available artifacts remain under validation/invalid_attempt_01. Only invalid case-definition settings were corrected, before outcome metrics were inspected; fresh onset times prevent reuse. Detector and baseline parameters were unchanged. The unchanged C configuration validator accepted every corrected case before registration and execution.
- Confirmation: 900 unique corrected configurations (720 faults, 180 benign, 144 per origin). Zero exact physical overlap with Candidate 1/2 development, the excluded partial attempt or within this cohort. Seeds are recorded, but these deterministic injectors do not establish independent random replication. The entire registered valid cohort completed.
- Final result: 606/720 detected, 0/180 benign alarms, 511/547 plant-propagating faults detected, 36 silent plant cases. 462/606 first alarms localized, all correctly; 144 first-alarm UNKNOWN, 248 runs with any CONFIRMED+UNKNOWN step. Full traces contain no wrong localized steps. Weighted Sum has exactly the same binary detection outcomes and lower P95 latency (200 vs 300 ms).
- Identifiability: zero mixed-origin exact full allowed-observation histories; three mixed-origin full extracted-evidence histories. No empirical full-raw sensor/communication collision was found. The inherited composite origin map structurally abstains on SENSOR_CONTROL. Do not confuse feature-map information loss with universal non-identifiability of the raw observables.
- Statistical summaries include nominal Wilson intervals and exploratory paired outcomes. Designed related cases are correlated; no population safety guarantee or final-paper significance claim is made.
- Mathematical freeze: the reference algorithm, mappings, eight copied parameters, protocol, study, machine configuration and contract were hashed before optimization. Origin discount and propagation decision modulation are removed; diagnostic graph metadata cannot feed back into scientific decisions.
- Exact optimization: all 900 archived allowlisted observation streams (1,080,900 samples) replayed through both implementations. Entire persistent detector state bit-identical, zero tolerance and zero decision/timestamp discrepancies. Sparse products preserve floating-point accumulation order; logical cardinalities are cached. Generic dense/sparse/aliasing/total-conflict math checks pass.
- Complete suite: 258 tests PASS. New tests cover hidden-label independence, frame separation, vacuous evidence, temporal accumulation, recovery, strict persistence/margins, diagnostic independence, CSV bit-exact round trips, configuration legality, all cohort identities, paired counts and full equivalence.
- Build: original make and additive optimized build PASS. Python compile PASS. git diff --check PASS. No staged changes.
- Accepted regression: 48 legacy cases, 64 RTL cases and eight v5 representative replays PASS. Accepted lock verifies 141 source/config entries and 5866 evidence entries; v1–v6, HETIA, Hybrid, timing and HT1–HT4 remain unchanged.
- Desktop: {gui_counts['gui_final']} final-candidate checks and {gui_counts['gui_legacy']} unchanged legacy desktop checks PASS. New launcher preserves Hybrid default and historical views; live C examples and CONFIRMED+UNKNOWN work. Session/history/export writes are isolated. Display access required approved sandbox escalation. No GUI callback errors.
- Host benchmark: 31 measured interleaved repetitions per mode and scenario after three warmup cycles. Final optimized median overhead vs legacy is 166.98% benign / 145.85% timing; observed improvement vs reference only 1.12% / 0.65%. Raw samples, mean/std/P95, state and section sizes retained. Logging precision differs from historical implementations and is included in end-to-end cost. No embedded WCET, real-time deployment or broad lightweight claim.
- PNG/PDF development-confirmation plots and candid findings retained. Presentation label placement was corrected after visual review; this changed no scientific results.

Scientific pre-optimization identity: clo_dsf_final_scientific_hashes.json.
Complete accepted implementation/dependency/artifact identity: clo_dsf_final_hashes.json.
The complete manifest covers all v7.2 evidence (including the invalid partial attempt), builds, source/configuration/test/report/GUI dependencies and the immutable scientific contract. It excludes only itself, generated Python caches and compiler object/dependency intermediates. Executable identities are included; rebuilding with another compiler may change their byte hashes and requires independent equivalence validation.

Verify without writing: `python3 scripts/package_clo_dsf_final.py --verify`.
Build: `make -f clo_dsf_final_optimized.mk`.
GUI: `python3 scripts/virtual_ecu_final_gui.py`.

Final git status is retained in validation/final_git_status.txt. The single tracked modification is the user's unchanged pre-existing presets/gui_session_state.json edit; all v7.2 additions remain unstaged. No git add, commit, push, reset, restore, checkout or clean was run.
'''
    (OUT / 'validation_record.md').write_text(record)
    # Include complete build/runtime/evaluator/GUI dependencies, not only the optimized kernel.
    source_paths = set(ROOT / name for name in json.loads(SCIENCE.read_text())['sha256'])
    for folder in ['src', 'include', 'scripts', 'python', 'tests', 'presets', 'studies', 'config']:
        directory = ROOT / folder
        if directory.exists():
            source_paths.update(p for p in directory.rglob('*') if p.is_file() and
                                '__pycache__' not in p.parts and p.suffix not in {'.o', '.d', '.pyc'} and
                                p.name != 'gui_session_state.json')
    source_paths.update(ROOT.glob('*.mk'))
    source_paths.update(ROOT.glob('docs/clo_dsf*.md'))
    source_paths.update(ROOT / name for name in ['Makefile', 'GNUmakefile',
                        'virtual_ecu_v7_2_reference', 'virtual_ecu_v7_2_optimized'])
    artifacts = {p for p in OUT.rglob('*') if p.is_file() and p != MANIFEST and
                 '__pycache__' not in p.parts and p.suffix not in {'.o', '.d', '.pyc'}}
    write(MANIFEST, {
        'status': 'FROZEN PRE-HOLDOUT DEVELOPMENT CANDIDATE',
        'implementation_sealed_utc': datetime.now(timezone.utc).isoformat(),
        'baseline_commit': baseline, 'holdout_created': False,
        'mathematical_freeze_before_optimization': True,
        'reference_and_optimized_bit_identical': True,
        'scientific_hash_manifest': str(SCIENCE.relative_to(ROOT)),
        'sha256': {str(p.relative_to(ROOT)): sha(p) for p in sorted(source_paths | artifacts)},
    })
    verify()


if __name__ == '__main__':
    if sys.argv[1:] == ['--verify']:
        verify()
    elif not sys.argv[1:]:
        package()
    else:
        raise SystemExit('Usage: package_clo_dsf_final.py [--verify]')
