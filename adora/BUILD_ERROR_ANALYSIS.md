# ADORA 构建报错分析与手动修改建议

记录日期：2026-10-05。本文仅记录诊断与修改建议，未修改源码或 CMake 配置。

## 1. 复现结果与结论

在 `/data/jrzhang/LinGo/adora` 实际执行：

```bash
cmake --build build -j 16 --target cgra-opt cgrv-opt
```

命令返回码为 **1**，最后输出 `ninja: build stopped: subcommand failed.`。
本轮有 **8 个 C++ 编译任务失败**，涉及 **7 个源码文件**，可归为下面 **5 类 API 兼容问题**。
`cgra-opt` 与 `cgrv-opt` 在 `tools/cgra-opt/CMakeLists.txt` 中由同一份
`cgra-opt.cpp` 和同一组库构建，因此工具入口的同一个错误会出现两次。

本轮明确报出的是编译错误，尚未进入两个可执行文件的链接阶段。
未观察到目标不存在、找不到头文件、链接缺库或内存不足的错误；降低 `-j` 或清空 build
不能解决已确认的接口错误。修复后是否还存在链接或运行问题，需要重新构建验证。

### 当前实际工具链

| 项目 | 实际值 / 证据 |
| --- | --- |
| 构建类型 | `build/CMakeCache.txt`：`CMAKE_BUILD_TYPE=Release` |
| C++ 编译器 | `/usr/bin/c++`，编译命令采用 C++17 |
| MLIR_DIR | `/data/jrzhang/LinGo/Polygeist/llvm-project/install/lib/cmake/mlir` |
| LLVM_DIR | `/data/jrzhang/LinGo/Polygeist/llvm-project/install/lib/cmake/llvm` |
| 安装头文件版本 | `llvm/Config/llvm-config.h`：`LLVM_VERSION_STRING="18.0.0git"` |
| 当前 LLVM 源码 checkout | `77c04bb2a7a2406ca9480bcc9e729b07d2c8d077`（不据此断言安装产物一定由该提交生成） |

`adora/README.md` 记载原 ADORA 所需提交为
`b270525f730be6e7196667925f5a9bfa153262e9`。
本次安装接口与部分 ADORA 调用方式不一致；仅检查 LLVM 主版本为 18，无法保证接口一致。
下述建议均依据**当前 build 实际使用的安装头文件**，以继续使用现有工具链为目标。

## 2. 错误一：AffineForOp::getStep() 已返回 int64_t

典型报错：

```text
error: request for member ‘getSExtValue’ in ‘...getStep()’,
which is of non-class type ‘int64_t’ {aka ‘long int’}
```

当前安装的 `mlir/Dialect/Affine/IR/AffineOps.h.inc:531` 定义为
`int64_t getStep()`。调用结果已经是整数，不能再调用 APInt 的 `getSExtValue()`。

需要修改的全部有效调用如下（行号以本次检查时源码为准）：

| 文件（相对 adora） | 行号 | 调用数量 |
| --- | --- | --- |
| `lib/Dialect/ADORA/Transforms/Loop/AffineLoopUnroll.cpp` | 172 | 1 |
| `lib/Dialect/ADORA/Transforms/Loop/AffineLoopUnrollAndJam.cpp` | 295 | 1 |
| `lib/Dialect/ADORA/Transforms/Loop/AdjustMemoryFootprint.cpp` | 291、292、487 | 4（291 行有两个） |
| `lib/Dialect/ADORA/Utility/Utility.cpp` | 682、686、736、2021 | 4 |
| `lib/DFG/DFGgen.cpp` | 1603、1643 | 2 |

共 **12 处有效调用**。建议只对这些已确认接收者为 `AffineForOp` 的调用做替换：

```cpp
// 修改前
int64_t step = forop.getStep().getSExtValue();
// 建议修改后
int64_t step = forop.getStep();
```

对应的乘法、取模、`std::gcd` 和 builder 参数中，也直接使用 `getStep()`。
`AffineLoopUnrollAndJam.cpp:155` 还有一处注释中的旧写法，不参与编译。
其他真正返回 APInt 的接口仍可能需要 `getSExtValue()`，不要全项目无差别删除。

## 3. 错误二：有符号向下/向上取整除法函数不可用

`lib/Dialect/ADORA/Utility/Utility.cpp` 报错：

```text
error: ‘divideFloorSigned’ was not declared in this scope
error: ‘divideCeilSigned’ was not declared in this scope
```

首次诊断位置为 766、776、793、1048、1057 行；后续表达式也使用相同函数。
需要覆盖全部调用：

- `divideFloorSigned`：766、793（两次）、1048、1049、1051，共 6 次。
- `divideCeilSigned`：776、1057、1058、1059，共 4 次。

当前安装的 `llvm/Support/MathExtras.h` 不提供上述两个名字；
`mlir/Support/MathExtras.h:23,33` 提供对应的 `mlir::ceilDiv` 与 `mlir::floorDiv`。
建议在 `Utility.cpp` 显式增加头文件：

```cpp
#include "mlir/Support/MathExtras.h"
```

并替换调用：

```cpp
// 修改前
divideFloorSigned(a, b)
divideCeilSigned(a, b)
// 建议修改后
mlir::floorDiv(a, b)
mlir::ceilDiv(a, b)
```

这些位置的除数已有正数检查，符合上述接口的非零除数要求。
务必保留有符号取整语义：例如 `floorDiv(-5, 2) == -3`，`ceilDiv(-5, 2) == -2`；
不能直接改成 C++ 的 `/`，否则负数边界计算会改变。不要只加 LLVM 头文件而保留不存在的名字。

## 4. 错误三：AffineExpr 使用了不兼容的自由函数 dyn_cast

`lib/Dialect/ADORA/Utility/Utility.cpp` 的 1006、1017、1027 行触发模板错误：

```text
error: invalid cast of an rvalue expression of type ‘std::nullptr_t’ ...
error: ‘classof’ is not a member of ‘mlir::AffineBinaryOpExpr’
error: ‘classof’ is not a member of ‘mlir::AffineConstantExpr’
```

虽然最后报错位置在 `llvm/Support/Casting.h`，源头是 ADORA 对 `AffineExpr` 的调用方式。
当前安装的 `mlir/IR/AffineExpr.h:89` 提供成员模板 `U dyn_cast() const`。
建议改为成员函数，与本文件其他已使用的写法保持一致：

```cpp
// 1006 行
auto binExpr = expr.dyn_cast<AffineBinaryOpExpr>();
// 1017 行
binExpr = expr.dyn_cast<AffineBinaryOpExpr>();
// 1027 行
auto rhsConst = rhs.dyn_cast<AffineConstantExpr>();
```

保留紧随其后的空值检查。不需要修改 LLVM 的 Casting.h；
也不要批量改写对 `Operation`、`Type`、`Attribute` 等其他类型的自由函数 `dyn_cast`。

## 5. 错误四：LLVMFuncOp 的内存效果属性 setter 名字不同

`lib/Dialect/ADORA/Lowering/KernelCallToLLVM.cpp:250`：

```text
error: ‘class mlir::LLVM::LLVMFuncOp’ has no member named ‘setMemoryEffectsAttr’;
did you mean ‘setMemoryAttr’?
```

已核对 `mlir/Dialect/LLVMIR/LLVMOps.h.inc:8521`，当前接口为：

```cpp
void setMemoryAttr(::mlir::LLVM::MemoryEffectsAttr attr);
```

建议替换为：

```cpp
if (memoryAttr)
  newFuncOp.setMemoryAttr(memoryAttr);
```

保留现有 `LLVM::MemoryEffectsAttr` 的创建逻辑以及三个 `NoModRef` 值，
使原 `readnone` 的内存效果语义继续保留。不要通过删掉整个设置过程绕过编译错误。

## 6. 错误五：Linalg pass 注册函数名不存在

`tools/cgra-opt/cgra-opt.cpp:62`（两个目标都会报错）：

```text
error: ‘registerConvertLinalgToAffineLoopsPass’ is not a member of ‘mlir’;
did you mean ‘createConvertLinalgToAffineLoopsPass’?
```

当前 `mlir/Dialect/Linalg/Passes.h.inc` 提供的是：

- `registerLinalgLowerToAffineLoops()`（847 行）。
- `registerLinalgLowerToAffineLoopsPass()`（854 行，兼容旧名字）。

**建议直接删除第 62 行的无效注册调用。** 原文件第 54 行已调用
`mlir::registerLinalgPasses()`，其实现（915–923 行）包含
`registerLinalgLowerToAffineLoops()`，因此该 pass 已经注册。

如果将来改成逐项注册而不调用 `registerLinalgPasses()`，可以使用：

```cpp
mlir::registerLinalgLowerToAffineLoops();
```

编译器提示的 `createConvertLinalgToAffineLoopsPass()` 是创建 pass 的工厂函数，
单独调用它不能替代命令行 pass 注册。

## 7. 推荐修改顺序与验证

1. 修改 5 个文件中的 12 处 `getStep()` 调用。
2. 在 `Utility.cpp` 增加 MLIR MathExtras 头文件，替换 10 处取整除法调用及 3 处表达式转换。
3. 修改 `KernelCallToLLVM.cpp` 的属性 setter。
4. 删除 `cgra-opt.cpp` 中已由 `registerLinalgPasses()` 覆盖的无效注册调用。
5. 执行原命令验证编译与链接，再检查两个工具的 pass 列表。

以上是 7 个 `.cpp` 文件的局部接口适配，不需要先改 CMake 或重建 LLVM。
从 `adora` 目录执行：

```bash
cmake --build build -j 16 --target cgra-opt cgrv-opt
build/bin/cgra-opt --help
build/bin/cgrv-opt --help
```

确认帮助中仍有 `convert-linalg-to-affine-loops`。可以进一步验证该 pass 能被解析：

```bash
printf 'module {}\n' | build/bin/cgra-opt --convert-linalg-to-affine-loops
printf 'module {}\n' | build/bin/cgrv-opt --convert-linalg-to-affine-loops
```

空 module 测试只验证工具启动与注册，不验证实际 Linalg lowering。
再用现有样例验证 ADORA IR 解析：

```bash
build/bin/cgra-opt examples/vecadd_opt.mlir -o /tmp/adora-cgra-vecadd-parse.mlir
build/bin/cgrv-opt examples/vecadd_opt.mlir -o /tmp/adora-cgrv-vecadd-parse.mlir
```

如果后续需要完整 CDFG 流程，还应单独构建并测试 `adora-cdfg`；它不属于本次命令的目标。
循环展开、访存 footprint、负数边界和 `readnone` lowering 的行为，需在编译通过后用相应输入进一步验证。
本次没有实施建议修改，所以不声称修复后编译、链接或端到端流程已通过。

## 8. 另一条路线：恢复原工具链

如果希望尽量保持 ADORA 源码接口原样，可以在独立目录构建 README 记载的原 LLVM/MLIR 提交，
然后为 ADORA 创建新的 build 目录并同时指定配套的 `MLIR_DIR` 和 `LLVM_DIR`。
不要直接切换或覆盖当前 Polygeist 使用的 LLVM checkout / install。

这条路线成本更高，而且本次未验证该历史工具链是否覆盖所有现存代码调用；
它是备选方案，并非已验证的一键修复。针对当前环境，优先采用上面的局部接口适配。
