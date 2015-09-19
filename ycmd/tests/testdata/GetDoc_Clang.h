///
/// A TestClass is a sort of class for testing.
///
/// TODO: BenJ 2010-09-21 Perhaps we should consider renaming this, as it is the
/// core of our application?
///
class TestClass
{
public:
    int a_public_var; /** don't touch this directly, use a_public_method */

    /**
     * Constructs a test class. Note gap to TestClass()
     */

    TestClass();

    /**
     * Call a_public_method when you want to do something exciting.
     *
     * @param excitement_level The level between 100 and 8 of required
     * excitement. The unit is puppy bounce height.
     *
     * @return whether or not the required excitement level was entered.
     */
    bool a_public_method( int excitement_level );

    void an_undocumented_method();
};
