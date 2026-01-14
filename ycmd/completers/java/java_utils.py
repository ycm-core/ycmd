# Copyright (C) 2013-2020 ycmd contributors
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

import os
from urllib.parse import urljoin, urlparse, unquote
from urllib.request import pathname2url, url2pathname
from ..language_server.language_server_protocol import InvalidUriException


def FilePathToUri( file_name ):
  if IsJdtContentUri( file_name ):
    return file_name

  return urljoin( 'file:', pathname2url( file_name ) )


def UriToFilePath( uri ):
  if IsJdtContentUri( uri ):
    return uri

  parsed_uri = urlparse( uri )
  if parsed_uri.scheme != 'file':
    raise InvalidUriException( uri )

  # url2pathname doesn't work as expected when uri.path is percent-encoded and
  # is a windows path for ex:
  # url2pathname('/C%3a/') == 'C:\\C:'
  # whereas
  # url2pathname('/C:/') == 'C:\\'
  # Therefore first unquote pathname.
  pathname = unquote( parsed_uri.path )
  return os.path.abspath( url2pathname( pathname ) )


def IsJdtContentUri( uri ):
  return isinstance( uri, str ) and uri[ : 5 ] == "jdt:/"
