#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "config.h"
#include "experiment.h"
#include "logger.h"
#include "metrics.h"
#include "scheduler.h"

/* Main entry point: initializes the ECU state, runs one deterministic
 * experiment, and writes the resulting CSV trace. */
static int looks_like_csv_path(const char *text)
{
    size_t len = strlen(text);

    return (len >= 4U) && (strcmp(text + len - 4U, ".csv") == 0);
}

static int configure_experiment_from_args(ecu_state_t *state, int argc, char **argv, const char **log_path)
{
    int arg_index = 1;

    *log_path = ECU_DEFAULT_LOG_PATH;
    experiment_init_default(state);

    if (argc > 1 && looks_like_csv_path(argv[1])) {
        *log_path = argv[1];
        arg_index = 2;
    }

    if (argc <= arg_index) {
        return 0;
    }

    if (strcmp(argv[arg_index], "--list-campaigns") == 0) {
        printf("%s", experiment_campaign_usage());
        experiment_list_campaigns(stdout);
        return 1;
    }

    if (strcmp(argv[arg_index], "custom") == 0) {
        fault_mode_t mode;
        fault_behavior_t behavior;
        unsigned int start_ms;
        unsigned int duration_ms;
        float parameter;

        if (argc <= arg_index + 5) {
            fprintf(stderr, "%s", experiment_campaign_usage());
            experiment_list_campaigns(stderr);
            return -1;
        }

        mode = experiment_fault_mode_from_string(argv[arg_index + 1]);
        behavior = experiment_fault_behavior_from_string(argv[arg_index + 4]);
        start_ms = (unsigned int)strtoul(argv[arg_index + 2], NULL, 10);
        duration_ms = (unsigned int)strtoul(argv[arg_index + 3], NULL, 10);
        parameter = strtof(argv[arg_index + 5], NULL);

        if (mode == FAULT_NONE || behavior == FAULT_BEHAVIOR_NONE) {
            fprintf(stderr, "Invalid custom fault configuration.\n");
            fprintf(stderr, "%s", experiment_campaign_usage());
            return -1;
        }

        if (experiment_configure_custom_single_fault(
                state,
                "custom",
                mode,
                behavior,
                start_ms,
                duration_ms,
                parameter
            ) != 0) {
            fprintf(stderr, "Failed to configure custom campaign.\n");
            return -1;
        }

        return 0;
    }

    if (strcmp(argv[arg_index], "custom_multi") == 0) {
        fault_event_t events[ECU_MAX_FAULT_EVENTS];
        unsigned int event_count;
        unsigned int required_argc;
        unsigned int i;

        if (argc <= arg_index + 1) {
            fprintf(stderr, "%s", experiment_campaign_usage());
            experiment_list_campaigns(stderr);
            return -1;
        }

        event_count = (unsigned int)strtoul(argv[arg_index + 1], NULL, 10);
        if (event_count < 2U || event_count > ECU_MAX_FAULT_EVENTS) {
            fprintf(stderr, "custom_multi expects between 2 and %u ordered fault events.\n", ECU_MAX_FAULT_EVENTS);
            fprintf(stderr, "%s", experiment_campaign_usage());
            return -1;
        }

        required_argc = (unsigned int)(arg_index + 2) + (event_count * 5U);
        if ((unsigned int)argc != required_argc) {
            fprintf(stderr, "custom_multi requires exactly %u event argument groups.\n", event_count);
            fprintf(stderr, "%s", experiment_campaign_usage());
            return -1;
        }

        memset(events, 0, sizeof(events));
        for (i = 0U; i < event_count; i++) {
            int base_index = arg_index + 2 + (int)(i * 5U);

            events[i].mode = experiment_fault_mode_from_string(argv[base_index]);
            events[i].start_ms = (unsigned int)strtoul(argv[base_index + 1], NULL, 10);
            events[i].duration_ms = (unsigned int)strtoul(argv[base_index + 2], NULL, 10);
            events[i].behavior = experiment_fault_behavior_from_string(argv[base_index + 3]);
            events[i].parameter = strtof(argv[base_index + 4], NULL);

            if (events[i].mode == FAULT_NONE || events[i].behavior == FAULT_BEHAVIOR_NONE) {
                fprintf(stderr, "Invalid custom_multi fault configuration at event %u.\n", i + 1U);
                fprintf(stderr, "%s", experiment_campaign_usage());
                return -1;
            }
        }

        if (experiment_configure_custom_fault_sequence(state, "custom_multi", events, event_count) != 0) {
            fprintf(stderr, "Failed to configure custom multi-fault scenario.\n");
            return -1;
        }

        return 0;
    }

    if (experiment_configure_campaign(state, argv[arg_index]) != 0) {
        fprintf(stderr, "Unknown campaign '%s'.\n", argv[arg_index]);
        fprintf(stderr, "%s", experiment_campaign_usage());
        experiment_list_campaigns(stderr);
        return -1;
    }

    return 0;
}

int main(int argc, char **argv)
{
    ecu_state_t state;
    const char *log_path = ECU_DEFAULT_LOG_PATH;
    int config_status;
    char summary_path[ECU_PATH_BUFFER_SIZE];

    memset(&state, 0, sizeof(state));
    config_status = configure_experiment_from_args(&state, argc, argv, &log_path);
    if (config_status != 0) {
        return (config_status > 0) ? 0 : 1;
    }

    scheduler_init(&state);

    if (logger_open(&state, log_path) != 0) {
        return 1;
    }

    scheduler_run(&state);
    logger_close(&state);
    if (metrics_write_summary(&state, log_path, summary_path, sizeof(summary_path)) != 0) {
        return 1;
    }

    printf("Simulation complete. CSV log written to %s\n", log_path);
    printf("Summary metrics written to %s\n", summary_path);
    printf("Experiment ID: %s\n", state.experiment.experiment_id);
    printf("Campaign: %s\n", state.experiment.campaign_id);
    printf("Final coolant temperature: %.2f C\n", state.plant.coolant_temp_true_c);
    printf("Final safe state: %d\n", (int)state.safety.current_state);
    printf("Primary DTC at end of run: %d\n", (int)state.diagnostics.primary_dtc);

    return 0;
}
