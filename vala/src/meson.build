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

ycmvala_lib = shared_library (
  'ycmvala',

  'Candidate.vala',
  'CandidateKind.vala',
  'CandidateTrie.vala',
  'Completer.vala',
  'CompleterError.vala',
  'Diagnostic.vala',
  'DiagnosticKind.vala',
  'Documentation.vala',
  'Fix.vala',
  'FixChunk.vala',
  'Flags.vala',
  'Location.vala',
  'Range.vala',
  'TranslationUnit.vala',
  'util.vala',
  'version.vala',

  dependencies : [ vala_dep ],
  install      : false,
  soversion    : 0,
  vala_args    : [ '--enable-experimental',
                   '--enable-experimental-non-null',
                   '--target-glib=2.60' ],
  vala_gir     : 'Ycmvala-0.gir'
)

path = ycmvala_lib.full_path()
path = path.split( '/' )[ -1 ]

g_ir_compiler = find_program( 'g-ir-compiler' )

custom_target( 'Ycmvala-0.typelib',
               command          : [ g_ir_compiler,
                                    '--output=@OUTPUT@',
                                    '--shared-library=' + path,
                                    '@INPUT@' ],
               depends          : ycmvala_lib,
               input            : join_paths( meson.current_build_dir(), 'Ycmvala-0.gir' ),
               install          : false,
               output           : 'Ycmvala-0.typelib' )

# Used only by tests and benchmarks
ycmvala_dep = declare_dependency(
  dependencies        : [ vala_dep ],
  include_directories : include_directories( '.' ),
  link_with           : ycmvala_lib
)
