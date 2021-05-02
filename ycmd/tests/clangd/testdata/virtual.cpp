struct foo_t {
  virtual int foo() = 0;
};

struct bar : foo_t{
  int foo() override { return 42; }
};

struct baz : foo_t {
  virtual int foo() { return 1; }
};

struct quux : foo_t {};
struct diamond : baz, quux {};
