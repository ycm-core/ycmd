// Copyright (C) 2017 ycmd contributors
//
// This file is part of ycmd.
//
// ycmd is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// ycmd is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

#include "benchmark/benchmark_api.h"
// iostream is included because of a bug with Python earlier than 2.7.12
// and 3.5.3 on OSX and FreeBSD.
#include <iostream>
#include <boost/python.hpp>


int main( int argc, char** argv ) {
  Py_Initialize();
  // Necessary because of usage of the ReleaseGil class.
  PyEval_InitThreads();

  benchmark::Initialize(&argc, argv);
  benchmark::RunSpecifiedBenchmarks();

  return 0;
}
