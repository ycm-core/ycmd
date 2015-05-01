struct Foo {
  int x; //!< A docstring.
  int y;
  char c;

  int foobar() {
    return 5;
  }
};

int main()
{
  Foo foo;
  // The location after the dot is line 15, col 7
  foo.
}
