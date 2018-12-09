// Identifier completion makes sense for duck-typing.
//
// The purpose of this test is to both demonstrate the use-case and test the
// functionality. Completions of "A.a_parameter" using the identifier
// completer feels natural, whereas offering no suggestions feels broken

typedef struct {
  int a_parameter;
  int another_parameter;
} TTest;

typedef struct {
  int another_int;
  int and_a_final_int;
} TTest_Which_Is_Not_TTest;

static void do_something( int );
static void do_another_thing( int );

// TESTCASE1: use of . on macro parameter. Macros used this way are compile-time
// duck-typing. Note this in this particular instance, libclang actually
// offers semantic completions if there is only call to this macro
// (e.g. DO_SOMETHING_TO( a_test ) - clever little shrew), so we don't call it

/*       1         2         3         4
1234567890123456789012345678901234567890123456789 */
#define DO_SOMETHING_TO( A )                   \
  do {                                         \
    do_something( A.a_parameter );             \
    do_another_thing( A.another_parameter );   \
  } while (0)

// TESTCASE2: use of -> on macro parameter. Macros used this way are
// compile-time duck-typing

/*       1         2         3         4
1234567890123456789012345678901234567890123456789 */
#define DO_SOMETHING_VIA( P )                  \
  do {                                         \
    do_something( P->a_parameter );            \
    do_another_thing( P->another_parameter );  \
  } while (0)

int main( int argc, char ** argv )
{
  TTest a_test;

// TESTCASE3: use of -> on struct. This is an error, but the user might
// subsequently change a_test to be a pointer. Assumption: user knows what they
// are doing

/*       1         2         3         4
1234567890123456789012345678901234567890123456789 */
  if ( a_test->anoth ) {
    (void) 0;
  }

// TESTCASE4: use of . on struct. Gets semantic suggestions

/*       1         2         3         4
1234567890123456789012345678901234567890123456789 */
  if ( a_test.a_parameter ) {
    (void) 0;
  }

// TESTCASE5: use of . on struct for non-matching text. Again, probably an
// error, but assume the user knows best, and might change it later.

/*       1         2         3         4
1234567890123456789012345678901234567890123456789 */
  if ( a_test.do_ ) {
    (void) 0;
  }

  TTest *p_test = &a_test;

// TESTCASE6: use of -> on pointer. Semantic completions

/*       1         2         3         4
1234567890123456789012345678901234567890123456789 */
  if ( p_test-> ) {

  }

}
