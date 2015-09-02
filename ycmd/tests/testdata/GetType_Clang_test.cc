// This file is used in RunCompleterCommand_GetType_Clang_test
#include <iostream>
#include <string>

namespace Std {
  template< typename T >
  struct BasicString
  {
      BasicString( const char * );
  };

  typedef BasicString< char > String;

  std::ostream& operator << ( std::ostream& o, const String& s);
}

struct Foo {
  int x;
  int y;
  char c;
};

int main()
{
  Foo foo;
  Std::String a = "hello";
  std::cout << a;

  auto &arFoo = foo;
  auto *apFoo = &foo;

  const auto &acrFoo = foo;
  const auto *acpFoo = &foo;

  std::cout << acrFoo.y
            << acpFoo->x
            << arFoo.y
            << apFoo->x;

  Foo &rFoo = foo;
  Foo *pFoo = &foo;

  const Foo &crFoo = foo;
  const Foo *cpFoo = &foo;

  std::cout << crFoo.y
            << cpFoo->x
            << rFoo.y
            << pFoo->x;

  return 0;
}
