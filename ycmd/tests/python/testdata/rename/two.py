import one


class Two( one.One ):
  def __init__( self, argument ):
    super().__init__( argument )
    self.variable_ = 1


def AtTheEndOfTheFile():
  x = one.One
