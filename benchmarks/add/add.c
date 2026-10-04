#define size 1024
    float x[size];
    float y[size];
    float z[size];
   //kernel 23
void kernel() { 
    #ifdef CGRA_COMPILER
    	loop_begin();
    #endif 
    #pragma unroll 2
    for ( int k=0 ; k<size ; k++ ) {
            x[k] = y[k] + z[k];
        }      
    #ifdef CGRA_COMPILER
    	loop_end();
    #endif 
}
