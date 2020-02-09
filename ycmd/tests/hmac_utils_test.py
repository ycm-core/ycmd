# Copyright (C) 2020 ycmd contributors
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
from hamcrest import raises, assert_that, calling, equal_to
from ycmd import hmac_utils as hu


def CreateHmac_ArgsNotBytes_test():
  assert_that( calling( hu.CreateHmac ).with_args( u'foo', bytes( b'foo' ) ),
               raises( TypeError, '.*content*' ) )
  assert_that( calling( hu.CreateHmac ).with_args( bytes( b'foo' ), u'foo' ),
               raises( TypeError, '.*hmac_secret*' ) )


def CreateHmac_WithBytes_test():
  # Test vectors from Wikipedia (HMAC_SHA256): https://goo.gl/cvX0Tn
  assert_that( hexlify( hu.CreateHmac(
    bytes( b'The quick brown fox jumps over the lazy dog' ),
    bytes( b'key' ) ) ),
    equal_to( bytes( b'f7bc83f430538424b13298e6aa6fb143'
                     b'ef4d59a14946175997479dbc2d1a3cd8' ) ) )


def CreateRequestHmac_ArgsNotBytes_test():
  assert_that(
    calling( hu.CreateRequestHmac ).with_args(
      u'foo', bytes( b'foo' ), bytes( b'foo' ), bytes( b'foo' ) ),
    raises( TypeError, '.*method*' ) )

  assert_that(
    calling( hu.CreateRequestHmac ).with_args(
      bytes( b'foo' ), u'foo', bytes( b'foo' ), bytes( b'foo' ) ),
    raises( TypeError, '.*path*' ) )

  assert_that(
    calling( hu.CreateRequestHmac ).with_args(
      bytes( b'foo' ), bytes( b'foo' ), u'foo', bytes( b'foo' ) ),
    raises( TypeError, '.*body*' ) )

  assert_that(
    calling( hu.CreateRequestHmac ).with_args(
      bytes( b'foo' ), bytes( b'foo' ), bytes( b'foo' ), u'foo' ),
    raises( TypeError, '.*hmac_secret*' ) )


def CreateRequestHmac_WithBytes_test():
  assert_that( hexlify( hu.CreateRequestHmac(
    bytes( b'GET' ),
    bytes( b'/foo' ),
    bytes( b'body' ),
    bytes( b'key' ) ) ),
    equal_to( bytes( b'bfbb6bc7a2b3eca2a78f4e7ec8a7dfa7'
                     b'e58bb8974166eaf20e0224d999894b34' ) ) )
