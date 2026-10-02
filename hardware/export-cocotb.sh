#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
dest="${1:-$script_dir/../simulation/circuits}"
src="$script_dir/verilog/lingo-spec"

test -f "$script_dir/verilog/LinGoWithAXI.v"
test -d "$dest"
cp "$script_dir/verilog/LinGoWithAXI.v" "$dest/LinGoWithAXI.v"
cp "$src/axilite_spec.json" "$dest/axilite_spec.json"
cp "$src/lingo_adg.json" "$dest/lingo_cgra_adg.json"
cp "$src/operations.json" "$dest/operations.json"
cp "$src/lingo_spec.json" "$dest/lingo_spec.json"
