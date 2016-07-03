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
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa
from future.utils import iteritems

from collections import defaultdict
import ycm_core
import re
import os.path
import textwrap
from ycmd import responses
from ycmd import extra_conf_store
from ycmd.utils import ToCppStringCompatible, ToUnicode
from ycmd.completers.completer import Completer
from ycmd.completers.completer_utils import GetIncludeStatementValue
from ycmd.completers.cpp.flags import Flags, PrepareFlagsForClang
from ycmd.completers.cpp.ephemeral_values_set import EphemeralValuesSet
from ycmd.responses import NoExtraConfDetected, UnknownExtraConf

import xml.etree.ElementTree

CLANG_FILETYPES = set( [ 'c', 'cpp', 'objc', 'objcpp' ] )
PARSING_FILE_MESSAGE = 'Still parsing file, no completions yet.'
NO_COMPILE_FLAGS_MESSAGE = 'Still no compile flags, no completions yet.'
INVALID_FILE_MESSAGE = 'File is invalid.'
NO_COMPLETIONS_MESSAGE = 'No completions found; errors in the file?'
NO_DIAGNOSTIC_MESSAGE = 'No diagnostic for current line!'
PRAGMA_DIAG_TEXT_TO_IGNORE = '#pragma once in main file'
TOO_MANY_ERRORS_DIAG_TEXT_TO_IGNORE = 'too many errors emitted, stopping now'
NO_DOCUMENTATION_MESSAGE = 'No documentation available for current context'


class ClangCompleter( Completer ):
  def __init__( self, user_options ):
    super( ClangCompleter, self ).__init__( user_options )
    self._max_diagnostics_to_display = user_options[
      'max_diagnostics_to_display' ]
    self._completer = ycm_core.ClangCompleter()
    self._flags = Flags()
    self._diagnostic_store = None
    self._files_being_compiled = EphemeralValuesSet()


  def SupportedFiletypes( self ):
    return CLANG_FILETYPES


  def GetUnsavedFilesVector( self, request_data ):
    files = ycm_core.UnsavedFileVector()
    for filename, file_data in iteritems( request_data[ 'file_data' ] ):
      if not ClangAvailableForFiletypes( file_data[ 'filetypes' ] ):
        continue
      contents = file_data[ 'contents' ]
      if not contents or not filename:
        continue

      unsaved_file = ycm_core.UnsavedFile()
      utf8_contents = ToCppStringCompatible( contents )
      unsaved_file.contents_ = utf8_contents
      unsaved_file.length_ = len( utf8_contents )
      unsaved_file.filename_ = ToCppStringCompatible( filename )

      files.append( unsaved_file )
    return files


  def ComputeCandidatesInner( self, request_data ):
    filename = request_data[ 'filepath' ]
    if not filename:
      return

    if self._completer.UpdatingTranslationUnit(
        ToCppStringCompatible( filename ) ):
      raise RuntimeError( PARSING_FILE_MESSAGE )

    flags = self._FlagsForRequest( request_data )
    if not flags:
      raise RuntimeError( NO_COMPILE_FLAGS_MESSAGE )

    files = self.GetUnsavedFilesVector( request_data )
    line = request_data[ 'line_num' ]
    column = request_data[ 'start_column' ]
    with self._files_being_compiled.GetExclusive( filename ):
      results = self._completer.CandidatesForLocationInFile(
          ToCppStringCompatible( filename ),
          line,
          column,
          files,
          flags )

    if not results:
      raise RuntimeError( NO_COMPLETIONS_MESSAGE )

    return [ ConvertCompletionData( x ) for x in results ]


  def GetSubcommandsMap( self ):
    return {
      'GoToDefinition'           : ( lambda self, request_data, args:
         self._GoToDefinition( request_data ) ),
      'GoToDeclaration'          : ( lambda self, request_data, args:
         self._GoToDeclaration( request_data ) ),
      'GoTo'                     : ( lambda self, request_data, args:
         self._GoTo( request_data ) ),
      'GoToImprecise'            : ( lambda self, request_data, args:
         self._GoToImprecise( request_data ) ),
      'GoToInclude'              : ( lambda self, request_data, args:
         self._GoToInclude( request_data ) ),
      'ClearCompilationFlagCache': ( lambda self, request_data, args:
         self._ClearCompilationFlagCache() ),
      'GetType'                  : ( lambda self, request_data, args:
         self._GetSemanticInfo( request_data, func = 'GetTypeAtLocation' ) ),
      'GetParent'                : ( lambda self, request_data, args:
         self._GetSemanticInfo( request_data,
                                func = 'GetEnclosingFunctionAtLocation' ) ),
      'FixIt'                    : ( lambda self, request_data, args:
         self._FixIt( request_data ) ),
      'GetDoc'                   : ( lambda self, request_data, args:
         self._GetSemanticInfo( request_data,
                                reparse = True,
                                func = 'GetDocsForLocationInFile',
                                response_builder = _BuildGetDocResponse ) ),
      'GetDocQuick'              : ( lambda self, request_data, args:
         self._GetSemanticInfo( request_data,
                                reparse = False,
                                func = 'GetDocsForLocationInFile',
                                response_builder = _BuildGetDocResponse ) ),
    }


  def _LocationForGoTo( self, goto_function, request_data, reparse = True ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    flags = self._FlagsForRequest( request_data )
    if not flags:
      raise ValueError( NO_COMPILE_FLAGS_MESSAGE )

    files = self.GetUnsavedFilesVector( request_data )
    line = request_data[ 'line_num' ]
    column = request_data[ 'column_num' ]
    return getattr( self._completer, goto_function )(
        ToCppStringCompatible( filename ),
        line,
        column,
        files,
        flags,
        reparse )


  def _GoToDefinition( self, request_data ):
    location = self._LocationForGoTo( 'GetDefinitionLocation', request_data )
    if not location or not location.IsValid():
      raise RuntimeError( 'Can\'t jump to definition.' )
    return _ResponseForLocation( location )


  def _GoToDeclaration( self, request_data ):
    location = self._LocationForGoTo( 'GetDeclarationLocation', request_data )
    if not location or not location.IsValid():
      raise RuntimeError( 'Can\'t jump to declaration.' )
    return _ResponseForLocation( location )


  def _GoTo( self, request_data ):
    include_response = self._ResponseForInclude( request_data )
    if include_response:
      return include_response

    location = self._LocationForGoTo( 'GetDefinitionLocation', request_data )
    if not location or not location.IsValid():
      location = self._LocationForGoTo( 'GetDeclarationLocation', request_data )
    if not location or not location.IsValid():
      raise RuntimeError( 'Can\'t jump to definition or declaration.' )
    return _ResponseForLocation( location )


  def _GoToImprecise( self, request_data ):
    include_response = self._ResponseForInclude( request_data )
    if include_response:
      return include_response

    location = self._LocationForGoTo( 'GetDefinitionLocation',
                                      request_data,
                                      reparse = False )
    if not location or not location.IsValid():
      location = self._LocationForGoTo( 'GetDeclarationLocation',
                                        request_data,
                                        reparse = False )
    if not location or not location.IsValid():
      raise RuntimeError( 'Can\'t jump to definition or declaration.' )
    return _ResponseForLocation( location )


  def _ResponseForInclude( self, request_data ):
    """Returns response for include file location if cursor is on the
       include statement, None otherwise.
       Throws RuntimeError if cursor is on include statement and corresponding
       include file not found."""
    current_line = request_data[ 'line_value' ]
    include_file_name, quoted_include = GetIncludeStatementValue( current_line )
    if not include_file_name:
      return None

    current_file_path = request_data[ 'filepath' ]
    client_data = request_data.get( 'extra_conf_data', None )
    quoted_include_paths, include_paths = (
            self._flags.UserIncludePaths( current_file_path, client_data ) )
    if quoted_include:
      include_file_path = _GetAbsolutePath( include_file_name,
                                            quoted_include_paths )
      if include_file_path:
        return responses.BuildGoToResponse( include_file_path,
                                            line_num = 1,
                                            column_num = 1 )

    include_file_path = _GetAbsolutePath( include_file_name, include_paths )
    if include_file_path:
      return responses.BuildGoToResponse( include_file_path,
                                          line_num = 1,
                                          column_num = 1 )
    raise RuntimeError( 'Include file not found.' )


  def _GoToInclude( self, request_data ):
    include_response = self._ResponseForInclude( request_data )
    if not include_response:
      raise RuntimeError( 'Not an include/import line.' )
    return include_response


  def _GetSemanticInfo(
      self,
      request_data,
      func,
      response_builder = responses.BuildDisplayMessageResponse,
      reparse = True ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    flags = self._FlagsForRequest( request_data )
    if not flags:
      raise ValueError( NO_COMPILE_FLAGS_MESSAGE )

    files = self.GetUnsavedFilesVector( request_data )
    line = request_data[ 'line_num' ]
    column = request_data[ 'column_num' ]

    message = getattr( self._completer, func )(
        ToCppStringCompatible( filename ),
        line,
        column,
        files,
        flags,
        reparse)

    if not message:
      message = "No semantic information available"

    return response_builder( message )

  def _ClearCompilationFlagCache( self ):
    self._flags.Clear()

  def _FixIt( self, request_data ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    flags = self._FlagsForRequest( request_data )
    if not flags:
      raise ValueError( NO_COMPILE_FLAGS_MESSAGE )

    files = self.GetUnsavedFilesVector( request_data )
    line = request_data[ 'line_num' ]
    column = request_data[ 'column_num' ]

    fixits = getattr( self._completer, "GetFixItsForLocationInFile" )(
        ToCppStringCompatible( filename ),
        line,
        column,
        files,
        flags,
        True )

    # don't raise an error if not fixits: - leave that to the client to respond
    # in a nice way

    return responses.BuildFixItResponse( fixits )

  def OnFileReadyToParse( self, request_data ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    flags = self._FlagsForRequest( request_data )
    if not flags:
      raise ValueError( NO_COMPILE_FLAGS_MESSAGE )

    with self._files_being_compiled.GetExclusive( filename ):
      diagnostics = self._completer.UpdateTranslationUnit(
        ToCppStringCompatible( filename ),
        self.GetUnsavedFilesVector( request_data ),
        flags )

    diagnostics = _FilterDiagnostics( diagnostics )
    self._diagnostic_store = DiagnosticsToDiagStructure( diagnostics )
    return [ responses.BuildDiagnosticData( x ) for x in
             diagnostics[ : self._max_diagnostics_to_display ] ]


  def OnBufferUnload( self, request_data ):
    self._completer.DeleteCachesForFile(
        ToCppStringCompatible( request_data[ 'unloaded_buffer' ] ) )


  def GetDetailedDiagnostic( self, request_data ):
    current_line = request_data[ 'line_num' ]
    current_column = request_data[ 'column_num' ]
    current_file = request_data[ 'filepath' ]

    if not self._diagnostic_store:
      raise ValueError( NO_DIAGNOSTIC_MESSAGE )

    diagnostics = self._diagnostic_store[ current_file ][ current_line ]
    if not diagnostics:
      raise ValueError( NO_DIAGNOSTIC_MESSAGE )

    closest_diagnostic = None
    distance_to_closest_diagnostic = 999

    # FIXME: all of these calculations are currently working with byte
    # offsets, which are technically incorrect. We should be working with
    # codepoint offsets, as we want the nearest character-wise diagnostic
    for diagnostic in diagnostics:
      distance = abs( current_column - diagnostic.location_.column_number_ )
      if distance < distance_to_closest_diagnostic:
        distance_to_closest_diagnostic = distance
        closest_diagnostic = diagnostic

    return responses.BuildDisplayMessageResponse(
      closest_diagnostic.long_formatted_text_ )


  def DebugInfo( self, request_data ):
    filename = request_data[ 'filepath' ]
    try:
      extra_conf = extra_conf_store.ModuleFileForSourceFile( filename )
      flags = self._FlagsForRequest( request_data ) or []
    except NoExtraConfDetected:
      return ( 'C-family completer debug information:\n'
               '  No configuration file found' )
    except UnknownExtraConf as error:
      return ( 'C-family completer debug information:\n'
               '  Configuration file found but not loaded\n'
               '  Configuration path: {0}'.format(
                 error.extra_conf_file ) )
    if not extra_conf:
      return ( 'C-family completer debug information:\n'
               '  No configuration file found' )
    return ( 'C-family completer debug information:\n'
             '  Configuration file found and loaded\n'
             '  Configuration path: {0}\n'
             '  Flags: {1}'.format( extra_conf, list( flags ) ) )


  def _FlagsForRequest( self, request_data ):
    filename = request_data[ 'filepath' ]
    if 'compilation_flags' in request_data:
      return PrepareFlagsForClang( request_data[ 'compilation_flags' ],
                                   filename )
    client_data = request_data.get( 'extra_conf_data', None )
    return self._flags.FlagsForFile( filename, client_data = client_data )


def ConvertCompletionData( completion_data ):
  return responses.BuildCompletionData(
    insertion_text = completion_data.TextToInsertInBuffer(),
    menu_text = completion_data.MainCompletionText(),
    extra_menu_info = completion_data.ExtraMenuInfo(),
    kind = completion_data.kind_.name,
    detailed_info = completion_data.DetailedInfoForPreviewWindow(),
    extra_data = ( { 'doc_string': completion_data.DocString() }
                   if completion_data.DocString() else None ) )


def DiagnosticsToDiagStructure( diagnostics ):
  structure = defaultdict( lambda : defaultdict( list ) )
  for diagnostic in diagnostics:
    structure[ diagnostic.location_.filename_ ][
      diagnostic.location_.line_number_ ].append( diagnostic )
  return structure


def ClangAvailableForFiletypes( filetypes ):
  return any( [ filetype in CLANG_FILETYPES for filetype in filetypes ] )


def InCFamilyFile( filetypes ):
  return ClangAvailableForFiletypes( filetypes )


def _FilterDiagnostics( diagnostics ):
  # Clang has an annoying warning that shows up when we try to compile header
  # files if the header has "#pragma once" inside it. The error is not
  # legitimate because it shows up because libclang thinks we are compiling a
  # source file instead of a header file.
  #
  # See our issue #216 and upstream bug:
  #   http://llvm.org/bugs/show_bug.cgi?id=16686
  #
  # The second thing we want to filter out are those incredibly annoying "too
  # many errors emitted" diagnostics that are utterly useless.
  return [ x for x in diagnostics if
           x.text_ != PRAGMA_DIAG_TEXT_TO_IGNORE and
           x.text_ != TOO_MANY_ERRORS_DIAG_TEXT_TO_IGNORE ]


def _ResponseForLocation( location ):
  return responses.BuildGoToResponse( location.filename_,
                                      location.line_number_,
                                      location.column_number_ )


# Strips the following leading strings from the raw comment:
# - <whitespace>///
# - <whitespace>///<
# - <whitespace>//<
# - <whitespace>//!
# - <whitespace>/**
# - <whitespace>/*!
# - <whitespace>/*<
# - <whitespace>/*
# - <whitespace>*
# - <whitespace>*/
# - etc.
# That is:
#  - 2 or 3 '/' followed by '<' or '!'
#  - '/' then 1 or 2 '*' followed by optional '<' or '!'
#  - '*' followed by optional '/'
STRIP_LEADING_COMMENT = re.compile( '^[ \t]*(/{2,3}[<!]?|/\*{1,2}[<!]?|\*/?)' )

# And the following trailing strings
# - <whitespace>*/
# - <whitespace>
STRIP_TRAILING_COMMENT = re.compile( '[ \t]*\*/[ \t]*$|[ \t]*$' )


def _FormatRawComment( comment ):
  """Strips leading indentation and comment markers from the comment string"""
  return textwrap.dedent(
    '\n'.join( [ re.sub( STRIP_TRAILING_COMMENT, '',
                 re.sub( STRIP_LEADING_COMMENT, '', line ) )
                 for line in ToUnicode( comment ).splitlines() ] ) )


def _BuildGetDocResponse( doc_data ):
  """Builds a "DetailedInfoResponse" for a GetDoc request. doc_data is a
  DocumentationData object returned from the ClangCompleter"""

  # Parse the XML, as this is the only way to get the declaration text out of
  # libclang. It seems quite wasteful, but while the contents of the XML
  # provide fully parsed doxygen documentation tree, we actually don't want to
  # ever lose any information from the comment, so we just want display
  # the stripped comment. Arguably we could skip all of this XML generation and
  # parsing, but having the raw declaration text is likely one of the most
  # useful pieces of documentation available to the developer. Perhaps in
  # future, we can use this XML for more interesting things.
  try:
    root = xml.etree.ElementTree.fromstring( doc_data.comment_xml )
  except:
    raise ValueError( NO_DOCUMENTATION_MESSAGE )

  # Note: declaration is False-y if it has no child elements, hence the below
  # (wordy) if not declaration is None
  declaration = root.find( "Declaration" )

  return responses.BuildDetailedInfoResponse(
    '{0}\n{1}\nType: {2}\nName: {3}\n---\n{4}'.format(
      ToUnicode( declaration.text ) if declaration is not None else "",
      ToUnicode( doc_data.brief_comment ),
      ToUnicode( doc_data.canonical_type ),
      ToUnicode( doc_data.display_name ),
      ToUnicode( _FormatRawComment( doc_data.raw_comment ) ) ) )


def _GetAbsolutePath( include_file_name, include_paths ):
  for path in include_paths:
    include_file_path = os.path.join( path, include_file_name )
    if os.path.isfile( include_file_path ):
      return include_file_path
  return None
