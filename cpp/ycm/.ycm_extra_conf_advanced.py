#!/usr/bin/python
# This file is NOT licensed under the GPLv3, which is the license for the rest
# of YouCompleteMe.
#
# Here's the license text for this file:
#
# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# For more information, please refer to <http://unlicense.org/>

import os
import ycm_core
import fnmatch
import logging
from pprint import pformat as PF
from pprint import pprint as PP

use_additional_files=True
additional_flag_files=[ '.clang_complete' ]
throw_exceptions = True
base_flags = [ '-xc++' ] #make sure we get c++ completion
fallback_flags = [
    '-Wall',
    '-Wextra',
    '-Werror',
    '-Wno-long-long',
    '-Wno-variadic-macros',
    '-fexceptions',
    '-ferror-limit=10000',
    '-DNDEBUG',
]
source_ext = [ '.cpp', '.cxx', '.cc', '.c', '.m', '.mm' ]
header_ext = [ '.hpp', '.hxx', '.hh', '.h' ]


class FakeInfo(object):
    def __init__(self):
        self.compiler_flags_ = []
        self.include_dirs = []
        self.compiler_flags_end = []
        self.compiler_working_dir_ = None
    def __bool__(self):
        return self.compiler_flags_ != None
    def add_info(self,info):

        if not self.compiler_flags_:
            start=None
            end=None
            self.compiler_working_dir_ = info.compiler_working_dir_
            for item in info.compiler_flags_:
                if item.startswith("-I") and not start:
                    start=True
                elif start:
                    end=True

                if not start:
                    self.compiler_flags_.append(item)
                if not end:
                    self.include_dirs.append(item)
                else:
                    self.compiler_flags_end.append(item)
        else:
            for item in info.compiler_flags_:
                if item.startswith("-I") and item not in self.include_dirs:
                    self.include_dirs += item

    def close(self):
        self.compiler_flags_ += self.include_dirs
        self.compiler_flags_ += self.compiler_flags_end
# class FakeInfo

## finding stuff
def find_closest_path(path, target):
    candidate = os.path.join(path, target)
    if(os.path.isfile(candidate) or os.path.isdir(candidate)):
        logging.info("closest " + target + " at " + candidate)
        return candidate;
    else:
        parent = os.path.dirname(os.path.abspath(path));
        if(parent == path):
            #end recursion
            return None
        return find_closest_path(parent, target)

def flags_for_closest_include(filename):
        flags = []
        include_path = find_closest_path(filename, 'include')
        if include_path:
            logging.info("found include dir")
            flags.append( "-I" + include_path )
        else:
            logging.info("no include dir found")
        return flags

def find_database(filename):
    compilation_db_path = find_closest_path(filename, 'compile_commands.json')
    if not compilation_db_path:
        return None
    compilation_db_dir = os.path.dirname(compilation_db_path)
    logging.info("Set compilation database directory to " + compilation_db_dir)
    compilation_db =  ycm_core.CompilationDatabase(compilation_db_dir)

    if not compilation_db:
        logging.info("Compilation database file found but unable to load")
        return None
    return compilation_db

def flags_from_additional_files(filename):
        flags = []
        for candidate in additional_flag_files:
            flag_file = find_closest_path(filename,candidate)
            if flag_file:
                with open(flag_file) as fh:
                    directory = os.path.dirname(flag_file)
                    new_flags = []
                    for line in fh:
                        new_flags.append(line.strip())
                flags += make_relative_flags_to_absolute(new_flags, directory)
        return flags

## finding stuff - end
## simple helper
def is_header(filename):
    extension = os.path.splitext(filename)[1]
    return extension in header_ext

def make_relative_flags_to_absolute(flags, working_directory):
    if not working_directory:
        return list(flags)
    new_flags = []
    make_next_absolute = False
    path_flags = [ '-isystem', '-I', '-iquote', '--sysroot=' ]
    for flag in flags:
        new_flag = flag

        if make_next_absolute:
            make_next_absolute = False
            if not flag.startswith('/'):
                new_flag = os.path.join(working_directory, flag)

        for path_flag in path_flags:
            if flag == path_flag:
                make_next_absolute = True
                break

            if flag.startswith(path_flag):
                path = flag[ len(path_flag): ]
                new_flag = path_flag + os.path.join(working_directory, path)
                break

        if new_flag:
            new_flags.append(new_flag)
    return new_flags

def string_vector_to_list(string_vector):
    return [ str(x) for x in string_vector ]

def string_vector_to_str(string_vector):
    return str([ str(x) for x in string_vector ])


## simple helper - end
## using database / c interface
def get_flags_from_compilation_database(database, filename):
    try:
        compilation_info = get_info_for_file_from_database(database, filename)
    except Exception as e:
        logging.info("No compilation info for " + filename + " in compilation database")
        if throw_exceptions:
            raise e
        else:
            return None
    if not compilation_info:
        logging.info("No compilation info for " + filename + " in compilation database")
        return None

    #if not compilation_info.compiler_flags_:
    if not string_vector_to_list(compilation_info.compiler_flags_):
        logging.error("flags empty")
        return None

    logging.info("found CompilationInfo for : " + filename)
    logging.debug("dir" + PF(dir(compilation_info)))
    logging.debug("vars" + PF(vars(compilation_info)))
    logging.debug("vars" + PF(vars(compilation_info)))
    logging.debug("__dict__" + PF(compilation_info.__dict__))
    logging.debug("dir" + PF(compilation_info.compiler_flags_))
    logging.debug("flags: " + string_vector_to_str(compilation_info.compiler_flags_))
    logging.debug("workingdir:" + str(compilation_info.compiler_working_dir_))
    logging.debug("flags: " + string_vector_to_str(compilation_info.compiler_flags_))

    return make_relative_flags_to_absolute(
        compilation_info.compiler_flags_,
        compilation_info.compiler_working_dir_)

def get_info_for_file_from_database(database, filename):
    logging.debug("database:" + PF(database))
    if not is_header(filename):
        logging.info("is cpp file")
        return database.GetCompilationInfoForFile(filename)
    else:
        #find matching source file
        logging.info("is header file")
        basename = os.path.splitext(filename)[0]
        for extension in source_ext:
            replacement_file = basename + extension
            if os.path.exists(replacement_file):
                compilation_info = database.GetCompilationInfoForFile(replacement_file)
                if compilation_info.compiler_flags_:
                    return compilation_info

        #use any source file in the headers directory
        dpath = os.path.dirname(filename)
        for f in os.listdir(dpath):
            #skip non source files
            extension = os.path.splitext(f)[1]
            if extension not in source_ext:
                continue

            #get and join compilation for all cpp files in dir
            fpath = dpath + os.path.sep + f
            compilation_info = FakeInfo()
            tmp_info = database.GetCompilationInfoForFile(fpath)
            if tmp_info:
                compilation_info.add_info(tmp_info)
            compilation_info.close()
            if compilation_info.compiler_flags_:
                return compilation_info

        return None
## using database - end

def FlagsForFile(filename, **kwargs):
    filename = os.path.realpath(filename)
    logging.info("filename:" + filename)
    final_flags = []
    database = find_database(filename)
    if database:
        final_flags = get_flags_from_compilation_database(database, filename)

    if not final_flags and use_additional_files:
        final_flags = flags_from_additional_files(filename)

    if not final_flags: #database not there or does not contain the file
        logging.warning("using fallback strategy to get flags")
        final_flags = fallback_flags
        final_flags += flags_for_closest_include(filename)

    final_flags += base_flags
    return { 'flags': final_flags }

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    import sys
    for filename in sys.argv[1:]:
        print("file: " + filename +"\n")
        print("final result:\n" + PF(FlagsForFile(filename)))
