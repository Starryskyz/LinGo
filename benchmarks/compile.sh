#!/usr/bin/env bash
set -euo pipefail

# Usage: from a benchmark subdir, e.g. benchmarks/add
#   ../compile.sh <prog_name> <kernel_fn>
# Example:
#   cd benchmarks/add && ../compile.sh add kernel
export PATH=/data/jrzhang/auforapro/llvm-project/build/bin:$PATH
PROG_NAME=${1:-add}
KERNEL_FN=${2:-kernel}

# Resolve paths relative to this script so it works from subdirs
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PASS_SO="${SCRIPT_DIR}/../app-compiler/build/llvm-pass/libCDFGPass.so"

# IR filenames in the current working directory (the benchmark folder)
IR0="${PROG_NAME}.ll"
IR1="${PROG_NAME}_gvn.ll"
IR2="${PROG_NAME}_cdfg.ll"

# Compile C to LLVM IR
clang-15 -D CGRA_COMPILER -target i386-unknown-linux-gnu -c -emit-llvm -O2 \
   -mprefer-vector-width=1 -fno-vectorize -fno-tree-vectorize -fno-unroll-loops -fno-discard-value-names  -ffreestanding "${PROG_NAME}.c" -S -o "${IR0}"

# Run standard scalar/loop optimizations (legacy PM style flags)
opt -mem2reg -memdep -memcpyopt -lcssa -loop-simplify -licm \
  -loop-deletion -indvars -loop-simplifycfg -simplifycfg -mergereturn -indvars --div-rem-pairs --disable-loop-unrolling --lowerswitch \
  -gvn \
  "${IR0}" -S -o "${IR1}"

# Load custom CDFG pass and run it using the legacy pass manager
# Note: --enable-new-pm=0 is required for -load/-cdfg style usage on LLVM 15
opt --enable-new-pm=0 -load "${PASS_SO}" -fn "${KERNEL_FN}" -cdfg \
  "${IR1}" -S -o "${IR2}"

echo "Generated ${IR2}"
