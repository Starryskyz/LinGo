// #define __CGRA_HARDWARE_OP(x) __attribute__((annotate("___CGRA_HARDWARE_OP__"x"___"), noinline, optnone))
// __CGRA_HARDWARE_OP("mylogsigmoid") float mylogsigmoid(float exp) {return *(float *) __hardware_imp();}

// // 宏定义
// #define MAT_DIM_I 8
// #define MAT_DIM_K 8
// #define MAT_DIM_J 8
// #define DATA_TYPE float
// const DATA_TYPE beta = 3, const1 = 1, upper = 5.0, lower = -5.0;      // 0.1 0.0 1.0
// // #define alpha 0.33333333333333f
// // 全局矩阵声明

// float C[MAT_DIM_I][MAT_DIM_J];
// float D[MAT_DIM_I][MAT_DIM_J];

// void kernel()
// {

//     // --- Step 1: 矩阵乘法 temp_C = A * B + D ---
// #ifdef CGRA_COMPILER
//     loop_begin();
// #endif
//     for (int i = 0; i < MAT_DIM_I; ++i)
//     {	
//         for (int j = 0; j < MAT_DIM_J; ++j)
//         {
//             // float sum = C[i][j];
//             // if(sum > upper){
//             //     sum = upper;
//             // }else if (sum < lower){
//             //     sum = lower;
//             // }
//             D[i][j] = mylogsigmoid(C[i][j]);
//         }
//     }
// #ifdef CGRA_COMPILER
//     loop_end();
// #endif
// }


#define __CGRA_HARDWARE_OP(x) __attribute__((annotate("___CGRA_HARDWARE_OP__"x"___"), noinline, optnone))
__CGRA_HARDWARE_OP("mySqrt") float mySqrt(float x) {return *(float *) __hardware_imp();}
// #define __CGRA_HARDWARE_OP(x) __attribute__((annotate("___CGRA_HARDWARE_OP__"x"___"), noinline, optnone))
// __CGRA_HARDWARE_OP("myExp") float myExp(float exp) {return *(float *) __hardware_imp();}
// 宏定义
#define NUM 16
float input[NUM];
float output[NUM];

void kernel()
{

    // --- Step 1: 矩阵乘法 temp_C = A * B + D ---
#ifdef CGRA_COMPILER
    loop_begin();
#endif
    for (int i = 0; i < NUM; i++)
    {
        output[i] = mySqrt(input[i]);
        //printf("distance %e\n", distance);
}
#ifdef CGRA_COMPILER
    loop_end();
#endif
}
