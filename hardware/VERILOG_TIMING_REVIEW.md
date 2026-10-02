# LinGo 手写 Verilog 时序写法审查

日期：2026-10-01  
范围：`src/main/resources/vsrc/` 中由 `LNS_Top` 引入的非 Chisel RTL 及其与 XCORE 包装层的时序契约。  
结论性质：静态代码审查；未修改 RTL/Chisel，未运行功能仿真、综合或 STA。

## 1. 审查范围

本次审查覆盖以下手写 Verilog：

- `LNS_Top.v`
- `CPA_tree_with_MAD.v`
- `CSA_tree.v`
- `converter.v`
- `anticonverter.v`
- `segSel.v`

这些文件由 `src/main/scala/op/XCore/LNS.scala:170-175` 作为 BlackBox resource 引入，并最终拼入 `verilog/LinGoWithAXI.v`。因此，本文指出的问题也存在于当前生成的单文件 Verilog 中，并不是“文件仍然分离”才会产生的问题。

本文没有逐行审查 Chisel 生成的 AXI、控制器、互连和存储系统逻辑。涉及 Chisel 的内容只用于核对手写 Verilog 与外层 XCORE 的接口和延迟契约。

## 2. 总结

当前最重要的问题不是某一条组合路径可能过长，而是**接口声明的固定 4 周期延迟与实际各输出路径的寄存器深度不一致**。

| 优先级 | 问题 | 静态判断 | 主要后果 |
|---|---|---|---|
| P0 | XCORE 声明 4 周期，但 tri 定点/浮点结果约为 6/7 周期 | 可由寄存器边界确认 | mapper 在错误的拍读取结果，可能读到前一迭代数据 |
| P0 | CPA 模式位、输出选择及 overflow 标志未与数据等深流水 | 可确认 | 连续事务可能发生跨拍串扰，标志与结果不属于同一输入 |
| P0 | `anticonverter` 活跃组合逻辑推断 latch | lint 与代码均可确认 | 输出依赖历史值，并引入 latch 时序弧 |
| P1 | BlackBox 内部没有 enable/valid | 可确认；影响取决于系统契约 | 外层停顿时，输入 delay pipe 与 LNS 内部流水状态不一致 |
| P1 | 组合逻辑使用非阻塞赋值 | 可确认 | delta-cycle 行为、RTL/综合模型差异及组合链仿真风险 |
| P1 | 异步复位直接由 Chisel reset 取反，释放未在本模块同步 | 可确认；实际风险取决于顶层复位保证 | recovery/removal 风险，复位释放后可能出现不一致状态 |
| P1 | 多个流水级包含很深的算术/查表/移位组合路径 | 结构可确认；是否违例需 STA | 可能成为 Fmax 关键路径 |
| P2 | 隐式扩展/截断与硬编码位宽 | 可确认 | 参数化脆弱，边界值行为不清晰 |

## 3. 对外 4 周期契约与实际路径不一致

### 3.1 对外契约

XCORE 的操作元数据明确声明延迟为 4：

- `src/main/scala/op/Operations.scala:105`：`"XCORE" -> ListBuffer(2, 1, 4, 0)`
- `verilog/lingo-spec/operations.json:275-281`：XCORE 的 `latency` 为 `4`

如果 mapper 按该延迟调度，下游节点会在输入进入 XCORE 后第 4 拍使用输出。

### 3.2 LNS 主流水

`LNS_Top.v` 中可以看到四组主流水寄存器：

| 边界 | 代码位置 | 主要内容 |
|---|---|---|
| 第 1 拍 | `LNS_Top.v:136-176` | 输入、模式、分段系数与 bias 寄存 |
| 第 2 拍 | `LNS_Top.v:231-265` | converter/log 结果及控制寄存 |
| 第 3 拍 | `LNS_Top.v:311-367` | CSA 输出及控制寄存 |
| 第 4 拍 | `LNS_Top.v:467-492` | anticonverter 输出、log 结果及控制寄存 |

因此下列输出确实在第 4 拍附近形成：

- `channel0_VEC_Power_result`：`LNS_Top.v:513-515`
- `channel0_log_result`：`LNS_Top.v:516`

但 `channel2_tri_result` 在第 4 拍之后还经过 `CPA_tree_with_MAD`：`LNS_Top.v:495-518`。

### 3.3 tri 路径的实际寄存器深度

CPA 树的结构为：

1. `CPA0/CPA1/CPA2` 做第一层加法；
2. `CPA3` 做第二层加法并寄存；
3. `CPA2_result_reg` 对第三支路补一拍；
4. `CPA4` 做最后一层加法并寄存。

证据位于 `CPA_tree_with_MAD.v:35-151`。第一层使用的 `CPA_float_add` 具有不对称延迟：

- 浮点结果在 `CPA_tree_with_MAD.v:302-319` 寄存一拍；
- 定点结果在该模块中为组合结果；
- `CPA3/CPA4` 使用 `CPA_float_add_all_reg`，定点和浮点结果都会在 `CPA_tree_with_MAD.v:447-466` 寄存。

由寄存器边界静态推导：

| 输出模式 | 相对原始 XCORE 输入的约定延迟 | 与元数据的差异 |
|---|---:|---:|
| log | 4 拍 | 一致 |
| vector/power | 4 拍 | 一致 |
| tri，定点 | 约 6 拍 | 多 2 拍 |
| tri，浮点 | 约 7 拍 | 多 3 拍 |

这里的“第几拍”以输入被第一级寄存器采样为起点。具体 testbench 对边沿的计数命名可能相差 1，但**三类输出的相对延迟不同**这一点不受计数习惯影响。

这会直接破坏 CGRA 的静态调度：对 tri 操作而言，下游按照 4 周期取数时，真正结果尚未到达，容易取得复位值、旧值或前一迭代结果。

## 4. CPA 树存在跨拍的数据、控制和标志错位

### 4.1 `float_flag` 没有随 CPA 数据流水

`float_flag` 直接送入 CPA0～CPA4，并在寄存器后的输出 mux 上继续使用：

- 顶层连接：`CPA_tree_with_MAD.v:35-145`
- 第一层结果选择：`CPA_tree_with_MAD.v:318-319`
- 后两层结果选择：`CPA_tree_with_MAD.v:466`

数据已经延迟一至多拍，但选择它的 `float_flag` 仍是当前拍的值。如果相邻事务的定点/浮点模式不同，当前控制可能选择上一事务的数据分支。配置在整个 kernel 执行期间保持不变时，这个问题可能被掩盖；从模块接口本身看，它不是安全的逐拍流接口。

LNS 外层最终输出选择同样由当前配置形成的 `VEC|isPower`、`isTri`、`isLog` 控制，见 `src/main/scala/op/XCore/LNS.scala:211-218`，而各结果路径延迟并不相同。只要这些配置并非整个执行阶段恒定，输出 mux 也会发生拍错位。

### 4.2 overflow/underflow 混合了不同事务的状态

CPA 树直接 OR 第一层、第二层和最后一层的标志：

- `CPA_tree_with_MAD.v:148-150`

这些标志来自不同数量的寄存器级，因而在流式工作时属于不同输入事务。最终输出的 overflow/underflow 可能包含相邻事务产生的标志，而不一定对应当前的 `tri_result`。

代码中已经有注释指出标志需要随结果延迟，例如 `CPA_tree_with_MAD.v:269` 和 `:414`；但树顶层把不同级的标志直接合并，仍未形成一条与最终结果同拍的状态流水。

## 5. enable/valid 语义不完整

LNS BlackBox 接口只有 `clk`、`rstn`、数据、配置和结果，没有 `en` 或 `valid`，见 `src/main/scala/op/XCore/LNS.scala:137-169`。所有内部时序块均在每个 `posedge clk` 前进，没有 clock enable。

与此同时，XCORE 外层输入 `SharedDelayPipe` 由 `io.en` 控制：

- `src/main/scala/dsa/pe/XCore.scala:152`
- LNS 输入来自该 delay pipe：`XCore.scala:159-163`

因此，当 `io.en=0` 时，外层输入管线和 LNS 内部流水不是同一种停顿语义：前者可能保持或重置自身状态，而后者继续逐拍移动。当前控制器在执行期间可能始终保持 `en=1`，这会降低实际触发概率；但该限制必须成为明确的体系结构契约，否则 pause、bubble 或调试停顿都会破坏事务对齐。

没有 `valid` 还意味着系统完全依赖固定延迟判断结果何时有效，所以第 3 节的延迟不一致会直接成为功能错误，而不仅是接口风格问题。

## 6. 组合逻辑推断 latch

### 6.1 `APP` 的 `segment` case 不完整

`anticonverter.v:1131-1165` 中，`segment` 是 6 位，但 case 只覆盖 `0` 到 `31`，且没有 `default`。当 `segment` 为 `32`～`63` 或含 X/Z 时，`A1/A2/A3` 保持旧值，综合会推断 latch。

这一问题同时具有功能和时序影响：输出依赖历史输入；实现中产生 latch 的 enable/data 时序弧；静态时序分析和复位覆盖也会更复杂。

### 6.2 shift 模块的 `sel` 未在 default 中赋值

`anticonverter.v:1307` 开始的 `new_Shift_operation32` 是活跃路径。在 case 的 default 分支中只赋值 `result0`，没有为 `sel` 赋值，因此 `sel` 被推断为 latch。`Shift_operation32` 在 `anticonverter.v:1237` 开始处也存在同类写法；即使它当前不是顶层活跃实例，也属于相同的时序编码缺陷。

只给输出 `result0` 默认值并不能消除 `sel` 的 latch；组合块中的每个 reg 都必须在所有路径被赋值。

## 7. 组合块使用非阻塞赋值

以下组合块使用了 `<=`：

- `LNS_Top.v:67-70`：`segment_bias_constant`
- `LNS_Top.v:92-101`：`bias_seg`
- `segSel.v:14-24`：`break_point` 与 `break_point_sign`

这些信号会继续进入后续组合选择，再在第一级流水寄存器采样。非阻塞赋值把更新放入 NBA 区域，可能使同一仿真时刻的下游组合块先看到旧值，再依赖额外 delta cycle 收敛。综合通常仍生成组合逻辑，但不同模拟器、lint 工具和门级模型对这种写法的表现可能不同。

这类写法未必在每个 testcase 中直接出错，但会增加 RTL 仿真竞态和 RTL/综合不一致的风险。组合逻辑应采用完整赋值的 blocking assignment，时序寄存器才采用 nonblocking assignment。

## 8. 异步复位释放风险

手写 RTL 普遍使用：

```verilog
always @(posedge clk or negedge rstn)
```

BlackBox 外层直接执行 `lns.io.rstn := !reset.asBool`，见 `src/main/scala/op/XCore/LNS.scala:178-180`。这意味着一个 Chisel reset 经组合取反后直接成为多个 Verilog 寄存器的异步低有效复位。

异步拉低本身没有问题，但释放若不与 `clk` 同步，会有 recovery/removal 风险，并可能造成不同寄存器在不同周期退出复位。当前模块内看不到 reset synchronizer，因此安全性依赖顶层对 reset 释放时序的保证。若目标平台或约束没有明确保证“异步置位、同步释放”，应将其视为 P1 风险。

## 9. 潜在关键组合路径

未提供目标时钟周期和时序约束，也未运行综合/STA，因此本节只能列出结构上最可能的关键路径，不能据此声称已经出现 negative slack。

### 9.1 输入到第一级寄存器

`segSel.v` 对 5 个 32 位有符号断点并行比较，再经 `casez` 优先选择系数和 bias，最后进入 `LNS_Top.v:136` 的第一级寄存器。该级包含宽比较器和优先 mux。

### 9.2 第一级到第二级

`converter.v` 包含绝对值/符号处理、前导位判断、大型分段查表、CSA/CPA 和指数处理。该文件规模较大，组合深度需要单独由综合报告确认。

### 9.3 第二级到第三级

`CSA_tree.v` 包含多组部分积、多个 CSA 层级及最终 CPA，全部位于第 2、3 级寄存器之间，是明显的候选关键路径。

### 9.4 第三级到第四级

`LNS_Top` 并行实例化 5 个 `anticonverter`。每个实例均包含大型 case 查表、饱和处理和可变移位逻辑，再进入第 4 级寄存器，也是明显的候选关键路径。

大型 case 在 FPGA/ASIC 工具中可能实现为深 mux 网络，也可能被优化为 ROM/LUT 结构；实际结果取决于综合器与目标器件，不能仅凭 RTL 假定其时序成本。

## 10. 位宽与参数化问题

### 10.1 明确的隐式截断

`LNS_Top.v:581`：

```verilog
wire [7:0] exponent;
assign exponent = {1'b0, float_y[30:23]} + 8'b10000001;
```

左操作数是 9 位，表达式结果宽于 8 位，赋给 `exponent` 时最高位被静默截断。这可能是有意做模 256 指数运算，也可能丢失溢出信息；目前代码没有显式表达这一意图。

### 10.2 reset 常量和参数宽度不一致

- `LNS_Top.v:149`：31 位常量赋给默认 30 位的 `logc_stage_K_custom_reg`
- `LNS_Top.v:235`：159 位常量赋给默认 160 位的 `lns_stage_logc`
- 多处寄存器声明使用参数宽度，但 reset 和数据赋值固定写成 32、30 或 160 位

当前默认参数下，部分赋值只是零扩展/截断，未必改变零值，但这使参数化名存实亡，也容易在修改 WIDTH 后引入真正的功能与时序问题。

### 10.3 大量隐式扩展

静态 lint 在近似查表逻辑中报告大量窄常量赋给宽信号的隐式扩展。多数可能是有意的零扩展，本身不等同于 bug；但应区分无符号零扩展和有符号扩展，特别是近似系数、指数与移位量参与混合运算的位置。

## 11. 静态 lint 摘要

曾以 `LNS_Top` 为 top 对上述六个文件运行只读 Verilator lint，未进行仿真或综合。高信号告警包括：

- 4 个 latch 告警
- 1 个不完整 case 告警
- 8 个组合块 nonblocking assignment 告警
- 2 个位宽截断告警
- 大量位宽扩展告警，主要来自生成式查表常量

告警数量不应直接当作严重度；最需要优先处理的是活跃路径上的 latch、输出延迟不一致，以及 CPA 的数据/控制/状态跨拍错位。

## 12. 建议的处理顺序

以下是后续设计决策与验证顺序，不代表本次已经修改代码：

1. **先定义 XCORE 时序契约**：每种 opcode 是统一固定延迟，还是允许 opcode-specific latency；`en=0` 时究竟冻结、冲刷还是继续前进。
2. **统一或准确描述输出延迟**：若架构只能表达 XCORE 固定 4 拍，则各输出必须在接口处同拍；若允许不同延迟，则 ADG/operation metadata 和 mapper 必须能逐 opcode 表达。
3. **让数据、模式、输出选择与 exception flags 等深流水**：尤其是 CPA 树的 `float_flag`、overflow/underflow 和最终 `tri_result`。
4. **消除所有活跃路径 latch 与组合块非阻塞赋值**：这是进入时序分析前应完成的 RTL 基线清理。
5. **明确 valid/enable 方案**：要么 BlackBox 跟随 `io.en` 冻结并携带 valid，要么明确禁止执行中停顿，并让外层所有相关状态遵守同一规则。
6. **确认复位释放策略**：在时钟域边界实现或证明异步置位、同步释放，并添加对应 recovery/removal 约束。
7. **最后以真实目标频率做逐级 STA**：分别检查 segSel、converter、CSA tree、anticonverter 和 CPA tree，而不是只看整个 top 的单条最差路径。

## 13. 最终判断

从静态 RTL 看，当前 Verilog 部分至少存在三个会影响功能正确性的时序问题：

1. tri 路径与 XCORE 的 4 周期声明不一致；
2. CPA 树的数据、模式位和异常标志未按同一事务对齐；
3. `anticonverter` 活跃组合路径中存在 latch。

其余问题——缺少 enable/valid、组合块使用非阻塞赋值、异步复位释放以及深组合路径——会进一步降低仿真一致性、停顿安全性和时序收敛的可控性。建议在评价具体 Fmax 之前，先解决或明确前三项功能性时序契约问题；否则即使 STA 收敛，mapper 仍可能在错误的周期消费数据。
