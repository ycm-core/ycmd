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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

import inspect
from mock import patch

from hamcrest import ( assert_that, calling, equal_to, has_length, none, raises,
                       same_instance )
from ycmd import extra_conf_store
from ycmd.responses import UnknownExtraConf
from ycmd.tests import PathToTestFile
from ycmd.tests.test_utils import UserOption


class ExtraConfStore_test():

  def setUp( self ):
    extra_conf_store.Reset()


  def ModuleForSourceFile_UnknownExtraConf_test( self ):
    filename = PathToTestFile( 'extra_conf', 'project', 'some_file' )
    assert_that(
      calling( extra_conf_store.ModuleForSourceFile ).with_args( filename ),
      raises( UnknownExtraConf, 'Found .*\.ycm_extra_conf\.py\. Load?' )
    )


  def ModuleForSourceFile_NoConfirmation_test( self ):
    filename = PathToTestFile( 'extra_conf', 'project', 'some_file' )
    extra_conf_file = PathToTestFile( 'extra_conf', 'project',
                                      '.ycm_extra_conf.py' )
    with UserOption( 'confirm_extra_conf', 0 ):
      module = extra_conf_store.ModuleForSourceFile( filename )
      assert_that( inspect.ismodule( module ) )
      assert_that( inspect.getfile( module ), equal_to( extra_conf_file ) )


  def ModuleForSourceFile_Whitelisted_test( self ):
    filename = PathToTestFile( 'extra_conf', 'project', 'some_file' )
    extra_conf_file = PathToTestFile( 'extra_conf', 'project',
                                      '.ycm_extra_conf.py' )
    with UserOption( 'extra_conf_globlist', [ extra_conf_file ] ):
      module = extra_conf_store.ModuleForSourceFile( filename )
      assert_that( inspect.ismodule( module ) )
      assert_that( inspect.getfile( module ), equal_to( extra_conf_file ) )


  def ModuleForSourceFile_Blacklisted_test( self ):
    filename = PathToTestFile( 'extra_conf', 'project', 'some_file' )
    extra_conf_file = PathToTestFile( 'extra_conf', 'project',
                                      '.ycm_extra_conf.py' )
    with UserOption( 'extra_conf_globlist', [ '!' + extra_conf_file ] ):
      assert_that( extra_conf_store.ModuleForSourceFile( filename ), none() )


  def ModuleForSourceFile_GlobalExtraConf_test( self ):
    filename = PathToTestFile( 'extra_conf', 'some_file' )
    extra_conf_file = PathToTestFile( 'extra_conf', 'global_extra_conf.py' )
    with UserOption( 'global_ycm_extra_conf', extra_conf_file ):
      module = extra_conf_store.ModuleForSourceFile( filename )
      assert_that( inspect.ismodule( module ) )
      assert_that( inspect.getfile( module ), equal_to( extra_conf_file ) )


  @patch( 'ycmd.extra_conf_store._logger', autospec = True )
  def CallGlobalExtraConfMethod_NoGlobalExtraConf_test( self, logger ):
    with UserOption( 'global_ycm_extra_conf',
                     PathToTestFile( 'extra_conf', 'no_extra_conf.py' ) ):
      extra_conf_store._CallGlobalExtraConfMethod( 'SomeMethod' )
    assert_that( logger.method_calls, has_length( 1 ) )
    logger.debug.assert_called_with( 'No global extra conf, not calling method '
                                     'SomeMethod' )


  @patch( 'ycmd.extra_conf_store._logger', autospec = True )
  def CallGlobalExtraConfMethod_NoMethodInGlobalExtraConf_test( self, logger ):
    with UserOption( 'global_ycm_extra_conf',
                     PathToTestFile( 'extra_conf', 'global_extra_conf.py' ) ):
      extra_conf_store._CallGlobalExtraConfMethod( 'MissingMethod' )
    assert_that( logger.method_calls, has_length( 1 ) )
    logger.debug.assert_called_with( 'Global extra conf not loaded or '
                                     'no function MissingMethod' )


  @patch( 'ycmd.extra_conf_store._logger', autospec = True )
  def CallGlobalExtraConfMethod_NoExceptionFromMethod_test( self, logger ):
    extra_conf_file = PathToTestFile( 'extra_conf', 'global_extra_conf.py' )
    with UserOption( 'global_ycm_extra_conf', extra_conf_file ):
      extra_conf_store._CallGlobalExtraConfMethod( 'NoException' )
    assert_that( logger.method_calls, has_length( 1 ) )
    logger.info.assert_called_with( 'Calling global extra conf method '
                                    'NoException on conf file '
                                    '{0}'.format( extra_conf_file ) )


  @patch( 'ycmd.extra_conf_store._logger', autospec = True )
  def CallGlobalExtraConfMethod_CatchExceptionFromMethod_test( self, logger ):
    extra_conf_file = PathToTestFile( 'extra_conf', 'global_extra_conf.py' )
    with UserOption( 'global_ycm_extra_conf', extra_conf_file ):
      extra_conf_store._CallGlobalExtraConfMethod( 'RaiseException' )
    assert_that( logger.method_calls, has_length( 2 ) )
    logger.info.assert_called_with( 'Calling global extra conf method '
                                    'RaiseException on conf file '
                                    '{0}'.format( extra_conf_file ) )
    logger.exception.assert_called_with(
      'Error occurred while calling global extra conf method RaiseException '
      'on conf file {0}'.format( extra_conf_file ) )


  @patch( 'ycmd.extra_conf_store._logger', autospec = True )
  def CallGlobalExtraConfMethod_CatchExceptionFromExtraConf_test( self,
                                                                  logger ):
    extra_conf_file = PathToTestFile( 'extra_conf', 'erroneous_extra_conf.py' )
    with UserOption( 'global_ycm_extra_conf', extra_conf_file ):
      extra_conf_store._CallGlobalExtraConfMethod( 'NoException' )
    assert_that( logger.method_calls, has_length( 1 ) )
    logger.exception.assert_called_with( 'Error occurred while '
                                         'loading global extra conf '
                                         '{0}'.format( extra_conf_file ) )


  def Load_DoNotReloadExtraConf_NoForce_test( self ):
    extra_conf_file = PathToTestFile( 'extra_conf', 'project',
                                      '.ycm_extra_conf.py' )
    with patch( 'ycmd.extra_conf_store._ShouldLoad', return_value = True ):
      module = extra_conf_store.Load( extra_conf_file )
      assert_that( inspect.ismodule( module ) )
      assert_that( inspect.getfile( module ), equal_to( extra_conf_file ) )
      assert_that(
        extra_conf_store.Load( extra_conf_file ),
        same_instance( module )
      )


  def Load_DoNotReloadExtraConf_ForceEqualsTrue_test( self ):
    extra_conf_file = PathToTestFile( 'extra_conf', 'project',
                                      '.ycm_extra_conf.py' )
    with patch( 'ycmd.extra_conf_store._ShouldLoad', return_value = True ):
      module = extra_conf_store.Load( extra_conf_file )
      assert_that( inspect.ismodule( module ) )
      assert_that( inspect.getfile( module ), equal_to( extra_conf_file ) )
      assert_that(
        extra_conf_store.Load( extra_conf_file, force = True ),
        same_instance( module )
      )
