#include "experiment.h"

#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>

#include "fault_injection.h"

/* Experiment module: centralizes campaign definitions and CLI-friendly custom
 * hardware-origin fault abstractions so multiple runs can be compared with
 * consistent metadata across sensing-path, timing/communication-path,
 * actuation-path, and computation/memory-path studies. */
typedef struct {
    const char *campaign_id;
    const char *campaign_label;
    const char *campaign_category;
    unsigned int event_count;
    float ambient_offset_c;
    float engine_load_scale;
    float heat_generation_bias;
    float ram_air_scale;
    fault_event_t events[ECU_MAX_FAULT_EVENTS];
} builtin_campaign_t;

static const builtin_campaign_t BUILTIN_CAMPAIGNS[] = {
    {
        "baseline",
        "Nominal thermal drive cycle without injected faults",
        "baseline",
        0U,
        0.0f,
        1.00f,
        0.0f,
        1.00f,
        {{ FAULT_NONE, FAULT_BEHAVIOR_NONE, 0U, 0U, 0.0f }}
    },
    {
        "paper_default",
        "Mixed hardware-origin campaign with sensing and actuation faults",
        "mixed_hardware_faults",
        3U,
        0.0f,
        1.00f,
        0.0f,
        1.00f,
        {
            { FAULT_SENSOR_BIAS, FAULT_BEHAVIOR_TRANSIENT, 30000U, 15000U, 6.0f },
            { FAULT_PUMP_DEGRADED, FAULT_BEHAVIOR_TRANSIENT, 60000U, 25000U, 0.45f },
            { FAULT_FAN_STUCK_OFF, FAULT_BEHAVIOR_PERMANENT, 90000U, 30000U, 0.0f },
            { FAULT_NONE, FAULT_BEHAVIOR_NONE, 0U, 0U, 0.0f }
        }
    },
    {
        "sensor_bias_only",
        "ADC or analog front-end offset fault campaign",
        "sensing_path_fault",
        1U,
        0.0f,
        1.00f,
        0.0f,
        1.00f,
        {
            { FAULT_SENSOR_BIAS, FAULT_BEHAVIOR_TRANSIENT, 30000U, 15000U, 6.0f },
            { FAULT_NONE, FAULT_BEHAVIOR_NONE, 0U, 0U, 0.0f }
        }
    },
    {
        "stale_sensor_data_only",
        "Delayed sampled-data coolant-sensor update campaign",
        "timing_communication_fault",
        1U,
        0.0f,
        1.00f,
        0.0f,
        1.00f,
        {
            { FAULT_STALE_SENSOR_DATA, FAULT_BEHAVIOR_TRANSIENT, 55000U, 50000U, 12000.0f },
            { FAULT_NONE, FAULT_BEHAVIOR_NONE, 0U, 0U, 0.0f }
        }
    },
    {
        "stale_sensor_data_hot_stress",
        "Thermally stressed stale coolant-sensor update campaign",
        "timing_communication_fault_stress",
        1U,
        6.0f,
        1.10f,
        2.0f,
        0.70f,
        {
            { FAULT_STALE_SENSOR_DATA, FAULT_BEHAVIOR_PERMANENT, 65000U, 0U, 15000.0f },
            { FAULT_NONE, FAULT_BEHAVIOR_NONE, 0U, 0U, 0.0f }
        }
    },
    {
        "pump_degraded_only",
        "Weak-driver or supply-droop related pump-actuation campaign",
        "actuation_path_fault",
        1U,
        0.0f,
        1.00f,
        0.0f,
        1.00f,
        {
            { FAULT_PUMP_DEGRADED, FAULT_BEHAVIOR_TRANSIENT, 60000U, 25000U, 0.45f },
            { FAULT_NONE, FAULT_BEHAVIOR_NONE, 0U, 0U, 0.0f }
        }
    },
    {
        "calibration_memory_corruption",
        "Corrupted coolant-control target calibration campaign",
        "computation_memory_fault",
        1U,
        0.0f,
        1.00f,
        0.0f,
        1.00f,
        {
            { FAULT_CALIBRATION_MEMORY_CORRUPTION, FAULT_BEHAVIOR_PERMANENT, 52000U, 0U, 16.0f },
            { FAULT_NONE, FAULT_BEHAVIOR_NONE, 0U, 0U, 0.0f }
        }
    },
    {
        "fan_stuck_only",
        "Gate-driver, PWM-output, or power-stage stuck-off fan campaign",
        "actuation_path_fault",
        1U,
        0.0f,
        1.00f,
        0.0f,
        1.00f,
        {
            { FAULT_FAN_STUCK_OFF, FAULT_BEHAVIOR_PERMANENT, 90000U, 30000U, 0.0f },
            { FAULT_NONE, FAULT_BEHAVIOR_NONE, 0U, 0U, 0.0f }
        }
    },
    {
        "fan_stuck_hot_stress",
        "Stuck-off fan power-stage fault under thermally stressful conditions",
        "actuation_path_fault_stress",
        1U,
        7.0f,
        1.10f,
        2.2f,
        0.70f,
        {
            { FAULT_FAN_STUCK_OFF, FAULT_BEHAVIOR_PERMANENT, 78100U, 41900U, 0.0f },
            { FAULT_NONE, FAULT_BEHAVIOR_NONE, 0U, 0U, 0.0f }
        }
    },
    {
        "sensor_interface_intermittent",
        "Intermittent sensor-interface corruption campaign",
        "sensing_path_fault",
        1U,
        0.0f,
        1.00f,
        0.0f,
        1.00f,
        {
            { FAULT_SENSOR_INTERFACE_INTERMITTENT, FAULT_BEHAVIOR_TRANSIENT, 45000U, 20000U, 8.0f },
            { FAULT_NONE, FAULT_BEHAVIOR_NONE, 0U, 0U, 0.0f }
        }
    }
};

static void zero_campaign(ecu_state_t *state)
{
    unsigned int i;

    memset(&state->experiment, 0, sizeof(state->experiment));

    for (i = 0U; i < ECU_MAX_FAULT_EVENTS; i++) {
        state->experiment.events[i].mode = FAULT_NONE;
        state->experiment.events[i].behavior = FAULT_BEHAVIOR_NONE;
    }
}

static void clear_driving_profile(ecu_state_t *state)
{
    memset(&state->driving_profile, 0, sizeof(state->driving_profile));
}

static void reset_simulation_duration(ecu_state_t *state)
{
    state->simulation.custom_duration_enabled = false;
    state->simulation.duration_ms = ECU_SIM_DURATION_MS;
}

static void copy_text(char *dst, size_t dst_size, const char *src)
{
    if (dst_size == 0U) {
        return;
    }

    snprintf(dst, dst_size, "%s", (src != NULL) ? src : "");
}

static void assign_campaign(ecu_state_t *state, const builtin_campaign_t *campaign)
{
    unsigned int i;

    zero_campaign(state);
    copy_text(state->experiment.campaign_id, sizeof(state->experiment.campaign_id), campaign->campaign_id);
    copy_text(state->experiment.campaign_label, sizeof(state->experiment.campaign_label), campaign->campaign_label);
    copy_text(state->experiment.campaign_category, sizeof(state->experiment.campaign_category), campaign->campaign_category);
    copy_text(state->experiment.experiment_id, sizeof(state->experiment.experiment_id), campaign->campaign_id);
    state->experiment.event_count = campaign->event_count;
    state->experiment.ambient_offset_c = campaign->ambient_offset_c;
    state->experiment.engine_load_scale = campaign->engine_load_scale;
    state->experiment.heat_generation_bias = campaign->heat_generation_bias;
    state->experiment.ram_air_scale = campaign->ram_air_scale;

    for (i = 0U; i < campaign->event_count && i < ECU_MAX_FAULT_EVENTS; i++) {
        state->experiment.events[i] = campaign->events[i];
    }
}

static const builtin_campaign_t *find_campaign(const char *campaign_id)
{
    unsigned int i;

    for (i = 0U; i < (sizeof(BUILTIN_CAMPAIGNS) / sizeof(BUILTIN_CAMPAIGNS[0])); i++) {
        if (strcmp(BUILTIN_CAMPAIGNS[i].campaign_id, campaign_id) == 0) {
            return &BUILTIN_CAMPAIGNS[i];
        }
    }

    return NULL;
}

void experiment_init_default(ecu_state_t *state)
{
    clear_driving_profile(state);
    reset_simulation_duration(state);
    assign_campaign(state, &BUILTIN_CAMPAIGNS[1]);
}

int experiment_configure_campaign(ecu_state_t *state, const char *campaign_id)
{
    const builtin_campaign_t *campaign = find_campaign(campaign_id);

    if (campaign == NULL) {
        return -1;
    }

    assign_campaign(state, campaign);
    return 0;
}

int experiment_configure_custom_single_fault(
    ecu_state_t *state,
    const char *campaign_id,
    fault_mode_t mode,
    fault_behavior_t behavior,
    unsigned int start_ms,
    unsigned int duration_ms,
    float parameter
)
{
    if (mode == FAULT_NONE) {
        return -1;
    }

    zero_campaign(state);
    copy_text(state->experiment.campaign_id, sizeof(state->experiment.campaign_id), campaign_id);
    copy_text(state->experiment.campaign_label, sizeof(state->experiment.campaign_label), "Custom single-fault campaign");
    copy_text(state->experiment.campaign_category, sizeof(state->experiment.campaign_category), "custom_fault");
    snprintf(
        state->experiment.experiment_id,
        sizeof(state->experiment.experiment_id),
        "%s_%s_%u_%u",
        campaign_id,
        fault_injection_mode_label(mode),
        start_ms,
        duration_ms
    );

    state->experiment.event_count = 1U;
    state->experiment.ambient_offset_c = 0.0f;
    state->experiment.engine_load_scale = 1.00f;
    state->experiment.heat_generation_bias = 0.0f;
    state->experiment.ram_air_scale = 1.00f;
    state->experiment.events[0].mode = mode;
    state->experiment.events[0].behavior = behavior;
    state->experiment.events[0].start_ms = start_ms;
    state->experiment.events[0].duration_ms = duration_ms;
    state->experiment.events[0].parameter = parameter;

    return 0;
}

int experiment_configure_custom_fault_sequence(
    ecu_state_t *state,
    const char *campaign_id,
    const fault_event_t *events,
    unsigned int event_count
)
{
    unsigned int i;

    if (events == NULL || event_count == 0U || event_count > ECU_MAX_FAULT_EVENTS) {
        return -1;
    }

    zero_campaign(state);
    copy_text(state->experiment.campaign_id, sizeof(state->experiment.campaign_id), campaign_id);
    copy_text(state->experiment.campaign_label, sizeof(state->experiment.campaign_label), "Custom multi-fault scenario");
    copy_text(state->experiment.campaign_category, sizeof(state->experiment.campaign_category), "custom_fault_sequence");
    snprintf(
        state->experiment.experiment_id,
        sizeof(state->experiment.experiment_id),
        "%s_%u_events",
        campaign_id,
        event_count
    );

    state->experiment.event_count = event_count;
    state->experiment.ambient_offset_c = 0.0f;
    state->experiment.engine_load_scale = 1.00f;
    state->experiment.heat_generation_bias = 0.0f;
    state->experiment.ram_air_scale = 1.00f;

    for (i = 0U; i < event_count; i++) {
        if (events[i].mode == FAULT_NONE || events[i].behavior == FAULT_BEHAVIOR_NONE) {
            return -1;
        }

        state->experiment.events[i] = events[i];
    }

    return 0;
}

static int parse_uint_field(const char *text, unsigned int *out)
{
    char *endptr;
    long value;

    errno = 0;
    value = strtol(text, &endptr, 10);
    if (errno != 0 || endptr == text || *endptr != '\0' || value < 0L || value > (long)UINT_MAX) {
        return -1;
    }

    *out = (unsigned int)value;
    return 0;
}

static int parse_float_field(const char *text, float *out)
{
    char *endptr;
    float value;

    errno = 0;
    value = strtof(text, &endptr);
    if (errno != 0 || endptr == text || *endptr != '\0') {
        return -1;
    }

    *out = value;
    return 0;
}

static void strip_line_end(char *text)
{
    size_t len = strlen(text);

    while (len > 0U && (text[len - 1U] == '\n' || text[len - 1U] == '\r')) {
        text[len - 1U] = '\0';
        len--;
    }
}

static int validate_driving_segment(const driving_profile_segment_t *segment, unsigned int line_number)
{
    if (segment->end_ms <= segment->start_ms) {
        fprintf(stderr, "Driving profile line %u: end_ms must be greater than start_ms.\n", line_number);
        return -1;
    }
    if (segment->vehicle_speed_kph < 0.0f) {
        fprintf(stderr, "Driving profile line %u: vehicle_speed_kph must be >= 0.\n", line_number);
        return -1;
    }
    if (segment->engine_load < 0.0f || segment->engine_load > 1.0f) {
        fprintf(stderr, "Driving profile line %u: engine_load must be in [0.0, 1.0].\n", line_number);
        return -1;
    }
    if (segment->ambient_temp_c < -40.0f || segment->ambient_temp_c > 80.0f) {
        fprintf(stderr, "Driving profile line %u: ambient_temp_c must be in [-40, 80].\n", line_number);
        return -1;
    }
    if (segment->external_airflow_factor < 0.0f || segment->external_airflow_factor > 1.0f) {
        fprintf(stderr, "Driving profile line %u: external_airflow_factor must be in [0.0, 1.0].\n", line_number);
        return -1;
    }
    if (segment->road_slope_percent < -20.0f || segment->road_slope_percent > 20.0f) {
        fprintf(stderr, "Driving profile line %u: road_slope_percent must be in [-20, 20].\n", line_number);
        return -1;
    }

    return 0;
}

static void sort_driving_segments(driving_profile_segment_t *segments, unsigned int count)
{
    unsigned int i;

    for (i = 1U; i < count; i++) {
        driving_profile_segment_t current = segments[i];
        unsigned int j = i;

        while (j > 0U && segments[j - 1U].start_ms > current.start_ms) {
            segments[j] = segments[j - 1U];
            j--;
        }
        segments[j] = current;
    }
}

int experiment_set_simulation_duration(ecu_state_t *state, unsigned int duration_ms)
{
    if (duration_ms < ECU_MIN_SIM_DURATION_MS || duration_ms > ECU_MAX_SIM_DURATION_MS) {
        fprintf(
            stderr,
            "Invalid simulation duration %u ms. Expected %u..%u ms.\n",
            duration_ms,
            ECU_MIN_SIM_DURATION_MS,
            ECU_MAX_SIM_DURATION_MS
        );
        return -1;
    }

    state->simulation.custom_duration_enabled = true;
    state->simulation.duration_ms = duration_ms;
    return 0;
}

int experiment_validate_driving_profile_coverage(const ecu_state_t *state)
{
    unsigned int expected_start = 0U;
    unsigned int i;

    if (!state->driving_profile.enabled || !state->simulation.custom_duration_enabled) {
        return 0;
    }

    if (state->driving_profile.segment_count == 0U) {
        fprintf(stderr, "Custom driving profile has no segments.\n");
        return -1;
    }

    if (state->driving_profile.segments[0].start_ms != 0U) {
        fprintf(
            stderr,
            "Custom driving profile must start at 0 ms; first segment starts at %u ms.\n",
            state->driving_profile.segments[0].start_ms
        );
        return -1;
    }

    for (i = 0U; i < state->driving_profile.segment_count; i++) {
        const driving_profile_segment_t *segment = &state->driving_profile.segments[i];

        if (segment->start_ms > expected_start) {
            fprintf(
                stderr,
                "Custom driving profile gap detected: %u-%u ms is uncovered.\n",
                expected_start,
                segment->start_ms
            );
            return -1;
        }
        if (segment->start_ms < expected_start) {
            fprintf(
                stderr,
                "Custom driving profile overlap detected around %u-%u ms.\n",
                segment->start_ms,
                expected_start
            );
            return -1;
        }
        expected_start = segment->end_ms;
    }

    if (expected_start < state->simulation.duration_ms) {
        fprintf(
            stderr,
            "Custom driving profile ends at %u ms but simulation duration is %u ms. "
            "Add a segment from %u to %u ms.\n",
            expected_start,
            state->simulation.duration_ms,
            expected_start,
            state->simulation.duration_ms
        );
        return -1;
    }
    if (expected_start > state->simulation.duration_ms) {
        fprintf(
            stderr,
            "Custom driving profile ends at %u ms but simulation duration is %u ms.\n",
            expected_start,
            state->simulation.duration_ms
        );
        return -1;
    }

    return 0;
}

int experiment_load_driving_profile(ecu_state_t *state, const char *path)
{
    FILE *profile_file;
    char line[512];
    driving_profile_config_t loaded_profile;
    unsigned int line_number = 0U;

    if (path == NULL || path[0] == '\0') {
        fprintf(stderr, "Driving profile path is empty.\n");
        return -1;
    }

    profile_file = fopen(path, "r");
    if (profile_file == NULL) {
        fprintf(stderr, "Failed to open driving profile '%s': %s\n", path, strerror(errno));
        return -1;
    }

    memset(&loaded_profile, 0, sizeof(loaded_profile));
    copy_text(loaded_profile.source_path, sizeof(loaded_profile.source_path), path);

    while (fgets(line, sizeof(line), profile_file) != NULL) {
        char *tokens[7];
        char *cursor;
        unsigned int token_count = 0U;
        driving_profile_segment_t segment;

        line_number++;
        strip_line_end(line);
        if (line[0] == '\0') {
            continue;
        }
        if (line_number == 1U && strstr(line, "start_ms") != NULL) {
            continue;
        }
        if (loaded_profile.segment_count >= ECU_MAX_DRIVING_PROFILE_SEGMENTS) {
            fprintf(
                stderr,
                "Driving profile has more than %u segments; keep this research model compact.\n",
                ECU_MAX_DRIVING_PROFILE_SEGMENTS
            );
            fclose(profile_file);
            return -1;
        }

        cursor = strtok(line, ",");
        while (cursor != NULL && token_count < 7U) {
            tokens[token_count] = cursor;
            token_count++;
            cursor = strtok(NULL, ",");
        }
        if (token_count != 7U || cursor != NULL) {
            fprintf(stderr, "Driving profile line %u: expected 7 CSV columns.\n", line_number);
            fclose(profile_file);
            return -1;
        }

        memset(&segment, 0, sizeof(segment));
        if (parse_uint_field(tokens[0], &segment.start_ms) != 0 ||
            parse_uint_field(tokens[1], &segment.end_ms) != 0 ||
            parse_float_field(tokens[2], &segment.vehicle_speed_kph) != 0 ||
            parse_float_field(tokens[3], &segment.engine_load) != 0 ||
            parse_float_field(tokens[4], &segment.ambient_temp_c) != 0 ||
            parse_float_field(tokens[5], &segment.external_airflow_factor) != 0 ||
            parse_float_field(tokens[6], &segment.road_slope_percent) != 0) {
            fprintf(stderr, "Driving profile line %u: failed to parse numeric values.\n", line_number);
            fclose(profile_file);
            return -1;
        }

        if (validate_driving_segment(&segment, line_number) != 0) {
            fclose(profile_file);
            return -1;
        }

        loaded_profile.segments[loaded_profile.segment_count] = segment;
        loaded_profile.segment_count++;
    }

    fclose(profile_file);

    if (loaded_profile.segment_count == 0U) {
        fprintf(stderr, "Driving profile '%s' does not contain any segments.\n", path);
        return -1;
    }

    sort_driving_segments(loaded_profile.segments, loaded_profile.segment_count);
    loaded_profile.enabled = true;
    state->driving_profile = loaded_profile;
    return 0;
}

fault_mode_t experiment_fault_mode_from_string(const char *text)
{
    if (strcmp(text, "sensor_bias") == 0) {
        return FAULT_SENSOR_BIAS;
    }
    if (strcmp(text, "sensor_interface_intermittent") == 0) {
        return FAULT_SENSOR_INTERFACE_INTERMITTENT;
    }
    if (strcmp(text, "stale_sensor_data") == 0) {
        return FAULT_STALE_SENSOR_DATA;
    }
    if (strcmp(text, "pump_degraded") == 0) {
        return FAULT_PUMP_DEGRADED;
    }
    if (strcmp(text, "calibration_memory_corruption") == 0) {
        return FAULT_CALIBRATION_MEMORY_CORRUPTION;
    }
    if (strcmp(text, "fan_stuck_off") == 0) {
        return FAULT_FAN_STUCK_OFF;
    }

    return FAULT_NONE;
}

fault_behavior_t experiment_fault_behavior_from_string(const char *text)
{
    if (strcmp(text, "transient") == 0) {
        return FAULT_BEHAVIOR_TRANSIENT;
    }
    if (strcmp(text, "permanent") == 0) {
        return FAULT_BEHAVIOR_PERMANENT;
    }

    return FAULT_BEHAVIOR_NONE;
}

const char *experiment_campaign_usage(void)
{
    return
        "Usage:\n"
        "  ./virtual_ecu [log_path]\n"
        "  ./virtual_ecu [log_path] <campaign_id>\n"
        "  ./virtual_ecu [log_path] custom <fault_type> <start_ms> <duration_ms> <fault_behavior> <parameter>\n"
        "  ./virtual_ecu [log_path] custom_multi <event_count> <fault_type> <start_ms> <duration_ms> <fault_behavior> <parameter> [...]\n"
        "  Append --detector <builtin_ecu|threshold|ewma|cusum|thermal_observer|kalman_filter|adaptive_kalman_filter|hybrid_adaptive_kalman> "
        "to select runtime detection.\n"
        "  Append --detector-action <observe_only|precautionary_cooling|limp_home> "
        "to select intervention.\n"
        "  Append --driving-profile <path> to enable an optional custom driving/environment CSV profile.\n"
        "  Append --simulation-duration-ms <duration_ms> to run with an explicit duration.\n";
}

void experiment_list_campaigns(FILE *stream)
{
    unsigned int i;

    fprintf(stream, "Available campaigns:\n");
    for (i = 0U; i < (sizeof(BUILTIN_CAMPAIGNS) / sizeof(BUILTIN_CAMPAIGNS[0])); i++) {
        fprintf(
            stream,
            "  %s: %s\n",
            BUILTIN_CAMPAIGNS[i].campaign_id,
            BUILTIN_CAMPAIGNS[i].campaign_label
        );
    }
}
