#!/usr/bin/env python
#
# Copyright (C) 2011, 2012  Stephen Sugden <me@stephensugden.com>
#                           Google Inc.
#                           Stanislav Golovanov <stgolovanov@gmail.com>
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

import subprocess
import json
from ycmd.completers.completer import Completer

class HackCompleter( Completer ):
  """
  A completer that offers integration with the HHVM typechecker.
  """

  def __init__( self, user_options ):
    super( HackCompleter, self ).__init__( user_options )

  def SupportedFiletypes( self ):
    """ Just hack """
    return [ 'hack' ]

  def ComputeCandidatesInner( self, request_data ):
    # Get the contents of the file and break it up by line.
    filename = request_data['filepath']
    contents = request_data['file_data'][filename]['contents']
    contents = contents.splitlines(True)

    # Lines are zero indexed.
    line = request_data['line_num'] - 1
    column = request_data['column_num']

    # Insert the autocomplete token into the file.
    contents[line] = contents[line][:column] + "AUTO332" + contents[line][column:]

    # Join everything back up.
    contents = "\n".join(contents)

    # completion_suggestions = call(["hh_client", "--auto-complete"])
    proc = subprocess.Popen(["hh_client", "--auto-complete"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    completion_suggestions = proc.communicate(contents)
    completion_suggestions = json.loads(completion_suggestions)

    for suggestion in completion_suggestions:
        print suggestion

