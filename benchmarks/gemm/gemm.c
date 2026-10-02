
#define ALPHA 3
#define BETA 2
#define NI 8
#define NJ 8
#define NK 8
volatile int inputX[NI][NK];
volatile int inputY[NK][NJ];
volatile int output[NI][NJ];

void kernel(){
  loop_begin();
  
  int i,j,k;
  // #pragma unroll 2
  for(i = 0; i < NI; i ++) {
        for(j = 0; j < NJ; j ++) {
            int sum = 0;
            // #pragma unroll 4
            for(k = 0; k < NK; k++) {
              sum += inputX[i][k] * inputY[k][j];
            }
            output[i][j] = ALPHA * sum + BETA * output[i][j];
        }
    }
  loop_end();
}