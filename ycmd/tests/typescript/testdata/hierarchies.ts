function f(){
  return 5;
}

function g() {
  return f() + f();
}

function h() {
  var a = g();
  return a + f();
}
