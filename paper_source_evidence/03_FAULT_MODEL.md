# 03 — Fault models and final residual misses

Evidence labels used throughout: **VERIFIED FROM SOURCE** (literal implemented behavior); **VERIFIED FROM EXPERIMENT ARTIFACT** (recorded outcomes/protocol); **DERIVED MATHEMATICALLY FROM VERIFIED SOURCE** (algebra or deterministic accounting, not a new experiment); **NOT RECOVERABLE / REQUIRES CONFIRMATION** (missing/limited evidence). Source paths are repository-relative unless explicitly absolute. Line numbers refer to the hashes in 07, not an assumed future HEAD.

## Five origins, actual mutation boundaries

**VERIFIED FROM SOURCE.** Fault class names describe the experimental attribution, not detector inputs.

| Origin | Actual modeled mutation | Observables / limitations |
|---|---|---|
| MEMORY | `target_register_c`: selected bit flip on activation; stuck-bit forcing through memory path read/write semantics; legal target shadow remains independent | Register/shadow, consumed target, scheduled active read/write checks. Dormant means forced bit equals the operational value; active probe may still expose it. |
| TIMING | Control job release/admission/delay/skip path; one pending delayed job, no catch-up burst; releases while pending discarded | Scheduler-owned event ledger and consumed-sample/control timing. Not an arbitrary software sleep or changed sensor period. |
| COMMUNICATION | Generated-sample delivery history: delay, drop or old sample replay with original source timestamp | Source versus consumed value/time, age/freshness and delivery cadence. Injection is after primary acquisition, not an analog sensor failure. |
| SENSOR_CONTROL | Final triplex adapter mutates A source/software consumed value, B output, C published output **after** their producer publication; mask chooses A/B/C/AB/ABC | Integrity detects post-publication changes when sampled; Triplex responds to disagreement but cannot necessarily identify member. Base legacy `sensors_step` also has separate pre-publication fault paths; do not conflate them. |
| ACTUATOR | Pump command realization multiplied by degradation scale; fan stuck-off realization forced to zero | Command/actual response contract and later measured thermal consequence. Multiplication by zero-command gives no discrepancy. |

**VERIFIED FROM SOURCE.** Cross-layer time policy is half-open: active after start; transient/intermittent stop at elapsed≥duration; permanent ignores finite recovery duration. Intermittent active when elapsed mod(on+off)<on. Bit-flip/stuck activation and memory restore/read/write rules are reproduced below. Legacy actuator fault scheduling and adapter sensor masks have their own branches—do not impose one generic continuous-time waveform on every subtype.

Delayed delivery withholds until the configured delay since activation, then uses an exact historical timestamp. Drops remove first N updates, or N within repeating P-update blocks when configured. Replay selects now−replay_age from bounded history; missing historical timestamp means no delivery. Delayed control admits one job, suppresses later releases including the completion-coincident release, and executes when the 100-ms host tick reaches the due timestamp. These event discretizations matter to reported latency.

## Sensor constructions and integrity boundary

**VERIFIED FROM SOURCE.** Adapter `inject_value` supports ramp (kind1), constant offsets/weak steps and finite pulses, held value (kind4), and diagnostic-C frozen readout (kind5). Mask bits choose channel(s). A/B evaluate mutation on the host acquisition epoch; C uses its actual published sample timestamp when newly acquired. A mutation also replaces the consumed primary value from the mutated source. A/B/AB/ABC share the configured offset but have distinct timestamps/protection records. This is post-conversion data corruption—not proof that a CRC diagnoses physical thermistor drift.

The final sampled sensor manifest uses `kind` step/pulse/ramp and domains A/B/C/AB/ABC. Weak step is the **reporting subgroup** |magnitude|<1, not a special runtime threshold. Finite short pulses can be 50 ms; they may overlap no acquisition/mutation opportunity. The final common-mode AB/ABC group has 96 cases, of which 93 detect; the three misses are already among the eight uncaptured pulses, not an additional miss category.

Legal B offsets use `di_legal` to update the producer record; legal primary timestamp-keyed noise/triangle uses the same authorized transformation boundary. The diagnostic injector does not update the witness. A pre-publication sensor error or consistent data+witness corruption need not fail DI. Failure-mode unit studies include value-only corruption, stale/replay, value+tag changes and witness corruption; inspect authentic `failure_mode_tests.csv` for the tested combinations and outcomes. These tests are not additional cases in the final unseen denominator.

## Actual parameter sets, not invented broad ranges

**VERIFIED FROM EXPERIMENT ARTIFACT.** `data/cohort_inventory.json` records each cohort's original manifest SHA-256, partitions and every scalar/configuration field's unique values (when compact), minima/maxima and unique counts. Those are **sampled configurations**, not parser-wide capability limits or field distributions. `profile_json`, domain, phase, seeds and group are part of identity; a distinct seed is not evidence of a new physical fault family. Exact exhaustive per-run values remain in the original manifest; original manifests are not silently replaced by rounded figure labels.

The primary final manifest's subtype/pattern parameter ranges follow; units are field-dependent: `magnitude` is bit index for stuck-bit, milliseconds/counts for appropriate timing/communication models, degrees C for sensor offsets, and dimensionless scale for pump degradation. Refer to command construction before interpreting a number.

| Origin / model / behavior / sensor kind | N | Magnitude min–max | Start ms min–max | Duration ms min–max |
|---|---:|---|---|---|
| ACTUATOR / fan_stuck_off / intermittent / none | 20 | 0 – 0 | 28000 – 34700 | 900 – 14900 |
| ACTUATOR / fan_stuck_off / permanent / none | 20 | 0 – 0 | 28200 – 35400 | 0 – 0 |
| ACTUATOR / fan_stuck_off / transient / none | 20 | 0 – 0 | 27300 – 34000 | 900 – 14900 |
| ACTUATOR / pump_degraded / intermittent / none | 60 | 0.619 – 0.989 | 28100 – 34800 | 900 – 14900 |
| ACTUATOR / pump_degraded / permanent / none | 60 | 0.619 – 0.989 | 27300 – 34200 | 0 – 0 |
| ACTUATOR / pump_degraded / transient / none | 60 | 0.619 – 0.989 | 27400 – 34300 | 900 – 14900 |
| COMMUNICATION / delayed_update / intermittent / none | 27 | 100 – 900 | 27800 – 34400 | 900 – 14900 |
| COMMUNICATION / delayed_update / permanent / none | 27 | 100 – 900 | 27900 – 34600 | 0 – 0 |
| COMMUNICATION / delayed_update / transient / none | 27 | 100 – 900 | 28000 – 35300 | 900 – 14900 |
| COMMUNICATION / dropped_update / intermittent / none | 27 | 1 – 5 | 27200 – 35000 | 900 – 14900 |
| COMMUNICATION / dropped_update / permanent / none | 27 | 1 – 5 | 27400 – 34500 | 0 – 0 |
| COMMUNICATION / dropped_update / transient / none | 27 | 1 – 5 | 27500 – 34900 | 900 – 14900 |
| COMMUNICATION / replayed_sample / intermittent / none | 26 | 100 – 1700 | 27600 – 34200 | 900 – 14900 |
| COMMUNICATION / replayed_sample / permanent / none | 26 | 100 – 1700 | 26700 – 34300 | 0 – 0 |
| COMMUNICATION / replayed_sample / transient / none | 26 | 100 – 1700 | 27400 – 34400 | 900 – 14900 |
| MEMORY / bit_flip / intermittent / none | 20 | 0 – 4 | 27700 – 32900 | 100 – 2300 |
| MEMORY / bit_flip / permanent / none | 20 | 0 – 4 | 27500 – 32300 | 0 – 0 |
| MEMORY / bit_flip / transient / none | 20 | 0 – 4 | 27600 – 32800 | 100 – 2300 |
| MEMORY / stuck_bit / intermittent / none | 60 | 0 – 4 | 27500 – 32700 | 100 – 2300 |
| MEMORY / stuck_bit / permanent / none | 60 | 0 – 4 | 27600 – 32800 | 0 – 0 |
| MEMORY / stuck_bit / transient / none | 60 | 0 – 4 | 27500 – 32900 | 100 – 2300 |
| SENSOR_CONTROL / sensor_bias / permanent / step | 120 | -1.12294089 – 1.12294089 | 26233 – 31333 | 0 – 0 |
| SENSOR_CONTROL / sensor_bias_ramp / permanent / ramp | 60 | -3.705704937 – 4.049798751 | 28533 – 31773 | 0 – 0 |
| SENSOR_CONTROL / sensor_interface_intermittent / transient / pulse | 60 | -0.69024807 – 0.69024807 | 27433 – 30573 | 50 – 1700 |
| TIMING / deadline_miss / intermittent / none | 40 | 0 – 0 | 28300 – 35200 | 700 – 13700 |
| TIMING / deadline_miss / permanent / none | 40 | 0 – 0 | 26900 – 34300 | 0 – 0 |
| TIMING / deadline_miss / transient / none | 40 | 0 – 0 | 27600 – 35100 | 100 – 100 |
| TIMING / task_delay / intermittent / none | 40 | 100 – 1100 | 27700 – 34500 | 900 – 14900 |
| TIMING / task_delay / permanent / none | 40 | 100 – 1100 | 28100 – 34800 | 0 – 0 |
| TIMING / task_delay / transient / none | 40 | 100 – 1100 | 27400 – 34400 | 900 – 14900 |

## Recorded final A2 miss accounting

**VERIFIED FROM EXPERIMENT ARTIFACT.** Filter authentic `integrity_final_unseen/misses.csv` to method A2: **76 distinct runs**. All have plant_manifestation=0.

| Primary attribution | Count | Recorded justification | Scope |
|---|---:|---|---|
| Unexcited pump degradation | 63 | No positive command in active intervals; 24 transient,24 intermittent,15 permanent | Structural **conditional on operating context**; future excitation could expose it |
| Uncaptured sensor pulse | 8 | All transient50-ms pulses; no integrity violation captured | Temporal/acquisition opportunity limitation |
| Dormant stuck-bit outside probes | 5 | No effective value corruption; zero active probe samples; two transient/three intermittent, four100-ms/one200-ms windows | Temporal/probing with dormant value prerequisite |
| Additional established classifier-only category | 0 | None established in these stored sufficient statistics | Not a theorem that no classifier failure is possible |
| Additional established joint-witness common failure category | 0 | Not tested by this final fault cohort | Not evidence of coverage |

Thus 63 context-structural +13 temporal. Do not call all dormant memory structurally invisible: final A2 detects 73/78 dormant cases through probing, and 162/162 effective cases. Do not delete dormant/unexcited cases to inflate raw detection. Primary per-origin outcomes: Memory235/240, Timing240/240, Communication240/240, Sensor232/240, Actuator177/240.

A runtime trace effect Γ=1 is not sufficient for reliable diagnosis: changed traces may still belong to the admissible healthy set (offset/noise/calibration/workload). DI is stronger only under the protected-producer trust assumption because it checks a deterministic value/provenance relation. The original observability specification is diagnostic fault distinguishability, not classical control-state observability. The stored miss table supports finite-cohort attribution, not pointwise equality proofs for all healthy and faulty trajectories; bulk primary traces were deliberately deleted.

## Exact source anchors


### Exact source: cross_layer_fault_step

**VERIFIED FROM SOURCE.** `src/cross_layer_fault.c` — `cross_layer_fault_step`, lines 55–103

```text
  55: void cross_layer_fault_step(ecu_state_t *state)
  56: {
  57:     const fault_descriptor_t *f = &state->cross_layer_fault;
  58:     cross_layer_fault_state_t *r = &state->cross_layer_runtime;
  59:     unsigned int now = state->time.time_ms;
  60:     bool was_active = r->active;
  61:     r->active = false;
  62:     r->phase = !f->enabled ? FAULT_PHASE_DISABLED : FAULT_PHASE_WAITING;
  63:     if (f->enabled && now >= f->start_ms) {
  64:         unsigned int elapsed = now - f->start_ms;
  65:         if (f->behavior != FAULT_BEHAVIOR_PERMANENT && elapsed >= f->duration_ms) {
  66:             r->phase = FAULT_PHASE_RECOVERED;
  67:         } else {
  68:             r->active = f->behavior != FAULT_BEHAVIOR_INTERMITTENT ||
  69:                 elapsed % (f->intermittent_on_ms + f->intermittent_off_ms) < f->intermittent_on_ms;
  70:             r->phase = r->active ? FAULT_PHASE_ACTIVE : FAULT_PHASE_INACTIVE;
  71:         }
  72:     }
  73:     if (r->active && !was_active) {
  74:         r->activation_count++;
  75:         r->last_activation_ms = (int)now;
  76:         r->active_update_count = 0;
  77:         if (!r->injected) {
  78:             r->injected = true;
  79:             state->propagation.injection_ms = (int)now;
  80:         }
  81:         if (f->layer == FAULT_LAYER_MEMORY) {
  82:             r->memory_original_value = state->control.target_register_c;
  83:             r->memory_values_valid = true;
  84:             if (f->model == FAULT_MODEL_BIT_FLIP) {
  85:                 state->control.target_register_c ^= (uint16_t)(1U << f->bit_index);
  86:             }
  87:         }
  88:     }
  89:     if (was_active && !r->active) {
  90:         r->last_recovery_ms = (int)now;
  91:         if (r->memory_values_valid) state->control.target_register_c = r->memory_original_value;
  92:     }
  93:     if (r->active && f->layer == FAULT_LAYER_MEMORY) {
  94:         if (f->model == FAULT_MODEL_STUCK_BIT) {
  95:             uint16_t mask = (uint16_t)(1U << f->bit_index);
  96:             state->control.target_register_c = f->stuck_polarity ?
  97:                 state->control.target_register_c | mask : state->control.target_register_c & (uint16_t)~mask;
  98:         }
  99:         r->memory_corrupted_value = state->control.target_register_c;
 100:         if (r->memory_corrupted_value != r->memory_original_value && state->propagation.internal_ms < 0)
 101:             state->propagation.internal_ms = (int)now;
 102:     }
 103: }
```


### Exact source: cross_layer_control_execution

**VERIFIED FROM SOURCE.** `src/cross_layer_fault.c` — `cross_layer_control_execution`, lines 105–156

```text
 105: bool cross_layer_control_execution(ecu_state_t *state)
 106: {
 107:     const fault_descriptor_t *f = &state->cross_layer_fault;
 108:     cross_layer_fault_state_t *r = &state->cross_layer_runtime;
 109:     int now = (int)state->time.time_ms;
 110:     bool execute = true;
 111:     runtime_timing_release(&state->timing_recorder, state->time.time_ms);
 112:     r->execution_skipped = r->execution_recovered = r->deadline_missed = r->release_discarded = false;
 113:     r->expected_execution_ms = now;
 114:     r->actual_execution_ms = now;
 115:     r->actual_delay_ms = 0;
 116:     if (f->enabled && f->model == FAULT_MODEL_TASK_DELAY) {
 117:         if (r->pending_job) {
 118:             runtime_timing_cancel_release(&state->timing_recorder, false);
 119:             /* Single outstanding job: discard releases while pending, including
 120:              * the release coincident with delayed completion. No catch-up burst. */
 121:             r->release_discarded = true;
 122:             execute = now >= r->job_due_ms;
 123:             if (execute) {
 124:                 r->pending_job = false;
 125:                 r->actual_delay_ms = (unsigned int)(now - r->nominal_release_ms);
 126:                 r->deadline_missed = now > r->deadline_ms;
 127:             } else r->deadline_missed = now >= r->deadline_ms;
 128:         } else {
 129:             runtime_timing_admit(&state->timing_recorder);
 130:             r->nominal_release_ms = now;
 131:             r->deadline_ms = now + (int)ECU_CONTROL_PERIOD_MS;
 132:             if (r->active) {
 133:                 r->pending_job = true;
 134:                 r->job_due_ms = now + (int)f->task_delay_ms;
 135:                 execute = false;
 136:             }
 137:         }
 138:     } else {
 139:         runtime_timing_admit(&state->timing_recorder);
 140:         r->nominal_release_ms = now;
 141:         r->deadline_ms = now + (int)ECU_CONTROL_PERIOD_MS;
 142:         if (r->active && f->model == FAULT_MODEL_DEADLINE_MISS) {
 143:             execute = false;
 144:             runtime_timing_cancel_release(&state->timing_recorder, true);
 145:             r->deadline_missed = true;
 146:         }
 147:     }
 148:     r->execution_skipped = !execute;
 149:     if (!execute) {
 150:         r->actual_execution_ms = -1;
 151:         if (state->propagation.internal_ms < 0) state->propagation.internal_ms = now;
 152:     }
 153:     r->execution_recovered = r->previous_execution_skipped && execute;
 154:     r->previous_execution_skipped = !execute;
 155:     return execute;
 156: }
```


### Exact source: memory_diagnostic_backend.c

**VERIFIED FROM SOURCE.** `src/memory_diagnostic_backend.c` — `file`, lines 1–26

```text
   1: /* Virtual storage model for diagnostic transactions, outside inference. */
   2: #include "memory_diagnostic_backend.h"
   3: #include "ecu_types.h"
   4: 
   5: uint16_t cross_layer_memory_read(void *context)
   6: {
   7:     const ecu_state_t *state = context;
   8:     return state->control.target_register_c;
   9: }
  10: 
  11: void cross_layer_memory_write(void *context, uint16_t value)
  12: {
  13:     ecu_state_t *state = context;
  14:     /* Device model only: an active stuck cell rejects the opposite write.
  15:      * Normal control writes and historical scheduled injection are unchanged.
  16:      * A past bit-flip is not a persistent inability to write. */
  17:     if (state->cross_layer_fault.enabled && state->cross_layer_runtime.active &&
  18:         state->cross_layer_fault.layer == FAULT_LAYER_MEMORY &&
  19:         state->cross_layer_fault.model == FAULT_MODEL_STUCK_BIT) {
  20:         uint16_t mask = (uint16_t)(1U << state->cross_layer_fault.bit_index);
  21:         value = state->cross_layer_fault.stuck_polarity ?
  22:             value | mask : value & (uint16_t)~mask;
  23:     }
  24:     state->control.target_register_c = value;
  25: }
  26: 
```


### Exact source: sensor_delivery.c

**VERIFIED FROM SOURCE.** `src/sensor_delivery.c` — `file`, lines 1–59

```text
   1: #include "cross_layer_fault.h"
   2: 
   3: /* Bounded generated-sample history. Timestamps identify real sample provenance;
   4:  * they are never read by a detector except through published acquisition age. */
   5: void cross_layer_sensor_delivery(ecu_state_t *state, float generated, float *delivered,
   6:     bool *refreshed, unsigned int *source_ms)
   7: {
   8:     const fault_descriptor_t *f = &state->cross_layer_fault;
   9:     cross_layer_fault_state_t *r = &state->cross_layer_runtime;
  10:     unsigned int now = state->time.time_ms;
  11:     unsigned int slot = (now / ECU_SENSOR_PERIOD_MS) % CROSS_LAYER_HISTORY_SAMPLES;
  12:     if (!f->enabled || f->layer != FAULT_LAYER_COMMUNICATION) return;
  13:     r->history[slot] = generated;
  14:     r->history_timestamps[slot] = now;
  15:     r->history_valid[slot] = true;
  16:     r->generated_value = generated; r->generated_ms = now;
  17:     r->update_generated = true; r->update_delivered = true;
  18:     r->update_dropped = r->update_delayed = r->replay_active = false;
  19:     r->replay_source_ms = -1;
  20:     unsigned int sample_time = now;
  21:     if (r->active) {
  22:         r->active_update_count++;
  23:         if (f->model == FAULT_MODEL_DELAYED_UPDATE) {
  24:             r->update_delayed = true;
  25:             if (now-(unsigned int)r->last_activation_ms < f->communication_delay_ms)
  26:                 r->update_delivered = false;
  27:             else sample_time = now-f->communication_delay_ms;
  28:         } else if (f->model == FAULT_MODEL_DROPPED_UPDATE) {
  29:             /* No pattern: drop the first N in each active window. With pattern P:
  30:              * repeat a burst of N dropped samples followed by P-N deliveries. */
  31:             unsigned int index = r->active_update_count-1U;
  32:             bool drop = f->drop_every_n_updates ?
  33:                 index % f->drop_every_n_updates < f->drop_count : index < f->drop_count;
  34:             r->update_dropped = drop;
  35:             r->update_delivered = !drop;
  36:             if (drop) { r->consecutive_drops++; r->total_drops++; }
  37:         } else if (f->model == FAULT_MODEL_REPLAYED_SAMPLE) {
  38:             sample_time = now-f->replay_age_ms;
  39:             r->replay_source_ms = (int)sample_time;
  40:             r->replay_active = true;
  41:         }
  42:     }
  43:     if (r->update_delivered) {
  44:         unsigned int source_slot = (sample_time / ECU_SENSOR_PERIOD_MS) % CROSS_LAYER_HISTORY_SAMPLES;
  45:         /* Configuration validation and exact tick history guarantee availability. */
  46:         if (r->history_valid[source_slot] && r->history_timestamps[source_slot] == sample_time) {
  47:             r->delivered_value = r->history[source_slot];
  48:             r->delivered_source_ms = sample_time;
  49:             r->delivered_ms = (int)now;
  50:             r->consecutive_drops = 0;
  51:         } else r->update_delivered = false;
  52:     }
  53:     *delivered = r->delivered_value;
  54:     *refreshed = r->update_delivered;
  55:     *source_ms = r->delivered_source_ms;
  56:     if (r->active && state->propagation.internal_ms < 0 &&
  57:         (!r->update_delivered || r->delivered_source_ms != now || r->delivered_value != generated))
  58:         state->propagation.internal_ms = (int)now;
  59: }
```


### Exact source: inject_value

**VERIFIED FROM SOURCE.** `/tmp/clo-integrity-final-unseen/work/adapter.c` — `inject_value`, lines 31–35

```text
  31: static void inject_value(float *value,unsigned member,unsigned now){
  32:  if(!(injection_mask&(1U<<member))||now<injection_start||(injection_duration&&now>=injection_start+injection_duration))return;
  33:  if(injection_kind==4){if(!held[member]){held[member]=true;held_value[member]=*value;}*value=held_value[member];}
  34:  else if(injection_kind!=5)*value+=(float)(injection_magnitude*(injection_kind==1?fmin(1.,(double)(now-injection_start)/injection_rise):1));
  35: }
```


### Exact source: diagnostic_acquire

**VERIFIED FROM SOURCE.** `/tmp/clo-integrity-final-unseen/work/adapter.c` — `diagnostic_acquire`, lines 36–46

```text
  36: static void diagnostic_acquire(ecu_state_t *state){
  37:  if(!state->log_file)return;
  38:  bool acquired=diagnostic_temperature_sample(&diagnostic_c,state->time.time_ms,state->plant.coolant_temp_true_c);
  39:  unsigned now=state->time.time_ms;
  40:  if(acquired)inject_value(&diagnostic_c.output.value_c,2,diagnostic_c.output.sample_ms);
  41:  if(injection_kind==5 && (injection_mask&4) && now>=injection_start && (!injection_duration||now<injection_start+injection_duration)){
  42:   if(!held[2]){frozen_c=diagnostic_c.output;held[2]=true;}diagnostic_c.output=frozen_c;
  43:  }
  44:  if(injection_mask&1){inject_value(&state->sensors.coolant_source_c,0,now);state->sensors.coolant_temp_meas_c=state->sensors.coolant_source_c;}
  45:  inject_value(&state->temperature_reference.value_c,1,now);
  46: }
```


### Exact source: reference_acquire

**VERIFIED FROM SOURCE.** `/tmp/clo-integrity-final-unseen/work/adapter.c` — `reference_acquire`, lines 224–239

```text
 224: static void reference_acquire(ecu_state_t *state)
 225: {
 226:  if(!reference_enabled)return;
 227:  redundant_temperature_t *r=&state->temperature_reference;
 228:  if(!r->initialized)redundant_temperature_init(r,reference_seed,reference_offset,reference_noise);
 229:  redundant_temperature_sample(r,state->time.time_ms,state->plant.coolant_temp_true_c);
 230:  if(!state->log_file || !reference_fault_kind || state->time.time_ms<reference_fault_start)return;
 231:  unsigned int age=state->time.time_ms-reference_fault_start;
 232:  if(reference_fault_duration && age>=reference_fault_duration)return;
 233:  if(reference_fault_period && age%reference_fault_period>=reference_fault_period/2)return;
 234:  if(reference_fault_kind==3){r->valid=false;r->failed=true;return;}
 235:  float amount=reference_fault_magnitude;
 236:  if(reference_fault_kind==1)amount*=fminf(1,(float)age/reference_fault_rise);
 237:  if(reference_fault_kind==4){unsigned int phase=(state->time.time_ms/100)%6;amount*=phase==0||phase==3?1:phase==1||phase==4?-.5f:0;}
 238:  r->value_c+=amount;di_legal(1,amount);
 239: }
```


### Exact source: __wrap_sensors_step

**VERIFIED FROM SOURCE.** `/tmp/clo-integrity-final-unseen/work/adapter.c` — `__wrap_sensors_step`, lines 252–270

```text
 252: void __wrap_sensors_step(ecu_state_t *state)
 253: {
 254:  di_producer=di_bank(state);
 255:  __real_sensors_step(state);
 256:  di_source(state);
 257:  reference_acquire(state);
 258:  diagnostic_acquire(state);
 259:  if(sensor_ramp_rise && state->log_file && state->time.time_ms>=sensor_ramp_start) {
 260:   double elapsed=state->time.time_ms-sensor_ramp_start;
 261:   float offset=(float)(sensor_ramp_offset*fmin(1.0,elapsed/sensor_ramp_rise));
 262:   state->sensors.coolant_source_c+=offset;
 263:   state->sensors.coolant_temp_meas_c+=offset;
 264:  }
 265:  if(sensor_jitter==0 && sensor_drift==0){di_finish(state);return;}
 266:  state->sensors.coolant_source_c+=sensor_variation(state->sensors.coolant_source_ms);
 267:  di_legal(0,sensor_variation(state->sensors.coolant_source_ms));
 268:  state->sensors.coolant_temp_meas_c+=sensor_variation(state->sensors.coolant_sensor_last_update_ms);
 269:  di_finish(state);
 270: }
```


### Exact source: actuators_step

**VERIFIED FROM SOURCE.** `src/actuators.c` — `actuators_step`, lines 83–117

```text
  83: void actuators_step(ecu_state_t *state)
  84: {
  85:     float pump_actual = clamp_unit(state->control.pump_command);
  86:     float fan_actual = clamp_unit(state->control.fan_command);
  87: 
  88:     /* Fault injection modifies actuator authority after the control decision. */
  89:     if (state->faults.enabled && state->faults.active_mode == FAULT_PUMP_DEGRADED) {
  90:         pump_actual *= state->faults.pump_scale;
  91:     }
  92: 
  93:     if (state->faults.enabled && state->faults.active_mode == FAULT_FAN_STUCK_OFF) {
  94:         fan_actual = 0.0f;
  95:     }
  96: 
  97:     /* Explicit trace replay is an opt-in actuator-interface source for RTL
  98:      * security studies. Ordinary control and fault workflows never enter this
  99:      * branch. */
 100:     if (state->fan_actual_trace.enabled &&
 101:         fan_actual_trace_get(
 102:             state,
 103:             state->time.time_ms,
 104:             &fan_actual
 105:         ) != 0) {
 106:         fprintf(
 107:             stderr,
 108:             "Fan actual trace has no sample for %u ms.\n",
 109:             state->time.time_ms
 110:         );
 111:         fan_actual = clamp_unit(state->control.fan_command);
 112:     }
 113: 
 114:     state->actuators.pump_actual = pump_actual;
 115:     state->actuators.fan_actual = fan_actual;
 116:     update_fan_actuator_feedback(state, state->control.fan_command, fan_actual);
 117: }
```

Conceptual relation/matrix (existing evidence, not new results): `docs/cross_layer_observability_model.md` — `file`, lines 1–193.
