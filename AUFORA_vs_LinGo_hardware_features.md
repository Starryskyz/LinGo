# AuFORA 相较于 LinGo 的硬件新特性与移植评估

## 1. 结论摘要

AuFORA 相较于当前 LinGo 的核心增量是**多 tile 架构及其配套控制、配置、存储和运行时资源管理**，而不是算力单元数量的简单增加。当前两个默认实例都包含 36 个 PE：LinGo 是一个 6×6 的混合粒度 FGRA，AuFORA 则将 36 个 PE 拆成 3 个 6×2 的 coarse-grained tile。AuFORA 因此具备按 tile 选择配置、启动、完成检测和存储分区的基础，并通过 tile 边界互连把多个 tile 拼成更大的逻辑阵列。

除默认实例外，AuFORA 代码中还保留了一组未默认启用的硬件能力：IACC、INTLV/DEINTLV、MAC/FMA、BF16 运算、共享乘法器式 FP32 除法、FIFO IOB 和异构 PE 配置入口等。它们也属于本文评估范围，但必须按成熟度区分：有些已经贯通操作表、ALU、PE 和配置寄存器，只差架构规格与软件链启用；有些只有独立模块或明确标为 `not support yet`，还不能视作可直接打开的功能。

若把这些能力移植到 LinGo，建议保留 LinGo 已有的混合粒度互连、LUT/XCore 和异构 PE，仅在其外层增加 tile 化。完整移植的主要难点不在复制若干 Chisel 模块，而在于同时保持以下四层语义一致：

1. RTL 中的 tile 边界、配置广播、执行状态和 SPM 分区；
2. ADG 中的 tile 坐标、跨 tile 边和配置地址；
3. mapper 中的 tile-aware 放置布线、配置生成和资源约束；
4. runtime/cocotb 中的 tile 分配、寄存器掩码、配置延迟和并发完成检测。

综合判断：实现一个“可选择任意 tile、但任务仍串行”的 MVP 为**高难度**；实现 AuFORA 式多任务空间并发和跨 tile 联合映射为**很高难度**。

## 2. 对比基线与口径

本文基于当前工作区源码进行静态比较：

- LinGo：本仓库的 [LinGoController.scala](hardware/src/main/scala/LinGoController.scala)、[FGRA.scala](hardware/src/main/scala/dsa/template/FGRA.scala)、[fgra_spec.json](hardware/src/main/resources/fgra_spec.json) 及 simulation/mapper 代码。
- AuFORA：本机 `/data/jrzhang/auforapro/AuFORA/AuFORA-CGRA` 中的 `MultiTileCGRA.scala`、`AuFORACGRAController.scala`、`MultiTileSRAMCoalesce.scala`、`AuFORASpec.scala` 等源码。
- 本文同时统计默认启用和未默认启用的功能。状态分为四级：A＝默认顶层已启用；B＝RTL 主路径已接通、默认规格关闭；C＝已有模块或参数入口，但尚未接入默认主路径；D＝占位、注释实现或源码明确标记尚不支持。
- B/C/D 级功能仍列入比较，但难度包含从当前成熟度推进到可验证、可映射、可运行状态所需的工作，而不只是取消一行注释。
- 难度按当前 LinGo 代码基础评估：低＝局部参数或接口扩展；中＝跨 2～3 个模块且协议基本不变；高＝同时修改 RTL/ADG/软件；很高＝涉及体系结构语义、mapper 算法和并发验证。

需要特别说明：AuFORA 并不是 LinGo 的严格超集。LinGo 的混合细/粗粒度数据通路、fine-grained I/O、LUT、异构 PE 和 XCore 非线性函数单元，均不是 AuFORA 此次对比中的新增能力。

## 3. 总览

| 特性 | AuFORA 状态 | 当前 LinGo 状态 | 移植难度 | 建议优先级 |
|---|---|---|---|---|
| 多 tile 阵列封装 | 默认启用，3×(6×2) | 单个 6×6 FGRA，`tile_num=1` | 很高 | P0 |
| 每 tile 独立配置/启动/完成 | 默认启用 | CSR 有兼容字段，但只使用 bit 0 | 高 | P0 |
| 跨 tile 路由与多 tile 拼接 | 默认启用 | 无 tile 边界概念 | 很高 | P1 |
| 分层配置广播和 tile 配置地址 | 默认启用 | 单阵列配置链 | 高 | P0 |
| tile 本地 SPM bank 分区 | 默认启用 | 单阵列、按上下侧分组 | 高 | P0 |
| 可扩展 AXI-Lite CSR/位图 | 默认启用 | 固定单字 CSR，最多 32 bank mask | 中到高 | P0 |
| 多任务空间并发基础 | RTL 控制基础已存在 | runtime 有 tile 分配框架，硬件仅 1 tile | 很高 | P1 |
| SPM 广播写 | 默认启用 | 已实现 AuFORA 兼容版本 | 低（保留规模）/中（扩展规模） | 已部分完成 |
| IACC 与 induction-controlled affine register | B：操作表、PE、DMR 已接通，默认规格关闭 | 有较早版 affine DMR，无 IACC | 中到高 | P2 |
| INTLV/DEINTLV 2/3/4 路交织 | B：操作表、ALU、PE launch/DMR 已接通，默认规格关闭 | 未发现同等操作 | 高 | P2 |
| 整数 MAC、FP32 FMA/FMAC、BF16 FMA/MAC | B：操作/数据通路已实现，默认规格关闭 | 有整数 MAC/CMAC 基础，无同名完整 FP32/BF16 组合 | 中到高 | P2 |
| BF16 加减乘除与比较 | B：算子库及 ALU 接入已实现，默认规格关闭 | 默认未启用 BF16 | 中到高 | P2 |
| FP32 除法复用乘法器 | B：FDIV32 prep 与共享 FPMult32 路径已接通，默认规格关闭 | 已有独立 FDIV 路径 | 中 | P2 |
| FIFO IOB、异构 PE 操作配置 | B/C：代码路径存在，默认采用 SRAM IOB/统一操作集 | LinGo 也有对应或更强基础 | 低到中 | 按需求 |
| Merge controller | C：独立模块存在，未进入 PE/顶层 | 无独立默认模块 | 高 | 暂缓 |
| FSQRT/BFSQRT 等占位操作 | D：操作表存在但标记尚不支持 | LinGo 已有 FSQRT/XCore 路径 | 不建议直接移植 | 不移植 |

## 4. 已默认启用的主要新特性

### 4.1 多 tile 阵列，而非单体阵列

AuFORA 的默认规格为 3 个 tile，每个 tile 为 6×2 PE，总 PE 数仍为 36。其 `MultiTileCGRA` 将 `cfg_en`、`iob_ens`、`en`、`start`、`done` 和 SRAM 端口都定义为 tile 维度的向量，并在 ADG 属性中记录 `tile`、`cfg_tile_offset` 和每 tile 模块数。

LinGo 当前由 [LinGoController.scala](hardware/src/main/scala/LinGoController.scala) 直接实例化一个 `FGRA`；[FGRA.scala](hardware/src/main/scala/dsa/template/FGRA.scala) 固定导出 `cgra_tile_num = 1`。虽然控制寄存器名称沿用了 AuFORA 接口，但配置和执行只检查 `cfgTileEn(0)`、`exeTileEn(0)`。

**收益**

- 小任务可只占用部分阵列，减少资源浪费；
- 多个独立任务具备在不同 tile 上并发的硬件基础；
- 大任务仍可通过跨 tile 路由使用多个 tile；
- tile 成为功耗隔离、时钟门控、故障隔离和物理实现的自然边界。

**在 LinGo 中实现：很高难度。需要做的工作**

1. 将 `FGRA` 重构为可复用的 `LinGoTile`，把 tile 行列数、tile ID 和配置块偏移参数化；
2. 新增 `MultiTileLinGo` 外层，生成 `Vec(tileNum, ...)` 的配置、执行、完成和 SRAM 接口；
3. 保留每个 tile 内的 CG/FG GIB、LUT、XCore 与异构 GPE，不应直接用 AuFORA 的纯 coarse-grained PE 替换；
4. ADG 为每个模块实例增加 tile ID，并保证模块 ID、配置块 ID 在全芯片唯一；
5. 更新规格生成逻辑，使总行列、tile 内行列和 tile 数不再混用；
6. 增加 1 tile 回归模式，保证重构后现有 6×6 LinGo bitstream 行为不变。

### 4.2 每 tile 独立配置、执行和完成状态

AuFORA 为每个 tile 实例化 `TileStateCtrl`，保存该 tile 的 configured/running/done 状态；控制器使用配置 tile mask、执行 tile mask 和 IOB mask，仅在选中 tile 无冲突时发出配置或执行脉冲。每个 tile 的完成位独立回读。

当前 LinGo 已有 `reg_cfg_en_tile_0`、`reg_exe_tile_ens_0`、`reg_exe_done_0` 等兼容名称，但硬件只实现一个全局执行 FSM 和一个 done 位。因此这是“接口外形已有、硬件语义未实现”。

**在 LinGo 中实现：高难度。需要做的工作**

1. 将全局 `exeState` 拆为每 tile 状态机，至少记录 configured、running、done 和 active IOB mask；
2. 定义并实现冲突规则：配置不能覆盖正在执行的 tile，执行不能占用已运行的 tile；
3. 明确一次任务占多个 tile 时的完成语义，建议为选中 tile 的 done 归约，同时保留逐 tile done 位；
4. 明确 reset、取消、超时和异常状态，避免某个 IOB 不完成导致整个 tile 永久占用；
5. 在 cocotb 中加入单 tile、多 tile 联合、两个不相交任务、非法重叠四类测试；
6. runtime 写寄存器时按任意长度位图处理，不假设 tile mask 只占一个 32-bit word。

注意：AuFORA 顶层仍有一个全局命令 FSM，因此“具备 tile 并发基础”不等于所有配置/启动请求都能无约束并行接受。移植时应先确定期望的软件命令模型，再决定照搬还是重写控制仲裁。

### 4.3 跨 tile 互连与可组合阵列

AuFORA 会把前一个 tile 右边界未连接的 GPE/GIB/IOB 与下一个 tile 左边界连接起来。其中 GIB track 为双向拼接，边界 PE 也接入相邻 tile 的 GIB。因此 3 个 6×2 tile 可在路由层面组成一个更宽的逻辑阵列，而不是三个完全隔离的小岛。

**在 LinGo 中实现：很高难度。需要做的工作**

1. 为 LinGo CG 与 FG 两套网络分别定义 tile 边界端口；
2. 决定跨 tile 是否同时支持 coarse data、fine control/predicate、LUT 输入和 XCore 通路；
3. 对每种 GIB track direction 建立确定的边界连接和寄存策略；
4. 在 ADG 中输出跨 tile edge，mapper 必须能识别边界带宽和方向；
5. 检查组合长路径，必要时在边界加入寄存器，并把新增周期反馈给 mapper 的时序模型；
6. 验证隔离性：未参与任务的 tile 不得被跨边界流量或配置误激活；
7. 增加跨 1 条、2 条 tile 边界的 directed routing 测试和拥塞测试。

这是整个移植中风险最高的部分，因为 LinGo 不是纯 coarse-grained 网格，AuFORA 的边界连接不能机械复制。

### 4.4 分层配置广播与 tile 配置地址空间

AuFORA 在全局配置流与各 tile 之间增加一级广播寄存：配置地址/数据按 tile 捕获，配置使能延迟一拍；`ConfigController` 同时计入 `cfgBroadcastBufferLevel = 1`。配置地址还包含 `cfg_tile_offset`，用于把同一 tile 内的配置块编号扩展到全芯片。

LinGo 当前只有一条进入单个 FGRA 的配置链。此前 cocotb 已需要根据生成电路的配置链级数补偿延迟；增加 tile 广播层后，不能再使用固定常数。

**在 LinGo 中实现：高难度。需要做的工作**

1. 定义配置地址格式：tile ID、tile 内 block ID、block 内 offset；
2. 在 tile 入口加入配置地址/数据寄存与 enable 对齐；
3. 修改 `ConfigController`，显式参数化广播层级和 tile 内配置链长度；
4. mapper 的配置生成器加入 tile offset，不再只编码单阵列 block ID；
5. ADG 导出实际配置延迟或配置链级数；
6. cocotb 在每次 config 调用后根据生成规格自动等待，而不是固化“21 级”或其他数字；
7. 做仅配置 tile 0/1/2 的隔离测试，并读取或执行不同配置验证没有串扰。

### 4.5 tile 本地 scratchpad 分区

AuFORA 的 `MultiTileSRAMCoalesce` 使用 `tile × bank` 二维组织。默认每个 6×2 tile 有 4 个 IOB/SPM bank（上侧 2 个、下侧 2 个），每个 bank 为 16 KiB；3 个 tile 共 12 个数据 bank。一个 tile 某一侧的 IOB 可访问该 tile 同侧的 bank，但不会自然访问其他 tile 的本地 bank。

LinGo 当前同样有 12 个数据 bank，但它们围绕一个 6×6 阵列按上下侧分组，每 bank 默认 4 KiB。因此两者 bank 数相同，关键差异是**局部性和归属关系**，并非仅容量差异。

**在 LinGo 中实现：高难度。需要做的工作**

1. 将 SRAM coalesce 接口改为 `tile × tileBanks`，为每个 tile 分别实例化上下侧 bank group；
2. 重新定义物理 bank ID 与 `(tile, side, localBank)` 的映射；
3. 修改 AXI scratchpad 地址译码、配置区基址和每 bank broadcast base；
4. ADG 导出 `iob_to_spad_banks` 的 tile 局部关系；
5. mapper 增加 bank locality 约束，避免把 I/O 映射到不可达 bank；
6. runtime 的 buffer 分配返回 tile-compatible bank，并处理多 tile 任务的 bank 集合；
7. 决定是否把 LinGo bank 从 4 KiB 增至 16 KiB。此项是容量选择，不是实现多 tile 的必要条件；
8. 验证同 tile bank 访问、跨 tile 非法访问、上下侧并发访问和广播写。

### 4.6 可扩展的 AXI-Lite 控制寄存器

AuFORA 根据 tile 数和 bank 数计算配置 mask、IOB mask、执行 mask、done mask 和广播 mask 所需的寄存器字数，并把动态地址写入 `axilite_spec.json`。LinGo 目前为单 tile 使用固定地址表，broadcast mask 还显式限制 `nBanks <= 32`。

**在 LinGo 中实现：中到高难度。需要做的工作**

1. 将配置/执行/done/IOB/broadcast mask 全部改成多 word 寄存器数组；
2. 用统一地址生成器替代固定 CSR 常量，避免 tile/bank 参数改变导致地址重叠；
3. 生成完整的 `axilite_spec.json`，包括每个 word 的地址、位宽和数量；
4. runtime 依据 spec 读写任意长度字段，并处理末 word 的无效高位；
5. 保留 `tile_num=1` 的旧 ABI 或提供 spec 版本号，避免现有 benchmark 静默失效；
6. 对 1、3、33 tile/bank 边界做寄存器布局单测，重点覆盖跨 32-bit word 的情况。

## 5. 已有基础或不是 AuFORA 独有的新特性

### 5.1 SPM 广播写：LinGo 已部分实现

当前 LinGo 已有 `bcast_en`、`bcast_bank_mask` 和逐 bank `bcast_base_addr`，顶层 AXI scratchpad 也已接入。因此不能再把“广播写”本身列为 AuFORA 相对 LinGo 的缺失功能。

剩余差距主要是规模化：AuFORA 的 mask 和 base register 数量随总 bank 数生成；LinGo 当前使用单个 32-bit mask，并限制 bank 数不超过 32。若多 tile 后总 bank 数仍不超过 32，工作量较低；若要任意扩展，则应与 4.6 的动态 CSR 一起完成。

### 5.2 runtime 已存在部分多 tile 抽象

[test_runif.py](simulation/server/test_runif.py) 已解析 `tile_num`、按 tile/IOB 数计算寄存器长度，并维护 `tile_free_list`。这会降低软件改造的起步成本，但不能证明当前硬件支持多 tile；当前生成的 [axilite_spec.json](simulation/circuits/axilite_spec.json) 和 ADG 仍明确为 1 tile。

需要重点复查连续 tile 分配假设、跨 tile 任务占用、多个 handler 的并发寄存器写时序，以及硬件 busy/done 与 free-list 更新是否原子一致。

## 6. AuFORA 中存在但默认未启用的可选能力

### 6.1 成熟度总表

| 能力 | 成熟度 | 已接入的 AuFORA 层次 | 默认关闭位置 | 可否仅改规格启用 |
|---|---|---|---|---|
| IACC | B | OpInfo、PE、AffineCtrlReg/DMR、配置字段 | `AuFORASpec.scala` 未列入操作集 | 否，还需 mapper 与验证 |
| INTLV/DEINTLV | B | OpInfo、ALU、PE launch、DMR mode | 默认操作集被注释 | 否，还需多输出语义与 mapper |
| MAC/FMA/FMAC | B | OpInfo、ALU、PE feedback、浮点单元 | 默认操作集被注释 | 否，还需调度和数值验证 |
| BF16 | B | BF16 算子、ALU 实例化、结果选择 | 默认操作集被注释 | 否，还需数据类型/打包和验证 |
| 共享乘法器 FDIV32 | B | div-prep、FPMult32 复用 MUX、结果路径 | 默认 `FDIV32` 被注释 | 否，还需资源冲突建模 |
| FIFO IOB | B | IOB/IOController 模式分支 | 默认选择 SRAM mode | 接近，但需顶层协议测试 |
| 异构 PE 操作集 | C/B | `specific_gpe_operations` 参数解析 | 示例配置被注释 | LinGo 已有类似机制，无需照搬 |
| MergeController | C | 独立 util 模块 | 未被 PE/顶层实例化 | 否 |
| FSQRT/BFSQRT | D | 只有操作信息/相关 FPU 基础 | 源码标记 `not support yet` | 否 |

“RTL 主路径已接通”只表示 elaboration 时有条件生成相应硬件，不表示当前 mapper 能生成正确配置，也不表示数值和周期行为已经过系统回归。

### 6.2 IACC 与 induction-controlled affine register

LinGo 已有 affine controlled register，可配置初值、写间隔、起始延迟、cycles、repeats、skip-first 等，并服务于 ACC/ISEL。AuFORA 的版本进一步加入 `lgMaxII`、`OutWI`、`UseIn`、`Reverse` 等字段，并允许第二输入参与 cycle 上限或初值选择，从而实现 induction-controlled accumulation（IACC）。

IACC 已出现在操作信息表，PE 会据此设置 `hasIACC` 并扩展 DMR；但默认 `cgra_gpe_operations` 未包含 IACC，因此当前生成阵列不会实例化这部分附加配置位。

**移植难度：中到高。需要做的工作**

- 扩展 LinGo `DMR.scala` 的 `UseIn`、`Reverse`、`OutWI`、`IIdmr` 配置字段及动态计数逻辑；
- 在 PE 操作表中加入 IACC，并接通第二输入和 DMR mode 4；
- 更新 operation JSON、ADG 配置位描述和 mapper 的归纳变量模式；
- 明确 IACC 的输入含义和 II/latency 约束；
- 添加 cycle/repeat/II 正反向变化、边界值和提前结束的逐周期测试。

### 6.3 INTLV/DEINTLV 2/3/4 路交织

AuFORA 定义了 2、3、4 路 `INTLV` 和 `DEINTLV` 操作。操作信息、ALU 函数、PE 的 `launch` 信号以及 DMR 的 mode 7 已经形成条件生成路径。INTLV 将多个输入按节拍合并；DEINTLV 将单输入按节拍分发为多个结果。默认规格中这些操作被注释关闭。

**相对 LinGo 的增量：** 当前 LinGo 操作表未发现等价的通用多路交织/解交织操作。该能力可减少显式选择节点和路由压力，但会引入多结果端口、相位和 launch 对齐语义。

**移植难度：高。需要做的工作**

- 在 LinGo PE/ALU 中支持最多 4 个输入或 4 个结果，并确认 CG/FG 输出端口是否足够；
- 移植 interleaver opcode、相位计数和 DMR launch 对齐；
- 扩展 ADG/DFG 对多结果端口的表达，mapper 建模每个相位的输入输出关系；
- 明确停顿、重新 start 和 II 大于 1 时的相位保持规则；
- 分别验证 2/3/4 路、连续 block、尾部不足一组和跨 tile 路由。

### 6.4 MAC、FMA 与反馈复用

AuFORA 的操作库包含整数 `MAC`、FP32 `FMA32/FMAC32` 以及 BF16 `BFMA16/BFMAC` 相关条目。PE 会在存在 MAC 类操作时启用额外反馈语义，AffineCtrlReg 使用专用 mode；浮点实现还可以让加法器/乘法器参与 FMA 数据通路。默认规格中的 MAC/FMAC 项被注释。

LinGo 已有整数 `MAC/CMAC` 的操作表、ALU 输入和 DMR 反馈基础，因此整数 MAC 不是全新的能力；真正的差距主要在 AuFORA 的 FP32/BF16 FMA 组合、opcode/latency 以及与 affine register 的统一控制方式。

**移植难度：整数路径低到中，FP32/BF16 路径中到高。需要做的工作**

- 先复用并验证 LinGo 现有整数 MAC/CMAC，避免重复移植；
- 为 FP32/BF16 定义 fused 还是非 fused 的舍入语义；
- 接通第三操作数、反馈 mux、DMR mode 6 和 FMA 结果路径；
- mapper 将 MAC/FMA 识别为单 PE pattern，并按真实 latency 排程；
- 比较独立 MUL+ADD 与 FMA 的面积、频率、精度和映射收益后再决定默认 PE 分布。

### 6.5 BF16 算术及 BF16 除法

AuFORA 算子库包含 BF16 加、减、乘、比较和多种 BF16 除法实现，操作表也包含相应 opcode；但默认 `AuFORASpec.scala` 中 BF16 操作均被注释。因此它表示可综合的库级储备，不代表默认 AuFORA bitstream 已启用 BF16。

**移植难度：中到高。需要做的工作**

- 选择 BF16 舍入、NaN/Inf/subnormal 语义并建立软件 golden model；
- 将 BF16 单元接入 LinGo `Operations.scala`/ALU，处理 32-bit 通路中的打包方式；
- 定义 latency、opcode、资源共享和异构 PE 分布；
- 更新 mapper 类型系统和调度延迟；
- 验证特殊值、舍入边界以及 BF16DIV 的流水级对齐。

### 6.6 共享乘法器的 FP32 除法

AuFORA 的 `FDIV32` 采用 reciprocal/div-prep 加共享 `FPMult32` 的结构：除法前级生成修正后的乘法操作数，随后与普通 `FMUL32` 复用乘法器和结果通路。相关 MUX、结果选择及操作 latency 已接入 `Operations.scala`，但默认规格关闭 `FDIV32`。

LinGo 已有可用的 `FDIV`，且默认架构中的部分 PE 已启用，因此这里的增量不是“支持除法”，而是**让除法与乘法共享昂贵的乘法资源**。是否值得采用需要用面积、吞吐和冲突率衡量。

**移植难度：中。需要做的工作**

- 将 LinGo FDIV 分解为 div-prep 与共享 multiplier 后级，或为现有结构增加可选共享模式；
- 定义 FMUL/FDIV 同时存在时的静态互斥或调度约束；
- 更新真实 latency，AuFORA 操作表中的 FDIV32 为 7 周期，不能沿用 LinGo 当前 FDIV 数值；
- 验证符号、指数修正、零、Inf、NaN、subnormal 和舍入；
- 综合比较独立 FDIV 与共享方案的 LUT/DSP、Fmax、II 和能耗。

### 6.7 FIFO IOB 与异构 PE 配置入口

AuFORA 的 IOB/IOController 保留 FIFO mode 和 SRAM mode 两套条件生成路径；规格生成器也支持通过 `specific_gpe_operations` 为特定 PE 指定不同操作集。当前默认使用 SRAM mode 和统一 GPE 操作集，所以这两项属于存在但未默认展开的参数化能力。

这些能力相对 LinGo 并不构成明显领先：LinGo 已有 FIFO/SRAM/扩展 I/O mode、fine-grained I/O，并已在 JSON 中逐 PE 描述异构操作集。正确策略是保留 LinGo 实现，只吸收 AuFORA 多 tile 后对 IOB mode 和 PE type 的 tile 维度描述。

**移植难度：低到中。需要做的工作**

- 不复制 AuFORA IOB，先验证 LinGo 现有 FIFO mode 在新 tile 外层下仍可综合和仿真；
- 为每个 tile/IOB 导出 mode、端口数和可达 bank；
- 让 PE type key 包含 tile 或使用可复用类型 ID，避免 ADG 膨胀；
- 增加 SRAM/FIFO 混合 tile 和异构 PE 的 elaboration、映射与 I/O 协议测试。

### 6.8 Merge controller 与尚未完成的操作

AuFORA 源码中有按 II/轮转选择输入的 `MergeController`，但静态搜索未发现其进入默认 PE 或顶层实例化路径。因此当前不建议以它为基线要求。若应用确实需要动态流合并，应先定义 valid/ready、背压和公平性语义，再决定是否移植。

操作表还列出了 `FSQRT` 和 `BFSQRT`，但旁注明确写着 `not support yet`；不能因为存在 opcode/latency 条目就认定硬件功能完成。部分 FPU 文件中也包含注释掉的旧实现或 TODO，同样只能视为设计储备。

**若要在 LinGo 中实现 MergeController：高难度。需要做的工作**

- 把独立模块接入 PE 或专用 routing node，并定义配置位和 ADG node type；
- 确定它是静态时分交织还是带 valid/ready 的动态 merge；
- mapper 建模输入仲裁、II、公平性及可能的背压；
- 验证空输入、输入速率不匹配、饥饿和任务停止后的状态恢复。

**FSQRT/BFSQRT 建议：** 不从 AuFORA 的 D 级占位路径移植。LinGo 已有 FSQRT/XCore 相关能力，应优先修正和验证现有实现；如需 BF16 sqrt，再以明确数值规范重新设计。

## 7. 建议的 LinGo 实现路线

### 阶段 0：冻结单 tile 基线

- 保存当前 1-tile ADG、AXI-Lite spec、代表性 bitstream 和 cocotb 输出；
- 为配置链实际级数建立自动探测/导出机制；
- 建立 `tile_num=1` 的回归门槛，后续每阶段必须通过。

**完成标准：** 现有 luttest、sqrt/logsigmod、mySigmoid、myEXP 等路径在重构前后逐周期一致。

### 阶段 1：只做物理 tile 化，不做并发

- 抽出 `LinGoTile`，先生成 1 个 tile，再生成 3 个 6×2 tile；
- 新增 tile ID、全局模块 ID 和 tile 配置地址；
- 接入配置广播层；
- 控制器一次仍只允许一个任务，降低首版状态空间。

**完成标准：** 可以分别配置并运行 tile 0、1、2，未选 tile 保持静止；单任务可占连续多个 tile。

### 阶段 2：跨 tile 路由和 tile 本地 SPM

- 定义 CG/FG 边界协议并生成跨 tile ADG edge；
- 重构 SRAM coalesce 与 AXI 地址译码；
- mapper 加入 bank locality 和跨边界带宽约束。

**完成标准：** 数据流能跨越两个边界；每个 tile 只能访问授权的本地 bank；所有地址和延迟由 spec 驱动。

### 阶段 3：独立 tile 状态与多任务并发

- 每 tile state controller、mask、done、busy；
- runtime 分配/释放 tile 与 bank；
- 支持不相交任务同时执行，配置与执行是否重叠则作为独立开关逐步开放。

**完成标准：** 两个任务在不相交 tile 上并发，结果与串行执行一致；冲突请求被可靠拒绝或等待；完成顺序任意时资源都能正确释放。

### 阶段 4：可选算子能力

- 建立完整候选清单：IACC、INTLV/DEINTLV、整数/FP32/BF16 MAC/FMA、BF16、共享 FDIV、FIFO IOB、异构 PE、Merge；
- 对 B 级功能逐个做独立 elaboration 和单元仿真，确认不是“能生成但行为未闭合”；
- 对 C 级功能先完成接口、配置和 ADG 设计评审，再接入主路径；
- D 级功能不直接移植，除非 workload 明确要求且重新完成设计与验证；
- 每次只开放一组 opcode，并同步更新 mapper、延迟模型和验证；
- 用映射成功率、周期、面积、Fmax、DSP/BRAM 和数值误差决定是否进入默认 LinGo 规格。

不建议在多 tile 基础尚未稳定时同时引入这些 PE 微架构变化，否则配置错误、路由错误和算术错误难以隔离。

## 8. 预计需要修改的 LinGo 代码区域

| 区域 | 主要文件 | 主要工作 |
|---|---|---|
| 阵列生成 | `hardware/src/main/scala/dsa/template/FGRA.scala`、`FgraParam.scala` | 抽取 tile、tile ID、边界端口、跨 tile 实例化 |
| 顶层控制 | [LinGoController.scala](hardware/src/main/scala/LinGoController.scala) | 多 tile FSM、mask/done、动态 CSR、配置冲突 |
| 顶层总线 | `hardware/src/main/scala/LinGoWithAXI.scala` | 总 bank 数、地址图、广播和接口展开 |
| 存储 | `hardware/src/main/scala/SRAMCoalesce.scala` | tile×bank 分组、局部可达性 |
| PE/寄存器 | `hardware/src/main/scala/dsa/pe/PE.scala`、`dsa/util/DMR.scala` | IACC、INTLV/DEINTLV、MAC/FMA 的输入/输出、反馈、mode 与配置字段 |
| 算子 | `hardware/src/main/scala/op/Operations.scala`、`op/FPU/*`、`op/XCore/*` | BF16、共享 FDIV、FMA 接入；保持 XCore 行为 |
| 架构规格 | [fgra_spec.json](hardware/src/main/resources/fgra_spec.json) 及生成代码 | tile 参数、配置 offset、bank 映射、延迟元数据 |
| mapper | `mapper/src/*`、`mapper/include/*` | tile-aware P&R、跨 tile 路由、bank 约束、bitstream 地址 |
| 仿真/runtime | [test_runif.py](simulation/server/test_runif.py) | 动态 CSR、多任务分配、配置延迟、done/busy 协议 |
| 测试产物 | `simulation/circuits/*`、benchmarks | 1/多 tile ADG、spec、定向与并发测试 |

## 9. 主要风险

1. **配置地址兼容性：** tile ID 插入地址后，旧 mapper 生成的 block ID 可能仍合法但指向错误模块，属于最危险的静默错误。
2. **配置延迟：** tile 广播寄存器、tile 内配置链和 SRAM 读延迟必须统一计数；不能继续依赖固定 21 级。
3. **跨 tile 时序：** 直接拼接 FG/CG 网络可能形成长组合路径；加寄存后又会改变 mapper 的时序语义。
4. **存储归属：** bank 数不变但编号含义改变，旧 runtime 的物理地址可能落到错误 tile。
5. **完成条件：** 多 IOB、多 tile 的 done 归约若与 mask 不一致，会出现提前完成或永久不完成。
6. **并发原子性：** 软件 free-list、CSR 写入和硬件状态变化之间缺少 reservation/ack 时，两个请求可能重叠占用资源。
7. **LinGo 特性回归：** AuFORA 的纯 coarse-grained 边界方案不能覆盖 LinGo 的 fine-grained predicate、LUT 和 XCore 通路。
8. **成熟度误判：** 操作名或独立模块存在不等于端到端可用；B/C/D 级功能必须分别经过 elaboration、模块仿真、mapper 接入和系统回归。

## 10. 推荐决策

优先实现“3 个 6×2 LinGo tile + 动态 CSR + tile 本地 SPM + 串行命令”的 MVP，暂不同时开放多任务并发、BF16 和新 affine mode。这样可以先验证 tile 地址、配置隔离、跨 tile 路由和 bank locality 四个根本问题。

MVP 稳定后，再加入每 tile 独立状态和 runtime 并发。BF16、IACC/INTLV/MAC、Merge controller 应由具体 workload 和面积/频率数据驱动，而不应因为 AuFORA 源码中存在相应模块就默认移植。

未启用功能也应进入正式 roadmap，而不是忽略：第一批评估 IACC、INTLV/DEINTLV 和共享 FDIV32；第二批评估 FP32/BF16 FMA 与完整 BF16；FIFO IOB 和异构 PE 优先复用 LinGo 现有能力；MergeController 作为 C 级研究项；FSQRT/BFSQRT 的 AuFORA 占位路径不作为移植源。
