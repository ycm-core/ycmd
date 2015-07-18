<?php 
/*
 * This PHP file is intended to be "orphaned" in that it represents a project
 * file that may be included by files executed before a file within the project
 * but not in the file itself. For instance
 *
 * root -- test.php    - uses "orphan_func()"
 *      |- orphan.php  - defines "orphan_func()"
 *      \  parent.php  - includes "orphan.php" then includes "test.php"
 *
 * When editing "test.php" there is no link to "orphan.php" within the file. 
 */
 

// Function definition is on line 16
function orphan_shallow_func() {
	return 'Special tricks needed to use me';
}