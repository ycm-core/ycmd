# Copyright (C) 2013 Google Inc.
#               2015 ycmd contributors
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
from future import standard_library
from future.utils import iteritems
standard_library.install_aliases()
from builtins import *  # noqa

from future.utils import PY2
from ycmd.completers.completer import Completer
from ycmd.responses import BuildCompletionData
from ycmd.utils import OnMac, OnWindows
import ycm_core
import os.path

try:
  from unittest import skipIf
except ImportError:
  from unittest2 import skipIf

Py2Only = skipIf( not PY2, 'Python 2 only' )
Py3Only = skipIf( PY2, 'Python 3 only' )
WindowsOnly = skipIf( not OnWindows(), 'Windows only' )
ClangOnly = skipIf( not ycm_core.HasClangSupport(),
                    'Only when Clang support available' )
MacOnly = skipIf( not OnMac(), 'Mac only' )


def BuildRequest( **kwargs ):
  filepath = kwargs[ 'filepath' ] if 'filepath' in kwargs else '/foo'
  contents = kwargs[ 'contents' ] if 'contents' in kwargs else ''
  filetype = kwargs[ 'filetype' ] if 'filetype' in kwargs else 'foo'

  request = {
    'line_num': 1,
    'column_num': 1,
    'filepath': filepath,
    'file_data': {
      filepath: {
        'contents': contents,
        'filetypes': [ filetype ]
      }
    }
  }

  for key, value in iteritems( kwargs ):
    if key in [ 'contents', 'filetype', 'filepath' ]:
      continue

    if key in request and isinstance( request[ key ], dict ):
      # allow updating the 'file_data' entry
      request[ key ].update( value )
    else:
      request[ key ] = value

  return request


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )


class DummyCompleter( Completer ):
  def __init__( self, user_options ):
    super( DummyCompleter, self ).__init__( user_options )

  def SupportedFiletypes( self ):
    return []


  def ComputeCandidatesInner( self, request_data ):
    return [ BuildCompletionData( candidate )
             for candidate in self.CandidatesList() ]


  # This method is here for testing purpose, so it can be mocked during tests
  def CandidatesList( self ):
    return []
