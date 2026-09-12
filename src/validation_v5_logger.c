#include "ecu_types.h"
#include "safety_policy_v5.h"
void validation_v5_csv_header(ecu_state_t *s)
{
    if (!s->safety_policy_v5_config.enabled) return;
    fputs(",v5_policy,scheduler_stress_enabled,scheduler_queue_count,scheduler_max_queue,scheduler_release_count,scheduler_completion_count,scheduler_rejected_count,scheduler_late_jobs,scheduler_first_violation_ms,scheduler_minimum_completion_margin_ms,scheduler_last_nominal_release_ms,scheduler_last_actual_release_ms,scheduler_last_start_ms,scheduler_last_completion_ms,scheduler_last_release_jitter_ms,scheduler_last_execution_duration_ms",s->log_file);
}
void validation_v5_csv_row(const ecu_state_t *s)
{
    if (!s->safety_policy_v5_config.enabled) return;
    static const char *policies[]={"observe_only","immediate","graded"};
    fprintf(s->log_file,",%s,%d",policies[s->safety_policy_v5_config.mode],s->scheduler_stress_config.enabled);
    if (!s->scheduler_stress_config.enabled) { for (int i=0;i<14;i++) fputc(',',s->log_file);return; }
    const scheduler_stress_state_t *v=&s->scheduler_stress;
    fprintf(s->log_file,",%u,%u,%u,%u,%u,%u,",v->count,v->max_queue,v->releases,v->completions,v->rejected,v->late_jobs);
    if (v->first_violation>=0) fprintf(s->log_file,"%d",v->first_violation);
    fputc(',',s->log_file);
    if (v->completions) fprintf(s->log_file,"%d",v->minimum_margin);
    if (v->last_completion<0) { for (int i=0;i<6;i++) fputc(',',s->log_file);return; }
    fprintf(s->log_file,",%u,%u,%u,%d,%u,%u",v->last_nominal,v->last_available,v->last_start,v->last_completion,v->last_jitter,v->last_duration);
}
