package com.test;

/**
 * @title TestFactory
 *
 * TestFactory is a pointless thing that OO programmers think is necessary
 * because they read about it in a book.
 *
 * All it does is instantiate the (one and only) concrete AbstractTestWidget
 * implementation
 */
public class TestFactory {
  private static class Bar {
    public int test;
    public String testString;
  }

  private void Wimble( Wibble w ) {
    if ( w == Wibble.CUTHBERT ) {
    }
  }

  public AbstractTestWidget getWidget( String info ) {
    AbstractTestWidget w = new TestWidgetImpl( info );
    Bar b = new Bar();

    if ( b.test ) {
      w.doSomethingVaguelyUseful();
    }
    if ( b.test ) { w.doSomethingVaguelyUseful( b ); }
    return w;
  }
}
