// Extracted from tools/cgra-mapper/cgra-mapper.cpp: MLIR -> CDFG only.
#include "ADORA/Dialect/ADORA/IR/ADORA.h"
#include "ADORA/Misc/DFG.h"
#include "mlir/InitAllDialects.h"
#include "mlir/Parser/Parser.h"
#include "mlir/IR/Verifier.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/InitLLVM.h"
#include "llvm/Support/raw_ostream.h"
#include <cstdlib>
#include <cctype>
#include <filesystem>
#include <set>

int main(int argc, char **argv) {
  llvm::InitLLVM init(argc, argv);
  llvm::cl::opt<std::string> input(llvm::cl::Positional,
      llvm::cl::desc("<optimized ADORA MLIR>"), llvm::cl::Required);
  llvm::cl::opt<std::string> outputDir("output-dir",
      llvm::cl::desc("Directory for per-kernel CDFG DOT files"),
      llvm::cl::init("."));
  const char *envNames = std::getenv("GeneralOpNameFile");
  llvm::cl::opt<std::string> opNames("op-names",
      llvm::cl::desc("MLIR-to-hardware operation name table"),
      llvm::cl::init(envNames ? envNames : ADORA_DEFAULT_OP_NAMES));
  llvm::cl::opt<bool> verbose("verbose", llvm::cl::init(false));
  llvm::cl::ParseCommandLineOptions(argc, argv, "ADORA MLIR to CDFG\n");

  if (!std::filesystem::is_regular_file(opNames.getValue())) {
    llvm::errs() << "Operation name table not found: " << opNames.getValue() << "\n";
    return 1;
  }
  mlir::DialectRegistry registry;
  registry.insert<mlir::func::FuncDialect, mlir::memref::MemRefDialect,
      mlir::LLVM::LLVMDialect, mlir::linalg::LinalgDialect,
      mlir::math::MathDialect, mlir::scf::SCFDialect,
      mlir::cf::ControlFlowDialect, mlir::vector::VectorDialect,
      mlir::arith::ArithDialect, mlir::affine::AffineDialect,
      mlir::DLTIDialect, mlir::ml_program::MLProgramDialect,
      mlir::tensor::TensorDialect, mlir::bufferization::BufferizationDialect,
      mlir::ADORA::ADORADialect>();
  mlir::MLIRContext context(registry, mlir::MLIRContext::Threading::DISABLED);
  auto module = mlir::parseSourceFile<mlir::ModuleOp>(input.getValue(), &context);
  if (!module || mlir::failed(mlir::verify(*module)))
    return 1;

  // Collect first: generation may clone and rewrite kernel operations.
  llvm::SmallVector<mlir::ADORA::KernelOp> kernels;
  module->walk([&](mlir::ADORA::KernelOp kernel) { kernels.push_back(kernel); });
  if (kernels.empty()) {
    llvm::errs() << "No ADORA.kernel found; run adoracc.py first.\n";
    return 1;
  }
  std::error_code ec;
  std::filesystem::create_directories(outputDir.getValue(), ec);
  if (ec) {
    llvm::errs() << "Cannot create output directory: " << ec.message() << "\n";
    return 1;
  }
  std::set<std::string> names;
  unsigned index = 0;
  for (auto kernel : kernels) {
    std::string name = kernel.getKernelName();
    if (name.empty()) name = "kernel_" + std::to_string(index);
    for (char &c : name)
      if (!(std::isalnum(static_cast<unsigned char>(c)) || c == '_' || c == '-'))
        c = '_';
    std::string base = name;
    unsigned suffix = 0;
    while (!names.insert(name).second) name = base + "_" + std::to_string(++suffix);
    ++index;
    LLVMCDFG *graph = new LLVMCDFG(name, opNames.getValue());
    mlir::ADORA::generateCDFGfromKernel(graph, kernel, verbose.getValue());
    auto path = std::filesystem::path(outputDir.getValue()) / (name + "_CDFG.dot");
    graph->CDFGtoDOT(path.string());
    delete graph;
    if (!std::filesystem::is_regular_file(path) || std::filesystem::file_size(path) == 0) {
      llvm::errs() << "Failed to write CDFG: " << path.string() << "\n";
      return 1;
    }
    llvm::outs() << path.string() << "\n";
  }
  return 0;
}
