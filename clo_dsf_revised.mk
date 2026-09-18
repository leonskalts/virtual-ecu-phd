# Additive entry point; all historical build files remain unchanged.
include clo_dsf_final.mk
REVISED_OBJ := src/v7_3/clo_dsf_revised.o src/v7_3/revised_runtime.o
all: virtual_ecu_v7_3
virtual_ecu_v7_3: $(filter-out src/main.o,$(OBJ)) $(REVISED_OBJ) src/v7_2/clo_dsf_final.o src/v7_2/final_observation_io.o $(FINAL_CORE_OBJ) src/v7/accepted_main.o
	$(CC) $^ -Wl,--wrap=detection_algorithm_step -o $@ $(LDFLAGS) -lm
-include $(REVISED_OBJ:.o=.d)
