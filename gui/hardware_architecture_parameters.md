# LinGo 硬件架构参数（GUI 配置参考）

本文依据当前 `hardware/generate_fgra_spec.py`、`FusionSpec.scala`、`FgraParam.scala` 和 `LinGoWithAXI.scala` 整理。默认值以 Python 架构生成器为准。每项采用“参数名一行、解释一行”的格式；`Architecture.*` 是生成器输入，`fgra_*` 等是输出 JSON 字段，二者不能直接混用。

GUI 应通过布局、实例模板和全局参数调用生成器。修改架构后需重新生成 RTL、ADG、配置规格并重新映射。生成器的基本检查不等于所有参数组合均被 RTL 和 mapper 支持。

标记含义：**可设置**为实际配置入口；**实例优先**表示显式实例值覆盖全局默认；**保留字段**表示当前 LinGo AXI 顶层没有接入对应硬件功能；**固定**表示当前实现不支持自由修改。所有自动联动、自动派生及顶层强制覆盖项集中列在文档末尾。

## 一、PE 模板与单实例参数

`Architecture.pe_profiles`  
【可设置】PE 模板字典，默认提供 basic、unified、xcore、acc、div_mul、div 六类；可添加模板并在布局中引用，模板名本身不是硬件操作。

`Architecture.pe_overrides`  
【可设置】按 `(row, col)` 覆盖某个 PE 的模板字段；坐标从 0 开始，覆盖只作用于该实例，不能越过布局范围。

`Architecture.pe_profiles.<name>.gpe_mode / Architecture.pe_overrides[(row, col)].gpe_mode`  
【可设置】PE 类型：0 为普通 GPE，1 为 Unified，2 为 XCore；默认取所选模板的类型。切换类型时应同时设置合法的 operations。

`Architecture.pe_profiles.<name>.operations / Architecture.pe_overrides[(row, col)].operations`  
【可设置】非空操作名列表，决定该 PE 支持的运算；必须使用现有硬件操作。Unified 不支持 FDIV，也不能同时包含 FMUL 和 MUL；XCore 必须为 ["XCORE"]；普通 PE 若使用 MAC，当前实现还要求包含 ACC。FCMP、FADDSUB 等操作组由 Scala loader 展开。

`Architecture.pe_profiles.<name>.num_input_lut / Architecture.pe_overrides[(row, col)].num_input_lut`  
【可设置】PE LUT 输入数，非负整数；basic、unified、xcore 默认 0，acc、div_mul、div 默认 2。改变此值会改变适用 PE 的 FG 端口和 LUT 配置规模，具体效果取决于 PE 类型。

`Architecture.pe_profiles.<name>.max_delay_cg / Architecture.pe_overrides[(row, col)].max_delay_cg`  
【可设置】PE 粗粒度输入延迟资源的最大周期数，非负整数；当前模板默认 16，用于匹配输入到达时间，不是该 PE 固定执行延迟。

`Architecture.pe_profiles.<name>.max_delay_fg / Architecture.pe_overrides[(row, col)].max_delay_fg`  
【可设置】PE 细粒度输入延迟资源的最大周期数，非负整数；当前模板默认 8。XCore 当前不提供 FG 输入输出，该值不能为它创建 FG 端口。

`fgra_gpe_num_reg_rf_for_lut`  
【可设置】LUT 使用的寄存器文件深度，默认 1；作用于带 LUT 的适用 PE，需为硬件可支持的正整数。

`fgra_gpe_in_from_dir`  
【可设置】PE 输入连接方向列表，默认 [4,5,7,6]；方向编码为 W=0、N=1、E=2、S=3、NW=4、NE=5、SE=6、SW=7。现有网格连接使用对角方向，其他方向组合须核查连接实现。

`fgra_gpe_out_to_dir`  
【可设置】PE 输出连接方向列表，默认 [4,5,7,6]，方向编码同上；列表顺序影响端口编号，不宜自动排序。

`logWidth`  
【可设置，高级】XCore LNS 系数的位宽，默认 32 bit；改变内部运算与配置规模，修改前需核查 LNS 和 Verilog 黑盒的实际位宽支持。

`maxSeg`  
【可设置，高级】XCore 分段近似的最大段数，默认 6；影响系数、阶数、偏置及断点配置规模，修改前需核查黑盒端口和配置容量，不能仅依据生成器接受整数就视为可运行。

## 二、IOB 模板与地址生成

`Architecture.iob_template`  
【可设置】所有 IOB 的基础模板，默认 {iob_mode:2, has_io_fg:true, max_delay_cg:2, max_delay_fg:2}；独立于全局 IOB 默认字段。

`Architecture.iob_overrides`  
【可设置】按 `(side, col)` 覆盖单个 IOB；side=0 为上侧，side=1 为下侧，列编号从 0 开始。

`Architecture.iob_template.iob_mode / Architecture.iob_overrides[(side, col)].iob_mode`  
【可设置】IOB 模式：1 为 FIFO，2 为 SRAM，3 为 TASK_COND_EXIT；当前实例默认 2。该模式影响 IOB 端口和控制逻辑，模式 3 也具有地址与数据输入。

`Architecture.iob_template.has_io_fg / Architecture.iob_overrides[(side, col)].has_io_fg`  
【可设置】是否提供 IOB 的细粒度 IO，布尔值，默认 true；须与 FG 网络连接范围配套。

`Architecture.iob_template.max_delay_cg / Architecture.iob_overrides[(side, col)].max_delay_cg`  
【可设置】IOB 粗粒度输入延迟资源的最大周期数，非负整数，默认 2。

`Architecture.iob_template.max_delay_fg / Architecture.iob_overrides[(side, col)].max_delay_fg`  
【可设置】IOB 细粒度输入延迟资源的最大周期数，非负整数，默认 2。

`fgra_iob_sram_add_reg`  
【可设置】是否在 IOB SRAM 接口增加寄存级，默认 true；当前 IOController 对应写/读延迟为 1/2 周期，关闭后为 0/1 周期，映射延迟模型也随之改变。

`fgra_iob_ag_nest_levels`  
【可设置】IOB 地址生成器支持的循环嵌套层数，默认 3；每层提供 stride 和 cycles 配置。

`fgra_iob_lg_max_stride`  
【可设置important】每层地址步进的有符号配置位数，默认 11；步进单位为阵列数据字，不能按字节或无符号范围解释。

`fgra_iob_lg_max_lat`  
【可设置】IOB 启动延迟配置的位数，默认 6；表示可配置范围，不是固定启动延迟。

`fgra_iob_lg_max_cycles`  
【可设置important】每层循环次数配置及相关计数器的位数，默认 13；不是某个任务实际执行次数。

`fgra_iob_lg_max_ii`  
【可设置】IOB 发起间隔 II 配置及计数器的位数，默认 4；不是把 II 固定为 4。

## 三、GIB 互连模板与轨道

`Architecture.cg_gib_template`  
【可设置】CG GIB 基础模板，默认 {diag_iopin_connect:true, fclist:[2,2,2]}；设为 None 时才使用全局 CG 对角连接和 flexibility 字段生成模板。

`Architecture.fg_gib_template`  
【可设置】FG GIB 基础模板，默认 {diag_iopin_connect:true, fclist:[2,2,2]}；设为 None 时才使用全局 FG 对角连接和 flexibility 字段生成模板。

`Architecture.cg_gib_overrides`  
【可设置】按 `(row, col)` 覆盖单个 CG GIB，坐标对应完整网格的交点；R×C PE 阵列的 CG GIB 网格为 (R+1)×(C+1)。

`Architecture.fg_gib_overrides`  
【可设置】按 `(row, col)` 覆盖单个 FG GIB，坐标对应筛选后的 FG 网格交点，不是未筛选的原始 PE 坐标。

`Architecture.cg_gib_template.diag_iopin_connect / Architecture.cg_gib_overrides[(row, col)].diag_iopin_connect`  
【可设置】CG GIB 是否允许对角方向 IO 引脚之间的连接，布尔值，默认 true。

`Architecture.fg_gib_template.diag_iopin_connect / Architecture.fg_gib_overrides[(row, col)].diag_iopin_connect`  
【可设置】FG GIB 是否允许对角方向 IO 引脚之间的连接，布尔值，默认 true。

`Architecture.cg_gib_template.fclist / Architecture.cg_gib_overrides[(row, col)].fclist`  
【可设置】CG 连接灵活度，三个非负整数依次为 [num_itrack_per_ipin, num_otrack_per_opin, num_ipin_per_opin]，实例默认 [2,2,2]；分别描述输入引脚连接轨道、输出引脚连接轨道及输出引脚直连输入引脚的规模，实际连接取决于轨道数与引脚数。

`Architecture.fg_gib_template.fclist / Architecture.fg_gib_overrides[(row, col)].fclist`  
【可设置】FG 连接灵活度，字段顺序和含义与 CG 相同，实例默认 [2,2,2]。

`fgra_gib_num_track_cg`  
【可设置】CG 网络每方向的轨道数，默认 1；增加可提供更多粗粒度路由资源，也增加互连开销。

`fgra_gib_num_track_fg`  
【可设置】FG 网络每方向的轨道数，默认 1；FG 轨道传送 1 bit 控制信号。

`fgra_gib_track_reged_mode_cg`  
【可设置】CG 轨道寄存模式：0 不加寄存器，1 按棋盘式位置给部分 GIB 加寄存器，2 全部 GIB 加寄存器；默认 1。

`fgra_gib_track_reged_mode_fg`  
【可设置】FG 轨道寄存模式，取值含义同 CG，默认 1。

## 四、配置编码与接口

`fgra_cfg_data_width`  
【可设置】配置总线数据位宽，默认 32 bit；生成器要求正整数且为 8 的倍数，修改会改变配置打包和块内配置字数量。

`fgra_cfg_addr_width`  
【可设置】配置总线地址位宽，默认 14 bit；高位选择配置块，低位寻址块内配置字，必须大于 fgra_cfg_blk_offset，阵列扩大时不会自动增大。

`fgra_cfg_blk_offset`  
【可设置】配置地址中块内偏移占用的位数，默认 6；应满足 0≤offset<fgra_cfg_addr_width，每块配置字数量和全阵列块数量均须能被对应位段编码。

`fgra_cfg_addr_width_align`  
【可设置】配置记录在配置 SPM 中存储地址时使用的对齐位宽，默认 16 bit；每条记录宽度为 fgra_cfg_data_width+该值，需能容纳实际配置地址，并与配置打包工具保持一致。

`id_width`  
【可设置】AXI4 事务 ID 位宽，默认 8 bit；直接用于当前 AXI4Scratchpad 接口。

## 五、全局默认值（实例优先）

`fgra_gpe_num_input_lut`  
【实例优先】PE 全局默认 LUT 输入数，默认 0；当前生成器始终生成显式 PE 实例表，实际应编辑 PE 模板或覆盖中的 num_input_lut。

`fgra_gpe_operations`  
【实例优先】PE 全局默认操作列表；当前实际运算能力来自每个 PE 实例的 operations，修改此字段不会覆盖显式 PE 模板。

`fgra_max_delay_cg`  
【实例优先】PE/IOB fallback 的粗粒度最大输入延迟，默认 4；当前显式 PE 模板为 16、IOB 模板为 2，不随本字段修改。

`fgra_max_delay_fg`  
【实例优先】PE/IOB fallback 的细粒度最大输入延迟，默认 8；当前显式实例使用各自模板值。

`fgra_iob_mode`  
【实例优先】IOB 全局默认模式，默认 3；当前实际 IOB 实例模板为模式 2，GUI 应主要编辑实例模板。

`fgra_iob_has_io_fg`  
【实例优先】IOB 全局默认 FG IO 开关，默认 true；实际由显式 IOB 实例的 has_io_fg 决定。

`fgra_gib_diag_iopin_connect_cg`  
【实例优先】CG GIB 全局默认对角 IO 连接开关，默认 true；仅在 cg_gib_template=None 时被生成器用于创建基础模板，不覆盖显式实例。

`fgra_gib_diag_iopin_connect_fg`  
【实例优先】FG GIB 全局默认对角 IO 连接开关，默认 true；仅在 fg_gib_template=None 时被生成器用于创建基础模板。

`fgra_gib_connect_flexibility_cg.num_itrack_per_ipin`  
【实例优先】CG 输入引脚连接轨道的全局默认灵活度，默认 2；仅在 cg_gib_template=None 时用于生成 fclist[0]。

`fgra_gib_connect_flexibility_cg.num_otrack_per_opin`  
【实例优先】CG 输出引脚连接轨道的全局默认灵活度，默认 4；仅在 cg_gib_template=None 时用于生成 fclist[1]。

`fgra_gib_connect_flexibility_cg.num_ipin_per_opin`  
【实例优先】CG 输出引脚直接连接输入引脚的全局默认灵活度，默认 4；仅在 cg_gib_template=None 时用于生成 fclist[2]。

`fgra_gib_connect_flexibility_fg.num_itrack_per_ipin`  
【实例优先】FG 输入引脚连接轨道的全局默认灵活度，默认 2；仅在 fg_gib_template=None 时用于生成 fclist[0]。

`fgra_gib_connect_flexibility_fg.num_otrack_per_opin`  
【实例优先】FG 输出引脚连接轨道的全局默认灵活度，默认 4；仅在 fg_gib_template=None 时用于生成 fclist[1]。

`fgra_gib_connect_flexibility_fg.num_ipin_per_opin`  
【实例优先】FG 输出引脚直接连接输入引脚的全局默认灵活度，默认 4；仅在 fg_gib_template=None 时用于生成 fclist[2]。

## 六、固定项与当前未接入的保留字段

这些字段用于说明输入规格的边界；GUI 不应将它们展示为已验证可改变当前 RTL 的普通硬件选项。

`fgra_gpe_num_reg_rf_for_alu`  
【固定】ALU 寄存器文件参数，默认 1；当前生成器明确要求等于 1，GUI 应只读。

`fgra_iob_num_sides`  
【固定】IOB 所在侧数，默认且必须为 2；当前只支持上下两侧，不能通过设置 4 启用左右两侧。

`fgra_cfg_sram_add_reg`  
【保留字段】原配置 SRAM 接口的附加寄存级开关，默认 false；当前 LinGoController 实例化 ConfigController 时固定 readLatencySram=1，没有读取此开关。

`fgra_support_multiple_precision`  
【保留字段】原多精度功能开关，默认 false；当前阵列实现未读取此字段，不能靠切换它启用多精度硬件。

`spad_addr_num`  
【保留字段】原规格中的 SPM 地址资源数量参数，默认 5；当前 LinGo AXI 顶层没有用它决定 bank 数、地址空间或端口数。

`fgra_exe_lg_max_ii`  
【保留字段】原执行控制器最大 II 的位数参数，默认 4；当前执行控制使用 LinGoController 的 CSR 与状态机，不读取此字段。

`fgra_exe_lg_max_execute_cycles`  
【保留字段】原执行控制器最大执行周期数的位数参数，默认 16；当前 LinGoController 不读取此字段。

`fgra_exe_lg_max_loop_cycles`  
【保留字段】原执行控制器最大循环周期数的位数参数，默认 10；当前 LinGoController 不读取此字段。

`dma_lg_max_burst_size`  
【保留字段】原 DMA 最大 burst 大小的 log2 参数，默认 5；当前顶层提供 AXI slave，没有实例化由此参数控制的 DMA master。

`dma_num_req_in_flight`  
【保留字段】原 DMA 可并行未完成请求数量，默认 8；不控制当前 AXI slave 的并发能力。

`ls_stream_queue_depth`  
【保留字段】原 load/store 流缓存队列深度，默认 2；当前 LinGo AXI 顶层没有接入对应队列。

`rs_cmd_queue_depth`  
【保留字段】原命令保留站队列深度，默认 16；当前 LinGoController 不使用该队列。

`rs_exe_queue_depth`  
【保留字段】原执行保留站队列深度，默认 4；当前 LinGoController 不使用该队列。

`rs_load_queue_depth`  
【保留字段】原 load 保留站队列深度，默认 8；当前 LinGoController 不使用该队列。

`rs_store_queue_depth`  
【保留字段】原 store 保留站队列深度，默认 8；当前 LinGoController 不使用该队列。

`tlb_num_ways`  
【保留字段】原 TLB 的 way 数，默认 32；当前 LinGo AXI 顶层没有实例化 TLB。

`tlb_is_shared`  
【保留字段】原 TLB 是否共享，默认 true；当前 LinGo AXI 顶层没有对应功能。

## 七、自动联动、自动派生与强制覆盖项（集中放在最后）

“自动联动输入”仍可手动设置；“自动派生输出”应只读。仅有校验约束的字段不会被生成器自动修正，需由 GUI 同步或提示用户处理。顶层派生字段写入 resolved spec，不是 Python 生成器支持的 parameters 键。

`Architecture.pe_layout`  
【可设置，自动联动输入】矩形二维 PE 布局，元素为模板名或完整 PE 字典，当前 6×6；改变尺寸会自动重建 PE、IOB、CG/FG GIB 表、行列数、bank 数及默认 FG 范围，未显式设置的 coalesce 也跟随列数。已有单实例覆盖坐标不会自动迁移，越界会报错。

`fgra_num_row`  
【自动派生，只读】PE 行数，由 pe_layout 的行数生成，当前 6；禁止通过 parameters 覆盖，GUI 的行数控件应修改布局。

`fgra_num_colum`  
【自动派生，只读】PE 列数，由 pe_layout 的列数生成，当前 6；字段拼写必须保留 colum，禁止通过 parameters 覆盖，GUI 的列数控件应修改布局。

`fgra_iob_sram_banks_coalesce`  
【可设置，自动联动输入/默认跟随列数】每组互连的 SPM bank 数；未设置或设为 None 时取列数，当前为 6；显式设置必须为正整数并整除每侧列数。改变后自动重算 IOB 地址宽度；新 RTL/ADG 会反映新的分组与 IOB 可访问范围。当前 6 列可选 1、2、3、6；显式值不会在列数变化时自动调整，整除失败会报错。

`spad_bank_lg_size`  
【可设置，自动联动输入】单个数据 bank 的字节容量 log2，默认 12，即 4 KiB；修改会自动重算 IOB 地址宽度，并在顶层影响 SRAM 深度、SPM 地址位宽和 AXI 地址空间。需能容纳端口数据字，生成器接受非负整数不代表任意小容量都能生成 RTL。

`spad_cfg_lg_size`  
【可设置，顶层联动输入】独立配置 SPM 的字节容量 log2，默认 12，即 4 KiB；顶层据此生成配置 SRAM 深度、配置 bank 地址窗口与总 AXI 地址宽度；它不改变数据 bank 数，也不会自动求解整个架构需要多少配置容量。

`fgra_iob_sram_addr_width`  
【自动派生，只读】IOB 按字节计的地址宽度，公式为 spad_bank_lg_size+ceil(log2(coalesce))，当前 15；coalesce=3 时为 14。非 2 的幂分组会留下无效 bank 编码，不能将 2^地址宽度直接解释为全部可用容量。

`spad_num_banks`  
【自动派生，只读】数据 SPM bank 数=2×列数，当前 12；不包含独立配置 SPM，禁止通过 parameters 覆盖。数据总容量为该值×2^spad_bank_lg_size 字节。

`fgra_gpe_fg_rows`  
【可设置，默认自动派生】接入 FG 网络的 PE 行索引，默认 None 自动展开为所有行，当前 [0,1,2,3,4,5]；显式列表必须递增、不重复、不越界，修改会改变 FG GIB 网格尺寸。列/行尺寸变化不会自动修正已显式设置的列表，缩减范围还需检查 FG 端口连通性。

`fgra_gpe_fg_columns`  
【可设置，默认自动派生】接入 FG 网络的 PE 列索引，默认 None 自动展开为所有列，当前 [0,1,2,3,4,5]；约束与 FG 行索引相同，修改会改变 FG GIB 网格尺寸。

`fgra_gpes`  
【自动生成，只读】R×C PE 实例表，由 pe_layout、pe_profiles 和 pe_overrides 生成；禁止直接通过 parameters 覆盖，GUI 应编辑布局和单实例属性。

`fgra_iobs`  
【自动生成，只读】2×C IOB 实例表，由列数、iob_template 和 iob_overrides 生成；禁止直接通过 parameters 覆盖。

`fgra_cg_gibs`  
【自动生成，只读】(R+1)×(C+1) CG GIB 实例表，由布局尺寸、cg_gib_template 和 cg_gib_overrides 生成。

`fgra_fg_gibs`  
【自动生成，只读】(FG 行数+1)×(FG 列数+1) FG GIB 实例表，由 FG 范围、fg_gib_template 和 fg_gib_overrides 生成。

`fgra_data_width`  
【可设置，顶层联动输入/校验约束】阵列数据及 SPM 的 IOB 端口位宽，默认 32 bit；顶层自动改变 SRAM B 端口和字地址宽度。生成器要求正的整字节位宽，且整除 spad_data_width；不会自动调整 SPM 位宽，浮点与 XCore 的具体位宽支持还需核查。

`spad_data_width`  
【可设置，顶层联动输入/校验约束】SPM 的 AXI 端口位宽，默认 128 bit；顶层据此派生 AXI beat 字节数和 SRAM A 端口深度。必须等于 system_bus_beat_bits，且为 fgra_data_width 的整数倍；当前 AXI4Scratchpad 还要求该位宽为 2 的幂。Python 生成器不会自动同步 system_bus_beat_bits，GUI 若提供一个总线位宽控件，应同时写入两者。

`system_bus_beat_bits`  
【可设置，校验约束】系统总线每个 beat 的位数，默认 128，必须等于 spad_data_width；当前顶层实际用 spad_data_width 创建 AXI 接口，本字段主要保留规格一致性，不能独立设置为另一种位宽。

`fgra_iob_sram_has_mask`  
【顶层强制覆盖，只读】输入规格默认 true；当前 LinGoWithAXI 强制设为 true，并创建支持字节掩码的 SPM，GUI 不应提供可关闭的开关。

`dumpADG`  
【顶层强制覆盖，只读】输入规格默认 true；LinGoWithAXI 强制开启 ADG 导出。

`fgra_adg_filename`  
【生成器可设置，顶层强制覆盖】输入规格默认 fgra_adg.json；LinGoWithAXI 实际改为 LINGO_OUTPUT_DIR/lingo-spec/lingo_adg.json，GUI 若需要改变输出目录，应设置输出环境变量。

`dumpOperationSet`  
【顶层强制覆盖，只读】输入规格默认 true；LinGoWithAXI 强制开启操作集合导出。

`operation_set_filename`  
【生成器可设置，顶层强制覆盖】输入规格默认 operations.json；LinGoWithAXI 实际改为 LINGO_OUTPUT_DIR/lingo-spec/operations.json。

`axi_addr_width`  
【顶层自动派生，只读】AXI 地址位宽=ceil(log2(数据 bank 数×2^spad_bank_lg_size+2^spad_cfg_lg_size))；表示顶层接口地址范围，不是 IOB 地址宽度。

`axi_data_width`  
【顶层自动派生，只读】等于 spad_data_width，当前 128 bit。

`axi_id_width`  
【顶层自动派生，只读】等于 id_width，当前 8 bit。

`axilite_datawidth / axilite_data_width`  
【顶层固定，只读】AXI-Lite CSR 数据位宽固定为 32 bit；两个名称分别用于控制器属性和导出规格。

`axilite_addrspace`  
【顶层自动派生，只读】CSR 空间字节数=0x20+数据 bank 数×4+2×ceil(数据 bank 数/32)×4；随 bank 数改变，当前 88 字节。

`axilite_addr_width`  
【顶层自动派生，只读】AXI-Lite 地址位宽=ceil(log2(axilite_addrspace))，当前 7 bit。

`iob_to_spad_banks`  
【ADG 自动派生，只读】每个 IOB 能访问的物理 bank 列表，按连续 coalesce 个 bank 分组；当前 IOB 0–5 对应 bank 0–5，IOB 6–11 对应 bank 6–11；coalesce 改为 3 后为四个互不跨组的 3-bank 组。
