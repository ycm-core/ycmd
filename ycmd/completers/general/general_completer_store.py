# Copyright (C) 2013-2018 ycmd contributors
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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from ycmd.completers.completer import Completer
from ycmd.completers.all.identifier_completer import IdentifierCompleter
from ycmd.completers.general.filename_completer import FilenameCompleter
from ycmd.completers.general.ultisnips_completer import UltiSnipsCompleter


class GeneralCompleterStore( Completer ):
  """
  Holds a list of completers that can be used in all filetypes.

  It overrides all Completer API methods so that specific calls to
  GeneralCompleterStore are passed to all general completers.
  """

  def __init__( self, user_options ):
    super( GeneralCompleterStore, self ).__init__( user_options )
    self._identifier_completer = IdentifierCompleter( user_options )
    self._filename_completer = FilenameCompleter( user_options )
    self._ultisnips_completer = UltiSnipsCompleter( user_options )
    self._non_filename_completers = [ self._identifier_completer ]
    if user_options.get( 'use_ultisnips_completer', True ):
      self._non_filename_completers.append( self._ultisnips_completer )
    self._all_completers = [ self._identifier_completer,
                             self._filename_completer,
                             self._ultisnips_completer ]


  def SupportedFiletypes( self ):
    return set()


  def GetIdentifierCompleter( self ):
    return self._identifier_completer


  def ComputeCandidates( self, request_data ):
    candidates = self._filename_completer.ComputeCandidates( request_data )
    if candidates:
      return candidates
    for completer in self._non_filename_completers:
      candidates += completer.ComputeCandidates( request_data )
    return candidates


  def OnFileReadyToParse( self, request_data ):
    for completer in self._all_completers:
      completer.OnFileReadyToParse( request_data )


  def OnBufferVisit( self, request_data ):
    for completer in self._all_completers:
      completer.OnBufferVisit( request_data )


  def OnBufferUnload( self, request_data ):
    for completer in self._all_completers:
      completer.OnBufferUnload( request_data )


  def OnInsertLeave( self, request_data ):
    for completer in self._all_completers:
      completer.OnInsertLeave( request_data )


  def OnCurrentIdentifierFinished( self, request_data ):
    for completer in self._all_completers:
      completer.OnCurrentIdentifierFinished( request_data )


  def GettingCompletions( self ):
    for completer in self._all_completers:
      completer.GettingCompletions()


  def Shutdown( self ):
    for completer in self._all_completers:
      completer.Shutdown()
