struct Unity
{
  int this_is_an_it;
};

static void static_method()
{
}

namespace
{
  void unity_method( int p );
}

#include "unitya.cc"

namespace
{
  void unity_method( int p )
  {
    Unity u;
    UnityA a;

    extern_method( &u );
    do_unity_A( &u );

    if (a.an_int)
    {
    }
  }
}
