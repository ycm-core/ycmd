// This file is used in RunCompleterCommand_GetType_Clang_test
namespace Ns {
    template< typename T >
    struct BasicType
    {
        BasicType( const T * );
    };

    typedef BasicType< char > Type;
}

struct Foo {
  int x;
  int y;
  char c;

  int bar(int i) {
    return i+1;
  }
};

int main()
{
  Foo foo;
  Ns::Type a = "hello";
  Ns::Type b = a;

  auto &arFoo = foo;
  auto *apFoo = &foo;

  const auto &acrFoo = foo;
  const auto *acpFoo = &foo;

  int acry = acrFoo.y;
  int acpx = acpFoo->x;
  int ary = arFoo.y;
  int apx = apFoo->x;

  Foo &rFoo = foo;
  Foo *pFoo = &foo;

  const Foo &crFoo = foo;
  const Foo *cpFoo = &foo;

  int cry = crFoo.y;
  int cpx = cpFoo->x;
  int ry = rFoo.y;
  int px = pFoo->x;

  struct Unicøde;
  Unicøde *ø;

  int i = foo.bar(1);
  int j = apFoo->bar(1);

  return 0;
}
