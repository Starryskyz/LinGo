#define __CGRA_HARDWARE_OP(x) __attribute__((annotate("___CGRA_HARDWARE_OP__"x"___"), noinline, optnone))
__CGRA_HARDWARE_OP("myExp") float myExp(float exp, float x) {return *(float *) __hardware_imp();}

// #define __CGRA_HARDWARE_OP(x) __attribute__((annotate("___CGRA_HARDWARE_OP__"x"___"), noinline, optnone))
// __CGRA_HARDWARE_OP("mySqrt") float mySqrt(float x) {return *(float *) __hardware_imp();}
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
        output[i] = myExp(2.71828182845904, input[i]);
        //printf("distance %e\n", distance);
}
#ifdef CGRA_COMPILER
    loop_end();
#endif
}
