#include "cross_layer_fault.h"

/* Bounded generated-sample history. Timestamps identify real sample provenance;
 * they are never read by a detector except through published acquisition age. */
void cross_layer_sensor_delivery(ecu_state_t *state, float generated, float *delivered,
    bool *refreshed, unsigned int *source_ms)
{
    const fault_descriptor_t *f = &state->cross_layer_fault;
    cross_layer_fault_state_t *r = &state->cross_layer_runtime;
    unsigned int now = state->time.time_ms;
    unsigned int slot = (now / ECU_SENSOR_PERIOD_MS) % CROSS_LAYER_HISTORY_SAMPLES;
    if (!f->enabled || f->layer != FAULT_LAYER_COMMUNICATION) return;
    r->history[slot] = generated;
    r->history_timestamps[slot] = now;
    r->history_valid[slot] = true;
    r->generated_value = generated; r->generated_ms = now;
    r->update_generated = true; r->update_delivered = true;
    r->update_dropped = r->update_delayed = r->replay_active = false;
    r->replay_source_ms = -1;
    unsigned int sample_time = now;
    if (r->active) {
        r->active_update_count++;
        if (f->model == FAULT_MODEL_DELAYED_UPDATE) {
            r->update_delayed = true;
            if (now-(unsigned int)r->last_activation_ms < f->communication_delay_ms)
                r->update_delivered = false;
            else sample_time = now-f->communication_delay_ms;
        } else if (f->model == FAULT_MODEL_DROPPED_UPDATE) {
            /* No pattern: drop the first N in each active window. With pattern P:
             * repeat a burst of N dropped samples followed by P-N deliveries. */
            unsigned int index = r->active_update_count-1U;
            bool drop = f->drop_every_n_updates ?
                index % f->drop_every_n_updates < f->drop_count : index < f->drop_count;
            r->update_dropped = drop;
            r->update_delivered = !drop;
            if (drop) { r->consecutive_drops++; r->total_drops++; }
        } else if (f->model == FAULT_MODEL_REPLAYED_SAMPLE) {
            sample_time = now-f->replay_age_ms;
            r->replay_source_ms = (int)sample_time;
            r->replay_active = true;
        }
    }
    if (r->update_delivered) {
        unsigned int source_slot = (sample_time / ECU_SENSOR_PERIOD_MS) % CROSS_LAYER_HISTORY_SAMPLES;
        /* Configuration validation and exact tick history guarantee availability. */
        if (r->history_valid[source_slot] && r->history_timestamps[source_slot] == sample_time) {
            r->delivered_value = r->history[source_slot];
            r->delivered_source_ms = sample_time;
            r->delivered_ms = (int)now;
            r->consecutive_drops = 0;
        } else r->update_delivered = false;
    }
    *delivered = r->delivered_value;
    *refreshed = r->update_delivered;
    *source_ms = r->delivered_source_ms;
    if (r->active && state->propagation.internal_ms < 0 &&
        (!r->update_delivered || r->delivered_source_ms != now || r->delivered_value != generated))
        state->propagation.internal_ms = (int)now;
}
