"""Read-only scientific reanalysis of accepted cross-layer CSV evidence.

No simulator execution, detector decisions, or writes to input evidence occur here.
Propagation timestamps are taken from the full-precision C monitor, not recomputed
from rounded CSV actuator or temperature columns.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from .cross_layer_safety import PROJECT_ROOT, read_rows, summarize_rows, STAGES, METRICS, V2_METRICS

DEFAULT_INPUT = PROJECT_ROOT / 'results/cross_layer_safety_v2'
DEFAULT_OUTPUT = PROJECT_ROOT / 'results/cross_layer_safety_v3'
FTTI_CANDIDATES = (1000, 2000, 5000, 10000)
GROUPS = ('fault_layer', 'fault_model', 'fault_behavior', 'operating_profile')
SC_CLASSES = ('SC0', 'SC1', 'SC2', 'SC3')
SEVERITIES = ('S0_NO_EFFECT', 'S1_INTERNAL_ONLY', 'S2_ECU_VISIBLE',
              'S3_ACTUATOR_OR_PLANT', 'S4_CRITICAL_TRANSIENT', 'S5_SUSTAINED_HAZARD')
TIMING_CLASSES = ('A_NO_DOWNSTREAM', 'B_CONTROL_ONLY', 'C_ACTUATOR', 'D_PLANT', 'E_HAZARD')


def number(value):
    if value in (None, '', 'N/A'):
        return None
    return float(value)


def timestamp(row, key):
    value = number(row.get(key))
    return int(value) if value is not None and value >= 0 else None


def typed(row):
    result = {}
    for key, value in row.items():
        if value in ('', None, 'N/A'):
            result[key] = None
        else:
            try:
                result[key] = int(value)
            except (ValueError, TypeError):
                result[key] = value
    return result


def write_table(path, rows, columns=None):
    """Also write a header for an empty selection; empty is valid evidence."""
    columns = columns or list(dict.fromkeys(k for r in rows for k in r))
    if not columns:
        raise ValueError(f'No schema for {path}')
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def hazard_states(samples, allowance_ms):
    """Use authoritative C threshold flags to avoid rounding boundary errors.

    Each input is (timestamp, warning_active, critical_active). Exposure integrates
    completed intervals. RECOVERED means below warning after an excursion; it
    does not assert fault recovery or containment. A final critical sample has
    no invented following interval.
    """
    previous_time = None
    previous_critical = False
    critical_start = None
    excursion = False
    exposure = 0
    for now, warning, critical in samples:
        if previous_time is not None and now <= previous_time:
            raise ValueError('Hazard samples must have strictly increasing times')
        if critical and not warning:
            raise ValueError('Critical must imply warning')
        if previous_critical:
            exposure += now - previous_time
        if critical and not previous_critical:
            critical_start = now
        consecutive = now - critical_start if critical else 0
        excursion |= warning
        state = ('HAZARD_SUSTAINED' if consecutive >= allowance_ms else 'CRITICAL_TRANSIENT') if critical else (
            'WARNING' if warning else 'RECOVERED' if excursion else 'NORMAL')
        yield {'time_ms': now, 'hazard_state': state,
               'critical_exposure_ms': exposure, 'consecutive_critical_ms': consecutive}
        previous_time, previous_critical = now, critical


def interval(start, end):
    # Signed: a negative result means the alarm preceded this manifestation.
    return None if start is None or end is None else end - start


def ftti_result(start, containment, hazard, end, budget, applicable=True):
    if not applicable or start is None:
        return None
    if hazard == 1:
        return 0
    if hazard is None:
        return None
    if containment is not None:
        return int(0 <= containment - start <= budget)
    return 0 if end - start >= budget else None


def classify_consequence(row):
    if row.get('injected') != 1:
        return 'NOT_APPLICABLE', 'NOT_APPLICABLE'
    hazard, critical = row.get('attributable_hazard'), row.get('post_injection_critical')
    actuator = row.get('actuator_any_effect') == 1
    plant = row.get('plant_manifestation') == 1
    control = row.get('control_effect') == 1 or row.get('sensing_visible_effect') == 1
    internal = row.get('internal_corruption') == 1
    if any(row.get(k) is None for k in ('internal_corruption', 'control_effect',
                                        'actuator_any_effect', 'plant_manifestation', 'detected')):
        return 'UNAVAILABLE', 'UNAVAILABLE'
    severity = (SEVERITIES[5] if hazard == 1 else SEVERITIES[4] if critical == 1 and plant else
                SEVERITIES[3] if actuator or plant else SEVERITIES[2] if control else
                SEVERITIES[1] if internal else SEVERITIES[0])
    alarm = row.get('propagation_detector_ms')
    hazard_time = row.get('hazard_entry_ms')
    if hazard is None:
        return 'UNAVAILABLE', 'UNAVAILABLE'
    if hazard == 1 and hazard_time is None:
        return severity, 'UNAVAILABLE'
    # SC3 includes late alarms, and thus is not necessarily a subset of legacy silent_corruption.
    if hazard == 1 and hazard_time is not None and (alarm is None or alarm >= hazard_time):
        silent = 'SC3'
    elif row['detected'] == 1:
        silent = 'DETECTED'
    elif hazard is None:
        silent = 'UNAVAILABLE'
    elif actuator or plant:
        silent = 'SC2'
    elif control:
        silent = 'SC1'
    elif internal:
        silent = 'SC0'
    else:
        silent = 'NO_EFFECT'
    return severity, silent


def containment_classification(row):
    """Require observed cooling-command/feedback or plant propagation.

    Retain the v2 stable-tail contract, but do not count internal/sensing/control
    metadata-only cases as successful containment. Recovery and protection are
    separate dimensions; neither alone proves containment.
    """
    if row.get('injected') != 1 or row.get('preexisting_hazard') == 1:
        return None, 'NOT_APPLICABLE'
    start = row.get('first_safety_relevant_manifestation_ms')
    if start is None:
        return None, 'NO_CONTAINMENT_REQUIRED'
    if row.get('attributable_hazard') == 1:
        return 0, 'FAILED_CONTAINMENT_HAZARD'
    success = row.get('legacy_v2_containment')
    confirmation = row.get('containment_time_ms')
    if success == 1 and confirmation is not None and confirmation >= start:
        plant = row.get('propagation_plant_ms')
        return 1, 'CONTAINED_BEFORE_PLANT' if plant is None or confirmation < plant else 'CONTAINED_AFTER_PLANT_BEFORE_HAZARD'
    if success is None or (success == 1 and (confirmation is None or confirmation < start)):
        return None, 'UNRESOLVED_CONTAINMENT'
    if row.get('protective_response_active_end') == 1:
        return 0, 'PROTECTIVE_RESPONSE_ACTIVE'
    if row.get('detected') == 1:
        return 0, 'DETECTED_NOT_CONTAINED'
    if row.get('fault_recovered') == 1:
        return 0, 'FAULT_RECOVERED'
    return 0, 'UNCONTAINED_AT_END'


def diagnose_miss(row):
    """Bounded evidence-based statements, not speculative causal explanations."""
    if row.get('detected') != 0:
        return 'NOT_APPLICABLE', 'A differential detector alarm was observed.'
    if row.get('safety_severity') == SEVERITIES[0]:
        return 'NO_OBSERVABLE_RUNTIME_EFFECT', 'No C propagation stage was reached; an injected constraint alone is not corruption.'
    if row.get('fault_layer') == 'timing' and row.get('scheduler_event_seen') == 1:
        return 'TIMING_EVENT_NOT_EXPOSED_TO_CURRENT_DETECTOR', (
            'Execution/deadline telemetry records the event; detection_algorithm.c and safety_monitor.c do not consume it. '
            'Physical score and downstream consequences are reported separately; absence of this input is not proof a timing monitor would be useful in every case.')
    if row.get('safety_severity') == SEVERITIES[1]:
        return 'INTERNAL_ONLY_EFFECT', 'Internal corruption was recorded without sensing, control, actuator, or plant propagation.'
    score = row.get('max_runtime_detection_score')
    if score is not None and score < 0.9 and row.get('detector') == 'hybrid_adaptive_kalman':
        return 'COMBINED_SCORE_BELOW_CURRENT_CONFIRMATION_FLOOR', (
            f'Maximum logged combined score {score:.6f} stays below the fixed 0.900 confirmation floor; '
            'no direct fast alarm fired. Individual innovation/support branches are not logged, so a finer root cause is unresolved.')
    return 'UNRESOLVED', 'Telemetry does not establish which unlogged support or persistence condition prevented confirmation.'


def analyze_run(campaign_row, trace, reference):
    row = typed(campaign_row)
    last = trace[-1]
    injection = row.get('fault_injection_ms')
    end = int(last['time_ms'])
    row['observation_end_ms'] = end
    row['legacy_v2_containment'] = row.get('containment_success')
    row['injection_based_experimental_ftti'] = row.get('ftti_met')
    row['legacy_v2_silent_corruption'] = row.get('silent_corruption')
    row['actuator_any_effect'] = (int(row.get('actuator_effect') == 1 or row.get('actuator_realization_effect') == 1)
                                  if row.get('actuator_effect') is not None and row.get('actuator_realization_effect') is not None else None)
    # The internal sensing comparator observes measurement residual or packet age.
    # Its timestamp is defensible as sensing-visible for these actual targets only.
    row['sensing_visible_effect'] = int(row.get('internal_corruption') == 1 and row.get('fault_target') == 'coolant_sensor')
    row['first_internal_manifestation_ms'] = row.get('propagation_internal_ms')
    row['first_plant_manifestation_ms'] = row.get('propagation_plant_ms')
    origins = [(row.get(k), k) for k in ('propagation_actuator_command_ms', 'propagation_actuator_realization_ms', 'propagation_plant_ms') if row.get(k) is not None]
    origin = min(origins) if origins else (None, None)
    row['first_safety_relevant_manifestation_ms'], row['safety_relevant_manifestation_source'] = origin
    row['attributable_hazard'] = row.get('hazard_entered') if row.get('preexisting_hazard') == 0 and injection is not None else None
    post = [r for r in trace if injection is not None and int(r['time_ms']) >= injection]
    hazard_available = last.get('hazard_monitor_enabled') == '1'
    row['post_injection_critical'] = int(any(r.get('critical_active') == '1' for r in post)) if hazard_available else None
    row['protective_response_active_end'] = int(last['safe_state_id']) > 0
    row['fault_recovery_seen'] = int(any(r.get('current_fault_phase') == 'recovered' or r.get('last_recovery_ms', '') not in ('', '-1') for r in post))
    # Legacy activation is explicit in fault_mode_id; do not infer recovery from duration.
    row['fault_recovered'] = int(bool(post) and (last.get('current_fault_phase') == 'recovered' if last.get('cross_layer_fault_enabled') == '1' else last.get('fault_mode_id') == '0')) if injection is not None else None
    row['fault_recovery_status'] = 'FAULT_RECOVERED' if row['fault_recovered'] else 'ACTIVE_OR_UNOBSERVED' if injection is not None else 'NOT_APPLICABLE'
    for out, source in (
        ('max_physical_deviation_c', 'plant_coolant_deviation_c'),
        ('max_runtime_detection_score', 'runtime_detection_score'),
        ('max_sample_age_ms', 'coolant_sensor_update_age_ms'),
        ('max_control_target_deviation_c', 'control_target_deviation_c'),
        ('max_pump_tracking_error', 'pump_tracking_error'),
        ('max_fan_tracking_error', 'fan_tracking_error'),
        ('max_legacy_truth_sensor_residual_c', 'coolant_sensor_residual_c'),
    ):
        values = [abs(number(r[source])) for r in post if number(r.get(source)) is not None]
        row[out] = max(values) if values else None
    deviations = [number(r.get('plant_coolant_deviation_c')) for r in post if number(r.get('plant_coolant_deviation_c')) is not None]
    row['max_signed_physical_deviation_c'] = max(deviations) if deviations else None
    row['min_signed_physical_deviation_c'] = min(deviations) if deviations else None
    row['raw_alarm_seen_after_injection'] = int(any(r.get('runtime_detection_alarm') == '1' for r in post)) if post else None
    row['first_alarm_evidence_label'] = next((r.get('runtime_detection_label') for r in post if int(r['time_ms']) == row.get('propagation_detector_ms')), None)
    row['scheduler_event_seen'] = int(any(r.get('execution_skipped') == '1' or r.get('deadline_missed') == '1' for r in post)) if post else None
    row['max_execution_gap_ms'] = max((int(r['time_ms'])-int(r['control_task_last_execution_ms']) for r in post if r.get('control_task_last_execution_ms', '') not in ('', '-1')), default=None)
    row['max_weak_score_streak_samples'] = 0 if post else None
    streak = 0
    for r in post:
        score = number(r.get('runtime_detection_score'))
        streak = streak + 1 if score is not None and score >= .9 else 0
        row['max_weak_score_streak_samples'] = max(row['max_weak_score_streak_samples'], streak)
    paired = [(r, reference[int(r['time_ms'])]) for r in post if int(r['time_ms']) in reference]
    row['differential_diagnostic_seen'] = int(any(r['primary_dtc_id'] != '0' and r['primary_dtc_id'] != b['primary_dtc_id'] for r, b in paired)) if len(paired) == len(post) and post else None
    row['first_differential_diagnostic_ms'] = next((int(r['time_ms']) for r,b in paired if r['primary_dtc_id'] != '0' and r['primary_dtc_id'] != b['primary_dtc_id']), None)
    row['diagnostic_labels'] = ';'.join(sorted({r['primary_dtc_label'] for r, b in paired if r['primary_dtc_id'] != '0' and r['primary_dtc_id'] != b['primary_dtc_id']}))
    row['max_measured_reference_difference_c'] = max((abs(float(r['coolant_temp_meas_c'])-float(b['coolant_temp_meas_c'])) for r,b in paired), default=None)
    row['available_runtime_evidence'] = json.dumps({
        'packet_age_ms': row['max_sample_age_ms'], 'target_deviation_c': row['max_control_target_deviation_c'],
        'pump_tracking_error': row['max_pump_tracking_error'], 'fan_tracking_error': row['max_fan_tracking_error'],
        'last_execution_gap_ms': row['max_execution_gap_ms'], 'diagnostic_labels': row['diagnostic_labels'],
        'combined_detector_score': row['max_runtime_detection_score'],
    }, sort_keys=True)
    row['hardened_containment'], row['containment_class'] = containment_classification(row)
    confirmation = row.get('containment_time_ms')
    hardened_time = confirmation if row['hardened_containment'] == 1 else None
    row['hardened_containment_time_ms'] = hardened_time
    row['manifestation_based_experimental_ftti'] = ftti_result(origin[0], hardened_time, row['attributable_hazard'], end,
        int(last.get('fault_tolerant_time_interval_ms') or 5000), row['hardened_containment'] is not None)
    for start_name, start in (('injection', injection), ('internal_manifestation', row['first_internal_manifestation_ms']),
                             ('safety_relevant_manifestation', origin[0]), ('plant_manifestation', row['first_plant_manifestation_ms'])):
        row[start_name+'_to_detection_ms'] = interval(start, row.get('propagation_detector_ms'))
        row[start_name+'_to_containment_ms'] = interval(start, confirmation if start_name == 'injection' else hardened_time)
    alarm, hazard_time = row.get('propagation_detector_ms'), row.get('hazard_entry_ms')
    row['remaining_time_to_hazard_at_detection_ms'] = hazard_time-alarm if row['attributable_hazard'] == 1 and alarm is not None and hazard_time > alarm else None
    row['safety_severity'], row['silent_corruption_class'] = classify_consequence(row)
    row['timing_consequence'] = (TIMING_CLASSES[4] if row['attributable_hazard'] == 1 else TIMING_CLASSES[3] if row.get('plant_manifestation') == 1 else
        TIMING_CLASSES[2] if row['actuator_any_effect'] == 1 else TIMING_CLASSES[1] if row.get('control_effect') == 1 else TIMING_CLASSES[0]) if row.get('fault_layer') == 'timing' else 'NOT_APPLICABLE'
    row['timing_metadata_only'] = int(row.get('fault_layer') == 'timing' and row.get('control_effect') == 1 and row['actuator_any_effect'] == 0 and row.get('plant_manifestation') == 0 and row['max_control_target_deviation_c'] == 0)
    row['miss_reason'], row['miss_explanation'] = diagnose_miss(row)
    row['detected_before_plant_v3'] = int(alarm < row['propagation_plant_ms']) if alarm is not None and row.get('propagation_plant_ms') is not None else None
    row['silent_plant'] = int(row['detected'] == 0) if row.get('plant_manifestation') == 1 else None
    row['pre_hazard_detection'] = int(alarm is not None and alarm < hazard_time) if row['attributable_hazard'] == 1 else None
    row['silent_hazard'] = 1-row['pre_hazard_detection'] if row['pre_hazard_detection'] is not None else None
    row['recovered_without_actuator_or_plant'] = int(row['fault_recovered'] == 1 and row['actuator_any_effect'] == 0 and row.get('plant_manifestation') == 0) if injection is not None else None
    row['fault_parameters'] = row.get('configuration')
    row.update({'parameter_'+k: v for k,v in json.loads(row.get('configuration') or '{}').items()})
    transitions = []
    if hazard_available:
        previous = None
        first_entry = first_exit = None
        states = hazard_states(((int(r['time_ms']), r['hazard_warning_active'] == '1', r['critical_active'] == '1') for r in trace), int(last['max_critical_exposure_ms']))
        for raw, state in zip(trace, states):
            active = state['hazard_state'] == 'HAZARD_SUSTAINED'
            if active and first_entry is None:
                first_entry = state['time_ms']
            if not active and previous == 'HAZARD_SUSTAINED' and first_exit is None:
                first_exit = state['time_ms']
            if active != (raw['hazard_active'] == '1') or state['critical_exposure_ms'] != int(raw['critical_exposure_time_ms']) or state['consecutive_critical_ms'] != int(raw['consecutive_critical_exposure_ms']):
                raise ValueError(f"Hazard contract mismatch: {row['run_id']} at {raw['time_ms']}")
            if timestamp(raw,'hazard_entry_ms') != first_entry or timestamp(raw,'hazard_exit_ms') != first_exit or int(raw['hazard_entered']) != int(first_entry is not None):
                raise ValueError(f"Hazard entry/exit mismatch: {row['run_id']} at {raw['time_ms']}")
            if state['hazard_state'] != previous:
                transitions.append({'run_id': row['run_id'], **state})
            previous = state['hazard_state']
        row['hazard_state_end'] = previous
        row['hazard_active_at_end'] = int(previous == 'HAZARD_SUSTAINED')
    else:
        row['hazard_state_end'], row['hazard_active_at_end'] = None, None
    return row, transitions


def grouped_rows(rows):
    injected = [r for r in rows if r.get('injected') == 1]
    yield 'overall', 'all', injected
    for key in GROUPS:
        for value in sorted({str(r.get(key) or 'N/A') for r in injected}):
            yield key, value, [r for r in injected if str(r.get(key) or 'N/A') == value]


def rate(metric, values, dimension='overall', group='all'):
    eligible = [v for v in values if v is not None]
    numerator = sum(v == 1 for v in eligible)
    return {'dimension': dimension, 'group': group, 'metric': metric, 'numerator': numerator,
            'denominator': len(eligible), 'excluded_count': len(values)-len(eligible),
            'percent': 100*numerator/len(eligible) if eligible else None}


def metric_summary(rows):
    output = []
    for dimension, group, selected in grouped_rows(rows):
        metrics = {'overall_detection_coverage': [r.get('detected') for r in selected]}
        for label, key in (('internal_corruption','internal_corruption'), ('control_effect','control_effect'),
                           ('actuator_effect','actuator_any_effect'), ('plant_propagation','plant_manifestation'), ('hazard','attributable_hazard')):
            metrics['detection_coverage_given_'+label] = [r.get('detected') if r.get(key) == 1 else None for r in selected]
        for label, key in (('pre_hazard_detection_rate','pre_hazard_detection'), ('silent_plant_propagation_rate','silent_plant'),
                           ('silent_hazard_rate','silent_hazard'), ('hazard_rate','attributable_hazard'),
                           ('hardened_containment_rate','hardened_containment'), ('legacy_v2_containment','legacy_v2_containment'),
                           ('manifestation_based_experimental_ftti','manifestation_based_experimental_ftti'),
                           ('injection_based_experimental_ftti','injection_based_experimental_ftti')):
            metrics[label] = [r.get(key) for r in selected]
        metrics['silent_plant_incidence_all_injected'] = [int(r['plant_manifestation'] == 1 and r['detected'] == 0) if r.get('plant_manifestation') is not None and r.get('detected') is not None else None for r in selected]
        metrics['silent_hazard_incidence_all_injected'] = [0 if r.get('attributable_hazard') == 0 else r.get('silent_hazard') if r.get('attributable_hazard') == 1 else None for r in selected]
        for label, values in metrics.items():
            output.append(rate(label, values, dimension, group))
    return output


def sensitivity(rows, budgets=FTTI_CANDIDATES):
    output = []
    for dimension, group, selected in grouped_rows(rows):
        for budget in budgets:
            for clock in ('injection', 'manifestation'):
                values = []
                for r in selected:
                    legacy = clock == 'injection'
                    start = r.get('fault_injection_ms') if legacy else r.get('first_safety_relevant_manifestation_ms')
                    confirmation = r.get('containment_time_ms') if legacy else r.get('hardened_containment_time_ms')
                    applicable = r.get('legacy_v2_containment' if legacy else 'hardened_containment') is not None
                    values.append(ftti_result(start, confirmation, r.get('attributable_hazard'), r['observation_end_ms'], budget, applicable))
                output.append({**rate(clock+'_based_experimental_ftti', values, dimension, group), 'ftti_budget_ms': budget})
    return output


def distribution(rows, key, categories=()):
    output = []
    for dimension, group, selected in grouped_rows(rows):
        counts = Counter(r.get(key) or 'UNAVAILABLE' for r in selected)
        for label in sorted(set(counts) | set(categories)):
            output.append({'dimension': dimension, 'group': group, 'category': label, 'count': counts[label],
                           'denominator': len(selected), 'percent': 100*counts[label]/len(selected) if selected else None})
    return output


def input_manifest(source):
    paths = list(source.glob('*.csv')) + [source/'study_config.json', source/'commands.json', source/'cross_layer_safety_report.md']
    paths += list((source/'raw').glob('*.csv'))
    return {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_file()}


def analyze_campaign(source=DEFAULT_INPUT, output=DEFAULT_OUTPUT):
    source, output = Path(source).resolve(), Path(output).resolve()
    protected = [DEFAULT_INPUT.resolve(), (PROJECT_ROOT/'results/cross_layer_safety_v1').resolve(), source]
    if any(output == p or p in output.parents or output in p.parents for p in protected):
        raise ValueError('Analysis output must be separate from input and accepted v1/v2 evidence')
    campaign = read_rows(source/'campaign_runs.csv')
    config = json.loads((source/'study_config.json').read_text())
    manifest = input_manifest(source)
    baselines = {}
    def raw_path(r):
        # Resolve by basename inside the evidence package, allowing portable copies.
        path = source/'raw'/Path(r['raw_csv']).name
        if not path.is_file():
            raise ValueError(f'Missing raw evidence {path}')
        return path
    for r in campaign:
        if r['injected'] == '0':
            key = (r['operating_profile'], r['detector'], r['detector_action'])
            if key in baselines:
                raise ValueError('Ambiguous matched baseline')
            baselines[key] = {int(x['time_ms']): x for x in read_rows(raw_path(r))}
    rows, transitions = [], []
    for r in campaign:
        key = (r['operating_profile'], r['detector'], r['detector_action'])
        if key not in baselines:
            raise ValueError(f'Missing matched baseline {key}')
        trace = read_rows(raw_path(r))
        actual, recorded = summarize_rows(trace), typed(r)
        for field in (*STAGES, *METRICS, *V2_METRICS, 'injected', 'internal_corruption', 'control_effect', 'actuator_effect', 'actuator_realization_effect', 'plant_manifestation', 'detected'):
            if actual[field] != recorded[field]:
                raise ValueError(f"Campaign/raw disagreement: {r['run_id']} {field}")
        for raw in trace:
            for field, setting in (('hazard_warning_threshold_c','warning_threshold_c'), ('hazard_critical_threshold_c','critical_threshold_c'),
                                   ('max_critical_exposure_ms','max_critical_exposure_ms'), ('containment_hold_ms','recovery_hold_ms'),
                                   ('fault_tolerant_time_interval_ms','fault_tolerant_time_interval_ms')):
                if number(raw.get(field)) != config['hazard'][setting]:
                    raise ValueError(f"Non-global hazard configuration: {r['run_id']} {field}")
        row, events = analyze_run(r, trace, baselines[key])
        rows.append(row)
        transitions.extend(events)
    # Validate the independent timing interpretation against the retained metric.
    for r in rows:
        if r.get('injected') == 1:
            recomputed = ftti_result(r['fault_injection_ms'], r.get('containment_time_ms'), r['attributable_hazard'], r['observation_end_ms'],
                int(config['hazard']['fault_tolerant_time_interval_ms']), r['legacy_v2_containment'] is not None)
            if recomputed != r['injection_based_experimental_ftti']:
                raise ValueError(f"Legacy FTTI mismatch: {r['run_id']}")
    output.mkdir(parents=True, exist_ok=True)
    from .cross_layer_analysis_report import write_package
    write_package(output, rows, transitions)
    (output/'source_manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    if manifest != input_manifest(source):
        raise RuntimeError('Input evidence changed during reanalysis')
    return rows
