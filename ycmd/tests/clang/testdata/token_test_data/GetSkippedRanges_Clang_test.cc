struct Foo {
#ifdef DEBUG
  void print() const {};
#endif
  int f;
};

int main(int argc, char *argv[])
{
  Foo foo;
#ifdef DEBUG
  foo.print();
#endif
  return 0;
}
