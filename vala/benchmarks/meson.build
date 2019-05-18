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

_generate_methods_dep = dependency( 'gio-2.0', native : true )

_generate_methods = executable(
  'generate_methods',

  'generate_methods.vala',

  dependencies: _generate_methods_dep,
  native : true
)

_methodsvala = custom_target(
  'methods*.vala',

  build_by_default : true,
  command          : [ _generate_methods ],
  output           : [ 'methods0.vala', 'methods1.vala', 'methods2.vala', 'methods3.vala' ]
)

_bench_methods = executable(
  'methods',

  'methods.vala',

  dependencies : ycmvala_dep
)

benchmark(
  'methods',

  _bench_methods,

  suite    : 'benchmark'
)
