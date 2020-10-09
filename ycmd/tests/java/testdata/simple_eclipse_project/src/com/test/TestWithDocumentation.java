package com.test;

public class TestWithDocumentation {
  public static void main( String[] args ) {
    MethodsWithDocumentation m = new MethodsWithDocumentation();
    m.useAString( m.getAString() );
    m.hashCode();
  }
}
