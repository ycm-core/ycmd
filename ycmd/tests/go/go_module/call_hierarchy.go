package main

func simple_2() {}
func simple_1() {
	simple_2();
}

func multiple_2() {
	multiple_2();
}
func multiple_1() {
	multiple_2();
	multiple_1();
}
func multiple_0() {
	multiple_2();
	multiple_1();
	multiple_0();
}
