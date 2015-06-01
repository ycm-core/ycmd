<?php

class Foo {
  
  const c = 'CONSTANT';
  
  public __construct() {
	$self->x = 1;
	$self->y = 2;
  }
  
  public static function members() {
    return array('x', 'y');
  }
}

function getFooX() {
  $foo = new Foo;
  return $foo->;
}

// Should return constant c and members functions. Position is line 23 col 6.
Foo::

/* End of line is line 34, column 7
 *
 * Should complete with built-in candidates:
 * - class_alias
 * - class_exists
 * - class_implements
 * - class_parents
 * - class_uses
 */
class_


/* End of line is line 46, column 5 
 *
 * Should complete with built-in candidates:
 * - DateInterval
 * - DatePeriod
 * - DateTime
 * - DateTimeImmutable
 * - DateTimeZone 
 */
Date