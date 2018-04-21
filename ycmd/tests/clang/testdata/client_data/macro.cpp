struct Test {
#ifdef SOME_MACRO
  int macro_defined;
#else
  int macro_not_defined;
#endif
};

int main() {
  Test test;
  test.
}
