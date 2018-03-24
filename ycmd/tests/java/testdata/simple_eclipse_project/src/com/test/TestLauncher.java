package com.test;

import com.youcompleteme.testing.Tset;
import com.youcompleteme.*; import com.test.wobble.*;

class TestLauncher {
  private TestFactory factory = new TestFactory();
  private Tset tset = new Tset();

  public TestLauncher( int test ) {}

  public static int static_int = 5;
  public static int static_method() {
	  return static_int;
  }

  private interface Launchable {
    public void launch( TestFactory f );
  }

  private void Run( Launchable l ) {
    tset.getTset().add( new Test() );
    l.launch( factory );
  }

  public static void main( String[] args ) {
    TestLauncher l = new TestLauncher( 10 );
    l.Run( new Launchable() {
      @Override
      public void launch() {
        AbstractTestWidget w = factory.getWidget( "Test" );
        w.doSomethingVaguelyUseful();

        System.out.println( "Did something useful: " + w.getWidgetInfo() );
      }
    });
    static_method();
    TestLauncher t = new TestLauncher( 4 );
    t.Run( null );
  }
}
