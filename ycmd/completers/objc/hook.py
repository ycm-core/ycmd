# Copyright (C) 2011, 2012 Google Inc.
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

import ycm_core
from ycmd.completers.cpp.clang_completer import ClangCompleter
from ycmd.completers.cpp.clangd_completer import ( ShouldEnableClangdCompleter,
                                                   ClangdCompleter )


def GetCompleter( user_options ):
  if ShouldEnableClangdCompleter( user_options ):
    return ClangdCompleter( user_options )
  if ycm_core.HasClangSupport():
    return ClangCompleter( user_options )
  return None
