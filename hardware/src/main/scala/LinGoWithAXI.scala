package fgramemfp

import chisel3._
import chisel3.stage.ChiselStage
import chisel3.util.log2Ceil
import fgramemfp.axi.{AXI4Bundle, AXI4BundleParameters, AXI4Scratchpad, AXILiteBundle}
import fgramemfp.spec.FusionSpec

import java.io.File
import java.nio.file.{Files, Paths, StandardOpenOption}

object LinGoParam {
  val outputDir: String = sys.env.getOrElse("LINGO_OUTPUT_DIR", "verilog")
  val specDir = new File(outputDir, "lingo-spec")
  specDir.mkdirs()
  val sourceSpec: String =
    sys.env.getOrElse("LINGO_SPEC", "src/main/resources/fgra_spec.json")
  val adgFile = new File(specDir, "lingo_adg.json").getPath
  val operationFile = new File(specDir, "operations.json").getPath
  val axiliteFile = new File(specDir, "axilite_spec.json").getPath
  val resolvedSpecFile = new File(specDir, "lingo_spec.json").getPath
}

class LinGoWithAXI extends Module {
  override def desiredName = "LinGoWithAXI"
  import LinGoParam._

  FusionSpec.loadSpec(sourceSpec)
  val attrs = FusionSpec.attrs
  attrs("dumpADG") = true
  attrs("dumpOperationSet") = true
  attrs("fgra_adg_filename") = adgFile
  attrs("operation_set_filename") = operationFile
  // Byte masks are required for general AXI transfers. IOB stores still
  // assert every byte lane, preserving the original full-word behavior.
  attrs("fgra_iob_sram_has_mask") = true

  val dataWidth = attrs("fgra_data_width").asInstanceOf[Int]
  val spadDataWidth = attrs("spad_data_width").asInstanceOf[Int]
  val nBanks = attrs("fgra_iob_num_sides").asInstanceOf[Int] *
    attrs("fgra_num_colum").asInstanceOf[Int]
  val axilDataWidth = 32
  val csrWordBytes = axilDataWidth / 8
  val numBankMaskRegs = (nBanks + axilDataWidth - 1) / axilDataWidth
  attrs("axilite_addrspace") = 0x20 + nBanks * csrWordBytes + 2 * numBankMaskRegs * csrWordBytes
  attrs("axilite_datawidth") = 32
  val bankLgBytes = attrs("spad_bank_lg_size").asInstanceOf[Int]
  val cfgLgBytes = attrs("spad_cfg_lg_size").asInstanceOf[Int]
  val idWidth = attrs("id_width").asInstanceOf[Int]
  val axiAddrWidth = log2Ceil(nBanks * (BigInt(1) << bankLgBytes) + (BigInt(1) << cfgLgBytes))
  val axilAddrWidth = log2Ceil(attrs("axilite_addrspace").asInstanceOf[Int])
  attrs("axi_addr_width") = axiAddrWidth
  attrs("axi_data_width") = spadDataWidth
  attrs("axi_id_width") = idWidth
  attrs("axilite_addr_width") = axilAddrWidth
  attrs("axilite_data_width") = 32
  FusionSpec.dumpSpec(resolvedSpecFile)

  val axiParam = AXI4BundleParameters(
    addrBits = axiAddrWidth, dataBits = spadDataWidth, idBits = idWidth)
  val axilParam = AXI4BundleParameters(
    addrBits = axilAddrWidth, dataBits = 32, idBits = 1)

  val io = IO(new Bundle {
    val s_axi = Flipped(new AXI4Bundle(axiParam))
    val s_axilite = Flipped(new AXILiteBundle(axilParam))
  })

  val spad = Module(new AXI4Scratchpad(
    idWidth = idWidth,
    baseAddr = 0,
    spadBanksNum = nBanks,
    lgSizeSpadBank = bankLgBytes,
    lgSizeLastBlock = cfgLgBytes,
    axiBeatBytes = spadDataWidth / 8,
    bPortBytes = dataWidth / 8,
    hasMask = true))
  val controller = Module(new LinGoController(attrs, axiliteFile))

  io.s_axi <> spad.io.s_axi
  io.s_axilite <> controller.io.s_axilite
  spad.io.aclk := clock
  spad.io.aresetn := !reset.asBool
  spad.io.srams <> controller.io.srams_iob
  spad.io.sram_last <> controller.io.sram_cfg
  spad.io.bcast_en := controller.io.bcast_en
  spad.io.bcast_bank_mask := controller.io.bcast_bank_mask
  spad.io.bcast_base_addr := controller.io.bcast_base_addr
}

object VerilogGen extends App {
  val outputDir = LinGoParam.outputDir
  (new ChiselStage).emitVerilog(
    new LinGoWithAXI, Array("-td", outputDir))
  val top = Paths.get(outputDir, "LinGoWithAXI.v")
  val resources = Seq("CPA_tree_with_MAD.v", "CSA_tree.v", "LNS_Top.v",
    "anticonverter.v", "converter.v", "segSel.v")
  resources.foreach { name =>
    Files.write(top, "\n".getBytes("UTF-8"), StandardOpenOption.APPEND)
    Files.write(top, Files.readAllBytes(Paths.get(outputDir, name)),
      StandardOpenOption.APPEND)
  }
  (resources :+ "firrtl_black_box_resource_files.f").foreach { name =>
    Files.deleteIfExists(Paths.get(outputDir, name))
  }
}
