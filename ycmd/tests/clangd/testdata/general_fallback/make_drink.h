#pragma once

namespace Test
{
  struct Drink {};

  enum class TypeOfDrink
  {
    COFFEE,
    TEA,
    JUICE,
  };

  enum class Temperature
  {
    HOT,
    COLD,
    WARM
  };

  enum class Flavour
  {
    ELDERFLOWER,
    RED,
    ORANGE_AND_PINEAPPLE
  };


  Drink& make_drink( TypeOfDrink type, Temperature temp, int sugargs );
  Drink& make_drink( TypeOfDrink type, double fizziness, Flavour Flavour );

  void simple_func( int d, float c, char *S );
  void simple_func( int f, char c );
  void simple_func( float f, char c );
}
