//===----------------------------------------------------------------------===//
//
// This file implements Data flow graph generation
//
//===----------------------------------------------------------------------===//

#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/IR/Builders.h"
#include "mlir/IR/SymbolTable.h"

#include <iostream>
#include <string>
#include <bit>
#include "ADORA/Dialect/ADORA/IR/ADORA.h"
#include "PassDetail.h"
#include "ADORA/Dialect/ADORA/Transforms/Passes.h"
#include "../../../DFG/inc/mlir_cdfg.h"
#include "ADORA/Misc/DFG.h"

// For Block handle 
// #include "mlir/IR/BlockAndValueMapping.h"
#include "mlir/IR/MLIRContext.h"
#include "mlir/IR/Verifier.h"

// For op transformation
#include "mlir/IR/Operation.h"
#include "mlir/Pass/Pass.h"

// // DFG
// ADORA::KernelOp* _kernel_toDFG;
// int _variable_config_cnt = 0;

using namespace mlir;
using namespace mlir::affine;
using namespace mlir::ADORA;

#define DEBUG_TYPE "adora-dfg-gen"

namespace
{
  class ADORALoopCdfgGenPass : public ADORALoopCdfgGenBase<ADORALoopCdfgGenPass>
  {
    void runOnOperation() override;
  };
} // namespace

void ADORALoopCdfgGenPass::runOnOperation()
{
  mlir::Operation *m = getOperation();
  LLVM_DEBUG(m->dump());

  SmallVector<ADORA::KernelOp> kernels;
  m->walk([&](ADORA::KernelOp kernel) { kernels.push_back(kernel); });
  if (kernels.empty()) {
    m->emitError("No ADORA.kernel found for CDFG generation");
    signalPassFailure();
    return;
  }
  unsigned count = 0;
  std::set<std::string> names;
  for (auto kernel : kernels) {
    std::string name = kernel.getKernelName();
    if (name.empty()) name = "kernel_" + std::to_string(count);
    std::string base = name;
    unsigned suffix = 0;
    while (!names.insert(name).second) name = base + "_" + std::to_string(++suffix);
    LLVMCDFG *graph = new LLVMCDFG(name, GeneralOpNameFile);
    generateCDFGfromKernel(graph, kernel, /*verbose=*/Verbose);
    graph->CDFGtoDOT(name + "_CDFG.dot");
    delete graph;
    ++count;
  }
}

std::unique_ptr<OperationPass<ModuleOp>> mlir::ADORA::createADORALoopCdfgGenPass()
{
  return std::make_unique<ADORALoopCdfgGenPass>();
}
