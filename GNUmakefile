# Preserve the accepted build verbatim; v7 links into its detector call boundary.
include Makefile
V7_SRC := $(wildcard src/v7/*.c)
V7_OBJ := $(V7_SRC:.c=.o)
V7_DEP := $(V7_OBJ:.o=.d)
V7_CORE := src/v7/ds_evidence.c src/v7/clo_observability.c src/v7/clo_dsf.c
.PHONY: clo-dsf-test
all: virtual_ecu_v7
src/v7/accepted_main.o: src/main.c
	$(CC) $(CFLAGS) -Dmain=clo_accepted_main -c $< -o $@
virtual_ecu_v7: $(filter-out src/main.o,$(OBJ)) $(V7_OBJ) src/v7/accepted_main.o
	$(CC) $^ -Wl,--wrap=detection_algorithm_step -o $@ $(LDFLAGS)
clo-dsf-test:
	python3 -m unittest discover -s tests -p 'test_clo_dsf*.py' -v
-include $(V7_DEP)
.PHONY: clean-v7
clean: clean-v7
clean-v7:
	rm -f $(V7_OBJ) $(V7_DEP) src/v7/accepted_main.o src/v7/accepted_main.d virtual_ecu_v7
