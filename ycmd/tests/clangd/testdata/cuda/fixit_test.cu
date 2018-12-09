#include "cuda.h"

__global__ int kernel();

int main()
{
  kernel<<<1, 1>>>();
  return 0;
}
