# Copyright (C) 2016-2020 ycmd contributors
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

from hamcrest import ( assert_that, contains_exactly, empty, equal_to,
                       has_entries, has_entry, instance_of )
from unittest.mock import patch

from ycmd.completers.cs.hook import GetCompleter
from ycmd.tests.cs import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    WaitUntilCompleterServerReady )
from ycmd import user_options_store
from ycmd.utils import ReadFile


@SharedYcmd
def DebugInfo_ServerIsRunning_test( app ):
  filepath = PathToTestFile( 'testy', 'Program.cs' )
  contents = ReadFile( filepath )
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilCompleterServerReady( app, 'cs' )

  request_data = BuildRequest( filepath = filepath,
                               filetype = 'cs' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'C#',
      'servers': contains_exactly( has_entries( {
        'name': 'OmniSharp',
        'is_running': True,
        'executable': instance_of( str ),
        'pid': instance_of( int ),
        'address': instance_of( str ),
        'port': instance_of( int ),
        'logfiles': contains_exactly( instance_of( str ),
                              instance_of( str ) ),
        'extras': contains_exactly( has_entries( {
          'key': 'solution',
          'value': instance_of( str )
        } ) )
      } ) ),
      'items': empty()
    } ) )
  )


@SharedYcmd
def DebugInfo_ServerIsNotRunning_NoSolution_test( app ):
  request_data = BuildRequest( filetype = 'cs' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'C#',
      'servers': contains_exactly( has_entries( {
        'name': 'OmniSharp',
        'is_running': False,
        'executable': instance_of( str ),
        'pid': None,
        'address': None,
        'port': None,
        'logfiles': empty()
      } ) ),
      'items': empty()
    } ) )
  )


def SolutionSelectCheck( app, sourcefile, reference_solution,
                         extra_conf_store = None ):
  # reusable test: verify that the correct solution (reference_solution) is
  #   detected for a given source file (and optionally a given extra_conf)
  if extra_conf_store:
    app.post_json( '/load_extra_conf_file',
                   { 'filepath': extra_conf_store } )

  result = app.post_json( '/debug_info',
                          BuildRequest( completer_target = 'filetype_default',
                                        filepath = sourcefile,
                                        filetype = 'cs' ) ).json

  assert_that(
    result,
    has_entry( 'completer', has_entries( {
      'name': 'C#',
      'servers': contains_exactly( has_entries( {
        'extras': contains_exactly( has_entries( {
          'key': 'solution',
          'value': reference_solution
        } ) )
      } ) )
    } ) )
  )


@SharedYcmd
def DebugInfo_UsesSubfolderHint_test( app ):
  SolutionSelectCheck( app,
                       PathToTestFile( 'testy-multiple-solutions',
                                       'solution-named-like-folder',
                                       'testy', 'Program.cs' ),
                       PathToTestFile( 'testy-multiple-solutions',
                                       'solution-named-like-folder',
                                       'testy.sln' ) )


@SharedYcmd
def DebugInfo_UsesSuperfolderHint_test( app ):
  SolutionSelectCheck( app,
                       PathToTestFile( 'testy-multiple-solutions',
                                       'solution-named-like-folder',
                                       'not-testy', 'Program.cs' ),
                       PathToTestFile( 'testy-multiple-solutions',
                                       'solution-named-like-folder',
                                       'solution-named-like-folder.sln' ) )


@SharedYcmd
def DebugInfo_ExtraConfStoreAbsolute_test( app ):
  SolutionSelectCheck( app,
                       PathToTestFile( 'testy-multiple-solutions',
                                       'solution-not-named-like-folder',
                                       'extra-conf-abs',
                                       'testy', 'Program.cs' ),
                       PathToTestFile( 'testy-multiple-solutions',
                                       'solution-not-named-like-folder',
                                       'testy2.sln' ),
                       PathToTestFile( 'testy-multiple-solutions',
                                       'solution-not-named-like-folder',
                                       'extra-conf-abs',
                                       '.ycm_extra_conf.py' ) )


@SharedYcmd
def DebugInfo_ExtraConfStoreRelative_test( app ):
  SolutionSelectCheck( app,
                       PathToTestFile( 'testy-multiple-solutions',
                                       'solution-not-named-like-folder',
                                       'extra-conf-rel',
                                       'testy', 'Program.cs' ),
                       PathToTestFile( 'testy-multiple-solutions',
                                       'solution-not-named-like-folder',
                                       'extra-conf-rel',
                                       'testy2.sln' ),
                       PathToTestFile( 'testy-multiple-solutions',
                                       'solution-not-named-like-folder',
                                       'extra-conf-rel',
                                       '.ycm_extra_conf.py' ) )


@SharedYcmd
def DebugInfo_ExtraConfStoreNonexisting_test( app ):
  SolutionSelectCheck( app,
                       PathToTestFile( 'testy-multiple-solutions',
                                       'solution-not-named-like-folder',
                                       'extra-conf-bad',
                                       'testy', 'Program.cs' ),
                       PathToTestFile( 'testy-multiple-solutions',
                                       'solution-not-named-like-folder',
                                       'extra-conf-bad',
                                       'testy2.sln' ),
                       PathToTestFile( 'testy-multiple-solutions',
                                       'solution-not-named-like-folder',
                                       'extra-conf-bad',
                                       'testy', '.ycm_extra_conf.py' ) )


def GetCompleter_RoslynFound_test():
  assert_that( GetCompleter( user_options_store.GetAll() ) )


@patch( 'ycmd.completers.cs.cs_completer.PATH_TO_OMNISHARP_ROSLYN_BINARY',
        None )
def GetCompleter_RoslynNotFound_test( *args ):
  assert_that( not GetCompleter( user_options_store.GetAll() ) )


@patch( 'ycmd.completers.cs.cs_completer.FindExecutableWithFallback',
        wraps = lambda x, fb: x if x == 'roslyn' else fb )
@patch( 'os.path.isfile', return_value = True )
def GetCompleter_RoslynFromUserOption_test( *args ):
  user_options = user_options_store.GetAll().copy(
      roslyn_binary_path = 'roslyn' )
  assert_that( GetCompleter( user_options )._roslyn_path, equal_to( 'roslyn' ) )
