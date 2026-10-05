// Already optimized input: tests CDFG extraction without cgeist.
module {
  func.func @vecadd(%a: memref<20xi32>, %b: memref<20xi32>, %c: memref<20xi32>) {
    %a_block = ADORA.BlockLoad %a [0] : memref<20xi32> -> memref<20xi32> {Id = "0", KernelName = "vecadd"}
    %b_block = ADORA.BlockLoad %b [0] : memref<20xi32> -> memref<20xi32> {Id = "1", KernelName = "vecadd"}
    %c_block = ADORA.LocalMemAlloc memref<20xi32> {Id = "2", KernelName = "vecadd"}
    ADORA.kernel {
      affine.for %i = 0 to 20 {
        %x = affine.load %a_block[%i] : memref<20xi32>
        %y = affine.load %b_block[%i] : memref<20xi32>
        %z = arith.addi %x, %y : i32
        affine.store %z, %c_block[%i] : memref<20xi32>
      }
      ADORA.terminator
    } {KernelName = "vecadd"}
    ADORA.BlockStore %c_block, %c [0] : memref<20xi32> -> memref<20xi32> {Id = "2", KernelName = "vecadd"}
    return
  }
}
