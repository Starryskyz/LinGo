# ADORA 优化前端与 CDFG 生成

从 `../adora-compiler` 分离的源码副本，不需要原目录参加构建。
保留 C/MLIR 优化流程和 `cgra-mapper` 使用的同一套
`generateCDFGfromKernel()`。没有复制 ADORA 的硬件 mapper、放置/布线、
配置生成、C/SDK/pytest emitter、ADORATensor/ONNX 前端或硬件描述。
映射与硬件测试使用外部 `../LinGo`。

```text
C --cgeist--> MLIR --adoracc/cgra-opt--> 优化后的 ADORA MLIR
  --adora-cdfg--> 每个 kernel 的 CDFG DOT
  --cdfg_to_lingo.py--> LinGo DFG JSON
  --LinGo mapperPro--> 配置与 cocotb/SDK 调用代码
```

目录和工具：

| 路径/工具 | 内容 |
| --- | --- |
| `include/ADORA`, `lib/Dialect/ADORA`, `lib/Misc` | ADORA 方言、优化 pass 及其依赖 |
| `lib/DFG` | MLIR → CDFG 的实现和操作名转换表 |
| `cgra-opt`、`cgrv-opt` | 同一个优化 driver 的两个名字；原工程实际名称为 `cgra-opt` |
| `adora-cdfg` | 从原 mapper 入口抽出的 MLIR → CDFG 入口，无映射动作 |
| `tools/adoracc/adoracc.py` | C/普通 MLIR → 优化 kernel MLIR，同时导出 CDFG DOT |
| `scripts/cdfg_to_lingo.py` | Graphviz JSON 转换与 LinGo 字段适配 |
| `examples/vecadd_opt.mlir`、`examples/vecadd.c` | 不依赖 cgeist / 完整 C 前端的两个测试输入 |

## 1. 构建环境与命令（尚未执行）

需要 CMake、Ninja、C++17、Python 3.10+ 和 Graphviz `dot`。
完整 C 流程还需要与 MLIR 兼容的 Polygeist `cgeist`。
原 ADORA README 指定 LLVM/MLIR 18，LLVM commit 为
`b270525f730be6e7196667925f5a9bfa153262e9`。
当前工作区的 `../llvm-project` 是 LLVM 15.0.x，不能直接拿它构建本源码；
这里没有做 LLVM 15 API 移植。请使用原 ADORA 所需的 LLVM/MLIR 18 构建或安装目录。
LinGo mapper 是独立程序，不需要和本前端链接同一版 LLVM。

以下命令从工作区根目录执行，第一行路径请换成实际工具链位置：

```bash
export ADORA_LLVM_ROOT="$(pwd)/Polygeist/llvm-project/install"
cmake -S adora -B adora/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DMLIR_DIR="$ADORA_LLVM_ROOT/lib/cmake/mlir" \
  -DLLVM_DIR="$ADORA_LLVM_ROOT/lib/cmake/llvm"
cmake --build adora/build --target cgra-opt cgrv-opt adora-cdfg -j8

export PATH="$PWD/adora/build/bin:$PATH"
```

不需要手动设置 `GeneralOpNameFile`：CMake 会将本源码目录下
`lib/DFG/Documents/GeneralOpName.txt` 的绝对路径编译为默认值，
`adoracc.py` 也会自动设置操作名表路径。仅在需要使用另一份操作名表时，
才设置该环境变量或为 `adora-cdfg` 指定 `--op-names`。

先用 build 目录即可，不需要 install。
如需安装，可在 configure 时加 `-DCMAKE_INSTALL_PREFIX=/your/prefix`，
构建后执行 `cmake --install adora/build`。
移动安装目录后，为 `adora-cdfg` 指定 `--op-names` 或设置
`GeneralOpNameFile=/your/prefix/share/adora/GeneralOpName.txt`。

## 2. 先测试优化后 MLIR → CDFG → LinGo JSON

这一步不需要 cgeist，也不执行映射：

```bash
adora/build/bin/adora-cdfg adora/examples/vecadd_opt.mlir \
  --output-dir adora/out/vecadd

python3 adora/scripts/cdfg_to_lingo.py \
  adora/out/vecadd/vecadd_CDFG.dot \
  -o adora/out/vecadd/vecadd.json \
  --operations LinGo/hardware/verilog/lingo-spec/operations.json

dot -Tpng adora/out/vecadd/vecadd_CDFG.dot \
  -o adora/out/vecadd/vecadd_CDFG.png
```

预期 DOT 中有两个 INPUT、一个 ADD 和一个 OUTPUT，以及访存
`ref_name`、`size`、`offset`、`pattern` 属性。
JSON 保留这些属性，并将 opcode 转为大写、十六进制常量转为十进制位模式。
转换还补齐 `backedge` 和 LinGo 的 `type`（0=data、1=memory、2=control）。
对旧 DOT，以虚线/颜色恢复这些属性。当前桥接以 32-bit 数据路径为测试范围；
不将向量操作拆成标量，不实现 LinGo 自定义算子或细粒度逻辑转换。
`--operations` 会在映射之前检查操作表是否支持图中的 opcode。

## 3. 用 LinGo mapper 映射

需要已有 `LinGo/mapper/build/mapperPro`；没有的话，先按 LinGo mapper
的 README 构建它。这里直接指定输入和架构，避免 `run.sh` 对不存在的
`LinGo/benchmarks/<name>/affine.json` 的默认依赖。

```bash
LinGo/mapper/build/mapperPro SPDLOG_LEVEL=off \
  -c true -m true -o true -t 600000 -i 2000 \
  -q true -v false -C true -e all \
  -p "$PWD/LinGo/hardware/verilog/lingo-spec/operations.json" \
  -a "$PWD/LinGo/hardware/verilog/lingo-spec/lingo_adg.json" \
  -d "$PWD/adora/out/vecadd/vecadd.json"
```

`-C true` 先走粗粒度路径。检查日志中的映射成功数量，以及输出目录中的
`mapped_dfg.dot`、`config.bit`、`vecadd_cocotb.py` 和 `vecadd_sdk.c`。
LinGo mapper 的结果写到输入 JSON 所在目录。进程返回值不能替代映射成功日志检查。

若要仿真，使用 `LinGo/simulation` 现有 `workspace/test_cgra.py` 中的
AXI、时钟复位和 `DeviceRuntime` 初始化方式，为生成的 kernel 写调用和断言。
先查看 `vecadd_cocotb.py` 的函数参数：ADORA 的数组名由 kernel 名和 block Id
生成（本例为 `vecadd:0`、`vecadd:1`、`vecadd:2`，Python 参数会被规范化）。
两个输入用 20 个 `np.int32` 元素，输出用同样大小的零数组；调用后执行
`await runtime.synchronize_all()`，并用 `np.testing.assert_array_equal(c, a + b)`
验证。生成的 `_cocotb.py` 是 kernel 调用模块，需要测试入口，并非完整 cocotb test。

运行你编写的测试模块时，可从 `LinGo/simulation` 执行：

```bash
export PYTHONPATH="$PWD/server:$PWD/workspace:$PWD/../../adora/out/vecadd:${PYTHONPATH:-}"
make MODULE=test_adora_vecadd
```

`test_adora_vecadd.py` 是你按上述方法编写的测试入口名。
映射 ADG、仿真 `circuits/lingo_cgra_adg.json` 与 Verilog 必须对应同一个硬件版本。

## 4. 再测试完整 C → 优化 MLIR → CDFG

将兼容的 `cgeist` 加入 PATH 后，从工作区根目录运行：

```bash
python3 adora/tools/adoracc/adoracc.py adora/examples/vecadd.c \
  --work-dir adora/out/from_c -o adora/out/from_c/vecadd_opt.mlir
```

优化后 MLIR 在 `adora/out/from_c/vecadd_opt.mlir`，CDFG 在
`adora/out/from_c/adora-cc-ir/2_dfgs/`，命令日志在
`adora/out/from_c/adora-cc-ir/tempfiles/pipeline.log`。
也可以将输出 MLIR 交给 `adora-cdfg`，再按第 2、3 步转换和映射。
`adoracc` 本身已经调用 `--adora-kernel-dfg-gen` 生成了 DOT，通常直接转换
`2_dfgs/` 中的图即可，无需再生成一次。

第一个测试先保持默认不自动展开。`--enable-unroll --adg-path ...` 保留了原前端
实现，但其 ADG 资源统计逻辑尚未针对 LinGo 架构验证。
复杂程序有多个 kernel 时，每个 kernel 对应一份图；逐个映射只验证 kernel，
原 C 程序的外围循环、host 运算和多次调用仍需测试入口组织。

## 已做检查与当前状态

未运行 CMake configure、build、MLIR 工具、LinGo 映射或 RTL 仿真。
已检查 Python 语法，并用 Graphviz 生成的测试 JSON 检查常量转换、
访存属性、回边距离、控制/内存依赖类型和非法操作/operand 拒绝。
编译与端到端行为需按上述步骤验证。

分离时的局部修正：去除 ADORATensor 与 LLVM test-pass 链接依赖；
操作名表改为本目录默认路径；`adoracc` 使用临时副本清理 MLIR 属性，
不覆盖用户输入；CDFG pass 在修改 IR 前一次收集 kernel，避免原实现按每个函数
重复遍历整个 module，以及重复 kernel 名造成输出覆盖。
