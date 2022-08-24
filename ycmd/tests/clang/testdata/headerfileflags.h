#pragma once

struct Struct
{
  int foo;
};

void declared_in_header( int s )
{
  Struct bar;
  bar.foo = s;
}
