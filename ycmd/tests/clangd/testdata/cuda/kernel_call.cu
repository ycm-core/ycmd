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


#include "cuda.h"

__global__ void g1(int x) {}

template <typename T> void t1(T arg) {
  g1<<<arg, arg>>>(1);
}

void h1(int x) {}
int h2(int x) { return 1; }

int main(void) {
  g1<<<1, 1>>>(42);
  g1(42); // expected-error {{call to global function 'g1' not configured}}
  g1<<<1>>>(42); // expected-error {{too few execution configuration arguments to kernel function call}}
  g1<<<1, 1, 0, 0, 0>>>(42); // expected-error {{too many execution configuration arguments to kernel function call}}

  t1(1);

  h1<<<1, 1>>>(42); // expected-error {{kernel call to non-global function 'h1'}}

  int (*fp)(int) = h2;
  fp<<<1, 1>>>(42); // expected-error {{must have void return type}}

  g1<<<undeclared, 1>>>(42); // expected-error {{use of undeclared identifier 'undeclared'}}
}
