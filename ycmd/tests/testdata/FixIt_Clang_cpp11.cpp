//
// A selection of the tests from llvm/tools/clang/test/FixIt/fixit-cxx0x.cpp
//
// Modified to test fixits across multiple lines and ensure that the number of
// diagnostics doesn't hit the compile threshold.
//

/* This is a test of the various code modification hints that only
   apply in C++0x. */
struct A {
  explicit operator int(); // expected-note{{conversion to integral type}}
};

// _FixIt_Check_cpp11_Ins (2 inserts on one line)
void x() {
  switch(A()) { // expected-error{{explicit conversion to}}
  }
}

// _FixIt_Check_cpp11_InsMultiLine
// same as above, except the 2 inserts split over multiple lines, neiher of
// which are the *same* line as the diagnostic report (diagnostic on line
// "switch", inserts on following line and later line
void y() {
  switch( // diag
      A   // insert: static_cast<int>(
    (
)         // insert: )
    ) {

  }
}

// _FixIt_Check_cpp11_Del
using ::T = void; // expected-error {{name defined in alias declaration must be an identifier}}

namespace dtor_fixit {
  class foo {
    // _FixIt_Check_cpp11_Repl
    ~bar() { }  // expected-error {{expected the class name after '~' to name a destructor}}
    // CHECK: fix-it:"{{.*}}":{[[@LINE-1]]:6-[[@LINE-1]]:9}:"foo"
  };

  class bar {
    ~bar();
  };
  // _FixIt_Check_cpp11_DelAdd
  ~bar::bar() {} // expected-error {{'~' in destructor name should be after nested name specifier}}
  // CHECK: fix-it:"{{.*}}":{[[@LINE-1]]:3-[[@LINE-1]]:4}:""
  // CHECK: fix-it:"{{.*}}":{[[@LINE-2]]:9-[[@LINE-2]]:9}:"~"
}

namespace test_fixit_multiple {
  class foo { ~bar() { } }; class bar { ~bar(); }; ~bar::bar() { }
}
