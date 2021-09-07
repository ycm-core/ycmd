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

from hamcrest import ( assert_that, empty, has_entries )
from unittest import TestCase

from ycmd.tests import SharedYcmd, IsolatedYcmd
from ycmd.tests.test_utils import ( EMPTY_SIGNATURE_HELP,
                                    BuildRequest )


class SignatureHelpTest( TestCase ):
  @SharedYcmd
  def test_SignatureHelp_IdentifierCompleter( self, app ):
    event_data = BuildRequest( contents = 'foo foogoo ba',
                               event_name = 'FileReadyToParse' )

    app.post_json( '/event_notification', event_data )

    # query is 'oo'
    request_data = BuildRequest( contents = 'oo foo foogoo ba',
                                    column_num = 3 )
    response_data = app.post_json( '/signature_help', request_data ).json

    assert_that( response_data, has_entries( {
      'errors': empty(),
      'signature_help': EMPTY_SIGNATURE_HELP
    } ) )


  @IsolatedYcmd( { 'disable_signature_help': 1 } )
  def test_SignatureHelp_IdentifierCompleter_disabled( self, app ):
    event_data = BuildRequest( contents = 'foo foogoo ba',
                               event_name = 'FileReadyToParse' )

    app.post_json( '/event_notification', event_data )

    # query is 'oo'
    request_data = BuildRequest( contents = 'oo foo foogoo ba',
                                    column_num = 3 )
    response_data = app.post_json( '/signature_help', request_data ).json

    assert_that( response_data, has_entries( {
      'errors': empty(),
      'signature_help': EMPTY_SIGNATURE_HELP
    } ) )
