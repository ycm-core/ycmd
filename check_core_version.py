#!/usr/bin/env python

import sys
import os
import ycm_client_support

VERSION_FILENAME = 'EXPECTED_CORE_VERSION'

def DirectoryOfThisScript():
  return os.path.dirname( os.path.abspath( __file__ ) )

def ExpectedCoreVersion():
  return int( open( os.path.join( DirectoryOfThisScript(),
                                  VERSION_FILENAME ) ).read() )

def CompatibleWithCurrentCoreVersion():
  try:
    current_core_version = ycm_client_support.YcmCoreVersion()
  except AttributeError:
    return False
  return ExpectedCoreVersion() == current_core_version

if not CompatibleWithCurrentCoreVersion():
  sys.exit( 2 )
sys.exit( 0 )
