#include "unity.h"

struct UnityA {
  char a_char;
  int an_int;
};

void do_unity_A( Unity* u )
{
  unity_method( u->this_is_an_it );
  static_method()
}
