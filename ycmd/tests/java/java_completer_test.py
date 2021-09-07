# Copyright (C) 2021 ycmd contributors
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
import requests

from hamcrest import assert_that, equal_to, calling, has_entries, is_not, raises
from unittest.mock import patch
from unittest import TestCase

from ycmd import handlers, user_options_store
from ycmd.tests.test_utils import BuildRequest, ErrorMatcher
from ycmd.tests.java import setUpModule, tearDownModule # noqa
from ycmd.tests.java import SharedYcmd
from ycmd.completers.java import java_completer, hook
from ycmd.completers.java.java_completer import NO_DOCUMENTATION_MESSAGE
from ycmd.tests import IsolatedYcmd as IsolatedYcmdWithoutJava


DEFAULT_OPTIONS = user_options_store.DefaultOptions()


class JavaCompleterTest( TestCase ):
  @patch( 'ycmd.completers.java.java_completer.utils.FindExecutable',
          return_value = '' )
  def test_ShouldEnableJavaCompleter_NoJava( *args ):
    assert_that( java_completer.ShouldEnableJavaCompleter( DEFAULT_OPTIONS ),
                 equal_to( False ) )


  @IsolatedYcmdWithoutJava( {
    'java_binary_path': '/this/path/does/not/exist' } )
  def test_ShouldEnableJavaCompleter_JavaNotFound( self, app ):
    request_data = BuildRequest( filetype = 'java' )
    response = app.post_json( '/defined_subcommands',
                              request_data,
                              expect_errors = True )
    assert_that( response.status_code,
                 equal_to( requests.codes.internal_server_error ) )
    assert_that( response.json,
                 ErrorMatcher( ValueError,
                               'No semantic completer exists for filetypes: '
                               "['java']" ) )


  def test_ShouldEnableJavaCompleter_NotInstalled( self ):
    orig_language_server_home = java_completer.LANGUAGE_SERVER_HOME
    try:
      java_completer.LANGUAGE_SERVER_HOME = ''
      assert_that( java_completer.ShouldEnableJavaCompleter( DEFAULT_OPTIONS ),
                   equal_to( False ) )
    finally:
      java_completer.LANGUAGE_SERVER_HOME = orig_language_server_home


  @patch( 'glob.glob', return_value = [] )
  def test_ShouldEnableJavaCompleter_NoLauncherJar( self, glob ):
    assert_that( java_completer.ShouldEnableJavaCompleter( DEFAULT_OPTIONS ),
                 equal_to( False ) )
    glob.assert_called()


  def test_WorkspaceDirForProject_HashProjectDir( self ):
    assert_that(
      java_completer._WorkspaceDirForProject( os.getcwd(),
                                              os.getcwd(),
                                              False ),
      equal_to( java_completer._WorkspaceDirForProject( os.getcwd(),
                                                        os.getcwd(),
                                                        False ) )
    )


  def test_WorkspaceDirForProject_UniqueDir( self ):
    assert_that(
      java_completer._WorkspaceDirForProject( os.getcwd(),
                                              os.getcwd(),
                                              True ),
      is_not( equal_to( java_completer._WorkspaceDirForProject( os.getcwd(),
                                                                os.getcwd(),
                                                                True ) ) )
    )


  @SharedYcmd
  def test_JavaCompleter_GetType( self, app ):
    completer = handlers._server_state.GetFiletypeCompleter( [ 'java' ] )

    # The LSP defines the hover response as either:
    # - a string
    # - a list of strings
    # - an object with keys language, value
    # - a list of objects with keys language, value
    # = an object with keys kind, value

    with patch.object( completer, 'GetHoverResponse', return_value = '' ):
      assert_that( calling( completer.GetType ).with_args( BuildRequest() ),
                   raises( RuntimeError, 'Unknown type' ) )

    with patch.object( completer, 'GetHoverResponse', return_value = 'string' ):
      assert_that( calling( completer.GetType ).with_args( BuildRequest() ),
                   raises( RuntimeError, 'Unknown type' ) )

    with patch.object( completer, 'GetHoverResponse', return_value = 'value' ):
      assert_that( calling( completer.GetType ).with_args( BuildRequest() ),
                   raises( RuntimeError, 'Unknown type' ) )

    with patch.object( completer, 'GetHoverResponse', return_value = [] ):
      assert_that( calling( completer.GetType ).with_args( BuildRequest() ),
                   raises( RuntimeError, 'Unknown type' ) )

    with patch.object( completer,
                       'GetHoverResponse',
                       return_value = [ 'a', 'b' ] ):
      assert_that( calling( completer.GetType ).with_args( BuildRequest() ),
                   raises( RuntimeError, 'Unknown type' ) )

    with patch.object( completer,
                       'GetHoverResponse',
                       return_value = { 'language': 'java', 'value': 'test' } ):
      assert_that( completer.GetType( BuildRequest() ),
                   has_entries( { 'message': 'test' } ) )

    with patch.object(
      completer,
      'GetHoverResponse',
      return_value = [ { 'language': 'java', 'value': 'test' } ] ):
      assert_that( completer.GetType( BuildRequest() ),
                   has_entries( { 'message': 'test' } ) )

    with patch.object(
      completer,
      'GetHoverResponse',
      return_value = [ { 'language': 'java', 'value': 'test' },
                       { 'language': 'java', 'value': 'not test' } ] ):
      assert_that( completer.GetType( BuildRequest() ),
                   has_entries( { 'message': 'test' } ) )

    with patch.object(
      completer,
      'GetHoverResponse',
      return_value = [ { 'language': 'java', 'value': 'test' },
                       'line 1',
                       'line 2' ] ):
      assert_that( completer.GetType( BuildRequest() ),
                   has_entries( { 'message': 'test' } ) )


    with patch.object(
        completer,
        'GetHoverResponse',
        return_value = { 'kind': 'plaintext', 'value': 'test' } ):
      assert_that( calling( completer.GetType ).with_args( BuildRequest() ),
                   raises( RuntimeError, 'Unknown type' ) )


  @SharedYcmd
  def test_JavaCompleter_GetDoc( self, app ):
    completer = handlers._server_state.GetFiletypeCompleter( [ 'java' ] )

    # The LSP defines the hover response as either:
    # - a string
    # - a list of strings
    # - an object with keys language, value
    # - a list of objects with keys language, value
    # = an object with keys kind, value

    with patch.object( completer, 'GetHoverResponse', return_value = '' ):
      assert_that( calling( completer.GetDoc ).with_args( BuildRequest() ),
                   raises( RuntimeError, NO_DOCUMENTATION_MESSAGE ) )

    with patch.object( completer, 'GetHoverResponse', return_value = 'string' ):
      assert_that( calling( completer.GetDoc ).with_args( BuildRequest() ),
                   raises( RuntimeError, NO_DOCUMENTATION_MESSAGE ) )

    with patch.object( completer, 'GetHoverResponse', return_value = [] ):
      assert_that( calling( completer.GetDoc ).with_args( BuildRequest() ),
                   raises( RuntimeError, NO_DOCUMENTATION_MESSAGE ) )

    with patch.object( completer,
                       'GetHoverResponse',
                       return_value = [ 'a', 'b' ] ):
      assert_that( completer.GetDoc( BuildRequest() ),
                   has_entries( { 'detailed_info': 'a\nb' } ) )

    with patch.object( completer,
                       'GetHoverResponse',
                       return_value = { 'language': 'java', 'value': 'test' } ):
      assert_that( calling( completer.GetDoc ).with_args( BuildRequest() ),
                   raises( RuntimeError, NO_DOCUMENTATION_MESSAGE ) )

    with patch.object(
      completer,
      'GetHoverResponse',
      return_value = [ { 'language': 'java', 'value': 'test' } ] ):
      assert_that( calling( completer.GetDoc ).with_args( BuildRequest() ),
                   raises( RuntimeError, NO_DOCUMENTATION_MESSAGE ) )

    with patch.object(
      completer,
      'GetHoverResponse',
      return_value = [ { 'language': 'java', 'value': 'test' },
                       { 'language': 'java', 'value': 'not test' } ] ):
      assert_that( calling( completer.GetDoc ).with_args( BuildRequest() ),
                   raises( RuntimeError, NO_DOCUMENTATION_MESSAGE ) )

    with patch.object(
      completer,
      'GetHoverResponse',
      return_value = [ { 'language': 'java', 'value': 'test' },
                       'line 1',
                       'line 2' ] ):
      assert_that( completer.GetDoc( BuildRequest() ),
                   has_entries( { 'detailed_info': 'line 1\nline 2' } ) )


    with patch.object(
        completer,
        'GetHoverResponse',
        return_value = { 'kind': 'plaintext', 'value': 'test' } ):
      assert_that( calling( completer.GetDoc ).with_args( BuildRequest() ),
                   raises( RuntimeError, NO_DOCUMENTATION_MESSAGE ) )


  @patch( 'ycmd.completers.java.hook.ShouldEnableJavaCompleter',
          return_value = False )
  def test_JavaHook_JavaNotEnabled( *args ):
    assert_that( hook.GetCompleter( {} ), equal_to( None ) )
