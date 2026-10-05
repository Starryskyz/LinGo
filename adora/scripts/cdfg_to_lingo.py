#!/usr/bin/env python3
"""ADORA DOT -> LinGo's Graphviz JSON, without importing either mapper."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def normalize(graph, operations=None):
    nodes = graph.get("objects", [])
    if not nodes:
        raise ValueError("CDFG contains no nodes")
    node_ids = {node["_gvid"] for node in nodes}
    for node in nodes:
        if "opcode" not in node:
            raise ValueError(f"Node {node.get('name')} has no opcode")
        node["opcode"] = node["opcode"].upper()
        if node["opcode"] in {"UNDEFINED", ""}:
            raise ValueError(f"Undefined opcode on {node['name']}")
        if node["opcode"] == "CONST":
            # LinGo uses std::stoull(value) with decimal base. Preserve the
            # integer/FP bit pattern; do not reinterpret it as a float.
            value = str(node["value"])
            if value.lower().startswith("0x"):
                node["value"] = str(int(value, 16))
        if "pattern" in node:
            pattern = node["pattern"].replace(" ", "").strip(",").split(",")
            if len(pattern) % 2 or not all(part for part in pattern):
                raise ValueError(f"Invalid stride/count pattern on {node['name']}")
    for edge in graph.get("edges", []):
        if edge["tail"] not in node_ids or edge["head"] not in node_ids:
            raise ValueError("CDFG edge references a missing node")
        if "operand" not in edge or int(edge["operand"]) < 0:
            raise ValueError(f"Invalid operand index on edge {edge['_gvid']}")
        # ADORA DOT encodes backedges and edge kinds as style/color.
        edge.setdefault("backedge", "1" if "dashed" in edge.get("style", "") else "0")
        color = edge.get("color", "black").lower()
        # LinGo enum: 0=data, 1=memory, 2=control.
        edge.setdefault("type", {"blue": "1", "red": "2"}.get(color, "0"))
        edge.setdefault("iterdist", "1")
        edge.setdefault("Width", "32" if edge["type"] == "0" else "1")
        edge.setdefault("tailport", "out0")
    if operations is not None:
        supported = {op["name"].upper() for op in operations["Operations"]}
        missing = sorted({node["opcode"] for node in nodes
                          if node["opcode"] != "CONST"} - supported)
        if missing:
            raise ValueError("LinGo operations.json does not support: " + ", ".join(missing))
    return graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="ADORA CDFG .dot")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--operations", type=Path,
                        help="Optional LinGo operations.json for opcode validation")
    args = parser.parse_args()
    result = subprocess.run(["dot", "-Tjson", str(args.input)],
                            check=True, capture_output=True, text=True)
    graph = json.loads(result.stdout)
    operations = json.loads(args.operations.read_text()) if args.operations else None
    normalize(graph, operations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(graph, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"CDFG conversion failed: {exc}", file=sys.stderr)
        sys.exit(1)
