# Copyright (C) 2011, 2012 Google Inc.
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


class GeneralCompleter( Completer ):
  """
  A base class for General completers in YCM. A general completer is used in all
  filetypes.

  Because this is a subclass of Completer class, you should refer to the
  Completer class documentation. Do NOT use this class for semantic completers!
  Subclass Completer directly.

  """
  def __init__( self, user_options ):
    super( GeneralCompleter, self ).__init__( user_options )


  def SupportedFiletypes( self ):
    return set()
