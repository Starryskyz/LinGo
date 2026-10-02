#define Convert(x) x
#define DATA_TYPE float
// #define STREAMING_ENBALED                               // Indicate that the streaming mode is enabled
#define STREAMING_WIDTH 100                            // The width of the streaming mode
#define max(a,b) (((a)>(b))?(a):(b))
#define min(a,b) (((a)<(b))?(a):(b))

#define MAT_DIM_I 32
#define MAT_DIM_K 32
#define MAT_DIM_J 32
const DATA_TYPE beta = 3, const1 = 1;      // 0.1 0.0 1.0
#define alpha 0.33333333333333f
// 全局矩阵声明
float A[MAT_DIM_I][MAT_DIM_K];
float B[MAT_DIM_K][MAT_DIM_J];
float D[MAT_DIM_I][MAT_DIM_J];
float C[MAT_DIM_I][MAT_DIM_J];
float igelu_C[MAT_DIM_I][MAT_DIM_J];

const DATA_TYPE c1 = 5, c2 = 6, c3 = 1;       // 0.5 1/6 1.0
//  0.79788456 0.044715  -2.0 1.0 0.5
const DATA_TYPE const2 = 6, const3 = -2, const4 = 1, const5 = 3;  
DATA_TYPE my_exp(DATA_TYPE x); 
inline DATA_TYPE my_exp(DATA_TYPE x) {
    const DATA_TYPE LN2     = 0.6931471805599453f;
    const DATA_TYPE INV_LN2 = 1.4426950408889634f;
    const DATA_TYPE c3 = 1.0f;
    const DATA_TYPE c2 = 1.0f / 6.0f;
    const DATA_TYPE c1 = 1.0f / 2.0f;
    int integer = (int)(x * INV_LN2);
    DATA_TYPE frac_x = x - (DATA_TYPE)integer * LN2;
    int bits = (127 + integer) << 23;
    DATA_TYPE exp_x = *(DATA_TYPE*)&bits;
    DATA_TYPE frac_x_square = frac_x * frac_x;
    DATA_TYPE tmp_poly = c2 * frac_x + c1;
    DATA_TYPE exp_frac_x = 1.0f + frac_x * (1.0f + frac_x * (0.5f + frac_x * (1.0f/6.0f + frac_x * (1.0f/24.0f))));
    return exp_x * exp_frac_x;
}


void kernel()
{

    // --- Step 1: 矩阵乘法 temp_C = A * B + D ---
#ifdef CGRA_COMPILER
    loop_begin();
#endif
    for (int i = 0; i < MAT_DIM_I; ++i)
    {	
        for (int j = 0; j < MAT_DIM_J; ++j)
        {
            float sum = 0.0f;
            for (int k = 0; k < MAT_DIM_K; ++k)
            {
                sum += A[i][k] * B[k][j];
            }
            sum += D[i][j];
            DATA_TYPE x = sum;
            // const1 should be 2/sqrt pi * (-2)
            DATA_TYPE xx = (DATA_TYPE)(-1.59576912160573f) * (x + (DATA_TYPE)(0.044715f) * x * x * x);
            DATA_TYPE exp_2x = my_exp(xx);
            DATA_TYPE tanh_x = ((DATA_TYPE)(1) - exp_2x) / ((DATA_TYPE)(1) + exp_2x);
            DATA_TYPE res = (DATA_TYPE)(0.5) * x * ((DATA_TYPE)(1) + tanh_x);
            igelu_C[i][j] = res;
        }
    }
#ifdef CGRA_COMPILER
    loop_end();
#endif
}
