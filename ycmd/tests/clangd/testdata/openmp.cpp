#include "omp.h"

int main()
{
  int sum = 0;
  #pragma omp parallel for num_threads(4)
  for ( int i = 0; i < 1000; ++i )
  {
    int thread_id = omp_get_thread_num();
    #pragma omp atomic
    sum += i * (thread_id % 2 == 0 ? 1 : -1);
  }
  return sum > 0;
}
