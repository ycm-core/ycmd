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

  int foobar() {
    return 5;
  }
};
typedef enum { VALUE_1, VALUE_2 } enum_test;
int main()
{
  Foo foo;
  Bar bar;
  // The location after the dots are lines 26 and 27, column 3
  bar.barbar();
  foo.x = 3;
  enum_test enumerate = VALUE_1;
}
