#!/usr/bin/env python3
"""独立生成 LinGo 输入规格；只依赖 Python 标准库，不读取旧 JSON 作为模板。

主要修改入口：PE_PROFILES、CURRENT_PE_LAYOUT、Architecture 和 make_architecture。
默认输出保留当前 JSON 的字段顺序、空格、CRLF 和无末尾换行格式。
完整使用方法和硬件限制见 generate_fgra_spec.md。
"""

import argparse
from copy import deepcopy
from dataclasses import dataclass, field
import json
from pathlib import Path
import sys


DEFAULT_OUTPUT = Path(__file__).resolve().parent / "src/main/resources/fgra_spec.json"

# 操作顺序也决定生成文件的字节内容；不要用 set 排序或去重。
INTEGER_OPS = [
    "PASS", "ADD", "SUB", "ULE", "ULT", "UGE", "UGT", "SLT", "SGE", "SGT",
    "SLE", "AND", "OR", "XOR", "XNOR", "NE", "EQ", "MUL", "SHL", "LSHR",
    "ASHR", "CSHL", "CSHR", "SEL",
]
FLOAT_CONVERSION_OPS = ["FMAX", "FMIN", "FPTOSI", "SITOFP"]


def pe(mode, operations, lut=0, delay_cg=16, delay_fg=8):
    """创建 PE 模板。mode: 0=普通 GPE，1=Unified，2=XCore。"""
    return {
        "max_delay_cg": delay_cg,
        "max_delay_fg": delay_fg,
        "num_input_lut": lut,
        "gpe_mode": mode,
        "operations": list(operations),
    }


PE_PROFILES = {
    "basic": pe(0, INTEGER_OPS + FLOAT_CONVERSION_OPS + ["FCMP", "FMUL", "FADDSUB"]),
    "unified": pe(1, ["FMUL", "FADDSUB"]),
    "xcore": pe(2, ["XCORE"]),
    "acc": pe(0, INTEGER_OPS + ["ACC", "ISEL"] + FLOAT_CONVERSION_OPS
              + ["FMUL", "FADDSUB", "FACC"], lut=2),
    "div_mul": pe(0, INTEGER_OPS + FLOAT_CONVERSION_OPS
                  + ["FMUL", "FADDSUB", "FDIV"], lut=2),
    "div": pe(0, INTEGER_OPS + FLOAT_CONVERSION_OPS + ["FADDSUB", "FDIV"], lut=2),
}

# 坐标均为零起始 [row][column]；布局的尺寸直接决定阵列尺寸。
CURRENT_PE_LAYOUT = [
    ["basic",   "basic",   "basic", "basic",   "basic",   "basic"],
    ["unified", "unified", "xcore", "unified", "unified", "unified"],
    ["acc",     "acc",     "acc",   "acc",     "acc",     "acc"],
    ["basic",   "unified", "unified", "xcore", "unified", "basic"],
    ["div_mul", "div",     "div",   "div",     "div",     "div_mul"],
    ["basic",   "basic",   "basic", "basic",   "basic",   "basic"],
]

# 保持原 JSON 字段顺序。None 是 build_spec 自动生成的布局/派生参数。
# lg_* 表示 log2 位数：例如 bank_lg_size=12 对应每个 bank 4096 字节。
# 全局 PE/IOB/GIB 默认值与逐实例值可不同；显式实例表优先。
SPEC_DEFAULTS = {
    "fgra_cfg_blk_offset": 6,
    "fgra_gib_track_reged_mode_cg": 1,
    "fgra_gpe_num_reg_rf_for_lut": 1,
    "ls_stream_queue_depth": 2,
    "spad_bank_lg_size": 12,
    "fgra_iob_lg_max_lat": 6,
    "fgra_cfg_sram_add_reg": False,
    "fgra_support_multiple_precision": False,
    "fgra_iob_sram_addr_width": None,
    "fgra_exe_lg_max_ii": 4,
    "logWidth": 32,
    "maxSeg": 6,
    "spad_data_width": 128,
    "system_bus_beat_bits": 128,
    "fgra_gpe_out_to_dir": [4, 5, 7, 6],  # NW, NE, SW, SE（保留当前顺序）
    "fgra_data_width": 32,
    "fgra_iob_sram_banks_coalesce": None,
    "fgra_gib_diag_iopin_connect_fg": True,
    "dma_lg_max_burst_size": 5,
    "rs_exe_queue_depth": 4,
    "operation_set_filename": "operations.json",
    "dumpOperationSet": True,
    "fgra_iob_lg_max_cycles": 13,
    "fgra_exe_lg_max_execute_cycles": 16,
    "rs_cmd_queue_depth": 16,
    "fgra_iobs": None,
    "fgra_iob_sram_add_reg": True,
    "fgra_gpe_num_input_lut": 0,
    "rs_store_queue_depth": 8,
    "fgra_max_delay_fg": 8,
    "fgra_gpe_fg_columns": None,
    "fgra_gpe_in_from_dir": [4, 5, 7, 6],
    "fgra_gib_diag_iopin_connect_cg": True,
    "fgra_iob_lg_max_stride": 11,
    "fgra_iob_has_io_fg": True,
    "tlb_num_ways": 32,
    "fgra_cfg_data_width": 32,
    "fgra_max_delay_cg": 4,
    "fgra_gpe_num_reg_rf_for_alu": 1,
    "fgra_num_row": None,
    "spad_cfg_lg_size": 12,
    "spad_addr_num": 5,
    "fgra_cg_gibs": None,
    "fgra_adg_filename": "fgra_adg.json",
    "id_width": 8,
    "fgra_num_colum": None,  # colum 是硬件已有字段名，不能改成 column。
    "fgra_fg_gibs": None,
    "dma_num_req_in_flight": 8,
    "tlb_is_shared": True,
    "fgra_iob_num_sides": 2,
    "fgra_iob_lg_max_ii": 4,
    "fgra_cfg_addr_width": 14,
    "fgra_exe_lg_max_loop_cycles": 10,
    "fgra_iob_mode": 3,
    "dumpADG": True,
    "fgra_gib_num_track_fg": 1,
    "rs_load_queue_depth": 8,
    "fgra_gib_connect_flexibility_cg": {
        "num_otrack_per_opin": 4, "num_itrack_per_ipin": 2, "num_ipin_per_opin": 4,
    },
    "fgra_iob_sram_has_mask": True,
    "fgra_gib_connect_flexibility_fg": {
        "num_otrack_per_opin": 4, "num_itrack_per_ipin": 2, "num_ipin_per_opin": 4,
    },
    "fgra_gpe_fg_rows": None,
    "fgra_gib_track_reged_mode_fg": 1,
    "fgra_gpes": None,
    "fgra_cfg_addr_width_align": 16,
    # 全局 fallback 不含 SEL，且 MUL 放在末尾；与 basic 模板不同。
    "fgra_gpe_operations": [op for op in INTEGER_OPS if op not in ("MUL", "SEL")] + ["MUL"],
    "spad_num_banks": None,
    "fgra_gib_num_track_cg": 1,
    "fgra_iob_ag_nest_levels": 3,
}


@dataclass
class Architecture:
    """Python 架构接口；每个实例均拥有独立可修改的配置副本。

    pe_layout: 二维模板名或完整 PE 字典。
    parameters: 全局字段覆盖；尺寸和地址宽度等派生字段禁止直接覆盖。
    *_overrides: {(row, col): {要覆盖的字段: 值}}。
    IOB 的 row 表示 side，0=上侧、1=下侧；CG GIB 坐标是网格交点，
    FG GIB 坐标对应筛选后的 FG 行列网格交点。
    """
    pe_layout: list = field(default_factory=lambda: deepcopy(CURRENT_PE_LAYOUT))
    pe_profiles: dict = field(default_factory=lambda: deepcopy(PE_PROFILES))
    parameters: dict = field(default_factory=dict)
    pe_overrides: dict = field(default_factory=dict)
    iob_template: dict = field(default_factory=lambda: {
        "iob_mode": 2, "has_io_fg": True, "max_delay_cg": 2, "max_delay_fg": 2,
    })
    iob_overrides: dict = field(default_factory=dict)
    # None 表示按全局 diag 和 flexibility 自动生成；当前实例 fclist=[2,2,2]
    # 与全局 flexibility=[2,4,4] 不同，必须独立保留，不能相互替换。
    cg_gib_template: dict = field(default_factory=lambda: {
        "diag_iopin_connect": True, "fclist": [2, 2, 2],
    })
    fg_gib_template: dict = field(default_factory=lambda: {
        "diag_iopin_connect": True, "fclist": [2, 2, 2],
    })
    cg_gib_overrides: dict = field(default_factory=dict)
    fg_gib_overrides: dict = field(default_factory=dict)


def make_architecture():
    """日常修改入口。默认保持原架构；修改示例见配套说明。"""
    return Architecture()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rectangular_shape(grid, name):
    require(isinstance(grid, list) and len(grid) > 0, f"{name} 不能为空")
    require(isinstance(grid[0], list) and len(grid[0]) > 0, f"{name} 行不能为空")
    cols = len(grid[0])
    require(all(isinstance(row, list) and len(row) == cols for row in grid),
            f"{name} 必须是矩形二维列表")
    return len(grid), cols


def apply_overrides(grid, overrides, name):
    rows, cols = rectangular_shape(grid, name)
    for coordinate, changes in overrides.items():
        require(isinstance(coordinate, tuple) and len(coordinate) == 2,
                f"{name} 覆盖坐标必须为 (row, col)")
        r, c = coordinate
        require(type(r) is int and type(c) is int and 0 <= r < rows and 0 <= c < cols,
                f"{name} 覆盖坐标越界: {coordinate}")
        require(isinstance(changes, dict) and not (changes.keys() - grid[r][c].keys()),
                f"{name}{coordinate} 包含未知字段")
        grid[r][c].update(deepcopy(changes))


def repeated_grid(rows, cols, template, overrides, name):
    grid = [[deepcopy(template) for _ in range(cols)] for _ in range(rows)]
    apply_overrides(grid, overrides, name)
    return grid


def build_spec(architecture=None):
    """从 Python 配置构建全新的 JSON 对象，不修改输入对象。"""
    arch = architecture if architecture is not None else make_architecture()
    rows, cols = rectangular_shape(arch.pe_layout, "pe_layout")
    spec = deepcopy(SPEC_DEFAULTS)
    derived = {"fgra_num_row", "fgra_num_colum", "spad_num_banks",
               "fgra_iob_sram_addr_width", "fgra_gpes", "fgra_iobs",
               "fgra_cg_gibs", "fgra_fg_gibs"}
    require(not (arch.parameters.keys() - spec.keys()), "parameters 包含未知字段")
    require(not (arch.parameters.keys() & derived), "请通过布局/模板修改派生字段，而非 parameters")
    spec.update(deepcopy(arch.parameters))
    spec["fgra_num_row"], spec["fgra_num_colum"] = rows, cols
    require(spec["fgra_iob_num_sides"] == 2, "当前硬件只支持上下两侧 IOB，请保留 num_sides=2")
    spec["spad_num_banks"] = 2 * cols
    coalesce = spec["fgra_iob_sram_banks_coalesce"]
    if coalesce is None:
        coalesce = cols  # 默认每侧全部 bank 合并为一组。
    require(type(coalesce) is int and coalesce > 0 and cols % coalesce == 0,
            "coalesce 必须为正整数且整除每侧列数")
    spec["fgra_iob_sram_banks_coalesce"] = coalesce
    bank_lg_size = spec["spad_bank_lg_size"]
    require(type(bank_lg_size) is int and bank_lg_size >= 0, "bank_lg_size 必须为非负整数")
    spec["fgra_iob_sram_addr_width"] = bank_lg_size + (coalesce - 1).bit_length()
    if spec["fgra_gpe_fg_rows"] is None:
        spec["fgra_gpe_fg_rows"] = list(range(rows))
    if spec["fgra_gpe_fg_columns"] is None:
        spec["fgra_gpe_fg_columns"] = list(range(cols))

    gpes = []
    for r, row in enumerate(arch.pe_layout):
        gpes.append([])
        for c, entry in enumerate(row):
            if isinstance(entry, str):
                require(entry in arch.pe_profiles, f"PE({r},{c}) 未知模板: {entry}")
                entry = arch.pe_profiles[entry]
            require(isinstance(entry, dict), f"PE({r},{c}) 必须是模板名或字典")
            gpes[-1].append(deepcopy(entry))
    apply_overrides(gpes, arch.pe_overrides, "PE")
    spec["fgra_gpes"] = gpes
    spec["fgra_iobs"] = repeated_grid(2, cols, arch.iob_template, arch.iob_overrides, "IOB")
    for grain, template, overrides in (
        ("cg", arch.cg_gib_template, arch.cg_gib_overrides),
        ("fg", arch.fg_gib_template, arch.fg_gib_overrides),
    ):
        if template is None:
            flex = spec[f"fgra_gib_connect_flexibility_{grain}"]
            template = {
                "diag_iopin_connect": spec[f"fgra_gib_diag_iopin_connect_{grain}"],
                "fclist": [flex["num_itrack_per_ipin"], flex["num_otrack_per_opin"],
                           flex["num_ipin_per_opin"]],
            }
        gib_rows = rows if grain == "cg" else len(spec["fgra_gpe_fg_rows"])
        gib_cols = cols if grain == "cg" else len(spec["fgra_gpe_fg_columns"])
        spec[f"fgra_{grain}_gibs"] = repeated_grid(gib_rows + 1, gib_cols + 1, template, overrides,
                                                   f"{grain.upper()} GIB")
    validate_spec(spec)
    return spec


def validate_spec(spec):
    """基本结构与已知硬件限制校验；不替代 Chisel elaboration/路由验证。"""
    rows, cols = spec["fgra_num_row"], spec["fgra_num_colum"]
    for key, shape in (("fgra_gpes", (rows, cols)), ("fgra_iobs", (2, cols)),
                       ("fgra_cg_gibs", (rows + 1, cols + 1)),
                       ("fgra_fg_gibs", (len(spec["fgra_gpe_fg_rows"]) + 1,
                                          len(spec["fgra_gpe_fg_columns"]) + 1))):
        require(rectangular_shape(spec[key], key) == shape, f"{key} 尺寸不匹配")
    for key, limit in (("fgra_gpe_fg_rows", rows), ("fgra_gpe_fg_columns", cols)):
        indices = spec[key]
        require(isinstance(indices, list) and all(type(x) is int and 0 <= x < limit for x in indices),
                f"{key} 索引越界")
        require(indices == sorted(set(indices)), f"{key} 必须递增且不能重复")
    require(spec["spad_data_width"] == spec["system_bus_beat_bits"],
            "spad_data_width 必须等于 system_bus_beat_bits")
    for key in ("spad_data_width", "fgra_data_width", "fgra_cfg_data_width"):
        width = spec[key]
        require(type(width) is int and width > 0 and width % 8 == 0,
                f"{key} 必须是正的整字节位宽")
    require(spec["spad_data_width"] % spec["fgra_data_width"] == 0,
            "SPM 位宽必须为阵列数据位宽的整数倍")
    require(spec["fgra_gpe_num_reg_rf_for_alu"] == 1, "当前 PE 要求 num_reg_rf_for_alu=1")
    require(type(spec["fgra_cfg_blk_offset"]) is int and
            type(spec["fgra_cfg_addr_width"]) is int and
            0 <= spec["fgra_cfg_blk_offset"] < spec["fgra_cfg_addr_width"],
            "cfg_blk_offset 必须小于 cfg_addr_width")
    for r, row in enumerate(spec["fgra_gpes"]):
        for c, cell in enumerate(row):
            require(cell.keys() == PE_PROFILES["basic"].keys(), f"PE({r},{c}) 字段不完整或有未知字段")
            ops, mode = cell["operations"], cell["gpe_mode"]
            require(type(mode) is int and mode in (0, 1, 2), f"PE({r},{c}) mode 必须为 0/1/2")
            require(isinstance(ops, list) and ops and all(isinstance(op, str) for op in ops),
                    f"PE({r},{c}) operations 必须是非空字符串列表")
            for key in ("max_delay_cg", "max_delay_fg", "num_input_lut"):
                require(type(cell[key]) is int and cell[key] >= 0, f"PE({r},{c}) {key} 必须为非负整数")
            if mode == 1:
                require("FDIV" not in ops and not ("FMUL" in ops and "MUL" in ops),
                        f"Unified PE({r},{c}) 不支持 FDIV 或同时包含 FMUL/MUL")
            if mode == 2:
                require(ops == ["XCORE"], f"XCore PE({r},{c}) operations 应为 ['XCORE']")
    for row in spec["fgra_iobs"]:
        for cell in row:
            require(cell.keys() == {"iob_mode", "has_io_fg", "max_delay_cg", "max_delay_fg"},
                    "IOB 字段不完整或有未知字段")
            require(type(cell["iob_mode"]) is int and cell["iob_mode"] in (1, 2, 3),
                    "IOB mode 必须为 1(FIFO)/2(SRAM)/3(TASK_COND_EXIT)")
            require(type(cell["has_io_fg"]) is bool, "IOB has_io_fg 必须为 bool")
            require(all(type(cell[k]) is int and cell[k] >= 0 for k in ("max_delay_cg", "max_delay_fg")),
                    "IOB delay 必须为非负整数")
    for grain in ("cg", "fg"):
        for row in spec[f"fgra_{grain}_gibs"]:
            for cell in row:
                require(cell.keys() == {"diag_iopin_connect", "fclist"}, "GIB 字段不完整或有未知字段")
                require(type(cell["diag_iopin_connect"]) is bool, "GIB diag_iopin_connect 必须为 bool")
                fc = cell["fclist"]
                require(isinstance(fc, list) and len(fc) == 3 and
                        all(type(x) is int and x >= 0 for x in fc), "GIB fclist 必须包含三个非负整数")


def _inline(value, tight_end=False):
    if isinstance(value, list):
        return "[ " + ", ".join(json.dumps(x, ensure_ascii=False) for x in value) + ("]" if tight_end else " ]")
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def render_spec(spec):
    """兼容当前输入文件的格式；返回 bytes，以避免平台自动转换换行。"""
    def cell_text(cell):
        return ",\n".join("    " + json.dumps(k) + " : " + _inline(v, k == "operations")
                           for k, v in cell.items())

    def matrix_text(matrix):
        return "[ [ {\n" + "\n  }],[ {\n".join(
            "\n  },{\n".join(cell_text(cell) for cell in row) for row in matrix
        ) + "\n  }]]"

    lines = []
    for key, value in spec.items():
        if key in ("fgra_gpes", "fgra_iobs", "fgra_cg_gibs", "fgra_fg_gibs"):
            rendered = matrix_text(value)
        elif isinstance(value, dict):
            rendered = "{\n" + cell_text(value) + "\n  }"
        else:
            rendered = _inline(value, key in ("fgra_gpe_fg_rows", "fgra_gpe_fg_columns"))
        lines.append("  " + json.dumps(key) + " : " + rendered)
    return ("{\n" + ",\n".join(lines) + "\n}").replace("\n", "\r\n").encode("utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT, help="输出路径（默认硬件输入规格）")
    parser.add_argument("--check", type=Path, metavar="JSON", help="只比较指定文件，不写入任何文件")
    parser.add_argument("--rows", type=int, help="同构阵列行数，须同时指定 --cols 和 --pe-profile")
    parser.add_argument("--cols", type=int, help="同构阵列列数")
    parser.add_argument("--pe-profile", choices=sorted(PE_PROFILES), help="生成同构阵列所用模板")
    parser.add_argument("--force", action="store_true", help="允许覆盖内容不同的已有输出文件")
    args = parser.parse_args(argv)
    arch = make_architecture()
    if any(x is not None for x in (args.rows, args.cols, args.pe_profile)):
        if not (args.rows is not None and args.cols is not None and args.pe_profile is not None):
            parser.error("同构阵列必须同时指定 --rows、--cols、--pe-profile")
        if args.rows <= 0 or args.cols <= 0:
            parser.error("rows 和 cols 必须为正整数")
        arch.pe_layout = [[args.pe_profile for _ in range(args.cols)] for _ in range(args.rows)]
    try:
        spec = build_spec(arch)
        generated = render_spec(spec)
        if args.check:
            existing = args.check.read_bytes()
            if existing == generated:
                print(f"PASS: 逐字节一致 ({len(generated)} bytes): {args.check}")
                return 0
            if json.loads(existing) == spec:
                print("FAIL: JSON 内容一致，但格式/字段顺序/换行不同", file=sys.stderr)
            else:
                print("FAIL: JSON 内容不同", file=sys.stderr)
            return 1
        if args.output.exists() and args.output.read_bytes() != generated and not args.force:
            raise ValueError(f"输出文件已有不同内容: {args.output}；请选择新路径或显式使用 --force")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(generated)
        print(f"已生成 {spec['fgra_num_row']}×{spec['fgra_num_colum']} PE, "
              f"{spec['spad_num_banks']} IOB: {args.output}")
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.exit(2, f"错误: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
