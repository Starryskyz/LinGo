package fgramemfp

import chisel3._
import chisel3.util._
import fgramemfp.axi.{AXI4BundleParameters, AXILiteBundle}
import fgramemfp.dsa.{FGRA, SRAMIO}
import fgramemfp.ir.IR

import scala.collection.mutable

/** Standalone AXI-Lite controller for one FGRA-MG array. */
class LinGoController(attrs: mutable.Map[String, Any], regSpecFile: String)
    extends Module with IR {
  val dataWidth = attrs("fgra_data_width").asInstanceOf[Int]
  val cfgDataWidth = attrs("fgra_cfg_data_width").asInstanceOf[Int]
  val cfgAddrWidth = attrs("fgra_cfg_addr_width").asInstanceOf[Int]
  val cfgAddrWidthAlign = attrs("fgra_cfg_addr_width_align").asInstanceOf[Int]
  val nSides = attrs("fgra_iob_num_sides").asInstanceOf[Int]
  val nColumns = attrs("fgra_num_colum").asInstanceOf[Int]
  val nBanks = nSides * nColumns
  val coalesceBanks = attrs("fgra_iob_sram_banks_coalesce").asInstanceOf[Int]
  val spadDataWidth = attrs("spad_data_width").asInstanceOf[Int]
  val bankLgBytes = attrs("spad_bank_lg_size").asInstanceOf[Int]
  val cfgLgBytes = attrs("spad_cfg_lg_size").asInstanceOf[Int]
  val bankAddrWidth = bankLgBytes - log2Ceil(dataWidth / 8)
  val cfgAddrWidthSram = cfgLgBytes - log2Ceil(spadDataWidth / 8)
  val spmAddrWidth = bankLgBytes - log2Ceil(spadDataWidth / 8)
  val hasMask = attrs("fgra_iob_sram_has_mask").asInstanceOf[Boolean]

  val axilDataWidth = attrs("axilite_datawidth").asInstanceOf[Int]
  val axilAddrWidth = log2Ceil(attrs("axilite_addrspace").asInstanceOf[Int])
  require(axilDataWidth == 32, "cocotb compatibility requires 32-bit AXI-Lite")
  require(coalesceBanks == nColumns,
    "AuFORA-style grouping requires one coalesced group per IOB side")
  require(nBanks <= axilDataWidth,
    "The compact broadcast mask CSR requires no more than 32 banks")

  val axilParam = AXI4BundleParameters(
    addrBits = axilAddrWidth, dataBits = axilDataWidth, idBits = 1)
  val io = IO(new Bundle {
    val s_axilite = Flipped(new AXILiteBundle(axilParam))
    val srams_iob = Vec(nBanks,
      Flipped(new SRAMIO(dataWidth, bankAddrWidth, hasMask)))
    val sram_cfg = Flipped(
      new SRAMIO(spadDataWidth, cfgAddrWidthSram, hasMask = false))
    val bcast_en = Output(Bool())
    val bcast_bank_mask = Output(UInt(nBanks.W))
    val bcast_base_addr = Output(Vec(nBanks, UInt(spmAddrWidth.W)))
  })

  // AuFORA-compatible single-tile CSR map.
  val RegCfgBase = 0x00
  val RegCfgNum = 0x04
  val RegCfgTileEn = 0x08
  val RegCfgStart = 0x0c
  val RegExeIobEn = 0x10
  val RegExeTileEn = 0x14
  val RegExeStart = 0x18
  val RegExeDone = 0x1c
  val RegBcastEn = 0x20
  val RegBcastMask = 0x24
  val RegBcastBase = 0x28

  val cfgBase = RegInit(0.U(axilDataWidth.W))
  val cfgNum = RegInit(0.U(axilDataWidth.W))
  val cfgTileEn = RegInit(0.U(axilDataWidth.W))
  val exeIobEn = RegInit(0.U(axilDataWidth.W))
  val exeTileEn = RegInit(0.U(axilDataWidth.W))
  val bcastEn = RegInit(0.U(axilDataWidth.W))
  val bcastMask = RegInit(0.U(axilDataWidth.W))
  val bcastBase = Seq.fill(nBanks)(RegInit(0.U(axilDataWidth.W)))

  val fgra = Module(new FGRA(attrs))
  val cfgCtrl = Module(new ConfigController(
    dataWidthSram = spadDataWidth,
    addrWidthSram = cfgAddrWidthSram,
    hasMaskSram = false,
    readLatencySram = 1,
    cfgDataWidth = cfgDataWidth,
    cfgAddrWidth = cfgAddrWidth,
    cfgAddrWidthAlign = cfgAddrWidthAlign,
    cfgRegNum = fgra.cfgRegNum))

  val sramCoalesce = Module(new SRAMCoalesce(
    dataWidth, bankAddrWidth, hasMask, nBanks, coalesceBanks))
  io.srams_iob <> sramCoalesce.io.orig
  fgra.io.srams <> sramCoalesce.io.coal
  io.sram_cfg <> cfgCtrl.io.sram
  io.bcast_en := bcastEn(0)
  io.bcast_bank_mask := bcastMask(nBanks - 1, 0)
  io.bcast_base_addr.zip(bcastBase).foreach {
    case (out, reg) => out := reg(spmAddrWidth - 1, 0)
  }
  fgra.io.cfg_en := cfgCtrl.io.cfg_en
  fgra.io.cfg_addr := cfgCtrl.io.cfg_addr
  fgra.io.cfg_data := cfgCtrl.io.cfg_data
  cfgCtrl.io.base_addr :=
    (cfgBase >> log2Ceil(spadDataWidth / 8))(cfgAddrWidthSram - 1, 0)
  cfgCtrl.io.cfg_num := cfgNum(cfgAddrWidth - 1, 0)

  val cfgStartPulse = WireDefault(false.B)
  val exeStartPulse = WireDefault(false.B)
  cfgCtrl.io.start := cfgStartPulse && cfgTileEn(0)

  val sExeIdle :: sExeStart :: sExeWaitLow :: sExeRun :: Nil = Enum(4)
  val exeState = RegInit(sExeIdle)
  val exeDone = RegInit(true.B)
  val activeIobEn = RegInit(0.U(nBanks.W))
  fgra.io.start := exeState === sExeStart
  fgra.io.en := exeState =/= sExeIdle
  fgra.io.iob_ens := activeIobEn

  switch(exeState) {
    is(sExeIdle) {
      when(exeStartPulse && exeTileEn(0)) {
        activeIobEn := exeIobEn(nBanks - 1, 0)
        exeDone := false.B
        exeState := sExeStart
      }
    }
    is(sExeStart) { exeState := sExeWaitLow }
    is(sExeWaitLow) {
      when(!fgra.io.done) { exeState := sExeRun }
    }
    is(sExeRun) {
      when(fgra.io.done) {
        exeDone := true.B
        exeState := sExeIdle
      }
    }
  }

  def mergeBytes(oldValue: UInt, newValue: UInt, strb: UInt): UInt =
    Cat((0 until axilDataWidth / 8).reverse.map { i =>
      Mux(strb(i), newValue(8 * i + 7, 8 * i), oldValue(8 * i + 7, 8 * i))
    })

  val wIdle :: wData :: wResp :: Nil = Enum(3)
  val wState = RegInit(wIdle)
  val writeAddr = RegInit(0.U(axilAddrWidth.W))
  io.s_axilite.aw.ready := wState === wIdle
  io.s_axilite.w.ready := wState === wData
  io.s_axilite.b.valid := wState === wResp
  io.s_axilite.b.bits.resp := 0.U

  switch(wState) {
    is(wIdle) {
      when(io.s_axilite.aw.fire) {
        writeAddr := io.s_axilite.aw.bits.addr
        wState := wData
      }
    }
    is(wData) {
      when(io.s_axilite.w.fire) {
        switch(writeAddr) {
          is(RegCfgBase.U) { cfgBase := mergeBytes(cfgBase, io.s_axilite.w.bits.data, io.s_axilite.w.bits.strb) }
          is(RegCfgNum.U) { cfgNum := mergeBytes(cfgNum, io.s_axilite.w.bits.data, io.s_axilite.w.bits.strb) }
          is(RegCfgTileEn.U) { cfgTileEn := mergeBytes(cfgTileEn, io.s_axilite.w.bits.data, io.s_axilite.w.bits.strb) }
          is(RegCfgStart.U) { cfgStartPulse := io.s_axilite.w.bits.data(0) && io.s_axilite.w.bits.strb(0) }
          is(RegExeIobEn.U) { exeIobEn := mergeBytes(exeIobEn, io.s_axilite.w.bits.data, io.s_axilite.w.bits.strb) }
          is(RegExeTileEn.U) { exeTileEn := mergeBytes(exeTileEn, io.s_axilite.w.bits.data, io.s_axilite.w.bits.strb) }
          is(RegExeStart.U) { exeStartPulse := io.s_axilite.w.bits.data(0) && io.s_axilite.w.bits.strb(0) }
          is(RegBcastEn.U) { bcastEn := mergeBytes(bcastEn, io.s_axilite.w.bits.data, io.s_axilite.w.bits.strb) }
          is(RegBcastMask.U) { bcastMask := mergeBytes(bcastMask, io.s_axilite.w.bits.data, io.s_axilite.w.bits.strb) }
        }
        for (i <- 0 until nBanks) {
          when(writeAddr === (RegBcastBase + 4 * i).U) {
            bcastBase(i) := mergeBytes(
              bcastBase(i), io.s_axilite.w.bits.data, io.s_axilite.w.bits.strb)
          }
        }
        wState := wResp
      }
    }
    is(wResp) { when(io.s_axilite.b.fire) { wState := wIdle } }
  }

  val rIdle :: rData :: Nil = Enum(2)
  val rState = RegInit(rIdle)
  val readData = RegInit(0.U(axilDataWidth.W))
  io.s_axilite.ar.ready := rState === rIdle
  io.s_axilite.r.valid := rState === rData
  io.s_axilite.r.bits.data := readData
  io.s_axilite.r.bits.resp := 0.U

  switch(rState) {
    is(rIdle) {
      when(io.s_axilite.ar.fire) {
        readData := MuxLookup(io.s_axilite.ar.bits.addr, 0.U, Seq(
          RegCfgBase.U -> cfgBase,
          RegCfgNum.U -> cfgNum,
          RegCfgTileEn.U -> cfgTileEn,
          RegCfgStart.U -> 0.U,
          RegExeIobEn.U -> exeIobEn,
          RegExeTileEn.U -> exeTileEn,
          RegExeStart.U -> 0.U,
          RegExeDone.U -> exeDone.asUInt,
          RegBcastEn.U -> bcastEn,
          RegBcastMask.U -> bcastMask))
        for (i <- 0 until nBanks) {
          when(io.s_axilite.ar.bits.addr === (RegBcastBase + 4 * i).U) {
            readData := bcastBase(i)
          }
        }
        rState := rData
      }
    }
    is(rData) { when(io.s_axilite.r.fire) { rState := rIdle } }
  }

  apply("reg_bit_width", axilDataWidth)
  apply("axilite_addr_bit_width", axilAddrWidth)
  apply("tile_num", 1)
  apply("tile_iob_bank_num", nBanks)
  apply("cfgmem_baseaddr", nBanks * (1 << bankLgBytes))
  apply("reg_cfg_base_addr_0", f"0x$RegCfgBase%X")
  apply("reg_cfg_num_0", f"0x$RegCfgNum%X")
  apply("reg_cfg_en_tile_0", f"0x$RegCfgTileEn%X")
  apply("reg_cfg_en", f"0x$RegCfgStart%X")
  apply("reg_exe_iob_ens_0", f"0x$RegExeIobEn%X")
  apply("reg_exe_tile_ens_0", f"0x$RegExeTileEn%X")
  apply("reg_exe_start", f"0x$RegExeStart%X")
  apply("reg_exe_done_0", f"0x$RegExeDone%X")
  apply("bcast_base_addr_num", nBanks)
  apply("reg_bcast_en", f"0x$RegBcastEn%X")
  apply("reg_bcast_bank_mask_0", f"0x$RegBcastMask%X")
  apply("reg_bcast_base_addr", f"0x$RegBcastBase%X")
  for (i <- 0 until nBanks)
    apply(s"reg_bcast_base_addr_$i", f"0x${RegBcastBase + 4 * i}%X")
  printIR(regSpecFile)
}
