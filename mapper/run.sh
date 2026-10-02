#!/bin/bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 <benchmark_name> [all|cocotb|sdk|legacy]"
    echo "Example: $0 add cocotb"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BENCHMARK_NAME="$1"
OUTPUT_TYPE="${2:-all}"
DFG_FILE="$SCRIPT_DIR/../benchmarks/$BENCHMARK_NAME/affine.json"
SPEC_DIR="$SCRIPT_DIR/../hardware/verilog/lingo-spec"



if [ ! -f "$DFG_FILE" ]; then
    echo "DFG not found: $DFG_FILE"
    exit 1
fi


OLD_PATH="$PATH"
export PATH="$(pwd)/../oss-cad-suite/bin/":$PATH


# conda run -n lora "$SCRIPT_DIR/build/mapperPro" SPDLOG_LEVEL=off \
"$SCRIPT_DIR/build/mapperPro" SPDLOG_LEVEL=off \
    -c true -m true -o true \
    -t 6000000 \
    -i 15 \
    -q true \
    -v false \
    -C false \
    -e "$OUTPUT_TYPE" \
    -p "$SPEC_DIR/operations.json" \
    -a "$SPEC_DIR/lingo_adg.json" \
    -d "$DFG_FILE"

dot -Tpng ../benchmarks/${BENCHMARK_NAME}/mapped_dfg.dot -o ../benchmarks/${BENCHMARK_NAME}/mapped_dfg.png


export PATH="$OLD_PATH"
unset OLD_PATH
