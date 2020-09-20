package com.test;

public class MethodsWithDocumentation {

  /**
   * This is the contructor
   */
  public MethodsWithDocumentation() {
  }

  /**
   * Single line description.
   *
   * @return a string
   */
  public String getAString() {
    return "";
  }

  /**
   * Multiple lines of
   * description
   * here.
   *
   * @param s a string
   */
  public void useAString( String s ) {
  }


  public static void main( String[] args ) {
    MethodsWithDocumentation m = new MethodsWithDocumentation();
    m.useAString( m.getAString() );
    m.hashCode();
  }
}
