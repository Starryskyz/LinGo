# LinGo

LinGo 将 `fgra/fgra-mg` 的阵列实现改造成独立的 AXI 插件，不依赖
Chipyard、RocketChip、TileLink 或 RoCC。

## 架构

- 阵列：保留 FGRA-MG 的异构 GPE、Unified GPE、XCore、双粒度互连和 IOB。
- 数据接口：一个 AXI4 slave，连接片上 scratchpad。
- 控制接口：一个 AXI-Lite slave，采用 AuFORA cocotb runtime 的寄存器命名。
- memory partition：已移除，地址不再执行 `startBankIdx/logN/logB` 重排。
- memory-bank coalescing：按 FGRA-MG 的 IOB side 分组。默认 2 个 side、每侧
  6 列，因此 bank `0..5` 和 `6..11` 分别组相连；同一侧的每个 IOB 都能访问
  该侧全部 6 个 bank。
- AXI broadcast：支持按 bank mask 将一次 AXI 写 burst 广播到多个 bank，且每个
  bank 可配置独立的起始地址。
- tile 兼容视图：FGRA-MG 整体作为一个 tile（`tile_num = 1`）。

顶层模块名保持为 `LinGoWithAXI`。接口宽度由输入硬件规格与实际地址空间推导；
默认规格生成 AXI data/address/id 128/16/8 bit；加入 broadcast CSR 后，默认
AXI-Lite data/address 为 32/7 bit。所有宽度均由硬件规格和实际地址空间决定，
cocotb wrapper 应读取生成规格并随硬件更新。

## 生成 Verilog

要求已存在名为 `cocotb` 的 conda 环境，并且环境中可运行 JDK 和 sbt。

```sh
cd LinGo/hardware
./lingo.sh
```

也可以直接运行：

```sh
conda run -n cocotb sbt "runMain fgramemfp.VerilogGen"
```

可用环境变量：

- `LINGO_SPEC`：输入 FGRA-MG 规格，默认
  `src/main/resources/fgra_spec.json`。
- `LINGO_OUTPUT_DIR`：输出目录，默认 `verilog`。

主要输出：

- `verilog/LinGoWithAXI.v`：单文件 RTL，已合并 XCore 外部 Verilog。
- `verilog/lingo-spec/lingo_adg.json`
- `verilog/lingo-spec/axilite_spec.json`
- `verilog/lingo-spec/operations.json`
- `verilog/lingo-spec/lingo_spec.json`

## Scratchpad 地址空间

默认规格有 12 个 4 KiB IOB bank。bank 0 从地址 0 开始，依次连续排列；
配置存储位于所有 IOB bank 之后：

- IOB 数据：`0x0000 .. 0xBFFF`
- 配置数据：`0xC000 .. 0xCFFF`

配置基地址 CSR 写入的是 AXI 字节地址，控制器会转换为配置 SRAM beat 地址。
coalescing 只改变 FGRA IOB 到 bank 的连接关系，不改变以上 AXI 地址映射，也不恢复
已删除的 memory-partition 地址重排。

## AXI-Lite CSR

| 地址 | JSON 字段 | 作用 |
| ---: | --- | --- |
| `0x00` | `reg_cfg_base_addr_0` | 配置在 AXI 空间中的字节地址 |
| `0x04` | `reg_cfg_num_0` | 配置项数量 |
| `0x08` | `reg_cfg_en_tile_0` | bit 0 使能单 tile 配置 |
| `0x0c` | `reg_cfg_en` | 写 bit 0 启动配置 |
| `0x10` | `reg_exe_iob_ens_0` | IOB 使能位 |
| `0x14` | `reg_exe_tile_ens_0` | bit 0 使能单 tile 执行 |
| `0x18` | `reg_exe_start` | 写 bit 0 启动执行 |
| `0x1c` | `reg_exe_done_0` | bit 0 表示执行完成 |
| `0x20` | `reg_bcast_en` | bit 0 使能 AXI 写广播 |
| `0x24` | `reg_bcast_bank_mask_0` | bit `i` 选择广播目标 bank `i` |
| `0x28 + 4*i` | `reg_bcast_base_addr_i` | bank `i` 的广播起始 beat 地址，默认 `i=0..11` |

broadcast base address 以 AXI beat 为单位；默认 AXI 数据宽度为 128 bit，因此一个
beat 为 16 byte。开启 broadcast 时，写 burst 的每个 beat 会写入 mask 选中的所有
bank，地址从各 bank 的 base address 独立递增。

## 接入现有 cocotb-sim

生成后执行：

```sh
./export-cocotb.sh
```

该脚本只同步电路和规格文件，不启动仿真。也可以把目标 circuits 目录作为第一个
参数传入。编译器仍需针对 LinGo ADG/配置位流完成你计划中的配套修改后，再运行
`AuFORA/cocotb-sim`。
