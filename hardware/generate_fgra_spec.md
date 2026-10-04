# FGRA 架构规格生成器

`generate_fgra_spec.py` 用 Python 标准库独立构建输入规格，不依赖原 JSON、
Chisel、sbt 或第三方包。默认配置复现当前 `src/main/resources/fgra_spec.json`
的全部 68 个顶层字段、实例布局和原始格式，包括 CRLF、字段顺序、空格及无末尾换行。

## 运行

在仓库根目录运行：

```sh
# 只验证，不写文件：检查默认生成结果是否与当前规格逐字节一致
python3 hardware/generate_fgra_spec.py --check hardware/src/main/resources/fgra_spec.json

# 默认生成到 hardware/src/main/resources/fgra_spec.json
python3 hardware/generate_fgra_spec.py

# 建议新架构先写到新路径
python3 hardware/generate_fgra_spec.py -o /tmp/my_fgra_spec.json

# 快速生成 4 行 8 列、全部 basic PE 的同构阵列
python3 hardware/generate_fgra_spec.py --rows 4 --cols 8 --pe-profile basic -o /tmp/fgra_4x8.json

# 单元测试
python3 hardware/test_generate_fgra_spec.py
```

默认输出路径相对脚本位置解析，与运行目录无关。`--output` 和 `--check`
中的相对路径则相对当前工作目录。已有文件与生成结果不同时拒绝覆盖；确认后
可加 `--force`。`--check` 总是不写入文件，退出码 0 表示逐字节一致，1 表示
内容或格式不同，2 表示配置/读取错误。

生成后仍需运行硬件生成流程：

```sh
cd hardware
LINGO_SPEC=/tmp/fgra_4x8.json ./lingo.sh
```

输入规格不是 mapper 使用的最终 ADG。新架构需要重新生成 RTL、ADG 和配置规格，
mapper 与仿真也必须使用对应的新输出，不能沿用旧架构的配置位流。

## 当前架构的表达

`PE_PROFILES` 定义独立的 PE 模板，`CURRENT_PE_LAYOUT` 定义零起始坐标的二维布局：

| 行 | 列 0 | 列 1 | 列 2 | 列 3 | 列 4 | 列 5 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | basic | basic | basic | basic | basic | basic |
| 1 | unified | unified | xcore | unified | unified | unified |
| 2 | acc | acc | acc | acc | acc | acc |
| 3 | basic | unified | unified | xcore | unified | basic |
| 4 | div_mul | div | div | div | div | div_mul |
| 5 | basic | basic | basic | basic | basic | basic |

模板含义：

- `basic`：普通 GPE，整数操作、浮点转换/比较、FMUL 和 FADDSUB，LUT 输入数 0。
- `unified`：mode 1，FMUL 和 FADDSUB，LUT 输入数 0。
- `xcore`：mode 2，XCORE，LUT 输入数 0。
- `acc`：普通 GPE，包含 ACC、ISEL、FACC，LUT 输入数 2。
- `div_mul`：普通 GPE，包含 FMUL、FADDSUB、FDIV，LUT 输入数 2。
- `div`：普通 GPE，包含 FADDSUB、FDIV，但不包含 FMUL，LUT 输入数 2。

所有当前模板的 CG/FG 最大输入延迟分别为 16/8。操作列表原样输出，
不自动去重或排序；`FCMP`、`FADDSUB` 等名称由 Scala loader 展开。

方向编码为 W=0、N=1、E=2、S=3、NW=4、NE=5、SE=6、SW=7；
当前输入/输出方向列表 `[4,5,7,6]` 按 NW、NE、SW、SE 排列。

当前 IOB 为上下两侧各 6 个，实例模板为 SRAM mode 2、FG IO 开启、
CG/FG 延迟 2/2。CG 和 FG GIB 均为 7×7，实例 `fclist=[2,2,2]`。

## 修改 Python 配置

建议修改脚本中的 `make_architecture()`，保留生成和校验逻辑。
也可以在自己的 Python 程序中导入 `Architecture`、`pe`、`build_spec` 和 `render_spec`。
每个架构实例、每个网格单元均独立深拷贝，修改一个单元不会联动其他单元。

### 调整尺寸与异构布局

行列数由 `pe_layout` 推导，不需要同步修改多个 JSON 字段：

```python
def make_architecture():
    return Architecture(pe_layout=[
        ["basic", "unified", "xcore", "basic"],
        ["acc",   "acc",     "acc",   "acc"],
        ["div",   "basic",   "basic", "div"],
    ])
```

生成器自动同步：

- `fgra_num_row` 和 `fgra_num_colum`（硬件原字段拼写就是 `colum`）。
- PE 实例表、上下两侧 IOB 实例表、CG/FG GIB 实例表。
- `spad_num_banks = 2 × 列数`。
- 默认 `fgra_iob_sram_banks_coalesce = 列数`。
- `fgra_iob_sram_addr_width = spad_bank_lg_size + ceil(log2(coalesce))`。
- 默认所有行列都接入 FG 网络。

例如 2×18 架构会生成 36 个 IOB，IOB 地址宽度为 17 bit（默认 bank 大小）。
这只保证输入规格派生关系正确，不代表该规模已通过硬件 elaboration 或 mapper 验证。

### 新建 PE 模板及单点覆盖

```python
def make_architecture():
    arch = Architecture()
    # 新增模板不会影响其他架构实例或原有模板。
    arch.pe_profiles["mac"] = pe(0, ["PASS", "ADD", "MUL", "MAC"],
                                 lut=0, delay_cg=16, delay_fg=8)
    arch.pe_layout = [["mac"] * 4 for _ in range(4)]
    arch.pe_overrides[(1, 2)] = {"max_delay_cg": 32}
    return arch
```

这里的 MAC 模板只演示已有操作的配置，不会自动增加 OS 脉动接口、数据转发、
驻留控制或 mapper 支持。指定一种操作并不等于验证该操作的所有时序与配置组合。

布局项也可直接使用完整字典，例如 `[[pe(0, ["PASS", "ADD"])]]`。

### 修改全局参数与存储

```python
def make_architecture():
    arch = Architecture()
    arch.parameters.update({
        "spad_bank_lg_size": 13,               # 每 bank 8 KiB
        "spad_cfg_lg_size": 13,                # 配置存储 8 KiB
        "fgra_iob_sram_banks_coalesce": 3,     # 每侧 6 bank 分成两个 3-bank 组
        "fgra_gib_num_track_cg": 2,
        "fgra_cfg_addr_width": 16,
        "fgra_iob_lg_max_cycles": 14,
    })
    return arch
```

`parameters` 的键与 JSON 全局字段相同，拼写错误会被拒绝。行列数、实例表、
bank 数和 IOB 地址宽度由生成器管理，禁止从 `parameters` 覆盖。
增大规模/操作集时，配置块地址位数、块内偏移和配置 SRAM 容量不一定够用；
这些参数没有自动求解，应以 Chisel elaboration 的检查和生成结果为准。

### 修改 IOB 和 GIB

```python
def make_architecture():
    arch = Architecture()
    arch.iob_template["max_delay_cg"] = 4
    arch.iob_overrides[(1, 2)] = {"max_delay_cg": 8}  # 下侧第 2 列
    arch.cg_gib_template["fclist"] = [2, 4, 4]
    arch.cg_gib_overrides[(0, 0)] = {"fclist": [1, 2, 2]}
    arch.fg_gib_overrides[(0, 0)] = {"diag_iopin_connect": False}
    return arch
```

GIB `fclist` 顺序是：`[num_itrack_per_ipin, num_otrack_per_opin, num_ipin_per_opin]`。
默认全局 flexibility 为 `[2,4,4]`，但当前显式 GIB 实例为 `[2,2,2]`；
它们确实不同，生成器不会擅自统一。

若希望全部 GIB 根据全局 flexibility 和 diag 参数生成，设置：

```python
arch.cg_gib_template = None
arch.fg_gib_template = None
```

同样，全局 `fgra_iob_mode=3`、`fgra_max_delay_cg=4`、
`fgra_gpe_num_input_lut=0` 等默认值不覆盖显式实例表。要改变实际实例，
应修改相应模板/单点覆盖，而不是只改全局 fallback 值。

### FG 行列筛选

`parameters` 可以指定 `fgra_gpe_fg_rows` 和 `fgra_gpe_fg_columns`。
此时 FG GIB 表尺寸为 `(所选行数+1) × (所选列数+1)`，其覆盖坐标为筛选后
网格坐标；CG GIB 坐标仍对应完整网格。

这需要同时检查 PE/IOB 的 FG 端口是否全部连接。脚本只检查索引递增、不重复和
范围正确，不证明不存在浮空端口；保留所有行列是最稳妥的默认设置。

## 参数索引

所有默认值可在 `SPEC_DEFAULTS` 中逐项修改或通过 `parameters` 覆盖。
下表按硬件作用归类，`fgra_*` 等前缀不能省略。

| 类别 | 字段及作用 |
| --- | --- |
| 阵列规模 | `fgra_num_row`、`fgra_num_colum`：从布局派生 |
| 数据位宽 | `fgra_data_width`：阵列；`spad_data_width`：SPM；`system_bus_beat_bits`：系统 beat，须等于 SPM 位宽 |
| XCore 参数 | `logWidth`、`maxSeg`：保留当前 XCore 参数，修改前需核查 XCore 实现 |
| 配置编码 | `fgra_cfg_data_width`、`fgra_cfg_addr_width`、`fgra_cfg_blk_offset`、`fgra_cfg_addr_width_align`：配置数据、地址、块内偏移和对齐 |
| 配置存储 | `spad_cfg_lg_size`、`fgra_cfg_sram_add_reg`：配置存储容量和附加寄存级 |
| PE 默认值 | `fgra_gpe_num_reg_rf_for_alu`、`fgra_gpe_num_reg_rf_for_lut`、`fgra_gpe_num_input_lut`、`fgra_gpe_operations`：全局默认，不覆盖显式模板 |
| PE 输入输出 | `fgra_gpe_in_from_dir`、`fgra_gpe_out_to_dir`：方向编码；`fgra_max_delay_cg`、`fgra_max_delay_fg`：全局默认延迟 |
| FG 范围 | `fgra_gpe_fg_rows`、`fgra_gpe_fg_columns`：启用 FG 网络的行列 |
| 互连轨道 | `fgra_gib_num_track_cg`、`fgra_gib_num_track_fg`：每方向轨道数；`fgra_gib_track_reged_mode_cg`、`fgra_gib_track_reged_mode_fg`：硬件寄存轨道模式 |
| 互连连接 | `fgra_gib_diag_iopin_connect_cg/fg`、`fgra_gib_connect_flexibility_cg/fg`：全局默认；实例由 GIB 模板决定 |
| IOB 结构 | `fgra_iob_num_sides`：当前固定 2；`fgra_iob_mode`、`fgra_iob_has_io_fg`：全局默认；`fgra_support_multiple_precision`：多精度开关 |
| IOB 存储 | `fgra_iob_sram_add_reg`、`fgra_iob_sram_has_mask`、`fgra_iob_sram_banks_coalesce`、`fgra_iob_sram_addr_width`：寄存、字节掩码、合并 bank 数、派生地址宽度 |
| IOB 地址生成 | `fgra_iob_ag_nest_levels`：循环嵌套级数；`fgra_iob_lg_max_stride/lat/cycles/ii`：步进、启动延迟、循环次数、II 的配置范围位数 |
| 执行计数 | `fgra_exe_lg_max_ii`、`fgra_exe_lg_max_execute_cycles`、`fgra_exe_lg_max_loop_cycles`：执行控制计数范围位数 |
| SPM 组织 | `spad_bank_lg_size`：单 bank 字节容量的 log2；`spad_num_banks`：派生 bank 数；`spad_addr_num`：原规格的地址资源参数 |
| AXI/DMA | `id_width`：事务 ID 位宽；`dma_lg_max_burst_size`、`dma_num_req_in_flight`：原规格 DMA 参数 |
| 队列 | `ls_stream_queue_depth`、`rs_cmd_queue_depth`、`rs_exe_queue_depth`、`rs_load_queue_depth`、`rs_store_queue_depth`：原规格队列容量 |
| TLB | `tlb_num_ways`、`tlb_is_shared`：原规格 TLB 参数 |
| 导出 | `dumpADG`、`fgra_adg_filename`、`dumpOperationSet`、`operation_set_filename`：导出开关和文件名 |
| 实例表 | `fgra_gpes`、`fgra_iobs`、`fgra_cg_gibs`、`fgra_fg_gibs`：由布局、模板和覆盖生成 |

部分原 FGRA 控制器/DMA/TLB 参数在独立 AXI 顶层中可能未使用，仍原样保留，
不能认为修改每个参数都会改变 LinGo RTL。`LinGoWithAXI` 还会强制开启 ADG、
operation 导出及字节掩码，并自行推导 AXI 地址宽度、CSR 空间。

## 验证边界

生成器检查矩形布局、覆盖坐标、模板字段、已知 Unified/XCore/IOB 限制、
coalescing 整除关系、位宽关系、FG 索引和基本配置地址关系。

它不实现新的硬件能力，也不保证任意参数组合能 elaboration、时序收敛或被 mapper
成功映射。尤其需要另外验证：操作支持及展开、FG 端口连通、配置容量、路由资源、
MAC 反馈时序、XCore 位宽约束，以及扩大阵列后的 mapper/runtime 配套。
