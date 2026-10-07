"""
Copyright (c) 2026 LinGo
All rights reserved.
"""


import os
import logging
import numpy as np
import itertools
import logging
import random

import cocotb

# from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb.regression import TestFactory
from cocotb.utils import get_sim_time


from test_runif import (
    DeviceInfo,
    DeviceData,
    DeviceConfig,
    DeviceStream,
    DeviceRuntime,
    Axi4LiteTb,
)
import test_runif

tests_dir = os.path.dirname(__file__)




## ================================
## Import from kernel function py
## ================================
from example import example

# ==============================
# Main cocotb coroutine
# ==============================
async def cgra_run_top_example(dut) -> None:
    # Reset DUT
    axibus = Axi4LiteTb(dut)
    await axibus.cycle_reset()
    axibus.log.info("[CGRA] Starting CGRA kernel test (intvecadd)")

    # set log level
    logging.getLogger("cocotb.test_cgra.axi").disabled = True
    logging.getLogger("cocotb.test_cgra.axil").disabled = True

    ## ================================
    ## prepare input data and golden result for example kernel
    ## ================================
    x=np.random.randint(0, 20, size=(8,8), dtype=np.int32)
    y=np.random.randint(0, 20, size=(8,8), dtype=np.int32)
    o=np.zeros((8,8), dtype=np.int32)
    oc=np.zeros((8,8), dtype=np.int32)
    for i in range(0,8):
        for j in range(0,8):
            sum = 0 
            for k in range(0,8):
                sum += x[i][k]*y[k][j]
            o[i][j] = 3*sum+2*o[i][j]


    base_dir = os.path.dirname(os.path.abspath(__file__))
    reg_json_path = os.path.join(base_dir, "../circuits/axilite_spec.json")
    adg_json_path = os.path.join(base_dir, "../circuits/lingo_cgra_adg.json")
    device1 = test_runif.create_device_info_factory(
        reg_json_path=reg_json_path, adg_json_path=adg_json_path
    )

    runtime = DeviceRuntime(
        dut=dut,
        axi=axibus.axi,
        axil=axibus.axil,
        axi_size=axibus.axi.write_if.max_burst_size,
    )

    runtime.add_device(device1)

    # Start kernel execution
    start_time = get_sim_time(units="ns")
    
    ## ================================
    ## call the example kernel function
    ## ================================
    await example(runtime, x, y, oc)
    
    await runtime.synchronize_all()
    await RisingEdge(dut.clk)

    end_time = get_sim_time(units="ns")
    axibus.log.info(f"Sim time: {end_time - start_time} ns")

    ## ================================
    ## check the result
    ## ================================

    for i in range(0,8):
        for j in range(0,8):
            if oc[i][j] != o[i][j]:
                assert False, f"Mismatch at ({i}, {j}): {oc[i][j]} != {o[i][j]}"




# ==============================
# TestFactory registration
# ==============================
if cocotb.SIM_NAME:
    cgra_run_top = cgra_run_top_example
    factory = TestFactory(cgra_run_top)
    factory.generate_tests()

