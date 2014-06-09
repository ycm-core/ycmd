
import os
import glob
import logging
from inspect import getfile
from ycmd import extra_conf_store


__logger = logging.getLogger( __name__ )

def Detect( filepath ):
    """ Try to find suitable solution file given a source file path """
    # try to load ycm_extra_conf
    # if it needs to be verified, abort here and try again later
    module = extra_conf_store.ModuleForSourceFile( filepath )
    path_to_solutionfile, preferred_name = PollModule( module, filepath )

    if not path_to_solutionfile:
      # no solution file provided, try to find one
      path_to_solutionfile = GuessFile( filepath, preferred_name )

    return path_to_solutionfile

def PollModule( module, filepath ):
  """ Try to use passed module in the selection process by calling CSharpSolutionFile on it """
  path_to_solutionfile=None
  preferred_name=None
  if module:
    try:
      preferred_name = module.CSharpSolutionFile( filepath )
      __logger.info( 'extra_conf_store suggests {0} as solution file'.format(
          str( preferred_name ) ) )
      if preferred_name:
        # received a full path or the name of a solution right next to the config?
        candidates = [ preferred_name,
          os.path.join( os.path.dirname( getfile( module ) ),
                        preferred_name ) ]
        # try the assumptions
        for path in candidates:
          if os.path.isfile( path ):
            # path seems to point to a solution
            path_to_solutionfile = path
            __logger.info(
                'Using solution file {0} selected by extra_conf_store'.format(
                path_to_solutionfile) )
            break
        # if no solution file found, use the filename as hint later on
        preferred_name=os.path.basename(preferred_name)
    except AttributeError, e:
      # the config script might not provide solution file locations
      __logger.error(
          'Could not retrieve solution for {0} from extra_conf_store: {1}'.format(
          filepath, str( e )) )
      preferred_name = None
  return path_to_solutionfile, preferred_name

def GuessFile( filepath, preferred_name ):
  """ Find solution files by searching upwards in the file tree """
  tokens = _PathComponents( filepath )
  selection = None
  first_hit = True
  for i in reversed( range( len( tokens ) - 1 ) ):
    path = os.path.join( *tokens[:i + 1] )
    candidates = glob.glob1( path, "*.sln" )
    if len( candidates ) > 0:
      # if a name was provided, try hard to find something matching
      final = _SolutionTestCheckPreferred( path, candidates, preferred_name )
      if final:
        return final
      # do the whole procedure only for the first solution file(s) you find
      if first_hit :
        selection = _SolutionTestCheckHeuristics( candidates, tokens, i )
        # we could not decide and aren't looking for anything specific, giving up
        if not preferred_name:
          return selection
      first_hit = False
  return selection

def _SolutionTestCheckPreferred( path, candidates, preferred_name ):
  """ Check if one of the candidates matches preferred_name hint """
  if preferred_name:
    check = [ c for c in candidates
        if ( preferred_name == c ) ]
    if len( check ) == 1:
      selection = os.path.join( path, check[0] )
      __logger.info(
          'Selected solution file {0} as it matches {1} (from extra_conf_store)'.format(
          selection, preferred_name ) )
      return selection
    elif len( check ) == 2:
      # pick the one ending in sln, can misbehave if there is a file.sln.sln
      selection = os.path.join( path, "%s.sln"%preferred_name )
      __logger.info(
          'Selected solution file {0} as it matches {1} (from extra_conf_store)'.format(
          selection, preferred_name ) )
      return selection

def _SolutionTestCheckHeuristics( candidates, tokens, i ):
  """ Test if one of the candidate files stands out """
  path = os.path.join( *tokens[:i + 1] )
  selection=None
  # if there is just one file here, use that
  if len( candidates ) == 1 :
    selection = os.path.join( path, candidates[0] )
    __logger.info(
        'Selected solution file {0} as it is the first one found'.format(
        selection ) )
  # there is more than one file, try some hints to decide
  # 1. is there a solution named just like the subdirectory with the source?
  if (not selection and i < len( tokens ) - 1 and
      "{0}.sln".format( tokens[i + 1] ) in candidates ):
    selection = os.path.join( path, "{0}.sln".format( tokens[i + 1] ) )
    __logger.info(
        'Selected solution file {0} as it matches source subfolder'.format(
        selection ) )
  # 2. is there a solution named just like the directory containing the solution?
  if not selection and "{0}.sln".format( tokens[i] ) in candidates:
    selection = os.path.join( path, "{0}.sln".format( tokens[i] ) )
    __logger.info(
        'Selected solution file {0} as it matches containing folder'.format(
        selection ) )
  if not selection:
    __logger.error(
        'Could not decide between multiple solution files:\n{0}'.format(
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


