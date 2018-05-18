#include "cuda.h"

/// This is a test kernel
__global__ void kernel() {}

int main()
{
  kernel<<<1, 1>>>();
  return 0;
}
