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

project( 'ycmvala',
         'c', 'vala' )

# libvala loads glib and everything
vala_dep = dependency( 'libvala-' + get_option( 'libvala_api_version' ),
                       version: '>= 0.44' )

subdir( 'src' )
subdir( 'tests' )
subdir( 'benchmarks' )
