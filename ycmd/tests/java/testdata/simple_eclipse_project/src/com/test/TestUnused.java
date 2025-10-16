package com.test;

import java.util.ArrayList;

class Unused {
  private int not_used;

  public Unused() {}

  private void Unusable() {
    System.out.println("This method is never called");
  }

  public void doSomething() {
    System.out.println("Doing something");
  }
}
