
import os
import glob
import logging
from inspect import getfile
from ycmd import extra_conf_store


__logger = logging.getLogger( __name__ )

def FindSolutionPath( filepath ):
    """ Try to find suitable solution file given a source file path using all available information sources """
    # try to load ycm_extra_conf
    # if it needs to be verified, abort here and try again later
    module = extra_conf_store.ModuleForSourceFile( filepath )
    path_to_solutionfile = PollModule( module, filepath )

    if not path_to_solutionfile:
      # ycm_extra_conf not available or did not provide a solution file
      path_to_solutionfile = GuessFile( filepath )

    return path_to_solutionfile

def PollModule( module, filepath ):
  """ Try to use passed module in the selection process by calling CSharpSolutionFile on it """
  path_to_solutionfile = None
  module_hint = None
  if module:
    try:
      module_hint = module.CSharpSolutionFile( filepath )
      __logger.info( u'extra_conf_store suggests {0} as solution file'.format(
          unicode( module_hint ) ) )
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
            __logger.info(
                u'Using solution file {0} selected by extra_conf_store'.format(
                path_to_solutionfile ) )
            break
    except AttributeError as e:
      # the config script might not provide solution file locations
      __logger.error(
          u'Could not retrieve solution for {0} from extra_conf_store: {1}'.format(
          filepath, unicode( e ) ) )
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
    __logger.info(
        u'Selected solution file {0} as it is the first one found'.format(
        selection ) )
  # there is more than one file, try some hints to decide
  # 1. is there a solution named just like the subdirectory with the source?
  if ( not selection and i < len( tokens ) - 1 and
      u'{0}.sln'.format( tokens[ i + 1 ] ) in candidates ) :
    selection = os.path.join( path, u'{0}.sln'.format( tokens[ i + 1 ] ) )
    __logger.info(
        u'Selected solution file {0} as it matches source subfolder'.format(
        selection ) )
  # 2. is there a solution named just like the directory containing the solution?
  if not selection and u'{0}.sln'.format( tokens[ i ] ) in candidates :
    selection = os.path.join( path, u'{0}.sln'.format( tokens[ i ] ) )
    __logger.info(
        u'Selected solution file {0} as it matches containing folder'.format(
        selection ) )
  if not selection:
    __logger.error(
        u'Could not decide between multiple solution files:\n{0}'.format(
        candidates ) )
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


