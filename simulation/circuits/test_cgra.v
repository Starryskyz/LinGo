/*

Copyright (c) 2020 Alex Forencich

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

*/

// Language: Verilog 2001

`timescale 1ns / 1ns

/*
 * AXI4 cgra test module
 */
module test_cgra #
(
    parameter DATA_WIDTH = 128,
    parameter ADDR_WIDTH = 18,
    parameter STRB_WIDTH = (DATA_WIDTH/8),
    parameter ID_WIDTH = 6,
    parameter AWUSER_WIDTH = 0,
    parameter WUSER_WIDTH = 0,
    parameter BUSER_WIDTH = 0,
    parameter ARUSER_WIDTH = 0,
    parameter RUSER_WIDTH = 0,

    /// axil parameters
    parameter AXIL_DATA_WIDTH = 32,
    parameter AXIL_ADDR_WIDTH = 10,
    parameter AXIL_STRB_WIDTH = (AXIL_DATA_WIDTH/8)
)
(
    input  wire                     clk,
    input  wire                     rst,

    ///// axi4
    inout  wire [ID_WIDTH-1:0]      axi_awid,
    inout  wire [ADDR_WIDTH-1:0]    axi_awaddr,
    inout  wire [7:0]               axi_awlen,
    inout  wire [2:0]               axi_awsize,
    inout  wire [1:0]               axi_awburst,
    inout  wire                     axi_awlock,
    inout  wire [3:0]               axi_awcache,
    inout  wire [2:0]               axi_awprot,
    inout  wire [3:0]               axi_awqos,
    inout  wire [3:0]               axi_awregion,
    inout  wire [AWUSER_WIDTH-1:0]  axi_awuser,
    inout  wire                     axi_awvalid,
    inout  wire                     axi_awready,
    inout  wire [DATA_WIDTH-1:0]    axi_wdata,
    inout  wire [STRB_WIDTH-1:0]    axi_wstrb,
    inout  wire                     axi_wlast,
    inout  wire [WUSER_WIDTH-1:0]   axi_wuser,
    inout  wire                     axi_wvalid,
    inout  wire                     axi_wready,
    inout  wire [ID_WIDTH-1:0]      axi_bid,
    inout  wire [1:0]               axi_bresp,
    inout  wire [BUSER_WIDTH-1:0]   axi_buser,
    inout  wire                     axi_bvalid,
    inout  wire                     axi_bready,
    inout  wire [ID_WIDTH-1:0]      axi_arid,
    inout  wire [ADDR_WIDTH-1:0]    axi_araddr,
    inout  wire [7:0]               axi_arlen,
    inout  wire [2:0]               axi_arsize,
    inout  wire [1:0]               axi_arburst,
    inout  wire                     axi_arlock,
    inout  wire [3:0]               axi_arcache,
    inout  wire [2:0]               axi_arprot,
    inout  wire [3:0]               axi_arqos,
    inout  wire [3:0]               axi_arregion,
    inout  wire [ARUSER_WIDTH-1:0]  axi_aruser,
    inout  wire                     axi_arvalid,
    inout  wire                     axi_arready,
    inout  wire [ID_WIDTH-1:0]      axi_rid,
    inout  wire [DATA_WIDTH-1:0]    axi_rdata,
    inout  wire [1:0]               axi_rresp,
    inout  wire                     axi_rlast,
    inout  wire [RUSER_WIDTH-1:0]   axi_ruser,
    inout  wire                     axi_rvalid,
    inout  wire                     axi_rready,


    /// axil
    inout  wire [AXIL_ADDR_WIDTH-1:0]  axil_awaddr,
    inout  wire [2:0]             axil_awprot,
    inout  wire                   axil_awvalid,
    inout  wire                   axil_awready,
    inout  wire [AXIL_DATA_WIDTH-1:0]  axil_wdata,
    inout  wire [AXIL_STRB_WIDTH-1:0]  axil_wstrb,
    inout  wire                   axil_wvalid,
    inout  wire                   axil_wready,
    inout  wire [1:0]             axil_bresp,
    inout  wire                   axil_bvalid,
    inout  wire                   axil_bready,
    inout  wire [AXIL_ADDR_WIDTH-1:0]  axil_araddr,
    inout  wire [2:0]             axil_arprot,
    inout  wire                   axil_arvalid,
    inout  wire                   axil_arready,
    inout  wire [AXIL_DATA_WIDTH-1:0]  axil_rdata,
    inout  wire [1:0]             axil_rresp,
    inout  wire                   axil_rvalid,
    inout  wire                   axil_rready
);

LinGoWithAXI uut (
    .clock(clk),
    .reset(rst),
    .io_s_axi_aw_ready(axi_awready),
    .io_s_axi_aw_valid(axi_awvalid),
    .io_s_axi_aw_bits_id(axi_awid),
    .io_s_axi_aw_bits_addr(axi_awaddr),
    .io_s_axi_aw_bits_len(axi_awlen),
    .io_s_axi_aw_bits_size(axi_awsize),
    .io_s_axi_aw_bits_burst(axi_awburst),
    .io_s_axi_aw_bits_lock(axi_awlock),
    .io_s_axi_aw_bits_cache(axi_awcache),
    .io_s_axi_aw_bits_prot(axi_awprot),
    .io_s_axi_aw_bits_qos(axi_awqos),
    .io_s_axi_w_ready(axi_wready),
    .io_s_axi_w_valid(axi_wvalid),
    .io_s_axi_w_bits_data(axi_wdata),
    .io_s_axi_w_bits_strb(axi_wstrb),
    .io_s_axi_w_bits_last(axi_wlast),
    .io_s_axi_b_ready(axi_bready),
    .io_s_axi_b_valid(axi_bvalid),
    .io_s_axi_b_bits_id(axi_bid),
    .io_s_axi_b_bits_resp(axi_bresp),
    .io_s_axi_ar_ready(axi_arready),
    .io_s_axi_ar_valid(axi_arvalid),
    .io_s_axi_ar_bits_id(axi_arid),
    .io_s_axi_ar_bits_addr(axi_araddr),
    .io_s_axi_ar_bits_len(axi_arlen),
    .io_s_axi_ar_bits_size(axi_arsize),
    .io_s_axi_ar_bits_burst(axi_arburst),
    .io_s_axi_ar_bits_lock(axi_arlock),
    .io_s_axi_ar_bits_cache(axi_arcache),
    .io_s_axi_ar_bits_prot(axi_arprot),
    .io_s_axi_ar_bits_qos(axi_arqos),
    .io_s_axi_r_ready(axi_rready),
    .io_s_axi_r_valid(axi_rvalid),
    .io_s_axi_r_bits_id(axi_rid),
    .io_s_axi_r_bits_data(axi_rdata),
    .io_s_axi_r_bits_resp(axi_rresp),
    .io_s_axi_r_bits_last(axi_rlast),

    .io_s_axilite_aw_ready(axil_awready),
    .io_s_axilite_aw_valid(axil_awvalid),
    .io_s_axilite_aw_bits_addr(axil_awaddr),
    .io_s_axilite_aw_bits_prot(axil_awprot),
    .io_s_axilite_w_ready(axil_wready),
    .io_s_axilite_w_valid(axil_wvalid),
    .io_s_axilite_w_bits_data(axil_wdata),
    .io_s_axilite_w_bits_strb(axil_wstrb),
    .io_s_axilite_b_ready(axil_bready),
    .io_s_axilite_b_valid(axil_bvalid),
    .io_s_axilite_b_bits_resp(axil_bresp),
    .io_s_axilite_ar_ready(axil_arready),
    .io_s_axilite_ar_valid(axil_arvalid),
    .io_s_axilite_ar_bits_addr(axil_araddr),
    .io_s_axilite_ar_bits_prot(axil_arprot),
    .io_s_axilite_r_ready(axil_rready),
    .io_s_axilite_r_valid(axil_rvalid),
    .io_s_axilite_r_bits_data(axil_rdata),
    .io_s_axilite_r_bits_resp(axil_rresp)
);

    // VCD Dumping
    //initial begin
    //    $dumpfile("sim_build/test_cgra.vcd");
   //     $dumpvars(0, test_cgra);
   // end

endmodule
