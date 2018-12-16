
class Foo {
  /** Unicode string: 说话 */
  methodA() {}
  methodB() {}
  methodC(
    a: {
      foo: string;
      bar: number;
    }
  ) {}
}

var foo = new Foo();

// line 17, column 6
foo.mA


/**
 * Class documentation
 *
 * Multi-line
 */
class Bar {

  /**
   * Method documentation
   */
  testMethod() {}
}

var bar = new Bar();
bar.testMethod();
bar.nonExistingMethod();

Bar.apply()

Bår
