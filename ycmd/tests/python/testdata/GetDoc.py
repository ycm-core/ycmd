
class TestClass:
  """ Class Documentation"""


  def TestMethod(self):
    """ Method Documentation """
    return self.member_variable


def _ModuleMethod():
  """ Module method docs
      Are dedented, like you might expect"""
  pass


_ModuleMethod()

tc = TestClass()
tc.TestMethod()
