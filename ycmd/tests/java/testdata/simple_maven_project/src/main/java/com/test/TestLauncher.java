package com.test;

class TestLauncher {
  private TestFactory factory = new TestFactory();

  private void Run() {
    AbstractTestWidget w = factory.getWidget( "Test" );
    w.doSomethingVaguelyUseful();

    System.out.println( "Did something useful: " + w.getWidgetInfo() );
  }

  public static void main( String[] args ) {
    TestLauncher l = new TestLauncher();
    l.Run();
  }
}
