#!/usr/bin/env python
#
# Copyright (C) 2015 ycmd contributors.
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

from .utils import PathToTestFile
from ..handlers_test import Handlers_test


class Cs_Handlers_test( Handlers_test ):

  def setUp( self ):
    super( Cs_Handlers_test, self ).setUp()
    self._app.post_json(
      '/ignore_extra_conf_file',
      { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
