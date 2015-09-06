// this file is used in RunCompleterCommand_GetParent_Clang_test
struct A {
    struct B {
        int x;
        char do_x();

        char do_z_inline()
        {
            return 'z';
        }

        template<typename T>
        char do_anything(T &t)
        {
            return t;
        }
    };

    int y;
    char do_y();

    char do_Z_inline()
    {
        return 'Z';
    }

    template<typename T>
    char do_anything(T &t);
};

template<typename T>
char A::do_anything(T &t)
{
    return t;
}

char A::B::do_x()
{
    return 'x';
}

char A::do_y()
{
    return 'y';
}

int main()
{
    auto l = [](){
        return "lambda";
    };

    l();

    return 0;
}
