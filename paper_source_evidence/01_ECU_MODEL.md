# 01 — Exact frozen virtual ECU model

Evidence labels used throughout: **VERIFIED FROM SOURCE** (literal implemented behavior); **VERIFIED FROM EXPERIMENT ARTIFACT** (recorded outcomes/protocol); **DERIVED MATHEMATICALLY FROM VERIFIED SOURCE** (algebra or deterministic accounting, not a new experiment); **NOT RECOVERABLE / REQUIRES CONFIRMATION** (missing/limited evidence). Source paths are repository-relative unless explicitly absolute. Line numbers refer to the hashes in 07, not an assumed future HEAD.

## Discrete model, not an invented physical ODE

**DERIVED MATHEMATICALLY FROM VERIFIED SOURCE.** Let \([x]_a^b=\min(b,\max(a,x))\). The model is an explicit discrete update with \(\Delta t=0.1\) s, single-precision C arithmetic. Its coefficients are simulator temperature-rate gains; there is no implemented coolant mass, heat capacity, radiator capacitance, engine thermodynamic model or calibrated SI heat-flow network.

For selected profile ambient \(A_p\), load \(L_p\), speed \(v_p\), road grade \(g\), extra airflow \(a\), experiment offsets/scales \(\delta_A,s_L,b_H,s_R\), and safety load scale \(s_S\):
\[
 A=A_p+\delta_A,\quad L=s_S\max(0,L_p s_L+0.01g),
\]
where the grade term and clipping to \([0,1.20]\) before the nonnegative clamp apply **only to custom driving profiles**; default profiles use \(s_S\max(0,L_p s_L)\). Shutdown multiplies profile speed by 0.25 and engine RPM by 0.60.
\[
 H=2.2+9.5L+2\,\mathbf1_{\mathrm{hot\ idle}}+b_H,\quad
 C_p=7.5u_p,\quad C_f=6u_f,
\]
\[
 C_v=(v/40)s_R+3a\,\mathbf1_{\mathrm{custom\ profile}},\quad
 C_A=0.08(T-A),
\]
\[
 T_{k+1}=\max\{0,T_k+0.1(H-C_p-C_f-C_v-C_A)\},
\quad R_{k+1}=A+(T_{k+1}-A)(0.55-0.15u_f).
\]
The radiator is algebraically assigned after the coolant update, **not a second integrated thermal node**. Default initialization: coolant 88 °C, radiator 78 °C, ambient 25 °C, load .35, speed 35 km/h, RPM 1500, grade/extra airflow zero.

Default profile boundaries (seconds): [0,20), [20,60), [60,90), [90,end], with (load,speed,RPM,ambient) respectively (.35,35,1500,25), (.72,85,2800,28), (.82,15,2200,31), (.98,0,2100,35). Frozen campaigns generally override these with their manifest `profile_json`; do not use the default table as the actual experimental workload. For custom profiles, speed ≥70 labels highway/RPM2800, speed >1 labels urban/RPM2200, otherwise hot-idle/RPM2100. This phase classification matters to the extra heat term.

## Control, actuation and order

**DERIVED MATHEMATICALLY FROM VERIFIED SOURCE.** With consumed sensor value \(y\) and effective stored target \(T_*\),
\[
 e=y-T_*,\quad p=[0.30+0.025e+0.35L]_0^1,
\quad f=[0.25+0.065e-0.10(v/200)]_0^1.
\]
Nominal target 92 °C; authorized `control_commit_target` writes both register and shadow. Initial command and realization are pump .25 and fan 0. Pump degradation realizes \(u_p=\gamma[p]_0^1\); fan-stuck-off realizes \(u_f=0\); otherwise realizations are clamped commands. No pump inertia or hydraulic dynamics are implemented. Generic control-target override and RTL trace paths exist but are not interchangeable with the selected memory injection.

**VERIFIED FROM SOURCE.** Scheduler order: fault/authorized-update/probe work → sensor acquisition/delivery → timing-gated control → actuator update → legacy diagnostics → legacy safety/reapplication → detector → conditional detector/runtime-safety reactions → reporting → plant update. Observation at time t sees the plant state produced by the preceding integration step. Main simulation covers 0 through duration inclusive in 100-ms ticks; 120,000 ms yields 1,201 reporting frames. Sensor/control/actuator/safety/log periods are 100 ms; legacy diagnostics 500 ms. Frozen comparison is observe-only, not a demonstration of closed-loop mitigation by the proposed alarm.

## Actual sensor chains

**DERIVED MATHEMATICALLY FROM VERIFIED SOURCE.** Primary A starts as the plant coolant value; base legacy front-end bias/intermittence is applied before its trusted source tap. There is **no universal primary ADC quantizer in `sensors_step`**. The selected triplex campaign applies its A/B/C mutation after the producer call (see 03); source comments calling all sensor errors “front-end” must not override this call ordering.

Reference B uses xorshift32 (xor shifts 13 left,17 right,5 left), then
\(n_B=N_B(2(x\mathbin{\&}65535)/65535-1)\),
\(y_B=\mathrm{round}_{\mathrm{away}}[100(T+o_B+n_B)]/100\)
for finite values between −100000 and 100000; otherwise returns the unquantized exceptional value. Seed zero becomes one. Offset/noise/seeds are manifest fields.

Independent C has period P and fixed phase φ, next due timestamp initially φ. At each host tick it processes all due timestamps \(t_s\le t\), using bounded linear interpolation between previous/current physical simulator samples:
\[
 w=[(t_s-t_{prev})/(t-t_{prev})]_0^1,\quad T_s=T_{prev}+w(T-T_{prev}),
\quad z\leftarrow z+\alpha(T_s-z),
\]
\(\alpha=1-e^{-P/\ell}\) if lag \(\ell>0\), otherwise 1 (P and lag both in ms).
\[
 y_C=Q\,\mathrm{round}\left(((1+g_C)z+o_C+n_C)(1+r_C)/Q\right).
\]
C uses its own xorshift state and bounded uniform sample formula. It is independent at the sensor-model interface, not an electrically demonstrated independence claim. Initialization sets prior physical and lag state from the first supplied physical value. Zero period/nonpositive quantum/nonfinite physical input marks failed/unavailable. These functions alone consume physical temperature; detector inputs are only published readouts.

Benign primary variation is a timestamp-keyed triangle plus alternating term: \(p=(t\bmod P_v)/P_v\); triangle is 4p for p<.25, 2−4p for .25≤p<.75, and 4p−4 otherwise; variation is \(d\,triangle+j(-1)^{\lfloor t/100\rfloor+1}\). Legitimate variation updates the protected witness via `di_legal`. It is not random scheduler jitter. Exact per-case Q, noise, gains, offsets, phase, profiles and authorized updates are indexed in `data/cohort_inventory.json`; exhaustive values remain in original hashed manifests.

## Runtime plant-related observable versus offline propagation

**VERIFIED FROM SOURCE.** Runtime high-temperature evidence is \([(y-108)/(115-108)]_0^1\), based on measured coolant. Command/actual contract evidence and engine-load/speed/ambient inputs are runtime observations. The counterfactual true-temperature difference is **offline evaluation only**, not a provider. Warning/critical/shutdown constants are 108/115/118 °C; sensor plausibility bounds −40/150 °C. See 04 for the 0.01 °C offline manifestation threshold.

## Equation-to-code and exact update excerpts


### Exact source: config.h

**VERIFIED FROM SOURCE.** `include/config.h` — `file`, lines 1–46

```text
   1: #ifndef CONFIG_H
   2: #define CONFIG_H
   3: 
   4: #define ECU_DT_MS 100U
   5: #define ECU_SIM_DURATION_MS 120000U
   6: #define ECU_MIN_SIM_DURATION_MS 1000U
   7: #define ECU_MAX_SIM_DURATION_MS 3600000U
   8: 
   9: #define ECU_SENSOR_PERIOD_MS 100U
  10: #define ECU_COOLANT_SENSOR_FRESHNESS_STALE_MS (3U * ECU_SENSOR_PERIOD_MS)
  11: #define ECU_CONTROL_PERIOD_MS 100U
  12: #define ECU_ACTUATOR_PERIOD_MS 100U
  13: #define ECU_FAN_ACTUATOR_COMMAND_ACTIVE_MIN 0.05f
  14: #define ECU_FAN_ACTUATOR_RESPONSE_GAP 0.20f
  15: #define ECU_FAN_ACTUATOR_HEALTH_FAULT_SCORE 1.00f
  16: #define ECU_DIAGNOSTIC_PERIOD_MS 500U
  17: #define ECU_SAFETY_PERIOD_MS 100U
  18: #define ECU_LOG_PERIOD_MS 100U
  19: 
  20: #define ECU_MAX_FAULT_EVENTS 4U
  21: #define ECU_MAX_DRIVING_PROFILE_SEGMENTS 16U
  22: #define ECU_PATH_BUFFER_SIZE 512U
  23: 
  24: #define ECU_DEFAULT_LOG_PATH "logs/thermal_run.csv"
  25: 
  26: #define ECU_TARGET_COOLANT_TEMP_C 92.0f
  27: #define ECU_CONTROL_TARGET_MIN_C 60.0f
  28: #define ECU_CONTROL_TARGET_MAX_C 130.0f
  29: #define ECU_WARN_COOLANT_TEMP_C 108.0f
  30: #define ECU_CRITICAL_COOLANT_TEMP_C 115.0f
  31: #define ECU_SHUTDOWN_COOLANT_TEMP_C 118.0f
  32: #define ECU_SENSOR_IMPLAUSIBLE_LOW_C -40.0f
  33: #define ECU_SENSOR_IMPLAUSIBLE_HIGH_C 150.0f
  34: #define ECU_SENSOR_RATIONALITY_RESIDUAL_C 4.0f
  35: 
  36: #define ECU_DTC_CONFIRM_COUNT 2U
  37: #define ECU_DTC_PERMANENT_COUNT 5U
  38: #define ECU_DTC_CLEAR_COUNT 4U
  39: 
  40: #define ECU_SAFE_STATE_RECOVERY_COUNT 20U
  41: 
  42: #define ECU_PRECAUTIONARY_LOAD_SCALE 1.00f
  43: #define ECU_LIMP_HOME_LOAD_SCALE 0.70f
  44: #define ECU_CONTROLLED_SHUTDOWN_LOAD_SCALE 0.25f
  45: 
  46: #endif
```


### Exact source: thermal_plant_init

**VERIFIED FROM SOURCE.** `src/thermal_plant.c` — `thermal_plant_init`, lines 50–61

```text
  50: void thermal_plant_init(ecu_state_t *state)
  51: {
  52:     state->plant.scenario_phase = SCENARIO_PHASE_WARMUP;
  53:     state->plant.ambient_temp_c = 25.0f;
  54:     state->plant.engine_load = 0.35f;
  55:     state->plant.engine_speed_rpm = 1500.0f;
  56:     state->plant.vehicle_speed_kph = 35.0f;
  57:     state->plant.external_airflow_factor = 0.0f;
  58:     state->plant.road_slope_percent = 0.0f;
  59:     state->plant.coolant_temp_true_c = 88.0f;
  60:     state->plant.radiator_temp_true_c = 78.0f;
  61: }
```


### Exact source: thermal_plant_step

**VERIFIED FROM SOURCE.** `src/thermal_plant.c` — `thermal_plant_step`, lines 142–205

```text
 142: void thermal_plant_step(ecu_state_t *state)
 143: {
 144:     float time_s = (float)state->time.time_ms / 1000.0f;
 145:     float dt_s = (float)ECU_DT_MS / 1000.0f;
 146:     float heat_generation;
 147:     float pump_cooling;
 148:     float fan_cooling;
 149:     float ram_air_cooling;
 150:     float ambient_coupling;
 151:     float temp_delta;
 152: 
 153:     if (state->driving_profile.enabled) {
 154:         apply_custom_driving_profile(state);
 155:     } else {
 156:         apply_default_thermal_phases(state, time_s);
 157:     }
 158: 
 159:     state->plant.ambient_temp_c += state->experiment.ambient_offset_c;
 160:     state->plant.engine_load *= state->experiment.engine_load_scale;
 161:     if (state->driving_profile.enabled) {
 162:         /* Simplified research-only road grade effect: positive grade adds
 163:          * effective load, negative grade subtracts it. This is not a calibrated
 164:          * production vehicle model. */
 165:         state->plant.engine_load += 0.01f * state->plant.road_slope_percent;
 166:         state->plant.engine_load = clamp_range(state->plant.engine_load, 0.0f, 1.20f);
 167:     }
 168:     state->plant.engine_load = clamp_min(state->plant.engine_load, 0.0f);
 169: 
 170:     /* The safety monitor limits the effective engine load rather than altering
 171:      * the scenario definition itself, which keeps the experiment design clear. */
 172:     state->plant.engine_load *= state->safety.load_limit_scale;
 173: 
 174:     if (state->safety.shutdown_requested) {
 175:         state->plant.vehicle_speed_kph *= 0.25f;
 176:         state->plant.engine_speed_rpm *= 0.60f;
 177:     }
 178: 
 179:     heat_generation = 2.2f + (9.5f * state->plant.engine_load);
 180: 
 181:     if (state->plant.scenario_phase == SCENARIO_PHASE_HOT_IDLE) {
 182:         heat_generation += 2.0f;
 183:     }
 184: 
 185:     heat_generation += state->experiment.heat_generation_bias;
 186: 
 187:     pump_cooling = 7.5f * state->actuators.pump_actual;
 188:     fan_cooling = 6.0f * state->actuators.fan_actual;
 189:     ram_air_cooling = (state->plant.vehicle_speed_kph / 40.0f) * state->experiment.ram_air_scale;
 190:     if (state->driving_profile.enabled) {
 191:         /* external_airflow_factor is a controllable extra-cooling knob for the
 192:          * virtual ECU study, not a real aerodynamic wind model. */
 193:         ram_air_cooling += 3.0f * state->plant.external_airflow_factor;
 194:     }
 195:     ambient_coupling = 0.08f * (state->plant.coolant_temp_true_c - state->plant.ambient_temp_c);
 196: 
 197:     temp_delta = heat_generation - pump_cooling - fan_cooling - ram_air_cooling - ambient_coupling;
 198:     state->plant.coolant_temp_true_c += temp_delta * dt_s;
 199:     state->plant.coolant_temp_true_c = clamp_nonnegative(state->plant.coolant_temp_true_c);
 200: 
 201:     state->plant.radiator_temp_true_c =
 202:         state->plant.ambient_temp_c +
 203:         (state->plant.coolant_temp_true_c - state->plant.ambient_temp_c) *
 204:         (0.55f - (0.15f * state->actuators.fan_actual));
 205: }
```


### Exact source: control_step

**VERIFIED FROM SOURCE.** `src/control.c` — `control_step`, lines 41–78

```text
  41: void control_step(ecu_state_t *state)
  42: {
  43:     float effective_target_c = (float)state->control.target_register_c;
  44:     float temp_error;
  45:     float load_term = 0.35f * state->plant.engine_load;
  46:     float speed_term = state->plant.vehicle_speed_kph / 200.0f;
  47: 
  48:     state->control.last_execution_ms = (int)state->time.time_ms;
  49: 
  50:     /* Calibration-memory corruption is modeled as a corrupted coolant-control
  51:      * target stored in memory/register space, which delays cooling demand. */
  52:     if (state->faults.enabled && state->faults.active_mode == FAULT_CALIBRATION_MEMORY_CORRUPTION) {
  53:         effective_target_c += state->faults.control_target_offset_c;
  54:     }
  55: 
  56:     /* An explicitly supplied RTL replay trace replaces only the stored
  57:      * control-target value. The trace is validated for complete, ordered
  58:      * control-period coverage before the scheduler starts. */
  59:     if (state->calibration_trace.enabled) {
  60:         (void)calibration_trace_get(
  61:             state,
  62:             state->time.time_ms,
  63:             &effective_target_c
  64:         );
  65:     }
  66: 
  67:     state->control.nominal_control_target_c = ECU_TARGET_COOLANT_TEMP_C;
  68:     state->control.active_control_target_c = effective_target_c;
  69:     state->control.control_target_deviation_c =
  70:         effective_target_c - ECU_TARGET_COOLANT_TEMP_C;
  71: 
  72:     temp_error = state->sensors.coolant_temp_meas_c - effective_target_c;
  73: 
  74:     /* The pump tracks bulk thermal load, while the fan reacts more strongly to
  75:      * local temperature error and is reduced slightly by ram-air cooling. */
  76:     state->control.pump_command = clamp_unit(0.30f + (0.025f * temp_error) + load_term);
  77:     state->control.fan_command = clamp_unit(0.25f + (0.065f * temp_error) - (0.10f * speed_term));
  78: }
```


### Exact source: scheduler_run

**VERIFIED FROM SOURCE.** `src/scheduler.c` — `scheduler_run`, lines 126–175

```text
 126: void scheduler_run(ecu_state_t *state)
 127: {
 128:     unsigned int duration_ms = state->simulation.duration_ms;
 129:     bool monitored = state->propagation.enabled;
 130:     ecu_state_t reference;
 131:     if (duration_ms == 0U) duration_ms = ECU_SIM_DURATION_MS;
 132:     /* The reference is local experiment instrumentation. It is never attached
 133:      * to the ECU state or passed into diagnostics, detectors, or safety. */
 134:     if (monitored) {
 135:         reference = *state;
 136:         reference.experiment.event_count = 0U;
 137:         reference.cross_layer_fault.enabled = false;
 138:         reference.propagation.enabled = false;
 139:         reference.log_file = NULL;
 140:         reference.scheduler_stress_config.overload = false;
 141:         reference.scheduler_stress_config.events_path[0] = '\0';
 142:         scheduler_init(&reference);
 143:     }
 144:     for (state->time.time_ms = 0U;
 145:          state->time.time_ms <= duration_ms;
 146:          state->time.time_ms += ECU_DT_MS, state->time.tick++) {
 147:         if (monitored) {
 148:             reference.time = state->time;
 149:             scheduler_inputs(&reference);
 150:         }
 151:         scheduler_inputs(state);
 152:         if (monitored) {
 153:             propagation_monitor_control(state, &reference);
 154:             scheduler_reactions(&reference);
 155:         }
 156:         scheduler_reactions(state);
 157:         if (monitored) {
 158:             propagation_monitor_step(state, &reference);
 159:             if (state->hazard_config.enabled) {
 160:                 runtime_observation_t observation;
 161:                 experiment_ground_truth_t truth;
 162:                 runtime_observation_capture(state, &observation);
 163:                 experiment_ground_truth_capture(state, &reference, &truth);
 164:                 hazard_model_step(&state->hazard_config, &state->hazard, &observation, &truth);
 165:             }
 166:         }
 167:         if (scheduler_task_due(state->time.time_ms, ECU_LOG_PERIOD_MS)) {
 168:             logger_write(state);
 169:         }
 170:         thermal_plant_step(state);
 171:         if (monitored) thermal_plant_step(&reference);
 172:     }
 173:     scheduler_stress_close(state);
 174:     if (monitored) scheduler_stress_close(&reference);
 175: }
```


### Exact source: redundant_temperature_sample

**VERIFIED FROM SOURCE.** `src/redundant_temperature.c` — `redundant_temperature_sample`, lines 11–22

```text
  11: void redundant_temperature_sample(redundant_temperature_t *s,unsigned int now,
  12:                                   float physical_c)
  13: {
  14:     if(!s->initialized || (s->valid && now<=s->sample_ms))return;
  15:     uint32_t x=s->random_state;
  16:     x^=x<<13;x^=x>>17;x^=x<<5;s->random_state=x;
  17:     float noise=s->noise_c*(2.0f*(float)(x&65535U)/65535.0f-1.0f);
  18:     float measured=physical_c+s->offset_c+noise;
  19:     s->value_c=isfinite(measured) && measured>-100000 && measured<100000 ?
  20:         (float)(int)(measured*100.0f+(measured>=0?.5f:-.5f))/100.0f : measured;
  21:     s->sample_ms=now;s->valid=isfinite(s->value_c);s->failed=!s->valid;
  22: }
```


### Exact source: diagnostic_temperature_sample

**VERIFIED FROM SOURCE.** `src/v7_3/diagnostic_temperature.c` — `diagnostic_temperature_sample`, lines 7–27

```text
   7: bool diagnostic_temperature_sample(diagnostic_temperature_t *s,unsigned now,float physical)
   8: {
   9:  if(!s->period_ms || !(s->quantum>0) || !isfinite(physical)){s->output.failed=true;s->output.valid=false;return false;}
  10:  if(!s->initialized){s->previous_physical=physical;s->thermal_state=physical;s->last_physical_ms=now;s->initialized=true;}
  11:  bool acquired=false;
  12:  while(s->next_ms<=now){
  13:   unsigned t=s->next_ms;s->next_ms+=s->period_ms;
  14:   double w=now>s->last_physical_ms?((double)t-s->last_physical_ms)/(now-s->last_physical_ms):1;
  15:   if(w<0)w=0;
  16:   if(w>1)w=1;
  17:   double at_sample=s->previous_physical+w*(physical-s->previous_physical);
  18:   double alpha=s->lag_ms>0?1-exp(-(double)s->period_ms/s->lag_ms):1;
  19:   s->thermal_state+=alpha*(at_sample-s->thermal_state);
  20:   uint32_t x=s->random_state;x^=x<<13;x^=x>>17;x^=x<<5;s->random_state=x;
  21:   double noise=s->noise*(2.*(x&65535U)/65535.-1);
  22:   double measured=((1+s->gain)*s->thermal_state+s->offset+noise)*(1+s->adc_reference_gain);
  23:   s->output.previous_c=s->output.value_c;s->output.previous_ms=s->output.sample_ms;s->output.previous_valid=s->output.valid;
  24:   s->output.value_c=(float)(round(measured/s->quantum)*s->quantum);s->output.sample_ms=t;s->output.valid=isfinite(measured);s->output.failed=!s->output.valid;acquired=true;
  25:  }
  26:  s->previous_physical=physical;s->last_physical_ms=now;return acquired;
  27: }
```

Other exact source references: `src/actuators.c` — `actuators_step`, lines 83–117; `src/sensors.c` — `sensors_step`, lines 61–137; `src/experiment.c` — `file`, lines 1–669.


### Exact source: scheduler_inputs

**VERIFIED FROM SOURCE.** `src/scheduler.c` — `scheduler_inputs`, lines 55–81

```text
  55: static void scheduler_inputs(ecu_state_t *state)
  56: {
  57:     if (state->scheduler_stress_config.enabled && state->time.time_ms) {
  58:         unsigned int boundary=state->time.time_ms;
  59:         for (state->time.time_ms=boundary-ECU_DT_MS+1; state->time.time_ms<boundary; state->time.time_ms++)
  60:             scheduler_stress_tick(state);
  61:     }
  62:     fault_injection_step(state);
  63:     cross_layer_fault_step(state);
  64:     if (scheduler_task_due(state->time.time_ms, ECU_SENSOR_PERIOD_MS)) {
  65:         sensors_step(state);
  66:     }
  67:     if (state->scheduler_stress_config.enabled) {
  68:         scheduler_stress_tick(state);
  69:         scheduler_stress_sample(state);
  70:     } else if (scheduler_task_due(state->time.time_ms, ECU_CONTROL_PERIOD_MS) &&
  71:         cross_layer_control_execution(state)) {
  72:         runtime_timing_start(&state->timing_recorder, state->time.time_ms);
  73:         control_step(state);
  74:         runtime_timing_complete(&state->timing_recorder, state->time.time_ms);
  75:     }
  76:     if (!state->scheduler_stress_config.enabled)
  77:         runtime_timing_observe(&state->timing_recorder, state->time.time_ms);
  78:     if (state->runtime_safety_config.enabled)
  79:         timing_safety_monitor_step(&state->timing_monitor, &state->timing_recorder.observation,
  80:             state->runtime_safety_config.timing_mode, state->runtime_safety_config.timing_evidence);
  81: }
```


### Exact source: scheduler_reactions

**VERIFIED FROM SOURCE.** `src/scheduler.c` — `scheduler_reactions`, lines 83–124

```text
  83: static void scheduler_reactions(ecu_state_t *state)
  84: {
  85:     if (scheduler_task_due(state->time.time_ms, ECU_ACTUATOR_PERIOD_MS)) {
  86:         actuators_step(state);
  87:     }
  88:     if (scheduler_task_due(state->time.time_ms, ECU_DIAGNOSTIC_PERIOD_MS)) {
  89:         diagnostics_step(state);
  90:     }
  91:     if (scheduler_task_due(state->time.time_ms, ECU_SAFETY_PERIOD_MS)) {
  92:         safety_monitor_step(state);
  93:         actuators_step(state);
  94:         if (scheduler_task_due(state->time.time_ms, ECU_DIAGNOSTIC_PERIOD_MS)) {
  95:             diagnostics_step(state);
  96:         }
  97:     }
  98:     detection_algorithm_step(state);
  99:     if (safety_monitor_apply_detector_request(state)) {
 100:         actuators_step(state);
 101:         if (scheduler_task_due(state->time.time_ms, ECU_DIAGNOSTIC_PERIOD_MS)) {
 102:             diagnostics_step(state);
 103:         }
 104:     }
 105:     if (state->runtime_safety_config.enabled) {
 106:         runtime_observation_t observation;
 107:         runtime_observation_capture(state, &observation);
 108:         if (state->safety_policy_v5_config.enabled)
 109:             safety_policy_v5_step(&state->runtime_safety, &state->safety_policy_v5,
 110:                 &state->runtime_safety_config, state->safety_policy_v5_config.mode,
 111:                 &observation, &state->timing_monitor);
 112:         else runtime_safety_policy_step(&state->runtime_safety, &state->runtime_safety_config,
 113:                 &observation, &state->timing_monitor);
 114:         if (safety_monitor_apply_runtime_request(state, state->runtime_safety.requested_state)) {
 115:             state->runtime_safety.action_applied = true;
 116:             state->runtime_safety.action_samples++;
 117:             if (state->runtime_safety.first_action_ms < 0)
 118:                 state->runtime_safety.first_action_ms = (int)state->time.time_ms;
 119:             actuators_step(state);
 120:             if (scheduler_task_due(state->time.time_ms, ECU_DIAGNOSTIC_PERIOD_MS)) diagnostics_step(state);
 121:         }
 122:     }
 123:     metrics_step(state);
 124: }
```

## Primary-unseen acquisition parameters (artifact-extracted)

**VERIFIED FROM EXPERIMENT ARTIFACT.** Primary campaign baseline experiment defaults are ambient offset0, load scale1, heat bias0, ram-air scale1 (experiment.c); each profile then provides its own ambient/load/speed. Exact floating-point lexical values remain in the manifest and inventory.

| Field | Unique sampled values |
|---|---|
| `simulation_duration_ms` | 120000 |
| `reference_offset` | -0.031, -0.062, -0.093, 0.0, 0.031, 0.062, 0.093 |
| `reference_noise` | 0.021, 0.028, 0.033, 0.049, 0.057, 0.061, 0.086 |
| `c_offset` | -0.0767, -0.0829, -0.0891, -0.0953, -0.1015, 0.0736, 0.0798, 0.086, 0.0922, 0.0984 |
| `c_gain` | -0.000457, -0.000478, -0.00052, -0.000541, -0.000583, -0.0006039999999999999, 0.00043599999999999997, 0.000499, 0.000562, 0.0006249999999999999 |
| `c_noise` | 0.011, 0.0162, 0.0169, 0.0176, 0.0183, 0.019, 0.019700000000000002, 0.0204, 0.0211, 0.0218, 0.0225, 0.027, 0.039 |
| `c_quantum` | 0.016, 0.024, 0.028 |
| `c_adc_gain` | -0.00024700000000000004, -0.00026900000000000003, -0.000291, -0.000313, -0.000335, 0.00023600000000000002, 0.000258, 0.00028, 0.000302, 0.000324 |
| `c_phase_ms` | 23, 49, 85, 9 |
| `c_lag_ms` | 0 |

Default/custom profile context: `src/thermal_plant.c` — `apply_default_thermal_phases`, lines 63–93; `src/thermal_plant.c` — `apply_custom_driving_profile`, lines 115–140.
