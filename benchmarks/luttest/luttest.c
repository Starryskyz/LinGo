#define size 20
#define bound 32
volatile int a[size];
volatile int b[size];

volatile int c[size];
volatile int d[size];

// volatile int q[2];
// volatile int a[10][10];
// granularity: 0 represents 1 word; 1 represents 2 words
// void kernel()
// {
//     loop_begin();
// 	for (int i = 0; i < 10; i++)
// 	{
// 		for (int j = 0; j < 10; j++)
// 		{
//          q[0] += a[i][j];
// 		}
// 	}
//     loop_end();
// }



void kernel() {
	loop_begin();
    for (int i = 0; i < size; i++) {
		// c[i] = i > 10?  a[i] : b[i];
		// a[i] + b[i];
		// i > 10?  a[i] : b[i];
        if (i > 10 )
        {
            c[i] = a[i];
        }
        else if(i>5)
        {
            c[i] = b[i];
        }
		else{
			c[i] = b[i]+10;
		}
    }
	loop_end();
}
