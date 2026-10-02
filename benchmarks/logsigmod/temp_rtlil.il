module \affine

  attribute \keep "coarse_wire_1_0"
  wire width 32 $1_0

  wire width 1 $2_0

  attribute \keep "coarse_wire_3_0"
  wire width 32 $3_0

  wire width 1 $5_0

  attribute \keep "coarse_wire_6_0"
  wire width 32 $6_0

  attribute \keep "coarse_wire_7_0"
  wire width 32 $7_0

  wire width 1 $8_0

  wire width 1 $9_0

  attribute \keep "coarse_wire_10_0"
  wire width 32 $10_0

  attribute \keep "coarse_wire_11_0"
  wire width 32 $11_0

  attribute \keep "coarse_wire_12_0"
  wire width 32 $12_0

  wire width 1 $13_0

  attribute \keep "coarse_wire_14_0"
  wire width 32 $14_0


  attribute \keep "coarse_node_1"
  cell \INPUT $Input7
     parameter \multiport "0"
     parameter \offset "0,0"
     parameter \pattern "4,8,4,8"
     parameter \ref_name "C"
     parameter \size "256"
     parameter \Y_WIDTH 32
     connect \Y $1_0
  end

  attribute \keep "node_2"
  cell \FLT $FLT8
     parameter \A_WIDTH 32
     parameter \B_WIDTH 32
     parameter \Y_WIDTH 1
     connect \A $6_0
     connect \B $1_0
     connect \Y $2_0
  end

  attribute \keep "coarse_node_3"
  cell \MYLOGSIGMOID $mylogsigmoid11
     parameter \A_WIDTH 32
     parameter \Y_WIDTH 32
     connect \A $14_0
     connect \Y $3_0
  end

  attribute \keep "coarse_node_4"
  cell \OUTPUT $Output13
     parameter \multiport "0"
     parameter \offset "0,0"
     parameter \pattern "4,8,4,8"
     parameter \ref_name "D"
     parameter \size "256"
     parameter \A_WIDTH 32
     connect \A $3_0
  end

  attribute \keep "node_5"
  cell \FLT $FLT17
     parameter \A_WIDTH 32
     parameter \B_WIDTH 32
     parameter \Y_WIDTH 1
     connect \A $1_0
     connect \B $7_0
     connect \Y $5_0
  end

  attribute \keep "coarse_node_6"
  cell \CONST $Const22
     parameter \Y_WIDTH 32
     parameter \VALUE "1084227584"
     connect \Y $6_0
  end

  attribute \keep "coarse_node_7"
  cell \CONST $Const25
     parameter \Y_WIDTH 32
     parameter \VALUE "3231711232"
     connect \Y $7_0
  end

  cell $and $AND26
     parameter \A_SIGNED 0
     parameter \B_SIGNED 0
     parameter \A_WIDTH 1
     parameter \B_WIDTH 1
     parameter \Y_WIDTH 1
     connect \A $5_0
     connect \B $9_0
     connect \Y $8_0
  end

  cell $not $NOT28
     parameter \A_SIGNED 0
     parameter \A_WIDTH 1
     parameter \Y_WIDTH 1
     connect \A $2_0
     connect \Y $9_0
  end

  attribute \keep "coarse_node_10"
  cell \CONST $Const37
     parameter \Y_WIDTH 32
     parameter \VALUE "3231711232"
     connect \Y $10_0
  end

  attribute \keep "coarse_node_11"
  cell \CONST $Const38
     parameter \Y_WIDTH 32
     parameter \VALUE "1084227584"
     connect \Y $11_0
  end

  attribute \keep "node_12"
  cell \SEL $SEL39
     parameter \A_WIDTH 32
     parameter \B_WIDTH 32
     parameter \C_WIDTH 1
     parameter \Y_WIDTH 32
     connect \A $10_0
     connect \B $1_0
     connect \C $13_0
     connect \Y $12_0
  end

  cell $and $AND40
     parameter \A_SIGNED 0
     parameter \B_SIGNED 0
     parameter \A_WIDTH 1
     parameter \B_WIDTH 1
     parameter \Y_WIDTH 1
     connect \A $9_0
     connect \B $8_0
     connect \Y $13_0
  end

  attribute \keep "node_14"
  cell \SEL $SEL42
     parameter \A_WIDTH 32
     parameter \B_WIDTH 32
     parameter \C_WIDTH 1
     parameter \Y_WIDTH 32
     connect \A $11_0
     connect \B $12_0
     connect \C $2_0
     connect \Y $14_0
  end
end
