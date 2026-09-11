"""Reviewed interface availability, separate from measured mechanism coverage."""
from .cross_layer_analysis import rate

MODELS = ('bit_flip', 'stuck_bit', 'deadline_miss', 'task_delay', 'delayed_update',
          'dropped_update', 'replayed_sample', 'sensor_bias', 'fan_stuck_off')
CHANNELS = ('kalman_innovation', 'sensor_freshness_age', 'sensor_value_residual',
            'actuator_command_actual_mismatch', 'thermal_observer_mismatch', 'thermal_trend',
            'calibration_control_target', 'ecu_diagnostics', 'scheduler_last_execution',
            'scheduler_release_deadline_contract', 'communication_delivery_freshness', 'safe_state_status')


def observability_matrix():
    """DIRECT = matching local evidence, not guaranteed identification/coverage.

    Innovation/thermal mismatch are derived indirect channels. Independent true
    sensor residual and injector delivery provenance are not runtime observables.
    The communication column refers solely to received timestamps/freshness.
    """
    rows = []
    for model in MODELS:
        memory = model in ('bit_flip', 'stuck_bit')
        timing = model in ('deadline_miss', 'task_delay')
        communication = model in ('delayed_update', 'dropped_update', 'replayed_sample')
        row = {'fault_model': model, **{k: 'INDIRECT' for k in CHANNELS}}
        row.update(sensor_freshness_age='DIRECT' if communication else 'NOT APPLICABLE',
                   sensor_value_residual='NOT AVAILABLE',
                   actuator_command_actual_mismatch='DIRECT' if model == 'fan_stuck_off' else 'NOT APPLICABLE',
                   calibration_control_target='DIRECT' if memory else 'NOT APPLICABLE',
                   scheduler_last_execution='DIRECT' if timing else 'NOT APPLICABLE',
                   scheduler_release_deadline_contract='NOT AVAILABLE',
                   communication_delivery_freshness='DIRECT' if communication else 'NOT APPLICABLE')
        rows.append(row)
    return rows


def coverage_matrix(rows):
    results = []
    for model in MODELS:
        selected = [r for r in rows if r.get('injected') == 1 and r.get('fault_model') == model]
        for mechanism, field in (('hybrid_adaptive_kalman', 'detected'),
                                 ('ecu_diagnostics', 'differential_diagnostic_seen'),
                                 ('builtin_safety_response', 'safe_state_reached'),
                                 ('timing_monitor_not_implemented', None),
                                 ('other_detectors_not_exercised', None)):
            stat = rate(mechanism, [r.get(field) if field else None for r in selected])
            n, d = stat['numerator'], stat['denominator']
            results.append({'fault_model': model, 'mechanism': mechanism,
                            'classification': 'NOT APPLICABLE' if d == 0 else 'DETECTED' if n == d else 'MISSED' if n == 0 else 'PARTIALLY DETECTED',
                            'numerator': n, 'denominator': d, 'percent': stat['percent'],
                            'interpretation': 'Protective response, not detector coverage' if field == 'safe_state_reached' else
                            'Different nonzero primary DTC versus matched baseline; legacy truth/metadata exceptions apply' if field == 'differential_diagnostic_seen' else
                            'No campaign evaluation; not a measured miss' if field is None else 'Differential alarm versus fault-free reference'})
    return results


OBSERVABILITY_NOTES = """# Observability and measured coverage

`observability_matrix.csv` describes modeled runtime availability and matching
evidence, not measured signal activation or detector consumption. DIRECT means a
local signal can expose the consequence (age, actual execution timestamp, target,
or feedback mismatch); it does not identify injected origin or guarantee an alarm.
INDIRECT means a possible downstream/derived response. NOT AVAILABLE means the
required independent runtime evidence is absent. NOT APPLICABLE means the channel
does not directly encode this fault's local event. Recovery, masking and matching
stuck polarity can prevent any channel response.

Sources: `include/runtime_observation.h`, `src/runtime_observation.c`,
`src/detection_algorithm.c`, `src/actuators.c`, `src/diagnostics.c`, `src/safety_monitor.c` and
`docs/detector_observability_boundary.md` (accepted baseline 97f18ce).

| Evidence | Available in current system | Current consumer / limitation |
| --- | --- | --- |
| Delivered measurement and acquisition age | Runtime snapshot | Hybrid freshness/innovation; received timestamp survives replay |
| Command and modeled feedback | Runtime snapshot | Hybrid actuator tracking and fan-health evidence |
| Target deviation | ECU-owned state / nominal reference | Hybrid calibration support, fixed 4 C evidence and 12 C strong-deviation criteria |
| Last actual execution timestamp | Runtime snapshot | Neither current Hybrid nor built-in safety consumes it |
| Nominal job release / relative deadline / discarded-release contract | Injector-side evaluation telemetry only | Missing from the allowlisted runtime snapshot; do not feed injection flags to a monitor |
| Independent sensor-value residual against true coolant | NOT AVAILABLE in runtime snapshot | Legacy detector and DTC use simulator truth; retained scientific limitation |
| Kalman innovation / thermal observer mismatch / trend | Derived inside existing detector | Components/support/persistence not individually logged in accepted CSV; combined score and dominant label are logged |
| DTC and safe-state status | Runtime snapshot outputs | Mechanism outputs, not independent fault evidence; DTC provenance uses legacy metadata |
| Generated-but-undelivered sample, replay source, drop flags | Experiment truth | Excluded; received packet age is the legitimate runtime alternative |

The second matrix is measured; `detector_coverage_evidence.csv` contains the
corresponding numerator, denominator and interpretation for every cell: Hybrid alarm, differential nonzero primary DTC,
and differential applied safe state against the profile-matched baseline. Safety
response is explicitly an outcome, not a detector. Other seven detectors were not
exercised by this campaign and are NOT APPLICABLE, never fabricated misses. A DTC
change can be secondary to physical consequences; it is not root-cause diagnosis.

The healthy actuator model follows bounded commands exactly. A corrupted command
can propagate to the plant while command-minus-actual tracking error remains zero.
Thus this particular mismatch channel is NOT APPLICABLE for the non-actuator
single-fault cases, rather than an invented indirect warning signal. Fan health
self-test is populated by the accepted fault model even when command is zero;
the 6/6 fan detections therefore rely on an optimistic modeled feedback assumption.

There is no isolated coverage estimate for innovation, trend, or freshness. The
first-alarm labels are dominant branch labels, not ablations or causal attribution.
Strong channel rankings require a separate frozen-detector ablation study. The
present evidence supports a timing interface gap, while communication freshness
already has a consumed direct channel. Sensor bias lacks an independent physical
truth residual on a production-like boundary. Actual field deployment observability
would also require trustworthy feedback, calibrated clocks and received timestamps.
"""
