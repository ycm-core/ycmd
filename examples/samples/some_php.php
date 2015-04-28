<?php

/**
 * Sample PHP file for testing
 */

class Example {

	public function __construct() {
		$this->x = 1;
		$this->y = 2;
		$this->z = 3;
	}
}

$ex = new Example();

// location after the -> operator is line 19, column 6
$ex->x = 5;

// location of cursor is line 22, column 12
$null = is_null($ex->z);

echo 'testing files';

function test1($i) {
	$b = 0;
	if ($i > 0) {
		$b = $i;
	}
}

// Middle call is line 34, column 10
$t = test1(0);