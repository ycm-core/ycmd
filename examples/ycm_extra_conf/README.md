# example .ycm_extra_conf.py for json compilation databases

ycm_extra_conf.jsondb.py is for finding flags in the compilation database for headers whose counterpart source file is not existent.
This is done by browsing the json db to find one source file (a translation unit), which uses the directory of our header as an include path (-I, -isystem).

Usage: cp ycm_extra_conf.XXXX.py to .ycm_extra_conf.py

