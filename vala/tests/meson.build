# Copyright (C) 2019  Jakub Kaszycki
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

_genf = configure_file(
  copy: true,
  input: 'simple.vala',
  output: 'simple.vala'
)

_test_complete = executable(
  'complete',

  'complete.vala',

  dependencies : ycmvala_dep
)

test(
  'complete',

  _test_complete,

  args     : [ '-k', '--tap' ],
  # 0.50.0
  protocol : 'tap',
  suite    : 'test'
)
