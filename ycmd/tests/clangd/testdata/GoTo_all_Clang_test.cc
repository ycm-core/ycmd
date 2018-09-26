// This file is used in RunCompleterCommand_GoTo_all_Clang_test
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
    int ix = Local::x;
    char cy = Local::in_line();
    char cx = Local::out_of_line();

    return 0;
}

void unicode()
{
  /* †est ê */ struct Unicøde { int u; }; struct Another_Unicøde;

  Unicøde *ç;

  ç->u; Another_Unicøde *u;

  u;
}
