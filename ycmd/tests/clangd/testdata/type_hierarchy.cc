struct B {};
struct A1 {};
struct A2 : A1 {};
struct A3 : A1, B {};
B b;
A2 a2;
