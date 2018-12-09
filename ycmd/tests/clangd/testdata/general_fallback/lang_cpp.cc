namespace
{
  struct TTest
  {
    static void PrintDiagnostic();

    int a_parameter;
    int another_parameter;
  }:

  void do_something(int);
  void do_another_thing(int);

  // TESTCASE1: use of . on template argument. Templates used this way are
  // compile-time duck typing
  template<typename T>
  void DO_SOMETHING_TO( T& t )
  {
/*       1         2         3         4
1234567890123456789012345678901234567890123456789 */
    do_something( t.a_parameter );
  }

  // TESTCASE2: use of -> on template argument. Templates used this way are
  // compile-time duck typing
  template<typename T>
  void DO_SOMETHING_WITH( T* t )
  {
/*       1         2         3         4
1234567890123456789012345678901234567890123456789 */
    do_something( t->a_parameter );
  }

  // TESTCASE3: use of :: on template argument. Templates used this way are
  // compile-time duck typing
  template<typename T>
  void PRINT_A_DIAGNOSTIC( )
  {
/*       1         2         3         4
1234567890123456789012345678901234567890123456789 */
    T::PrintDiagnostic();
  }
}

int main (int , char **)
{
  // bonus test case (regression test) for identifier/forced semantic without
  // trigger

  TTest test;

/*       1         2         3         4
1234567890123456789012345678901234567890123456789 */
  DO_SOMETHING_TO(test);
}
