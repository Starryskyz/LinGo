#!/bin/bash
# set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# conda run -n lora cmake -S "$SCRIPT_DIR" -B "$SCRIPT_DIR/build" -G Ninja
# conda run -n lora cmake --build "$SCRIPT_DIR/build"


cmake -S "$SCRIPT_DIR" -B "$SCRIPT_DIR/build" -G Ninja
cmake --build "$SCRIPT_DIR/build"