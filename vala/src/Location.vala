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

public class Ycmvala.Location : Object {
  public uint column { get; construct; }
  public string? file { get; construct; }
  public uint line { get; construct; }

  public Location( string file,
                   uint line,
                   uint column ) {
    Object( column: column,
            file: file,
            line: line );
  }

  public Location.invalid() {
    Object( column: 0,
            file: null,
            line: 0 );
  }

  internal Location.vala( Vala.SourceReference reference,
                          bool end = false ) {
    var file = reference.file.filename;
    uint column, line;

    if ( end ) {
      line = (uint) reference.end.line;
      column = (uint) reference.end.column + 1;
    } else {
      line = (uint) reference.begin.line;
      column = (uint) reference.begin.column;
    }

    Object( column: column,
            file: file,
            line: line );
  }

  internal Vala.SourceLocation to_vala() {
    return Vala.SourceLocation( null, (int) line, (int) column );
  }

  public bool valid() {
    return file != (string) null
      && line != 0
      && column != 0;
  }
}
