@protocol X;

// _FixIt_Check_objc, _FixIt_Check_objc_NoFixIt
void foo() {
  <X> *P;    // expected-warning{{protocol has no object type specified; defaults to qualified 'id'}}

  char *x = nullptr; // no fix-it for this error (nullptr undefinied)
}
