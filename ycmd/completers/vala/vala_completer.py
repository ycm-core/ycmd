# Copyright (C) 2011-2012 Google Inc.
#               2017      ycmd contributors
#               2019      Jakub Kaszycki
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

from future.utils import iteritems
import logging

from ycmd import responses
from ycmd.utils import ToBytes, ToUnicode
from ycmd.completers.completer import Completer
from ycmd.completers.vala.flags import Flags
from ycmd.completers.cpp.ephemeral_values_set import EphemeralValuesSet
from ycmd.responses import NoExtraConfDetected, UnknownExtraConf

from ycmd.completers.vala.native import GLib, Ycmvala

VALA_FILETYPES = set( [ 'genie', 'vala' ] )
PARSING_FILE_MESSAGE = 'Still parsing file, no completions yet.'
NO_COMPILE_FLAGS_MESSAGE = 'Still no compile flags, no completions yet.'
INVALID_FILE_MESSAGE = 'File is invalid.'
NO_COMPLETIONS_MESSAGE = 'No completions found; errors in the file?'
NO_DIAGNOSTIC_MESSAGE = 'No diagnostic for current line!'
NO_DOCUMENTATION_MESSAGE = 'No documentation available for current context'


class ValaCompleter( Completer ):
  def __init__( self, user_options ):
    super( ValaCompleter, self ).__init__( user_options )
    self._max_diagnostics_to_display \
      = user_options[ 'max_diagnostics_to_display' ]
    self._completer = Ycmvala.Completer()
    self._flags = Flags()
    self._files_being_compiled = EphemeralValuesSet()
    self._logger = logging.getLogger( __name__ )


  def SupportedFiletypes( self ):
    return VALA_FILETYPES


  def GetUnsavedFiles( self, request_data ):
    files = {}
    for filename, file_data in iteritems( request_data[ 'file_data' ] ):
      if not self.ValaAvailableForFiletypes( file_data[ 'filetypes' ] ):
        continue
      contents = file_data[ 'contents' ]

      if not contents or not filename:
        continue

      files[filename] = GLib.Bytes.new( ToBytes( contents ) )

    return files


  def BuildLocationData( self, location ):
    return {
      'line_num': location.get_line(),
      'column_num': location.get_column(),
      'filepath': location.get_file() or ''
    }


  def BuildRangeData( self, source_range ):
    return {
      'start': self.BuildLocationData( source_range.get_begin() ),
      'end': self.BuildLocationData( source_range.get_end() )
    }


  def BuildDiagnosticData( self, diagnostic ):
    range = diagnostic.get_range()
    loc = range.get_begin()
    range_data = self.BuildRangeData( range )
    return {
      'ranges': [ range_data ],
      'location': self.BuildLocationData( loc ),
      'location_extent': range_data,
      'text': diagnostic.get_message(),
      'kind': Ycmvala.diagnostic_kind_to_string( diagnostic.get_kind() ),
      'fixit_available': diagnostic.get_can_fix()
    }


  def BuildFixitChunkData( self, chunk ):
    return {
      'replacement_text': chunk.replacement_text,
      'range': self.BuildRangeData( chunk.get_range() ),
    }


  def BuildFixItData( self, fixit ):
    return {
      'location': self.BuildLocationData( fixit.get_location() ),
      'chunks' : [ self.BuildFixitChunkData( x ) for x in fixit.get_chunks() ],
      'text': fixit.get_text(),
    }


  def BuildFixItResponse( self, fixits ):
    """Build a response from a list of FixIt (aka Refactor) objects. This
    response can be used to apply arbitrary changes to arbitrary files and is
    suitable for both quick fix and refactor operations"""

    return {
      'fixits' : [ self.BuildFixItData( x ) for x in fixits ]
    }


  def GetCachedTranslationUnit( self, filename ):
    return self._completer.get_cached_translation_unit( filename )


  def GetTranslationUnit( self, filename, files, flags ):
    result, created = self._completer.get_translation_unit( filename,
                                                            files,
                                                            flags )

    if created:
      # If in the future there is a need to do something once, do it right here
      pass

    return result


  def ComputeCandidatesInner( self, request_data ):
    filename = request_data[ 'filepath' ]
    if not filename:
      return

    files = self.GetUnsavedFiles( request_data )

    flags = self._FlagsForRequest( request_data )
    if flags is None:
      raise ValueError( NO_COMPILE_FLAGS_MESSAGE )

    tu = self.GetTranslationUnit( filename,
                                  files,
                                  flags )

    if tu.updating():
      raise RuntimeError( PARSING_FILE_MESSAGE )

    line = request_data[ 'line_num' ]
    column = request_data[ 'start_column' ]
    with self._files_being_compiled.GetExclusive( filename ):
      results = tu.complete( line, column, files, reparse = True )

    if not results:
      raise RuntimeError( NO_COMPLETIONS_MESSAGE )

    return [ self.ConvertCompletionData( x ) for x in results ]


  def GetSubcommandsMap( self ):
    return {
      'GoTo'                     : ( lambda self, request_data, args:
         self._GoTo( request_data ) ),
      'GoToImprecise'            : ( lambda self, request_data, args:
         self._GoTo( request_data,
                     reparse = False ) ),
      'ClearCompilationFlagCache': ( lambda self, request_data, args:
         self._ClearCompilationFlagCache() ),
      'GetParent'                : ( lambda self, request_data, args:
         self._GetParent( request_data, reparse = True ) ),
      'GetParentImprecise'       : ( lambda self, request_data, args:
         self._GetParent( request_data, reparse = False ) ),
      'GetType'                  : ( lambda self, request_data, args:
         self._GetType( request_data, reparse = True, debug = False ) ),
      'GetTypeImprecise'         : ( lambda self, request_data, args:
         self._GetType( request_data, reparse = False, debug = False ) ),
      'GoToParent'               : ( lambda self, request_data, args:
         self._GoToParent( request_data, reparse = True ) ),
      'GoToParentImprecise'      : ( lambda self, request_data, args:
         self._GoToParent( request_data, reparse = False ) ),
      'FixIt'                    : ( lambda self, request_data, args:
         self._FixIt( request_data, reparse = True ) ),
      'FixItImprecise'           : ( lambda self, request_data, args:
         self._FixIt( request_data, reparse = False ) ),
      'GetDoc'                   : ( lambda self, request_data, args:
         self._GetDocumentation( request_data, reparse = True ) ),
      'GetDocImprecise'          : ( lambda self, request_data, args:
         self._GetDocumentation( request_data, reparse = False ) ),
      'DebugGetNode'             : ( lambda self, request_data, args:
         self._DebugGetNode( request_data, reparse = True ) ),
      'DebugGetNodeImprecise'    : ( lambda self, request_data, args:
         self._DebugGetNode( request_data, reparse = False ) ),
      'DebugGetType'             : ( lambda self, request_data, args:
         self._GetType( request_data, reparse = True, debug = True ) ),
      'DebugGetTypeImprecise'    : ( lambda self, request_data, args:
         self._GetType( request_data, reparse = False, debug = True ) ),
    }


  def _GoTo( self, request_data, reparse = True ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    flags = self._FlagsForRequest( request_data )
    if flags is None:
      raise ValueError( NO_COMPILE_FLAGS_MESSAGE )

    files = self.GetUnsavedFiles( request_data )
    line = request_data[ 'line_num' ]
    column = request_data[ 'column_num' ]

    tu = self.GetTranslationUnit( filename,
                                  files,
                                  flags )

    location = tu.go_to( line,
                         column,
                         files,
                         reparse )

    if not location or not location.valid():
      raise RuntimeError( 'Can\'t jump to declaration.' )

    return self._ResponseGoTo( location )


  def _GoToParent( self, request_data, reparse = True ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    flags = self._FlagsForRequest( request_data )
    if flags is None:
      raise ValueError( NO_COMPILE_FLAGS_MESSAGE )

    files = self.GetUnsavedFiles( request_data )
    line = request_data[ 'line_num' ]
    column = request_data[ 'column_num' ]

    tu = self.GetTranslationUnit( filename,
                                  files,
                                  flags )

    location = tu.go_to_parent( line,
                                column,
                                files,
                                reparse )

    if not location or not location.valid():
      raise RuntimeError( 'Can\'t jump to parent.' )

    return self._ResponseGoTo( location )


  def _GetParent( self, request_data, reparse = True ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    flags = self._FlagsForRequest( request_data )
    if flags is None:
      raise ValueError( NO_COMPILE_FLAGS_MESSAGE )

    files = self.GetUnsavedFiles( request_data )
    line = request_data[ 'line_num' ]
    column = request_data[ 'column_num' ]

    tu = self.GetTranslationUnit( filename,
                                  files,
                                  flags )

    name = tu.get_parent( line,
                          column,
                          files,
                          reparse )

    if not name:
      raise RuntimeError( 'Can\'t get parent.' )

    return responses.BuildDisplayMessageResponse( name )


  def _GetType( self, request_data, reparse = True, debug = False ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    flags = self._FlagsForRequest( request_data )
    if flags is None:
      raise ValueError( NO_COMPILE_FLAGS_MESSAGE )

    files = self.GetUnsavedFiles( request_data )
    line = request_data[ 'line_num' ]
    column = request_data[ 'column_num' ]

    tu = self.GetTranslationUnit( filename,
                                  files,
                                  flags )

    name = tu.get_expr_type( line,
                             column,
                             files,
                             reparse,
                             debug )

    if not name:
      raise RuntimeError( 'Can\'t get type.' )

    return responses.BuildDisplayMessageResponse( name )


  def _GetDocumentation( self,
                         request_data,
                         reparse = True ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    flags = self._FlagsForRequest( request_data )
    if flags is None:
      raise ValueError( NO_COMPILE_FLAGS_MESSAGE )

    files = self.GetUnsavedFiles( request_data )
    line = request_data[ 'line_num' ]
    column = request_data[ 'column_num' ]

    tu = self.GetTranslationUnit( filename, files, flags )

    return self._BuildGetDocResponse( tu.get_documentation( line,
                                                            column,
                                                            files,
                                                            reparse ) )

  def _DebugGetNode( self,
                     request_data,
                     reparse = True ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    flags = self._FlagsForRequest( request_data )
    if flags is None:
      raise ValueError( NO_COMPILE_FLAGS_MESSAGE )

    files = self.GetUnsavedFiles( request_data )
    line = request_data[ 'line_num' ]
    column = request_data[ 'column_num' ]

    tu = self.GetTranslationUnit( filename, files, flags )

    return responses.BuildDetailedInfoResponse( tu.debug_get_node( line,
                                                                   column,
                                                                   files,
                                                                   reparse ) )


  def _ClearCompilationFlagCache( self ):
    self._flags.Clear()


  def _FixIt( self, request_data, reparse = True ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    flags = self._FlagsForRequest( request_data )
    if flags is None:
      raise ValueError( NO_COMPILE_FLAGS_MESSAGE )

    files = self.GetUnsavedFiles( request_data )
    line = request_data[ 'line_num' ]
    column = request_data[ 'column_num' ]

    tu = self.GetTranslationUnit( filename, files, flags )

    fixits = tu.fix( line,
                     column,
                     files,
                     reparse )

    # don't raise an error if not fixits: - leave that to the client to respond
    # in a nice way

    return self.BuildFixItResponse( fixits )


  def OnFileReadyToParse( self, request_data ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    flags = self._FlagsForRequest( request_data )
    if flags is None:
      raise ValueError( NO_COMPILE_FLAGS_MESSAGE )

    files = self.GetUnsavedFiles( request_data )


    tu = self.GetTranslationUnit( filename,
                                  files,
                                  flags )

    with self._files_being_compiled.GetExclusive( filename ):
      tu.reparse( self.GetUnsavedFiles( request_data ) )

    return [ self.BuildDiagnosticData( x )
      for x in tu.get_diagnostics( self._max_diagnostics_to_display ) ]


  def OnBufferUnload( self, request_data ):
    self._completer.delete_translation_unit( request_data[ 'filepath' ] )


  def GetDetailedDiagnostic( self, request_data ):
    current_line = request_data[ 'line_num' ]
    current_column = request_data[ 'column_num' ]
    current_file = request_data[ 'filepath' ]
    loc = Ycmvala.Location.new( current_file, current_line, current_column )

    tu = self.GetCachedTranslationUnit( current_file )

    if not tu:
      raise ValueError( NO_DIAGNOSTIC_MESSAGE )

    diagnostic = tu.get_closest_diagnostic( loc )

    if not diagnostic:
      raise ValueError( NO_DIAGNOSTIC_MESSAGE )

    return responses.BuildDisplayMessageResponse( diagnostic.get_message() )


  def DebugInfo( self, request_data ):
    try:
      # Note that it only raises NoExtraConfDetected:
      #  - when extra_conf is None and,
      #  - there is no compilation database
      flags = self._FlagsForRequest( request_data ) or []
    except ( NoExtraConfDetected, UnknownExtraConf ):
      # If _FlagsForRequest returns None or raises, we use an empty list in
      # practice.
      flags = []

    flags_item = responses.DebugInfoItem(
      key = 'flags', value = '{0}'.format( flags ) )

    return responses.BuildDebugInfoResponse( name = 'Vala',
                                             items = [ flags_item ] )


  def _FlagsForRequest( self, request_data ):
    filename = request_data[ 'filepath' ]
    if 'compilation_flags' in request_data:
      return request_data[ 'compilation_flags' ]
    client_data = request_data.get( 'extra_conf_data', None )
    return self._flags.FlagsForFile( filename, client_data = client_data )


  def _BuildGetDocResponse( self, documentation ):
    """Builds a "DetailedInfoResponse" for a GetDoc request. documentation is a
    Documentation object returned from the Vala completer"""

    if not documentation:
      raise ValueError( NO_DOCUMENTATION_MESSAGE )

    return responses.BuildDetailedInfoResponse(
      '{0}\n{1}\nType: {2}\nName: {3}\n---\n{4}'.format(
        ToUnicode( documentation.get_text() ),
        ToUnicode( documentation.get_brief_description() ),
        ToUnicode( documentation.get_type_name() ),
        ToUnicode( documentation.get_display_name() ),
        ToUnicode( documentation.get_long_description() )
      ) )


  def ConvertCompletionData( self, candidate ):
    doc = candidate.get_documentation()
    return responses.BuildCompletionData(
      insertion_text = candidate.get_insertion_text(),
      menu_text = candidate.get_menu_text(),
      extra_menu_info = candidate.get_extra_menu_information(),
      kind = Ycmvala.candidate_kind_to_string( candidate.get_candidate_kind() ),
      detailed_info = candidate.get_detailed_information(),
      extra_data = ( { 'doc_string': doc.get_brief_description() }
        if doc else None ) )


  def ValaAvailableForFiletypes( self, filetypes ):
    return any( [ filetype in VALA_FILETYPES for filetype in filetypes ] )


  def _ResponseGoTo( self, location ):
    return responses.BuildGoToResponse( location.get_file(),
                                        location.get_line(),
                                        location.get_column() )
