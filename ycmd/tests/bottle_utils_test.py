# Copyright (C) 2016 ycmd contributors.
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

# Intentionally not importing unicode_literals!
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from nose.tools import eq_
from mock import patch, call
from ycmd import bottle_utils
from ycmd.tests.test_utils import Py2Only, Py3Only
import bottle


@Py2Only
@patch( 'bottle.response' )
def SetResponseHeader_Py2CorrectTypesWithStr_test( *args ):
  bottle_utils.SetResponseHeader( 'foo', 'bar' )
  eq_( bottle.response.set_header.call_args, call( 'foo', u'bar' ) )


@Py2Only
@patch( 'bottle.response' )
def SetResponseHeader_Py2CorrectTypesWithUnicode_test( *args ):
  bottle_utils.SetResponseHeader( u'foo', u'bar' )
  eq_( bottle.response.set_header.call_args, call( 'foo', u'bar' ) )


@Py3Only
@patch( 'bottle.response' )
def SetResponseHeader_Py3CorrectTypesWithBytes_test( *args ):
  bottle_utils.SetResponseHeader( b'foo', b'bar' )
  eq_( bottle.response.set_header.call_args, call( u'foo', u'bar' ) )


@Py3Only
@patch( 'bottle.response' )
def SetResponseHeader_Py3CorrectTypesWithUnicode_test( *args ):
  bottle_utils.SetResponseHeader( u'foo', u'bar' )
  eq_( bottle.response.set_header.call_args, call( u'foo', u'bar' ) )
