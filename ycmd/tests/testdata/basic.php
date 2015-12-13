<?php

class Foo {
  
  const c = 'CONSTANT';
  
  public __construct() {
	$self->x = 1;
	$self->y = 2;
  }
}

function getFooX() {
  $foo = new Foo;
  return $foo->;
}

class_ 
