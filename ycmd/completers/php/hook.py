# Copyright (C) 2015 Neo Mofoka <neo@jeteon.com>

from ycmd.completers.php.ci_completer import CodeIntelCompleter

def GetCompleter( user_options ):
  return CodeIntelCompleter( user_options )  
