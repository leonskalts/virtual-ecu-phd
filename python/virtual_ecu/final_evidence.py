"""Immutable v1–v5 evidence access and v6 provenance; no simulation decisions."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import yaml

from .cross_layer_safety import PROJECT_ROOT, MODEL_TARGETS, STAGES
from .validation_v5_report import records

ROOT = PROJECT_ROOT
V5 = ROOT / 'results/cross_layer_safety_v5'
OUTPUT = ROOT / 'results/cross_layer_safety_v6'
PRESET = ROOT / 'studies/cross_layer_final_paper_study.yaml'
LOCK = ROOT / 'studies/cross_layer_final_evidence_lock.json'
GENERATOR = 'scripts/run_cross_layer_reproducibility_package.py'


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def safe_output(path):
    path = Path(path).resolve()
    protected = [ROOT / f'results/cross_layer_safety_v{i}' for i in range(1, 6)]
    protected.append(ROOT / 'results/paper_evidence_security_v1')
    protected.append(ROOT / 'results/rtl_hardware_trojan_study_v1')
    for accepted in protected:
        if path == accepted or path in accepted.parents or accepted in path.parents:
            raise ValueError(f'Output overlaps immutable evidence: {path}')
    return path


def read_lock():
    return json.loads(LOCK.read_text())


def verify_frozen():
    lock = read_lock()
    from .gui_execution import verify_gui_execution
    if 'scripts/virtual_ecu_gui.py' in lock['source_sha256']:
        verify_gui_execution(ROOT)
    for name, digest in lock['source_sha256'].items():
        # v6.1 permits presentation integration in both GUI containers.
        # The C simulator, detectors, configurations and accepted evidence stay pinned.
        if name in {'python/virtual_ecu/cross_layer_gui.py', 'scripts/virtual_ecu_gui.py'}:
            continue
        if not (ROOT / name).is_file() or sha256(ROOT / name) != digest:
            raise ValueError(f'Accepted scientific source/configuration changed: {name}')
    for name, digest in lock['accepted_evidence_sha256'].items():
        if not (ROOT / name).is_file() or sha256(ROOT / name) != digest:
            raise ValueError(f'Accepted evidence missing or changed: {name}')
    for folder in sorted({Path(name).parts[1] for name in lock['accepted_evidence_sha256']}):
        prefix = 'results/' + folder + '/'
        expected = {p for p in lock['accepted_evidence_sha256'] if p.startswith(prefix)}
        actual = {relative(p) for p in (ROOT / 'results' / folder).rglob('*') if p.is_file()}
        if actual != expected:
            raise ValueError(f'Accepted file set changed: {folder}')
    return {'source_files': len(lock['source_sha256']), 'accepted_evidence_files': len(lock['accepted_evidence_sha256']),
            'scientific_behavior_changed': False, 'baseline_commit': lock['baseline_commit']}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def write_csv(path, rows, columns=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = columns or list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='raise')
        writer.writeheader()
        writer.writerows({k: '' if row.get(k) is None else row.get(k, '') for k in columns} for row in rows)


def markdown_table(rows, columns=None):
    columns = columns or list(dict.fromkeys(k for row in rows for k in row))
    def cell(value):
        return ('N/A' if value is None or value == '' else str(value)).replace('|', '\\|').replace('\n', '<br>')
    return '\n'.join(['| ' + ' | '.join(columns) + ' |', '| ' + ' | '.join(['---'] * len(columns)) + ' |'] +
                     ['| ' + ' | '.join(cell(row.get(c)) for c in columns) + ' |' for row in rows]) + '\n'


def table_forms(path, rows):
    path = Path(path)
    write_csv(path.with_suffix('.csv'), rows)
    display = [{k.replace('_', ' '): f'{v:.2f}' if isinstance(v, float) else v.replace('_', ' ') if isinstance(v, str) else v
                for k, v in row.items()} for row in rows]
    path.with_suffix('.md').write_text(markdown_table(display))
    def tex(value):
        text = 'N/A' if value is None or value == '' else str(value)
        substitutions = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#',
                         '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
        return ''.join(substitutions.get(c, c) for c in text)
    columns = list(display[0])
    lines = [r'\begin{tabular}{' + 'l' * len(columns) + '}', r'\hline',
             ' & '.join(tex(c) for c in columns) + r' \\', r'\hline']
    lines += [' & '.join(tex(row.get(c)) for c in columns) + r' \\' for row in display]
    lines += [r'\hline', r'\end{tabular}']
    path.with_suffix('.tex').write_text('\n'.join(lines) + '\n')


def metric(filename, name, **filters):
    values = [r for r in records(V5 / filename) if r.get('metric') == name and all(r.get(k) == v for k, v in filters.items())]
    if len(values) != 1:
        raise ValueError(f'Expected one source metric: {filename}, {name}, {filters}; got {len(values)}')
    return values[0]


def final_configuration():
    frozen = json.loads((V5 / 'timing_monitor_contract.json').read_text())
    study = yaml.safe_load((ROOT / 'studies/cross_layer_v5_holdout.yaml').read_text())
    preset = yaml.safe_load(PRESET.read_text())
    constants = {}
    source = (ROOT / 'include/config.h').read_text()
    for name in ['ECU_DT_MS', 'ECU_CONTROL_PERIOD_MS', 'ECU_SENSOR_PERIOD_MS', 'ECU_LOG_PERIOD_MS',
                 'ECU_WARN_COOLANT_TEMP_C', 'ECU_CRITICAL_COOLANT_TEMP_C']:
        token = re.search(r'^#define ' + name + r' ([0-9.]+)[Uf]*$', source, re.M).group(1)
        constants[name] = float(token) if '.' in token else int(token)
    assert constants['ECU_CONTROL_PERIOD_MS'] == frozen['period_ms']
    assert constants['ECU_WARN_COOLANT_TEMP_C'] == study['hazard']['warning_threshold_c']
    assert constants['ECU_CRITICAL_COOLANT_TEMP_C'] == study['hazard']['critical_threshold_c']
    return {'accepted_baseline': read_lock()['baseline_commit'], 'scientific_behavior_modified': False,
            'unified_fault_fields': ['id', 'layer', 'model', 'target', 'behavior', 'start', 'duration', 'seed', 'model_parameters'],
            'custom_model_targets': MODEL_TARGETS, 'accepted_cross_layer_models': study['cross_layer']['models'],
            'propagation_stages': list(STAGES), 'hazard': study['hazard'], 'source_constants': constants,
            'timing_contract': frozen, 'recommended_monitor': preset['recommended_monitor'],
            'default_research_action': preset['default_research_action'], 'experimental_policies': preset['experimental_policies'],
            'legacy_cli_default': 'Timing monitor disabled unless requested; unchanged for compatibility. Final research preset selects combined observe-only.',
            'communication_observation': 'Existing freshness and detector alarm; no new threshold or detector.',
            'containment': 'Applicable, no preexisting hazard; coolant below warning with protection or resolved paired effects for recovery_hold_ms in final stable tail, and no prior hazard. Policy comparisons use fixed no-action actuator/plant eligibility.',
            'ftti': 'Injection-to-containment budget includes recovery hold; manifestation-origin clocks retained where available. Non-injection workload containment/FTTI is N/A.',
            'boundary': 'New timing monitor/policy use runtime telemetry. Legacy residuals use true plant state; diagnostic/bookkeeping scenario dependencies remain. Evaluation uses fault truth and reference trajectories.',
            'limitations': ['100 ms plant/monitor sampling; 1 ms modeled workload events', 'Modeled CPU occupancy; no embedded WCET',
                            'Trusted timing supervisor', 'Deterministic correlated design; descriptive Wilson intervals',
                            'No new holdout hazards', 'Experimental hazard/FTTI; no full vehicle dynamics or certification'],
            'source_locations': ['include/config.h', 'include/cross_layer_fault.h', 'src/cross_layer_fault.c', 'src/hazard_model.c',
                                 'src/timing_safety_monitor.c', 'src/runtime_timing_observation.c', 'src/safety_policy_v5.c',
                                 'src/scheduler_stress.c', 'python/virtual_ecu/validation_v5_metrics.py',
                                 'docs/detector_observability_boundary.md', 'studies/cross_layer_v5_holdout.yaml']}


def artifact_manifest(out):
    """Index immutable evidence in place, plus generated publication inputs/outputs.

    Exclude this index itself (no recursive self-hash), ephemeral executions, GUI
    logs and mode completion records. Never put wall-clock timestamps in the index.
    """
    out = Path(out)
    old = {r['relative_path']: r for r in records(out / 'manifests/artifact_manifest.csv')} if (out / 'manifests/artifact_manifest.csv').exists() else {}
    paths = {ROOT / p for p in read_lock()['accepted_evidence_sha256']}
    paths.update(ROOT / p for p in read_lock()['source_sha256'])
    paths.update(p for folder in ['docs', 'studies', 'python/virtual_ecu', 'scripts', 'tests'] for p in (ROOT / folder).glob('*')
                 if p.is_file() and ('final_' in p.name or 'reproducibility' in p.name or p.name in ['cross_layer_platform_user_guide.md', 'cross_layer_platform_architecture.md', 'independent_validation_roadmap.md']))
    # Include v6.1/v6.2 presentation dependencies in newly generated inventories;
    # the accepted manifest and evidence lock are never rewritten.
    paths.update(ROOT / name for name in (
        'python/virtual_ecu/gui_design.py', 'python/virtual_ecu/gui_workflows.py',
        'python/virtual_ecu/cross_layer_ui.py', 'python/virtual_ecu/gui_execution.py',
        'python/virtual_ecu/gui_execution_lock.json', 'tests/test_gui_ux.py',
        'tests/gui_v61_desktop_checks.py', 'tests/gui_window_capture.py',
        'tests/fixtures/gui_v6_commands.json',
        'python/virtual_ecu/research_analysis_gui.py', 'tests/test_gui_v62.py',
        'tests/gui_v62_desktop_checks.py', 'docs/gui_v62_validation.md',
    ) if (ROOT / name).is_file())
    paths.update(p for p in out.rglob('*') if p.is_file() and not any(x in p.relative_to(out).parts for x in ['validation', 'runtime', 'full_reproduction'])
                 and p.name not in ['artifact_manifest.csv', 'analysis_reproducibility.json'])
    session_record = out / 'validation/session_validation.md'
    if session_record.is_file():
        paths.add(session_record)
    result = []
    for path in sorted(paths):
        try:
            name = relative(path)
        except ValueError:
            name = str(path)  # Explicitly external output roots; accepted sources stay repository-relative.
        digest = sha256(path)
        rows = None
        if path.suffix == '.csv':
            if name in old and old[name]['sha256'] == digest:
                rows = old[name]['row_count']
            else:
                with path.open(newline='') as stream:
                    rows = max(0, sum(1 for _ in csv.reader(stream)) - 1)
        match = re.search(r'cross_layer_safety_v([1-6])', str(path))
        version = 'v' + match.group(1) if match else 'HETIA' if 'paper_evidence_security' in str(path) else 'RTL' if 'rtl_hardware_trojan_study_v1' in str(path) else 'source'
        if out == path or out in path.parents:
            version = 'v6'
        kind = 'raw_evidence' if 'raw' in path.parts else 'figure' if path.suffix == '.png' else 'configuration' if path.suffix in ['.yaml', '.json'] else 'table' if path.suffix in ['.csv', '.tex'] else 'documentation' if path.suffix == '.md' else 'source_or_binary'
        provenance = {
            'v1': ('results/cross_layer_safety_v1/cross_layer_safety_summary.md', 'scripts/run_cross_layer_safety_study.py'),
            'v2': ('results/cross_layer_safety_v2/study_config.json', 'scripts/run_cross_layer_campaign.py'),
            'v3': ('results/cross_layer_safety_v2/study_config.json', 'scripts/analyze_cross_layer_safety.py'),
            'v4': ('studies/timing_monitor_validation_v1.yaml;studies/communication_safety_response_v1.yaml', 'scripts/run_runtime_safety_studies.py'),
            'v5': ('studies/cross_layer_v5_holdout.yaml', 'scripts/run_cross_layer_v5_validation.py'),
            'v6': (relative(PRESET), GENERATOR),
            'HETIA': ('results/paper_evidence_security_v1/README.md', 'scripts/export_paper_evidence_security_v1.py'),
            'RTL': ('scripts/run_rtl_hardware_trojan_study.py', 'scripts/run_rtl_hardware_trojan_study.py'),
            'source': (relative(PRESET), 'Authored source/configuration; not generated'),
        }
        config, generator = provenance[version]
        result.append({'relative_path': name, 'artifact_type': kind, 'study_version': version,
                       'description': path.stem.replace('_', ' '), 'row_count': rows, 'file_size': path.stat().st_size,
                       'sha256': digest, 'source_configuration': config, 'generated_by_script': generator,
                       'timestamp': None})
    write_csv(out / 'manifests/artifact_manifest.csv', result)
    return result


def verify_artifact_manifest(out):
    rows = records(Path(out) / 'manifests/artifact_manifest.csv')
    for row in rows:
        path = ROOT / row['relative_path']
        if not path.is_file() or sha256(path) != row['sha256']:
            raise ValueError(f'Artifact manifest mismatch: {path}')
    return len(rows)
