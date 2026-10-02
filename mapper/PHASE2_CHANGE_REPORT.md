# mapperPro 二阶段变更报告

## 范围

- 从 `fgra/fgra-mapper` 独立复制为 `mapperPro`，原 mapper 未修改。
- 保留原有映射、配置生成和 legacy 后端。
- 不实现 tile splitting、ping-pong、memory partition 或 broadcast 优化。
- cocotb wrapper 不决定硬件结构；生成参数均来自本次映射所使用的 AuFORApro ADG。

## 新增输出后端

命令行新增：

```text
-e, --output-type all|cocotb|sdk|legacy
```

默认值为 `all`。

- `cocotb`：生成 `<dfg>_cocotb.py` 和 `config.bit`。
- `sdk`：生成 `<dfg>_sdk.c` 和 `config.bit`。
- `all`：从同一次 IO 调度结果同时生成上述 Python、C 和 bit 文件。
- `legacy`：保留原来的 `cgra_execute.c`、`cgra_call.txt` 和 `config.bit`。

## cocotb 后端

生成文件保留 ADORA 原有的 `aux_stream()` 结构。生成的 kernel 直接以映射中的数组名接收 NumPy 数组，例如：

```python
async def affine(runtime: DeviceRuntime, y: np.ndarray,
                 z: np.ndarray, x: np.ndarray):
    ...
```

`aux_stream()` 负责：

1. `apply` 和 `config`；
2. 对每个映射输入执行 `memcpyHostToDevice`；
3. 启动 `execution_start`；
4. 对每个输出执行 `memcpyDeviceToHost`；
5. `release`，随后由 kernel 调用 `synchronize`。

当前 runtime 会在执行与 D2H、下一次执行或释放之间自动等待完成，因此不生成已经删除的 `execution_finish()`。

配置被展开为运行时需要的 16-bit 三元组 `[data_lo, data_hi, cfg_addr]`。IOB enable 按硬件 IOB 数量生成 little-endian byte list。主机输入/输出要求 C-contiguous NumPy buffer，并按 DFG 中的 byte offset 和 byte length 建立 view。

同一 NumPy 数组对应多个映射 IO 时，kernel 从同一个数组参数建立多个 view 并保留为多次 DMA，不使用 broadcast 合并。

## FPGA SDK 后端

生成代码沿用 ADORA SDK 的接口约定：

- `HostToDeviceTransfer`
- `DeviceToHostTransfer`
- `cgra_config`
- `cgra_exe`
- `wait_cgra_all_finish`

默认数据总线基地址为 `0x90000000`，可在平台工程中通过 `AUFORAPRO_AXI_BASE` 覆盖。配置存储地址由 `numIobNodes * iobSpadBankSize` 计算，不写死 cocotb wrapper 参数。

## 构建和使用

构建保持 C++23，并固定使用 conda `lora` 环境：

```bash
./build.sh
./run.sh add cocotb
./run.sh add sdk
./run.sh add all
```

`run.sh` 默认读取：

- `AuFORApro/verilog/auforapro-spec/operations.json`
- `AuFORApro/verilog/auforapro-spec/auforapro_adg.json`
- `fgra/benchmarks/<name>/affine.json`

## 验证

- 在 conda `lora` 中以 C++23 完整编译通过。
- 使用当前 AuFORApro ADG 对临时复制的 `add/affine.json` 完成映射，并由同一次 IO 调度成功生成 cocotb Python、FPGA SDK C 与 config.bit。
- 当前验证 ADG 给出的关键参数是 12 个 IOB、每 bank 4096 bytes、32-bit 配置数据和 14-bit 配置地址，因此配置 scratchpad 基址为 `0xc000`。
- 按二阶段要求，没有运行 cocotb/RTL 仿真。
