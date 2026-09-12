#include "ecu_types.h"
#include "safety_policy_v5.h"
#include <stdlib.h>
#include <string.h>
#include <errno.h>

int validation_v5_parse_options(int *argc, char **argv, ecu_state_t *state)
{
    scheduler_stress_config_t *c=&state->scheduler_stress_config;
    *c=(scheduler_stress_config_t){ .seed=1,.execution_ms=20,.stress_start_ms=1000,
        .stress_duration_ms=1000,.overload_execution_ms=150 };
    int write=1;
    for (int read=1;read<*argc;read++) {
        const char *key=argv[read];
        if (strcmp(key,"--v5-policy") && strncmp(key,"--scheduler-",12)) { argv[write++]=argv[read];continue; }
        if (++read>=*argc) { fprintf(stderr,"Missing %s value\n",key);return -1; }
        const char *value=argv[read];
        state->safety_policy_v5_config.enabled=true;
        if (!strcmp(key,"--v5-policy")) {
            if (!strcmp(value,"observe_only")) state->safety_policy_v5_config.mode=V5_OBSERVE;
            else if (!strcmp(value,"immediate")) state->safety_policy_v5_config.mode=V5_IMMEDIATE;
            else if (!strcmp(value,"graded")) state->safety_policy_v5_config.mode=V5_GRADED;
            else goto invalid;
        } else if (!strcmp(key,"--scheduler-stress")) {
            c->enabled=true;
            if (!strcmp(value,"legal")) c->overload=false;
            else if (!strcmp(value,"overload")) c->overload=true;
            else goto invalid;
        } else if (!strcmp(key,"--scheduler-events")) {
            if (strlen(value)>=sizeof(c->events_path)) goto invalid;
            strcpy(c->events_path,value);
        } else {
            char *end;errno=0;unsigned long number=strtoul(value,&end,10);
            if (errno || !*value || *end || value[0]=='-' || number>100000000U) goto invalid;
            unsigned int *target=NULL;
            if (!strcmp(key,"--scheduler-seed")) target=&c->seed;
            else if (!strcmp(key,"--scheduler-release-jitter-ms")) target=&c->release_jitter_ms;
            else if (!strcmp(key,"--scheduler-start-jitter-ms")) target=&c->start_jitter_ms;
            else if (!strcmp(key,"--scheduler-execution-ms")) target=&c->execution_ms;
            else if (!strcmp(key,"--scheduler-stress-start-ms")) target=&c->stress_start_ms;
            else if (!strcmp(key,"--scheduler-stress-duration-ms")) target=&c->stress_duration_ms;
            else if (!strcmp(key,"--scheduler-overload-execution-ms")) target=&c->overload_execution_ms;
            else if (!strcmp(key,"--scheduler-on-ms")) target=&c->on_ms;
            else if (!strcmp(key,"--scheduler-off-ms")) target=&c->off_ms;
            if (!target) goto invalid;
            *target=(unsigned int)number;
        }
        continue;
invalid:
        fprintf(stderr,"Invalid v5 option %s %s\n",key,value);return -1;
    }
    *argc=write;argv[write]=NULL;
    if (c->enabled && c->release_jitter_ms+c->start_jitter_ms+c->execution_ms>100U) {
        fprintf(stderr,"Base scheduler envelope must meet P=D=100 ms\n");return -1;
    }
    if (state->safety_policy_v5_config.enabled) {
        state->runtime_safety_config.enabled=true;
        bool action=state->safety_policy_v5_config.mode!=V5_OBSERVE;
        state->runtime_safety_config.timing_mode=action ? TIMING_PROTECTIVE_ACTION : TIMING_OBSERVE_ONLY;
        state->runtime_safety_config.communication_protective_action=action;
    }
    return 0;
}
