
autoidx 98

module \affine

  attribute \keep "coarse_wire_9_0"
  wire width 32 $9_0

  attribute \keep "coarse_wire_8_0"
  wire width 32 $8_0

  wire $5_0

  attribute \keep "coarse_wire_57_0"
  wire width 32 $57_0

  wire $56_0

  attribute \keep "coarse_wire_55_0"
  wire width 32 $55_0

  attribute \keep "coarse_wire_54_0"
  wire width 32 $54_0

  wire $53_0

  attribute \keep "coarse_wire_52_0"
  wire width 32 $52_0

  attribute \keep "coarse_wire_51_0"
  wire width 32 $51_0

  attribute \keep "coarse_wire_50_0"
  wire width 32 $50_0

  attribute \keep "coarse_wire_4_0"
  wire width 32 $4_0

  wire $48_0

  wire $47_0

  attribute \keep "coarse_wire_3_0"
  wire width 32 $3_0

  wire $39_0

  attribute \keep "coarse_wire_35_0"
  wire width 32 $35_0

  attribute \keep "coarse_wire_34_0"
  wire width 32 $34_0

  attribute \keep "coarse_wire_33_0"
  wire width 32 $33_0

  attribute \keep "coarse_wire_32_0"
  wire width 32 $32_0

  attribute \keep "coarse_wire_31_0"
  wire width 32 $31_0

  attribute \keep "coarse_wire_30_0"
  wire width 32 $30_0

  attribute \keep "coarse_wire_2_0"
  wire width 32 $2_0

  attribute \keep "coarse_wire_29_0"
  wire width 32 $29_0

  attribute \keep "coarse_wire_28_0"
  wire width 32 $28_0

  attribute \keep "coarse_wire_27_0"
  wire width 32 $27_0

  attribute \keep "coarse_wire_26_0"
  wire width 32 $26_0

  attribute \keep "coarse_wire_25_0"
  wire width 32 $25_0

  attribute \keep "coarse_wire_24_0"
  wire width 32 $24_0

  attribute \keep "coarse_wire_23_0"
  wire width 32 $23_0

  attribute \keep "coarse_wire_22_0"
  wire width 32 $22_0

  attribute \keep "coarse_wire_21_0"
  wire width 32 $21_0

  attribute \keep "coarse_wire_20_0"
  wire width 32 $20_0

  attribute \keep "coarse_wire_1_0"
  wire width 32 $1_0

  wire $19_0

  wire $18_0

  wire $17_0

  attribute \keep "coarse_wire_16_0"
  wire width 32 $16_0

  attribute \keep "coarse_wire_15_0"
  wire width 32 $15_0

  attribute \keep "coarse_wire_14_0"
  wire width 32 $14_0

  attribute \keep "coarse_wire_13_0"
  wire width 32 $13_0

  wire $12_0

  wire $11_0

  cell $lut $abc$92$auto$blifparse.cc:536:parse_blif$97
    parameter \WIDTH 3
    parameter \LUT 8'00110101
    connect \Y $47_0
    connect \A { $5_0 $11_0 $12_0 }
  end

  cell $lut $abc$92$auto$blifparse.cc:536:parse_blif$96
    parameter \WIDTH 3
    parameter \LUT 8'00110101
    connect \Y $48_0
    connect \A { $17_0 $18_0 $19_0 }
  end

  cell $lut $abc$92$auto$blifparse.cc:536:parse_blif$95
    parameter \WIDTH 2
    parameter \LUT 4'0100
    connect \Y $39_0
    connect \A { $19_0 $17_0 }
  end

  cell $lut $abc$92$auto$blifparse.cc:536:parse_blif$94
    parameter \WIDTH 2
    parameter \LUT 4'1000
    connect \Y $56_0
    connect \A { $11_0 $5_0 }
  end

  cell $lut $abc$92$auto$blifparse.cc:536:parse_blif$93
    parameter \WIDTH 2
    parameter \LUT 4'1000
    connect \Y $53_0
    connect \A { $18_0 $17_0 }
  end

  attribute \keep "coarse_node_25"
  cell \SUB $SUB63
    parameter \Y_WIDTH 32
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $25_0
    connect \B $1_0
    connect \A $4_0
  end

  attribute \keep "coarse_node_23"
  cell \SUB $SUB60
    parameter \Y_WIDTH 32
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $23_0
    connect \B $22_0
    connect \A $4_0
  end

  attribute \keep "coarse_node_21"
  cell \SUB $SUB57
    parameter \Y_WIDTH 32
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $21_0
    connect \B $20_0
    connect \A $1_0
  end

  attribute \keep "coarse_node_16"
  cell \SUB $SUB47
    parameter \Y_WIDTH 32
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $16_0
    connect \B $1_0
    connect \A $2_0
  end

  attribute \keep "coarse_node_14"
  cell \SUB $SUB44
    parameter \Y_WIDTH 32
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $14_0
    connect \B $3_0
    connect \A $2_0
  end

  attribute \keep "coarse_node_13"
  cell \SUB $SUB42
    parameter \Y_WIDTH 32
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $13_0
    connect \B $3_0
    connect \A $1_0
  end

  attribute \keep "coarse_node_9"
  cell \SUB $SUB32
    parameter \Y_WIDTH 32
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $9_0
    connect \B $1_0
    connect \A $8_0
  end

  attribute \keep "node_17"
  cell \SLT $SLT50
    parameter \Y_WIDTH 1
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $17_0
    connect \B $32_0
    connect \A $50_0
  end

  attribute \keep "node_5"
  cell \SLT $SLT23
    parameter \Y_WIDTH 1
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $5_0
    connect \B $27_0
    connect \A $51_0
  end

  attribute \keep "coarse_node_24"
  cell \SHL $SHL61
    parameter \Y_WIDTH 32
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $24_0
    connect \B $35_0
    connect \A $23_0
  end

  attribute \keep "coarse_node_15"
  cell \SHL $SHL45
    parameter \Y_WIDTH 32
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $15_0
    connect \B $31_0
    connect \A $14_0
  end

  attribute \keep "node_57"
  cell \SEL $SEL114
    parameter \Y_WIDTH 32
    parameter \C_WIDTH 1
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $57_0
    connect \C $47_0
    connect \B $55_0
    connect \A $15_0
  end

  attribute \keep "node_55"
  cell \SEL $SEL111
    parameter \Y_WIDTH 32
    parameter \C_WIDTH 1
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $55_0
    connect \C $56_0
    connect \B $13_0
    connect \A $16_0
  end

  attribute \keep "node_54"
  cell \SEL $SEL110
    parameter \Y_WIDTH 32
    parameter \C_WIDTH 1
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $54_0
    connect \C $48_0
    connect \B $52_0
    connect \A $24_0
  end

  attribute \keep "node_52"
  cell \SEL $SEL107
    parameter \Y_WIDTH 32
    parameter \C_WIDTH 1
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $52_0
    connect \C $53_0
    connect \B $21_0
    connect \A $25_0
  end

  attribute \keep "coarse_node_10"
  cell \OUTPUT $Output34
    parameter \size "4096"
    parameter \ref_name "z"
    parameter \pattern "4,32,4,32"
    parameter \offset "0,0"
    parameter \multiport "0"
    parameter \A_WIDTH 32
    connect \A $9_0
  end

  attribute \keep "coarse_node_7"
  cell \OUTPUT $Output29
    parameter \size "4096"
    parameter \ref_name "dfy"
    parameter \pattern "4,32,4,32"
    parameter \offset "0,0"
    parameter \multiport "0"
    parameter \A_WIDTH 32
    connect \A $54_0
  end

  attribute \keep "coarse_node_6"
  cell \OUTPUT $Output27
    parameter \size "4096"
    parameter \ref_name "dfx"
    parameter \pattern "4,32,4,32"
    parameter \offset "0,0"
    parameter \multiport "0"
    parameter \A_WIDTH 32
    connect \A $57_0
  end

  attribute \keep "coarse_node_8"
  cell \INPUT $Input31
    parameter \size "4096"
    parameter \ref_name "data0"
    parameter \pattern "4,32,4,32"
    parameter \offset "0,0"
    parameter \multiport "0"
    parameter \Y_WIDTH 32
    connect \Y $8_0
  end

  attribute \keep "coarse_node_4"
  cell \INPUT $Input19
    parameter \size "4224"
    parameter \ref_name "data"
    parameter \pattern "4,32,4,32"
    parameter \offset "0,128"
    parameter \multiport "1"
    parameter \Y_WIDTH 32
    connect \Y $4_0
  end

  attribute \keep "coarse_node_3"
  cell \INPUT $Input16
    parameter \size "4224"
    parameter \ref_name "data"
    parameter \pattern "4,32,4,32"
    parameter \offset "0,-4"
    parameter \multiport "1"
    parameter \Y_WIDTH 32
    connect \Y $3_0
  end

  attribute \keep "coarse_node_2"
  cell \INPUT $Input13
    parameter \size "4224"
    parameter \ref_name "data"
    parameter \pattern "4,32,4,32"
    parameter \offset "0,4"
    parameter \multiport "1"
    parameter \Y_WIDTH 32
    connect \Y $2_0
  end

  attribute \keep "coarse_node_1"
  cell \INPUT $Input10
    parameter \size "4224"
    parameter \ref_name "data"
    parameter \pattern "4,32,4,32"
    parameter \offset "0,0"
    parameter \multiport "1"
    parameter \Y_WIDTH 32
    connect \Y $1_0
  end

  attribute \keep "node_19"
  cell \EQ $EQ54
    parameter \Y_WIDTH 1
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $19_0
    connect \B $34_0
    connect \A $50_0
  end

  attribute \keep "node_18"
  cell \EQ $EQ52
    parameter \Y_WIDTH 1
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $18_0
    connect \B $33_0
    connect \A $50_0
  end

  attribute \keep "node_12"
  cell \EQ $EQ40
    parameter \Y_WIDTH 1
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $12_0
    connect \B $30_0
    connect \A $51_0
  end

  attribute \keep "node_11"
  cell \EQ $EQ38
    parameter \Y_WIDTH 1
    parameter \B_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $11_0
    connect \B $29_0
    connect \A $51_0
  end

  attribute \keep "coarse_node_35"
  cell \CONST $CONST81
    parameter \Y_WIDTH 32
    parameter \VALUE 1
    connect \Y $35_0
  end

  attribute \keep "coarse_node_34"
  cell \CONST $CONST80
    parameter \Y_WIDTH 32
    parameter \VALUE 31
    connect \Y $34_0
  end

  attribute \keep "coarse_node_33"
  cell \CONST $CONST79
    parameter \Y_WIDTH 32
    parameter \VALUE 0
    connect \Y $33_0
  end

  attribute \keep "coarse_node_32"
  cell \CONST $CONST78
    parameter \Y_WIDTH 32
    parameter \VALUE 31
    connect \Y $32_0
  end

  attribute \keep "coarse_node_31"
  cell \CONST $CONST77
    parameter \Y_WIDTH 32
    parameter \VALUE 1
    connect \Y $31_0
  end

  attribute \keep "coarse_node_30"
  cell \CONST $CONST76
    parameter \Y_WIDTH 32
    parameter \VALUE 31
    connect \Y $30_0
  end

  attribute \keep "coarse_node_29"
  cell \CONST $CONST75
    parameter \Y_WIDTH 32
    parameter \VALUE 0
    connect \Y $29_0
  end

  attribute \keep "coarse_node_28"
  cell \CONST $CONST73
    parameter \Y_WIDTH 32
    parameter \VALUE 1
    connect \Y $28_0
  end

  attribute \keep "coarse_node_27"
  cell \CONST $CONST72
    parameter \Y_WIDTH 32
    parameter \VALUE 31
    connect \Y $27_0
  end

  attribute \keep "coarse_node_26"
  cell \CONST $CONST66
    parameter \Y_WIDTH 32
    parameter \VALUE 1
    connect \Y $26_0
  end

  attribute \keep "node_22"
  cell \CINPUT $CInput59
    parameter \size "4224"
    parameter \ref_name "data"
    parameter \pattern "4,32,4,32"
    parameter \offset "0,-128"
    parameter \multiport "1"
    parameter \Y_WIDTH 32
    parameter \A_WIDTH 1
    connect \Y $22_0
    connect \A $48_0
  end

  attribute \keep "node_20"
  cell \CINPUT $CInput56
    parameter \size "4224"
    parameter \ref_name "data"
    parameter \pattern "4,32,4,32"
    parameter \offset "0,-128"
    parameter \multiport "1"
    parameter \Y_WIDTH 32
    parameter \A_WIDTH 1
    connect \Y $20_0
    connect \A $39_0
  end

  attribute \keep "coarse_node_51"
  cell \ACC $ACC106
    parameter \acc_params "0,32,1,32"
    parameter \acc_first "0"
    parameter \Y_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $51_0
    connect \A $28_0
  end

  attribute \keep "coarse_node_50"
  cell \ACC $ACC103
    parameter \acc_params "0,32,32,1"
    parameter \acc_first "0"
    parameter \Y_WIDTH 32
    parameter \A_WIDTH 32
    connect \Y $50_0
    connect \A $26_0
  end
end
