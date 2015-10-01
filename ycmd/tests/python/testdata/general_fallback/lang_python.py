class DoSomething:
  def __init__(self):
    self.this_is_well_known = 'too easy'
    # Jedi is smart enough to spot self.a_parameter = 1, but not if we just hack
    # it in some other method
    hack(self)
    pass

def hack( obj ):
  obj.a_parameter = 'secret'

  def a_method( abc, **kwargs ):
    print abc

  obj.another_parameter = a_method

def Main():
  a_thing = DoSomething()

  # TESTCASE1: param jedi knows about
#       1         2         3         4
#234567890123456789012345678901234567890123456789
  print a_thing.this_is_well_known

  # TESTCASE2: param jedi does not know about
#        1         2         3         4
#234567890123456789012345678901234567890123456789
  print a_thing.a_parameter

  # TESTCASE3: method jedi does not know about
#       1         2         3         4
#234567890123456789012345678901234567890123456789
  a_thing.another_parameter( 'test' )

# to ensure we can run this script to test the code actually makes sense!
if __name__ == "__main__":
  Main()
