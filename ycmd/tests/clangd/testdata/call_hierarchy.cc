void simple_2() {
}
void simple_1() {
  return simple_2();
}
void multiple_2() {
  multiple_2();
}

void multiple_1() {
  multiple_2();
}

void multiple_0() {
  multiple_2();
}
