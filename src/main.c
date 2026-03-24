#include <stdio.h>
#include <string.h>

#include "config.h"
#include "logger.h"
#include "scheduler.h"

/* Main entry point: initializes the ECU state, runs one deterministic
 * experiment, and writes the resulting CSV trace. */
int main(int argc, char **argv)
{
    ecu_state_t state;
    const char *log_path = ECU_DEFAULT_LOG_PATH;

    memset(&state, 0, sizeof(state));

    if (argc > 1) {
        log_path = argv[1];
    }

    scheduler_init(&state);

    if (logger_open(&state, log_path) != 0) {
        return 1;
    }

    scheduler_run(&state);
    logger_close(&state);

    printf("Simulation complete. CSV log written to %s\n", log_path);
    printf("Final coolant temperature: %.2f C\n", state.plant.coolant_temp_true_c);
    printf("Final safe state: %d\n", (int)state.safety.current_state);
    printf("Primary DTC at end of run: %d\n", (int)state.diagnostics.primary_dtc);

    return 0;
}
