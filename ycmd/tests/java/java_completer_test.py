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

from hamcrest import assert_that, equal_to, is_not
from mock import patch

from ycmd.completers.java import java_completer


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
