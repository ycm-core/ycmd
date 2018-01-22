package com.test;

public interface AbstractTestWidget {
  /**
   * Do the actually useful stuff.
   *
   * Eventually, you have to find the code which is useful, as opposed to just
   * boilerplate.
   */
  public void doSomethingVaguelyUseful();

  /**
   * Return runtime debugging info.
   *
   * Useful for finding the actual code which is useful.
   */
  public String getWidgetInfo();
};
