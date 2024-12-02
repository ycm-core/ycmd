# Copyright (C) 2024 ycmd contributors
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

# Portions taken from https://github.com/bottlepy/bottle
# which is MIT licensed and copyrighted by Marcel Hellkamp.

from typing import Callable, Mapping, Tuple, List
import http.client
import json
import sys
import traceback
import urllib.parse


_MEMFILE_MAX = 10 * 1024 * 1024


class RouteNotFound( KeyError ):
  def __str__( self ):
    return super().__str__()


class HTTPError( Exception ):
  def __init__( self, status, body, exception = None, traceback = None ):
    self.status = status
    self.body = body
    self.exception = exception
    self.traceback = traceback


class Response:
  def __init__( self ):
    self.headers : List[ Tuple[ str, str ] ] = []

  def set_header( self, name : str, value : str ) -> None:
    self.headers.append( ( name, value ) )


def _FixRequestHeaderName( key : str ) -> str:
  key = key.replace( '-', '_' ).upper()
  if key in { 'CONTENT_LENGTH', 'CONTENT_TYPE' }:
    return key
  return 'HTTP_' + key


class Query( dict ):
  def __init__( self, query_str : str ):
    super().__init__( urllib.parse.parse_qs( query_str ) )

  def __getattribute__( self, query_name : str ) -> str:
    # `parse_qs` creates a dictionary whose values are lists
    # >>> urllib.parse.parse_qs('a=b&a=3')
    # {'a': ['b', '3']}
    # >>> urllib.parse.parse_qs('a=b&c=d')
    # {'a': ['b'], 'c': ['d']}
    return super().get( query_name, [ '' ] )[ 0 ]


class RequestHeaders( dict ):
  def __contains__( self, key : str ) -> bool:
    key = _FixRequestHeaderName( key )
    return super().__contains__( key )

  def __getitem__( self, key : str ) -> str:
    key = _FixRequestHeaderName( key )
    return super().__getitem__( key )


class Request:
  def __init__( self, env : dict ) -> str:
    self.env : dict = env
    self.headers = RequestHeaders( env )
    self.content_length = int( env.get( 'CONTENT_LENGTH' ) or 0 )
    self.body : bytes = env[ 'wsgi.input' ].read( int( self.content_length ) )
    self.method : str = env[ 'REQUEST_METHOD' ]
    self.path : str = env[ 'PATH_INFO' ]

  @property
  def query( self ) -> Query:
    return Query( self.env[ 'QUERY_STRING' ] )

  @property
  def json( self ):
    return json.loads( self.body )


CallbackType = Callable[ [ Request, Response ], str ]
CallbackDecoratorType = Callable[ [ CallbackType ], CallbackType ]
PluginType = Callable[ [ CallbackType ], CallbackType ]


def _ApplyPlugins( plugins : List[ PluginType ],
                   callback : CallbackType ) -> CallbackType:
  """ The __call__ operator of a plugin needs to return a callback
  decorator. The returned decorator has to take thte same arguments
  as the callback and return a str, just like a "naked" callback.
  The result of this function is a transformed callback, calling which
  actually invokes all of the decorators, finishing with the actual callback.
  """
  for plugin in reversed( plugins ):
    callback = plugin( callback )
  return callback


class AppProducer:
  """ Implements a WSGI application, mostly according to PEP 3333.
  Some corners were cut to implement just the parts that ycmd needs.
  Current limitations:
    - Only handles POST and GET requests.
    - Complete disregard for RFCs, even the ones mentioned in PEP 3333.
    - Error handling is limited.
  """
  def __init__( self ):
    self.plugins : List[ PluginType ] = []
    self._get_routes : Mapping[ str, CallbackType ] = {}
    self._post_routes : Mapping[ str, CallbackType ] = {}
    self._original_routes : Tuple[ str, str, CallbackType ] = []

  def _ErrorHandler( self, http_error : HTTPError, response : Response ): # noqa
    raise RuntimeError( "Should be replaced by application." )

  def SetErrorHandler(
      self,
      error_handler : Callable[ [ HTTPError, Response ], str ] ) -> None:
    """ The provided error_handler needs to satisfy the following:
    - Must not throw exceptions.
    - Must return a utf-8 string.
    - Must set Content-Type header.
    """
    self._ErrorHandler = error_handler

  def post( self, path : str ) -> CallbackDecoratorType:
    """ Convenience decorator factory for
    turning callables into POST callbacks.
    The callback should take two arguments:
    - request, of type Request
    - response, of type Response
    """
    return self._AddRouteDecorator( path, 'POST' )

  def get( self, path : str ) -> CallbackDecoratorType:
    """ Convenience decorator factory for
    turning callables into GET callbacks.
    The callback should take two arguments:
    - request, of type Request
    - response, of type Response
    """
    return self._AddRouteDecorator( path, 'GET' )

  def _AddRouteDecorator( self,
                          path : str,
                          method : str ) -> CallbackDecoratorType:
    def Decorator( Callback : CallbackType ):
      self._AddPath( path, method, Callback )
      return Callback
    return Decorator

  def _RecalculateRoute( self, path, method, callback : CallbackType ) -> None:
    callback = _ApplyPlugins( self.plugins, callback )
    if method == 'GET':
      self._get_routes[ path ] = callback
    else:
      self._post_routes[ path ] = callback

  def _RecalculateAllRoutes( self ) -> None:
    for route in self._original_routes:
      self._RecalculateRoute( *route )

  def _AddPath( self,
                path : str,
                method : str,
                callback : CallbackType ) -> None:
    self._original_routes.append( ( path, method, callback ) )
    self._RecalculateRoute( path, method, callback )

  def install( self, plugin : PluginType ) -> None:
    """ Installs Bottle-like plugins. Bottle plugin API:
    http://bottlepy.org/docs/dev/plugindev.html
    Currently on __call__ is handled.
    """
    self.plugins.append( plugin )
    self._RecalculateAllRoutes()

  def __call__( self, environ, start_response ) -> List[ bytes ]:
    status = '200 OK'
    request = Request( environ )
    response = Response()
    try:
      if int( environ.get( 'CONTENT_LENGTH' ) or '0' ) > _MEMFILE_MAX:
        raise HTTPError( 413, 'Request too large' )
      try:
        if request.method == 'GET':
          callback = self._get_routes[ request.path ]
        else:
          callback = self._post_routes[ request.path ]
      except KeyError as e:
        raise RouteNotFound( e.args[ 0 ] )
      else:
        out = callback( request, response )
    except HTTPError as e:
      status = f'{ e.status } { e.body }'
      response = Response()
      out = self._ErrorHandler( e, response )
    except Exception:
      e = HTTPError( 500,
                     http.client.responses[ 500 ],
                     sys.exc_info()[ 1 ],
                     traceback.format_exc() )
      status = '500 ' + e.body
      response = Response()
      out = self._ErrorHandler( e, response )
    out = out.encode( 'utf-8' )
    response.set_header( 'Content-Length', str( len( out ) ) )
    start_response( status, response.headers )
    return [ out ]


def abort( code : int, text : str ):
  """ abort() lets plugins easily abort a response, providing an HTTP status
  code and reason as arguments. """
  raise HTTPError( code, text )
