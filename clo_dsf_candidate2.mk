# Additive v7.1 build; GNUmakefile and every Candidate 1 source remain untouched.
C2_SRC := $(wildcard src/v7_1/*.c)
C2_OBJ := $(C2_SRC:.c=.o)
C2_DEP := $(C2_OBJ:.o=.d)
all: virtual_ecu_v7_1
virtual_ecu_v7_1: $(filter-out src/main.o,$(OBJ)) $(C2_OBJ) src/v7/ds_evidence.o src/v7/clo_observability.o src/v7/clo_dsf.o src/v7/accepted_main.o
	$(CC) $^ -Wl,--wrap=detection_algorithm_step -o $@ $(LDFLAGS)
.PHONY: clean-candidate2
clean: clean-candidate2
clean-candidate2:
	rm -f $(C2_OBJ) $(C2_DEP) virtual_ecu_v7_1
-include $(C2_DEP)
