package main

func f() (int) {
    return 5;
}
func g() (int) {
    return f() + f();
}
func h() (int) {
    var x = g();
    return f() + x;
}
