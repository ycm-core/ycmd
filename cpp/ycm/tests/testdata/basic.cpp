struct Foo {
  int x; //!< A docstring.
  int y;
  char c;

  int foobar(int t) {
    return t;
  }
};

int main()
{
  Foo foo;
  // The location after the dot is line 15, col 7
  foo.
}
