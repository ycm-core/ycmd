package com.test;

import com.youcompleteme.*; import com.test.wobble.*;
import com.youcompleteme.testing.Tset;

class TestLauncher {
  private TestFactory factory = new TestFactory();
  private Tset tset = new Tset();

  private interface Launchable {
    public void launch( TestFactory f );
  }

  private void Run( Launchable l ) {
    tset.getTset().add( new Test() );
    l.launch( factory );
  }

  public static void main( String[] args ) {
    TestLauncher l = new TestLauncher();
    l.Run( new Launchable() {
      @Override
      public void launch() {
        AbstractTestWidget w = factory.getWidget( "Test" );
        w.doSomethingVaguelyUseful();

        System.out.println( "Did something useful: " + w.getWidgetInfo() );
      }
    });
  }
}
