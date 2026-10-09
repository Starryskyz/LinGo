COCOTB_RESOLVE_X ?= ZEROS
export COCOTB_RESOLVE_X

TOPLEVEL_LANG = verilog

SIM ?= verilator

# VERILATOR_BIN_DIR ?= $(abspath ../oss-cad-suite/bin)
# VERILATOR_BIN_DIR ?= $(abspath ../verilator/bin)
# VERILATOR_BIN_DIR ?= $(abspath ../../CGRA-SoC/verilator/bin)
WAVES ?= 0

COCOTB_HDL_TIMEUNIT = 1ns
COCOTB_HDL_TIMEPRECISION = 1ns

DUT      = test_cgra
CGRA     = LinGoWithAXI
TOPLEVEL = $(DUT)
MODULE   = $(DUT)

VERILOG_SOURCES += $(PWD)/circuits/$(DUT).v $(PWD)/circuits/$(CGRA).v
# VERILOG_SOURCES += $(DUT).v $(CGRA).v


# axi4 module parameters
export PARAM_DATA_WIDTH := 128
export PARAM_ADDR_WIDTH := 19
export PARAM_STRB_WIDTH := $(shell expr $(PARAM_DATA_WIDTH) / 8)
export PARAM_ID_WIDTH := 6

export PARAM_AWUSER_WIDTH := 1
export PARAM_WUSER_WIDTH := 1
export PARAM_BUSER_WIDTH := 1
export PARAM_ARUSER_WIDTH := 1
export PARAM_RUSER_WIDTH := 1

#axil parameters
export PARAM_AXIL_DATA_WIDTH := 32
export PARAM_AXIL_ADDR_WIDTH := 10
export PARAM_AXIL_STRB_WIDTH := $(shell expr $(PARAM_AXIL_DATA_WIDTH) / 8)

ifeq ($(SIM),icarus)

    COMPILE_ARGS += $(foreach v,$(filter PARAM_%,$(.VARIABLES)), \
        -P $(TOPLEVEL).$(subst PARAM_,,$(v))=$($(v)))



else ifeq ($(SIM),verilator)
#     ifneq ($(filter default undefined,$(origin CXX)),)
#         CXX := $(or $(wildcard $(abspath ../llvm-project/install/bin/clang++)),clang++)
#     endif
#     BUILD_ARGS ?= CXX=$(CXX) OPT_FAST=-O2 OPT_SLOW=-O2

    EXTRA_ARGS += -Wno-SELRANGE
    EXTRA_ARGS += -Wno-WIDTH
    EXTRA_ARGS += -Wno-CASEINCOMPLETE
#     EXTRA_ARGS += -Wno-fatal ###

    EXTRA_ARGS += $(foreach v,$(filter PARAM_%,$(.VARIABLES)), \
        -G$(subst PARAM_,,$(v))=$($(v)))

    EXTRA_ARGS += --threads 16
    EXTRA_ARGS += --build-jobs 16

    ifeq ($(WAVES),1)
        EXTRA_ARGS += --trace
        EXTRA_ARGS += --trace-fst
        EXTRA_ARGS += --trace-structs
    endif

endif

include $(shell cocotb-config --makefiles)/Makefile.sim

clean::
	@rm -rf sim_build
	@rm -f dump.fst
	@rm -f dump.vcd
	@rm -f $(TOPLEVEL).fst
	@rm -f results.xml