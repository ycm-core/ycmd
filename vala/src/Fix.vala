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

public class Ycmvala.Fix : Object {
  public GenericArray< FixChunk > chunks
    {
      get;
      set;
      default = new GenericArray< FixChunk >();
    }
  public Location location { get; construct; }
  public string text { get; construct; }

  public Fix( string text,
              Location location ) {
    Object( location: location,
            text: text );
  }

  public Fix.for_diagnostic( Diagnostic diagnostic ) {
    Object( location: diagnostic.range.begin,
            text: diagnostic.message );
  }
}
