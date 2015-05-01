// This file is used in RunCompleterCommand_GoTo_all_Clang_test
#include <iostream>
namespace Local
{
    int x;

    char in_line()
    {
        return 'y';
    };

    char out_of_line();
}

char Local::out_of_line()
{
    return 'x';
}

int main();

int main()
{
    std::cout << Local::x
              << Local::in_line()
              << Local::out_of_line();
    return 0;
}
