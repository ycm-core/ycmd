class Bar {
public:
  int x;
  int y;
  char c;

  void barbar() {
    x = 5;
  }
};

struct Foo {
  int x; //!< A docstring.
  int y;
  char c;

  int foobar( int a, float b = 3.0, char c = '\n' ) {
    return 5;
  }
};

typedef enum { VALUE_1, VALUE_2 } enum_test;

int main()
{
  Foo foo;
  Bar bar;
  // The location after the dots are lines 29 and 30, column 7
  bar.barbar();
  foo.x = 3;
  enum_test enumerate = VALUE_1;
}
