package fgramemfp.axi

import chisel3._
import chisel3.util.Irrevocable

/** Parameters for the standalone AXI4 bundles used by the CGRA top. */
final case class AXI4BundleParameters(
  addrBits: Int,
  dataBits: Int,
  idBits: Int,
  lenBits: Int = 8,
  sizeBits: Int = 3,
  burstBits: Int = 2,
  lockBits: Int = 1,
  cacheBits: Int = 4,
  protBits: Int = 3,
  qosBits: Int = 4,
  respBits: Int = 2
) {
  require(addrBits > 0, "AXI address width must be positive")
  require(dataBits > 0 && dataBits % 8 == 0, "AXI data width must be byte aligned")
  require(idBits > 0, "AXI ID width must be positive")
}

abstract class AXI4BundleBase(val params: AXI4BundleParameters) extends Bundle

abstract class AXI4BundleA(params: AXI4BundleParameters) extends AXI4BundleBase(params) {
  val id = UInt(params.idBits.W)
  val addr = UInt(params.addrBits.W)
  val len = UInt(params.lenBits.W)
  val size = UInt(params.sizeBits.W)
  val burst = UInt(params.burstBits.W)
  val lock = UInt(params.lockBits.W)
  val cache = UInt(params.cacheBits.W)
  val prot = UInt(params.protBits.W)
  val qos = UInt(params.qosBits.W)
}

class AXI4BundleAW(params: AXI4BundleParameters) extends AXI4BundleA(params)
class AXI4BundleAR(params: AXI4BundleParameters) extends AXI4BundleA(params)

class AXI4BundleW(params: AXI4BundleParameters) extends AXI4BundleBase(params) {
  val data = UInt(params.dataBits.W)
  val strb = UInt((params.dataBits / 8).W)
  val last = Bool()
}

class AXI4BundleR(params: AXI4BundleParameters) extends AXI4BundleBase(params) {
  val id = UInt(params.idBits.W)
  val data = UInt(params.dataBits.W)
  val resp = UInt(params.respBits.W)
  val last = Bool()
}

class AXI4BundleB(params: AXI4BundleParameters) extends AXI4BundleBase(params) {
  val id = UInt(params.idBits.W)
  val resp = UInt(params.respBits.W)
}

class AXI4Bundle(params: AXI4BundleParameters) extends AXI4BundleBase(params) {
  val aw = Irrevocable(new AXI4BundleAW(params))
  val w = Irrevocable(new AXI4BundleW(params))
  val b = Flipped(Irrevocable(new AXI4BundleB(params)))
  val ar = Irrevocable(new AXI4BundleAR(params))
  val r = Flipped(Irrevocable(new AXI4BundleR(params)))
}

object AXI4Bundle {
  def apply(params: AXI4BundleParameters): AXI4Bundle = new AXI4Bundle(params)
}
