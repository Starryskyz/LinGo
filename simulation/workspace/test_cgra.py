"""
Copyright (c) 2025 CGRA
All rights reserved.

This module contains a cocotb testbench for running a CGRA kernel with pytest

"""

###########
## Import from cocotb
###########
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

# from cocotbext.axi import AxiBus, AxiMaster, AxiLiteBus, AxiLiteMaster, AxiRam

## set path for  cgra_test_pylib
from test_runif import (
    DeviceInfo,
    DeviceData,
    DeviceConfig,
    DeviceStream,
    DeviceRuntime,
    Axi4LiteTb,
)
import test_runif

## ================================
## Import from kernel function py
## ================================
# @zwzhong
# from IntVecAdd import IntVecAdd
from gemm import gemm
from luttest import luttest
from sqrt import sqrt
from exp import exp
# from fir import fir


tests_dir = os.path.dirname(__file__)


# ==============================
# Main cocotb coroutine
# ==============================
# def random_init_i16(shape, low=0, high=30):
#     return np.random.randint(low, high + 1, size=shape, dtype=np.int16)


# def zero_init_i16(shape):
#     return np.zeros(shape, dtype=np.int16)


def ri32(shape, low=0, high=1000):
    return np.random.randint(low, high + 1, size=shape, dtype=np.int32)


def zi32(shape):
    return np.zeros(shape, dtype=np.int32)

# ==============================
# Main cocotb coroutine
# ==============================
async def cgra_run_top_intvecadd(dut) -> None:
    """
    Run a CGRA kernel test.

    Args:
        dut: cocotb DUT object (Design Under Test).
    """
    # Reset DUT
    axibus = Axi4LiteTb(dut)
    await axibus.cycle_reset()
    axibus.log.info("[CGRA] Starting CGRA kernel test (intvecadd)")

    # set log level
    # axibus.log.setLevel(logging.WARNING)
    logging.getLogger("cocotb.test_cgra.axi").disabled = True
    logging.getLogger("cocotb.test_cgra.axil").disabled = True
    # logging.getLogger("test_runif").setLevel(logging.DEBUG)

    # gemm test prepare begin
    x=ri32((8,8))
    y=ri32((8,8))
    o=zi32((8,8))
    oc=zi32((8,8))
    for i in range(0,8):
        for j in range(0,8):
            sum = 0 
            for k in range(0,8):
                sum += x[i][k]*y[k][j]
            o[i][j] = 3 *sum+2*o[i][j]

    # gemm end

    ## luttest prepare begin

    c1=zi32(20)
    c2=zi32(20)
    a=zi32(20)
    b=zi32(20)
    for i in range(0,20):
        a[i] = 3
        b[i] = 5
        if i > 10:
            c2[i] = a[i]
        elif i > 5:
            c2[i] = b[i]
        else:
            c2[i] = b[i] + 10

    ## luttest end

    ## sqrt/exp test prepare begin
    input= np.random.uniform(0.5, 4.0, size=16).astype(np.float32)
    output1= np.zeros(16, dtype=np.float32)
    output2= np.zeros(16, dtype=np.float32)
    for i in range(0,16):
        # output1[i] = np.sqrt(input[i])
        output1[i] = np.exp(input[i])
        # output1[i] = -np.log(1.0 + np.exp(-input[i]))

    #  sqrt/exp test prepare end

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
    # await IntVecAdd(runtime, a, b, c)
    # await gemm(runtime, x, y, oc)
    await luttest(runtime, a, b, c1)
    # await sqrt(runtime, input, output2)
    # await exp(runtime, input, output2)
    

    await runtime.synchronize_all()
    await RisingEdge(dut.clk)



    end_time = get_sim_time(units="ns")
    axibus.log.info(f"Sim time: {end_time - start_time} ns")


    # for i in range(0,8):
    #     for j in range(0,8):
    #         if oc[i][j] != o[i][j]:
    #             print(f"Mismatch at ({i}, {j}): {oc[i][j]} != {o[i][j]}")
    


    for i in range(0,20):
        if c1[i] != c2[i]:
            print(f"Mismatch at ({i}): {c1[i]} != {c2[i]}")


    # for i in range(0,16):
    #     print(f"input: {input[i]}, output1: {output1[i]}, output2: {output2[i]}")
    #     print(f"abs_diff: {abs(output1[i] - output2[i])}")


    # for i in range(0,8):
    #     for j in range(0,8):
    #         abs_diff = abs(output1[i][j] - output2[i][j])
    #         if abs_diff > 1e-5:
    #             print(f"Mismatch at ({i}, {j}): {output1[i][j]} != {output2[i][j]}, abs_diff={abs_diff}")
    # print("Test completed successfully.")




# ==============================
# TestFactory registration
# ==============================
if cocotb.SIM_NAME:
    cgra_run_top = cgra_run_top_intvecadd
    factory = TestFactory(cgra_run_top)
    factory.generate_tests()

# if __name__ == "__main__":
#     cgra_run_top
