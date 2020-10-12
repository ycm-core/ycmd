# Copyright (C) 2015-2020 ycmd contributors
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

from hamcrest import ( assert_that, empty, has_entries, has_items )

from ycmd.utils import ReadFile
from ycmd.tests.clang import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( EMPTY_SIGNATURE_HELP,
                                    BuildRequest,
                                    CompletionEntryMatcher )


@SharedYcmd
def SignatureHelp_NotImplemented_test( app ):
  app.post_json(
    '/load_extra_conf_file',
    { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )

  filepath = PathToTestFile( 'unity.cc' )
  contents = ReadFile( filepath )

  app.post_json( '/event_notification',
                 BuildRequest( filepath = filepath,
                               contents = contents,
                               filetype = 'cpp',
                               event_name = 'FileReadyToParse' ) )

  # Doing a completion proves that we have semantic parsing working
  response_data = app.post_json( '/completions',
                                 BuildRequest( filepath = filepath,
                                               contents = contents,
                                               filetype = 'cpp',
                                               line_num = 27,
                                               column_num = 11,
                                               force_semantic = True ) ).json

  assert_that( response_data[ 'completions' ],
               has_items( CompletionEntryMatcher( 'an_int' ),
                          CompletionEntryMatcher( 'a_char' ) ) )

  # Signature help request always returns nothing
  # FIXME: A method to say "don't bother sending more signature help request"
  response_data = app.post_json( '/signature_help',
                                BuildRequest( filepath = filepath,
                                              contents = contents,
                                              filetype = 'cpp',
                                              line_num = 24,
                                              column_num = 19 ) ).json

  assert_that( response_data, has_entries( {
    'errors': empty(),
    'signature_help': EMPTY_SIGNATURE_HELP
  } ) )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
