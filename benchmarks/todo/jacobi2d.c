

#define N 32
#define TSTEPS 10


void jacobi2d(int A[N][N], int B[N][N]) {
    int t, i, j;
      #pragma scop
        for (i = 1; i < N - 1; i++)
            for (j = 1; j < N - 1; j++)
                B[i][j] = (A[i][j] + A[i][j-1] + A[i][j+1] + A[i+1][j] + A[i-1][j]) * 5;

      #pragma endscop
}

