#include "ecu_types.h"
#include "runtime_safety_policy.h"
#include <string.h>

int runtime_safety_parse_options(int *argc, char **argv, ecu_state_t *state)
{
    runtime_safety_config_t *c = &state->runtime_safety_config;
    *c = (runtime_safety_config_t){ .timing_evidence = TIMING_COMBINED };
    int write = 1;
    for (int read = 1; read < *argc; read++) {
        const char *option = argv[read];
        if (strcmp(option,"--timing-monitor") && strcmp(option,"--timing-evidence") && strcmp(option,"--communication-safety-response")) {
            argv[write++] = argv[read]; continue;
        }
        c->enabled = true;
        if (++read >= *argc) { fprintf(stderr,"Missing value for %s.\n",option); return -1; }
        const char *value = argv[read];
        if (!strcmp(option,"--timing-monitor")) {
            if (!strcmp(value,"disabled")) c->timing_mode = TIMING_DISABLED;
            else if (!strcmp(value,"observe_only")) c->timing_mode = TIMING_OBSERVE_ONLY;
            else if (!strcmp(value,"protective_action")) c->timing_mode = TIMING_PROTECTIVE_ACTION;
            else goto invalid;
        } else if (!strcmp(option,"--timing-evidence")) {
            if (!strcmp(value,"deadline_only")) c->timing_evidence = TIMING_DEADLINE_ONLY;
            else if (!strcmp(value,"execution_age_only")) c->timing_evidence = TIMING_EXECUTION_AGE_ONLY;
            else if (!strcmp(value,"combined")) c->timing_evidence = TIMING_COMBINED;
            else goto invalid;
        } else {
            if (!strcmp(value,"observe_only")) c->communication_protective_action = false;
            else if (!strcmp(value,"protective_action")) c->communication_protective_action = true;
            else goto invalid;
        }
        continue;
invalid:
        fprintf(stderr,"Invalid value for %s: %s.\n",option,value); return -1;
    }
    *argc = write; argv[write] = NULL;
    return 0;
}
