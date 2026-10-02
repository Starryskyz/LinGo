#define size 1024
#define bound 32
volatile int input[size];
volatile int data[size];
volatile int data0[size];
// granularity: 0 represents 1 word; 1 represents 2 words
void kernel()
{
    loop_begin();
	for (int i = 0; i < bound; i++)
	{
		for (int j = 0; j < bound; j++)
		{

		}
	}
    loop_end();
}
