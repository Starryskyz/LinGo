# This includes several libs that extends the linking time
# only the necessary libs are included instead
get_property(dialect_libs GLOBAL PROPERTY MLIR_DIALECT_LIBS)
get_property(conversion_libs GLOBAL PROPERTY MLIR_CONVERSION_LIBS)

# message(PUBLIC "${dialect_libs}")
# message(PUBLIC "${conversion_libs}")

set(LIBS
  # ${dialect_libs}
  # ${conversion_libs}

  # Core
  MLIRIR
  MLIRTransforms
  MLIROptLib
  MLIRParser
  
  # Dialects
  MLIRLLVMDialect
  MLIRLinalgDialect
  MLIRMemRefDialect
  MLIRAffineDialect
  MLIRArithDialect
  MLIRMathDialect
  MLIRFuncDialect
  MLIRSCFDialect
  MLIRMLProgramDialect
  MLIRTensorDialect

 
  # Transforms
  MLIRFuncTransforms
  MLIRLinalgTransforms
  MLIRAffineTransforms
  MLIRSCFTransforms
  MLIRReconcileUnrealizedCasts
  MLIRMemRefTransforms

  
  # Conversion
  MLIRAffineToStandard
  MLIRSCFToControlFlow
  MLIRMemRefToLLVM
  MLIRMathToLLVM
  MLIRMathToLibm
  MLIRArithToLLVM
  MLIRFuncToLLVM
  MLIRLinalgTransforms
  MLIRLinalgToStandard

  #ADORA
  MLIRADORAMisc
  MLIRADORAOps
  MLIRADORAKernelOp
  MLIRADORATransforms
  MLIRADORALowerings
  GeneralCDFGGen

)

list(APPEND LIBS
  MLIRBufferizationDialect MLIRBufferizationTransforms
  MLIRVectorDialect MLIRControlFlowDialect MLIRDLTIDialect MLIRSupport
)

foreach(tool cgra-opt cgrv-opt)
  add_llvm_executable(${tool} cgra-opt.cpp)
  target_link_libraries(${tool} PRIVATE ${LIBS})
  llvm_update_compile_flags(${tool})
  mlir_check_link_libraries(${tool})
  install(TARGETS ${tool} RUNTIME DESTINATION bin)
endforeach()

add_llvm_executable(adora-cdfg ../adora-cdfg/adora-cdfg.cpp)
target_link_libraries(adora-cdfg PRIVATE ${LIBS})
llvm_update_compile_flags(adora-cdfg)
mlir_check_link_libraries(adora-cdfg)
install(TARGETS adora-cdfg RUNTIME DESTINATION bin)
