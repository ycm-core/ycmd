#include "make_drink.h"

using namespace Test;

int main( int , char ** )
{
  make_drink( TypeOfDrink::COFFEE, 10.0, Flavour::ELDERFLOWER );
  make_drink( TypeOfDrink::JUICE, Temperature::COLD, 1 );
}

void test_right_edge_80()
{
                                                                     make_drink(
                                                                  TypeOfDrink::COFFEE,
                                                                  10, Flavour::ORANGE_AND_PINEAPPLE);
}

void test_left_edge()
{
make_drink( TypeOfDrink::JUICE,
            Temperature
::WARM, 10 );
}
