/* The frozen reference body is compiled unchanged with exact helper substitutions.
 * No thresholds, mappings, mass/state operations or fold order are duplicated. */
#include "clo_final_sparse_math.h"
#define clo_final_init clo_final_optimized_init_internal
#define clo_final_config_valid clo_final_optimized_config_valid_internal
#define clo_final_diagnostic clo_final_optimized_diagnostic_internal
#define clo_final_step clo_final_optimized_step
#define ds_combine final_sparse_combine
#define c2_origin_betp final_cached_betp
#include "clo_dsf_final.c"
