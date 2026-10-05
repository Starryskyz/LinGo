// Fixed bounds and integer arithmetic for the first LinGo mapping test.
void vecadd(int a[20], int b[20], int c[20]) {
  for (int i = 0; i < 20; ++i)
    c[i] = a[i] + b[i];
}
