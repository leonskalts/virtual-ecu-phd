/* Isolated experiment driver. Calls unchanged ECU components, not scheduler_run.
 * Fixed plant input and omitted reactions/integration are explicit model bounds. */
#include "ecu_types.h"
#include "control.h"
#include "sensors.h"
#include "actuators.h"
#include "fault_injection.h"
#include "cross_layer_fault.h"
#include "runtime_observation.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <float.h>
_Static_assert(sizeof(float)==4 && FLT_MANT_DIG==24 && FLT_RADIX==2, "binary32 required");
static uint32_t word(float f) { uint32_t u; memcpy(&u,&f,4); return u; }
int main(int argc,char **argv) {
    if(argc!=7) return 2;
    ecu_state_t s={0};
    const char *kind=argv[1]; unsigned start=(unsigned)atoi(argv[2]), duration=(unsigned)atoi(argv[3]);
    float parameter=strtof(argv[4],NULL); unsigned aux=(unsigned)atoi(argv[5]);
    s.plant.coolant_temp_true_c=strtof(argv[6],NULL);
    s.simulation.duration_ms=500;
    fault_injection_init(&s); sensors_init(&s); control_init(&s); actuators_init(&s);
    runtime_timing_init(&s.timing_recorder,100); cross_layer_fault_init(&s);
    if(!strcmp(kind,"bias") || !strcmp(kind,"pump")) {
        s.experiment.event_count=1;
        s.experiment.events[0]=(fault_event_t){.mode=!strcmp(kind,"bias")?FAULT_SENSOR_BIAS:FAULT_PUMP_DEGRADED,
            .behavior=FAULT_BEHAVIOR_TRANSIENT,.start_ms=start,.duration_ms=duration,.parameter=parameter};
    } else if(strcmp(kind,"healthy")) {
        fault_descriptor_t *f=&s.cross_layer_fault;
        f->enabled=true; f->behavior=FAULT_BEHAVIOR_TRANSIENT; f->start_ms=start; f->duration_ms=duration;
        if(!strcmp(kind,"flip") || !strcmp(kind,"stuck")) {
            f->layer=FAULT_LAYER_MEMORY; f->target=FAULT_TARGET_CONTROL_TARGET_REGISTER;
            f->model=!strcmp(kind,"flip")?FAULT_MODEL_BIT_FLIP:FAULT_MODEL_STUCK_BIT;
            f->bit_index=(unsigned)parameter; f->stuck_polarity=aux;
        } else if(!strcmp(kind,"skip") || !strcmp(kind,"delay")) {
            f->layer=FAULT_LAYER_TIMING; f->target=FAULT_TARGET_CONTROL_TASK;
            f->model=!strcmp(kind,"skip")?FAULT_MODEL_DEADLINE_MISS:FAULT_MODEL_TASK_DELAY;
            f->task_delay_ms=(unsigned)parameter;
        } else {
            f->layer=FAULT_LAYER_COMMUNICATION; f->target=FAULT_TARGET_COOLANT_SENSOR;
            if(!strcmp(kind,"replay")){f->model=FAULT_MODEL_REPLAYED_SAMPLE;f->replay_age_ms=(unsigned)parameter;}
            else if(!strcmp(kind,"comm_delay")){f->model=FAULT_MODEL_DELAYED_UPDATE;f->communication_delay_ms=(unsigned)parameter;}
            else if(!strcmp(kind,"drop")){f->model=FAULT_MODEL_DROPPED_UPDATE;f->drop_count=(unsigned)parameter;}
            else return 3;
        }
    }
    if(cross_layer_validate(&s)) return 4;
    for(unsigned t=0;t<=400;t+=100) {
        s.time.time_ms=t;
        fault_injection_step(&s); cross_layer_fault_step(&s); sensors_step(&s);
        if(cross_layer_control_execution(&s)) {
            runtime_timing_start(&s.timing_recorder,t); control_step(&s); runtime_timing_complete(&s.timing_recorder,t);
        }
        runtime_timing_observe(&s.timing_recorder,t); actuators_step(&s);
        runtime_observation_t o; runtime_observation_capture(&s,&o);
        printf("%u,%08x,%08x,%08x,%u,%u,%d,%u,%u,%d,%08x,%d,%08x,%u,%d\n",
            o.time_ms,word(o.coolant_measured_c),word(o.pump_command),word(o.pump_actual),
            o.sample_timestamp_ms,o.sample_age_ms,o.sample_freshness_ok,o.target_register_c,o.target_shadow_c,
            o.target_shadow_valid,word(o.control_target_c),o.control_execution_ms,word(o.source_c),o.source_ms,o.source_valid);
    }
    return 0;
}
