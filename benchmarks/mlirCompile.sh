#!/bin/bash

PROG_NAME=${1:-MLIRgemm}

OLD_PATH="$PATH"
export PATH="$(pwd)/../adora/build/bin/":$PATH
export PATH="$(pwd)/../Polygeist/build/bin/":$PATH


cgeist \
    -O2 \
    -lm -lgcc \
    --import-all-index \
    ./${PROG_NAME}/${PROG_NAME}.c \
    -S -o ./${PROG_NAME}/${PROG_NAME}.mlir

python3 ../adora/tools/adoracc/adoracc.py ./${PROG_NAME}/${PROG_NAME}.mlir --work-dir ./${PROG_NAME}/

dot -Tpng ./${PROG_NAME}/adora-cc-ir/2_dfgs/${PROG_NAME}_CDFG.dot -o ./${PROG_NAME}/${PROG_NAME}_CDFG.png

python3 ../adora/scripts/cdfg_to_lingo.py \
  ./${PROG_NAME}/adora-cc-ir/2_dfgs/${PROG_NAME}_CDFG.dot \
  -o ./${PROG_NAME}/affine.json \
  --operations ../hardware/verilog/lingo-spec/operations.json

export PATH="$OLD_PATH"
unset OLD_PATH

# /data/jrzhang/LinGo/adora/build/bin/cgra-opt   --allow-unregistered-dialect --adora-simplify-affine-loop-levels --canonicalize  -cse --adora-simplify-loadstore --adora-math-rewrite "--adora-adjust-kernel-mem-footprint=cachesize=128 singlearraysize=8 disable-remainder-block explicit-datablock" MLIRgemm.mlir -o out.mlir