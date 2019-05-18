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

public class Ycmvala.Range : Object {
  public Location begin { get; construct; }
  public Location end { get; construct; }
  public string? file {
    get {
      return begin.file;
    }
  }

  public Range( Location begin,
                Location end ) {
    Object( begin: begin,
            end: end );
  }

  public Range.invalid() {
    Object( begin: new Location.invalid(),
            end: new Location.invalid() );
  }

  internal Range.vala( Vala.SourceReference reference ) {
    Object( begin: new Location.vala( reference, false ),
            end: new Location.vala( reference, true ) );
  }

  public bool valid() {
    return begin.valid() && end.valid();
  }
}
