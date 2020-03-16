# Copyright (C) 2020 ycmd contributors
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

from ycmd import responses, utils
from ycmd.completers.language_server import language_server_completer


class GenericLSPCompleter( language_server_completer.LanguageServerCompleter ):
  def __init__( self, user_options, server_settings ):
    self._name = server_settings[ 'name' ]
    self._supported_filetypes = server_settings[ 'filetypes' ]
    self._project_root_files = server_settings.get( 'project_root_files', [] )
    super().__init__( user_options )
    self._command_line = server_settings[ 'cmdline' ]
    self._command_line[ 0 ] = utils.FindExecutable( self._command_line[ 0 ] )


  def GetProjectRootFiles( self ):
    return self._project_root_files


  def Language( self ):
    return self._name


  def GetServerName( self ):
    return self._name + 'Completer'


  def GetCommandLine( self ):
    return self._command_line


  def GetCustomSubcommands( self ):
    return { 'GetHover': lambda self, request_data, args:
      self._GetHover( request_data ) }


  def _GetHover( self, request_data ):
    raw_hover = self.GetHoverResponse( request_data )
    if isinstance( raw_hover, dict ):
      # Both MarkedString and MarkupContent contain 'value' key.
      # MarkupContent is the only one not deprecated.
      return responses.BuildDetailedInfoResponse( raw_hover[ 'value' ] )
    if isinstance( raw_hover, str ):
      # MarkedString might be just a string.
      return responses.BuildDetailedInfoResponse( raw_hover )
    # If we got this far, this is a list of MarkedString objects.
    lines = []
    for marked_string in raw_hover:
      if isinstance( marked_string, str ):
        lines.append( marked_string )
      else:
        lines.append( marked_string[ 'value' ] )
    return responses.BuildDetailedInfoResponse( '\n'.join( lines ) )


  def GetCodepointForCompletionRequest( self, request_data ):
    if request_data[ 'force_semantic' ]:
      return request_data[ 'column_codepoint' ]
    return super().GetCodepointForCompletionRequest( request_data )


  def SupportedFiletypes( self ):
    return self._supported_filetypes
