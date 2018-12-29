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

import threading
from future.utils import itervalues
from importlib import import_module
from ycmd.completers.general.general_completer_store import (
    GeneralCompleterStore )
from ycmd.utils import LOGGER


class ServerState( object ):
  def __init__( self, user_options ):
    self._user_options = user_options
    self._filetype_completers = {}
    self._filetype_completers_lock = threading.Lock()
    self._gencomp = GeneralCompleterStore( self._user_options )


  @property
  def user_options( self ):
    return self._user_options


  def Shutdown( self ):
    with self._filetype_completers_lock:
      for completer in self._filetype_completers.values():
        if completer:
          completer.Shutdown()

    self._gencomp.Shutdown()


  def _GetFiletypeCompleterForFiletype( self, filetype ):
    with self._filetype_completers_lock:
      try:
        return self._filetype_completers[ filetype ]
      except KeyError:
        pass

      try:
        module = import_module( 'ycmd.completers.{}.hook'.format( filetype ) )
        completer = module.GetCompleter( self._user_options )
      except ImportError:
        completer = None

      supported_filetypes = { filetype }
      if completer:
        supported_filetypes.update( completer.SupportedFiletypes() )

      for supported_filetype in supported_filetypes:
        if supported_filetype not in self._filetype_completers:
          self._filetype_completers[ supported_filetype ] = completer
      return completer


  def GetFiletypeCompleter( self, current_filetypes ):
    completers = [ self._GetFiletypeCompleterForFiletype( filetype )
                   for filetype in current_filetypes ]

    for completer in completers:
      if completer:
        return completer

    raise ValueError( 'No semantic completer exists for filetypes: {0}'.format(
        current_filetypes ) )


  def GetLoadedFiletypeCompleters( self ):
    with self._filetype_completers_lock:
      return { completer for completer in
               itervalues( self._filetype_completers ) if completer }


  def FiletypeCompletionAvailable( self, filetypes ):
    try:
      self.GetFiletypeCompleter( filetypes )
      return True
    except Exception:
      LOGGER.exception( 'Semantic completion not available for %s', filetypes )
      return False


  def FiletypeCompletionUsable( self, filetypes ):
    return ( self.CurrentFiletypeCompletionEnabled( filetypes ) and
             self.FiletypeCompletionAvailable( filetypes ) )


  def ShouldUseFiletypeCompleter( self, request_data ):
    """Determines whether or not the semantic completer should be called."""
    filetypes = request_data[ 'filetypes' ]
    if not self.FiletypeCompletionUsable( filetypes ):
      # don't use semantic, ignore whether or not the user requested forced
      # completion
      return False

    if request_data[ 'force_semantic' ]:
      # use semantic, and it was forced
      return True

    # was not forced. check the conditions for triggering
    return self.GetFiletypeCompleter( filetypes ).ShouldUseNow(
      request_data )


  def GetGeneralCompleter( self ):
    return self._gencomp


  def CurrentFiletypeCompletionEnabled( self, current_filetypes ):
    filetype_to_disable = self._user_options[
        'filetype_specific_completion_to_disable' ]
    if '*' in filetype_to_disable:
      return False
    else:
      return not all( x in filetype_to_disable for x in current_filetypes )
