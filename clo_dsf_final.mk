# Separate entry point preserves both historical build manifests byte-for-byte.
include GNUmakefile
FINAL_SRC := src/v7_2/clo_dsf_final.c src/v7_2/final_observation_io.c src/v7_2/final_runtime.c
FINAL_OBJ := $(FINAL_SRC:.c=.o)
FINAL_CORE_OBJ := src/v7/ds_evidence.o src/v7/clo_observability.o src/v7/clo_dsf.o src/v7_1/candidate2_evidence.o src/v7_1/candidate2_observability.o src/v7_1/clo_dsf_candidate2.o
all: virtual_ecu_v7_2_reference
virtual_ecu_v7_2_reference: $(filter-out src/main.o,$(OBJ)) $(FINAL_OBJ) $(FINAL_CORE_OBJ) src/v7/accepted_main.o
	$(CC) $^ -Wl,--wrap=detection_algorithm_step -o $@ $(LDFLAGS)
-include $(FINAL_OBJ:.o=.d)
