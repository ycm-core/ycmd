# Copyright (C) 2015 Google Inc.
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

from builtins import bytes

import hmac
import hashlib


def CreateHmac( content, hmac_secret ):
  # Note that py2's str type passes this check (and that's ok)
  if not isinstance( content, bytes ):
    raise TypeError( 'content was not of bytes type; you have a bug!' )
  if not isinstance( hmac_secret, bytes ):
    raise TypeError( 'hmac_secret was not of bytes type; you have a bug!' )

  return bytes( hmac.new( hmac_secret,
                          msg = content,
                          digestmod = hashlib.sha256 ).digest() )


def CreateRequestHmac( method, path, body, hmac_secret ):
  # Note that py2's str type passes this check (and that's ok)
  if not isinstance( body, bytes ):
    raise TypeError( 'body was not of bytes type; you have a bug!' )
  if not isinstance( hmac_secret, bytes ):
    raise TypeError( 'hmac_secret was not of bytes type; you have a bug!' )
  if not isinstance( method, bytes ):
    raise TypeError( 'method was not of bytes type; you have a bug!' )
  if not isinstance( path, bytes ):
    raise TypeError( 'path was not of bytes type; you have a bug!' )

  method_hmac = CreateHmac( method, hmac_secret )
  path_hmac = CreateHmac( path, hmac_secret )
  body_hmac = CreateHmac( body, hmac_secret )

  joined_hmac_input = bytes().join( ( method_hmac, path_hmac, body_hmac ) )
  return CreateHmac( joined_hmac_input, hmac_secret )


# This is the compare_digest function from python 3.4
#   http://hg.python.org/cpython/file/460407f35aa9/Lib/hmac.py#l16
def SecureBytesEqual( a, b ):
  """Returns the equivalent of 'a == b', but avoids content based short
  circuiting to reduce the vulnerability to timing attacks."""
  # Consistent timing matters more here than data type flexibility
  # We do NOT want to support py2's str type because iterating over them
  # (below) produces different results.
  if type( a ) != bytes or type( b ) != bytes:
    raise TypeError( "inputs must be bytes instances" )

  # We assume the length of the expected digest is public knowledge,
  # thus this early return isn't leaking anything an attacker wouldn't
  # already know
  if len( a ) != len( b ):
    return False

  # We assume that integers in the bytes range are all cached,
  # thus timing shouldn't vary much due to integer object creation
  result = 0
  for x, y in zip( a, b ):
    result |= x ^ y
  return result == 0
