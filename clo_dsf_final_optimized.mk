# Optimization-only extension; reference build and scientific hash remain intact.
include clo_dsf_final.mk
FINAL_OPT_OBJ := src/v7_2/clo_dsf_final_optimized.o src/v7_2/final_sparse_math.o src/v7_2/final_runtime_optimized.o
all: virtual_ecu_v7_2_optimized
src/v7_2/final_runtime_optimized.o: src/v7_2/final_runtime.c
	$(CC) $(CFLAGS) -Dclo_final_step=clo_final_optimized_step -c $< -o $@
virtual_ecu_v7_2_optimized: $(filter-out src/main.o,$(OBJ)) $(filter-out src/v7_2/final_runtime.o,$(FINAL_OBJ)) $(FINAL_OPT_OBJ) $(FINAL_CORE_OBJ) src/v7/accepted_main.o
	$(CC) $^ -Wl,--wrap=detection_algorithm_step -o $@ $(LDFLAGS)
-include $(FINAL_OPT_OBJ:.o=.d)
