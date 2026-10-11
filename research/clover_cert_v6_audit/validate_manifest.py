#!/usr/bin/env python3
"""Read-only source/provenance validation. Writes reports only inside this audit.

Standard-library structural schema checks deliberately avoid new dependencies.
A successful structural check does NOT discharge UNVERIFIED trust/timing claims.
Run --self-test --check-preservation for the full local audit verification.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[1]
STATUS = {'VERIFIED', 'INFERRED', 'UNVERIFIED'}
VISIBILITY = {'RUNTIME_PUBLISHED_MODEL', 'RUNTIME_OPTIONAL_MODEL',
              'RUNTIME_PUBLISHED_ORACLE_DERIVED', 'GROUND_TRUTH_ONLY',
              'UNVERIFIED_RUNTIME'}


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1048576), b''):
            result.update(chunk)
    return result.hexdigest()


def source_path(value):
    if not isinstance(value, str) or not value or Path(value).is_absolute() or '..' in Path(value).parts:
        raise ValueError('Source path must be a nonempty relative path without traversal')
    path = (ROOT / value).resolve()
    if ROOT not in path.parents or path == AUDIT or AUDIT in path.parents:
        raise ValueError('Anchor must reference implementation outside the audit, within the repository')
    if path.suffix not in {'.c', '.h', '.py', '.mk'} and path.name not in {'Makefile', 'GNUmakefile'}:
        raise ValueError('Documentation/output is not implementation proof')
    return path


def validate_document(document):
    errors, findings = [], []
    def error(where, message): errors.append({'location': where, 'message': message})
    def finding(where, message): findings.append({'location': where, 'message': message})
    if not isinstance(document, dict):
        return [{'location': '$', 'message': 'Manifest must be an object'}], []
    required = {'schema_version': str, 'git_commit': str, 'scope': dict,
                'source_files': list, 'anchors': list, 'assumptions': list,
                'trust_domains': list, 'evidence': list, 'timing': list,
                'fault_origins': list, 'provenance_edges': list, 'ground_truth_only_fields': list,
                'cases': list, 'modeling_candidates': list, 'audit_verdict': dict}
    for key, kind in required.items():
        if not isinstance(document.get(key), kind) or not document.get(key):
            error(key, 'Missing/nonempty ' + kind.__name__ + ' required')
    if errors: return errors, findings
    if document['schema_version'] != 'CLOVER_CERT_V6': error('schema_version', 'Wrong version')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', document['git_commit']) or document['git_commit'] != commit:
        error('git_commit', 'Invalid or different HEAD; do not silently re-anchor another snapshot')
    sections = ('anchors', 'assumptions', 'trust_domains', 'evidence', 'timing', 'fault_origins', 'cases', 'modeling_candidates', 'provenance_edges')
    indexes = {}
    for section in sections:
        index = {}
        for number, item in enumerate(document[section]):
            where = f'{section}[{number}]'
            if not isinstance(item, dict): error(where, 'Object required'); continue
            ident = item.get('id')
            if not isinstance(ident, str) or not ident or ident in index:
                error(where, 'Missing/duplicate ID'); continue
            index[ident] = item
            if item.get('status') not in STATUS: error(ident, 'Explicit VERIFIED/INFERRED/UNVERIFIED status required')
        indexes[section] = index
    def text(item, field):
        if not isinstance(item.get(field), str) or not item[field].strip():
            error(item.get('id', '?'), 'Missing nonempty string: ' + field)
    def refs(item, field, section, nonempty=True):
        values = item.get(field)
        if not isinstance(values, list) or (nonempty and not values):
            error(item.get('id', '?'), 'Missing reference list: ' + field); return
        for value in values:
            if not isinstance(value, str) or value not in indexes[section]:
                error(item.get('id', '?'), f'Unknown {field} reference: {value!r}')
    def anchors(item): refs(item, 'anchors', 'anchors')
    file_index, contents = {}, {}
    for entry in document['source_files']:
        if not isinstance(entry, dict): error('source_files', 'Object required'); continue
        name = entry.get('path')
        try:
            path = source_path(name)
            if name in file_index: raise ValueError('Duplicate source path')
            if entry.get('git_tracking') not in {'tracked', 'pre-existing untracked'}: raise ValueError('Missing tracking classification')
            if not path.is_file(): raise ValueError('Source file does not exist')
            expected = entry.get('sha256', '')
            if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected) or digest(path) != expected:
                raise ValueError('Source hash differs from audited working-tree snapshot')
            contents[name] = path.read_text().splitlines()
            file_index[name] = entry
        except (ValueError, OSError, UnicodeError) as exc: error(str(name), str(exc))
    for ident, anchor in indexes['anchors'].items():
        for field in ('path', 'token', 'function', 'meaning', 'scope'): text(anchor, field)
        line, name, token = anchor.get('line'), anchor.get('path'), anchor.get('token')
        if not isinstance(name, str) or name not in file_index: error(ident, 'Anchor file missing from verified source inventory'); continue
        if type(line) is not int or line < 1 or line > len(contents[name]): error(ident, 'Invalid 1-based source line'); continue
        if not isinstance(token, str) or not token or '\n' in token or token not in contents[name][line - 1]:
            error(ident, 'Exact source token is absent from the specified line')
        if anchor.get('status') != 'VERIFIED': error(ident, 'Catalog records must be verified source anchors; place unknown claims in assumptions')
    # Every sourced record carries references; no VERIFIED claim without anchors.
    for section in ('assumptions', 'trust_domains', 'evidence', 'timing', 'cases', 'modeling_candidates', 'provenance_edges'):
        for item in indexes[section].values(): anchors(item)
    for item in indexes['assumptions'].values():
        text(item, 'statement'); text(item, 'resolution')
        if item.get('status') == 'UNVERIFIED': finding(item['id'], item.get('statement', 'Unverified assumption'))
    for item in indexes['trust_domains'].values():
        text(item, 'members'); refs(item, 'assumptions', 'assumptions'); refs(item, 'shared_with', 'trust_domains', False)
        if item.get('isolation_status') not in STATUS: error(item['id'], 'Missing isolation status')
        if item.get('isolation_status') != 'VERIFIED': finding(item['id'], 'Logical grouping does not establish protected independent fault domain')
    for item in indexes['evidence'].values():
        if item.get('visibility') not in VISIBILITY: error(item['id'], 'Explicit evidence visibility classification required')
        if not isinstance(item.get('fields'), list) or not item['fields'] or not all(isinstance(x,str) and x for x in item['fields']): error(item['id'], 'Nonempty field-name list required')
        text(item, 'availability'); refs(item, 'domains', 'trust_domains'); refs(item, 'assumptions', 'assumptions'); refs(item, 'depends_on', 'evidence', False)
        if item.get('physical_independence') not in STATUS: error(item['id'], 'Physical independence status missing')
        if item.get('visibility') == 'UNVERIFIED_RUNTIME' and item.get('status') != 'UNVERIFIED': error(item['id'], 'Unavailable runtime witness cannot be VERIFIED')
        if item.get('visibility') in {'UNVERIFIED_RUNTIME', 'RUNTIME_PUBLISHED_ORACLE_DERIVED'}:
            finding(item['id'], item.get('availability', 'Input requires qualification'))
    for item in indexes['timing'].values():
        text(item, 'description'); refs(item, 'assumptions', 'assumptions')
        if item.get('status') == 'UNVERIFIED':
            text(item, 'unverified_reason'); finding(item['id'], item.get('unverified_reason', 'Unverified timing'))
    for item in indexes['fault_origins'].values():
        for field in ('family', 'definition', 'build_variant', 'attribution'): text(item, field)
        refs(item, 'injection_anchors', 'anchors'); refs(item, 'runtime_evidence', 'evidence')
        refs(item, 'ground_truth_only', 'evidence'); refs(item, 'timing', 'timing'); refs(item, 'provenance_dependencies', 'evidence')
        refs(item, 'shared_fault_domains', 'trust_domains'); refs(item, 'assumptions', 'assumptions')
        for field in ('affected_state', 'propagation', 'indistinguishable_origins'):
            if not isinstance(item.get(field), list) or not item[field] or not all(isinstance(v,str) and v for v in item[field]): error(item['id'], 'Missing string list: ' + field)
        for key in item.get('ground_truth_only', []):
            if isinstance(key, str) and key in indexes['evidence'] and indexes['evidence'][key].get('visibility') != 'GROUND_TRUTH_ONLY': error(item['id'], 'Ground-truth list contains runtime evidence')
        for key in item.get('runtime_evidence', []):
            if isinstance(key, str) and key in indexes['evidence'] and indexes['evidence'][key].get('visibility') == 'GROUND_TRUTH_ONLY': error(item['id'], 'Oracle metadata misclassified as runtime witness')
        earliest = item.get('earliest_observable')
        if not isinstance(earliest, dict): error(item['id'], 'Earliest observability object required'); continue
        if earliest.get('status') not in STATUS: error(item['id'], 'Earliest timing needs explicit status')
        text(earliest, 'condition'); anchors(earliest)
        if 'guaranteed_bound_ms' not in earliest: error(item['id'], 'Explicit null or sourced timing bound required')
        bound = earliest.get('guaranteed_bound_ms')
        if bound is None: finding(item['id'], 'No unconditional guaranteed fault-to-observation bound; see conditional earliest_observable')
        elif type(bound) is not int or bound < 0 or earliest.get('status') != 'VERIFIED': error(item['id'], 'A finite guaranteed bound requires VERIFIED timing support')
    edge_pairs = set()
    for item in indexes['provenance_edges'].values():
        text(item, 'meaning'); refs(item, 'assumptions', 'assumptions')
        pair = (item.get('from'), item.get('to'))
        if not all(isinstance(v,str) and v in indexes['evidence'] for v in pair):
            error(item['id'], 'Unknown provenance edge endpoint'); continue
        if pair in edge_pairs: error(item['id'], 'Duplicate provenance edge')
        edge_pairs.add(pair)
        if item.get('kind') not in {'physical_input_to_measurement_model', 'operating_context_model_input', 'conditional_transport_publication', 'runtime_or_model_dataflow', 'oracle_input_to_published_legacy_output'}:
            error(item['id'], 'Explicit supported dependency kind required')
    expected_pairs = {(dep, e['id']) for e in indexes['evidence'].values() for dep in e.get('depends_on',[]) if isinstance(dep,str)}
    if edge_pairs != expected_pairs: error('provenance_edges', 'Typed edges must cover exactly the evidence dependency lists')
    ground = document['ground_truth_only_fields']
    if not all(isinstance(x,dict) for x in ground): error('ground_truth_only_fields', 'Objects required')
    else:
        expected = {key: value.get('fields') for key, value in indexes['evidence'].items() if value.get('visibility') == 'GROUND_TRUTH_ONLY'}
        actual = {entry.get('evidence_id'): entry.get('fields') for entry in ground if isinstance(entry.get('evidence_id'),str)}
        if actual != expected or len(actual) != len(ground): error('ground_truth_only_fields', 'Ground-truth inventory inconsistent')
    if set(indexes['cases']) != {f'CASE_{i}' for i in range(1,6)}: error('cases', 'Exactly the five critical cases required')
    for item in indexes['cases'].values():
        for field in ('title', 'analysis', 'conditional_result'): text(item, field)
        refs(item, 'fault_origins', 'fault_origins'); refs(item, 'evidence', 'evidence'); refs(item, 'timing', 'timing'); refs(item, 'assumptions', 'assumptions')
        if not isinstance(item.get('competing_explanations'),list) or len(item['competing_explanations'])<2: error(item['id'], 'Competing explanations required')
        if item.get('verdict') != 'UNKNOWN': error(item['id'], 'Unresolved critical cases must abstain; this audit establishes no unconditional origin certificate')
    for item in indexes['modeling_candidates'].values():
        text(item, 'scope'); refs(item, 'blocked_by', 'assumptions')
    if document['audit_verdict'].get('algorithm_implemented') is not False: error('audit_verdict', 'This is an audit, not an implementation')
    return errors, findings


def check_preservation():
    baseline = json.loads((AUDIT / 'workspace_baseline.json').read_text())
    current = set()
    for directory, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d != '.git' and Path(directory) / d != AUDIT]
        current.update((Path(directory) / name).relative_to(ROOT).as_posix() for name in names)
    expected = baseline['files']
    changed, unreadable = [], []
    for name in sorted(current & set(expected)):
        path, entry = ROOT / name, expected[name]
        try:
            same = path.is_symlink() and os.readlink(path) == entry['symlink'] if 'symlink' in entry else (not path.is_symlink() and path.stat().st_size == entry['size'] and digest(path) == entry['sha256'])
            if not same: changed.append(name)
        except OSError as exc: unreadable.append({'path':name,'error':str(exc)})
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    return {'status':'PASS' if not changed and not unreadable and current == set(expected) and commit == baseline['git_commit'] else 'FAIL',
            'files_checked':len(expected),'bytes_in_baseline':sum(x.get('size',0) for x in expected.values()),
            'changed':changed,'added_outside_audit':sorted(current-set(expected)),
            'missing':sorted(set(expected)-current),'unreadable':unreadable,'git_commit_unchanged':commit==baseline['git_commit']}


def self_test(document):
    mutations = [
        ('wrong schema version', lambda d: d.update(schema_version='invented')),
        ('missing evidence collection', lambda d: d.pop('evidence')),
        ('duplicate anchor', lambda d: d['anchors'].append(copy.deepcopy(d['anchors'][0]))),
        ('missing source file', lambda d: d['source_files'][0].update(path='src/no_such_clover_source.c')),
        ('absolute source path', lambda d: d['source_files'][0].update(path='/etc/passwd')),
        ('line zero', lambda d: d['anchors'][0].update(line=0)),
        ('line past EOF', lambda d: d['anchors'][0].update(line=10**9)),
        ('boolean line number', lambda d: d['anchors'][0].update(line=True)),
        ('wrong exact token', lambda d: d['anchors'][0].update(token='TOKEN_NOT_PRESENT_CLOVER_AUDIT')),
        ('source hash mismatch', lambda d: d['source_files'][0].update(sha256='0'*64)),
        ('missing visibility', lambda d: d['evidence'][0].pop('visibility')),
        ('missing trust assumption', lambda d: d['trust_domains'][0].update(assumptions=[])),
        ('unknown dependency', lambda d: d['evidence'][0].update(depends_on=['MISSING'])),
        ('unexplained unverified timing', lambda d: d['timing'][-1].pop('unverified_reason')),
        ('anchorless verified claim', lambda d: d['timing'][0].update(anchors=[])),
        ('unsupported guaranteed bound', lambda d: d['fault_origins'][0]['earliest_observable'].update(guaranteed_bound_ms=1)),
        ('oracle promoted to runtime', lambda d: d['fault_origins'][0].update(runtime_evidence=['E_TRUTH'])),
        ('unsupported origin claim', lambda d: d['cases'][0].update(verdict='MEMORY')),
        ('missing typed provenance edge', lambda d: d['provenance_edges'].pop()),
        ('invalid dependency kind', lambda d: d['provenance_edges'][0].update(kind='independent_by_name')),
    ]
    checks = []
    for name, mutate in mutations:
        candidate = copy.deepcopy(document); mutate(candidate)
        errors, _ = validate_document(candidate)
        checks.append({'name':name,'passed':bool(errors)})
    checks.append({'name':'valid manifest retains unresolved findings',
                   'passed':not validate_document(document)[0] and bool(validate_document(document)[1])})
    return {'status':'PASS' if all(c['passed'] for c in checks) else 'FAIL','checks':checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=AUDIT/'fault_provenance_manifest.json')
    parser.add_argument('--report', type=Path, default=AUDIT/'validation_report.json')
    parser.add_argument('--check-preservation', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--strict-unresolved', action='store_true', help='Exit 2 when structural validation passes but unresolved findings remain')
    args = parser.parse_args()
    destination = args.report.resolve()
    if AUDIT not in destination.parents:
        parser.error('Report writes must remain inside research/clover_cert_v6_audit/')
    try:
        document = json.loads(args.manifest.read_text())
        errors, findings = validate_document(document)
    except (ValueError, OSError, TypeError) as exc:
        document = {}; errors = [{'location':'$','message':str(exc)}]; findings = []
    report = {'status':'INVALID' if errors else 'STRUCTURALLY_VALID_WITH_UNRESOLVED_FINDINGS' if findings else 'STRUCTURALLY_VALID',
              'errors':errors,'unresolved_findings':findings,
              'counts':{key:len(document.get(key,[])) if isinstance(document,dict) and isinstance(document.get(key,[]),list) else 0 for key in ('source_files','anchors','fault_origins','evidence','timing','cases','provenance_edges')},
              'scope':'Validates schema, references, exact source tokens/hashes and explicit qualifications; does not prove physical independence, semantic completeness or origin attribution.'}
    if args.self_test and not errors: report['validator_self_tests'] = self_test(document)
    if args.check_preservation: report['workspace_preservation'] = check_preservation()
    (AUDIT/'git_status_after.txt').write_bytes(subprocess.check_output(['git','status','--short','--untracked-files=all'],cwd=ROOT))
    destination.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(report['status'])
    print(json.dumps(report['counts'],sort_keys=True))
    print(f'Structural/source errors: {len(errors)}; unresolved findings: {len(findings)}')
    for key in ('validator_self_tests','workspace_preservation'):
        if key in report: print(key+': '+report[key]['status'])
    print('Report: '+str(destination.relative_to(ROOT)))
    failed = errors or any(report.get(key,{}).get('status')=='FAIL' for key in ('validator_self_tests','workspace_preservation'))
    return 1 if failed else 2 if findings and args.strict_unresolved else 0


if __name__ == '__main__':
    sys.exit(main())
