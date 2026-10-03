
#define NI 32
#define NJ 32
//  int out=0;
/* Main computational kernel. The whole function will be timed,
   including the call and return. */
void conv(int A[NI][NJ], int B[NI][NJ],int out[])
{
 int i,j;
 int ij;
    #pragma scop
  for (i = 0; i < NI; i++) {
    for (j = 0; j < NJ; j++) {
      out[0] += A[i][j] * B[i][j];
    }
  }
 #pragma endscop
  // for (int x = 0; x < NI*NJ; x++) {
  //   i = x / NJ;
  //   j = x % NJ;
  //   out += A[i][j] * B[i][j];
  // }


    //   i = 0;
    // j = 0;

    // for (ij = 0; ij < NI * NJ; ++ij) {


    //     out += A[i][j] * B[i][j];

    //     ++j;
    //     if (j == NJ) {
    //         j = 0;
    //         ++i;
    //     }
    // }


}