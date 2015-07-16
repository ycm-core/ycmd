<?php

require 'required.php';
include 'included.php';

// Completing the line below should bring up variables from both the included
// and required files. The cursor is on line 8 column 11.
$variable_

// Completing the line below should bring up the required function and class.
// Cursor is at line 12 column 9
required

// Completing the line below should bring up the included function and class.
// Cursor is at line 16 column 9
included

// GoTo for this function would be in file required.php on line 6
// Cursor is at line 20 column 22
$a = requiredFunction();

// GoTo for the class would be in file included.php on line 10
// Cursor is at line 24 column 23
$c = new includedClass();
$c->foo();