MODULE_SCOPE = 'module'


class One:
  ClassVariable = 'one'

  def __init__( self, argument ):
    self.argument_ = argument + MODULE_SCOPE
    self.variable_ = One.ClassVariable if not argument else self.argument_

  def InstanceMethod( self ):
    return self.variable_

  @classmethod
  def ClassMethod( cls ):
    return One.ClassVariable + MODULE_SCOPE
