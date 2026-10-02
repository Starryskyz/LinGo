// #include "../../include/utils.h"

// void kernel(DATA_TYPE input[], DATA_TYPE output[], DATA_TYPE alpha);
#define Convert(x) x
#define DATA_TYPE float
#define NTAPS 2048
#define LOOP_LENGTH  NTAPS
// #define STREAMING_ENBALED                               // Indicate that the streaming mode is enabled
#define STREAMING_WIDTH 100                            // The width of the streaming mode
#define max(a,b) (((a)>(b))?(a):(b))
#define min(a,b) (((a)<(b))?(a):(b))
DATA_TYPE input[NTAPS], output[NTAPS], input_buf[STREAMING_WIDTH], output_buf[STREAMING_WIDTH];
const DATA_TYPE const1 = 0, const2 = 1;      // 0.1 0.0 1.0
#define alpha 0.33333333333333f
// const DATA_TYPE c1 = 5, c2 = 6, c3 = 1;       // 0.5 1/6 1.0
// int main()
// {
//     #ifndef __STREAMING_ENBALED__
//         kernel(input, output, alpha);
//     #else
//         for (int i = 0; i < NTAPS; i += STREAMING_WIDTH) {
//             for (int j = 0; j < STREAMING_WIDTH; j++) {
//                 input_buf[j] = input[i + j];
//             }
//             kernel(input_buf, output_buf, alpha);
//             for (int j = 0; j < STREAMING_WIDTH; j++) {
//                 output[i + j] = output_buf[j];
//             }
//         }
//     #endif

//     return 0;
// }
inline DATA_TYPE exp(DATA_TYPE x) {
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
volatile DATA_TYPE input_data[NTAPS];
DATA_TYPE output_data[NTAPS];
void kernel()
/*   input :           input sample array */
/*   output:           output sample array */
{
    #ifdef CGRA_COMPILER
    	loop_begin();
    #endif 
    for (int i = 0; i < LOOP_LENGTH; i++) {
        float tmp1 = max((DATA_TYPE)(const1), input[i]);
        float tmp2 = min((DATA_TYPE)(const1), alpha * (exp(input[i] * alpha) - (DATA_TYPE)(const2)));
        output[i] = tmp1 + tmp2;
    }
    #ifdef CGRA_COMPILER
    	loop_end();
    #endif 
}