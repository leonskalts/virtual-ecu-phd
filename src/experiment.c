#include "experiment.h"

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
        "  Append --detector <builtin_ecu|threshold|ewma|cusum> to select runtime detection.\n"
        "  Append --detector-action <observe_only|precautionary_cooling|limp_home> "
        "to select intervention.\n";
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
