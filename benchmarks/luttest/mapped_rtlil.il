
autoidx 75

module \affine

  wire $1_0

  attribute \keep "coarse_wire_3_0"
  wire width 32 $3_0

  wire $4_0

  attribute \keep "coarse_wire_5_0"
  wire width 32 $5_0

  attribute \keep "coarse_wire_6_0"
  wire width 32 $6_0

  attribute \keep "coarse_wire_7_0"
  wire width 32 $7_0

  attribute \keep "coarse_wire_8_0"
  wire width 32 $8_0

  attribute \keep "coarse_wire_9_0"
  wire width 32 $9_0

  attribute \keep "coarse_wire_10_0"
  wire width 32 $10_0

  wire $11_0

  wire $12_0

  attribute \keep "coarse_wire_13_0"
  wire width 32 $13_0

  attribute \keep "coarse_wire_14_0"
  wire width 32 $14_0

  attribute \keep "coarse_wire_15_0"
  wire width 32 $15_0

  attribute \keep "coarse_wire_16_0"
  wire width 32 $16_0

  attribute \keep "node_1"
  cell \ULT $ULT1
    parameter \A_WIDTH 32
    parameter \B_WIDTH 32
    parameter \Y_WIDTH 1
    connect \A $7_0
    connect \B $13_0
    connect \Y $1_0
  end

  attribute \keep "coarse_node_2"
  cell \OUTPUT $Output5
    parameter \multiport "0"
    parameter \offset "0,0"
    parameter \pattern "4,20"
    parameter \ref_name "c"
    parameter \size "80"
    parameter \A_WIDTH 32
    connect \A $14_0
  end

  attribute \keep "node_3"
  cell \CINPUT $CInput10
    parameter \multiport "0"
    parameter \offset "0,0"
    parameter \pattern "4,20"
    parameter \ref_name "a"
    parameter \size "80"
    parameter \A_WIDTH 1
    parameter \Y_WIDTH 32
    connect \A $1_0
    connect \Y $3_0
  end

  attribute \keep "node_4"
  cell \ULT $ULT12
    parameter \A_WIDTH 32
    parameter \B_WIDTH 32
    parameter \Y_WIDTH 1
    connect \A $9_0
    connect \B $13_0
    connect \Y $4_0
  end

  attribute \keep "node_5"
  cell \CINPUT $CInput14
    parameter \multiport "0"
    parameter \offset "0,0"
    parameter \pattern "4,20"
    parameter \ref_name "b"
    parameter \size "80"
    parameter \A_WIDTH 1
    parameter \Y_WIDTH 32
    connect \A $12_0
    connect \Y $5_0
  end

  attribute \keep "node_6"
  cell \SEL $SEL16
    parameter \A_WIDTH 32
    parameter \B_WIDTH 32
    parameter \C_WIDTH 1
    parameter \Y_WIDTH 32
    connect \A $15_0
    connect \B $10_0
    connect \C $11_0
    connect \Y $6_0
  end

  attribute \keep "coarse_node_7"
  cell \CONST $Const18
    parameter \Y_WIDTH 32
    parameter \VALUE "10"
    connect \Y $7_0
  end

  attribute \keep "coarse_node_8"
  cell \CONST $Const19
    parameter \Y_WIDTH 32
    parameter \VALUE "1"
    connect \Y $8_0
  end

  attribute \keep "coarse_node_9"
  cell \CONST $Const21
    parameter \Y_WIDTH 32
    parameter \VALUE "5"
    connect \Y $9_0
  end

  attribute \keep "coarse_node_10"
  cell \CONST $Const22
    parameter \Y_WIDTH 32
    parameter \VALUE "10"
    connect \Y $10_0
  end

  attribute \keep "coarse_node_16"
  cell \ADD $ADD38
    parameter \A_WIDTH 32
    parameter \B_WIDTH 32
    parameter \Y_WIDTH 32
    connect \A $5_0
    connect \B $6_0
    connect \Y $16_0
  end

  attribute \keep "coarse_node_15"
  cell \CONST $Const37
    parameter \Y_WIDTH 32
    parameter \VALUE "0"
    connect \Y $15_0
  end

  attribute \keep "coarse_node_13"
  cell \ACC $ACC28
    parameter \acc_first "0"
    parameter \acc_params "0,20,1,1"
    parameter \A_WIDTH 32
    parameter \Y_WIDTH 32
    connect \A $8_0
    connect \Y $13_0
  end

  attribute \keep "node_14"
  cell \SEL $SEL29
    parameter \A_WIDTH 32
    parameter \B_WIDTH 32
    parameter \C_WIDTH 1
    parameter \Y_WIDTH 32
    connect \A $3_0
    connect \B $16_0
    connect \C $1_0
    connect \Y $14_0
  end

  cell $lut $abc$74$blif$74$1
    parameter \WIDTH 1
    parameter \LUT 2'01
    connect \Y $12_0
    connect \A $1_0
  end

  cell $lut $abc$74$blif$74$0
    parameter \WIDTH 2
    parameter \LUT 4'0100
    connect \Y $11_0
    connect \A { $4_0 $1_0 }
  end
end
