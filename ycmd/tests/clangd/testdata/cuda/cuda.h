/* Modified by ycmd contributors */
/*
  University of Illinois/NCSA
  Open Source License

  Copyright (c) 2007-2016 University of Illinois at Urbana-Champaign.
  All rights reserved.

  Developed by:

      LLVM Team

      University of Illinois at Urbana-Champaign

      http://llvm.org

  Permission is hereby granted, free of charge, to any person obtaining a copy of
  this software and associated documentation files (the "Software"), to deal with
  the Software without restriction, including without limitation the rights to
  use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
  of the Software, and to permit persons to whom the Software is furnished to do
  so, subject to the following conditions:

      * Redistributions of source code must retain the above copyright notice,
        this list of conditions and the following disclaimers.

      * Redistributions in binary form must reproduce the above copyright notice,
        this list of conditions and the following disclaimers in the
        documentation and/or other materials provided with the distribution.

      * Neither the names of the LLVM Team, University of Illinois at
        Urbana-Champaign, nor the names of its contributors may be used to
        endorse or promote products derived from this Software without specific
        prior written permission.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
  FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
  CONTRIBUTORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS WITH THE
  SOFTWARE.
*/


/* Minimal declarations for CUDA support.  Testing purposes only. */

typedef __SIZE_TYPE__ size_t;

// Make this file work with nvcc, for testing compatibility.

#ifndef __NVCC__
#define __constant__ __attribute__((constant))
#define __device__ __attribute__((device))
#define __global__ __attribute__((global))
#define __host__ __attribute__((host))
#define __shared__ __attribute__((shared))
#define __launch_bounds__(...) __attribute__((launch_bounds(__VA_ARGS__)))

struct dim3 {
  unsigned x, y, z;
  __host__ __device__ dim3(unsigned x, unsigned y = 1, unsigned z = 1) : x(x), y(y), z(z) {}
};

typedef struct cudaStream *cudaStream_t;

int cudaConfigureCall(dim3 gridSize, dim3 blockSize, size_t sharedSize = 0,
                      cudaStream_t stream = 0);

// Host- and device-side placement new overloads.
void *operator new(__SIZE_TYPE__, void *p) { return p; }
void *operator new[](__SIZE_TYPE__, void *p) { return p; }
__device__ void *operator new(__SIZE_TYPE__, void *p) { return p; }
__device__ void *operator new[](__SIZE_TYPE__, void *p) { return p; }

#endif // !__NVCC__
