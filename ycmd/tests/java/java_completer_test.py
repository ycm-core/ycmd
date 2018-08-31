# Copyright (C) 2017 ycmd contributors
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

import os

from hamcrest import assert_that, equal_to, calling, has_entries, is_not, raises
from mock import patch

from ycmd import handlers
from ycmd.tests.test_utils import BuildRequest
from ycmd.tests.java import SharedYcmd
from ycmd.completers.java import java_completer, hook
from ycmd.completers.java.java_completer import NO_DOCUMENTATION_MESSAGE


def ShouldEnableJavaCompleter_NoJava_test():
  orig_java_path = java_completer.PATH_TO_JAVA
  try:
    java_completer.PATH_TO_JAVA = ''
    assert_that( java_completer.ShouldEnableJavaCompleter(), equal_to( False ) )
  finally:
    java_completer.PATH_TO_JAVA = orig_java_path


def ShouldEnableJavaCompleter_NotInstalled_test():
  orig_language_server_home = java_completer.LANGUAGE_SERVER_HOME
  try:
    java_completer.LANGUAGE_SERVER_HOME = ''
    assert_that( java_completer.ShouldEnableJavaCompleter(), equal_to( False ) )
  finally:
    java_completer.LANGUAGE_SERVER_HOME = orig_language_server_home


@patch( 'glob.glob', return_value = [] )
def ShouldEnableJavaCompleter_NoLauncherJar_test( glob ):
  assert_that( java_completer.ShouldEnableJavaCompleter(), equal_to( False ) )
  glob.assert_called()


def WorkspaceDirForProject_HashProjectDir_test():
  assert_that(
    java_completer._WorkspaceDirForProject( os.getcwd(), False ),
    equal_to( java_completer._WorkspaceDirForProject( os.getcwd(), False ) )
  )


def WorkspaceDirForProject_UniqueDir_test():
  assert_that(
    java_completer._WorkspaceDirForProject( os.getcwd(), True ),
    is_not( equal_to( java_completer._WorkspaceDirForProject( os.getcwd(),
                                                              True ) ) )
  )


@SharedYcmd
def JavaCompleter_GetType_test( app ):
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


  with patch.object( completer,
                     'GetHoverResponse',
                     return_value = { 'kind': 'plaintext', 'value': 'test' } ):
    assert_that( calling( completer.GetType ).with_args( BuildRequest() ),
                 raises( RuntimeError, 'Unknown type' ) )


@SharedYcmd
def JavaCompleter_GetDoc_test( app ):
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


  with patch.object( completer,
                     'GetHoverResponse',
                     return_value = { 'kind': 'plaintext', 'value': 'test' } ):
    assert_that( calling( completer.GetDoc ).with_args( BuildRequest() ),
                 raises( RuntimeError, NO_DOCUMENTATION_MESSAGE ) )


@SharedYcmd
def JavaCompleter_UnknownCommand_test( app ):
  completer = handlers._server_state.GetFiletypeCompleter( [ 'java' ] )

  notification = {
    'command': 'this_is_not_a_real_command',
    'params': {}
  }
  assert_that( completer.HandleServerCommand( BuildRequest(), notification ),
               equal_to( None ) )



@patch( 'ycmd.completers.java.hook.ShouldEnableJavaCompleter',
        return_value = False )
def JavaHook_JavaNotEnabled_test( *args ):
  assert_that( hook.GetCompleter( {} ), equal_to( None ) )
