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

# Intentionally not importing unicode_literals!
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from binascii import hexlify
from nose.tools import eq_, ok_
from hamcrest import raises, assert_that, calling
from ycmd import hmac_utils as hu
from ycmd.tests.test_utils import Py2Only


def CreateHmac_ArgsNotBytes_test():
  assert_that( calling( hu.CreateHmac ).with_args( u'foo', bytes( b'foo' ) ),
               raises( TypeError, '.*content*' ) )
  assert_that( calling( hu.CreateHmac ).with_args( bytes( b'foo' ), u'foo' ),
               raises( TypeError, '.*hmac_secret*' ) )


def CreateHmac_WithBytes_test():
  # Test vectors from Wikipedia (HMAC_SHA256): https://goo.gl/cvX0Tn
  eq_( hexlify( hu.CreateHmac(
    bytes( b'The quick brown fox jumps over the lazy dog' ),
    bytes( b'key' ) ) ),
    bytes( b'f7bc83f430538424b13298e6aa6fb143'
           b'ef4d59a14946175997479dbc2d1a3cd8' ) )


@Py2Only
def CreateHmac_WithPy2Str_test():
  # Test vectors from Wikipedia (HMAC_SHA256): https://goo.gl/cvX0Tn
  eq_( hexlify( hu.CreateHmac(
    'The quick brown fox jumps over the lazy dog',
    'key' ) ),
    'f7bc83f430538424b13298e6aa6fb143'
    'ef4d59a14946175997479dbc2d1a3cd8' )


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
  eq_( hexlify( hu.CreateRequestHmac(
    bytes( b'GET' ),
    bytes( b'/foo' ),
    bytes( b'body' ),
    bytes( b'key' ) ) ),
    bytes( b'bfbb6bc7a2b3eca2a78f4e7ec8a7dfa7'
           b'e58bb8974166eaf20e0224d999894b34' ) )


@Py2Only
def CreateRequestHmac_WithPy2Str_test():
  eq_( hexlify( hu.CreateRequestHmac(
    'GET',
    '/foo',
    'body',
    'key' ) ),
    'bfbb6bc7a2b3eca2a78f4e7ec8a7dfa7'
    'e58bb8974166eaf20e0224d999894b34' )


def SecureBytesEqual_Basic_test():
  ok_( hu.SecureBytesEqual( bytes( b'foo' ), bytes( b'foo' ) ) )
  ok_( not hu.SecureBytesEqual( bytes( b'foo' ), bytes( b'fo' ) ) )
  ok_( not hu.SecureBytesEqual( bytes( b'foo' ), bytes( b'goo' ) ) )


def SecureBytesEqual_Empty_test():
  ok_( hu.SecureBytesEqual( bytes(), bytes() ) )


def SecureBytesEqual_ExceptionOnUnicode_test():
  assert_that( calling( hu.SecureBytesEqual ).with_args( u'foo', u'foo' ),
               raises( TypeError, '.*inputs must be bytes.*' ) )


@Py2Only
def SecureBytesEqual_ExceptionOnPy2Str_test():
  assert_that( calling( hu.SecureBytesEqual ).with_args( 'foo', 'foo' ),
               raises( TypeError, '.*inputs must be bytes.*' ) )
