cmake_minimum_required(VERSION 3.20)
project(ADORAFrontend VERSION 0.1.0 LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17 CACHE STRING "C++ standard")
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(MLIR REQUIRED CONFIG)
if(LLVM_PACKAGE_VERSION VERSION_LESS 18)
  message(FATAL_ERROR "This ADORA source requires the original LLVM/MLIR 18 toolchain; LLVM 15 is not supported.")
endif()
list(APPEND CMAKE_MODULE_PATH "${MLIR_CMAKE_DIR}" "${LLVM_CMAKE_DIR}")
include(TableGen)
include(AddLLVM)
include(AddMLIR)
include(HandleLLVMOptions)

set(LLVM_RUNTIME_OUTPUT_INTDIR "${CMAKE_BINARY_DIR}/bin")
set(LLVM_LIBRARY_OUTPUT_INTDIR "${CMAKE_BINARY_DIR}/lib")
set(MLIR_BINARY_DIR "${CMAKE_BINARY_DIR}")
set(PROJ_INCLUDE_DIR "${PROJECT_SOURCE_DIR}/include")
include_directories(${LLVM_INCLUDE_DIRS} ${MLIR_INCLUDE_DIRS}
  "${PROJECT_SOURCE_DIR}/include" "${PROJECT_BINARY_DIR}/include"
  "${PROJECT_SOURCE_DIR}/lib/DFG/inc")
add_definitions(${LLVM_DEFINITIONS})
add_compile_definitions(ADORA_DEFAULT_OP_NAMES="${PROJECT_SOURCE_DIR}/lib/DFG/Documents/GeneralOpName.txt")

add_subdirectory(include/ADORA)
add_subdirectory(lib)
add_subdirectory(tools/cgra-opt)
install(PROGRAMS tools/adoracc/adoracc.py scripts/cdfg_to_lingo.py
  DESTINATION bin)
install(FILES lib/DFG/Documents/GeneralOpName.txt DESTINATION share/adora)
