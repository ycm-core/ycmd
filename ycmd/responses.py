#!/usr/bin/env python
#
# Copyright (C) 2013  Google Inc.
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

import os

YCM_EXTRA_CONF_FILENAME = '.ycm_extra_conf.py'

CONFIRM_CONF_FILE_MESSAGE = ('Found {0}. Load? \n\n(Question can be turned '
                             'off with options, see YCM docs)')

NO_EXTRA_CONF_FILENAME_MESSAGE = ( 'No {0} file detected, so no compile flags '
  'are available. Thus no semantic support for C/C++/ObjC/ObjC++. Go READ THE '
  'DOCS *NOW*, DON\'T file a bug report.' ).format( YCM_EXTRA_CONF_FILENAME )

NO_DIAGNOSTIC_SUPPORT_MESSAGE = ( 'YCM has no diagnostics support for this '
  'filetype; refer to Syntastic docs if using Syntastic.')


class ServerError( Exception ):
  def __init__( self, message ):
    super( ServerError, self ).__init__( message )


class UnknownExtraConf( ServerError ):
  def __init__( self, extra_conf_file ):
    message = CONFIRM_CONF_FILE_MESSAGE.format( extra_conf_file )
    super( UnknownExtraConf, self ).__init__( message )
    self.extra_conf_file = extra_conf_file


class NoExtraConfDetected( ServerError ):
  def __init__( self ):
    super( NoExtraConfDetected, self ).__init__(
      NO_EXTRA_CONF_FILENAME_MESSAGE )


class NoDiagnosticSupport( ServerError ):
  def __init__( self ):
    super( NoDiagnosticSupport, self ).__init__( NO_DIAGNOSTIC_SUPPORT_MESSAGE )


def BuildGoToResponse( filepath, line_num, column_num, description = None ):
  response = {
    'filepath': os.path.realpath( filepath ),
    'line_num': line_num,
    'column_num': column_num
  }

  if description:
    response[ 'description' ] = description
  return response


def BuildDescriptionOnlyGoToResponse( text ):
  return {
    'description': text,
  }


# TODO: Look at all the callers and ensure they are not using this instead of an
# exception.
def BuildDisplayMessageResponse( text ):
  return {
    'message': text
  }


def BuildCompletionPart( part,
                         literal = True ):
  return {
    'part': part,
    'literal': literal,
  }

def BuildSimpleCompletionData ( completion_string,
                                typed_string = None,
                                display_string = None,
                                result_type = None,
                                kind = None,
                                doc_string = None,
                                extra_data = None ):
  return BuildCompletionData(
    completion_parts = [ BuildCompletionPart( completion_string ) ],
    typed_string = typed_string,
    display_string = display_string,
    result_type = result_type,
    kind = kind,
    doc_string = doc_string )


def BuildCompletionData( completion_parts,
                         typed_string = None,
                         display_string = None,
                         result_type = None,
                         kind = None,
                         doc_string = None,
                         extra_data = None ):
  if typed_string == None:
    typed_string = completion_parts[0]['part']
  if display_string == None:
    display_string = ''.join( map( lambda part: part[ 'part' ], completion_parts ) )

  completion_data = {
    'completion_parts': completion_parts,
    'typed_string': typed_string,
    'display_string': display_string,
  }

  if result_type:
    completion_data[ 'result_type' ] = result_type
  if kind:
    completion_data[ 'kind' ] = kind
  if doc_string:
    completion_data[ 'doc_string' ] = doc_string
  if extra_data:
    completion_data[ 'extra_data' ] = extra_data
  return completion_data


def BuildCompletionResponse( completion_datas, start_column ):
  return {
    'completions': completion_datas,
    'completion_start_column': start_column
  }


def BuildDiagnosticData( diagnostic ):
  def BuildRangeData( source_range ):
    return {
      'start': BuildLocationData( source_range.start_ ),
      'end': BuildLocationData( source_range.end_ ),
    }

  def BuildLocationData( location ):
    return {
      'line_num': location.line_number_,
      'column_num': location.column_number_,
      'filepath': location.filename_,
    }

  kind = ( diagnostic.kind_.name if hasattr( diagnostic.kind_, 'name' )
           else diagnostic.kind_ )

  return {
    'ranges': [ BuildRangeData( x ) for x in diagnostic.ranges_ ],
    'location': BuildLocationData( diagnostic.location_ ),
    'location_extent': BuildRangeData( diagnostic.location_extent_ ),
    'text': diagnostic.text_,
    'kind': kind
  }


def BuildExceptionResponse( exception, traceback ):
  return {
    'exception': exception,
    'message': str( exception ),
    'traceback': traceback
  }

