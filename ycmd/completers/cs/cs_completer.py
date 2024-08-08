# Copyright (C) 2011-2020 ycmd contributors
#
# This file is part of ycmd.
#
# ycmd is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ycmd is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

import os
import logging

from ycmd.completers.language_server import language_server_completer
from ycmd import responses
from ycmd.utils import ( FindExecutable,
                         FindExecutableWithFallback,
                         LOGGER )
from ycmd import utils

PATH_TO_ROSLYN_OMNISHARP = os.path.join(
  os.path.abspath( os.path.dirname( __file__ ) ),
  '..', '..', '..', 'third_party', 'omnisharp-roslyn'
)
PATH_TO_OMNISHARP_ROSLYN_BINARY = os.path.join(
  PATH_TO_ROSLYN_OMNISHARP, 'Omnisharp.exe' )
if ( not os.path.isfile( PATH_TO_OMNISHARP_ROSLYN_BINARY )
     and os.path.isfile( os.path.join(
       PATH_TO_ROSLYN_OMNISHARP, 'omnisharp', 'OmniSharp.exe' ) ) ):
  PATH_TO_OMNISHARP_ROSLYN_BINARY = (
    os.path.join( PATH_TO_ROSLYN_OMNISHARP, 'omnisharp', 'OmniSharp.exe' ) )


def ShouldEnableCsCompleter( user_options ):
  user_roslyn_path = user_options[ 'roslyn_binary_path' ]
  if user_roslyn_path and not os.path.isfile( user_roslyn_path ):
    LOGGER.error( 'No omnisharp-roslyn executable at %s', user_roslyn_path )
    # We should trust the user who specifically asked for a custom path.
    return False

  if os.path.isfile( user_roslyn_path ):
    roslyn = user_roslyn_path
  else:
    roslyn = PATH_TO_OMNISHARP_ROSLYN_BINARY
  if roslyn:
    return True
  LOGGER.info( 'No mono executable at %s', mono )
  return False


class CsharpCompleter( language_server_completer.LanguageServerCompleter ):
  def __init__( self, user_options ):
    super().__init__( user_options )
    if os.path.isfile( user_options[ 'roslyn_binary_path' ] ):
      self._roslyn_path = user_options[ 'roslyn_binary_path' ]
    else:
      self._roslyn_path = PATH_TO_OMNISHARP_ROSLYN_BINARY


  def GetServerName( self ):
    return 'OmniSharp-Roslyn'


  def GetProjectRootFiles( self ):
    return [ '*.csproj' ]


  def GetCommandLine( self ):
    # TODO: User options?
    cmdline = [ self._roslyn_path, '-lsp' ]
    if utils.LOGGER.isEnabledFor( logging.DEBUG ):
      cmdline += [ '-v' ]
    return cmdline


  def SupportedFiletypes( self ):
    return [ 'cs' ]


  def GetType( self, request_data ):
    raw_hover = self.GetHoverResponse( request_data )
    value = raw_hover[ 'value' ]
    if not value:
      raise RuntimeError( 'No type found.' )
    value = value.split( '\n' )[ 1 ]
    return responses.BuildDetailedInfoResponse( value )
