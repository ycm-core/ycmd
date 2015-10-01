#include "GetDoc_Clang.h"

/// This is a test namespace
namespace Test {

    /// This is a global variable, that isn't really all that global.
    int a_global_variable;

    /// This is a method which is only pretend global
    /// @param test Set this to true. Do it.
    int get_a_global_variable( bool test );

    char postfix_comment(); ///< Method postfix

    /**
     * This is not the brief.
     *
     * \brief brevity is for suckers
     *
     * This is more information
     */
    char with_brief();

    /** The
* indentation
                    * of this comment
            * is
    * all messed up. */
    int messed_up();
}

/// This really is a global variable.
///
/// The first line of comment is the brief.
char a_global_variable;

/** JavaDoc-style */
bool javadoc_style;

//! Qt-style
bool qt_style;

/// This method has lots of lines of text in its comment.
///
/// That's important because the preview window
///
/// Has
///
/// Limited Space.
char get_a_global_variable( );

bool postfix_comment; ///< The brief follows the declaration.

typedef TestClass AnotherClass;

// Double slash is not considered attached to declaration
bool double_slash;

/* slash asterisk is also not considered attached to declaration */
bool slash_asterisk;

/** Main */
int main() {
    char c = get_a_global_variable( );
    int i = Test::get_a_global_variable( true );

    typedef int(*FUNCTION_POINTER)( bool );
    FUNCTION_POINTER fp = &Test::get_a_global_variable;

    bool b = c == a_global_variable &&
             i == Test::a_global_variable &&
             javadoc_style &&
             qt_style &&
             postfix_comment &&
             double_slash &&
             slash_asterisk;

    TestClass tc;
    const AnotherClass& ac = tc;
    tc.a_public_method( tc.a_public_var );
    tc.an_undocumented_method();

    Test::postfix_comment();
    Test::messed_up();

    return b ? 0 : 1;
}
