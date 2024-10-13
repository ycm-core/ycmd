/// <summary>
/// testy is a namespace for testing
/// </summary>
namespace testy {
	/// <summary>
        /// Tests the GetDoc subcommands
	/// </summary>
	public class GetDocTestCase {
		/// <summary>
                /// Constructor
		/// </summary>
		public GetDocTestCase() {
                    this.an_int = 1;
		}

		/// <summary>
                /// Very important method.
                ///
                /// With multiple lines of commentary
                ///     And Format-
                /// -ting
		/// </summary>
                public int DoATest() {
                    return an_int;
                }

		/// <summary>
                /// an integer, or something
		/// </summary>
                private int an_int;

		/// <summary>
                /// Use this for testing
		/// </summary>
                private static void DoTesting() {
                    GetDocTestCase tc;
                    tc.DoATest();
                }
        }
}
