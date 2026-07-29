CC := gcc
CFLAGS := -std=c11 -Wall -Wextra -Wpedantic -Iinclude -O2 -MMD -MP
LDFLAGS :=

TARGET := virtual_ecu
SRC := $(wildcard src/*.c)
OBJ := $(SRC:.c=.o)
DEP := $(OBJ:.o=.d)

.PHONY: all clean run recommended-study paper-bundle rtl-trojan-study

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CC) $(OBJ) -o $@ $(LDFLAGS)

src/%.o: src/%.c
	$(CC) $(CFLAGS) -c $< -o $@

run: $(TARGET)
	./$(TARGET)

recommended-study: $(TARGET)
	python3 scripts/run_recommended_study.py

paper-bundle: recommended-study

rtl-trojan-study: $(TARGET)
	python3 scripts/run_rtl_hardware_trojan_study.py

clean:
	rm -f $(OBJ) $(DEP) $(TARGET)

-include $(DEP)
