struct Foo {
  int x;
  int y;
  char c;
};

int main()
{
  Foo foo;
  // The location after the dot is line 11, col 7
  foo.
}


static Foo test_function_that_has_no_errors()
{
  Foo foo = { 1,2,'c'};
  if (foo.c ) {
    foo.x = 1;
    foo.y = 2;
  }

  return foo;
}
