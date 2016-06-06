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

from hamcrest.core.base_matcher import BaseMatcher
from hamcrest import assert_that, has_item, contains, equal_to, is_not  # noqa
from mock import patch
import sys

from ycmd import utils
from ycmd.completers.python.jedi_completer import BINARY_NOT_FOUND_MESSAGE
from ycmd.tests.python import IsolatedYcmd
from ycmd.tests.test_utils import BuildRequest, ErrorMatcher, UserOption


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


@IsolatedYcmd
@patch( 'ycmd.utils.SafePopen' )
def UserDefinedPython_WithoutAnyOption_DefaultToYcmdPython_test( app, *args ):
  app.get( '/ready', { 'subserver': 'python' } )
  assert_that( utils.SafePopen, was_called_with_python( sys.executable ) )


@IsolatedYcmd
@patch( 'ycmd.utils.SafePopen' )
@patch( 'ycmd.utils.FindExecutable', return_value = None )
def UserDefinedPython_WhenNonExistentPythonIsGiven_ReturnAnError_test( app,
                                                                       *args ):
  python = '/non/existing/path/python'
  with UserOption( 'python_binary_path', python ):
    response = app.get( '/ready',
                        { 'subserver': 'python' },
                        expect_errors = True ).json

    msg = BINARY_NOT_FOUND_MESSAGE.format( python )
    assert_that( response, ErrorMatcher( RuntimeError, msg ) )
    utils.SafePopen.assert_not_called()


@IsolatedYcmd
@patch( 'ycmd.utils.SafePopen' )
@patch( 'ycmd.utils.FindExecutable', side_effect = lambda x: x )
def UserDefinedPython_WhenExistingPythonIsGiven_ThatIsUsed_test( app, *args ):
  python = '/existing/python'
  with UserOption( 'python_binary_path', python ):
    app.get( '/ready', { 'subserver': 'python' } ).json
    assert_that( utils.SafePopen, was_called_with_python( python ) )


@IsolatedYcmd
@patch( 'ycmd.utils.SafePopen' )
@patch( 'ycmd.utils.FindExecutable', side_effect = lambda x: x )
def UserDefinedPython_RestartServerWithoutArguments_WillReuseTheLastPython_test(
  app, *args ):
  request = BuildRequest( filetype = 'python',
                          command_arguments = [ 'RestartServer' ] )
  app.post_json( '/run_completer_command', request )
  assert_that( utils.SafePopen, was_called_with_python( sys.executable ) )


@IsolatedYcmd
@patch( 'ycmd.utils.SafePopen' )
@patch( 'ycmd.utils.FindExecutable', side_effect = lambda x: x )
def UserDefinedPython_RestartServerWithArgument_WillUseTheSpecifiedPython_test(
  app, *args ):
  python = '/existing/python'
  request = BuildRequest( filetype = 'python',
                          command_arguments = [ 'RestartServer', python ] )
  app.post_json( '/run_completer_command', request )
  assert_that( utils.SafePopen, was_called_with_python( python ) )


@IsolatedYcmd
@patch( 'ycmd.utils.SafePopen' )
@patch( 'ycmd.utils.FindExecutable', return_value = None )
def UserDefinedPython_RestartServerWithNonExistingPythonArgument_test( app,
                                                                       *args ):
  python = '/non/existing/python'
  request = BuildRequest( filetype = 'python',
                          command_arguments = [ 'RestartServer', python ] )
  response = app.post_json( '/run_completer_command',
                            request,
                            expect_errors = True ).json

  msg = BINARY_NOT_FOUND_MESSAGE.format( python )
  assert_that( response, ErrorMatcher( RuntimeError, msg ) )
  assert_that( utils.SafePopen, was_called_with_python( sys.executable ) )
