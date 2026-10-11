# 02 — Frozen CLOVER-ECU diagnosis

Evidence labels used throughout: **VERIFIED FROM SOURCE** (literal implemented behavior); **VERIFIED FROM EXPERIMENT ARTIFACT** (recorded outcomes/protocol); **DERIVED MATHEMATICALLY FROM VERIFIED SOURCE** (algebra or deterministic accounting, not a new experiment); **NOT RECOVERABLE / REQUIRES CONFIRMATION** (missing/limited evidence). Source paths are repository-relative unless explicitly absolute. Line numbers refer to the hashes in 07, not an assumed future HEAD.

## Which executable is authoritative

**VERIFIED FROM SOURCE / VERIFIED FROM EXPERIMENT ARTIFACT.** CLOVER-ECU is the publication name of refined A2, not a new identifier in source. `run_integrity_final_unseen.py` calls `run_benign_alarm.execute_setup`, whose build wraps `run_digital_integrity.build`, inherited adapter generators and existing C objects. The authoritative generated `extended.c` supplies `clo_triplex_core_step`; generated `adapter.c` supplies producer hooks, independent C, `dc_probe`, DI hold and `ba_capture`. `freeze.json` hashes generated C, objects, executable and configuration. `src/v7_3/clo_dsf_revised.c` by itself is not final A2.

The selected G2 alarm is calculated in C inside `ba_capture`; `collect()` reads `audit.csv` column 25 and replaces the reported pre-gate M2 alarm through `score()`. Column 21's origin is shifted right one bit and suppressed when G2 rejects the alarm. This composition is deterministic runtime-data processing; do not claim the standalone simulator's default alarm field or control policy is already rewired to the G2 output. Evaluation metadata appears in the harness but is not an input to core/gate inference.

## Providers and inputs

**VERIFIED FROM SOURCE.** `runtime_observation_t` is the allowlisted packet: measured coolant and sample timestamp/age/freshness; consumed control target; command/actual pump and fan; execution timestamp; load/ambient/speed; scheduler release/start/completion/deadline/age/status ledger; target register/shadow/validity; active-probe time/valid/failed; primary source/current and previous values/timestamps/validity; B value/time/enabled/valid/failed. Independent C is a separately published current/previous readout. DI supplies channel availability, per-channel mismatch masks and held FAIL. No true coolant temperature, injected model/class, onset or counterfactual outcome is passed to inference. Original diagnostic/alarm fields in the struct are not automatically permissible ML inputs.

For u(x)=min(1,max(0,x)), six channels are ordered **timing, communication, memory, sensor, actuator, measured-temperature hazard**. Exact transformations/availability/reset code is transcribed below:
- Timing: available if period>0; maximum of u((execution_age−period−relative_deadline)/period) and explicit deadline/missed-release/late-completion status.
- Communication: timestamp≤now and expected period>0; u((age−300)/300), or 1 for invalid freshness/backward delivery timestamp; raise to 1 for current acquisition/current control consuming an older delivered sample.
- Memory: trusted shadow availability; any register/shadow or same-tick consumed-target inconsistency →1. A valid recent failed active check →1. Recent means age strictly below `MEMORY_DIAGNOSTIC_MAX_INTERVAL_MS`, not an invented window.
- Sensor: measured implausibility/slew, local source plausibility/slew, opposing-edge excess, bounded response forecast, A/B SLOW/FAST, independent C comparisons and DI held failure, merged by **maximum**, not treated as independent repeated DS sources.
- Actuator: finite commands/actuals on actuator cadence; actual must lie between adjacent representable floats around clamp(command). A violation →1. Idle degradation with command zero need not violate this contract.
- Hazard: measured coolant u((y−108)/7); its origin support is Θ, not a forced actuator class.

Source-local slew is u((|Δsource|−2.5Δt)/2), plus out-of-range status. Contiguous opposing-direction excesses can be summed and clipped. Five contiguous within-slew acquisitions qualify startup origin evidence; this is not an alarm lock or injected origin rule.

## Sensor history contracts

**VERIFIED FROM SOURCE / DERIVED MATHEMATICALLY FROM VERIFIED SOURCE.** Response forecast uses five acquisitions spanning .4 s; endpoint slope predicts at most .300001 s with envelope .20+.50h+1.50h². Two same-sign exceedances produce u((|residual|−envelope)/2). Invalid/gapped acquisitions or changed load/speed/ambient/target/fan invalidate the history/anchor.

SLOW uses the signed A−B mean over 320 contiguous acquisitions; only the full window contributes u((|mean|−.90)/2). Invalid/gapped samples reset it. B explicit same-tick conversion failure can independently contribute 1.

FAST: Δ=A−B; an edge exceeds .40+1.2(.1)=.52 °C. Anchor the preceding value for ≤300 ms. Two same-direction exceedances of .40+1.2h certify evidence 1. Bounded same-sign integration requires each |residual|>.40 and cumulative absolute residual above cumulative original envelopes after at least two samples. Exact source also deactivates the anchor on failure of the original envelope test; do not rewrite this into a free-running CUSUM. Three excessive edges in the ten-acquisition history also yield 1. Gaps, expiration and sign/recovery checks follow the literal order below.

Independent C must have current and previous valid, nonfailed samples, contiguous 100-ms timestamps, current sample≤now and age≤100. It is causally extrapolated to A/B time: C'=C+(C−Cprev)(now−tC)/(tC−tprev). A/C and B/C feed the **existing pair evidence** implementation; after five valid alignment steps, max(AC,BC) contributes. Explicit failed/stale C after 500 ms can contribute 1 (stale beyond 200 ms). Pairwise agreement cutoff .90 identifies cuts A|BC, B|AC, C|AB or all-disagree; these are disagreement patterns, **not proof of the faulty member**. All-disagree marks ambiguity.

## DS operations and logical origin encoding

**DERIVED MATHEMATICALLY FROM VERIFIED SOURCE.** Standard simple support: m(S)=s, m(Θ)=1−s; if S=Θ keep a vacuous mass. Standard reliability discount: m'(A)=r m(A) for A≠Θ and m'(Θ)=r m(Θ)+1−r. Standard conjunctive products sum over B∩C=A; K is the empty-set sum. Dempster normalization divides the remaining nonempty sum by its total. For 1−K≤10⁻¹² return vacuous mass and surface fallback; no hidden conflict-to-fault bonus.

Detection uses ABNORMAL=62, NORMAL=1 and Θ=63 (the storage encoding from `clo_dsf_candidate2.h`) with r_detection=1. Origin uses five logical classes, encoded as disjoint storage blocks {33,2,4,8,16}; Memory's two storage bits are ONE logical atom. Origin supports by channel are {2,4,33,12,16,63}. Local qualified sensor evidence replaces ambiguous communication/sensor support with sensor block8. Do not use six-atom equal-bit BetP to double-weight Memory.

Per channel, fuse detection and origin independently. Discount previous detection/origin masses by λ=.8 and combine once each: six channel combinations + one temporal combination per head. No propagation scoring. Bel(A)=Σ(B⊆A)m(B); Pl(A)=Σ(B∩A≠∅)m(B). Logical origin BetP(i)=Σ(S∋i)m(encoded(S))/|S| over nonempty subsets of FIVE logical classes.

Frozen config: detection confirmed .5, suspect .35, persistence1; origin top score≥.55, top−second≥.15, ignorance≤.5. Ties use the first strict-maximum index (Memory→Timing→Communication→Sensor→Actuator), but a tied top pair fails the positive margin. UNKNOWN is returned when localization fails; it is not a sixth predicted fault origin. Conflict and ignorance are diagnostics, not calibrated probabilities.

## Complete control-flow pseudocode

**VERIFIED FROM SOURCE**, algebraically restated; exact numerical/helper branches are reproduced in the source appendix.

```text
At a scheduled acquisition boundary:
  publish A record after real primary acquisition (including any pre-boundary error)
  acquire B and due independent C; their wrappers seal producer-owned records
  apply configured test mutations in experiment adapter only
  apply legitimate offsets/noise through trusted transformation API
  verify consumer values/envelopes against each valid protected witness
  set availability and mismatch masks; on mismatch set until[channel]=now+300ms
Before control tasks:
  authorized target update commits register AND shadow
  injection affects memory path; phase-scheduled diagnostic saves value,
      writes/reads 0 and 0xffff, restores/reads saved value (7 operations)
At diagnostic frame:
  capture runtime allowlist; update independent C pair comparisons
  z = runtime observation with dc_memory checked/valid/failed fields
  hold = any(until[channel]!=0 AND now<until[channel])
  local anomaly/origin DI contribution = 1 if hold else 0
  if now <= previous processed time: return without updating core state
  update all six providers and their required local histories
  local = max(local slew/opposing edges, response, SLOW, FAST, Triplex, hold)
  origin_local uses startup-qualified slew plus independently qualified providers
  merge local into sensor strength and availability
  track unresolved pump/fan response violations; certify recovery only with
      positive successful response and valid non-subambient source evidence
  derive direct origins from non-sensor/non-hazard available strengths >= .5
  establish first direct onset; flag simultaneous multiple origins or competing
      sensor/direct onset as ambiguous (unless sensor already established first)
  downstream_sensor = direct onset exists, sensor not first, now > direct onset
  reset per-frame conflicts/fallbacks; start two vacuous masses
  for each channel:
      build/discount/fuse ABNORMAL support into detection
      build/fuse channel origin support; suppress downstream sensor origin only
  discount old head masses by .8; combine; store new head masses
  score = Bel(ABNORMAL); increment/reset detection persistence
  qualify anomaly episode from independent runtime evidence
  suppress unqualified startup-only anomaly; update NORMAL/SUSPECT/CONFIRMED
  compute five logical BetP scores, strict top/runner-up, ignorance
  localize only if alarm + .55/.15/.5 gates and no onset/Triplex ambiguity
  sensor-established-first may be set only by localized sensor runtime evidence
  on NORMAL + all evidence quiet + certified actuator recovery:
      clear episode qualification, unresolved actuator mask and origin precedence
  apply G2 below; emit UNKNOWN when final alarm is suppressed or origin uncertain
```

## G2 and memory/integrity details

**VERIFIED FROM SOURCE.** G2's PASS predicate is all three witnesses available (`available==7`), bad mask zero, no held FAIL. Other support is any non-sensor channel with available positive evidence (including hazard), OR established direct origins. If integrity is FAIL/UNAVAILABLE or other support exists, bypass suppression, reset G2 count, retain base alarm. Otherwise require three consecutive 100-ms timestamps with finite qualified sensor strength≥.5 and >0. Gaps reset count; duplicate/backward timestamps use base_alarm AND previous gate output. G2 never promotes a base no-alarm into an alarm.

**Important M2 implementation detail:** the final `dc_probe` is not merely a fixed 250-ms timer. It creates a 100-slot (10-s) phase mask: mark 0,11,…,99; insert midpoints of the largest circular gap until 40 slots are set, first-gap tie order determined by ascending scan. Probe on marked 100-ms ticks, avoiding duplicate checks. This has mean spacing250 ms. `mr_memory_step`'s alternating200/300-ms helper also exists in the adapter but its output is not the final z.memory_check source. No extra actuator excitation is introduced.

DI uses channel/value bits/sequence/timestamp/tag, availability separate from the unsigned mismatch return. An invalid witness returns status0 but means UNAVAILABLE, not PASS. Tag corruption→bit4; protected/delivered/envelope value, tag or identity mismatch→bit1; sequence/timestamp mismatch→bit2. All bits can coexist. Legal transformations update protected value/tag and envelope without overwriting the delivered measurement. CRC is not authentication and cannot detect an internally consistent joint replacement of data and witness.

## Authoritative source appendix


### Exact source: runtime_observation.h

**VERIFIED FROM SOURCE.** `include/runtime_observation.h` — `file`, lines 1–38

```text
   1: #ifndef RUNTIME_OBSERVATION_H
   2: #define RUNTIME_OBSERVATION_H
   3: 
   4: #include <stdbool.h>
   5: #include "runtime_timing_observation.h"
   6: 
   7: /* Allowlist for future runtime monitors: deliberately no plant truth or labels. */
   8: typedef struct {
   9:     unsigned int time_ms;
  10:     float coolant_measured_c;
  11:     unsigned int sample_timestamp_ms;
  12:     unsigned int sample_age_ms;
  13:     float control_target_c;
  14:     float pump_command, fan_command, pump_actual, fan_actual;
  15:     int control_execution_ms;
  16:     int diagnostic_id;
  17:     int safety_state;
  18:     bool detector_alarm;
  19:     float engine_load, ambient_c, vehicle_speed_kph;
  20:     bool sample_freshness_ok;
  21:     unsigned int sample_expected_period_ms;
  22:     runtime_timing_observation_t timing;
  23:     /* Trusted runtime integrity/acquisition boundary, no injection labels. */
  24:     unsigned int target_register_c, target_shadow_c;
  25:     bool target_shadow_valid;
  26:     unsigned int memory_check_ms;
  27:     bool memory_check_valid, memory_check_failed;
  28:     float source_c, source_previous_c;
  29:     unsigned int source_ms, source_previous_ms;
  30:     bool source_valid, source_previous_valid;
  31:     float reference_c;
  32:     unsigned int reference_ms;
  33:     bool reference_enabled, reference_valid, reference_failed;
  34: } runtime_observation_t;
  35: 
  36: struct ecu_state;
  37: void runtime_observation_capture(const struct ecu_state *state, runtime_observation_t *observation);
  38: #endif
```


### Exact source: runtime_timing_observation.h

**VERIFIED FROM SOURCE.** `include/runtime_timing_observation.h` — `file`, lines 1–28

```text
   1: #ifndef RUNTIME_TIMING_OBSERVATION_H
   2: #define RUNTIME_TIMING_OBSERVATION_H
   3: #include <stdbool.h>
   4: 
   5: /* Scheduler-owned event ledger. No injection or evaluation metadata. */
   6: typedef struct {
   7:     unsigned int task_id, time_ms, period_ms, relative_deadline_ms;
   8:     unsigned int release_sequence, execution_sequence;
   9:     int current_release_ms, job_release_ms, actual_start_ms, actual_completion_ms;
  10:     int last_successful_execution_ms;
  11:     unsigned int execution_age_ms;
  12:     bool job_outstanding, missed_expected_execution, deadline_exceeded;
  13:     unsigned int cancelled_release_count;
  14: } runtime_timing_observation_t;
  15: 
  16: typedef struct {
  17:     runtime_timing_observation_t observation;
  18:     int cancelled_deadline_ms;
  19: } runtime_timing_recorder_t;
  20: 
  21: void runtime_timing_init(runtime_timing_recorder_t *r, unsigned int period_ms);
  22: void runtime_timing_release(runtime_timing_recorder_t *r, unsigned int now);
  23: void runtime_timing_admit(runtime_timing_recorder_t *r);
  24: void runtime_timing_cancel_release(runtime_timing_recorder_t *r, bool cancel_outstanding);
  25: void runtime_timing_start(runtime_timing_recorder_t *r, unsigned int now);
  26: void runtime_timing_complete(runtime_timing_recorder_t *r, unsigned int now);
  27: void runtime_timing_observe(runtime_timing_recorder_t *r, unsigned int now);
  28: #endif
```


### Exact source: memory_diagnostic.h

**VERIFIED FROM SOURCE.** `include/memory_diagnostic.h` — `file`, lines 1–18

```text
   1: #ifndef MEMORY_DIAGNOSTIC_H
   2: #define MEMORY_DIAGNOSTIC_H
   3: #include <stdbool.h>
   4: #include <stdint.h>
   5: #define MEMORY_DIAGNOSTIC_PERIOD_MS 1000U
   6: #define MEMORY_DIAGNOSTIC_PHASE_STEP_MS 100U
   7: #define MEMORY_DIAGNOSTIC_MAX_INTERVAL_MS 1100U
   8: typedef struct {
   9:     unsigned int checked_ms, checks, operations;
  10:     bool valid, failed;
  11: } memory_diagnostic_t;
  12: typedef uint16_t (*memory_read_fn)(void *);
  13: typedef void (*memory_write_fn)(void *, uint16_t);
  14: /* Caller guarantees exclusive access for the entire synchronous transaction.
  15:  * Neither callback exposes a failure label or a faulty bit identity. */
  16: void memory_diagnostic_step(memory_diagnostic_t *, unsigned int,
  17:                             memory_read_fn, memory_write_fn, void *);
  18: #endif
```


### Exact source: clo_dsf_candidate2.h

**VERIFIED FROM SOURCE.** `include/clo_dsf_candidate2.h` — `file`, lines 1–47

```text
   1: #ifndef CLO_DSF_CANDIDATE2_H
   2: #define CLO_DSF_CANDIDATE2_H
   3: #include "clo_dsf.h"
   4: /* Partition embeddings preserve union/intersection and Theta=63 in the frozen
   5:  * DS core. Origin BetP counts FIVE logical blocks, never six storage bits. */
   6: #define C2_D_NORMAL 1U
   7: #define C2_D_ABNORMAL 62U
   8: #define C2_ORIGIN_RELIABILITY 1U
   9: #define C2_PROPAGATION 2U
  10: #define C2_TEMPORAL 4U
  11: #define C2_DETECTION_RELIABILITY 8U
  12: #define C2_FULL 15U
  13: extern const unsigned int c2_origin_blocks[5];
  14: extern const unsigned int c2_origin_support[CLO_CHANNELS];
  15: typedef struct {
  16:     clo_config_t common; /* r_direct/r_indirect apply ONLY to origin evidence. */
  17:     double r_detection;
  18: } c2_config_t;
  19: typedef struct {
  20:     clo_state_t state;
  21:     double anomaly_belief, anomaly_plausibility, anomaly_decision_score, anomaly_ignorance;
  22:     double detection_conflict, localization_conflict;
  23:     double detection_conflict_steps[7], localization_conflict_steps[7];
  24:     double origin_score, origin_belief, origin_plausibility, origin_margin, origin_ignorance;
  25:     double origin_scores[5];
  26:     unsigned int estimated_origin, leading_origin;
  27:     bool alarm, localization_valid, propagation_support, detection_fallback, localization_fallback;
  28:     int alarm_timestamp_ms, localization_timestamp_ms;
  29: } c2_output_t;
  30: typedef struct {
  31:     ds_mass_t detection_mass, origin_mass;
  32:     clo_evidence_t evidence;
  33:     double detection_reliability[CLO_CHANNELS], origin_reliability[CLO_CHANNELS];
  34:     c2_output_t output;
  35:     unsigned int confirmation_count, previous_time_ms;
  36:     bool has_previous_time;
  37: } c2_state_t;
  38: void c2_config_default(c2_config_t *c);
  39: bool c2_config_valid(const c2_config_t *c);
  40: void c2_init(c2_state_t *s);
  41: void c2_extract(clo_evidence_t *e, const runtime_observation_t *o);
  42: void c2_propagation(clo_evidence_t *e, const clo_config_t *c, unsigned int now);
  43: unsigned int c2_encode_origin_subset(unsigned int logical_mask);
  44: void c2_origin_betp(const ds_mass_t *m, double scores[5]);
  45: void c2_step(c2_state_t *s, const c2_config_t *c, unsigned int extensions,
  46:              const runtime_observation_t *o);
  47: #endif
```


### Exact source: c2_extract

**VERIFIED FROM SOURCE.** `src/v7_1/candidate2_evidence.c` — `c2_extract`, lines 10–48

```text
  10: void c2_extract(clo_evidence_t *e, const runtime_observation_t *o)
  11: {
  12:     memset(e->strength,0,sizeof(e->strength));
  13:     memset(e->available,0,sizeof(e->available));
  14:     e->available[0]=o->timing.period_ms>0;
  15:     if (e->available[0]) {
  16:         double limit=(double)o->timing.period_ms+o->timing.relative_deadline_ms;
  17:         double age=unit(((double)o->timing.execution_age_ms-limit)/o->timing.period_ms);
  18:         bool late=o->timing.actual_completion_ms>=0 && o->timing.job_release_ms>=0 &&
  19:             (double)o->timing.actual_completion_ms-o->timing.job_release_ms>o->timing.relative_deadline_ms;
  20:         e->strength[0]=maximum(age,(o->timing.deadline_exceeded || o->timing.missed_expected_execution || late)?1:0);
  21:     }
  22:     e->available[1]=o->sample_expected_period_ms>0 && o->sample_timestamp_ms<=o->time_ms;
  23:     if (e->available[1]) {
  24:         e->strength[1]=unit(((double)o->sample_age_ms-ECU_COOLANT_SENSOR_FRESHNESS_STALE_MS)/ECU_COOLANT_SENSOR_FRESHNESS_STALE_MS);
  25:         if (!o->sample_freshness_ok || (e->initialized && o->sample_timestamp_ms<e->previous_sample_timestamp_ms)) e->strength[1]=1;
  26:     }
  27:     e->available[2]=isfinite(o->control_target_c);
  28:     if (e->available[2]) e->strength[2]=unit(fabs(o->control_target_c-ECU_TARGET_COOLANT_TEMP_C)/4.0);
  29:     e->available[3]=isfinite(o->coolant_measured_c);
  30:     if (e->available[3]) {
  31:         if (o->coolant_measured_c<ECU_SENSOR_IMPLAUSIBLE_LOW_C || o->coolant_measured_c>ECU_SENSOR_IMPLAUSIBLE_HIGH_C) e->strength[3]=1;
  32:         /* A measured slew residual, not simulator true-temperature residual.
  33:          * 2.5 C/s is a deliberately broad physical envelope, not plant truth. */
  34:         if (e->initialized && o->time_ms>e->previous_timestamp_ms) {
  35:             double dt=(o->time_ms-e->previous_timestamp_ms)/1000.0;
  36:             double residual=fabs(o->coolant_measured_c-e->previous_temperature)-2.5*dt;
  37:             e->strength[3]=maximum(e->strength[3],unit(residual/2.0));
  38:         }
  39:     }
  40:     e->available[4]=isfinite(o->fan_command)&&isfinite(o->fan_actual)&&isfinite(o->pump_command)&&isfinite(o->pump_actual);
  41:     if (e->available[4]) e->strength[4]=unit(maximum(fabs(o->fan_command-o->fan_actual)/.25,fabs(o->pump_command-o->pump_actual)/.20));
  42:     e->available[5]=isfinite(o->coolant_measured_c);
  43:     if (e->available[5]) e->strength[5]=unit((o->coolant_measured_c-ECU_WARN_COOLANT_TEMP_C)/(ECU_CRITICAL_COOLANT_TEMP_C-ECU_WARN_COOLANT_TEMP_C));
  44:     if (e->available[3]) { e->previous_temperature=o->coolant_measured_c; e->initialized=true; }
  45:     else e->initialized=false;
  46:     e->previous_timestamp_ms=o->time_ms;
  47:     e->previous_sample_timestamp_ms=o->sample_timestamp_ms;
  48: }
```


### Exact source: extended.c

**VERIFIED FROM SOURCE.** `/tmp/clo-integrity-final-unseen/work/extended.c` — `file`, lines 1–419

```text
   1: extern double triplex_extra_strength;
   2: #include <stdbool.h>
   3: extern bool triplex_extra_ambiguous;
   4: extern double dc_mass,dc_origin,dc_discount;
   5: #include "clo_dsf_revised.h"
   6: #include "config.h"
   7: #include "memory_diagnostic.h"
   8: #include <math.h>
   9: extern double ba_provider[7];
  10: void ba_capture(const clo_revised_t *,const runtime_observation_t *,double);
  11: void benchmark_capture(unsigned,const clo_revised_t *,const runtime_observation_t *,double,double);
  12: 
  13: 
  14: /* Contract: actuators_step realizes clamp(command) synchronously before this
  15:  * scheduler's detector call. Adjacent representable floats are conservatively
  16:  * accepted, avoiding a fitted physical tolerance. This is a virtual-ECU
  17:  * contract, not an assumed physical actuator model or a calibrated probability.
  18:  * Non-finite or off-cadence observations contribute no actuator evidence. */
  19: static bool outside_response_contract(float command, float actual)
  20: {
  21:     const float expected = fminf(1.0f, fmaxf(0.0f, command));
  22:     return actual < nextafterf(expected, -INFINITY) ||
  23:            actual > nextafterf(expected, INFINITY);
  24: }
  25: void clo_triplex_core_extract(clo_evidence_t *e, const runtime_observation_t *o)
  26: {
  27:     c2_extract(e, o);
  28:     /* This synchronous ECU acquires before executing control. When both events
  29:      * occur now, consuming an older delivered sample violates that ordering,
  30:      * even if a generic freshness timeout has not expired. No age threshold is
  31:      * reduced: this compares observed production/consumption provenance. */
  32:     if(o->source_valid && o->source_ms==o->time_ms &&
  33:        o->control_execution_ms==(int)o->time_ms && e->available[1] &&
  34:        o->sample_timestamp_ms<o->source_ms)e->strength[1]=1.0;
  35:     e->available[2] = o->target_shadow_valid;
  36:     e->strength[2] = e->available[2] &&
  37:         (o->target_register_c != o->target_shadow_c ||
  38:          (o->control_execution_ms == (int)o->time_ms &&
  39:          (!isfinite(o->control_target_c) || o->control_target_c != (float)o->target_shadow_c))) ? 1.0 : 0.0;
  40:     if (o->memory_check_valid && o->memory_check_ms <= o->time_ms &&
  41:         o->time_ms - o->memory_check_ms < MEMORY_DIAGNOSTIC_MAX_INTERVAL_MS) {
  42:         e->available[2] = true;
  43:         if (o->memory_check_failed) e->strength[2] = 1.0;
  44:     }
  45:     e->available[4] = e->available[4] && o->time_ms % ECU_ACTUATOR_PERIOD_MS == 0;
  46:     e->strength[4] = e->available[4] &&
  47:         (outside_response_contract(o->pump_command, o->pump_actual) ||
  48:          outside_response_contract(o->fan_command, o->fan_actual)) ? 1.0 : 0.0;
  49: }
  50: 
  51: /* Independent acquisition plausibility uses the existing physical envelope.
  52:  * Absence of local evidence does not prove a communication origin. */
  53: static double local_sensor_strength(const runtime_observation_t *o)
  54: {
  55:     if (!o->source_valid || o->source_ms != o->time_ms || !isfinite(o->source_c)) return 0;
  56:     double strength = o->source_c < ECU_SENSOR_IMPLAUSIBLE_LOW_C ||
  57:                       o->source_c > ECU_SENSOR_IMPLAUSIBLE_HIGH_C ? 1.0 : 0.0;
  58:     if (o->source_previous_valid && isfinite(o->source_previous_c) &&
  59:         o->source_previous_ms < o->source_ms) {
  60:         double dt = (o->source_ms - o->source_previous_ms) / 1000.0;
  61:         double residual = (fabs(o->source_c - o->source_previous_c) - 2.5 * dt) / 2.0;
  62:         strength = fmax(strength, fmin(1.0, fmax(0.0, residual)));
  63:     }
  64:     return strength;
  65: }
  66: 
  67: /* Short-horizon local response envelope, not an absolute thermal model.
  68:  * Five trusted acquisitions span 400 ms. Endpoint slope predicts at most 300 ms.
  69:  * With +/-0.10 C sample uncertainty, displacement uncertainty is 0.20 C and
  70:  * slope uncertainty 0.50 C/s. The global curvature allowance is 3 C/s^2.
  71:  * Two same-sign out-of-envelope acquisitions are required. Forecasts expire,
  72:  * and operating-input transitions invalidate them. Evidence shares the existing
  73:  * sensor mass (max, not an additional independent DS source) and 2 C scale.
  74:  * Slowly varying common-mode bias can be absorbed by the slope: no absolute
  75:  * calibration observability is claimed. */
  76: static double sensor_response(clo_revised_t *s,const runtime_observation_t *o)
  77: {
  78:     s->response_strength=0;s->response_residual=0;
  79:     bool valid=o->source_valid && o->source_ms==o->time_ms &&
  80:         isfinite(o->source_c) && isfinite(o->engine_load) &&
  81:         isfinite(o->vehicle_speed_kph) && isfinite(o->ambient_c) &&
  82:         isfinite(o->control_target_c) && isfinite(o->fan_actual);
  83:     bool contiguous=s->response_count && o->source_previous_valid &&
  84:         o->source_ms==s->response_last_ms+ECU_SENSOR_PERIOD_MS &&
  85:         o->source_previous_ms==s->response_last_ms &&
  86:         o->source_previous_c==s->response_history[s->response_count-1];
  87:     bool same_inputs=s->response_count && o->engine_load==s->response_load &&
  88:         o->vehicle_speed_kph==s->response_speed && o->ambient_c==s->response_ambient &&
  89:         o->control_target_c==s->response_target && o->fan_actual==s->response_fan;
  90:     if(!valid || !contiguous || !same_inputs) {
  91:         s->response_count=0;s->response_active=false;s->response_streak=0;
  92:     }
  93:     if(!valid)return 0;
  94:     if(s->response_count==5) {
  95:         if(!s->response_active) {
  96:             s->response_anchor_ms=s->response_last_ms;
  97:             s->response_anchor=s->response_history[4];
  98:             s->response_slope=(s->response_history[4]-s->response_history[0])/
  99:                 (4.0*ECU_SENSOR_PERIOD_MS/1000.0);
 100:             s->response_streak=0;s->response_sign=0;s->response_active=true;
 101:         }
 102:         double h=(o->source_ms-s->response_anchor_ms)/1000.0;
 103:         double residual=o->source_c-s->response_anchor-s->response_slope*h;
 104:         double bound=.20+.50*h+1.50*h*h;
 105:         s->response_residual=residual;
 106:         int sign=residual>0?1:-1;
 107:         if(h<=.300001 && fabs(residual)>bound) {
 108:             s->response_streak=sign==s->response_sign?s->response_streak+1:1;
 109:             s->response_sign=sign;
 110:             if(s->response_streak>=2)s->response_strength=fmin(1.0,(fabs(residual)-bound)/2.0);
 111:         } else {s->response_active=false;s->response_streak=0;}
 112:         if(h>=.299999)s->response_active=false;
 113:     }
 114:     if(s->response_count==5) {
 115:         for(unsigned int i=0;i<4;i++)s->response_history[i]=s->response_history[i+1];
 116:         s->response_count=4;
 117:     }
 118:     s->response_history[s->response_count++]=o->source_c;
 119:     s->response_last_ms=o->source_ms;s->response_load=o->engine_load;
 120:     s->response_speed=o->vehicle_speed_kph;s->response_ambient=o->ambient_c;
 121:     s->response_target=o->control_target_c;s->response_fan=o->fan_actual;
 122:     return s->response_strength;
 123: }
 124: 
 125: /* A paired, time-aligned acquisition check, not an absolute plant observer.
 126:  * |mean(primary-reference)| tolerates 0.90 C: the prior legal primary
 127:  * triangle (A<=2.3 C,P<=24.2 s) has at most A*P/(4*32)=0.435 C
 128:  * signed window mean; add offsets <=0.20 C, bounded noise <=0.20 C,
 129:  * quantization <=0.005 C. 0.90 C rounds this envelope conservatively up.
 130:  * Full 320 acquisitions required. Opposite signs cancel; gaps reset.
 131:  * Existing 2 C evidence scale and all DS thresholds remain unchanged.
 132:  * Disagreement identifies the sensing subsystem, NEVER which sensor failed.
 133:  */
 134: static double redundant_sensor(clo_revised_t *s,const runtime_observation_t *o)
 135: {
 136:     s->reference_strength=0;
 137:     bool valid=o->reference_enabled && o->reference_valid && !o->reference_failed &&
 138:         o->source_valid && o->source_ms==o->time_ms &&
 139:         o->reference_ms==o->source_ms && isfinite(o->source_c) && isfinite(o->reference_c);
 140:     if(!valid || (s->reference_count && o->time_ms!=s->reference_last_ms+ECU_SENSOR_PERIOD_MS)) {
 141:         s->reference_count=0;s->reference_index=0;s->reference_sum=0;s->reference_mean=0;
 142:     }
 143:     /* Explicit local conversion-failure status; absent/unconfigured hardware
 144:      * never raises an alarm. A stale timestamp alone does not name an origin. */
 145:     if(o->reference_enabled && o->reference_failed && o->reference_ms==o->time_ms)
 146:         return s->reference_strength=1;
 147:     if(!valid)return 0;
 148:     double delta=(double)o->source_c-o->reference_c;
 149:     if(s->reference_count==320)s->reference_sum-=s->reference_window[s->reference_index];
 150:     else s->reference_count++;
 151:     s->reference_window[s->reference_index]=delta;s->reference_sum+=delta;
 152:     s->reference_index=(s->reference_index+1)%320;s->reference_last_ms=o->time_ms;
 153:     s->reference_mean=s->reference_sum/s->reference_count;
 154:     if(s->reference_count==320)
 155:         s->reference_strength=fmin(1.0,fmax(0.0,(fabs(s->reference_mean)-.90)/2.0));
 156:     return s->reference_strength;
 157: }
 158: 
 159: /* Fast redundancy contract: independent-chain calibration cancels in changes.
 160:  * Combined bounded sample noise is <=0.20 C; two samples permit 0.40 C.
 161:  * Legal differential ramps up to 1.2 C/s add 1.2*dt. Freeze the last
 162:  * pre-event acquisition for at most 300 ms. Two consecutive same-direction
 163:  * out-of-envelope residuals certify persistence; one isolated spike cannot.
 164:  * Recurrent alternating pulses instead require >=3 excessive edges in 1 s:
 165:  * an isolated spike and its recovery supply at most two edges. Both tests
 166:  * are one short-history consistency provider, not independent DS sources.
 167:  * A confirmed contract violation supplies direct sensor evidence (as other
 168:  * runtime contract providers do), not a calibrated fault probability.
 169:  */
 170: static double fast_redundant_sensor(clo_revised_t *s,const runtime_observation_t *o)
 171: {
 172:     s->fast_strength=0;
 173:     bool valid=o->reference_enabled && o->reference_valid && !o->reference_failed &&
 174:         o->source_valid && o->source_ms==o->time_ms && o->reference_ms==o->source_ms &&
 175:         isfinite(o->source_c) && isfinite(o->reference_c);
 176:     if(!valid || (s->fast_valid && o->time_ms!=s->fast_last_ms+ECU_SENSOR_PERIOD_MS)) {
 177:         s->fast_valid=false;s->fast_active=false;s->fast_count=0;
 178:         s->fast_index=0;s->fast_edges=0;
 179:         s->fast_integral=0;s->fast_bound_integral=0;s->fast_integral_count=0;
 180:         for(unsigned int i=0;i<10;i++)s->fast_edge_history[i]=0;
 181:     }
 182:     if(!valid)return 0;
 183:     double delta=(double)o->source_c-o->reference_c;
 184:     bool edge=s->fast_valid && fabs(delta-s->fast_previous)>.40+1.2*ECU_SENSOR_PERIOD_MS/1000.;
 185:     s->fast_edges-=s->fast_edge_history[s->fast_index];
 186:     s->fast_edge_history[s->fast_index]=edge;s->fast_edges+=edge;
 187:     s->fast_index=(s->fast_index+1)%10;
 188:     if(s->fast_active && o->time_ms-s->fast_anchor_ms>300)s->fast_active=false;
 189:     if(edge && !s->fast_active) {
 190:         s->fast_anchor=s->fast_previous;s->fast_anchor_ms=s->fast_last_ms;
 191:         s->fast_active=true;s->fast_count=0;s->fast_sign=0;
 192:         s->fast_integral=0;s->fast_bound_integral=0;s->fast_integral_count=0;s->fast_integral_sign=0;
 193:     }
 194:     if(s->fast_active) {
 195:         double h=(o->time_ms-s->fast_anchor_ms)/1000.;
 196:         double residual=delta-s->fast_anchor;
 197:         int sign=residual>0?1:-1;
 198:         /* Bounded signed-window certificate: both acquisitions must exceed
 199:          * the0.40C noise-only floor in the same direction; their mean must
 200:          * exceed the mean original slew+noise envelope. Never carry across
 201:          * a recovery, sign reversal, gap or expired300ms anchor. This uses
 202:          * the existing uncertainty bounds, not a lower detection threshold. */
 203:         if(fabs(residual)>.40 && (!s->fast_integral_count || sign==s->fast_integral_sign)) {
 204:             s->fast_integral+=fabs(residual);s->fast_bound_integral+=.40+1.2*h;
 205:             s->fast_integral_count++;s->fast_integral_sign=sign;
 206:             if(s->fast_integral_count>=2 && s->fast_integral>s->fast_bound_integral)
 207:                 s->fast_strength=1;
 208:         } else {s->fast_integral=0;s->fast_bound_integral=0;s->fast_integral_count=0;}
 209:         if(fabs(residual)>.40+1.2*h) {
 210:             s->fast_count=sign==s->fast_sign?s->fast_count+1:1;s->fast_sign=sign;
 211:             if(s->fast_count>=2)s->fast_strength=1;
 212:         } else {s->fast_active=false;s->fast_count=0;}
 213:     }
 214:     if(s->fast_edges>=3)s->fast_strength=1;
 215:     s->fast_previous=delta;s->fast_last_ms=o->time_ms;s->fast_valid=true;
 216:     return s->fast_strength;
 217: }
 218: 
 219: #include <string.h>
 220: static double unit(double x) { return x<0?0:x>1?1:x; }
 221: static void support(ds_mass_t *m,unsigned int subset,double strength)
 222: {
 223:     ds_vacuous(m);
 224:     if(subset==DS_THETA)return; /* Indistinguishable origins remain vacuous. */
 225:     m->mass[subset]=unit(strength);m->mass[DS_THETA]=1-unit(strength);
 226: }
 227: static bool combine(ds_mass_t *current,const ds_mass_t *channel,double *step,double *maximum)
 228: {
 229:     bool ok=ds_combine(current,channel,DS_DEMPSTER,current,step);
 230:     if(*step>*maximum)*maximum=*step;
 231:     return ok;
 232: }
 233: void clo_triplex_core_init(clo_revised_t *s)
 234: {
 235:     memset(s,0,sizeof(*s));
 236:     clo_final_init(&s->fusion);
 237: }
 238: void clo_triplex_core_step(clo_revised_t *state,const clo_final_config_t *c,const runtime_observation_t *o)
 239: {
 240:     clo_final_t *s=&state->fusion;
 241:     if(s->has_previous_time && o->time_ms<=s->previous_time_ms)return;
 242:     s->has_previous_time=true;s->previous_time_ms=o->time_ms;
 243:     clo_triplex_core_extract(&s->evidence,o);
 244:     double local = local_sensor_strength(o);ba_provider[0]=s->evidence.strength[3];ba_provider[1]=local;
 245:     /* A minimal two-edge total-variation residual catches weak alternating
 246:      * pulses that a discounted one-step residual forgets between excursions.
 247:      * Reuse the same physical slew envelope and 2 C normalization. Only adjacent
 248:      * opposing excesses are added, never same-direction thermal excursions or
 249:      * missing/gapped samples. This replaces one feature; it is not a second DS
 250:      * source and is not recursively accumulated. */
 251:     bool valid=o->source_valid && o->source_previous_valid &&
 252:         o->source_ms==o->time_ms && o->source_previous_ms<o->source_ms &&
 253:         isfinite(o->source_c) && isfinite(o->source_previous_c);
 254:     double excess=0;int direction=0;
 255:     if(valid) {
 256:         double delta=(double)o->source_c-o->source_previous_c;
 257:         double dt=(o->source_ms-o->source_previous_ms)/1000.0;
 258:         excess=fmax(0.0,(fabs(delta)-2.5*dt)/2.0);
 259:         direction=delta>0?1:delta<0?-1:0;
 260:         if(excess>0 && state->previous_local_excess>0 && state->previous_local_valid &&
 261:            state->previous_local_ms==o->source_previous_ms &&
 262:            direction==-state->previous_local_direction)
 263:             local=fmax(local,fmin(1.0,excess+state->previous_local_excess));
 264:     }
 265:     state->previous_local_valid=valid;
 266:     state->previous_local_excess=excess;
 267:     state->previous_local_direction=direction;
 268:     state->previous_local_ms=o->source_ms;
 269:     /* A startup thermal transient can violate absolute slew without sensor
 270:      * inconsistency. Qualify that provider against its own2.5C/s contract:
 271:      * five consecutive contiguous in-envelope acquisitions (the existing
 272:      * forecast history length). This gates ORIGIN only, never anomaly.
 273:      * Differential/forecast/status providers retain their own qualification,
 274:      * allowing legitimate early faults to alarm and localize independently. */
 275:     bool slew_contiguous=valid && o->source_ms==o->source_previous_ms+ECU_SENSOR_PERIOD_MS &&
 276:         (!state->slew_qualification_count || o->source_previous_ms==state->slew_qualification_ms);
 277:     if(!slew_contiguous)state->slew_qualification_count=0;
 278:     if(slew_contiguous && state->slew_qualification_count<5) {
 279:         if(fabs(o->source_c-o->source_previous_c)<=2.5*ECU_SENSOR_PERIOD_MS/1000.)
 280:             state->slew_qualification_count++;
 281:         else state->slew_qualification_count=0;
 282:     }
 283:     state->slew_qualification_ms=o->source_ms;
 284:     double origin_local=state->slew_qualification_count>=5 ? local :
 285:         (o->source_valid && o->source_ms==o->time_ms && isfinite(o->source_c) &&
 286:          (o->source_c<ECU_SENSOR_IMPLAUSIBLE_LOW_C || o->source_c>ECU_SENSOR_IMPLAUSIBLE_HIGH_C) ? 1.0 : 0.0);
 287:     ba_provider[2]=local;ba_provider[3]=sensor_response(state,o);ba_provider[4]=redundant_sensor(state,o);double independent=fmax(ba_provider[3],ba_provider[4]);
 288:     ba_provider[5]=fast_redundant_sensor(state,o);ba_provider[6]=triplex_extra_strength;independent=fmax(independent,ba_provider[5]);
 289:     independent=fmax(independent,triplex_extra_strength);
 290:     local=fmax(local,independent);
 291:     origin_local=fmax(origin_local,independent);
 292: 
 293:     local=fmax(local,dc_mass);origin_local=fmax(origin_local,dc_origin);
 294:     s->evidence.strength[3] = fmax(s->evidence.strength[3], local);
 295: 
 296:     s->evidence.available[3] = s->evidence.available[3] || local > 0;
 297:     /* Establish precedence only from a directly observed contract violation,
 298:      * never from the leading BetP guess. Same-tick competing observations do
 299:      * not establish a causal order. Weak local residuals cannot reserve origin. */
 300:     /* Zero command/response is not a recovery witness for a stuck actuator.
 301:      * Retain provenance until that same component successfully responds to a
 302:      * positive command. This records a contract, not an indefinitely fixed label. */
 303:     bool actuator_recovered=true;
 304:     if(s->evidence.available[4]) {
 305:         const float command[2]={o->pump_command,o->fan_command};
 306:         const float actual[2]={o->pump_actual,o->fan_actual};
 307:         for(unsigned int i=0;i<2;i++) {
 308:             if(outside_response_contract(command[i],actual[i]))state->actuator_unresolved|=1U<<i;
 309:             if((state->actuator_unresolved&(1U<<i)) &&
 310:                (command[i]<=0 || outside_response_contract(command[i],actual[i])))actuator_recovered=false;
 311:         }
 312:     }
 313:     else if(state->actuator_unresolved)actuator_recovered=false;
 314:     /* A quiet, clipped/sub-ambient cooling excursion is not thermal recovery.
 315:      * This passive coolant circuit has no refrigeration. Cold starts can be
 316:      * below current ambient, so this only delays re-arming an existing actuator
 317:      * episode; it never creates an alarm or assigns an origin. Missing trusted
 318:      * acquisition/ambient evidence likewise cannot certify recovery. */
 319:     if(state->actuator_unresolved &&
 320:        (!o->source_valid || o->source_ms!=o->time_ms || !isfinite(o->source_c) ||
 321:         !isfinite(o->ambient_c) || o->source_c<o->ambient_c))actuator_recovered=false;
 322:     benchmark_capture(1,state,o,origin_local,local);
 323:     unsigned int direct=0, direct_count=0;
 324:     for(int i=0;i<CLO_CHANNELS;i++)
 325:         if(i!=3 && i!=5 && s->evidence.available[i] &&
 326:            s->evidence.strength[i]>=c->confirmed_threshold)
 327:             { direct |= c2_origin_support[i]; direct_count++; }
 328:     if(direct && !state->direct_origins) {
 329:         state->direct_origins=direct;
 330:         state->direct_onset_ms=o->time_ms;
 331:         if(direct_count>1 || (origin_local>=c->confirmed_threshold && !state->sensor_established_first))
 332:             state->ambiguous_onset=true;
 333:     }
 334:     const bool downstream_sensor=state->direct_origins &&
 335:         !state->sensor_established_first && o->time_ms>state->direct_onset_ms;
 336:     c2_output_t *v=&s->output;
 337:     v->detection_conflict=v->localization_conflict=0;
 338:     v->detection_fallback=v->localization_fallback=false;
 339:     memset(v->detection_conflict_steps,0,sizeof(v->detection_conflict_steps));
 340:     memset(v->localization_conflict_steps,0,sizeof(v->localization_conflict_steps));
 341:     ds_mass_t detect,origin,channel;
 342:     ds_vacuous(&detect);ds_vacuous(&origin);
 343:     v->propagation_support=false;
 344:     for(int i=0;i<CLO_CHANNELS;i++) {
 345:         double strength=s->evidence.available[i]?s->evidence.strength[i]:0;
 346:         double rd=s->evidence.available[i]?c->r_detection:0;
 347:         /* Detection never reads origin mass, its discount, or propagation. */
 348:         support(&channel,C2_D_ABNORMAL,strength);
 349:         ds_discount(&channel,rd,&channel);
 350:         if(!combine(&detect,&channel,&v->detection_conflict_steps[i],&v->detection_conflict))v->detection_fallback=true;
 351:         /* One source mass per channel: do not count delivered and local
 352:          * observations twice. Singleton support never exceeds local evidence. */
 353:         unsigned int subset = c2_origin_support[i];
 354:         double origin_strength = strength;
 355:         if (i == 3 && local > 0) { subset = c2_origin_blocks[3]; origin_strength = origin_local; }
 356:         /* Suppress contamination only in localization. Detection above still
 357:          * receives the entire measured anomaly. No propagation bonus/locking. */
 358:         if(i==3 && downstream_sensor)origin_strength=0;
 359:         support(&channel,subset,origin_strength);
 360:         if(!combine(&origin,&channel,&v->localization_conflict_steps[i],&v->localization_conflict))v->localization_fallback=true;
 361:     }
 362:     { /* Temporal fusion is always part of the final algorithm. */
 363:         ds_discount(&s->detection_mass,c->lambda_temporal,&channel);
 364:         if(!combine(&detect,&channel,&v->detection_conflict_steps[6],&v->detection_conflict))v->detection_fallback=true;
 365:         ds_discount(&s->origin_mass,c->lambda_temporal,&channel);
 366:         if(!combine(&origin,&channel,&v->localization_conflict_steps[6],&v->localization_conflict))v->localization_fallback=true;
 367:     }
 368:     s->detection_mass=detect;s->origin_mass=origin;
 369:     v->anomaly_belief=ds_belief(&detect,C2_D_ABNORMAL);
 370:     v->anomaly_plausibility=ds_plausibility(&detect,C2_D_ABNORMAL);
 371:     v->anomaly_decision_score=v->anomaly_belief;v->anomaly_ignorance=detect.mass[DS_THETA];
 372:     if(v->anomaly_decision_score>=c->confirmed_threshold) {
 373:         if(s->confirmation_count<c->confirmation_persistence)s->confirmation_count++;
 374:     } else s->confirmation_count=0;
 375:     v->alarm=s->confirmation_count>=c->confirmation_persistence;
 376:     /* Unqualified absolute-slew history may accumulate, but cannot alone
 377:      * confirm an anomaly. Any independently qualified provider can corroborate;
 378:      * this is the same runtime qualification used for origin, not a timer. */
 379:     bool qualified_current=origin_local>0 || s->evidence.strength[3]>local;
 380:     for(int i=0;i<CLO_CHANNELS;i++)
 381:         if(i!=3 && i!=5 && s->evidence.available[i] && s->evidence.strength[i]>0)
 382:             qualified_current=true;
 383:     if(qualified_current)state->qualified_anomaly_episode=true;
 384:     if(state->slew_qualification_count<5 && !state->qualified_anomaly_episode)v->alarm=false;
 385:     v->state=v->alarm?CLO_STATE_CONFIRMED:v->anomaly_decision_score>=c->suspect_threshold?CLO_STATE_SUSPECT:CLO_STATE_NORMAL;
 386:     if(v->alarm && v->alarm_timestamp_ms<0)v->alarm_timestamp_ms=(int)o->time_ms;
 387:     c2_origin_betp(&origin,v->origin_scores);
 388:     double best=-1,second=-1;unsigned int top=0;
 389:     for(unsigned int i=0;i<5;i++) {
 390:         if(v->origin_scores[i]>best) {second=best;best=v->origin_scores[i];top=i;}
 391:         else if(v->origin_scores[i]>second)second=v->origin_scores[i];
 392:     }
 393:     v->leading_origin=1U<<(top+1); /* Public names use Candidate 1 origin IDs. */
 394:     v->origin_score=best;v->origin_margin=best-second;
 395:     v->origin_belief=ds_belief(&origin,c2_origin_blocks[top]);
 396:     v->origin_plausibility=ds_plausibility(&origin,c2_origin_blocks[top]);
 397:     v->origin_ignorance=origin.mass[DS_THETA];
 398:     v->localization_valid=v->alarm && best>=c->localization_threshold &&
 399:         v->origin_margin>=c->localization_margin_threshold && v->origin_ignorance<=c->ignorance_limit;
 400:     if(state->ambiguous_onset || (triplex_extra_ambiguous && !state->direct_origins))v->localization_valid=false;
 401:     v->estimated_origin=v->localization_valid?v->leading_origin:0;
 402:     if(!state->direct_origins && origin_local>0 && v->localization_valid &&
 403:        v->estimated_origin==CLO_SENSOR_CONTROL)state->sensor_established_first=true;
 404:     /* Quiet recovery closes the episode. A subsequent unrelated sensor event
 405:      * can establish its own origin. Earlier mass still decays normally to UNKNOWN. */
 406:     bool evidence_quiet=true;
 407:     for(int i=0;i<CLO_CHANNELS;i++)
 408:         if(s->evidence.available[i] && s->evidence.strength[i]>0)evidence_quiet=false;
 409:     if(v->state==CLO_STATE_NORMAL && evidence_quiet && actuator_recovered) {
 410:         state->qualified_anomaly_episode=false;
 411:         state->actuator_unresolved=0;
 412:         state->direct_origins=0;
 413:         state->direct_onset_ms=0;
 414:         state->sensor_established_first=false;
 415:         state->ambiguous_onset=false;
 416:     }
 417:     if(v->localization_valid && v->localization_timestamp_ms<0)v->localization_timestamp_ms=(int)o->time_ms;
 418:     ba_capture(state,o,origin_local);
 419: }
```


### Exact source: candidate2_observability.c

**VERIFIED FROM SOURCE.** `src/v7_1/candidate2_observability.c` — `file`, lines 1–21

```text
   1: #include "clo_dsf_candidate2.h"
   2: /* Five disjoint blocks cover all six storage bits. No NORMAL origin exists.
   3:  * MEMORY's two storage bits are ONE logical atom, not extra evidence. */
   4: const unsigned int c2_origin_blocks[5]={33U,2U,4U,8U,16U};
   5: const unsigned int c2_origin_support[CLO_CHANNELS]={2U,4U,33U,4U|8U,16U,DS_THETA};
   6: unsigned int c2_encode_origin_subset(unsigned int logical_mask)
   7: {
   8:     unsigned int encoded=0;
   9:     for(unsigned int i=0;i<5;i++) if(logical_mask&(1U<<i)) encoded|=c2_origin_blocks[i];
  10:     return encoded;
  11: }
  12: void c2_origin_betp(const ds_mass_t *m,double scores[5])
  13: {
  14:     for(unsigned int i=0;i<5;i++) scores[i]=0;
  15:     for(unsigned int subset=1;subset<32;subset++) {
  16:         unsigned int n=0;
  17:         for(unsigned int i=0;i<5;i++) n+=(subset&(1U<<i))!=0;
  18:         double share=m->mass[c2_encode_origin_subset(subset)]/n;
  19:         for(unsigned int i=0;i<5;i++) if(subset&(1U<<i)) scores[i]+=share;
  20:     }
  21: }
```


### Exact source: ds_evidence.c

**VERIFIED FROM SOURCE.** `src/v7/ds_evidence.c` — `file`, lines 1–85

```text
   1: #include "ds_evidence.h"
   2: #include <math.h>
   3: #include <string.h>
   4: void ds_empty(ds_mass_t *m) { memset(m, 0, sizeof(*m)); }
   5: void ds_vacuous(ds_mass_t *m) { ds_empty(m); m->mass[DS_THETA] = 1; }
   6: bool ds_assign(ds_mass_t *m, unsigned int subset, double mass)
   7: {
   8:     if (!subset || subset > DS_THETA || !isfinite(mass) || mass < 0 || mass > 1) return false;
   9:     m->mass[subset] = mass;
  10:     return true;
  11: }
  12: bool ds_normalize(ds_mass_t *m)
  13: {
  14:     double total = 0;
  15:     if (m->mass[0] != 0) return false;
  16:     for (unsigned int i = 1; i < DS_SIZE; i++) {
  17:         if (!isfinite(m->mass[i]) || m->mass[i] < 0) return false;
  18:         total += m->mass[i];
  19:     }
  20:     if (!isfinite(total) || total <= 0) return false;
  21:     for (unsigned int i = 1; i < DS_SIZE; i++) m->mass[i] /= total;
  22:     return true;
  23: }
  24: bool ds_valid(const ds_mass_t *m)
  25: {
  26:     double total = 0;
  27:     if (m->mass[0] != 0) return false;
  28:     for (unsigned int i = 1; i < DS_SIZE; i++) {
  29:         if (!isfinite(m->mass[i]) || m->mass[i] < 0 || m->mass[i] > 1) return false;
  30:         total += m->mass[i];
  31:     }
  32:     return fabs(total - 1) < 1e-10;
  33: }
  34: double ds_belief(const ds_mass_t *m, unsigned int subset)
  35: {
  36:     double result = 0;
  37:     for (unsigned int i = 1; i < DS_SIZE; i++) if ((i & subset) == i) result += m->mass[i];
  38:     return result;
  39: }
  40: double ds_plausibility(const ds_mass_t *m, unsigned int subset)
  41: {
  42:     double result = 0;
  43:     for (unsigned int i = 1; i < DS_SIZE; i++) if (i & subset) result += m->mass[i];
  44:     return result;
  45: }
  46: void ds_pignistic(const ds_mass_t *m, double scores[DS_ATOMS])
  47: {
  48:     for (unsigned int atom = 0; atom < DS_ATOMS; atom++) scores[atom] = 0;
  49:     for (unsigned int i = 1; i < DS_SIZE; i++) {
  50:         unsigned int count = 0;
  51:         for (unsigned int b = 0; b < DS_ATOMS; b++) if (i & (1U << b)) count++;
  52:         for (unsigned int b = 0; b < DS_ATOMS; b++) if (i & (1U << b)) scores[b] += m->mass[i] / count;
  53:     }
  54: }
  55: bool ds_discount(const ds_mass_t *m, double r, ds_mass_t *out)
  56: {
  57:     if (!ds_valid(m) || !isfinite(r) || r < 0 || r > 1) return false;
  58:     ds_mass_t result;
  59:     ds_empty(&result);
  60:     for (unsigned int i = 1; i < DS_SIZE; i++) result.mass[i] = r * m->mass[i];
  61:     result.mass[DS_THETA] += 1 - r;
  62:     *out = result;
  63:     return true;
  64: }
  65: bool ds_combine(const ds_mass_t *a, const ds_mass_t *b, ds_rule_t rule,
  66:                 ds_mass_t *out, double *conflict)
  67: {
  68:     if (!ds_valid(a) || !ds_valid(b) || (rule != DS_DEMPSTER && rule != DS_YAGER)) return false;
  69:     ds_mass_t result;
  70:     ds_empty(&result);
  71:     for (unsigned int i = 1; i < DS_SIZE; i++) {
  72:         if (!a->mass[i]) continue;
  73:         for (unsigned int j = 1; j < DS_SIZE; j++)
  74:             if (b->mass[j]) result.mass[i & j] += a->mass[i] * b->mass[j];
  75:     }
  76:     *conflict = result.mass[0];
  77:     result.mass[0] = 0;
  78:     if (rule == DS_YAGER) result.mass[DS_THETA] += *conflict;
  79:     else if (1 - *conflict <= 1e-12) { ds_vacuous(out); return false; }
  80:     /* For Dempster, normalizing the nonempty sum is division by 1-K.
  81:      * For Yager this only removes floating-point roundoff. */
  82:     if (!ds_normalize(&result)) { ds_vacuous(out); return false; }
  83:     *out = result;
  84:     return true;
  85: }
```


### Exact source: triplex_consistency.c

**VERIFIED FROM SOURCE.** `src/v7_3/triplex_consistency.c` — `file`, lines 1–31

```text
   1: #include "triplex_consistency.h"
   2: #include <math.h>
   3: #include <string.h>
   4: void triplex_consistency_init(triplex_consistency_t *s){memset(s,0,sizeof(*s));clo_revised_init(&s->ac);clo_revised_init(&s->bc);}
   5: void triplex_consistency_step(triplex_consistency_t *s,const runtime_observation_t *o,const diagnostic_readout_t *c)
   6: {
   7:  s->strength=s->ac_strength=s->bc_strength=0;s->qualified=false;s->ambiguous=false;s->member_pattern=0;
   8:  runtime_observation_t ac=*o,bc=*o;
   9:  bool valid=c->valid&&c->previous_valid&&!c->failed&&c->sample_ms<=o->time_ms&&o->time_ms-c->sample_ms<=100&&c->sample_ms==c->previous_ms+100;
  10:  double projected=0;
  11:  if(valid){projected=c->value_c+(c->value_c-c->previous_c)*(double)(o->time_ms-c->sample_ms)/(c->sample_ms-c->previous_ms);valid=isfinite(projected);}
  12:  /* Only causal acquired C samples are projected to the A/B epoch. No physical
  13:     state or injection metadata is available to this module. */
  14:  ac.reference_enabled=true;ac.reference_valid=valid;ac.reference_failed=false;ac.reference_ms=o->time_ms;ac.reference_c=(float)projected;
  15:  bc=ac;bc.source_c=o->reference_c;bc.source_valid=o->reference_valid&&!o->reference_failed;bc.source_ms=o->reference_ms;
  16:  s->ac_strength=clo_existing_pair_strength(&s->ac,&ac);s->bc_strength=clo_existing_pair_strength(&s->bc,&bc);
  17:  if(valid){s->samples++;s->qualified=s->samples>=5;}else s->samples=0;
  18:  /* Explicit independently timestamped failed/stale acquisition is a diagnostic
  19:     channel contract violation, never evidence from the injector's state. */
  20:  bool status=o->time_ms>500&&(c->failed||(c->valid&&o->time_ms>c->sample_ms+200));
  21:  if(s->qualified)s->strength=fmax(s->ac_strength,s->bc_strength);
  22:  if(status)s->strength=1;
  23:  s->aligned_c=projected;
  24:  if(valid&&o->source_valid&&o->reference_valid){
  25:   bool ab=fabs(o->source_c-o->reference_c)<=.90,ac_ok=fabs(o->source_c-projected)<=.90,bc_ok=fabs(o->reference_c-projected)<=.90;
  26:   /* Pattern identifies a disagreement cut, NOT which side is actually faulty.
  27:      1=A|BC,2=B|AC,3=C|AB,4=all mutually disagree;0=no unique cut. */
  28:   s->member_pattern=bc_ok&&!ab&&!ac_ok?1:ac_ok&&!ab&&!bc_ok?2:ab&&!ac_ok&&!bc_ok?3:!ab&&!ac_ok&&!bc_ok?4:0;
  29:   s->ambiguous=s->member_pattern==4;
  30:  }
  31: }
```


### Exact source: digital_sensor_integrity.c

**VERIFIED FROM SOURCE.** `src/v7_3/digital_sensor_integrity.c` — `file`, lines 1–34

```text
   1: #include "digital_sensor_integrity.h"
   2: #include <string.h>
   3: /* CRC-32 covers canonical little-endian words; no struct padding or pointers.
   4:  * The protected record models an isolated driver mailbox. CRC is not a MAC.
   5:  * Independent protected storage, NOT secrecy of the polynomial, is the trust
   6:  * assumption. Producer and legitimate transform API alone may update it. */
   7: uint32_t di_tag(const di_record_t *r){
   8:  uint32_t crc=~0U,v[4]={r->channel,r->bits,r->sequence,r->ms};
   9:  for(unsigned i=0;i<4;i++)for(unsigned b=0;b<4;b++){
  10:   crc^=(v[i]>>(8*b))&255U;
  11:   for(unsigned k=0;k<8;k++)crc=(crc>>1)^((0U-(crc&1U))&0xedb88320U);
  12:  }
  13:  return ~crc;
  14: }
  15: void di_publish(di_witness_t *w,di_record_t *r,unsigned channel,float value,unsigned ms){
  16:  di_record_t p={.channel=channel,.sequence=w->valid?w->protected_record.sequence+1:1,.ms=ms};
  17:  memcpy(&p.bits,&value,sizeof p.bits);p.tag=di_tag(&p);w->protected_record=p;w->valid=true;*r=p;
  18: }
  19: void di_transform(di_witness_t *w,di_record_t *r,float offset){
  20:  if(!w->valid)return;
  21:  float v;memcpy(&v,&w->protected_record.bits,sizeof v);v+=offset;
  22:  memcpy(&w->protected_record.bits,&v,sizeof v);w->protected_record.tag=di_tag(&w->protected_record);
  23:  /* Update only envelope integrity, never overwrite the delivered value. */
  24:  *r=w->protected_record;
  25: }
  26: unsigned di_verify(const di_witness_t *w,const di_record_t *r,float value,unsigned ms){
  27:  if(!w->valid)return 0;
  28:  uint32_t bits;memcpy(&bits,&value,sizeof bits);
  29:  const di_record_t *p=&w->protected_record;unsigned status=0;
  30:  if(p->tag!=di_tag(p)||r->tag!=di_tag(r))status|=4;
  31:  if(bits!=p->bits||r->bits!=p->bits||r->tag!=p->tag||r->channel!=p->channel)status|=1;
  32:  if(ms!=p->ms||r->sequence!=p->sequence||r->ms!=p->ms)status|=2;
  33:  return status;
  34: }
```


### Exact source: sensor_confirmation.c

**VERIFIED FROM SOURCE.** `src/v7_3/sensor_confirmation.c` — `file`, lines 1–15

```text
   1: #include "sensor_confirmation.h"
   2: #include <math.h>
   3: bool sensor_confirmation_step(sensor_confirmation_t *s,unsigned ms,bool pass,
   4:  bool other,double strength,bool alarm,unsigned required,double threshold)
   5: {
   6:  if(!required)return alarm;
   7:  /* FAIL and UNKNOWN never permit suppression, including duplicate timestamps. */
   8:  if(!pass||other){s->count=0;s->previous_ms=ms;s->initialized=true;s->last=alarm;return alarm;}
   9:  if(s->initialized&&ms<=s->previous_ms)return alarm&&s->last;
  10:  if(!s->initialized||ms-s->previous_ms!=100)s->count=0;
  11:  s->initialized=true;s->previous_ms=ms;
  12:  if(isfinite(strength)&&strength>0&&strength>=threshold){if(s->count<required)s->count++;}
  13:  else s->count=0;
  14:  s->last=alarm&&s->count>=required;return s->last;
  15: }
```


### Exact source: dc_probe

**VERIFIED FROM SOURCE.** `/tmp/clo-integrity-final-unseen/work/adapter.c` — `dc_probe`, lines 59–78

```text
  59: static void dc_probe(ecu_state_t *state){
  60:  if(!state->log_file)return;
  61:  static bool phases[100],initialized;
  62:  if(!initialized){
  63:   for(unsigned i=0;i<10;i++)phases[11*i]=true;
  64:   for(unsigned n=10;n<40;n++){
  65:    unsigned best=0,begin=0;
  66:    for(unsigned i=0;i<100;i++)if(phases[i]){unsigned gap=1;while(!phases[(i+gap)%100])gap++;if(gap>best){best=gap;begin=i;}}
  67:    phases[(begin+best/2)%100]=true;
  68:   }initialized=true;
  69:  }
  70:  unsigned now=state->time.time_ms;
  71:  if(now%100||!phases[(now/100)%100]||(dc_memory.valid&&now<=dc_memory.checked_ms))return;
  72:  uint16_t before=state->control.target_register_c,saved=cross_layer_memory_read(state);
  73:  cross_layer_memory_write(state,0);bool failed=cross_layer_memory_read(state)!=0;
  74:  cross_layer_memory_write(state,UINT16_MAX);failed=(cross_layer_memory_read(state)!=UINT16_MAX)||failed;
  75:  cross_layer_memory_write(state,saved);failed=(cross_layer_memory_read(state)!=saved)||failed;
  76:  dc_memory.checked_ms=now;dc_memory.checks++;dc_memory.operations+=7;dc_memory.valid=true;dc_memory.failed=failed;
  77:  if(before!=state->control.target_register_c)abort();
  78: }
```


### Exact source: ba_capture

**VERIFIED FROM SOURCE.** `/tmp/clo-integrity-final-unseen/work/adapter.c` — `ba_capture`, lines 164–181

```text
 164: void ba_capture(const clo_revised_t *s,const runtime_observation_t *o,double qualified){
 165:  if(plus_arch!=6)return;
 166:  if(!ba_log)ba_log=fopen(getenv("BA_LOG"),"w");
 167:  const clo_evidence_t *e=&s->fusion.evidence;unsigned other=0;
 168:  for(unsigned i=0;i<6;i++)if(i!=3&&e->available[i]&&e->strength[i]>0)other|=1U<<i;
 169:  bool fail=false;for(unsigned i=0;i<3;i++)if(ba_current->until[i]&&o->time_ms<ba_current->until[i])fail=true;
 170:  fprintf(ba_log,"%u,%u,%u,%u,%u,%.17g",o->time_ms,ba_current->available,ba_current->bad,fail,other,qualified);
 171:  for(unsigned i=0;i<6;i++)fprintf(ba_log,",%.17g",e->available[i]?e->strength[i]:0.);
 172:  for(unsigned i=0;i<7;i++)fprintf(ba_log,",%.17g",ba_provider[i]);
 173:  fprintf(ba_log,",%.17g,%u,%u,%u",s->fusion.output.anomaly_decision_score,s->fusion.output.alarm,s->fusion.output.estimated_origin,s->direct_origins);
 174:  const unsigned count[5]={0,2,3,1,3};const double threshold[5]={0,.5,.5,.75,.75};
 175:  if(getenv("BA_CHOICE"))ba_choice=(unsigned)strtoul(getenv("BA_CHOICE"),NULL,10);
 176:  for(unsigned k=0;k<5;k++){
 177:   int alarm=-1;
 178:   if(ba_choice==99||k==0||k==ba_choice)alarm=sensor_confirmation_step(&ba_gate[k],o->time_ms,ba_current->available==7&&!ba_current->bad&&!fail,other||s->direct_origins,qualified,s->fusion.output.alarm,count[k],threshold[k]);
 179:   fprintf(ba_log,",%d",alarm);
 180:  }fprintf(ba_log,"\n");
 181: }
```


### Exact source: __wrap_detection_algorithm_step

**VERIFIED FROM SOURCE.** `/tmp/clo-integrity-final-unseen/work/adapter.c` — `__wrap_detection_algorithm_step`, lines 359–412

```text
 359: void __wrap_detection_algorithm_step(struct ecu_state *state)
 360: {
 361:  if(!enabled || !state->log_file){__real_detection_algorithm_step(state);return;}
 362:  runtime_observation_t o;runtime_observation_capture(state,&o);
 363:  if(observations)final_observation_write(observations,&o);
 364:  clo_revised_step(&detector,&config,&o);
 365:  clo_final_diagnostic(&detector.fusion.evidence,o.time_ms,3000);
 366:  final_score(0,o.time_ms,&detector.fusion.output);
 367:  if(trace)log_row(trace,o.time_ms,&detector,&o);
 368:  if(comparison) {
 369:   clo_prechange_step(&prechange,&config,&o);clo_final_diagnostic(&prechange.fusion.evidence,o.time_ms,3000);
 370:   if(memcmp(&prechange,&detector,sizeof(detector)))abort();
 371:   triplex_consistency_step(&triplex,&o,&diagnostic_c.output);triplex_extra_strength=triplex.strength;triplex_extra_ambiguous=triplex.ambiguous;
 372:   dc_mass=dc_origin=dc_discount=0;plus_arch=0;double begin=cpu();
 373:   clo_triplex_core_step(&triplex_detector,&config,&o);clo_final_diagnostic(&triplex_detector.fusion.evidence,o.time_ms,3000);
 374:   core_cpu[0]+=cpu()-begin;
 375:   final_score(1,o.time_ms,&triplex_detector.fusion.output);
 376: 
 377:  const unsigned memory_index[5]={1,2,0,1,2};
 378:  for(unsigned j=0;j<5;j++){
 379:   if(plus_host_mode!=99&&plus_host_mode!=j+1)continue;
 380:   runtime_observation_t x=o;
 381:   if(j==99&&memory_index[j]){
 382:    memory_diagnostic_t *m=&plus_memory[memory_index[j]-1];
 383:    x.memory_check_ms=m->checked_ms;x.memory_check_valid=m->valid;x.memory_check_failed=m->failed;
 384:   }
 385:   triplex_extra_strength=triplex.strength;triplex_extra_ambiguous=triplex.ambiguous;
 386:   
 387:   dc_mass=dc_origin=di_strength(state,o.time_ms);plus_arch=j+1;double begin=cpu();clo_triplex_core_step(&plus_detector[j],&config,&x);
 388:   core_cpu[j+1]+=cpu()-begin;clo_final_diagnostic(&plus_detector[j].fusion.evidence,o.time_ms,3000);
 389:   final_score(j+2,o.time_ms,&plus_detector[j].fusion.output);
 390:  if(j==1){
 391:   runtime_observation_t z=o;z.memory_check_ms=dc_memory.checked_ms;z.memory_check_valid=dc_memory.valid;z.memory_check_failed=dc_memory.failed;
 392:   ba_current=di_bank(state);plus_arch=6;clo_triplex_core_step(&dc_memory_detector,&config,&z);clo_final_diagnostic(&dc_memory_detector.fusion.evidence,z.time_ms,3000);final_score(2,z.time_ms,&dc_memory_detector.fusion.output);
 393: if(!dc_input_log)dc_input_log=fopen(getenv("DC_INPUT"),"w");
 394:   bool qualified=o.time_ms>=1000&&triplex.qualified&&triplex_detector.slew_qualification_count>=5&&o.source_valid&&o.source_ms==o.time_ms&&o.reference_valid&&!o.reference_failed&&o.reference_ms==o.time_ms&&o.sample_timestamp_ms==o.source_ms;
 395:   dc_packet_t q={.o=o,.extra=triplex.strength,.c=triplex.aligned_c,.m={plus_memory[1],dc_memory},.ambiguous=triplex.ambiguous,.qualified=qualified};
 396:   fprintf(dc_input_log,"%u,%.17g,%.17g,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n",o.time_ms,o.source_c-q.c,o.reference_c-q.c,qualified,triplex_detector.fusion.output.alarm,triplex_detector.fusion.output.estimated_origin,plus_detector[j].fusion.output.alarm,plus_detector[j].fusion.output.estimated_origin,dc_memory_detector.fusion.output.alarm,dc_memory_detector.fusion.output.estimated_origin,state->control.memory_diagnostic.checks,plus_memory[1].checks,dc_memory.checks,o.source_c,o.reference_c,q.c,o.engine_load,o.pump_command,o.fan_command,o.vehicle_speed_kph,q.extra);
 397:   if(!di_log)di_log=fopen(getenv("DI_LOG"),"w");di_bank_t *ib=di_bank(state);
 398:   fprintf(di_log,"%u,%u,%u,%u,%u,%u,%.0f\n",o.time_ms,ib->available,ib->bad,ib->status[0],ib->status[1],ib->status[2],di_strength(state,o.time_ms));
 399: 
 400:  }
 401: 
 402:  }
 403:  fprintf(plus_meta,"%u,%u,%u,%u,%lu,%lu,%lu,%.9g,%.9g,%.9g,%.9g,%u,%u,%zu",o.time_ms,state->control.memory_diagnostic.checks,plus_memory[0].checks,plus_memory[1].checks,plus_acquisitions[0],plus_acquisitions[1],plus_acquisitions[2],sensor_cpu,memory_cpu[0],memory_cpu[1],core_cpu[0],stagger.accepted_pairs,stagger.rejected_alignment,sizeof(plus_stagger_t)+sizeof(stagger_b)+sizeof(stagger_c));
 404:  const clo_revised_t *all[6]={&triplex_detector,&plus_detector[0],&plus_detector[1],&plus_detector[2],&plus_detector[3],&plus_detector[4]};
 405:  for(unsigned j=0;j<6;j++)fprintf(plus_meta,",%u,%u",all[j]->fusion.output.alarm,all[j]->fusion.output.estimated_origin);
 406:  fprintf(plus_meta,"\n");
 407: 
 408:   fprintf(triplex_log,"%u,%.17g,%d,%d,%u,%.17g,%.17g,%d,%u,%d,%u\n",o.time_ms,triplex.strength,triplex.qualified,triplex.ambiguous,triplex.member_pattern,triplex.ac_strength,triplex.bc_strength,triplex_detector.fusion.output.alarm,triplex_detector.fusion.output.estimated_origin,detector.fusion.output.alarm,detector.fusion.output.estimated_origin);
 409:  }
 410:  if(primary){state->detection.current_score=(float)detector.fusion.output.anomaly_decision_score;state->detection.alarm_active=detector.fusion.output.alarm;state->detection.detected=detector.fusion.output.alarm_timestamp_ms>=0;state->detection.first_detection_time_ms=detector.fusion.output.alarm_timestamp_ms;snprintf(state->detection.runtime_label,sizeof(state->detection.runtime_label),"clo_dsf_revised");}
 411:  else __real_detection_algorithm_step(state);
 412: }
```

Assembly transformations: `scripts/run_digital_integrity.py` — `build`, lines 55–92; `scripts/run_benign_alarm.py` — `build`, lines 35–47; final normalization/report path `scripts/run_integrity_final_unseen.py` — `collect`, lines 88–114.


### Exact source: clo_existing_pair_strength

**VERIFIED FROM SOURCE.** `/tmp/clo-integrity-final-unseen/work/bridge.c` — `clo_existing_pair_strength`, lines 410–410

```text
 410: double clo_existing_pair_strength(clo_revised_t *s,const runtime_observation_t *o){return fmax(redundant_sensor(s,o),fast_redundant_sensor(s,o));}
```
