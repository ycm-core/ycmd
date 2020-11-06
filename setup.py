import setuptools
from distutils.core import Extension
import pathlib
import os

with open( 'CORE_VERSION' ) as version:
  YCMD_CORE_VERSION = version.read().rstrip()

ycm_core = Extension(
  'ycm_core',
  sources = [
      str( p ) for p in pathlib.Path( 'cpp/ycm' ).glob( '*.cpp' )
  ],
  define_macros = [
    ( 'YCMD_CORE_VERSION', YCMD_CORE_VERSION ),
    ( 'YCM_EXPORT', '' ),
    # TODO: YCM_EXPORT
    # TODO: /DUNICODE /MP /bigobj /utf-8
  ],
  extra_compile_args = [ '-std=c++17' ],
  include_dirs = [ 'cpp/pybind11' ],
  language = 'c++'
)


def GetDirContents( data_files: list, root: pathlib.Path ):
  files = []
  for f in root.iterdir():
    if f.is_dir():
      GetDirContents( data_files, f )
    else:
      files.append( str( f ) )

  rel_path = os.path.relpath( str( root ) )
  data_files.append( ( os.path.join( 'ycmd', rel_path ), files ) )
  return data_files


setuptools.setup(
  # project_urls = { TODO
  #   'Documentation': 'https://packaging.python.org/tutorials/distributing-packages/',
  #   'Funding': 'https://donate.pypi.org',
  #   'Say Thanks!': 'http://saythanks.io/to/example',
  #   'Source': 'https://github.com/pypa/sampleproject/',
  #   'Tracker': 'https://github.com/pypa/sampleproject/issues',
  # },
  # classifiers = [], TODO
  # keywords = [], TODO

  data_files = [
    ( 'ycmd', [ 'CORE_VERSION' ] ),
  ] + GetDirContents( [], pathlib.Path( 'third_party/clang/lib' ) ),
  ext_modules = [ ycm_core ]
)
