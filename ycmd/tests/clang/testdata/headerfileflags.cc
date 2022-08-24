#include "headerfileflags.h"

int main()
{
  Struct s = {};
  declared_in_header( s.foo );
}
