# Copyright (C) 2016  ycmd contributors.
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

from binascii import hexlify
from nose.tools import eq_, ok_, raises
from ycmd import hmac_utils as hu


def CreateHmac_Basic_test():
  # Test vectors from Wikipedia (HMAC_SHA256): https://goo.gl/cvX0Tn
  eq_( hexlify( hu.CreateHmac( 'The quick brown fox jumps over the lazy dog',
                               'key' ) ),
       'f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8' )


def CreateRequestHmac_Basic_test():
  eq_( hexlify( hu.CreateRequestHmac( 'GET', '/foo', 'body', 'key' ) ),
       'bfbb6bc7a2b3eca2a78f4e7ec8a7dfa7e58bb8974166eaf20e0224d999894b34' )


def SecureStringsEqual_Basic_test():
  ok_( hu.SecureStringsEqual( 'foo', 'foo' ) )
  ok_( not hu.SecureStringsEqual( 'foo', 'goo' ) )


def SecureStringsEqual_Empty_test():
  ok_( hu.SecureStringsEqual( '', '' ) )


@raises( TypeError )
def SecureStringsEqual_ExceptionOnUnicode_test():
  ok_( hu.SecureStringsEqual( u'foo', u'foo' ) )
