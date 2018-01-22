package com.test;

/**
 * This is the actual code that matters.
 *
 * This concrete implentation is the equivalent of the main function in other
 * languages
 */


class TestWidgetImpl implements AbstractTestWidget {
  private String info;

  TestWidgetImpl( String info ) {
    this.info = info;
  }

  @Override
  public void doSomethingVaguelyUseful() {
    System.out.println( "42" );
  }

  @Override
  public String getWidgetInfo() {
    return this.info;
  }
}
