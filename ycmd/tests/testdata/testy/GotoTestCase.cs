using System;

namespace testy
{
	class GotoTestCase
	{
		static void Main (string[] args)
		{
			MainClass.Main(new String[0]);
		}

		static void ImplementionTest(IGotoTest test) {
			test.DoSomething();
		}

		static void InterfaceOnlyTest(IGotoTestWithoutImpl test) {
			test.DoSomething();
		}

		static void MultipleImplementionTest(IGotoTestMultiple test) {
			test.DoSomething();
		}
	}

	interface IGotoTest {
		void DoSomething();
	}

	class GotoTestImpl : IGotoTest {
		public void DoSomething() {
		}
	}

	interface IGotoTestWithoutImpl {
		void DoSomething();
	}

	interface IGotoTestMultiple {
		void DoSomething();
	}

	class GotoTestMultipleImplOne : IGotoTestMultiple {
		public void DoSomething() {
		}
	}

	class GotoTestMultipleImplTwo : IGotoTestMultiple {
		public void DoSomething() {
		}
	}
}
