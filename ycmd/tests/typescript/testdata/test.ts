
class Foo {
  // Unicode string: 说话
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

// line 12, column 6
foo.m


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
