def MultipleArguments( a, b, c ):
  pass


def KeywordArguments( d, e, *args, **kwargs ):
  pass


class Class:
  def __init__( self, argument ):
    self.Method()
    self.MultipleArgumentsMethod( argument )
    KeywordArguments( 1, 2, 4, 5, test=6 )
    MultipleArguments( 'test'.center( 100, ' ' ), 10, Class( 10 ) )

  def Method( self ):
    pass

  def MultipleArgumentsMethod( self, this_is_an_argument ):
    pass


if something:
  def MultipleDefinitions( many, more, arguments, to, this, one ):
    pass
else:
  def MultipleDefinitions( a, b, c ):
    pass

MultipleDefinitions( 1, 2, 3, 4,



