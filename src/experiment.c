#include "experiment.h"

#include <stdlib.h>
#include <string.h>

#include "fault_injection.h"

/* Experiment module: centralizes campaign definitions and CLI-friendly custom
 * fault configuration so multiple runs can be compared with consistent metadata. */
typedef struct {
    const char *campaign_id;
    const char *campaign_label;
    unsigned int event_count;
    fault_event_t events[ECU_MAX_FAULT_EVENTS];
} builtin_campaign_t;

static const builtin_campaign_t BUILTIN_CAMPAIGNS[] = {
    {
        "baseline",
        "Nominal thermal drive cycle without injected faults",
        0U,
        {{ FAULT_NONE, FAULT_BEHAVIOR_NONE, 0U, 0U, 0.0f }}
    },
    {
        "paper_default",
        "Three-phase paper campaign with sensor, pump, and fan faults",
        3U,
        {
            { FAULT_SENSOR_BIAS, FAULT_BEHAVIOR_TRANSIENT, 30000U, 15000U, 6.0f },
            { FAULT_PUMP_DEGRADED, FAULT_BEHAVIOR_TRANSIENT, 60000U, 25000U, 0.45f },
            { FAULT_FAN_STUCK_OFF, FAULT_BEHAVIOR_PERMANENT, 90000U, 30000U, 0.0f },
            { FAULT_NONE, FAULT_BEHAVIOR_NONE, 0U, 0U, 0.0f }
        }
    },
    {
        "sensor_bias_only",
        "Single transient coolant-sensor bias campaign",
        1U,
        {
            { FAULT_SENSOR_BIAS, FAULT_BEHAVIOR_TRANSIENT, 30000U, 15000U, 6.0f },
            { FAULT_NONE, FAULT_BEHAVIOR_NONE, 0U, 0U, 0.0f }
        }
    },
    {
        "pump_degraded_only",
        "Single transient pump-degradation campaign",
        1U,
        {
            { FAULT_PUMP_DEGRADED, FAULT_BEHAVIOR_TRANSIENT, 60000U, 25000U, 0.45f },
            { FAULT_NONE, FAULT_BEHAVIOR_NONE, 0U, 0U, 0.0f }
        }
    },
    {
        "fan_stuck_only",
        "Single permanent fan-stuck-off campaign",
        1U,
        {
            { FAULT_FAN_STUCK_OFF, FAULT_BEHAVIOR_PERMANENT, 90000U, 30000U, 0.0f },
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
    copy_text(state->experiment.experiment_id, sizeof(state->experiment.experiment_id), campaign->campaign_id);
    state->experiment.event_count = campaign->event_count;

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
    state->experiment.events[0].mode = mode;
    state->experiment.events[0].behavior = behavior;
    state->experiment.events[0].start_ms = start_ms;
    state->experiment.events[0].duration_ms = duration_ms;
    state->experiment.events[0].parameter = parameter;

    return 0;
}

fault_mode_t experiment_fault_mode_from_string(const char *text)
{
    if (strcmp(text, "sensor_bias") == 0) {
        return FAULT_SENSOR_BIAS;
    }
    if (strcmp(text, "pump_degraded") == 0) {
        return FAULT_PUMP_DEGRADED;
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
        "  ./virtual_ecu [log_path] custom <fault_type> <start_ms> <duration_ms> <fault_behavior> <parameter>\n";
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
