#!/bin/bash

files=$(find cpp/ycm -type f \
        \( -name "*.cpp" -o -name "*.h" \) -and \
        -not \( -path "**/gmock/**" -o -path "**/testdata/**" -o \
        -path "**/CustomAssert.*" -o -path "**/ycm_*" \) )

clang-format -i -style=file $files
