#include "cuda.h"

namespace Kernels
{
  __device__ void do_something(float* a) {}
}

template<typename F, class ...Args>
__global__ void launch(F& fn, Args args...)
{
  fn(args...);
}

int main() {
  // The location after the colon is line 16, col 29
  launch<<<1, 1>>>(Kernels::
  return 0;
}
