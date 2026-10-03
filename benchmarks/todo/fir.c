#define NTAPS 32

// int input[NTAPS];
// int output[NTAPS];
// int coefficients[NTAPS] = {025, 150, 375, -225, 050, 075, -300, 125,
// 025, 150, 375, -225, 050, 075, -300, 125,
// 025, 150, 375, -225, 050, 075, -300, 125,
// 025, 150, 375, -225, 050, 075, -300, 125};

void fir(int input[NTAPS], int output[NTAPS], int coefficient[NTAPS]){
int i;
int j = 0;

#pragma scop
for(j=0; j< NTAPS; ++j) {
    for (i = 0; i < NTAPS; ++i) {
      output[j] += input[i] * coefficient[i];
    }
 }
  #pragma endscop
}
