# Copyright (C) 2016 ycmd contributors
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

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from .python_handlers_test import Python_Handlers_test
from mock import patch
from ycmd import utils
from ycmd.completers.python.jedi_completer import BINARY_NOT_FOUND_MESSAGE
from hamcrest.core.base_matcher import BaseMatcher
from hamcrest import assert_that, has_item, contains, equal_to, is_not # noqa
import sys


class CalledWith( BaseMatcher ):

  def __init__( self, python ):
    self._python = python


  def _extract_python( self, popen ):
    def safe_first( l, default ):
      return next( iter( l ), default )

    call = popen.call_args
    if not call:
      return None

    # The python that SafePopen used is inside a `call` object which contains:
    #  - a tuple of the given positional arguments
    #  - kwargs
    # call( ( ['python', 'arg1', 'arg2' ], ... ), kwargs )
    args, kwargs = call
    return safe_first( safe_first( args, [ None ] ), None )


  def _matches( self, popen ):
    executable = self._extract_python( popen )
    return executable == self._python


  def describe_to( self, description ):
    description.append_description_of( self._python )


  def describe_mismatch( self, item, description ):
    python = self._extract_python( item )
    if python:
      description.append_description_of( python )
    else:
      description.append_text( 'not called' )


def was_called_with_python( python ):
  return CalledWith( python )



class UserDefinedPython_test( Python_Handlers_test ):

  @patch( 'ycmd.utils.SafePopen' )
  def WithoutAnyOption_DefaultToYcmdPython_test( self, *args ):
    self._app.get( '/ready', { 'subserver': 'python' } )
    assert_that( utils.SafePopen, was_called_with_python( sys.executable ) )


  @patch( 'ycmd.utils.SafePopen' )
  @patch( 'ycmd.completers.python.jedi_completer.'
            'JediCompleter._CheckBinaryExists',
          return_value = False )
  def WhenNonExistentPythonIsGiven_ReturnAnError_test( self, *args ):
    python = '/non/existing/path/python'
    with self.UserOption( 'python_binary_path', python ):
      response = self._app.get( '/ready',
                                { 'subserver': 'python' },
                                expect_errors = True ).json

      msg = BINARY_NOT_FOUND_MESSAGE.format( python )
      assert_that( response, self._ErrorMatcher( RuntimeError, msg ) )
      utils.SafePopen.assert_not_called()


  @patch( 'ycmd.utils.SafePopen' )
  @patch( 'ycmd.completers.python.jedi_completer.'
            'JediCompleter._CheckBinaryExists',
          return_value = True )
  def WhenExistingPythonIsGiven_ThatIsUsed_test( self, *args ):
    python = '/existing/python'
    with self.UserOption( 'python_binary_path', python ):
      self._app.get( '/ready', { 'subserver': 'python' } ).json
      assert_that( utils.SafePopen, was_called_with_python( python ) )


  @patch( 'ycmd.utils.SafePopen' )
  @patch( 'ycmd.completers.python.jedi_completer.'
            'JediCompleter._CheckBinaryExists',
          return_value = True )
  def RestartServerWithoutArguments_WillReuseTheLastPython_test( self, *args ):
    request = self._BuildRequest( filetype = 'python',
                                  command_arguments = [ 'RestartServer' ] )
    self._app.post_json( '/run_completer_command', request )
    assert_that( utils.SafePopen, was_called_with_python( sys.executable ) )


  @patch( 'ycmd.utils.SafePopen' )
  @patch( 'ycmd.completers.python.jedi_completer.'
            'JediCompleter._CheckBinaryExists',
          return_value = True )
  def RestartServerWithArgument_WillUseTheSpecifiedPython_test( self, *args ):
    python = '/existing/python'
    request = self._BuildRequest( filetype = 'python',
                                  command_arguments = [ 'RestartServer',
                                                        python ] )
    self._app.post_json( '/run_completer_command', request )
    assert_that( utils.SafePopen, was_called_with_python( python ) )


  @patch( 'ycmd.utils.SafePopen' )
  @patch( 'ycmd.completers.python.jedi_completer.'
            'JediCompleter._CheckBinaryExists',
          return_value = False )
  def RestartServerWithNonExistingPythonArgument_test( self, *args ):
    python = '/non/existing/python'
    request = self._BuildRequest( filetype = 'python',
                                  command_arguments = [ 'RestartServer',
                                                        python ] )
    response = self._app.post_json( '/run_completer_command',
                                    request,
                                    expect_errors = True ).json

    msg = BINARY_NOT_FOUND_MESSAGE.format( python )
    assert_that( response, self._ErrorMatcher( RuntimeError, msg ) )
    assert_that( utils.SafePopen, was_called_with_python( sys.executable ) )
