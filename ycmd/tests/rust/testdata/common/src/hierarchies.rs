fn f() -> i32 {
    5
}

fn g() -> i32 {
    f() + f()
}

fn h() -> i32 {
    let x = g();
    f() + x
}
