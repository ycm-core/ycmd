# Copyright (C) 2013-2018 ycmd contributors.
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

import os
import glob
from inspect import getfile
from ycmd import extra_conf_store
from ycmd.utils import LOGGER


def FindSolutionPath( filepath ):
  """Try to find suitable solution file given a source file path using all
     available information sources"""
  # try to load ycm_extra_conf
  # if it needs to be verified, abort here and try again later
  module = extra_conf_store.ModuleForSourceFile( filepath )
  path_to_solutionfile = PollModule( module, filepath )

  if not path_to_solutionfile:
    # ycm_extra_conf not available or did not provide a solution file
    path_to_solutionfile = GuessFile( filepath )

  return path_to_solutionfile


def PollModule( module, filepath ):
  """ Try to use passed module in the selection process by calling
  CSharpSolutionFile on it """
  path_to_solutionfile = None
  module_hint = None
  if module:
    try:
      module_hint = module.CSharpSolutionFile( filepath )
      LOGGER.info( 'extra_conf_store suggests %s as solution file',
                   module_hint )
      if module_hint:
        # received a full path or one relative to the config's location?
        candidates = [ module_hint,
          os.path.join( os.path.dirname( getfile( module ) ),
                        module_hint ) ]
        # try the assumptions
        for path in candidates:
          if os.path.isfile( path ):
            # path seems to point to a solution
            path_to_solutionfile = path
            LOGGER.info( 'Using solution file %s selected by extra_conf_store',
                         path_to_solutionfile )
            break
    except AttributeError:
      # the config script might not provide solution file locations
      LOGGER.exception( 'Could not retrieve solution for %s'
                        'from extra_conf_store', filepath )
  return path_to_solutionfile


def GuessFile( filepath ):
  """ Find solution files by searching upwards in the file tree """
  tokens = _PathComponents( filepath )
  for i in reversed( range( len( tokens ) - 1 ) ):
    path = os.path.join( *tokens[ : i + 1 ] )
    candidates = glob.glob1( path, '*.sln' )
    if len( candidates ) > 0:
      # do the whole procedure only for the first solution file(s) you find
      return _SolutionTestCheckHeuristics( candidates, tokens, i )
  return None


def _SolutionTestCheckHeuristics( candidates, tokens, i ):
  """ Test if one of the candidate files stands out """
  path = os.path.join( *tokens[ : i + 1 ] )
  selection = None
  # if there is just one file here, use that
  if len( candidates ) == 1 :
    selection = os.path.join( path, candidates[ 0 ] )
    LOGGER.info( 'Selected solution file %s as it is the first one found',
                 selection )

  # there is more than one file, try some hints to decide
  # 1. is there a solution named just like the subdirectory with the source?
  if ( not selection and i < len( tokens ) - 1 and
       u'{0}.sln'.format( tokens[ i + 1 ] ) in candidates ):
    selection = os.path.join( path, u'{0}.sln'.format( tokens[ i + 1 ] ) )
    LOGGER.info( 'Selected solution file %s as it matches source subfolder',
                 selection )

  # 2. is there a solution named just like the directory containing the
  # solution?
  if not selection and u'{0}.sln'.format( tokens[ i ] ) in candidates :
    selection = os.path.join( path, u'{0}.sln'.format( tokens[ i ] ) )
    LOGGER.info( 'Selected solution file %s as it matches containing folder',
                 selection )

  if not selection:
    LOGGER.error( 'Could not decide between multiple solution files:\n%s',
                  candidates )

  return selection


def _PathComponents( path ):
  path_components = []
  while True:
    path, folder = os.path.split( path )
    if folder:
      path_components.append( folder )
    else:
      if path:
        path_components.append( path )
      break
  path_components.reverse()
  return path_components
