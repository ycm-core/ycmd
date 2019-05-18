// Copyright (C) 2019 Jakub Kaszycki
//
// This file is part of ycmd.
//
// ycmd is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// ycmd is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

public errordomain Ycmvala.CompleterError {
  NO_SUCH_TRANSLATION_UNIT,
  INVALID_LOCATION,
  NODE_NOT_FOUND,
  INVALID_NODE,
  MAIN_FILE_NOT_IN_SOURCES,
  INVALID_FLAGS,
  UNKNOWN_PROFILE,
  PACKAGE_LOAD_FAILED,
  NO_FILES,
}
