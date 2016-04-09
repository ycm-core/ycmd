/**
 * testy is a namespace for testing
 */
namespace testy {
        /**
         * Tests the GetDoc subcommands
         */
	public class GetDocTestCase {
                /**
                 * Constructor
                 */
		public GetDocTestCase() {
                    this.an_int = 1;
		}

                /**
                 * Very important method.
                 *
                 * With multiple lines of commentary
                 *     And Format-
                 * -ting
                 */
                public int DoATest() {
                    return an_int;
                }

                /// an integer, or something
                private int an_int;

                /// Use this for testing
                private static void DoTesting() {
                    GetDocTestCase tc;
                    tc.DoATest();
                }
        }
}
