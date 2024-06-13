package com.test;

public class Hierarchies {

  public Hierarchies() {}

  public int f() {
    return 5;
  }

  public int g() {
    return f() + f();
  }

  public int h() {
    int x = g();
    return x + f();
  }
}
