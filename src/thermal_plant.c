#include "thermal_plant.h"

#include "config.h"

/* Thermal plant: a compact lumped model for coolant and radiator temperature.
 * It is intentionally simple enough for a paper appendix, yet rich enough to
 * excite diagnostics, control, and safety behavior. */
static float clamp_nonnegative(float value)
{
    if (value < 0.0f) {
        return 0.0f;
    }
    return value;
}

static float clamp_min(float value, float minimum)
{
    if (value < minimum) {
        return minimum;
    }
    return value;
}

static float clamp_range(float value, float minimum, float maximum)
{
    if (value < minimum) {
        return minimum;
    }
    if (value > maximum) {
        return maximum;
    }
    return value;
}

const char *thermal_plant_phase_label(scenario_phase_t phase)
{
    switch (phase) {
    case SCENARIO_PHASE_HIGHWAY:
        return "highway_load";
    case SCENARIO_PHASE_URBAN_TRAFFIC:
        return "urban_traffic";
    case SCENARIO_PHASE_HOT_IDLE:
        return "hot_idle";
    case SCENARIO_PHASE_WARMUP:
    default:
        return "warmup";
    }
}

void thermal_plant_init(ecu_state_t *state)
{
    state->plant.scenario_phase = SCENARIO_PHASE_WARMUP;
    state->plant.ambient_temp_c = 25.0f;
    state->plant.engine_load = 0.35f;
    state->plant.engine_speed_rpm = 1500.0f;
    state->plant.vehicle_speed_kph = 35.0f;
    state->plant.external_airflow_factor = 0.0f;
    state->plant.road_slope_percent = 0.0f;
    state->plant.coolant_temp_true_c = 88.0f;
    state->plant.radiator_temp_true_c = 78.0f;
}

static void apply_default_thermal_phases(ecu_state_t *state, float time_s)
{
    if (time_s < 20.0f) {
        state->plant.scenario_phase = SCENARIO_PHASE_WARMUP;
        state->plant.engine_load = 0.35f;
        state->plant.vehicle_speed_kph = 35.0f;
        state->plant.engine_speed_rpm = 1500.0f;
        state->plant.ambient_temp_c = 25.0f;
    } else if (time_s < 60.0f) {
        state->plant.scenario_phase = SCENARIO_PHASE_HIGHWAY;
        state->plant.engine_load = 0.72f;
        state->plant.vehicle_speed_kph = 85.0f;
        state->plant.engine_speed_rpm = 2800.0f;
        state->plant.ambient_temp_c = 28.0f;
    } else if (time_s < 90.0f) {
        state->plant.scenario_phase = SCENARIO_PHASE_URBAN_TRAFFIC;
        state->plant.engine_load = 0.82f;
        state->plant.vehicle_speed_kph = 15.0f;
        state->plant.engine_speed_rpm = 2200.0f;
        state->plant.ambient_temp_c = 31.0f;
    } else {
        state->plant.scenario_phase = SCENARIO_PHASE_HOT_IDLE;
        state->plant.engine_load = 0.98f;
        state->plant.vehicle_speed_kph = 0.0f;
        state->plant.engine_speed_rpm = 2100.0f;
        state->plant.ambient_temp_c = 35.0f;
    }

    state->plant.external_airflow_factor = 0.0f;
    state->plant.road_slope_percent = 0.0f;
}

static const driving_profile_segment_t *active_driving_segment(const ecu_state_t *state)
{
    unsigned int i;
    const driving_profile_segment_t *last_segment = NULL;

    for (i = 0U; i < state->driving_profile.segment_count; i++) {
        const driving_profile_segment_t *segment = &state->driving_profile.segments[i];

        last_segment = segment;
        if (state->time.time_ms >= segment->start_ms && state->time.time_ms < segment->end_ms) {
            return segment;
        }
        if (state->time.time_ms < segment->start_ms) {
            break;
        }
    }

    return last_segment;
}

static void apply_custom_driving_profile(ecu_state_t *state)
{
    const driving_profile_segment_t *segment = active_driving_segment(state);

    if (segment == NULL) {
        apply_default_thermal_phases(state, (float)state->time.time_ms / 1000.0f);
        return;
    }

    if (segment->vehicle_speed_kph >= 70.0f) {
        state->plant.scenario_phase = SCENARIO_PHASE_HIGHWAY;
        state->plant.engine_speed_rpm = 2800.0f;
    } else if (segment->vehicle_speed_kph > 1.0f) {
        state->plant.scenario_phase = SCENARIO_PHASE_URBAN_TRAFFIC;
        state->plant.engine_speed_rpm = 2200.0f;
    } else {
        state->plant.scenario_phase = SCENARIO_PHASE_HOT_IDLE;
        state->plant.engine_speed_rpm = 2100.0f;
    }

    state->plant.vehicle_speed_kph = segment->vehicle_speed_kph;
    state->plant.engine_load = segment->engine_load;
    state->plant.ambient_temp_c = segment->ambient_temp_c;
    state->plant.external_airflow_factor = segment->external_airflow_factor;
    state->plant.road_slope_percent = segment->road_slope_percent;
}

void thermal_plant_step(ecu_state_t *state)
{
    float time_s = (float)state->time.time_ms / 1000.0f;
    float dt_s = (float)ECU_DT_MS / 1000.0f;
    float heat_generation;
    float pump_cooling;
    float fan_cooling;
    float ram_air_cooling;
    float ambient_coupling;
    float temp_delta;

    if (state->driving_profile.enabled) {
        apply_custom_driving_profile(state);
    } else {
        apply_default_thermal_phases(state, time_s);
    }

    state->plant.ambient_temp_c += state->experiment.ambient_offset_c;
    state->plant.engine_load *= state->experiment.engine_load_scale;
    if (state->driving_profile.enabled) {
        /* Simplified research-only road grade effect: positive grade adds
         * effective load, negative grade subtracts it. This is not a calibrated
         * production vehicle model. */
        state->plant.engine_load += 0.01f * state->plant.road_slope_percent;
        state->plant.engine_load = clamp_range(state->plant.engine_load, 0.0f, 1.20f);
    }
    state->plant.engine_load = clamp_min(state->plant.engine_load, 0.0f);

    /* The safety monitor limits the effective engine load rather than altering
     * the scenario definition itself, which keeps the experiment design clear. */
    state->plant.engine_load *= state->safety.load_limit_scale;

    if (state->safety.shutdown_requested) {
        state->plant.vehicle_speed_kph *= 0.25f;
        state->plant.engine_speed_rpm *= 0.60f;
    }

    heat_generation = 2.2f + (9.5f * state->plant.engine_load);

    if (state->plant.scenario_phase == SCENARIO_PHASE_HOT_IDLE) {
        heat_generation += 2.0f;
    }

    heat_generation += state->experiment.heat_generation_bias;

    pump_cooling = 7.5f * state->actuators.pump_actual;
    fan_cooling = 6.0f * state->actuators.fan_actual;
    ram_air_cooling = (state->plant.vehicle_speed_kph / 40.0f) * state->experiment.ram_air_scale;
    if (state->driving_profile.enabled) {
        /* external_airflow_factor is a controllable extra-cooling knob for the
         * virtual ECU study, not a real aerodynamic wind model. */
        ram_air_cooling += 3.0f * state->plant.external_airflow_factor;
    }
    ambient_coupling = 0.08f * (state->plant.coolant_temp_true_c - state->plant.ambient_temp_c);

    temp_delta = heat_generation - pump_cooling - fan_cooling - ram_air_cooling - ambient_coupling;
    state->plant.coolant_temp_true_c += temp_delta * dt_s;
    state->plant.coolant_temp_true_c = clamp_nonnegative(state->plant.coolant_temp_true_c);

    state->plant.radiator_temp_true_c =
        state->plant.ambient_temp_c +
        (state->plant.coolant_temp_true_c - state->plant.ambient_temp_c) *
        (0.55f - (0.15f * state->actuators.fan_actual));
}
