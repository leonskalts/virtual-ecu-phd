#include "control.h"
#include "sensors.h"
#include "runtime_observation.h"
#include <assert.h>
#include <math.h>
#include <string.h>
int main(void)
{
    ecu_state_t s={0};
    control_init(&s);
    control_commit_target(&s,104);
    assert(s.control.target_register_c==104 && s.control.target_shadow_c==104 && s.control.target_shadow_valid);
    s.control.target_register_c^=1;
    runtime_observation_t o;
    runtime_observation_capture(&s,&o);
    assert(o.target_register_c==105 && o.target_shadow_c==104);
    s.plant.coolant_temp_true_c=80;
    sensors_init(&s);
    assert(!s.sensors.coolant_source_valid);
    s.faults.enabled=true;s.faults.active_mode=FAULT_SENSOR_BIAS;s.faults.sensor_bias_c=7;
    sensors_step(&s);
    runtime_observation_capture(&s,&o);
    assert(o.source_valid && o.source_c==87 && o.coolant_measured_c==87);
    /* Local tap contains front-end corruption, not pristine temperature. */
    s.time.time_ms=100;s.faults.active_mode=FAULT_STALE_SENSOR_DATA;s.faults.sensor_update_hold_ms=500;
    sensors_step(&s);
    s.time.time_ms=200;s.plant.coolant_temp_true_c=81;sensors_step(&s);
    runtime_observation_capture(&s,&o);
    assert(o.source_c==81 && o.coolant_measured_c==80 && o.source_ms==200);
    assert(o.source_previous_valid && o.source_previous_c==80 && o.source_previous_ms==100);
    ecu_state_t hidden=s;
    hidden.plant.coolant_temp_true_c=999;hidden.cross_layer_runtime.active=true;
    hidden.cross_layer_fault.layer=FAULT_LAYER_MEMORY;hidden.propagation.plant_ms=0;
    runtime_observation_t q;runtime_observation_capture(&hidden,&q);
    assert(!memcmp(&o,&q,sizeof(o)));
    return 0;
}
